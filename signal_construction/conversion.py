"""PIT -> TTC -> S&P conversion (TiC paper Section 5).

Two consistent routes are provided:

1. **Lookup** against the conversion workbook (``TiC_TTC_conversion
   .xlsx``): the ``TTC`` grid gives the no-regulatory-arbitrage Through-The-Cycle
   PD by ``(CCM, mu)`` and the ``SP`` sheet maps a PD to an S&P letter. These
   grids are proprietary and are read from the git-ignored ``local/``
   tree at runtime; nothing proprietary is committed.

2. **Analytical no-arbitrage conversion**, step 1 only (Prop. 5.2.1 Eq. 26):
   match the capital confidence level ``alpha`` between the first-hitting and
   S&P systems (Eq. 22, CML=e^1.35, theta=1, S&P Q=0.625913) to solve ``CCM*``.
   Verified to reproduce the paper (alpha_FH(1.5)=0.91906, CCM*=1.35373).

The lookup route is the only route that produces a rating. The analytical route
is a **verification check against the paper's published anchors, and nothing
more**: it is not reachable from the rating path and it does not extend past the
grid edges. Turning ``CCM*`` into a rating requires Eq. (27),
``RS_B = TiC_B(PD_A, CCM*)``, which in turn requires the S&P rating half of
Eq. (24); neither is implemented (issue #11). Until they are, a point outside the
grid has no rating and is reported as ``OFF_GRID`` (issue #12) rather than being
clamped to an edge cell.
"""

from __future__ import annotations

import enum
import functools
import math
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import log_ndtr, logsumexp
from scipy.stats import norm

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_XLSX = os.path.join(_PROJECT_ROOT, "local", "TiC_TTC_conversion.xlsx")
CACHE_DIR = os.path.join(_PROJECT_ROOT, "local", "tables")

# Analytical constants (paper Prop. 4.5.2-4.5.3, Section 5.3).
CML = math.e ** 1.35
SQRT_CML = math.sqrt(CML)
Q_SP = 0.625913


# --------------------------------------------------------------------------- #
# Lookup tables (loaded from the local, git-ignored workbook)
# --------------------------------------------------------------------------- #
@dataclass
class ConversionTables:
    ccm_axis: np.ndarray          # grid rows, ascending
    mu_axis: np.ndarray           # grid columns, ascending
    ttc_grid: np.ndarray          # TTC (S&P-equivalent) PD by [CCM, mu]
    pit_grid: np.ndarray          # PIT PD by [CCM, mu] (cross-check)
    sp_labels: list[str]          # S&P letters, best -> worst
    sp_thresholds: np.ndarray     # ascending lower-bound PD per label


class RatingBasis(enum.Enum):
    """How a reported rating was arrived at. Every rating carries one.

    GRID_INTERIOR   (CCM, mu) fell inside the lookup grid; the TTC PD is an
                    interpolation between real grid cells and the letter is
                    model-determined.
    ANALYTICAL      the lookup grid did not cover the point and the analytical
                    no-arbitrage route (Prop. 5.2.1) supplied the rating.
                    Requires Eq. (27), which is not implemented -- see #11.
                    No result currently carries this basis.
    OFF_GRID        (CCM, mu) fell outside the grid and no analytical route was
                    available. **No letter is reported.** The previous behaviour
                    clamped to the nearest edge and published the resulting
                    letter, which made the grid boundary, not the model, decide
                    the rating.
    NOT_APPLICABLE  the drift regime is defective (Prop. 4.4.1 fails), so
                    (CCM, mu) do not exist and nothing downstream of them does.
    """

    GRID_INTERIOR = "GRID_INTERIOR"
    ANALYTICAL = "ANALYTICAL"
    OFF_GRID = "OFF_GRID"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class GridLookup:
    value: float
    off_grid: bool                # True if (CCM, mu) was clamped to an edge
    basis: RatingBasis = RatingBasis.GRID_INTERIOR
    at_floor: bool = False        # value sits on the grid's TTC floor (2bp)


def _axis(series: pd.Series) -> np.ndarray:
    return pd.to_numeric(series, errors="coerce").to_numpy()


def _grid(block: pd.DataFrame) -> np.ndarray:
    return block.apply(pd.to_numeric, errors="coerce").to_numpy()


