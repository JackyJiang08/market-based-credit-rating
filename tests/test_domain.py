"""Domain models: the invariants as code (pydantic v2)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from creditrating.domain import (AssetEstimates, CompanyInputs, RatingResult,
                                 RiskMeasures)


def _est(**kw):
    base = dict(ticker="TST", asset_value=2.0e11, default_point=3.0e10,
                sigma_a=0.25, eta_a=0.08, em_iterations=3, em_converged=True)
    base.update(kw)
    return AssetEstimates(**base)


def test_asset_estimates_accept_a_healthy_company():
    assert _est().sigma_a == 0.25


def test_a_must_strictly_exceed_d():
    with pytest.raises(ValidationError, match="precondition"):
        _est(asset_value=1.0e10, default_point=3.0e10)


@pytest.mark.parametrize("sigma", [0.0, -0.1, 3.0, 5.0])
def test_sigma_bounds_are_enforced(sigma):
    with pytest.raises(ValidationError):
        _est(sigma_a=sigma)


def test_em_iteration_cap_is_the_config_cap():
    with pytest.raises(ValidationError):
        _est(em_iterations=21)


@pytest.mark.parametrize("field", ["edf", "pit_pd", "ttc_pd"])
@pytest.mark.parametrize("bad", [-0.01, 1.01])
def test_probabilities_stay_in_the_unit_interval(field, bad):
    kw = dict(ticker="TST", risk_score=1.0, dd=5.0, edf=0.0, pit_pd=0.0)
    kw[field] = bad
    with pytest.raises(ValidationError):
        RiskMeasures(**kw)


def test_a_letter_never_appears_bare():
    with pytest.raises(ValidationError, match="bare letter"):
        RatingResult(ticker="TST", letter="AAA")
    ok = RatingResult(ticker="TST", letter="AAA", basis="ANALYTICAL",
                      determination="PINNED_AT_SCALE_TOP")
    assert ok.letter == "AAA"


def test_no_letter_needs_no_basis():
    assert RatingResult(ticker="TST").letter is None


def test_company_inputs_reject_nonpositive_equity():
    with pytest.raises(ValidationError):
        CompanyInputs(ticker="TST", equity_value=0.0, default_point=1.0,
                      risk_free_rate=0.04, prices_observations=100)


def test_checks_flag_nothing_on_the_offline_fixture():
    """The committed COST fixture must satisfy every domain invariant."""
    import os

    from creditrating.data import cache
    from creditrating.data.pipeline import RunConfig, fetch_company
    from creditrating.diagnostics import checks

    if not os.path.exists(os.path.join(cache.cache_dir(), "COST", "prices.parquet")):
        pytest.skip("fixtures absent")
    rates = cache.load_rates()
    c = fetch_company("COST", RunConfig(tickers=["COST"], run_bootstrap=False), rates)
    assert checks.check_company(c) == []
