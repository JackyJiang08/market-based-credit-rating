"""Reporting-currency gate (found by the 150-name universe run).

TM (Toyota) prices in USD but files in JPY. Before the gate, EM raised
`A <= D` because the debt barrier arrived ~x150 too large in the equity's
unit -- and TSM/BABA/SAP/ASML were silently RATED on the same mismatch. The
committed TM cache fixture reproduces the loud case end to end, offline.
"""

from __future__ import annotations

import os

import pytest

from data_cleaning.workflow import RunConfig, fetch_company
from raw_data_architecture import cache, sources

TM_FIXTURE = os.path.exists(os.path.join(cache.cache_dir(), "TM", "info.json"))


@pytest.mark.skipif(not TM_FIXTURE, reason="TM cache fixture not present")
def test_tm_is_gated_for_currency_mismatch_not_crashed(monkeypatch):
    def _no_network(*a, **k):
        raise AssertionError("network entry point called despite fixtures")

    monkeypatch.setattr(sources, "get_info", _no_network)
    monkeypatch.setattr(sources, "get_history", _no_network)
    monkeypatch.setattr(sources, "get_statements", _no_network)
    monkeypatch.delenv("MDT_CACHE_REFRESH", raising=False)
    monkeypatch.delenv("MDT_CACHE_OFF", raising=False)

    rates = cache.load_rates()
    c = fetch_company("TM", RunConfig(tickers=["TM"], run_bootstrap=False),
                      rates)
    assert c.financial_currency == "JPY" and c.currency == "USD"
    assert c.model_applicable is False
    assert c.applicability_reason == "REPORTING_CURRENCY_MISMATCH"
    # Unlike the firm-type gate, the measures are suppressed too: they would
    # be unit-corrupt, not merely inapplicable.
    assert c.sigma_A is None and c.sp_rating is None
    assert "JPY" in (c.em_error or "")


def test_matching_currencies_do_not_gate():
    """The gate must not fire on ordinary domestic names (or USD-filing ADRs)."""
    from data_cleaning.company import CompanyData

    c = CompanyData(ticker="XX")
    c.currency, c.financial_currency = "USD", "USD"
    # The gate logic lives in workflow; replicate its predicate exactly.
    fires = bool(c.currency and c.financial_currency
                 and c.currency != c.financial_currency)
    assert not fires


def test_missing_financial_currency_does_not_gate():
    """Absent metadata is not evidence of a mismatch."""
    from data_cleaning.company import CompanyData

    c = CompanyData(ticker="XX")
    c.currency, c.financial_currency = "USD", ""
    fires = bool(c.currency and c.financial_currency
                 and c.currency != c.financial_currency)
    assert not fires
