"""TiC / first-passage credit measures derived from the EM asset estimates.

All formulas are the first-passage (KMV) results of the TiC paper. Inputs are
the EM outputs ``(sigma_A, A, eta_A)`` and the default-point debt ``D`` on the
last trading day, with horizon ``T = 1`` year.

Paper references:
  - mu, CCM (first-passage driving factors) ......... Eq. (11)
  - TiC = CCM/mu = sigma_A^2 / ln^2(A/D), RiskScore=100*TiC ... Eq. (12), (5)
  - Default peak lambda, CCM = lambda^(-2/3) - 1 .... Eq. (3), (6)
  - DD, EDF = Phi(-DD) .............................. Eq. (14)
  - PIT PD (inverse-Gaussian first-hitting) ......... Eq. (13)
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass

import numpy as np
from scipy.special import log_ndtr, logsumexp

from . import config


class DriftRegime(enum.Enum):
    """Whether Prop. 4.4.1's precondition `eta - sigma_A^2/2 > 0` holds.

    VALID      the assumption holds; Eq. (11) `mu` and `CCM` are defined.
    DEFECTIVE  the assumption fails. The first-passage time is defective:
               default occurs almost surely and `mu = E[tau]` diverges, so
               Eq. (11) has no finite value. Downstream measures that depend
               on `mu`/`CCM` are NOT_APPLICABLE, not merely unavailable.
    """

    VALID = "VALID"
    DEFECTIVE = "DEFECTIVE"


def is_weakly_identified(drift: float, drift_se: float,
                         threshold: float = None) -> bool:
    """Is the drift statistically indistinguishable from zero?

    `|t| = |drift| / SE` below the threshold means `mu = ln(A/D)/drift` and
    `CCM` are dividing by a quantity the data cannot pin down. The rating is
    still produced -- this annotates it. Contrast `drift_regime`, which
    suppresses output for the Prop. 4.4.1 assumption failure.
    """
    if threshold is None:
        threshold = config.WEAK_IDENTIFICATION_T
    if not (math.isfinite(drift) and math.isfinite(drift_se)) or drift_se <= 0:
        return True
    return abs(drift / drift_se) < threshold


def drift_regime(drift: float) -> DriftRegime:
    """Classify a signed drift `eta - sigma_A^2/2` against Prop. 4.4.1."""
    if math.isfinite(drift) and drift > 0.0:
        return DriftRegime.VALID
    return DriftRegime.DEFECTIVE


@dataclass
class CreditMeasures:
    sigma_A: float
    asset: float          # A on the last trading day
    debt: float           # default-point debt D
    eta_A: float          # asset return (drift)
    ln_A_D: float         # ln(A/D)
    drift: float          # eta_A - sigma_A^2/2  (signed)
    mu: float             # Life Expectancy E[tau]        (Eq. 11)
    ccm: float            # Credit Corrosion Measure       (Eq. 11)
    tic: float            # Time-Consistent rating (Q=1)   (Eq. 12)
    risk_score: float     # 100 * TiC                      (Eq. 5)
    lam: float            # default peak lambda            (Eq. 3/6)
    dd: float             # distance to default            (Eq. 14)
    edf: float            # Phi(-DD)                        (Eq. 14)
    pit_pd: float         # 1-year PIT PD                  (Eq. 13)
    regime: "DriftRegime" = DriftRegime.VALID   # Prop. 4.4.1 precondition


def pit_pd_first_hitting(mu: float, ccm: float, horizon: float = 1.0) -> float:
    """1-year Point-in-Time PD from the inverse-Gaussian first-hitting time.

    Paper Eq. (13):
        PD_T = Phi( a*(sqrt(T/mu) - sqrt(mu/T)) )
             + exp(2/CCM) * Phi( -a*(sqrt(T/mu) + sqrt(mu/T)) ),  a = sqrt(1/CCM)

    Verified against paper Table 13 (CCM=1.5: mu=1 -> 69.40%, mu=5 -> 12.60%)
    and Table 14 (CCM=5: mu=1 -> 77.70%).

    Computed in log space. The `exp(2/CCM)` factor overflows a float64 above
    CCM ~ 0.00276, and the claim that "the paired Phi underflows faster" is
    false: the exponents are `2/CCM` and `-(1/CCM)(sqrt(T/mu)+sqrt(mu/T))^2/2`,
    which cancel exactly at mu = T. The product tends to an O(1) quantity there,
    so the old `except OverflowError: term2 = 0` discarded up to ~0.9 percentage
    points of PD, always understating risk. Summing the two logs with logsumexp
    removes the overflow and the fallback together.
    """
    # NaN reaches here from a defective drift regime, where (mu, CCM) are
    # undefined by construction. Return NaN explicitly rather than relying on
    # NaN comparisons falling through the guard below.
    if not (math.isfinite(mu) and math.isfinite(ccm)) or mu <= 0 or ccm <= 0:
        return float("nan")
    a = math.sqrt(1.0 / ccm)
    s_t_mu = math.sqrt(horizon / mu)
    s_mu_t = math.sqrt(mu / horizon)

    log_term1 = log_ndtr(a * (s_t_mu - s_mu_t))
    log_term2 = 2.0 / ccm + log_ndtr(-a * (s_t_mu + s_mu_t))
    log_pd = logsumexp([log_term1, log_term2])
    if not np.isfinite(log_pd):
        raise ValueError(
            f"non-finite log PD at mu={mu!r}, ccm={ccm!r}, horizon={horizon!r}")

    pd = float(np.exp(log_pd))
    return float(min(max(pd, 0.0), 1.0))


def compute(sigma_A: float, asset: float, debt: float, eta_A: float,
            horizon: float = 1.0) -> CreditMeasures:
    """Compute all first-passage credit measures for one company."""
    if not (asset > debt > 0):
        raise ValueError(f"require A ({asset:.3g}) > D ({debt:.3g}) > 0")

    ln_ad = math.log(asset / debt)
    drift = eta_A - 0.5 * sigma_A ** 2          # signed, exactly as Eq. (11) uses it

    # Prop. 4.4.1 assumes `eta - sigma_A^2/2 > 0`. When it does not hold the
    # first-passage time is defective -- default occurs almost surely and
    # `mu = E[tau]` diverges -- so Eq. (11) has no value to compute. We classify
    # the regime and return NaN rather than substituting |drift|, which is what
    # this code used to do and which silently reported a finite `mu`/`CCM` that
    # is not the paper's quantity. See docs/adr/0001-drift-estimation.md.
    regime = drift_regime(drift)
    if regime is DriftRegime.VALID:
        mu = ln_ad / drift
        ccm = sigma_A ** 2 / (ln_ad * drift)
    else:
        mu = float("nan")
        ccm = float("nan")

    # TiC rating is eta-independent (Q=1): sigma_A^2 / ln^2(A/D) (Eq. 12).
    # This one survives a defective regime: Prop. 4.4.2 makes it a function of
    # sigma_A and ln(A/D) only, so it is defined whatever the drift does.
    tic = sigma_A ** 2 / ln_ad ** 2
    risk_score = 100.0 * tic
    lam = (ccm + 1.0) ** (-1.5) if math.isfinite(ccm) else float("nan")  # Eq. (6)

    # Distance to default / EDF (Eq. 14), using the signed drift.
    # EDF via log_ndtr: norm.cdf(-dd) returns exactly 0.0 from dd ~ 38 upward,
    # while log_ndtr still resolves past 39. The exp() underflows to 0 only when
    # the true value is genuinely below the smallest subnormal.
    sqrtT = math.sqrt(horizon)
    dd = (ln_ad + drift * horizon) / (sigma_A * sqrtT)
    edf = float(np.exp(log_ndtr(-dd)))

    # PIT PD is a function of (mu, CCM), so it is undefined in a defective
    # regime too. DD and EDF are not: Eq. (14) uses the signed drift directly
    # and stays meaningful (a negative drift simply lowers DD).
    pit = pit_pd_first_hitting(mu, ccm, horizon)

    return CreditMeasures(
        sigma_A=sigma_A, asset=asset, debt=debt, eta_A=eta_A, ln_A_D=ln_ad,
        drift=drift, mu=mu, ccm=ccm, tic=tic, risk_score=risk_score, lam=lam,
        dd=dd, edf=edf, pit_pd=pit, regime=regime)
