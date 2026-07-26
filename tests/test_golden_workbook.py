"""Golden file for the workbook: the COST fixture's Asset row, pinned.

Column-aware on purpose: the grid-dependent columns (TTC PD, the letter, and
everything downstream of the licensed conversion workbook) exist only where
``local/`` is present. Where it is present they are asserted against the
golden file; where it is absent they are asserted to be NaN -- the pipeline's
documented no-workbook behavior. Both paths are real assertions; neither is
a silent skip. The absent path is ALSO tested explicitly everywhere via a
monkeypatched loader, so a machine with local/ still exercises it.

Regenerate deliberately (see tests/golden/README.md); the MANIFEST records
which environment produced the golden file.
"""

from __future__ import annotations

import math
import os

import pandas as pd
import pytest
from creditrating.data import cache
from creditrating.data.pipeline import RunConfig, fetch_company
from creditrating.io import records
from creditrating.model import conversion

GOLDEN = os.path.join(os.path.dirname(__file__), "golden", "cost_asset_row.csv")
HAS_FIXTURE = os.path.exists(os.path.join(cache.cache_dir(), "COST", "prices.parquet"))
HAS_WORKBOOK = os.path.exists(conversion.DEFAULT_XLSX)

# Everything downstream of the licensed conversion workbook.
GRID_COLUMNS = {
    "TTC PD",
    "SP Rating",
    "Outlook",
    "Rating Basis",
    "Rating Determination",
    "Rating Interval Low",
    "Rating Interval High",
    "Rating Interval Notches",
}


def _cost_row():
    c = fetch_company("COST", RunConfig(tickers=["COST"]), cache.load_rates())
    return records.asset_frame([c]).iloc[0]


def _assert_equal(col, got, want):
    if isinstance(want, float) and not isinstance(got, str):
        got = float("nan") if got is None else float(got)
        if math.isnan(want):
            assert got != got, f"{col}: expected NaN, got {got}"
        else:
            assert got == pytest.approx(want, rel=1e-9), f"{col}: {got} != {want}"
    else:
        assert str(got) == str(want), f"{col}: {got!r} != {want!r}"


def _assert_absent(col, got):
    """The documented no-workbook value: NaN/None (0 for the notch count)."""
    if col == "Rating Interval Notches":
        assert got in (0,) or got != got, f"{col}: expected 0/NaN, got {got!r}"
    else:
        assert (
            got is None or got != got or (isinstance(got, float) and math.isnan(got))
        ), f"{col}: expected NaN without the workbook, got {got!r}"


@pytest.mark.skipif(not HAS_FIXTURE, reason="cache fixtures not present")
def test_core_columns_match_the_golden_file_in_every_environment():
    got = _cost_row()
    want = pd.read_csv(GOLDEN).iloc[0]
    for col in records.ASSET_SCHEMA:
        if col not in GRID_COLUMNS:
            _assert_equal(col, got[col], want[col])


@pytest.mark.skipif(not HAS_FIXTURE, reason="cache fixtures not present")
def test_grid_columns_golden_when_workbook_present_nan_when_absent():
    """One test, two real branches -- the environment picks which, and both
    assert; a machine without local/ verifies the documented NaN contract."""
    got = _cost_row()
    if HAS_WORKBOOK:
        want = pd.read_csv(GOLDEN).iloc[0]
        for col in GRID_COLUMNS:
            _assert_equal(col, got[col], want[col])
    else:
        for col in GRID_COLUMNS:
            _assert_absent(col, got[col])


@pytest.mark.skipif(not HAS_FIXTURE, reason="cache fixtures not present")
def test_grid_columns_are_nan_when_the_workbook_is_absent(monkeypatch):
    """The absent path, exercised on EVERY machine via a failing loader."""

    def _no_workbook(*a, **k):
        raise FileNotFoundError("simulated absent local/ workbook")

    monkeypatch.setattr(conversion, "load_tables", _no_workbook)
    got = _cost_row()
    for col in GRID_COLUMNS:
        _assert_absent(col, got[col])
    # Core measures are untouched by the workbook's absence.
    assert float(got["sigma"]) > 0 and float(got["TiC Risk Score"]) > 0
