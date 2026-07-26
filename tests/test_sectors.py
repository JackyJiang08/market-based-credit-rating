"""Firm-type classification and the applicability gate (Part C, ADR 0003)."""

from __future__ import annotations

import pandas as pd
import pytest
from creditrating.data import cleaning as transforms
from creditrating.data import sectors


# --- classification ---------------------------------------------------------
def test_manual_override_beats_inference():
    assert sectors.classify("PNC", "Technology", "Software") is sectors.FirmType.BANK


@pytest.mark.parametrize(
    "industry, expected",
    [
        ("Banks - Regional", sectors.FirmType.BANK),
        ("Banks—Diversified", sectors.FirmType.BANK),
        ("Capital Markets", sectors.FirmType.BANK),
        ("Insurance - Property & Casualty", sectors.FirmType.INSURER),
        ("Reinsurance", sectors.FirmType.INSURER),
        ("REIT - Industrial", sectors.FirmType.REIT),
    ],
)
def test_industry_drives_classification(industry, expected):
    assert sectors.classify("XXXX", "Financial Services", industry) is expected


def test_financial_sector_without_a_known_industry_is_unknown_not_gated():
    """An asset manager or payment processor has an ordinary balance sheet."""
    t = sectors.classify("XXXX", "Financial Services", "Asset Management")
    assert t is sectors.FirmType.UNKNOWN
    status, reason = sectors.applicability(t)
    assert status is sectors.Applicability.APPLICABLE
    assert reason is None


@pytest.mark.parametrize("ticker", ["V", "MA", "PYPL"])
def test_payment_networks_are_not_banks(ticker):
    """Found by the universe run: 'Credit Services' misgated V/MA/PYPL.

    A payment network has an ordinary corporate balance sheet and no
    deposits; gating it as BANK_DEPOSIT_FUNDED was a misclassification.
    """
    t = sectors.classify(ticker, "Financial Services", "Credit Services")
    assert t is sectors.FirmType.NONFINANCIAL
    status, reason = sectors.applicability(t)
    assert status is sectors.Applicability.APPLICABLE and reason is None


@pytest.mark.parametrize("ticker", ["ALLY", "COF", "AXP"])
def test_deposit_funded_credit_services_names_stay_gated(ticker):
    """ALLY/COF are deposit-funded lenders; AXP funds through its own bank.
    The 'Credit Services' marker must keep catching them."""
    t = sectors.classify(ticker, "Financial Services", "Credit Services")
    assert t is sectors.FirmType.BANK


def test_ordinary_company_is_nonfinancial():
    assert (
        sectors.classify("COST", "Consumer Defensive", "Discount Stores")
        is sectors.FirmType.NONFINANCIAL
    )


def test_missing_metadata_is_unknown_and_still_rated():
    assert sectors.classify("XXXX", None, None) is sectors.FirmType.UNKNOWN
    status, _ = sectors.applicability(sectors.FirmType.UNKNOWN)
    assert status is sectors.Applicability.APPLICABLE


# --- the gate ---------------------------------------------------------------
@pytest.mark.parametrize(
    "ft, code",
    [
        (sectors.FirmType.BANK, "BANK_DEPOSIT_FUNDED"),
        (sectors.FirmType.INSURER, "INSURER_RESERVE_LIABILITIES"),
        (sectors.FirmType.REIT, "REIT_ASSET_STRUCTURE"),
    ],
)
def test_gated_types_are_not_applicable_with_a_machine_readable_reason(ft, code):
    status, reason = sectors.applicability(ft)
    assert status is sectors.Applicability.NOT_APPLICABLE
    assert reason == code
    assert code in sectors.REASON_TEXT, "every code needs prose for the workbook"


def test_nonfinancial_is_applicable_regardless_of_book_equity():
    """Book equity is not an input to the gate any more (ADR 0003, revision 1).

    The signature change is the test: `applicability` takes only the firm type,
    so a negative-book-equity name like DELL cannot be gated on an accounting
    artifact the market-implied model never uses.
    """
    status, reason = sectors.applicability(sectors.FirmType.NONFINANCIAL)
    assert status is sectors.Applicability.APPLICABLE
    assert reason is None


# --- market-based capital-structure test (ADR 0003, revision 1) --------------
def test_dell_shaped_firm_passes_the_market_test():
    """DELL: A ~= $301bn against ~$31bn total debt -- negative book equity,
    comfortably applicable on market numbers."""
    status, reason = sectors.market_applicability(301.3e9, 31.2e9)
    assert status is sectors.Applicability.APPLICABLE
    assert reason is None


def test_assets_inside_the_convention_band_are_gated():
    status, reason = sectors.market_applicability(90e9, 100e9)
    assert status is sectors.Applicability.NOT_APPLICABLE
    assert reason == "ASSETS_BELOW_TOTAL_DEBT"
    assert reason in sectors.REASON_TEXT


