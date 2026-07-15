"""Tests for TiC / first-passage credit measures against the paper's tables
and hand-computed values."""

from __future__ import annotations

import math

import pytest

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
