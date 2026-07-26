"""The committed cache fixtures make the pipeline runnable with no network.

The fixture subset (the original 10-name universe + the FRED rates frame)
lives under data/cache/ and is committed. This test proves the promise: a
fresh clone can fetch, align, and estimate COST end to end while every
network entry point raises.
"""

from __future__ import annotations

import os

import pytest
from creditrating.data import cache
from creditrating.data import providers as sources
from creditrating.data.pipeline import RunConfig, fetch_company

FIXTURE_PRESENT = os.path.exists(os.path.join(cache.cache_dir(), "COST", "prices.parquet"))


@pytest.mark.skipif(not FIXTURE_PRESENT, reason="cache fixtures not present")
def test_cost_runs_end_to_end_from_fixtures_with_no_network(monkeypatch):
    def _no_network(*a, **k):
        raise AssertionError("network entry point called despite fixtures")

    monkeypatch.setattr(sources, "get_info", _no_network)
    monkeypatch.setattr(sources, "get_history", _no_network)
    monkeypatch.setattr(sources, "get_statements", _no_network)
    monkeypatch.setattr(sources, "fetch_rates", _no_network)
    monkeypatch.delenv("MDT_CACHE_REFRESH", raising=False)
    monkeypatch.delenv("MDT_CACHE_OFF", raising=False)

    rates = cache.load_rates()
    assert rates is not None and not rates.empty

    c = fetch_company("COST", RunConfig(tickers=["COST"], run_bootstrap=False), rates)
    assert c is not None
    assert c.data_status == "OK"
    assert not c.panel.empty
    assert c.sigma_A is not None and 0.05 < c.sigma_A < 0.80
    assert c.risk_score is not None
