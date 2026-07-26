"""Tests for TiC / first-passage credit measures against the paper's tables
and hand-computed values."""

from __future__ import annotations

import math

import pytest
from scipy.special import log_ndtr
from scipy.stats import invgauss

from signal_construction import measures


# --- PIT PD (Eq. 13) vs paper Tables 13 (CCM=1.5) and 14 (CCM=5) -------------
@pytest.mark.parametrize("mu, ccm, expected", [
    (1.0, 1.5, 0.6940),
    (5.0, 1.5, 0.1260),
    (10.0, 1.5, 0.0190),
    (1.0, 5.0, 0.7770),
    (5.0, 5.0, 0.3840),
    (10.0, 5.0, 0.1910),
])
def test_pit_pd_matches_paper_tables(mu, ccm, expected):
    assert measures.pit_pd_first_hitting(mu, ccm) == pytest.approx(expected, abs=5e-4)


# --- Composite measures on a clean hand example -----------------------------
def test_compute_hand_values():
    m = measures.compute(sigma_A=0.30, asset=200.0, debt=100.0, eta_A=0.10)

    ln_ad = math.log(2.0)                       # 0.693147
    assert m.ln_A_D == pytest.approx(ln_ad)
    assert m.drift == pytest.approx(0.10 - 0.5 * 0.30 ** 2)   # 0.055

    # TiC = sigma^2 / ln^2(A/D); RiskScore = 100*TiC (eta-independent).
    assert m.tic == pytest.approx(0.09 / ln_ad ** 2)
    assert m.risk_score == pytest.approx(18.7315, abs=1e-3)

    # mu, CCM (Eq. 11) and TiC = CCM/mu consistency.
    assert m.mu == pytest.approx(ln_ad / 0.055, rel=1e-6)
    assert m.ccm == pytest.approx(0.09 / (ln_ad * 0.055), rel=1e-6)
    assert m.tic == pytest.approx(m.ccm / m.mu, rel=1e-9)

    # DD (Eq. 14) and EDF.
    dd = (ln_ad + 0.055) / 0.30
    assert m.dd == pytest.approx(dd, rel=1e-9)
    assert m.edf == pytest.approx(0.00632, abs=1e-4)


def test_tic_is_eta_independent():
    a = measures.compute(0.30, 200.0, 100.0, eta_A=0.10)
    b = measures.compute(0.30, 200.0, 100.0, eta_A=-0.40)
    assert a.tic == pytest.approx(b.tic)            # Q=1 rating ignores drift
    assert a.dd != pytest.approx(b.dd)              # DD does depend on drift


def test_lambda_ccm_relation_matches_agency():
    # Paper Table 6: Aaa CCM=0.57 -> lambda ~ 0.51.
    m = measures.compute(sigma_A=0.20, asset=200.0, debt=100.0, eta_A=0.05)
    assert m.lam == pytest.approx((m.ccm + 1.0) ** -1.5, rel=1e-9)
    assert (0.57 + 1.0) ** -1.5 == pytest.approx(0.508, abs=2e-3)


def test_compute_requires_asset_above_debt():
    with pytest.raises(ValueError):
        measures.compute(0.30, 90.0, 100.0, eta_A=0.10)


# --- Eq. (13) against an independent oracle (#4, #5) ------------------------
# The first-passage time of a GBM to a lower barrier is Inverse Gaussian. With
# our parameterization -- mean `mu`, shape `mu/CCM` -- scipy's two-parameter
# form is invgauss(mu=CCM, scale=mu/CCM), since scipy's mean is `mu*scale` and
# its shape is `scale`. That gives a completely independent implementation of
# Eq. (13) to test against.
@pytest.mark.parametrize("ccm", [1e-3, 1e-2, 0.1, 0.5, 1.0, 1.5, 5.0, 50.0, 1e3])
@pytest.mark.parametrize("mu", [0.5, 1.0, 1.05, 2.0, 10.0, 160.0, 1e3, 1e4])
def test_pit_pd_matches_scipy_invgauss(ccm, mu):
    ours = measures.pit_pd_first_hitting(mu, ccm, horizon=1.0)
    theirs = float(invgauss.cdf(1.0, mu=ccm, scale=mu / ccm))
    assert math.isfinite(ours)
    assert 0.0 <= ours <= 1.0
    # Absolute tolerance carries the deep tail where both underflow; the
    # relative check binds wherever the value is actually resolvable.
    assert ours == pytest.approx(theirs, rel=1e-6, abs=1e-12)


def test_pit_pd_does_not_lose_the_second_term_at_small_ccm():
    """The old linear-space code hit OverflowError here and returned term1 only.

    At mu = horizon the two exponents cancel exactly, so the second term is
    O(1) and dropping it understates the PD. These values come from the
    log-space reference and are ~0.9pp above what the old fallback produced.
    """
    assert measures.pit_pd_first_hitting(1.0, 0.002) == pytest.approx(0.5089162, abs=1e-6)
    assert measures.pit_pd_first_hitting(1.0, 0.001) == pytest.approx(0.5063063, abs=1e-6)
    # The dropped term is what separates these from a flat 0.5.
    for ccm in (0.002, 0.001, 5e-4):
        assert measures.pit_pd_first_hitting(1.0, ccm) > 0.5


def test_edf_resolves_past_the_linear_space_underflow_cliff():
    """`norm.cdf(-dd)` returns exactly 0.0 from dd ~ 37.6; log space does not.

    The recovered band is narrow -- roughly dd in [37.6, 38.4], where the true
    value is a float64 subnormal. Past ~38.4 the value is below the smallest
    subnormal and *any* linear representation is zero, log space included.
    Widening that further means carrying log-PD end to end rather than
    exponentiating at the boundary; that is a larger change and is not done
    here. What this test pins is that we no longer throw the band away.
    """
    from scipy.stats import norm

    # sigma 0.05, ln(A/D) ~ 1.891, drift 0.00875  ->  DD ~ 38.0
    m = measures.compute(sigma_A=0.05, asset=6.628, debt=1.0, eta_A=0.01)
    assert 37.6 < m.dd < 38.4, f"test needs DD in the recoverable band, got {m.dd}"
    assert norm.cdf(-m.dd) == 0.0, "premise: linear space underflows here"
    assert m.edf > 0.0, "EDF underflowed to exactly zero in log space too"
    assert m.edf == pytest.approx(math.exp(log_ndtr(-m.dd)), rel=1e-9)
