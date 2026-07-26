"""EM estimation tests: recover a known sigma_A from a synthetic asset path,
and enforce the A > D / A > E invariants. Offline (no network)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from signal_construction import em


def _simulate_equity(sigma_true=0.25, eta=0.08, D=100.0, r=0.04,
                     A0=200.0, n=252, seed=7):
    """Simulate a GBM asset path and map it to equity via the exact BS call."""
    rng = np.random.default_rng(seed)
    dt = 1.0 / 250.0
    z = rng.standard_normal(n)
    log_ret = (eta - 0.5 * sigma_true ** 2) * dt + sigma_true * np.sqrt(dt) * z
    A = np.exp(np.log(A0) + np.cumsum(log_ret))
    idx = pd.bdate_range("2023-01-02", periods=n)
    D_arr = np.full(n, D)
    r_arr = np.full(n, r)
    E = em._bs_equity(A, D_arr, r_arr, sigma_true, 1.0)
    return pd.Series(E, idx), pd.Series(D_arr, idx), pd.Series(r_arr, idx), A


def test_em_recovers_true_sigma():
    E, D, R, _ = _simulate_equity(sigma_true=0.25)
    res = em.estimate(E, D, R)

    assert res.converged
    assert res.n_iter <= 20                       # typically converges in ~10
    assert abs(res.sigma_A - 0.25) < 0.03         # recovered within sampling noise
    # Structural invariants.
    assert res.asset_last > res.debt_last
    assert res.asset_last > res.equity_last
    assert len(res.asset_values) == len(E)


def test_em_recovers_higher_sigma():
    E, D, R, _ = _simulate_equity(sigma_true=0.45, seed=11)
    res = em.estimate(E, D, R)
    assert abs(res.sigma_A - 0.45) < 0.04


def test_em_short_input_raises():
    E, D, R, _ = _simulate_equity(n=20)
    with pytest.raises(em.EMError):
        em.estimate(E, D, R)


def test_em_asset_exceeds_debt_everywhere():
    E, D, R, _ = _simulate_equity()
    res = em.estimate(E, D, R)
    assert (res.asset_values.to_numpy() > D.iloc[0]).all()


# --- Bracket expansion must fail loudly, never bisect a rootless interval ----
def test_inversion_raises_when_the_root_cannot_be_bracketed(monkeypatch):
    """A `g` that never reaches E must raise, not return a bisection midpoint.

    The loop previously fell through after its doublings and bisected an
    interval known not to contain the root, producing a confident wrong asset
    value with no error anywhere.
    """
    import numpy as np

    from signal_construction import em as em_mod

    # g(A) = 0 for all A, so g(hi) < E can never be satisfied.
    monkeypatch.setattr(em_mod, "_bs_equity",
                        lambda A, D, r, sigma, T: np.zeros_like(np.asarray(A, dtype=float)))
    with pytest.raises(em_mod.EMError, match="failed to bracket"):
        em_mod._invert_assets(np.array([100.0, 200.0]), np.array([50.0, 50.0]),
                              np.array([0.04, 0.04]), 0.3, 1.0)


def test_bracket_failure_message_counts_the_offending_days(monkeypatch):
    import numpy as np

    from signal_construction import em as em_mod

    monkeypatch.setattr(em_mod, "_bs_equity",
                        lambda A, D, r, sigma, T: np.zeros_like(np.asarray(A, dtype=float)))
    with pytest.raises(em_mod.EMError) as exc:
        em_mod._invert_assets(np.array([1.0, 2.0, 3.0]), np.array([1.0, 1.0, 1.0]),
                              np.array([0.0, 0.0, 0.0]), 0.3, 1.0)
    assert "3 of 3 day(s)" in str(exc.value)
