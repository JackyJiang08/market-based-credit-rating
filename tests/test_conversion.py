"""PIT -> TTC -> S&P conversion tests.

Analytical no-arbitrage checks run everywhere. Grid/lookup checks need the
instructor's conversion workbook (IP, kept under local/) and are skipped when
it is absent, so a fresh clone still runs green.
"""

from __future__ import annotations

import os

import pytest

from signal_construction import conversion

HAS_TABLES = os.path.exists(conversion.DEFAULT_XLSX)
needs_tables = pytest.mark.skipif(not HAS_TABLES,
                                  reason="conversion workbook (IP) not present")


# --- Analytical no-regulatory-arbitrage (Section 5.3) -----------------------
def test_alpha_first_hitting_matches_paper():
    assert conversion.alpha_first_hitting(1.5) == pytest.approx(0.91906, abs=1e-4)


def test_no_arb_ccm_star_matches_paper():
    assert conversion.no_arb_ccm_star(1.5) == pytest.approx(1.35373, abs=1e-4)


# --- Grid reproduces the paper's S&P TTC (Tables 13-14) ---------------------
@needs_tables
def test_ttc_grid_reproduces_paper_sp_ttc():
    t = conversion.load_tables()
    assert conversion.ttc_pd(t, 1.5, 1).value == pytest.approx(0.237, abs=2e-3)
    assert conversion.ttc_pd(t, 1.5, 5).value == pytest.approx(0.047, abs=2e-3)
    assert conversion.ttc_pd(t, 5.0, 1).value == pytest.approx(1.000, abs=2e-3)
    assert conversion.ttc_pd(t, 5.0, 5).value == pytest.approx(0.188, abs=2e-3)


@needs_tables
def test_sp_rating_thresholds():
    t = conversion.load_tables()
    assert conversion.sp_rating(t, 0.0) == "AAA"
    assert conversion.sp_rating(t, 0.05) == "B"          # in [0.0441, 0.0765)
    assert conversion.sp_rating(t, 1.0) == "D"           # beyond the worst band


@needs_tables
def test_off_grid_is_flagged():
    t = conversion.load_tables()
    assert conversion.ttc_pd(t, 0.05, 1.0).off_grid       # CCM below grid min 0.1
    assert conversion.ttc_pd(t, 1.0, 500.0).off_grid      # mu above grid max 160
    assert not conversion.ttc_pd(t, 1.5, 5.0).off_grid    # inside the grid
