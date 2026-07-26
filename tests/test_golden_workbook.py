"""Golden file for the workbook: the COST fixture's Asset row, pinned.

Deterministic on purpose: the committed cache fixture fixes the data, the EM
is deterministic, and the bootstrap is seeded. Any numeric drift here means
the model changed, not the data -- which is exactly what a golden file is for.
Regenerate deliberately (and say why in the commit) with:

    python -c "..."  # see tests/golden/README
"""

from __future__ import annotations

import math
import os

import pandas as pd
import pytest
from creditrating.data import cache
from creditrating.data.pipeline import RunConfig, fetch_company
from creditrating.io import records

GOLDEN = os.path.join(os.path.dirname(__file__), "golden", "cost_asset_row.csv")


@pytest.mark.skipif(
    not os.path.exists(os.path.join(cache.cache_dir(), "COST", "prices.parquet")),
    reason="fixtures absent",
)
def test_cost_asset_row_matches_the_golden_file():
    c = fetch_company("COST", RunConfig(tickers=["COST"]), cache.load_rates())
    got = records.asset_frame([c]).iloc[0]
    want = pd.read_csv(GOLDEN).iloc[0]

    for col in records.ASSET_SCHEMA:
        g, w = got[col], want[col]
        if isinstance(w, float) and not isinstance(g, str):
            g = float("nan") if g is None else float(g)
            if math.isnan(w):
                assert g != g, f"{col}: expected NaN, got {g}"
            else:
                assert g == pytest.approx(w, rel=1e-9), f"{col}: {g} != {w}"
        else:
            assert str(g) == str(w), f"{col}: {g!r} != {w!r}"
