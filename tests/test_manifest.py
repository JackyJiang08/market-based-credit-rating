"""Run manifest: input hashes, versions, vintage, team-standard timestamp."""

from __future__ import annotations

import json
import os
import re

import pytest

from creditrating.data import cache
from creditrating.data.pipeline import RunConfig, fetch_company
from creditrating.data import provenance


@pytest.mark.skipif(
    not os.path.exists(os.path.join(cache.cache_dir(), "COST", "prices.parquet")),
    reason="fixtures absent")
def test_manifest_records_hashes_versions_and_vintage(tmp_path):
    cfg = RunConfig(tickers=["COST"], run_bootstrap=False)
    c = fetch_company("COST", cfg, cache.load_rates())
    path = provenance.write_manifest("testrun123", cfg, [c], str(tmp_path))
    m = json.load(open(path))

    assert m["run_id"] == "testrun123"
    # Team timestamp standard (TIMING_PROTOCOL §10): tz-aware UTC ISO 8601.
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", m["generated_utc"])
    assert m["package_version"]
    assert m["data_vintage_latest_priced_day"] >= "2026-07-24"
    assert m["config"]["tickers"] == ["COST"]
    # Every COST cache artifact is hashed, so a rerun can prove same inputs.
    assert any(k.startswith("COST/") for k in m["input_hashes_sha256_16"])
    assert all(re.fullmatch(r"[0-9a-f]{16}", v)
               for v in m["input_hashes_sha256_16"].values())
