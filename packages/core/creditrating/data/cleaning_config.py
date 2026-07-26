"""Layer 2 configuration: normalization rules and clean-data paths."""

from __future__ import annotations

import os

from creditrating._paths import REPO_ROOT as PROJECT_ROOT

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

# Candidate line items for deposits, used by the financial-firm default-point
# variants. The free tier does not publish a deposits row for every bank; when
# it is absent the ex-deposits variant is reported as not computable rather
# than silently equal to total liabilities.
DEPOSIT_ROWS: tuple[str, ...] = (
    "Total Deposits",
    "Deposits",
    "Customer Deposits",
    "Deposits From Customers",
    "Interest Bearing Deposits Liability",
)

# Which default-point definition the pipeline rates on:
#   standard | total_liabilities | total_liabilities_ex_deposits
DEFAULT_POINT_VARIANT = "standard"

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

# Plausible band for an annualised risk-free rate expressed as a decimal, used
# to catch a units change at the source. 1-year Treasury yields have ranged
# roughly 0.04%-16% since 1962, so this is wide enough never to fire on real
# data and narrow enough to catch a percent/decimal mix-up (which would land
# either near 0.0004 or near 4.0).
RATE_MIN = 0.0
RATE_MAX = 0.30
# Below this (in percent, before conversion) a series is suspiciously flat for a
# percent quote and may already be in decimals. Warn only -- see alignment.py.
RATE_PERCENT_SUSPICIOUS_MAX = 0.5

# Credit horizon in years, tied to the 1-year risk-free tenor (DGS1) used in
# alignment. Owned by the cleaning layer that builds the daily panel.
HORIZON_YEARS = 1.0


CLEAN_DATA_DIR = os.path.join(PROJECT_ROOT, "data_cleaning", "data")
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, "raw_data_architecture", "data")
