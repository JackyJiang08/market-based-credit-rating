"""PIT -> TTC -> S&P conversion tests.

Analytical no-arbitrage checks run everywhere. Grid/lookup checks need the
conversion workbook (proprietary, kept under local/) and are skipped when
it is absent, so a fresh clone still runs green.
"""

from __future__ import annotations

import os

import pytest

from signal_construction import conversion

HAS_TABLES = os.path.exists(conversion.DEFAULT_XLSX)
needs_tables = pytest.mark.skipif(not HAS_TABLES,
                                  reason="conversion workbook (proprietary) not present")


# --- Analytical no-regulatory-arbitrage (Section 5.3) -----------------------
def test_alpha_first_hitting_matches_paper():
    assert conversion.alpha_first_hitting(1.5) == pytest.approx(0.91906, abs=1e-4)


def test_no_arb_ccm_star_matches_paper():
    assert conversion.no_arb_ccm_star(1.5) == pytest.approx(1.35373, abs=1e-4)


# --- Outlook direction (Prop. 5.3, Eq. 28) ----------------------------------
# Eq. (28) reads `Outlook = PD_FH - S&P TTC`, i.e. PIT - TTC. The prose above it
# in the paper reads in the opposite order and has already prompted one proposal
# to invert this. These tests exist to make that inversion fail loudly.
def test_outlook_is_pit_minus_ttc_not_the_reverse():
    assert conversion.outlook(0.30, 0.10) == pytest.approx(0.20)
    assert conversion.outlook(0.10, 0.30) == pytest.approx(-0.20)
    # Asymmetric inputs: an inverted implementation returns the negation, so a
    # symmetric pair would pass either way. This pair cannot.
    assert conversion.outlook(0.75, 0.25) == pytest.approx(0.50)


def test_outlook_sign_matches_the_papers_trend_reading():
    """`Outlook > 0` must mean PIT above TTC (elevated short-term risk)."""
    # Prop. 5.3: "If Outlook>0, then the future trend is positive" -- short-term
    # risk exceeds through-the-cycle, so reversion to TTC is an improvement.
    assert conversion.outlook(0.20, 0.05) > 0      # PIT > TTC -> positive trend
    assert conversion.outlook(0.05, 0.20) < 0      # PIT < TTC -> negative trend
    assert conversion.outlook(0.10, 0.10) == 0.0   # neutral


def test_outlook_reproduces_the_delivered_asset_sheet_value():
    """The delivered sheet shows -0.0002 at PIT=0, TTC=0.0002 (the 2bp floor).

    That value is correct per Eq. (28). It is negative only because the TTC grid
    floors at 2bp while PIT underflows to 0 -- a floor artifact, not a signal.
    See the `rating_basis` / floor-determined reporting for the interpretation.
    """
    assert conversion.outlook(0.0, 0.0002) == pytest.approx(-0.0002)


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
