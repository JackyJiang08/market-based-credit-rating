"""The in-memory record for one company, passed between pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from raw_data_architecture import lineage


@dataclass
class CompanyData:
    ticker: str
    as_of: str = lineage.RUN_TIMESTAMP
    name: str = ""
    currency: str = ""
    sector: str = ""
    industry: str = ""

    # Point-in-time facts
    market_cap: Optional[float] = None
    shares_traded_class: Optional[float] = None   # yfinance sharesOutstanding
    reference_shares: Optional[float] = None       # one-day method: mktcap / price
    last_close: Optional[float] = None
    dividend_rate: Optional[float] = None
    dividend_yield: Optional[float] = None

    # Time series
    prices: pd.DataFrame = field(default_factory=pd.DataFrame)
    dividends: pd.DataFrame = field(default_factory=pd.DataFrame)
    debt_schedule: pd.DataFrame = field(default_factory=pd.DataFrame)
    panel: pd.DataFrame = field(default_factory=pd.DataFrame)  # aligned daily panel

    # Statements
    q_income: pd.DataFrame = field(default_factory=pd.DataFrame)
    q_balance: pd.DataFrame = field(default_factory=pd.DataFrame)
    q_cashflow: pd.DataFrame = field(default_factory=pd.DataFrame)
    a_income: pd.DataFrame = field(default_factory=pd.DataFrame)
    a_balance: pd.DataFrame = field(default_factory=pd.DataFrame)
    a_cashflow: pd.DataFrame = field(default_factory=pd.DataFrame)

    # EM asset-value estimation (Layer 3 outputs; plain floats to keep this
    # cleaning-layer container free of a modelling-package dependency).
    sigma_A: Optional[float] = None       # annualized asset volatility
    eta_A: Optional[float] = None         # annualized asset return (drift)
    asset_value: Optional[float] = None   # A on the last trading day
    em_iters: Optional[int] = None
    em_converged: Optional[bool] = None
    em_warnings: list = field(default_factory=list)

    # Derived first-passage credit measures (Layer 3)
    mu: Optional[float] = None            # life expectancy E[tau]
    ccm: Optional[float] = None           # credit corrosion measure
    tic: Optional[float] = None           # time-consistent rating (Q=1)
    risk_score: Optional[float] = None    # 100 * TiC
    lam: Optional[float] = None           # default peak lambda
    dd: Optional[float] = None            # distance to default
    edf: Optional[float] = None           # Phi(-DD)
    pit_pd: Optional[float] = None        # 1-year PIT PD

    # How data acquisition went: "OK", or a typed reason the company has no
    # (or partial) data. Populated by Layer 1/2; see #9.
    data_status: Optional[str] = None

    # Drift provenance (Prop. 4.4.1). `drift_regime` is "VALID" or "DEFECTIVE";
    # DEFECTIVE means eta - sigma^2/2 <= 0, so mu/CCM/PIT/TTC/rating are
    # NOT_APPLICABLE rather than merely missing.
    drift_regime: Optional[str] = None
    drift_se: Optional[float] = None          # sigma_A / sqrt(drift span years)
    drift_span_years: Optional[float] = None  # calendar span used for eta

    # PIT -> TTC -> S&P conversion (Layer 3)
    ttc_pd: Optional[float] = None        # no-arbitrage through-the-cycle PD
    sp_rating: Optional[str] = None       # S&P-equivalent letter grade
    outlook: Optional[float] = None       # PIT PD - TTC PD (Prop. 5.3)
    rating_off_grid: Optional[bool] = None  # (CCM, mu) outside the lookup grid
    # How the rating was arrived at: GRID_INTERIOR | ANALYTICAL | OFF_GRID |
    # NOT_APPLICABLE. Only GRID_INTERIOR (and, once Eq. 27 lands, ANALYTICAL)
    # carries a letter; the others report none rather than a clamped one.
    rating_basis: Optional[str] = None
    # True when the TTC PD sits on the grid's smallest expressible value (2bp).
    # The letter is then floor-determined, not model-determined.
    ttc_at_floor: Optional[bool] = None
