"""PIT -> TTC -> S&P conversion (TiC paper Section 5).

Two consistent routes are provided:

1. **Lookup** against the conversion workbook (``TiC_TTC_conversion
   .xlsx``): the ``TTC`` grid gives the no-regulatory-arbitrage Through-The-Cycle
   PD by ``(CCM, mu)`` and the ``SP`` sheet maps a PD to an S&P letter. These
   grids are proprietary and are read from the git-ignored ``local/``
   tree at runtime; nothing proprietary is committed.

2. **Analytical no-arbitrage conversion** (Prop. 5.2.1-5.2.2): match the capital
   confidence level ``alpha`` between the first-hitting and S&P systems
   (Eq. 22, CML=e^1.35, theta=1, S&P Q=0.625913) to solve ``CCM*``. Verified to
   reproduce the paper (alpha_FH(1.5)=0.91906, CCM*=1.35373).

The lookup route is authoritative for the submission; the analytical route
validates it and extends past the grid edges.
"""

from __future__ import annotations

import functools
import math
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import brentq
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


@dataclass
class GridLookup:
    value: float
    off_grid: bool                # True if (CCM, mu) was clamped to an edge


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
    """No-arbitrage Through-The-Cycle PD by (CCM, mu) from the TTC grid."""
    return _bilinear(tables.ttc_grid, tables.ccm_axis, tables.mu_axis, ccm, mu)


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
    """
    a = SQRT_CML
    return float(norm.cdf(a / ccm - 1 / a)
                 + math.exp(2 / ccm) * norm.cdf(-a / ccm - 1 / a))


def alpha_sp(ccm: float) -> float:
    """Capital confidence level under the S&P log-normal system (Eq. 22)."""
    L = math.log(ccm + 1.0)
    return float(norm.cdf((1.35 - (1.0 / Q_SP) * math.log(ccm) + L / 2.0)
                          / math.sqrt(L)))


def no_arb_ccm_star(ccm_first_hitting: float) -> float:
    """S&P CCM* matching the first-hitting confidence level (Prop. 5.2.1).

    Verified: no_arb_ccm_star(1.5) = 1.35373 (paper Section 5.3).
    """
    target = alpha_first_hitting(ccm_first_hitting)
    return float(brentq(lambda c: alpha_sp(c) - target, 1e-4, 1e4, maxiter=200))
