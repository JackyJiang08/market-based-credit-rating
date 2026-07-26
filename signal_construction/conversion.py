"""PIT -> TTC -> S&P conversion (TiC paper Section 5).

Two routes, with a clear division of labour.

1. **Lookup** against the conversion workbook (``TiC_TTC_conversion.xlsx``): the
   ``TTC`` grid gives the no-regulatory-arbitrage Through-The-Cycle PD by
   ``(CCM, mu)`` and the ``SP`` sheet maps a PD to a letter. The grids are
   proprietary, read from the git-ignored ``local/`` tree at runtime; nothing
   proprietary is committed. Authoritative **inside** its domain,
   ``CCM in [0.1, 540] x mu in [1, 160]``.

2. **Analytical no-arbitrage conversion** (Prop. 5.2.1), in two steps:
     Eq. (26)  solve ``CL_SP(CCM*) = CL_FH(CCM)`` so both systems demand the
               same capital confidence level;
     Eq. (27)  substitute the source PD and ``CCM*`` into the S&P TiC formula,
               the rating half of Eq. (24), to get the S&P RiskScore.
   The RiskScore is mapped back to a TTC PD through the published S&P
   Through-The-Cycle scale (Table 8, Prop. 5.1). This route needs no table and
   is defined for every ``CCM > 0``.

Inside the grid the lookup wins and the analytical route is the **oracle** that
checks it; a regression test asserts they agree to within one letter notch.
Outside the grid there is nothing to look up, so the analytical route produces
the rating and it is labelled ``ANALYTICAL``.

Verified against the paper: ``alpha_FH(1.5)=0.91906`` and ``alpha_FH(5.0)=0.72749``;
``CCM*=1.35373`` and ``2.22928``; every row of the S&P RiskScore column of
Tables 13 and 14 to within 0.01; Table 12's alpha and ``CCM*`` columns for all
seven agency grades.

**Known limit.** The Table 8 scale has seven grades. Below its best grade
(RiskScore 2.7) and inside its worst band (CCC/C) it cannot resolve notches, so
a rating there is determined by where the published scale stops rather than by
the model. Those are flagged ``at_floor`` rather than presented as measurements.
"""

from __future__ import annotations

import enum
import functools
import math
import os
from dataclasses import dataclass

import logging

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import log_ndtr, logsumexp
from scipy.stats import norm

LOG = logging.getLogger("pfpa.conversion")

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_XLSX = os.path.join(_PROJECT_ROOT, "local", "TiC_TTC_conversion.xlsx")
CACHE_DIR = os.path.join(_PROJECT_ROOT, "local", "tables")

# Analytical constants (paper Prop. 4.5.2-4.5.3, Section 5.3).
CML = math.e ** 1.35
SQRT_CML = math.sqrt(CML)

# Constants of Rating System Q (Prop. 4.2). Prop. 4.2 quotes S&P as 0.626 and
# Moody's as 0.746; Section 5.3 uses the precise values below.
Q_SP = 0.625913
Q_MOODYS = 0.7462

# S&P's Through-The-Cycle scale (paper Table 8, Prop. 5.1): the RiskScore of each
# letter grade and the TTC one-year default probability that goes with it. This
# is the published agency scale, and it is what turns an analytically converted
# RiskScore back into a probability. Ascending in both columns.
SP_TTC_RISK_SCORES = np.array([2.7, 3.5, 5.2, 9.9, 22.2, 50.7, 154.8])
SP_TTC_PD1 = np.array([0.0001, 0.0003, 0.0007, 0.0023, 0.0088, 0.0441, 0.3359])


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