def test_assets_exactly_at_the_w1_barrier_are_gated():
    """The margin is strict: A must exceed the w = 1.0 barrier, not meet it."""
    status, reason = sectors.market_applicability(100e9, 100e9)
    assert status is sectors.Applicability.NOT_APPLICABLE
    assert reason == "ASSETS_BELOW_TOTAL_DEBT"


@pytest.mark.parametrize(
    "a, d", [(None, 100e9), (100e9, None), (float("nan"), 100e9), (100e9, float("nan")),]
)
def test_missing_market_inputs_do_not_gate(a, d):
    """Same philosophy as UNKNOWN firm types: absent data is not evidence."""
    status, reason = sectors.market_applicability(a, d)
    assert status is sectors.Applicability.APPLICABLE
    assert reason is None


def test_reason_codes_are_stable_identifiers_not_prose():
    for code in sectors.REASON_TEXT:
        assert code.isupper()
        assert " " not in code


# --- PNC under each default-point variant (#16, ADR 0003) -------------------
def _pnc_balance():
    return pd.DataFrame(
        {
            "2026-03-31": {
                "Total Debt": 66_666e6,
                "Long Term Debt": 66_666e6,
                "Total Liabilities Net Minority Interest": 539_352e6,
                "Total Assets": 603_028e6,
                "Stockholders Equity": 63_627e6,
            }
        }
    )


def test_pnc_default_point_variants_differ_by_an_order_of_magnitude():
    bal = _pnc_balance()
    term = transforms.split_term_debt(bal)
    v = transforms.default_point_variants(bal, term["ShortTermDebt"], term["LongTermDebt"])
    standard = v["standard"].dropna().iloc[-1]
    total_liab = v["total_liabilities"].dropna().iloc[-1]

    assert standard == pytest.approx(0.5 * 66_666e6)
    assert total_liab == pytest.approx(539_352e6)
    assert total_liab / standard > 15, "the model sees ~6% of what PNC owes"


def test_pnc_ex_deposits_variant_is_absent_when_the_source_has_no_deposits():
    """Not computable is reported as absent, never as equal to total liabilities."""
    bal = _pnc_balance()
    term = transforms.split_term_debt(bal)
    v = transforms.default_point_variants(bal, term["ShortTermDebt"], term["LongTermDebt"])
    assert "total_liabilities_ex_deposits" not in v


def test_ex_deposits_variant_computes_when_deposits_are_present():
    bal = _pnc_balance()
    bal.loc["Total Deposits"] = {"2026-03-31": 420_000e6}
    term = transforms.split_term_debt(bal)
    v = transforms.default_point_variants(bal, term["ShortTermDebt"], term["LongTermDebt"])
    assert "total_liabilities_ex_deposits" in v
    assert v["total_liabilities_ex_deposits"].dropna().iloc[-1] == pytest.approx(
        539_352e6 - 420_000e6
    )


def test_pnc_is_gated_under_every_variant():
    """The flag does not depend on which default point is chosen."""
    bal = _pnc_balance()
    term = transforms.split_term_debt(bal)
    variants = transforms.default_point_variants(
        bal, term["ShortTermDebt"], term["LongTermDebt"]
    )
    ft = sectors.classify("PNC", "Financial Services", "Banks - Regional")
    for _name in variants:
        status, reason = sectors.applicability(ft)
        assert status is sectors.Applicability.NOT_APPLICABLE
        assert reason == "BANK_DEPOSIT_FUNDED"


# --- #16: provenance and contradiction --------------------------------------
def test_split_term_debt_records_which_field_supplied_each_leg():
    bal = _pnc_balance()
    term = transforms.split_term_debt(bal)
    assert "ShortTermDebtSource" in term.columns
    assert "LongTermDebtSource" in term.columns
    # PNC has no current-debt row at all, so ST is imputed from the complement.
    assert term["ShortTermDebtSource"].iloc[0] in ("missing", "imputed:Total-LongTerm")
    assert term["LongTermDebtSource"].iloc[0] == "Long Term Debt"


def test_contradictory_source_is_flagged_not_silently_clipped():
    """Total < Long-term means the rows disagree; that must be visible."""
    bal = pd.DataFrame({"2026-03-31": {"Total Debt": 400e6, "Long Term Debt": 900e6}})
    term = transforms.split_term_debt(bal)
    assert bool(
        term["DebtSourceContradictory"].iloc[0]
    ), "a negative complement means the source contradicts itself"
    assert term["ShortTermDebt"].iloc[0] == 0.0, "still clipped, but flagged"


def test_consistent_source_is_not_flagged():
    bal = pd.DataFrame({"2026-03-31": {"Total Debt": 1000e6, "Long Term Debt": 900e6}})
    term = transforms.split_term_debt(bal)
    assert not bool(term["DebtSourceContradictory"].iloc[0])
    assert term["ShortTermDebt"].iloc[0] == pytest.approx(100e6)
