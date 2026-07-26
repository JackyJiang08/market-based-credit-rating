"""Layer 3 configuration: credit-model assumptions."""

HORIZON_YEARS = 1.0
# A year is sized at ~250 trading days (each trading day ~ 1/250 years).
TRADING_DAYS_PER_YEAR = 250

# EM estimation window and convergence controls.
EM_WINDOW_DAYS = 252  # trailing ~1 year of daily observations
EM_MAX_ITER = 20  # hard-fail beyond this (typically converges in ~10)
EM_TOL = 1e-5  # convergence tolerance on sigma_A

# Drift (eta_A) estimation window, deliberately longer than the volatility
# window. Volatility is a high-frequency quantity: it is estimated from the
# quadratic variation of the path, so 252 daily observations already give a
# tight estimate. The drift is not. The standard error of a mean log-return
# estimated over a span of `y` years is sigma_A / sqrt(y), independent of the
# sampling frequency -- sampling the same year more finely does not help.
# At y = 1 that makes SE(eta) ~ sigma_A, i.e. the estimate is the same size as
# its own error. Five years cuts it to sigma_A / sqrt(5), ~55% lower.
# See docs/adr/0001-drift-estimation.md.
DRIFT_WINDOW_DAYS = 1260  # trailing ~5 years of daily observations

# Asset inversion (E-step). `g` is increasing in A with g(A) < A, so the root of
# g(A) = E lies above E; the upper bracket is doubled until it covers the root.
# 60 doublings span a factor of 2^60 ~ 1e18 above the starting guess, which no
# real balance sheet reaches -- exhausting them means the inversion is broken,
# not that the bracket was too small, so em.estimate raises rather than
# bisecting an interval with no root in it.
BRACKET_MAX_DOUBLINGS = 60
BISECTION_STEPS = 80  # ~2^-80 relative precision on the recovered A
MIN_OBSERVATIONS = 30  # fewest clean daily rows EM will accept

# Sanity-check bounds for annualized asset volatility.
SIGMA_A_WARN_LOW = 0.10
SIGMA_A_WARN_HIGH = 0.60


# Uncertainty propagation (signal_construction/bootstrap.py).
BOOTSTRAP_REPLICATES = 500  # per company in a batch run; analysis uses more
BOOTSTRAP_SEED = 20260726  # fixed so a run is reproducible
BOOTSTRAP_INTERVAL = (0.05, 0.95)

# Weak identification. A drift whose |t| falls below this is not distinguishable
# from zero at any conventional level, so mu and CCM -- which divide by it -- are
# driven by noise. This ANNOTATES a rating; it never suppresses one. Suppression
# is reserved for the genuine Prop. 4.4.1 violation (drift <= 0), because that is
# an assumption failure rather than a precision problem.
# See docs/adr/0002-defective-drift-interval-proposal.md.
WEAK_IDENTIFICATION_T = 2.0
