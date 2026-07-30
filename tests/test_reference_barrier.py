"""The reference convention's fourth switch: the total-liabilities barrier.

Confirmed by the reconciliation study: the reference implementation's
implied default point equals the Total Liabilities line (TL/D* 0.98-1.01 on
every name with reference values). DOCUMENTED keeps D = 1.0*ST + 0.5*LT.
"""

from __future__ import annotations

import os

import pandas as pd
import pytest
from creditrating.data import cache
from creditrating.data import cleaning as transforms
from creditrating.data.pipeline import RunConfig, fetch_company
from creditrating.model import convention as conventions
from creditrating.model import conversion

HAS_COST = os.path.exists(os.path.join(cache.cache_dir(), "COST", "prices.parquet"))
HAS_PNC = os.path.exists(os.path.join(cache.cache_dir(), "PNC", "prices.parquet"))
# The letter layer needs the licensed workbook; without it the conversion
# never runs and determinations stay None (the documented no-workbook
# contract, asserted by the golden tests). Letter-level assertions below are
# conditional on it, measure-level assertions are not.
HAS_WORKBOOK = os.path.exists(conversion.DEFAULT_XLSX)


def test_total_liabilities_extraction_prefers_the_canonical_row():
    bal = pd.DataFrame(
        {
            pd.Timestamp("2026-03-31"): {
                "Total Liabilities Net Minority Interest": 100.0,
                "Total Liab": 90.0,
            },
            pd.Timestamp("2025-12-31"): {
                "Total Liabilities Net Minority Interest": 95.0,
                "Total Liab": 85.0,
            },
        }
    )
    s, row = transforms.total_liabilities_by_period(bal)
    assert row == "Total Liabilities Net Minority Interest"
    assert s.loc[pd.Timestamp("2026-03-31")] == 100.0


def test_total_liabilities_falls_back_with_provenance():
    bal = pd.DataFrame({pd.Timestamp("2026-03-31"): {"Total Liab": 90.0}})
    s, row = transforms.total_liabilities_by_period(bal)
    assert row == "Total Liab"
    assert s.iloc[0] == 90.0


def test_missing_row_is_reported_not_substituted():
    bal = pd.DataFrame({pd.Timestamp("2026-03-31"): {"Something Else": 1.0}})
    s, row = transforms.total_liabilities_by_period(bal)
    assert row is None and s.empty


def test_presets_carry_the_barrier_and_gate_switches():
    assert conventions.DOCUMENTED.barrier_field == "st_plus_half_lt"
    assert conventions.DOCUMENTED.applicability == "suppress"
    assert conventions.REFERENCE.barrier_field == "total_liabilities"
    assert conventions.REFERENCE.applicability == "annotate"


@pytest.mark.skipif(not HAS_COST, reason="cache fixtures not present")
def test_reference_barrier_is_total_liabilities_on_the_fixture():
    c = fetch_company(
        "COST", RunConfig(tickers=["COST"], convention="REFERENCE"), cache.load_rates()
    )
    assert c.convention == "REFERENCE"
    assert c.barrier_source == "Total Liabilities Net Minority Interest"
    d_last = float(c.panel["DefaultPointDebt_D"].dropna().iloc[-1])
    st = float(c.panel["ShortTermDebt"].dropna().iloc[-1])
    lt = float(c.panel["LongTermDebt"].dropna().iloc[-1])
    # the barrier is the liability side, far above the documented default point
    assert d_last > 3 * (st + 0.5 * lt)
    # the documented run is untouched
    cd = fetch_company("COST", RunConfig(tickers=["COST"]), cache.load_rates())
    assert cd.barrier_source == "ST_PLUS_HALF_LT"
    assert float(cd.panel["DefaultPointDebt_D"].dropna().iloc[-1]) == pytest.approx(
        st + 0.5 * lt, rel=1e-9
    )


@pytest.mark.skipif(not HAS_PNC, reason="cache fixtures not present")
def test_gated_bank_is_annotated_not_suppressed_under_reference():
    ref = fetch_company(
        "PNC", RunConfig(tickers=["PNC"], convention="REFERENCE"), cache.load_rates()
    )
    # the classification keeps running...
    assert ref.applicability_reason == "BANK_DEPOSIT_FUNDED"
    assert ref.model_applicable is False
    # ...and the measures are produced against the whole liability side.
    assert ref.risk_score is not None
    # DOCUMENTED still suppresses the letter either way.
    doc = fetch_company("PNC", RunConfig(tickers=["PNC"]), cache.load_rates())
    assert doc.sp_rating is None
    if HAS_WORKBOOK:
        # With the conversion tables: REFERENCE produces the letter and keeps
        # the classification as an annotation; DOCUMENTED stamps the
        # not-applicable determination.
        assert ref.sp_rating is not None
        assert ref.rating_determination != "MODEL_NOT_APPLICABLE"
        assert doc.rating_determination == "MODEL_NOT_APPLICABLE"
    else:
        # Without them the conversion never runs: no letter, no
        # determination -- the documented no-workbook contract.
        assert ref.sp_rating is None and doc.rating_determination is None
