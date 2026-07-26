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


def classify(ticker: str, sector: Optional[str] = None,
             industry: Optional[str] = None) -> FirmType:
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


def applicability(firm_type: FirmType,
                  total_equity: Optional[float] = None
                  ) -> tuple[Applicability, Optional[str]]:
    """Decide whether to rate this firm, with a machine-readable reason.

    Returns `(status, reason_code)`. `reason_code` is None when applicable and
    otherwise a stable identifier suitable for a workbook column or an API
    field -- not prose, which callers cannot branch on.
    """
    if firm_type is FirmType.BANK:
        return Applicability.NOT_APPLICABLE, "BANK_DEPOSIT_FUNDED"
    if firm_type is FirmType.INSURER:
        return Applicability.NOT_APPLICABLE, "INSURER_RESERVE_LIABILITIES"
    if firm_type is FirmType.REIT:
        return Applicability.NOT_APPLICABLE, "REIT_ASSET_STRUCTURE"
    if total_equity is not None and total_equity < 0:
        # A > D is the model's own precondition; negative book equity does not
        # by itself violate it (A is market-implied), but it signals a capital
        # structure the barrier construction handles badly.
        return Applicability.NOT_APPLICABLE, "NEGATIVE_BOOK_EQUITY"
    return Applicability.APPLICABLE, None


REASON_TEXT = {
    "BANK_DEPOSIT_FUNDED":
        "Deposits dominate the liability side and are a funding input, not a "
        "default trigger. The regulatory failure point is a capital ratio, not "
        "asset value crossing a debt barrier.",
    "INSURER_RESERVE_LIABILITIES":
        "Policy reserves are the dominant liability and are contingent, not "
        "fixed claims with a payment date.",
    "REIT_ASSET_STRUCTURE":
        "Asset value is property-appraisal driven and the capital structure is "
        "shaped by distribution requirements rather than default risk.",
    "NEGATIVE_BOOK_EQUITY":
        "Negative book equity signals a capital structure the debt-barrier "
        "construction handles badly.",
}
