"""Uncertainty propagation by moving-block bootstrap over asset returns.

Every number this pipeline publishes is a point estimate built on two quantities
estimated from a finite sample: the asset volatility `sigma_A` and the asset
drift `eta_A`. `docs/adr/0001-drift-estimation.md` records that the drift's
standard error is `sigma_A / sqrt(span)`, which for several companies is the
same size as the drift itself. A point rating computed from such an estimate
looks exactly like one computed from a precise estimate. This module makes the
difference visible.

Method
------
Resample the **asset** log-returns recovered by the EM inversion, not the equity
returns, because the model's parameters are defined on the asset process.

A *moving block* bootstrap is used rather than an i.i.d. one. Daily returns carry
volatility clustering and mild autocorrelation; resampling single days destroys
both and understates the variance of the volatility estimator. Blocks of `L`
consecutive returns are drawn with replacement from the `n - L + 1` overlapping
blocks and concatenated. The default `L = n^(1/3)` is the standard rate for a
moving-block bootstrap of a mean-like statistic under weak dependence.

What is resampled and what is held fixed
----------------------------------------
Resampled: the asset return path, and therefore `sigma_A` and `eta_A`.

Held fixed: the valuation-date asset value `A_0` and default point `D`. Those are
*observations*, not estimates -- `A_0` comes from inverting the observed market
capitalisation and `D` from a filed balance sheet. Resampling them would be
modelling a different kind of uncertainty (measurement error in the inputs)
which this bootstrap does not claim to capture. The intervals below are
therefore **estimation intervals for the model parameters**, and they are a
lower bound on total uncertainty. That limitation is deliberate and stated.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from . import config
from .conversion import ConversionTables, RatingBasis, sp_rating, ttc_pd
from .measures import DriftRegime, compute

DEFAULT_REPLICATES = 2000
DEFAULT_SEED = 20260726


@dataclass
class BootstrapResult:
    """Empirical distributions from the replicates. Arrays may contain NaN."""

    ticker: str
    n_replicates: int
    block_length: int
    n_observations: int

    sigma_A: np.ndarray
    eta_A: np.ndarray
    drift: np.ndarray
    mu: np.ndarray
    ccm: np.ndarray
    risk_score: np.ndarray
    tic: np.ndarray
    dd: np.ndarray
    edf: np.ndarray
    pit_pd: np.ndarray
    ttc_pd: np.ndarray
    notch: np.ndarray                  # index into the S&P label list
    labels: list[str] = field(default_factory=list)

    # Point estimates from the unresampled data, for reference.
    point_drift: float = float("nan")
    point_drift_se: float = float("nan")

    # Share of replicates in which Prop. 4.4.1 fails.
    defective_fraction: float = float("nan")

    def relative_width(self, name: str, lo: float = 0.05,
                       hi: float = 0.95) -> float:
        """Interval width as a fraction of the quantity's own median.

        Dimensionless, so RiskScore (order 1-10) and PIT PD (order 1e-30) can be
        compared on the same axis.
        """
        q = self.quantiles(name, (lo, 0.5, hi))
        med = q[0.5]
        if not np.isfinite(med) or med == 0:
            return float("nan")
        return float((q[hi] - q[lo]) / abs(med))

    def quantiles(self, name: str, qs=(0.05, 0.5, 0.95)) -> dict:
        arr = getattr(self, name)
        finite = arr[np.isfinite(arr)]
        if finite.size == 0:
            return {q: float("nan") for q in qs}
        return {q: float(np.quantile(finite, q)) for q in qs}

    def notch_interval(self, lo: float = 0.05, hi: float = 0.95
                       ) -> tuple[Optional[str], Optional[str], int]:
        """(best label, worst label, width in notches) over the interval.

        Width counts the labels spanned inclusive, so an interval that resolves
        to a single grade has width 1.
        """
        finite = self.notch[np.isfinite(self.notch)]
        if finite.size == 0 or not self.labels:
            return None, None, 0
        a = int(round(float(np.quantile(finite, lo))))
        b = int(round(float(np.quantile(finite, hi))))
        a, b = max(0, min(a, b)), min(len(self.labels) - 1, max(a, b))
        return self.labels[a], self.labels[b], b - a + 1

    @property
    def t_statistic(self) -> float:
        """Point drift over its standard error."""
        if not np.isfinite(self.point_drift_se) or self.point_drift_se == 0:
            return float("nan")
        return float(self.point_drift / self.point_drift_se)


def block_length_for(n: int) -> int:
    """`n^(1/3)`, floored at 2 -- the standard moving-block rate."""
    return max(2, int(round(n ** (1.0 / 3.0))))


def moving_block_resample(x: np.ndarray, rng: np.random.Generator,
                          block_length: int) -> np.ndarray:
    """One moving-block resample of `x`, same length as `x`."""
    n = x.size
    L = min(block_length, n)
    n_blocks = int(math.ceil(n / L))
    starts = rng.integers(0, n - L + 1, size=n_blocks)
    return np.concatenate([x[s:s + L] for s in starts])[:n]


def run(ticker: str,
        asset_returns: np.ndarray,
        asset_value: float,
        debt: float,
        tables: Optional[ConversionTables] = None,
        *,
        n_replicates: int = DEFAULT_REPLICATES,
        block_length: Optional[int] = None,
        seed: int = DEFAULT_SEED,
        trading_days: int = config.TRADING_DAYS_PER_YEAR,
        vol_window: int = config.EM_WINDOW_DAYS,
        horizon: float = config.HORIZON_YEARS) -> BootstrapResult:
    """Propagate estimation uncertainty through the whole measure chain.

    The two parameters are estimated on **different windows**, exactly as
    `em.estimate` does: `sigma_A` from the trailing `vol_window` observations
    and the drift from the whole span. Each is therefore resampled from its own
    window. A bootstrap that computed both from the full span would report the
    sampling distribution of an estimator the pipeline does not use -- and a
    narrower one, since it would have ~5x the observations for the volatility.

    Consequence worth stating: the two resamples are drawn independently, while
    the real estimators share the trailing year of data and are therefore
    slightly dependent. Each marginal sampling distribution is right; their
    joint dependence is not modelled. For the quantities reported here that
    matters little -- RiskScore depends on sigma alone, and mu and CCM are
    dominated by the drift -- but it is an approximation, not an identity.
    """
    u = np.asarray(asset_returns, dtype=float)
    u = u[np.isfinite(u)]
    n = u.size
    if n < 30:
        raise ValueError(f"{ticker}: too few asset returns to bootstrap ({n})")

    L = block_length or block_length_for(n)
    u_vol = u[-vol_window:] if u.size > vol_window else u
    L_vol = block_length or block_length_for(u_vol.size)
    rng = np.random.default_rng(seed)

    nan = float("nan")
    out = {k: np.full(n_replicates, nan) for k in
           ("sigma_A", "eta_A", "drift", "mu", "ccm", "risk_score", "tic",
            "dd", "edf", "pit_pd", "ttc_pd", "notch")}
    labels = list(tables.sp_labels) if tables is not None else []
    defective = 0

    for i in range(n_replicates):
        # Each parameter is resampled from the window its estimator actually
        # uses. Taking a trailing slice of a full-span resample would NOT work:
        # a moving-block resample draws blocks uniformly from the whole series,
        # so every slice of it is the same regime-mixture, and a company whose
        # recent volatility differs from its five-year volatility would be
        # bootstrapped around the wrong centre.
        sigma = float(np.std(moving_block_resample(u_vol, rng, L_vol), ddof=1)
                      * math.sqrt(trading_days))
        drift = float(np.mean(moving_block_resample(u, rng, L)) * trading_days)
        if not np.isfinite(sigma) or sigma <= 0:
            continue
        eta = drift + 0.5 * sigma ** 2

        out["sigma_A"][i] = sigma
        out["eta_A"][i] = eta
        out["drift"][i] = drift

        try:
            m = compute(sigma, asset_value, debt, eta, horizon=horizon)
        except ValueError:
            continue

        # Recorded for EVERY replicate, because these do not depend on the sign
        # of the drift:
        #   TiC = CCM/mu = sigma_A^2 / ln^2(A/D)  -- the (eta - sigma^2/2) terms
        #   cancel exactly between Eq. (11) and Eq. (12), so RiskScore is a
        #   function of sigma_A and A/D alone (Prop. 4.4.2).
        #   DD and EDF use the signed drift directly and stay defined.
        #
        # Recording them after the DEFECTIVE check would condition their
        # distributions on `drift > 0`. That is not a neutral filter: since
        # drift = eta - sigma^2/2, a larger sigma makes DEFECTIVE more likely,
        # so the surviving replicates would be a sigma-truncated sample and the
        # RiskScore interval would be narrower than the truth. That bug was
        # present in the first version of this module.
        out["risk_score"][i] = m.risk_score
        out["tic"][i] = m.tic
        out["dd"][i] = m.dd
        out["edf"][i] = m.edf

        if m.regime is DriftRegime.DEFECTIVE:
            defective += 1
            continue

        # These genuinely do not exist in a defective regime.
        out["mu"][i] = m.mu
        out["ccm"][i] = m.ccm
        out["pit_pd"][i] = m.pit_pd

        if tables is None:
            continue
        look = ttc_pd(tables, m.ccm, m.mu, pit_pd=m.pit_pd)
        if look.basis in (RatingBasis.OFF_GRID, RatingBasis.NOT_APPLICABLE):
            continue
        if not np.isfinite(look.value):
            continue
        out["ttc_pd"][i] = look.value
        label = sp_rating(tables, look.value)
        if label in labels:
            out["notch"][i] = labels.index(label)

    point_drift = float(np.mean(u) * trading_days)
    point_sigma = float(np.std(u[-vol_window:], ddof=1) * math.sqrt(trading_days))
    span_years = n / float(trading_days)
    point_se = point_sigma / math.sqrt(span_years) if span_years > 0 else nan

    return BootstrapResult(
        ticker=ticker, n_replicates=n_replicates, block_length=L,
        n_observations=n, labels=labels,
        point_drift=point_drift, point_drift_se=point_se,
        defective_fraction=defective / n_replicates,
        **out)
