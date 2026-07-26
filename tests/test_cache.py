"""Acquisition cache: round-trips, switches, and batch isolation (offline)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from raw_data_architecture import cache


@pytest.fixture()
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("MDT_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("MDT_CACHE_OFF", raising=False)
    monkeypatch.delenv("MDT_CACHE_REFRESH", raising=False)
    return tmp_path


def test_info_round_trip(tmp_cache):
    info = {"longName": "Test Co", "sector": "Technology", "marketCap": 1.5e9}
    cache.save_info("TST", info)
    assert cache.load_info("TST") == info
    assert cache.load_info("OTHER") is None


def test_prices_round_trip_preserves_tz_aware_index(tmp_cache):
    """The vendor returns a tz-aware index; the cache must not quietly drop it."""
    idx = pd.date_range("2026-01-02", periods=5, freq="B",
                        tz="America/New_York")
    prices = pd.DataFrame({"Close": np.linspace(10, 11, 5),
                           "Dividends": [0.0, 0.0, 0.5, 0.0, 0.0]}, index=idx)
    cache.save_prices("TST", prices)
    back = cache.load_prices("TST")
    assert back.index.tz is not None
    # check_freq=False: parquet does not persist the index freq attribute,
    # which real vendor data never carries anyway.
    pd.testing.assert_frame_equal(back, prices, check_freq=False)


def test_statements_round_trip_restores_timestamp_columns(tmp_cache):
    """Statement columns are period-end dates; parquet stores them as strings."""
    bal = pd.DataFrame({pd.Timestamp("2026-03-31"): {"Total Debt": 400e6},
                        pd.Timestamp("2025-12-31"): {"Total Debt": 380e6}})
    cache.save_statements("TST", {"q_balance": bal})
    back = cache.load_statements("TST")
    assert all(isinstance(c, pd.Timestamp) for c in back["q_balance"].columns)
    pd.testing.assert_frame_equal(back["q_balance"], bal)
    # Absent statements come back as empty frames, present ones as data.
    assert back["a_income"].empty


def test_rates_round_trip(tmp_cache):
    rates = pd.DataFrame({"Date": pd.date_range("2026-01-01", periods=3),
                          "DGS1": [0.041, 0.0415, 0.042]})
    cache.save_rates(rates)
    pd.testing.assert_frame_equal(cache.load_rates(), rates)


def test_cache_off_bypasses_everything(tmp_cache, monkeypatch):
    monkeypatch.setenv("MDT_CACHE_OFF", "1")
    cache.save_info("TST", {"a": 1})
    monkeypatch.delenv("MDT_CACHE_OFF")
    assert cache.load_info("TST") is None, "nothing must be written while off"


def test_refresh_ignores_existing_entries(tmp_cache, monkeypatch):
    cache.save_info("TST", {"a": 1})
    monkeypatch.setenv("MDT_CACHE_REFRESH", "1")
    assert cache.load_info("TST") is None


def test_batch_isolation_one_raising_company_cannot_abort_the_run(monkeypatch):
    """run() must return the survivors and record the raiser, never propagate."""
    from data_cleaning import workflow
    from data_cleaning.company import CompanyData

    def fake_fetch(ticker, cfg, rates):
        if ticker == "BAD":
            raise RuntimeError("boom")
        return CompanyData(ticker=ticker, name=ticker)

    monkeypatch.setattr(workflow, "fetch_company", fake_fetch)
    from dashboard import excel, longtable, submission
    monkeypatch.setattr(excel, "write_company_workbook", lambda *a, **k: None)
    monkeypatch.setattr(excel, "write_master_workbook", lambda *a, **k: None)
    monkeypatch.setattr(longtable, "write_long_table", lambda *a, **k: None)
    monkeypatch.setattr(longtable, "build_long_table", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(submission, "write_submission", lambda *a, **k: "x")

    for workers in (1, 4):
        cfg = workflow.RunConfig(tickers=["GOOD1", "BAD", "GOOD2"],
                                 include_rates=False, workers=workers)
        out = workflow.run(cfg)
        assert sorted(c.ticker for c in out) == ["GOOD1", "GOOD2"], \
            f"workers={workers}"
