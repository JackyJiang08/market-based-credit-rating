"""Compatibility orchestration: fetch -> transform -> align -> model -> write.

The active project scope currently ends after alignment. Model and publishing
calls remain here temporarily so the existing CLI keeps working while the
four-layer workflow is separated into stage-specific commands.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Sequence

import pandas as pd
import yfinance as yf

from raw_data_architecture import cache
from raw_data_architecture import config as raw_config
from raw_data_architecture import errors as raw_errors
from raw_data_architecture import sources

from . import alignment, persistence, sectors, transforms
from . import config as clean_config
from .company import CompanyData

LOG = logging.getLogger(__name__)


@dataclass
class RunConfig:
    tickers: Sequence[str]
    years: int = raw_config.DEFAULT_YEARS
    include_rates: bool = True
    run_credit_model: bool = True
    run_bootstrap: bool = True
    # Concurrent company fetches. 1 keeps the historical sequential behavior
    # (with the polite inter-ticker delay); >1 uses a thread pool with
    # per-company isolation, so one failure cannot abort the run.
    workers: int = 1

    @property
    def cutoff_date(self) -> datetime:
        return datetime.now() - timedelta(days=365 * self.years + 7)


def fetch_company(ticker: str, cfg: RunConfig, rates: pd.DataFrame) -> Optional[CompanyData]:
    ticker = ticker.strip().upper()
    if not ticker:
        return None
    LOG.info("=== %s ===", ticker)
    tk = yf.Ticker(ticker)
    data = CompanyData(ticker=ticker)

    # --- company info ---
    # Each acquisition records why it failed. The worst status seen wins, so a
    # rate limit is never reported as "this company has no data".
    statuses: list[raw_errors.DataStatus] = []
    info = cache.load_info(ticker)
    if info is None:
        try:
            info = sources.get_info(tk)
            if not info:
                raise raw_errors.NoDataError("Ticker.info returned nothing")
            cache.save_info(ticker, info)
        except raw_errors.DataSourceError as exc:
            info = {}
            statuses.append(exc.status)
            LOG.warning("  info unavailable (%s): %s", exc.status.value, exc)
    data.name = info.get("longName") or info.get("shortName") or ticker
    data.currency = info.get("currency", "")
    data.financial_currency = info.get("financialCurrency", "")
    data.sector = info.get("sector", "")
    data.industry = info.get("industry", "")
    data.market_cap = info.get("marketCap")
    data.shares_traded_class = info.get("sharesOutstanding")
    data.dividend_rate = info.get("dividendRate")
    data.dividend_yield = info.get("dividendYield")

    # --- prices ---
    prices = cache.load_prices(ticker)
    if prices is None:
        try:
            prices = sources.get_history(tk, cfg.cutoff_date)
            if prices is None or prices.empty:
                raise raw_errors.NoDataError("no price history returned")
            cache.save_prices(ticker, prices)
        except raw_errors.DataSourceError as exc:
            prices = pd.DataFrame()
            statuses.append(exc.status)
            LOG.warning("  prices unavailable (%s): %s", exc.status.value, exc)
    if not prices.empty:
        if getattr(prices.index, "tz", None) is not None:
            prices.index = prices.index.tz_localize(None)
        # The vendor sometimes appends a placeholder row for the current session
        # with a missing Close. Left in, it makes last_close NaN, which
        # propagates through reference_shares into an all-NaN equity series and
        # starves the EM step. Keep only days that actually priced.
        dropped = int(prices["Close"].isna().sum())
        if dropped:
            prices = prices[prices["Close"].notna()]
            LOG.info("  dropped %d price row(s) with no Close", dropped)
        if prices.empty:
            LOG.warning("  no priced days in window; skipping price-derived fields")
        if "Adj Close" in prices and "Close" in prices:
            prices["Div/Split Adj Factor"] = (prices["Adj Close"] / prices["Close"]).round(6)
    if not prices.empty:
        data.prices = prices
        data.last_close = float(prices["Close"].iloc[-1])
        LOG.info("  prices: %d rows (%s -> %s)", len(prices),
                 prices.index.min().date(), prices.index.max().date())

    # Reference shares via the one-day method (mktcap / price).
    data.reference_shares, data.shares_method = transforms.reference_shares(
        data.market_cap, data.last_close, data.shares_traded_class)
    # TIMING_PROTOCOL §3: the constant-share assumption is only permitted when
    # its reference date is stored. That date is the last priced day, because
    # that is the day market cap and price were both observed.
    if not prices.empty:
        data.shares_reference_date = prices.index[-1].date().isoformat()
    if data.shares_method == "shares_outstanding_single_class":
        LOG.warning("  shares: market cap unavailable; fell back to "
                    "sharesOutstanding, which is one share class only")

    # --- dividends ---
    if not prices.empty and "Dividends" in prices:
        divs = prices.loc[prices["Dividends"] > 0, ["Dividends"]].copy()
        if not divs.empty:
            divs.index.name = "Date"
            data.dividends = divs

    # --- statements ---
    stmts = cache.load_statements(ticker)
    if stmts is None:
        try:
            stmts = sources.get_statements(tk)
            if not any(v is not None and not v.empty for v in (stmts or {}).values()):
                raise raw_errors.NoDataError("no statements returned")
            cache.save_statements(ticker, stmts)
        except raw_errors.DataSourceError as exc:
            stmts = {}
            statuses.append(exc.status)
            LOG.warning("  statements unavailable (%s): %s", exc.status.value, exc)
    data.q_income = transforms.trim_to_window(stmts.get("q_income"), cfg.cutoff_date)
    data.q_balance = transforms.trim_to_window(stmts.get("q_balance"), cfg.cutoff_date)
    data.q_cashflow = transforms.trim_to_window(stmts.get("q_cashflow"), cfg.cutoff_date)
    data.a_income = transforms.trim_to_window(stmts.get("a_income"), cfg.cutoff_date)
    data.a_balance = transforms.trim_to_window(stmts.get("a_balance"), cfg.cutoff_date)
    data.a_cashflow = transforms.trim_to_window(stmts.get("a_cashflow"), cfg.cutoff_date)

    # Union the quarterly and annual balance sheets on their period-end columns.
    # Yahoo's free tier returns only ~5-7 quarters, which caps how far back the
    # default point D is known and therefore how long a drift span the EM step
    # can use. Annual statements reach slightly further back and are real
    # observations at their own period end, so unioning them extends the usable
    # history without backfilling anything (docs/TIMING_PROTOCOL.md §2).
    # Quarterly wins on any shared period end, being the finer observation.
    balance_for_debt = transforms.union_balance_sheets(data.q_balance, data.a_balance)
    data.debt_schedule = transforms.build_debt_schedule(balance_for_debt)
    if not data.debt_schedule.empty:
        LOG.info("  debt schedule: %d metrics x %d periods", *data.debt_schedule.shape)

    # Resolve the acquisition outcome. Severity order matters: a rate limit or
    # transport failure means we do not KNOW whether the company has data, so it
    # must never be reported as NO_DATA -- which is a statement about the
    # company, not about us.
    if not statuses:
        data.data_status = raw_errors.DataStatus.OK.value
    else:
        severity = [raw_errors.DataStatus.RATE_LIMITED,
                    raw_errors.DataStatus.SOURCE_ERROR,
                    raw_errors.DataStatus.DELISTED,
                    raw_errors.DataStatus.NO_DATA]
        data.data_status = next(s.value for s in severity if s in statuses)
    if data.data_status != raw_errors.DataStatus.OK.value:
        LOG.warning("  data status: %s", data.data_status)

    # --- date-aligned model panel ---
    rf_series = None
    if rates is not None and not rates.empty and raw_config.RISK_FREE_SERIES in rates:
        rf_series = rates.set_index("Date")[raw_config.RISK_FREE_SERIES]
    # available_at per statement period end (period end + conservative filing
    # lag), so the as-of join below cannot see an unfiled statement.
    available_at = transforms.statement_available_at(data.q_balance, data.a_balance)
    data.panel = alignment.build_panel(
        data.prices, data.reference_shares, balance_for_debt, rf_series,
        available_at=available_at)
    data.availability_method = clean_config.AVAILABILITY_METHOD

    # --- applicability gate (financial firms) ---
    # The first-passage construction assumes the barrier is debt. For a
    # deposit-funded bank it is not, and PNC shows the size of the gap: a
    # default point of ~$33bn against ~$539bn of total liabilities. Rating it
    # anyway produces a confident-looking investment-grade letter.
    firm_type = sectors.classify(ticker, data.sector, data.industry)
    status, reason = sectors.applicability(firm_type)
    data.firm_type = firm_type.value
    data.model_applicable = status is sectors.Applicability.APPLICABLE
    data.applicability_reason = reason
    if not data.model_applicable:
        LOG.warning("  %s: %s (%s) -- the structural model is not meaningful "
                    "for this firm type; measures are still computed and "
                    "reported, the rating is not", status.value, reason,
                    firm_type.value)

    # --- unit-consistency gate: statements must be in the price currency ---
    # An ADR prices in USD while filing in its home currency, so E arrives in
    # one unit and D in another. TM made this loud (EM raised: A <= D by a
    # factor of JPY); TSM/BABA/SAP/ASML were silently RATED on the same
    # mismatch, which is worse. No FX conversion is attempted -- converting
    # statements at some chosen rate would be a fabricated input (rule 2) --
    # the company is gated and the mismatch stated. Unlike the firm-type gate
    # this also suppresses the measures: they would be unit-corrupt, not
    # merely inapplicable.
    if (data.model_applicable and data.currency and data.financial_currency
            and data.currency != data.financial_currency):
        data.model_applicable = False
        data.applicability_reason = "REPORTING_CURRENCY_MISMATCH"
        data.em_error = (f"statements report in {data.financial_currency}, "
                         f"prices in {data.currency}; EM would mix units")
        LOG.warning("  MODEL_NOT_APPLICABLE: REPORTING_CURRENCY_MISMATCH "
                    "(%s statements vs %s prices) -- EM and measures skipped",
                    data.financial_currency, data.currency)

    # --- EM asset-value estimation (Layer 3) ---
    _em_asset_path = None
    _em_debt_last = None
    _conversion_tables = None
    if (cfg.run_credit_model and not data.panel.empty
            and data.applicability_reason != "REPORTING_CURRENCY_MISMATCH"):
        # Import the modelling layer only when used, so Layer 1/2 tooling and
        # CLI help do not require SciPy.
        from signal_construction import config as sig_config, em, measures

        # Pass the full drift window; em.estimate takes sigma_A from its
        # trailing EM_WINDOW_DAYS and the drift from the whole span.
        window = data.panel.tail(sig_config.DRIFT_WINDOW_DAYS)
        try:
            res = em.estimate(window["MarketCap_E"], window["DefaultPointDebt_D"],
                              window["RiskFree_R"])
            _em_asset_path = res.asset_values.to_numpy()
            _em_debt_last = res.debt_last
            data.sigma_A = res.sigma_A
            data.eta_A = res.eta_A
            data.asset_value = res.asset_last
            data.em_iters = res.n_iter
            data.em_converged = res.converged
            data.em_warnings = res.warnings
            data.drift_se = res.drift_se
            data.drift_span_years = res.drift_span_years
            LOG.info("  EM: sigma_A=%.1f%% (%dd)  eta_A=%.1f%% (%.1fy, SE=%.1f%%)  "
                     "A=%.4g  iters=%d",
                     res.sigma_A * 100, sig_config.EM_WINDOW_DAYS,
                     res.eta_A * 100, res.drift_span_years, res.drift_se * 100,
                     res.asset_last, res.n_iter)

            # Derived first-passage credit measures (Eq. 11-14).
            m = measures.compute(res.sigma_A, res.asset_last, res.debt_last, res.eta_A)
            data.mu, data.ccm, data.tic, data.risk_score = m.mu, m.ccm, m.tic, m.risk_score
            data.lam, data.dd, data.edf, data.pit_pd = m.lam, m.dd, m.edf, m.pit_pd
            data.drift_regime = m.regime.value
            data.drift_t_stat = (m.drift / res.drift_se
                                 if res.drift_se else float("nan"))
            data.weakly_identified = measures.is_weakly_identified(
                m.drift, res.drift_se)
            if data.weakly_identified and m.regime is measures.DriftRegime.VALID:
                LOG.warning(
                    "  WEAKLY_IDENTIFIED: drift t=%.2f (|t| < %.1f) -- mu and CCM "
                    "divide by a drift indistinguishable from zero",
                    data.drift_t_stat, sig_config.WEAK_IDENTIFICATION_T)
            if m.regime is measures.DriftRegime.DEFECTIVE:
                LOG.warning(
                    "  drift regime DEFECTIVE: eta-sigma^2/2 = %+.4f <= 0 "
                    "(Prop. 4.4.1 fails); mu/CCM/PIT/TTC/rating are NOT_APPLICABLE",
                    m.drift)
            LOG.info("  measures: RiskScore=%.2f  CCM=%.3f  mu=%.1f  DD=%.2f  "
                     "EDF=%.4f  PIT_PD=%.4f",
                     m.risk_score, m.ccm, m.mu, m.dd, m.edf, m.pit_pd)
        except (em.EMError, ValueError) as exc:
            data.em_error = f"{type(exc).__name__}: {exc}"
            LOG.warning("  EM/measures failed: %s", exc)

    # --- market-based applicability (ADR 0003, revision 1) ---
    # Runs after EM because it needs the market-implied asset value. The firm
    # must clear the barrier under the most conservative debt weight (w = 1.0,
    # total debt), so applicability cannot depend on the arbitrary 0.5.
    if data.model_applicable and data.asset_value is not None:
        total_debt_w1 = None
        if not data.panel.empty and {"ShortTermDebt", "LongTermDebt"} <= set(data.panel.columns):
            st = data.panel["ShortTermDebt"].dropna()
            lt = data.panel["LongTermDebt"].dropna()
            if not st.empty and not lt.empty:
                total_debt_w1 = float(st.iloc[-1]) + float(lt.iloc[-1])
        status, reason = sectors.market_applicability(data.asset_value, total_debt_w1)
        if status is not sectors.Applicability.APPLICABLE:
            data.model_applicable = False
            data.applicability_reason = reason
            LOG.warning("  %s: %s -- A=%.4g does not clear the w=1.0 barrier "
                        "%.4g; the letter would be a statement about the debt "
                        "weight, not the firm", status.value, reason,
                        data.asset_value, total_debt_w1)

    # --- PIT -> TTC -> S&P conversion (local tables; skipped if tables absent) ---
    if data.ccm is not None and data.mu is not None:
        from signal_construction import conversion

        try:
            tables = conversion.load_tables()
            _conversion_tables = tables
            # pit_pd is PD_A of Eq. (27); without it an off-grid point
            # cannot be converted analytically.
            ttc = conversion.ttc_pd(tables, data.ccm, data.mu,
                                    pit_pd=data.pit_pd)
            data.ttc_pd = ttc.value
            data.rating_basis = ttc.basis.value
            data.rating_off_grid = ttc.off_grid
            data.ttc_at_floor = ttc.at_floor
            data.sp_risk_score = (float(ttc.risk_score)
                                  if ttc.risk_score == ttc.risk_score else None)
            data.rating_determination = conversion.classify_determination(
                ttc.basis, ttc.at_floor, ttc.risk_score).value
            if not data.model_applicable:
                data.sp_rating = None
                data.outlook = None
                data.rating_determination = "MODEL_NOT_APPLICABLE"
                LOG.warning("  rating suppressed: %s", data.applicability_reason)
            elif ttc.basis in (conversion.RatingBasis.GRID_INTERIOR,
                               conversion.RatingBasis.ANALYTICAL):
                data.sp_rating = conversion.sp_rating(tables, ttc.value)
                data.outlook = conversion.outlook(data.pit_pd, ttc.value)
                LOG.info("  rating: TTC_PD=%.4f  S&P=%-4s Outlook=%+.4f  "
                         "basis=%s%s",
                         data.ttc_pd, data.sp_rating, data.outlook,
                         data.rating_basis,
                         "  (TTC at grid floor -- floor-determined)"
                         if ttc.at_floor else "")
            else:
                # No letter. An off-grid or not-applicable point has no rating,
                # and the clamped edge value is not a substitute for one.
                data.sp_rating = None
                data.outlook = None
                LOG.warning("  rating: %s -- no letter reported (CCM=%.4g, mu=%.4g)",
                            data.rating_basis, data.ccm, data.mu)
        except FileNotFoundError as exc:
            LOG.warning("  TTC/S&P skipped: %s", exc)

    # --- uncertainty propagation (bootstrap) ---
    if (cfg.run_bootstrap and data.sigma_A is not None
            and data.asset_value is not None and _em_asset_path is not None):
        from signal_construction import bootstrap as bs

        try:
            import numpy as _np

            u = _np.diff(_np.log(_em_asset_path))
            b = bs.run(ticker, u, data.asset_value, _em_debt_last,
                       _conversion_tables,
                       n_replicates=sig_config.BOOTSTRAP_REPLICATES,
                       seed=sig_config.BOOTSTRAP_SEED)
            lo_q, hi_q = sig_config.BOOTSTRAP_INTERVAL
            data.boot_sigma_lo, data.boot_sigma_hi = (
                b.quantiles("sigma_A", (lo_q, hi_q))[lo_q],
                b.quantiles("sigma_A", (lo_q, hi_q))[hi_q])
            data.boot_defective_fraction = b.defective_fraction
            best, worst, width = b.notch_interval(lo_q, hi_q)
            data.rating_interval_low = best
            data.rating_interval_high = worst
            data.rating_interval_notches = width
            LOG.info("  bootstrap: %d reps, block=%d, defective in %.0f%% of "
                     "replicates, rating interval %s..%s (%d notches)",
                     b.n_replicates, b.block_length,
                     100 * b.defective_fraction, best, worst, width)
        except Exception as exc:  # noqa: BLE001 - bootstrap is diagnostic
            LOG.warning("  bootstrap skipped: %s", exc)

    # Persist raw + cleaned datasets per company (git-ignored data trees).
    try:
        persistence.save_company(data)
    except Exception as exc:  # noqa: BLE001
        LOG.warning("  persistence failed: %s", exc)
    return data


def _fmt(x: Optional[float]) -> str:
    return f"{x:.4f}" if x is not None and pd.notna(x) else "n/a"


def _log_vol_comparison(companies: list[CompanyData]) -> None:
    """Log asset volatility by sector -- a cross-check that riskier/tech names
    carry higher sigma_A than defensive/financial names."""
    rows = [(c.ticker, c.sector or "?", c.sigma_A)
            for c in companies if c.sigma_A is not None]
    if not rows:
        return
    rows.sort(key=lambda x: x[2], reverse=True)
    LOG.info("Asset-volatility cross-check (high -> low):")
    for ticker, sector, sigma in rows:
        LOG.info("    %-6s %-22s sigma_A=%5.1f%%", ticker, sector[:22], sigma * 100)


def run(cfg: RunConfig) -> list[CompanyData]:
    # Layer 4 remains a compatibility publisher while only Layers 1/2 are
    # active. Keeping this import local prevents a dashboard dependency from
    # becoming part of the cleaning package's import contract.
    from dashboard import config as dashboard_config
    from dashboard import excel, longtable

    os.makedirs(dashboard_config.OUTPUT_DIR, exist_ok=True)
    LOG.info("Universe: %s | window: %dy | rates: %s | credit-model: %s",
             ", ".join(cfg.tickers), cfg.years, cfg.include_rates, cfg.run_credit_model)

    # Resolve any company-name inputs to tickers up front; skip unresolvable
    # ones with an actionable message rather than aborting the whole run.
    resolved: list[str] = []
    for raw_query in cfg.tickers:
        # A plain symbol goes straight through -- config files carry exact
        # tickers, and probing each over the network would cost one vendor
        # call per name. Only free-text company names need the resolver.
        if sources.looks_like_symbol(raw_query):
            resolved.append(raw_query.strip().upper())
            continue
        try:
            resolved.append(sources.resolve_ticker(raw_query))
        except sources.TickerResolutionError as exc:
            LOG.error("Skipping '%s': %s", raw_query, exc)
    if not resolved:
        LOG.error("No resolvable tickers/companies in %s", list(cfg.tickers))
        return []

    rates = pd.DataFrame()
    if cfg.include_rates:
        cached_rates = cache.load_rates()
        if cached_rates is not None:
            rates = cached_rates
        else:
            rates = sources.fetch_rates(cfg.years)
            cache.save_rates(rates)

    # One company end to end, isolated: an exception is recorded and returned,
    # never propagated, so one failure cannot abort the batch.
    def _one(ticker: str):
        try:
            data = fetch_company(ticker, cfg, rates)
            if data is not None:
                excel.write_company_workbook(data, cfg.years)
            return ticker, data, None
        except Exception as exc:  # noqa: BLE001 - isolation is the contract
            LOG.error("Ticker %s aborted: %s", ticker, exc)
            return ticker, None, exc

    companies: list[CompanyData] = []
    failures: list[tuple[str, Exception]] = []
    if cfg.workers > 1:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=cfg.workers) as pool:
            results = list(pool.map(_one, resolved))
    else:
        results = []
        for i, ticker in enumerate(resolved):
            results.append(_one(ticker))
            if i < len(resolved) - 1:
                time.sleep(raw_config.INTER_TICKER_DELAY_SECONDS)
    for ticker, data, exc in results:
        if data is not None:
            companies.append(data)
        elif exc is not None:
            failures.append((ticker, exc))
    if failures:
        LOG.error("%d ticker(s) raised instead of degrading -- by this "
                  "codebase's rules that is a bug, not a data condition: %s",
                  len(failures), ", ".join(t for t, _ in failures))

    if companies:
        _log_vol_comparison(companies)
        excel.write_master_workbook(companies, rates)
        longtable.write_long_table(longtable.build_long_table(companies, rates))
        from dashboard import submission
        submission.write_submission(companies)

    LOG.info("Done. %d/%d companies succeeded. Output: %s",
             len(companies), len(resolved), dashboard_config.OUTPUT_DIR)
    return companies
