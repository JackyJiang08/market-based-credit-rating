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

# Credit horizon in years, tied to the 1-year risk-free tenor (DGS1) used in
# alignment. Owned by the cleaning layer that builds the daily panel.
HORIZON_YEARS = 1.0

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DATA_DIR = os.path.join(PROJECT_ROOT, "data_cleaning", "data")
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, "raw_data_architecture", "data")
