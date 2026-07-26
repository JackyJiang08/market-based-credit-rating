"""Property tests over the numerics (hypothesis).

The algebraic identities are free test oracles: TiC = CCM/mu =
sigma^2/ln^2(A/D) is provable on paper, so any implementation violating it
is wrong without needing a reference dataset (the bootstrap bug episode in
docs/UNCERTAINTY.md is why this file exists).
"""

from __future__ import annotations

import math

import pytest
from creditrating.model import conversion
from creditrating.model import tic as measures
from hypothesis import given, settings
from hypothesis import strategies as st

# Valid first-passage inputs: A strictly above D, positive drift regime.
sigmas = st.floats(min_value=0.05, max_value=1.5)
ratios = st.floats(min_value=1.02, max_value=50.0)  # A/D
etas = st.floats(min_value=-0.5, max_value=1.0)


@settings(max_examples=200, deadline=None)
@given(sigma=sigmas, ratio=ratios, eta=etas)
def test_tic_identity_and_probability_bounds(sigma, ratio, eta):
    d = 1.0e10
    m = measures.compute(sigma, ratio * d, d, eta)

    tic_direct = sigma**2 / math.log(ratio) ** 2
    assert m.tic == pytest.approx(tic_direct, rel=1e-9)
    assert m.risk_score == pytest.approx(100.0 * m.tic, rel=1e-12)

    assert 0.0 <= m.edf <= 1.0

    if m.regime is measures.DriftRegime.VALID:
        assert 0.0 <= m.pit_pd <= 1.0
        # The identity the bootstrap bug hid behind: TiC == CCM / mu.
        assert m.tic == pytest.approx(m.ccm / m.mu, rel=1e-6)
        assert m.mu > 0 and m.ccm > 0
    else:
        # Defective regime reports NaN for the first-passage chain, never a
        # substituted magnitude (Prop. 4.4.1; engineering rule 2).
        assert m.mu != m.mu and m.ccm != m.ccm and m.pit_pd != m.pit_pd


@settings(max_examples=200, deadline=None)
@given(ccm=st.floats(min_value=0.01, max_value=500.0))
def test_alpha_first_hitting_is_a_probability(ccm):
    a = conversion.alpha_first_hitting(ccm)
    assert 0.0 < a <= 1.0


@settings(max_examples=100, deadline=None)
@given(
    lo=st.floats(min_value=0.01, max_value=400.0),
    bump=st.floats(min_value=1e-3, max_value=100.0),
)
def test_alpha_first_hitting_is_monotone_decreasing(lo, bump):
    assert conversion.alpha_first_hitting(lo) >= conversion.alpha_first_hitting(lo + bump)


@settings(max_examples=100, deadline=None)
@given(sigma=sigmas, ratio=ratios, eta=etas, scale=st.floats(min_value=1e-4, max_value=1e4))
def test_tic_is_scale_invariant(sigma, ratio, eta, scale):
    """RiskScore depends on A/D only -- currency units must cancel."""
    d = 1.0e10
    a = measures.compute(sigma, ratio * d, d, eta)
    b = measures.compute(sigma, ratio * d * scale, d * scale, eta)
    assert a.risk_score == pytest.approx(b.risk_score, rel=1e-9)
