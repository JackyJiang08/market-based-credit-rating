"""Firm-type classification and the applicability gate.

The first-passage model prices equity as a call on assets struck at a debt
barrier. That construction assumes the barrier is *debt* -- a fixed claim whose
non-payment triggers default. For a bank it is not: the dominant liability is
deposits, which are a funding input rather than a default trigger, and the
regulatory failure point is a capital ratio, not asset value crossing debt.

PNC makes the size of the problem concrete. Its default point under the shipped
convention is about $33bn against **$539bn of total liabilities** -- the model is
looking at roughly 6% of what the firm owes. It nonetheless comes back
`SCALE_RESOLVED` with an investment-grade letter, which is precisely why an
explicit gate is needed: the output looks confident.

Classification is deliberately conservative. A firm we cannot classify is
`UNKNOWN` and is *not* gated, because silently refusing to rate a company on a
missing metadata field would be its own failure mode.
"""

from __future__ import annotations

import enum
from typing import Optional


class FirmType(enum.Enum):
    """What kind of balance sheet this is."""

    NONFINANCIAL = "NONFINANCIAL"
    BANK = "BANK"
    INSURER = "INSURER"
    REIT = "REIT"
    UNKNOWN = "UNKNOWN"


class Applicability(enum.Enum):
    """Whether the structural model is meaningful for this firm."""

    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "MODEL_NOT_APPLICABLE"


# Firm types for which the debt-barrier construction does not hold.
GATED_TYPES = (FirmType.BANK, FirmType.INSURER, FirmType.REIT)

# Manual overrides win over any inferred classification. Vendor sector strings
# are inconsistent and occasionally wrong, and a wrong classification here is
# expensive in both directions.
MANUAL_OVERRIDES: dict[str, FirmType] = {
    # The vendor's "Credit Services" industry string lumps deposit-funded
    # lenders (ALLY, COF -- correctly gated as banks) together with payment
    # networks, which carry ordinary corporate balance sheets and no deposits.
    # The marker must stay for the former, so the latter are pinned here.
    # AXP is deliberately NOT pinned: it funds through its own bank charter.
    # (Found by the 150-name universe run: V/MA/PYPL came back
    # BANK_DEPOSIT_FUNDED.)
    "V": FirmType.NONFINANCIAL,
    "MA": FirmType.NONFINANCIAL,
    "PYPL": FirmType.NONFINANCIAL,
    "PNC": FirmType.BANK,
    "JPM": FirmType.BANK,
    "BAC": FirmType.BANK,
    "WFC": FirmType.BANK,
    "C": FirmType.BANK,
    "GS": FirmType.BANK,
    "MS": FirmType.BANK,
    "USB": FirmType.BANK,
    "TFC": FirmType.BANK,
    "SCHW": FirmType.BANK,
    "BRK-B": FirmType.INSURER,
    "AIG": FirmType.INSURER,
    "MET": FirmType.INSURER,
    "PRU": FirmType.INSURER,
    "ALL": FirmType.INSURER,
    "TRV": FirmType.INSURER,
    "CB": FirmType.INSURER,
    "PLD": FirmType.REIT,
    "AMT": FirmType.REIT,
    "SPG": FirmType.REIT,
    "O": FirmType.REIT,
}

# Substrings matched case-insensitively against the vendor's industry string.
_BANK_MARKERS = ("bank", "thrift", "savings", "credit services", "capital markets")
_INSURER_MARKERS = ("insurance", "insurer", "reinsurance")
_REIT_MARKERS = ("reit", "real estate investment trust")

_FINANCIAL_SECTORS = ("financial services", "financial", "financials")
_REAL_ESTATE_SECTORS = ("real estate",)


