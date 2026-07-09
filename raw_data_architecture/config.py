"""Layer 1 configuration: data universe, source parameters, and raw paths.

Keeping every tunable constant in one module is an enterprise convention: the
rest of the package imports from here, so behaviour changes live in a single,
reviewable place.
"""

from __future__ import annotations

import os

# --------------------------------------------------------------------------- #
# Company universe (the 10 assigned tickers)
# --------------------------------------------------------------------------- #
DEFAULT_TICKERS: tuple[str, ...] = (
    "COST", "KO", "DELL", "ORCL", "PNC",
    "WMT", "INTU", "AMZN", "T", "KHC",
)

# --------------------------------------------------------------------------- #
# Macro rates (FRED series id -> human label). Same data as the Federal
# Reserve H.15 release. DGS1 is the risk-free benchmark used by the model.
# --------------------------------------------------------------------------- #
FRED_SERIES: dict[str, str] = {
    "DGS1": "1-Year Treasury Constant Maturity Rate (%)",
    "SOFR": "Secured Overnight Financing Rate (%)",
}
RISK_FREE_SERIES = "DGS1"  # the series fed into the credit model as r

# --------------------------------------------------------------------------- #
# Network politeness / resilience (Yahoo rate-limits heavy use)
# --------------------------------------------------------------------------- #
MAX_RETRIES = 4
BACKOFF_BASE_SECONDS = 2.0
INTER_TICKER_DELAY_SECONDS = 1.5
REQUEST_TIMEOUT = 20

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, "raw_data_architecture", "data")

DEFAULT_YEARS = 2  # trailing window for prices and financials