@functools.lru_cache(maxsize=1)
def load_tables(xlsx_path: str = DEFAULT_XLSX) -> ConversionTables:
    """Parse the conversion workbook and cache CSV copies under local/tables."""
    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(
            f"Conversion workbook not found at {xlsx_path}. It is proprietary PFPA data "
            "kept out of git; place it under local/ to enable TTC/S&P mapping.")
    xl = pd.ExcelFile(xlsx_path)

    def parse_grid(sheet: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        raw = pd.read_excel(xl, sheet, header=None)
        ccm_axis = _axis(raw.iloc[2:, 0])      # rows = CCM
        mu_axis = _axis(raw.iloc[1, 1:])       # cols = mu
        grid = _grid(raw.iloc[2:, 1:])
        return ccm_axis, mu_axis, grid

    ccm_axis, mu_axis, ttc = parse_grid("TTC")
    _, _, pit = parse_grid("PIT")

    sp_raw = pd.read_excel(xl, "SP", header=None)
    labels, thresholds = [], []
    for _, row in sp_raw.iterrows():
        label, thr = row.iloc[0], pd.to_numeric(row.iloc[1], errors="coerce")
        if isinstance(label, str) and label.strip() and pd.notna(thr):
            labels.append(label.strip())
            thresholds.append(float(thr))

    tables = ConversionTables(ccm_axis, mu_axis, ttc, pit,
                              labels, np.asarray(thresholds))
    _cache_csv(tables)
    return tables


def _cache_csv(tables: ConversionTables) -> None:
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        pd.DataFrame(tables.ttc_grid, index=tables.ccm_axis,
                     columns=tables.mu_axis).to_csv(os.path.join(CACHE_DIR, "ttc.csv"))
        pd.DataFrame({"SP": tables.sp_labels,
                      "PD_threshold": tables.sp_thresholds}).to_csv(
            os.path.join(CACHE_DIR, "sp_thresholds.csv"), index=False)
    except Exception:  # noqa: BLE001 - caching is best-effort
        pass


def _bilinear(grid: np.ndarray, xaxis: np.ndarray, yaxis: np.ndarray,
              x: float, y: float) -> GridLookup:
    """Bilinear interpolation with edge clamping; flags out-of-range inputs."""
    xc = float(np.clip(x, xaxis[0], xaxis[-1]))
    yc = float(np.clip(y, yaxis[0], yaxis[-1]))
    off = (xc != x) or (yc != y)
    i = int(np.clip(np.searchsorted(xaxis, xc) - 1, 0, len(xaxis) - 2))
    j = int(np.clip(np.searchsorted(yaxis, yc) - 1, 0, len(yaxis) - 2))
    x0, x1 = xaxis[i], xaxis[i + 1]
    y0, y1 = yaxis[j], yaxis[j + 1]
    tx = 0.0 if x1 == x0 else (xc - x0) / (x1 - x0)
    ty = 0.0 if y1 == y0 else (yc - y0) / (y1 - y0)
    v = ((1 - tx) * (1 - ty) * grid[i, j] + tx * (1 - ty) * grid[i + 1, j]
         + (1 - tx) * ty * grid[i, j + 1] + tx * ty * grid[i + 1, j + 1])
    return GridLookup(float(v), off)


def ttc_pd(tables: ConversionTables, ccm: float, mu: float) -> GridLookup:
    """No-arbitrage Through-The-Cycle PD by (CCM, mu), with its rating basis.

    A point outside the grid is reported as ``OFF_GRID`` with a NaN value. The
    clamped edge value is deliberately **not** returned as a rating: for every
    off-grid company in the current universe the clamped cell sits on the grid's
    2bp TTC floor, so publishing it meant the grid boundary chose the letter.
    """
    # A defective drift regime leaves (CCM, mu) undefined; nothing to look up.
    if not (np.isfinite(ccm) and np.isfinite(mu)):
        return GridLookup(float("nan"), False, RatingBasis.NOT_APPLICABLE, False)

    look = _bilinear(tables.ttc_grid, tables.ccm_axis, tables.mu_axis, ccm, mu)
    if look.off_grid:
        # Prop. 5.2.1's analytical route would belong here, but it needs Eq. (27)
        # to turn CCM* into a rating and that is not implemented (#11). Until it
        # is, an off-grid point has no defensible rating.
        return GridLookup(float("nan"), True, RatingBasis.OFF_GRID, False)

    look.basis = RatingBasis.GRID_INTERIOR
    look.at_floor = is_floor_determined(tables, look.value)
    return look


# Width of the grid's floor region, as a multiple of the floor itself. The
# shipped workbook floors at 2bp and its next distinct values are 0.00020022,
# 0.00020023, ... -- cells that differ only in the fifth significant figure
# because the underlying no-arbitrage PD is far below what the grid expresses.
# Anything inside this band is saturated, not resolved.
FLOOR_BAND = 1.05


def ttc_floor(tables: ConversionTables) -> float:
    """The smallest TTC PD the grid can express (2bp in the shipped workbook)."""
    finite = tables.ttc_grid[np.isfinite(tables.ttc_grid)]
    return float(finite.min()) if finite.size else float("nan")


def is_floor_determined(tables: ConversionTables, value: float) -> bool:
    """Is this TTC PD set by the grid's floor rather than by the model?

    A value inside the floor band means the model asked for a smaller number
    than the grid can represent, so the letter that follows is an artifact of
    where the table stops -- not a measurement. This is the honest explanation
    for a cluster of identical top ratings.
    """
    if value is None or not np.isfinite(value):
        return False
    floor = ttc_floor(tables)
    return bool(np.isfinite(floor) and value <= floor * FLOOR_BAND)


def sp_rating(tables: ConversionTables, pd_value: float) -> str:
    """Map a (TTC) PD to an S&P letter: the worst grade whose threshold <= PD."""
    if pd_value is None or not np.isfinite(pd_value):
        return "n/a"
    idx = int(np.searchsorted(tables.sp_thresholds, pd_value, side="right") - 1)
    idx = max(0, min(idx, len(tables.sp_labels) - 1))
    return tables.sp_labels[idx]


def outlook(pit_pd: float, ttc_pd_value: float) -> float:
    """Credit outlook = PIT PD - S&P TTC PD (Prop. 5.3).

    >0: short-term risk exceeds through-the-cycle (expected to revert down);
    <0: the reverse. Reported as a signed value.
    """
    return float(pit_pd - ttc_pd_value)


# --------------------------------------------------------------------------- #
# Analytical no-regulatory-arbitrage conversion (Prop. 5.2.1-5.2.2)
# --------------------------------------------------------------------------- #
def alpha_first_hitting(ccm: float) -> float:
    """Capital confidence level for a first-hitting rating (Eq. 22, IG, theta=1).

    Verified: alpha_first_hitting(1.5) = 0.91906 (paper Section 5.3).

    Computed in log space for the same reason as Eq. (13): this expression has
    the same `exp(2/CCM) * Phi(...)` shape, and previously had no overflow guard
    at all -- it raised OverflowError outright for CCM below ~0.00276.
    """
    a = SQRT_CML
    log_alpha = logsumexp([log_ndtr(a / ccm - 1 / a),
                           2.0 / ccm + log_ndtr(-a / ccm - 1 / a)])
    if not np.isfinite(log_alpha):
        raise ValueError(f"non-finite log alpha at ccm={ccm!r}")
    return float(np.exp(log_alpha))


def alpha_sp(ccm: float) -> float:
    """Capital confidence level under the S&P log-normal system (Eq. 22)."""
    L = math.log(ccm + 1.0)
    return float(norm.cdf((1.35 - (1.0 / Q_SP) * math.log(ccm) + L / 2.0)
                          / math.sqrt(L)))


def no_arb_ccm_star(ccm_first_hitting: float) -> float:
    """S&P CCM* matching the first-hitting confidence level (Prop. 5.2.1 Eq. 26).

    Verified: no_arb_ccm_star(1.5) = 1.35373 (paper Section 5.3).

    **Not on the rating path.** This is step 1 of the two-step conversion; step 2
    (Eq. 27) is not implemented, so this cannot produce a rating on its own. Its
    only caller is the test that pins the paper's anchor. See #11.
    """
    target = alpha_first_hitting(ccm_first_hitting)
    return float(brentq(lambda c: alpha_sp(c) - target, 1e-4, 1e4, maxiter=200))