def classify(
    ticker: str, sector: Optional[str] = None, industry: Optional[str] = None
) -> FirmType:
    """Classify a firm from its ticker override, then sector and industry.

    Order matters: an explicit override beats inference, and industry beats
    sector because "Financial Services" covers banks, insurers, asset managers
    and payment processors, which do not share a balance-sheet shape.
    """
    key = (ticker or "").strip().upper()
    if key in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[key]

    ind = (industry or "").strip().lower()
    sec = (sector or "").strip().lower()

    if any(m in ind for m in _REIT_MARKERS):
        return FirmType.REIT
    if any(m in ind for m in _INSURER_MARKERS):
        return FirmType.INSURER
    if any(m in ind for m in _BANK_MARKERS):
        return FirmType.BANK
    if any(s in sec for s in _REAL_ESTATE_SECTORS) and "reit" in ind:
        return FirmType.REIT
    if any(s in sec for s in _FINANCIAL_SECTORS):
        # Financial sector but an industry we could not pin down. Not gated --
        # an asset manager or a payment processor has an ordinary balance sheet.
        return FirmType.UNKNOWN
    if not sec and not ind:
        return FirmType.UNKNOWN
    return FirmType.NONFINANCIAL


def applicability(firm_type: FirmType) -> tuple[Applicability, Optional[str]]:
    """Decide from the firm type whether to rate this firm.

    Returns `(status, reason_code)`. `reason_code` is None when applicable and
    otherwise a stable identifier suitable for a workbook column or an API
    field -- not prose, which callers cannot branch on.

    Book equity deliberately does not appear here. An earlier revision gated on
    negative book equity; that removed DELL, whose negative equity is a buyback
    artifact the market-implied model never looks at (ADR 0003, revision 1).
    The capital-structure test is `market_applicability`, run after EM.
    """
    if firm_type is FirmType.BANK:
        return Applicability.NOT_APPLICABLE, "BANK_DEPOSIT_FUNDED"
    if firm_type is FirmType.INSURER:
        return Applicability.NOT_APPLICABLE, "INSURER_RESERVE_LIABILITIES"
    if firm_type is FirmType.REIT:
        return Applicability.NOT_APPLICABLE, "REIT_ASSET_STRUCTURE"
    return Applicability.APPLICABLE, None


def market_applicability(
    asset_value: Optional[float], total_debt: Optional[float]
) -> tuple[Applicability, Optional[str]]:
    """Market-based capital-structure test, run after the EM step.

    `A > D` alone is vacuous as a gate -- the EM inverter raises on it -- so the
    margin is the operative choice. The margin here: market-implied assets must
    clear the barrier under the MOST CONSERVATIVE debt convention, `w = 1.0`
    (`ST + 1.0*LT`, i.e. total debt), not merely the rated `w = 0.5` one. The
    convention sweep showed the letter moves with `w`; applicability must not.
    A firm inside the band [ST+0.5*LT, ST+LT] would flip between ratable and
    at-the-barrier on an arbitrary weight, which is a specification question,
    not a credit measurement (ADR 0003, revision 1).

    Missing inputs do not gate, for the same reason `UNKNOWN` firm types do
    not: refusing to rate on absent metadata is its own failure mode.
    """
    if asset_value is None or total_debt is None:
        return Applicability.APPLICABLE, None
    if not (asset_value == asset_value and total_debt == total_debt):  # NaN
        return Applicability.APPLICABLE, None
    if asset_value <= total_debt:
        return Applicability.NOT_APPLICABLE, "ASSETS_BELOW_TOTAL_DEBT"
    return Applicability.APPLICABLE, None


REASON_TEXT = {
    "BANK_DEPOSIT_FUNDED": "Deposits dominate the liability side and are a funding input, not a "
    "default trigger. The regulatory failure point is a capital ratio, not "
    "asset value crossing a debt barrier.",
    "INSURER_RESERVE_LIABILITIES": "Policy reserves are the dominant liability and are contingent, not "
    "fixed claims with a payment date.",
    "REIT_ASSET_STRUCTURE": "Asset value is property-appraisal driven and the capital structure is "
    "shaped by distribution requirements rather than default risk.",
    "REPORTING_CURRENCY_MISMATCH": "The statements report in a different currency than the listed price "
    "(an ADR filing in its home currency). Equity and the debt barrier "
    "would enter the inversion in different units, so EM and the measures "
    "are skipped entirely rather than published unit-corrupt. No FX "
    "conversion is attempted: a converted statement at a chosen rate "
    "would be a fabricated input.",
    "ASSETS_BELOW_TOTAL_DEBT": "Market-implied asset value does not clear the default barrier under "
    "the most conservative debt convention (ST + 1.0*LT). Inside that band "
    "the rating would depend on the arbitrary long-term debt weight rather "
    "than on the firm.",
}