class RatingDetermination(enum.Enum):
    """What actually decided the letter: the model, or the edge of a scale.

    A rating basis (`RatingBasis`) says which *route* produced a number. This
    says whether that number carries information.

    SCALE_RESOLVED       the TTC PD sits strictly inside the range the route can
                         express, so the scale could tell this value apart from
                         its neighbours. **This is a statement about the scale's
                         resolution, not about the estimate's precision.** DELL
                         is the cautionary case: it has the strongest drift
                         t-statistic in the universe and the *widest* bootstrap
                         letter interval (10 notches), because it sits where the
                         S&P scale is finely notched. The label was called
                         MODEL_DETERMINED until 2026-07-26; that name implied a
                         precision claim it never made.
    PINNED_AT_FLOOR      the grid lookup returned its smallest expressible value
                         (2bp in the shipped workbook). The model asked for
                         something smaller; the table had nothing left to say.
    PINNED_AT_SCALE_TOP  the analytical route produced a RiskScore below the best
                         published grade of the Table 8 scale (2.7), so the TTC
                         PD is that grade's 0.01% whatever the model said.
    NOT_RATED            no letter was produced at all (OFF_GRID or the drift
                         regime is defective).

    This is not a defect report. A structural model applied to large
    investment-grade issuers produces one-year default probabilities many orders
    of magnitude below anything a rating scale resolves -- see
    docs/RATING_DETERMINATION.md. Publishing the count is how the deliverable
    stays honest about which of its ratings the scale could resolve at all.
    Whether the *estimate* behind a resolved letter is precise is a separate
    question, answered by the drift t-statistic and the bootstrap interval.
    """

    SCALE_RESOLVED = "SCALE_RESOLVED"
    PINNED_AT_FLOOR = "PINNED_AT_FLOOR"
    PINNED_AT_SCALE_TOP = "PINNED_AT_SCALE_TOP"
    NOT_RATED = "NOT_RATED"


def classify_determination(basis: "RatingBasis | None", at_floor: bool | None,
                           risk_score: float | None = None) -> RatingDetermination:
    """Classify a rating by what decided it."""
    if basis is None or basis in (RatingBasis.OFF_GRID, RatingBasis.NOT_APPLICABLE):
        return RatingDetermination.NOT_RATED
    if basis is RatingBasis.ANALYTICAL:
        if risk_score is not None and is_scale_floor_determined(risk_score):
            return RatingDetermination.PINNED_AT_SCALE_TOP
        if at_floor:
            return RatingDetermination.PINNED_AT_SCALE_TOP
        return RatingDetermination.SCALE_RESOLVED
    return (RatingDetermination.PINNED_AT_FLOOR if at_floor
            else RatingDetermination.SCALE_RESOLVED)


class RatingBasis(enum.Enum):
    """How a reported rating was arrived at. Every rating carries one.

    GRID_INTERIOR   (CCM, mu) fell inside the lookup grid; the TTC PD is an
                    interpolation between real grid cells and the letter is
                    model-determined.
    ANALYTICAL      the lookup grid did not cover the point, so the analytical
                    no-arbitrage route (Prop. 5.2.1, Eq. 26 then Eq. 27)
                    supplied the rating. No table was consulted.
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
    at_floor: bool = False        # value sits at the edge of what the route expresses
    risk_score: float = float("nan")   # analytical route only: Eq. (27) output


def _axis(series: pd.Series) -> np.ndarray:
    return pd.to_numeric(series, errors="coerce").to_numpy()


def _grid(block: pd.DataFrame) -> np.ndarray:
    return block.apply(pd.to_numeric, errors="coerce").to_numpy()


@functools.lru_cache(maxsize=1)
def load_tables(xlsx_path: str = DEFAULT_XLSX) -> ConversionTables:
    """Parse the conversion workbook and cache CSV copies under local/tables."""
    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(
            f"Conversion workbook not found at {xlsx_path}. It is proprietary "
            "reference data kept out of git; place it under local/ to enable "
            "the grid route.")
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
    except OSError as exc:
        # Caching is best-effort, but a read-only disk or a permissions problem
        # should not be invisible -- it was silently swallowed before.
        LOG.warning("conversion table cache not written to %s: %s", CACHE_DIR, exc)


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


def ttc_pd(tables: ConversionTables, ccm: float, mu: float,
           pit_pd: float | None = None) -> GridLookup:
    """Through-The-Cycle PD by (CCM, mu), with the basis it was reached on.

    Inside the grid the lookup is authoritative and the analytical route is the
    oracle that checks it. Outside the grid there is nothing to look up, so the
    analytical route (Prop. 5.2.1, Eq. 26 then Eq. 27) produces the rating --
    which is defined for every `CCM > 0` and needs no table. The clamped edge
    value is never returned: for every off-grid company in this universe the
    clamped cell sits on the 2bp floor, so publishing it let the grid boundary
    choose the letter.

    `pit_pd` is required for the analytical route (it is the `PD_A` of Eq. 27).
    Without it an off-grid point stays OFF_GRID.
    """
    # A defective drift regime leaves (CCM, mu) undefined; nothing to look up.
    if not (np.isfinite(ccm) and np.isfinite(mu)):
        return GridLookup(float("nan"), False, RatingBasis.NOT_APPLICABLE, False)

    look = _bilinear(tables.ttc_grid, tables.ccm_axis, tables.mu_axis, ccm, mu)
    if not look.off_grid:
        look.basis = RatingBasis.GRID_INTERIOR
        look.at_floor = is_floor_determined(tables, look.value)
        return look

    # --- outside the grid: convert analytically -----------------------------
    if pit_pd is None or not np.isfinite(pit_pd):
        return GridLookup(float("nan"), True, RatingBasis.OFF_GRID, False)

    analytical = no_arb_convert(pit_pd, ccm)
    if not np.isfinite(analytical.ttc_pd):
        return GridLookup(float("nan"), True, RatingBasis.OFF_GRID, False)

    # For an analytical rating "at floor" means the *scale* ran out, not the
    # grid: the RiskScore fell below Table 8's best grade.
    return GridLookup(analytical.ttc_pd, True, RatingBasis.ANALYTICAL,
                      analytical.at_scale_floor, analytical.risk_score)


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


def alpha_lognormal(ccm: float, q: float) -> float:
    """Capital confidence level for a log-normal rating system (Eq. 22).

    The exponent `theta` of Eq. (22) is `1/Q` for an agency system, so the
    coefficient on `ln CCM` is `1/q`, not `q`. In the PDF this renders as a
    stacked fraction that reads like `0.625913 * ln CCM`; it is its reciprocal.
    Verified through the paper's anchors -- do not "simplify" it.
    """
    L = math.log(ccm + 1.0)
    return float(norm.cdf((1.35 - (1.0 / q) * math.log(ccm) + L / 2.0)
                          / math.sqrt(L)))


def alpha_sp(ccm: float) -> float:
    """Capital confidence level under the S&P log-normal system (Eq. 22)."""
    return alpha_lognormal(ccm, Q_SP)


def alpha_moodys(ccm: float) -> float:
    """Capital confidence level under the Moody's log-normal system (Eq. 22)."""
    return alpha_lognormal(ccm, Q_MOODYS)


