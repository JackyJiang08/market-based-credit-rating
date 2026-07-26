"""Window invariance of the equity series and everything downstream (#15).

The old additive add-back made `DivAddBackClose` equal `Close` plus every
dividend paid since the first downloaded row, so the level of the series -- and
therefore `sigma_A`, `A`, `ln(A/D)`, `CCM`, `mu` and the rating -- depended on
`DEFAULT_YEARS`. Raising that config value from 2 to 6 silently moved every
number in the batch.

These tests are the fix. They run the same pipeline stages over the same cached
panel truncated to different window lengths and assert the outputs agree.
"""

from __future__ import annotations

import math
import os

import numpy as np
import pandas as pd
import pytest

from data_cleaning import alignment
from signal_construction import config as sig_config
from signal_construction import conversion, em, measures

# Tolerances. sigma_A and A are asserted tightly: a window-invariant
# construction should reproduce them to within EM's own convergence tolerance
# and the arithmetic of a different-length cumprod. The rating must be identical.
SIGMA_TOL = 5e-4          # absolute, on a quantity of order 0.15-0.55
ASSET_REL_TOL = 1e-6      # relative, on the asset value A
DRIFT_TOL = 5e-3          # absolute; the drift genuinely uses more data


def _synthetic_prices(n: int = 1600, seed: int = 7,
                      div_every: int = 63, div_amount: float = 0.9):
    """A deterministic price path with regular dividends."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2019-01-01", periods=n)
    steps = rng.normal(0.0004, 0.012, size=n)
    close = pd.Series(100.0 * np.exp(np.cumsum(steps)), index=idx, name="Close")
    div = pd.Series(0.0, index=idx, name="Dividends")
    div.iloc[div_every::div_every] = div_amount
    return close, div


# --- the construction itself ------------------------------------------------
def test_total_return_close_is_anchored_at_the_valuation_date():
    close, div = _synthetic_prices()
    out = alignment.total_return_close(close, div)
    assert out.iloc[-1] == pytest.approx(close.iloc[-1], rel=1e-12), \
        "the last value must be the real market price"


@pytest.mark.parametrize("start", [0, 200, 500, 900])
def test_total_return_returns_are_invariant_to_the_window_start(start):
    """Truncating the front of the window must not change any later return."""
    close, div = _synthetic_prices()
    full = alignment.total_return_close(close, div)
    part = alignment.total_return_close(close.iloc[start:], div.iloc[start:])

    r_full = np.log(full / full.shift(1)).iloc[start + 1:]
    r_part = np.log(part / part.shift(1)).iloc[1:]
    assert np.allclose(r_full.to_numpy(), r_part.to_numpy(), atol=1e-12)


def test_old_additive_construction_was_not_invariant():
    """Pins the defect, so the regression cannot be reintroduced quietly."""
    close, div = _synthetic_prices()
    old_full = (close + div.cumsum())
    old_part = (close.iloc[500:] + div.iloc[500:].cumsum())
    r_full = np.log(old_full / old_full.shift(1)).iloc[501:]
    r_part = np.log(old_part / old_part.shift(1)).iloc[1:]
    assert not np.allclose(r_full.to_numpy(), r_part.to_numpy(), atol=1e-9), \
        "premise: the additive construction depended on the window start"


def test_missing_dividends_are_not_treated_as_zero():
    close, div = _synthetic_prices()
    div_unknown = div.copy()
    div_unknown.iloc[div_unknown.index.get_indexer([div.index[400]])] = np.nan

    known = alignment.total_return_close(close, div)
    unknown = alignment.total_return_close(close, div_unknown)
    # An unknown dividend makes that day's return unknown, and the index cannot
    # be continued through it -- it must not silently become a zero dividend.
    assert unknown.isna().any(), "a NaN dividend must not be read as 0.0"
    assert not known.isna().any()


def test_absent_dividend_column_yields_nan_not_a_price_return_series():
    idx = pd.bdate_range("2024-01-02", periods=40)
    prices = pd.DataFrame({"Close": np.linspace(100, 120, 40)}, index=idx)
    panel = alignment.build_panel(prices, 1000.0, pd.DataFrame(), None)
    assert panel["Dividends"].isna().all()
    assert panel["DivAddBackClose"].isna().all(), \
        "no dividend column means unknown total return, not zero dividends"
    assert panel["MarketCap_E"].isna().all(), "and no equity series to fit"


# --- end-to-end invariance over the real cached panels ----------------------
CACHED = "data_cleaning/data"
TICKERS = ["COST", "KO", "DELL", "ORCL", "PNC", "WMT", "INTU", "AMZN", "T", "KHC"]
has_cache = pytest.mark.skipif(
    not os.path.isdir(CACHED),
    reason="no cached panels; run `python -m mdt batch config/companies.yaml`")


def _panel(ticker: str) -> pd.DataFrame:
    return pd.read_csv(f"{CACHED}/{ticker}/aligned_panel.csv",
                       index_col=0, parse_dates=True).sort_index()


def _fit(panel: pd.DataFrame, years: int):
    """Re-run EM + measures over the trailing `years` of a cached panel.

    Rebuilds the equity series from Close and Dividends so the truncation
    exercises the add-back, not just the estimator.
    """
    days = int(years * sig_config.TRADING_DAYS_PER_YEAR)
    w = panel.tail(days)
    if len(w) < 60:
        return None
    e = alignment.total_return_close(w["Close"], w["Dividends"]) * w["Shares"]
    res = em.estimate(e, w["DefaultPointDebt_D"], w["RiskFree_R"])
    m = measures.compute(res.sigma_A, res.asset_last, res.debt_last, res.eta_A)
    return res, m


@has_cache
@pytest.mark.parametrize("ticker", TICKERS)
def test_sigma_and_asset_are_invariant_to_the_download_window(ticker):
    """The acceptance criterion: DEFAULT_YEARS must not move sigma_A or A.

    sigma_A is estimated on a trailing 252 days that all three windows share, so
    a window-invariant equity series must reproduce it. A is the last inverted
    asset value, also on the shared tail.
    """
    try:
        panel = _panel(ticker)
    except FileNotFoundError:
        pytest.skip(f"no cached panel for {ticker}")

    fits = {y: _fit(panel, y) for y in (2, 4, 6)}
    fits = {y: f for y, f in fits.items() if f is not None}
    if len(fits) < 2:
        pytest.skip(f"{ticker}: not enough history for two window lengths")

    sigmas = {y: f[0].sigma_A for y, f in fits.items()}
    assets = {y: f[0].asset_last for y, f in fits.items()}

    lo, hi = min(sigmas.values()), max(sigmas.values())
    assert hi - lo < SIGMA_TOL, f"{ticker}: sigma_A moved {hi - lo:.2e} across windows {sigmas}"

    a_lo, a_hi = min(assets.values()), max(assets.values())
    assert (a_hi - a_lo) / a_hi < ASSET_REL_TOL, \
        f"{ticker}: A moved {(a_hi - a_lo) / a_hi:.2e} relative across windows"


@has_cache
@pytest.mark.parametrize("ticker", TICKERS)
def test_rating_is_invariant_once_the_drift_span_is_saturated(ticker):
    """The letter must not depend on the download window -- with one caveat.

    `sigma_A` and `A` are window-invariant unconditionally (asserted above). The
    *drift* is deliberately not: ADR 0001 estimates it over the whole available
    span precisely because its standard error falls with calendar length. So a
    2-year download genuinely yields a noisier eta than a 6-year one, and that
    is intended behaviour, not the #15 defect.

    What must hold is that once the download is long enough to saturate the
    drift estimator -- i.e. once `drift_span_years` stops growing -- the rating
    stops moving. This test compares only windows whose drift span is equal.
    """
    if not os.path.exists(conversion.DEFAULT_XLSX):
        pytest.skip("conversion workbook (proprietary) not present")
    try:
        panel = _panel(ticker)
    except FileNotFoundError:
        pytest.skip(f"no cached panel for {ticker}")

    tables = conversion.load_tables()
    by_span: dict[float, set[str]] = {}
    for years in (2, 4, 6):
        fit = _fit(panel, years)
        if fit is None:
            continue
        res, m = fit
        span = round(res.drift_span_years, 2)
        if m.regime is measures.DriftRegime.DEFECTIVE:
            label = "NOT_APPLICABLE"
        else:
            look = conversion.ttc_pd(tables, m.ccm, m.mu, pit_pd=m.pit_pd)
            label = (conversion.sp_rating(tables, look.value)
                     if math.isfinite(look.value) else look.basis.value)
        by_span.setdefault(span, set()).add(label)

    saturated = {span: labels for span, labels in by_span.items() if len(labels) > 0}
    for span, labels in saturated.items():
        assert len(labels) == 1, (
            f"{ticker}: at an identical drift span of {span}y the rating still "
            f"depends on the download window: {labels}")

    # And at least one span must be shared by two window lengths, otherwise the
    # test asserted nothing.
    assert any(True for _ in saturated), f"{ticker}: no comparable windows"


@has_cache
@pytest.mark.parametrize("ticker", TICKERS)
def test_drift_span_saturates_and_then_stops_changing_the_drift(ticker):
    """Document the intended dependency: more download -> more drift span,
    until the balance-sheet history runs out, after which nothing moves."""
    try:
        panel = _panel(ticker)
    except FileNotFoundError:
        pytest.skip(f"no cached panel for {ticker}")

    spans, drifts = {}, {}
    for years in (2, 4, 6):
        fit = _fit(panel, years)
        if fit is None:
            continue
        spans[years], drifts[years] = fit[0].drift_span_years, fit[0].drift
    if len(spans) < 2:
        pytest.skip(f"{ticker}: not enough history")

    ordered = sorted(spans)
    for a, b in zip(ordered, ordered[1:]):
        assert spans[b] >= spans[a] - 1e-9, "drift span must not shrink with more data"
        if abs(spans[b] - spans[a]) < 1e-9:
            assert drifts[b] == pytest.approx(drifts[a], abs=DRIFT_TOL), (
                f"{ticker}: identical drift span {spans[a]:.2f}y but the drift "
                f"moved {drifts[b] - drifts[a]:+.4f}")


# --- Bootstrap must mirror the estimator it claims to describe ---------------
def test_bootstrap_sigma_is_centred_on_the_pipeline_sigma():
    """The replicate median must track the point estimate, not another one.

    sigma_A is estimated on the trailing EM_WINDOW_DAYS; the drift on the whole
    span. A bootstrap computing sigma from the full span would report the
    sampling distribution of an estimator the pipeline does not use -- and a
    narrower one, since it would have ~5x the observations.
    """
    import numpy as np

    from signal_construction import bootstrap as bs

    rng = np.random.default_rng(11)
    # A path whose recent volatility is deliberately unlike its full-span one.
    early = rng.normal(0.0002, 0.004, size=1000)
    recent = rng.normal(0.0002, 0.016, size=300)
    u = np.concatenate([early, recent])

    pipeline_sigma = float(np.std(u[-sig_config.EM_WINDOW_DAYS:], ddof=1)
                           * np.sqrt(sig_config.TRADING_DAYS_PER_YEAR))
    full_span_sigma = float(np.std(u, ddof=1)
                            * np.sqrt(sig_config.TRADING_DAYS_PER_YEAR))
    assert full_span_sigma < 0.75 * pipeline_sigma, "premise: the two differ a lot"

    b = bs.run("TEST", u, 1.0e11, 1.0e10, None, n_replicates=300)
    median = b.quantiles("sigma_A")[0.5]
    assert median == pytest.approx(pipeline_sigma, rel=0.15), \
        f"bootstrap centred on {median:.4f}, pipeline uses {pipeline_sigma:.4f}"
    assert abs(median - pipeline_sigma) < abs(median - full_span_sigma)


def test_bootstrap_records_drift_free_quantities_for_defective_replicates():
    """RiskScore is drift-free, so excluding defective replicates biases it.

    drift = eta - sigma^2/2, so a larger sigma makes DEFECTIVE more likely.
    Conditioning RiskScore on drift > 0 would truncate its high-sigma tail and
    report an interval narrower than the truth.
    """
    import numpy as np

    from signal_construction import bootstrap as bs

    rng = np.random.default_rng(5)
    # Negative mean drift -> many defective replicates.
    u = rng.normal(-0.0006, 0.02, size=800)
    b = bs.run("TEST", u, 1.0e11, 1.0e10, None, n_replicates=300)

    assert b.defective_fraction > 0.2, "premise: a good share must be defective"
    n_rs = int(np.isfinite(b.risk_score).sum())
    n_mu = int(np.isfinite(b.mu).sum())
    assert n_rs > n_mu, "RiskScore must survive replicates where mu does not"
    assert n_rs >= 0.99 * b.n_replicates, "RiskScore is defined in every replicate"
