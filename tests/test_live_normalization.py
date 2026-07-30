"""The LIVE acquisition path must emit canonical [ns] datetimes.

Regression for the 2026-07-29 live-refresh failure: fresh vendor frames
arrived as datetime64[s] (prices) and datetime64[us] (to_datetime under
pandas 3), and the as-of join refused to merge them. The cache READ path
already normalized; the live path did not. `cache.normalize_datetimes` is
the shared public chokepoint for both.
"""

from __future__ import annotations

import pandas as pd
import pytest
from creditrating.data import cache


def _frame(unit: str) -> pd.DataFrame:
    idx = pd.DatetimeIndex(pd.to_datetime(["2026-07-24", "2026-07-27"])).as_unit(unit)
    df = pd.DataFrame({"Close": [1.0, 2.0]}, index=idx)
    df["Date"] = df.index
    df["Date"] = df["Date"].dt.as_unit(unit)
    return df


@pytest.mark.parametrize("unit", ["s", "ms", "us", "ns"])
def test_every_vendor_unit_normalizes_to_ns(unit):
    out = cache.normalize_datetimes(_frame(unit))
    assert str(out.index.dtype) == "datetime64[ns]"
    assert str(out["Date"].dtype) == "datetime64[ns]"


def test_dict_of_statements_normalizes_each_frame():
    stmts = {"q_balance": _frame("s"), "a_balance": _frame("us"), "meta": None}
    out = cache.normalize_datetimes(stmts)
    assert str(out["q_balance"].index.dtype) == "datetime64[ns]"
    assert str(out["a_balance"]["Date"].dtype) == "datetime64[ns]"
    assert out["meta"] is None


def test_mixed_unit_frames_as_of_join_after_normalization():
    left = cache.normalize_datetimes(_frame("s"))[["Date", "Close"]]
    right = cache.normalize_datetimes(_frame("us"))[["Date"]].assign(r=0.04)
    merged = pd.merge_asof(left.sort_values("Date"), right.sort_values("Date"), on="Date")
    assert len(merged) == 2 and merged["r"].notna().all()


def test_passthrough_for_non_frames():
    assert cache.normalize_datetimes(None) is None
    assert cache.normalize_datetimes({"a": 1}) == {"a": 1}
