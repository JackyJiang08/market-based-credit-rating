"""Layer 3 configuration: credit-model assumptions."""

HORIZON_YEARS = 1.0
# The deck sizes a year at ~250 trading days ("each day is about 1/250 years").
TRADING_DAYS_PER_YEAR = 250

# EM estimation window and convergence controls.
EM_WINDOW_DAYS = 252          # trailing ~1 year of daily observations
EM_MAX_ITER = 20              # hard-fail beyond this (deck expects ~10)
EM_TOL = 1e-5                 # convergence tolerance on sigma_A

# Sanity-check bounds for annualized asset volatility.
SIGMA_A_WARN_LOW = 0.10
SIGMA_A_WARN_HIGH = 0.60
