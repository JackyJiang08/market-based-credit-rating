"""Layer 1 configuration: data universe, source parameters, and raw paths.

Keeping every tunable constant in one module is an enterprise convention: the
rest of the package imports from here, so behaviour changes live in a single,
reviewable place.
"""

from __future__ import annotations

import os

# --------------------------------------------------------------------------- #
# Company universe (the 10-company batch)
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
from creditrating._paths import REPO_ROOT as PROJECT_ROOT  # noqa: E501
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, "raw_data_architecture", "data")

# Trailing window for prices and financials. Must cover
# signal_construction.config.DRIFT_WINDOW_DAYS (~5y) so the drift estimate has
# its full span; the volatility window is a 1y tail of the same series. A
# shorter window silently shortens the drift span and widens its standard error.
DEFAULT_YEARS = 6  # 5y drift window + headroom for holidays and short listings