def tic_lognormal(pd_value: float, ccm: float, q: float) -> float:
    """The rating half of Eq. (24): TiC of a log-normal agency system.

        ln(TiC) = Q * Phi^-1(PD) * sqrt(ln(CCM+1))
                  - (Q/2) * ln(CCM+1) + ln(CCM)

    Substituting a *source* system's PD together with the matched `CCM*` is
    Eq. (27), the second half of the no-arbitrage conversion. Verified against
    the paper: reproduces every row of the `S&P` RiskScore column of Tables 13
    and 14 to within 0.005, and Table 12 to within 0.01.
    """
    if not (0.0 < pd_value < 1.0) or not (ccm > 0.0) or not np.isfinite(ccm):
        return float("nan")
    L = math.log(ccm + 1.0)
    ln_tic = (q * norm.ppf(pd_value) * math.sqrt(L) - (q / 2.0) * L
              + math.log(ccm))
    return float(math.exp(ln_tic))


def risk_score_sp(pd_value: float, ccm_star: float) -> float:
    """S&P RiskScore = 100 * TiC_SP (Eq. 5 applied to Eq. 24)."""
    return 100.0 * tic_lognormal(pd_value, ccm_star, Q_SP)


def ttc_pd_from_risk_score(risk_score: float) -> float:
    """Map an S&P RiskScore back to a TTC PD using the Table 8 scale.

    Log-log monotone interpolation over the seven published grades. Agreement
    with the `S&P TTC` column of Tables 13/14 is within 0.25pp from AAA through
    B; it widens to ~4pp inside the CCC/C band, where the published column uses
    a finer notching than the paper prints. Values outside the scale are held at
    its endpoints rather than extrapolated.
    """
    if risk_score is None or not np.isfinite(risk_score) or risk_score <= 0:
        return float("nan")
    return float(np.exp(np.interp(math.log(risk_score),
                                  np.log(SP_TTC_RISK_SCORES),
                                  np.log(SP_TTC_PD1))))


