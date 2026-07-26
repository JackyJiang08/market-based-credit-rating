"""Layer 2 configuration: normalization rules and clean-data paths."""

from __future__ import annotations

import os

BALANCE_SHEET_MAP: dict[str, tuple[str, ...]] = {
    "Total Debt": ("Total Debt",),
    "Total Liabilities": (
        "Total Liabilities Net Minority Interest",
        "Total Liab",
        "Total Liabilities",
    ),
    "Short-term / Current Debt": (
        "Current Debt And Capital Lease Obligation",
        "Current Debt",
        "Short Term Debt",
        "Short Long Term Debt",
    ),
    "Short-term / Current Liabilities": (
        "Current Liabilities",
        "Total Current Liabilities",
    ),
    "Long-term Debt": (
        "Long Term Debt And Capital Lease Obligation",
        "Long Term Debt",
    ),
    "Long-term Liabilities": (
        "Total Non Current Liabilities Net Minority Interest",
        "Total Non Current Liabilities",
        "Non Current Liabilities",
    ),
}

SHORT_TERM_DEBT_WEIGHT = 1.0
LONG_TERM_DEBT_WEIGHT = 0.5

# Publication lag: how long after a period end a statement is assumed to have
# become public. docs/TIMING_PROTOCOL.md §3 requires that a statement is eligible
# only from its filing time, and that where the true filing time is unavailable
# we "use a documented conservative lag and set an explicit flag such as
# availability_method='estimated_lag'". The data source publishes period ends,
# not filing dates, so these are the conservative bounds.
#
# SEC deadlines: a 10-Q is due 40 days after quarter end for a large accelerated
# filer and 45 for everyone else; a 10-K is due 60, 75 or 90 days after fiscal
# year end by filer status. We take the *latest* deadline in each case, because
# erring late means the model sees less information than it might have, which is
# the safe direction for a no-look-ahead guarantee.
QUARTERLY_FILING_LAG_DAYS = 45
ANNUAL_FILING_LAG_DAYS = 90
AVAILABILITY_METHOD = "estimated_lag"

# Credit horizon in years, tied to the 1-year risk-free tenor (DGS1) used in
# alignment. Owned by the cleaning layer that builds the daily panel.
HORIZON_YEARS = 1.0

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DATA_DIR = os.path.join(PROJECT_ROOT, "data_cleaning", "data")
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, "raw_data_architecture", "data")
