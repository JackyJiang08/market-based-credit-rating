"""Duan-style EM estimation of unobserved asset value and volatility (KMV).

Equity is a call option on the firm's assets (Merton), so the observed daily
equity series ``E_t`` is a deterministic, monotone transform of the latent asset
value ``A_t`` once the asset volatility ``sigma_A`` is fixed. We recover
``(A_t, sigma_A, eta_A)`` by Expectation-Maximization:

  E-step:  given ``sigma_A``, invert ``E_t = g(A_t)`` for ``A_t`` on every
           trading day. ``g`` is the Black-Scholes call value, strictly
           increasing in ``A`` -> solved by bisection (deck slides 63-64).
  M-step:  recompute ``sigma_A`` from the asset log-returns and estimate the
           real-world asset drift ``eta_A`` simultaneously (deck slide 56).

Iterate until ``sigma_A`` converges.

References: asset GBM ``A_t = A_0 exp((eta_A - sigma_A^2/2) t + sigma_A W_t)``
(paper Eq. 10); DD/EDF (paper Eq. 14); deck "KMV Rating Method" slides 52-68.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.stats import norm

from . import config

LOG = logging.getLogger("pfpa.em")


class EMError(RuntimeError):
    """Raised when the EM estimation cannot produce a valid, converged result."""


@dataclass
class EMResult:
    sigma_A: float                 # annualized asset volatility (vol window)
    eta_A: float                   # annualized real-world asset return (drift window)
    drift: float                   # eta_A - sigma_A^2/2  (= mean annual log-return)
    drift_se: float                # SE of the drift estimate = sigma_A/sqrt(years)
    drift_span_years: float        # calendar span the drift was estimated over
    asset_last: float              # A on the last trading day (A_0 for the model)
    debt_last: float               # default-point debt D on the last trading day
    equity_last: float             # equity E on the last trading day
    asset_values: pd.Series        # full inverted asset path A_t
    n_iter: int
    converged: bool
    warnings: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Black-Scholes equity value g(A) and its bisection inverse
# --------------------------------------------------------------------------- #
def _bs_equity(A: np.ndarray, D: np.ndarray, r: np.ndarray,
               sigma: float, T: float) -> np.ndarray:
    """g(A): Black-Scholes value of equity as a call on assets A struck at D."""
    A = np.asarray(A, dtype=float)
    sqrtT = np.sqrt(T)
    with np.errstate(divide="ignore", invalid="ignore"):
        d1 = (np.log(A / D) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrtT)
        d2 = d1 - sigma * sqrtT
        val = A * norm.cdf(d1) - D * np.exp(-r * T) * norm.cdf(d2)
    # Intrinsic-value floor guards the degenerate sigma*sqrtT -> 0 corner.
    return np.where(np.isfinite(val), val, np.maximum(A - D * np.exp(-r * T), 0.0))


def _invert_assets(E: np.ndarray, D: np.ndarray, r: np.ndarray,
                   sigma: float, T: float,
                   n_bisect: int = config.BISECTION_STEPS) -> np.ndarray:
    """Vectorized bisection: solve g(A) = E for A on every day at once.

    g is increasing in A and g(A) < A, so A lies in (E, hi]; expand hi until it
    brackets the root, then bisect.
    """
    E = np.asarray(E, dtype=float)
    lo = E.copy()                                  # g(E) < E  =>  f(lo) < 0
    hi = E + D * np.exp(-r * T) + 1.0
    for _ in range(config.BRACKET_MAX_DOUBLINGS):  # grow hi until g(hi) >= E
        need = _bs_equity(hi, D, r, sigma, T) < E
        if not need.any():
            break
        hi = np.where(need, hi * 2.0, hi)
    else:
        # The loop finished without bracketing the root on every day. Bisecting
        # an interval that does not contain the solution returns a confident
        # wrong asset value, so fail instead.
        unbracketed = int(np.count_nonzero(_bs_equity(hi, D, r, sigma, T) < E))
        raise EMError(
            f"asset inversion failed to bracket the root on {unbracketed} of "
            f"{E.size} day(s) after {config.BRACKET_MAX_DOUBLINGS} doublings "
            f"(sigma={sigma:.4f}). Refusing to bisect an interval with no root.")
    for _ in range(n_bisect):
        mid = 0.5 * (lo + hi)
        val = _bs_equity(mid, D, r, sigma, T)
        lo = np.where(val < E, mid, lo)
        hi = np.where(val >= E, mid, hi)
    return 0.5 * (lo + hi)


# --------------------------------------------------------------------------- #
# EM driver
# --------------------------------------------------------------------------- #
def estimate(equity: pd.Series, debt: pd.Series, rate: pd.Series,
             *, horizon: float = config.HORIZON_YEARS,
             trading_days: int = config.TRADING_DAYS_PER_YEAR,
             max_iter: int = config.EM_MAX_ITER,
             tol: float = config.EM_TOL,
             vol_window: int = config.EM_WINDOW_DAYS) -> EMResult:
    """Estimate (sigma_A, eta_A, asset path) from a daily equity/debt/rate series.

    Inputs are aligned daily series. Pass the **full drift window** (see
    ``config.DRIFT_WINDOW_DAYS``); the volatility is estimated on its trailing
    ``vol_window`` rows and the drift on the whole span:

      - ``sigma_A``  EM over the trailing ``vol_window`` days. Volatility is a
        high-frequency quantity; a longer span would blend distinct volatility
        regimes into one number.
      - ``eta_A``    mean asset log-return over the **entire** input span,
        inverted with the converged ``sigma_A``. The standard error of a drift
        estimate scales with the calendar span, not the sampling frequency, so
        this is the only term that benefits from more history.

    Passing a series no longer than ``vol_window`` reproduces the previous
    single-window behaviour exactly. Rows with a non-positive or missing
    equity/debt/rate are dropped before estimation.
    """
    df = pd.DataFrame({"E": equity, "D": debt, "r": rate}).dropna()
    df = df[(df["E"] > 0) & (df["D"] > 0)]
    if len(df) < config.MIN_OBSERVATIONS:
        raise EMError(f"insufficient clean observations ({len(df)}) for EM.")

    # Volatility is estimated on the trailing window; the drift on everything.
    vol_df = df.tail(vol_window)
    if len(vol_df) < config.MIN_OBSERVATIONS:
        raise EMError(
            f"insufficient clean observations ({len(vol_df)}) in the volatility "
            f"window for EM.")

    E = vol_df["E"].to_numpy(float)
    D = vol_df["D"].to_numpy(float)
    r = vol_df["r"].to_numpy(float)

    # Initialize sigma_A from the equity return volatility, delevered roughly.
    eq_ret = np.diff(np.log(E))
    sigma = float(np.nanstd(eq_ret, ddof=1) * np.sqrt(trading_days))
    if not np.isfinite(sigma) or sigma <= 0:
        sigma = 0.3
    sigma *= E[-1] / (E[-1] + D[-1])               # asset vol < equity vol
    sigma = float(np.clip(sigma, 0.02, 2.0))

    converged, n_iter = False, max_iter
    for it in range(1, max_iter + 1):
        A = _invert_assets(E, D, r, sigma, horizon)
        u = np.diff(np.log(A))
        sigma_new = float(np.std(u, ddof=1) * np.sqrt(trading_days))
        if not np.isfinite(sigma_new) or sigma_new <= 0:
            raise EMError(f"non-finite sigma at iteration {it}.")
        if abs(sigma_new - sigma) < tol:
            sigma, converged, n_iter = sigma_new, True, it
            break
        sigma = sigma_new

    if not converged:
        raise EMError(
            f"EM did not converge within {max_iter} iterations "
            f"(last sigma={sigma:.4f}). Data may be too short/illiquid.")

    # Final asset path over the FULL span, inverted with the converged sigma.
    # The drift is the mean log-return of that longer path; sigma stays the
    # trailing-window estimate.
    A = _invert_assets(df["E"].to_numpy(float), df["D"].to_numpy(float),
                       df["r"].to_numpy(float), sigma, horizon)
    u = np.diff(np.log(A))
    drift = float(np.mean(u) * trading_days)        # = eta_A - sigma^2/2
    eta_A = drift + 0.5 * sigma ** 2

    # Standard error of the drift estimate: sigma_A / sqrt(span in years).
    # Reported so a caller can see when eta is indistinguishable from zero.
    span_years = max(len(u), 1) / float(trading_days)
    drift_se = float(sigma / math.sqrt(span_years)) if span_years > 0 else float("inf")

    result = EMResult(
        sigma_A=sigma, eta_A=eta_A, drift=drift, drift_se=drift_se,
        drift_span_years=span_years,
        asset_last=float(A[-1]), debt_last=float(df["D"].to_numpy(float)[-1]),
        equity_last=float(df["E"].to_numpy(float)[-1]),
        asset_values=pd.Series(A, index=df.index, name="AssetValue"),
        n_iter=n_iter, converged=True,
    )
    _sanity_checks(result)
    return result


def _sanity_checks(res: EMResult) -> None:
    """Assert hard invariants; log soft warnings. Never silently pass."""
    # Hard invariant: assets must exceed the default point and the equity value.
    if not (res.asset_last > res.debt_last):
        raise EMError(f"A ({res.asset_last:.3g}) <= D ({res.debt_last:.3g}); "
                      "the inversion is wrong.")
    if not (res.asset_last > res.equity_last):
        raise EMError(f"A ({res.asset_last:.3g}) <= E ({res.equity_last:.3g}); "
                      "assets must exceed equity.")
    # Soft warnings.
    if not (config.SIGMA_A_WARN_LOW <= res.sigma_A <= config.SIGMA_A_WARN_HIGH):
        msg = (f"sigma_A={res.sigma_A:.1%} outside typical "
               f"[{config.SIGMA_A_WARN_LOW:.0%}, {config.SIGMA_A_WARN_HIGH:.0%}]")
        res.warnings.append(msg)
        LOG.warning("  %s", msg)
    if res.n_iter > 10:
        res.warnings.append(f"slow convergence ({res.n_iter} iters)")