def no_arb_ccm_star(ccm_first_hitting: float) -> float:
    """S&P CCM* matching the first-hitting confidence level (Prop. 5.2.1 Eq. 26).

    Step 1 of the two-step conversion: solve `CL_SP(CCM*) = CL_FH(CCM)` so both
    systems demand the same capital confidence level, which is what makes the
    conversion free of regulatory arbitrage.

    Verified: no_arb_ccm_star(1.5) = 1.35373 and no_arb_ccm_star(5.0) = 2.22928
    (paper Section 5.3).
    """
    target = alpha_first_hitting(ccm_first_hitting)
    return _solve_ccm_star(target)


# Bracket for the CCM* root search. alpha is decreasing in CCM (Eq. 22 part 3)
# and tends to 1 as CCM -> 0, so a source system whose alpha has saturated at
# 1.0 in float64 has no identifiable CCM*: any small enough CCM satisfies it.
# Returning the bracket edge in that case would be a fabricated number.
_CCM_STAR_LO, _CCM_STAR_HI = 1e-8, 1e4


def _solve_ccm_star(target_alpha: float) -> float:
    """Solve CL_SP(CCM*) = target_alpha, or NaN if the target is unreachable."""
    if not np.isfinite(target_alpha):
        return float("nan")
    lo = alpha_sp(_CCM_STAR_LO) - target_alpha
    hi = alpha_sp(_CCM_STAR_HI) - target_alpha
    if lo == 0.0:
        return _CCM_STAR_LO
    if lo * hi > 0:
        # No sign change: the confidence level is outside what the S&P system
        # can express. Saturated alpha (a firm the model reads as essentially
        # default-free at one year) lands here.
        return float("nan")
    return float(brentq(lambda c: alpha_sp(c) - target_alpha,
                        _CCM_STAR_LO, _CCM_STAR_HI, maxiter=200))


def no_arb_ccm_star_from_agency(ccm_source: float, q_source: float) -> float:
    """CCM* converting one log-normal agency system into S&P's (Eq. 26).

    The Moody's -> S&P direction of Prop. 5.2.2 / Table 12.
    """
    return _solve_ccm_star(alpha_lognormal(ccm_source, q_source))


@dataclass
class AnalyticalRating:
    """A rating produced without touching the lookup grid."""

    ccm_star: float          # Eq. (26): the S&P CCM at matched confidence
    risk_score: float        # Eq. (27): 100 * TiC_SP(PD_FH, CCM*)
    ttc_pd: float            # Table 8 scale applied to the RiskScore
    alpha: float             # the matched capital confidence level
    at_scale_floor: bool = False   # RiskScore below the Table 8 scale's lowest
                                   # grade, so the TTC PD is the scale's floor
                                   # rather than a resolved value


def no_arb_convert(pit_pd: float, ccm_first_hitting: float) -> AnalyticalRating:
    """The full Prop. 5.2.1 conversion, Eq. (26) then Eq. (27).

    Takes a first-passage rating -- its PIT PD from Eq. (13) and its CCM from
    Eq. (11) -- and returns the S&P-equivalent rating with no lookup grid
    involved, so it is defined wherever `CCM > 0`, including outside the grid's
    `CCM in [0.1, 540]` domain.
    """
    nan = float("nan")
    if not (np.isfinite(pit_pd) and np.isfinite(ccm_first_hitting)) \
            or ccm_first_hitting <= 0:
        return AnalyticalRating(nan, nan, nan, nan)

    alpha = alpha_first_hitting(ccm_first_hitting)
    ccm_star = _solve_ccm_star(alpha)
    if not np.isfinite(ccm_star):
        return AnalyticalRating(nan, nan, nan, alpha)
    rs = risk_score_sp(pit_pd, ccm_star)
    return AnalyticalRating(ccm_star, rs, ttc_pd_from_risk_score(rs), alpha,
                            at_scale_floor=is_scale_floor_determined(rs))


def is_scale_floor_determined(risk_score: float) -> bool:
    """Is this RiskScore below the Table 8 scale's best grade?

    Below RiskScore 2.7 the scale has nothing left to say: every such firm maps
    to the AAA anchor's 0.01%. The rating is then determined by where the
    published scale stops, exactly as a grid-floor rating is determined by where
    the table stops.
    """
    return bool(np.isfinite(risk_score)
                and risk_score <= float(SP_TTC_RISK_SCORES[0]))
