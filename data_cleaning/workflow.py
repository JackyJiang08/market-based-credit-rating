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

from raw_data_architecture import config as raw_config
from raw_data_architecture import sources

from . import alignment, persistence, transforms
from .company import CompanyData

LOG = logging.getLogger("pfpa.workflow")


@dataclass
class RunConfig:
    tickers: Sequence[str]
    years: int = raw_config.DEFAULT_YEARS
    include_rates: bool = True
    run_credit_model: bool = True

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
    try:
        info = sources.get_info(tk)
    except Exception:  # noqa: BLE001
        info = {}
    data.name = info.get("longName") or info.get("shortName") or ticker
    data.currency = info.get("currency", "")
    data.sector = info.get("sector", "")
    data.industry = info.get("industry", "")
    data.market_cap = info.get("marketCap")
    data.shares_traded_class = info.get("sharesOutstanding")
    data.dividend_rate = info.get("dividendRate")
    data.dividend_yield = info.get("dividendYield")

    # --- prices ---
    try:
        prices = sources.get_history(tk, cfg.cutoff_date)
    except Exception:  # noqa: BLE001
        prices = pd.DataFrame()
    if not prices.empty:
        prices.index = prices.index.tz_localize(None)
        if "Adj Close" in prices and "Close" in prices:
            prices["Div/Split Adj Factor"] = (prices["Adj Close"] / prices["Close"]).round(6)
        data.prices = prices
        data.last_close = float(prices["Close"].iloc[-1])
        LOG.info("  prices: %d rows (%s -> %s)", len(prices),
                 prices.index.min().date(), prices.index.max().date())

    # Reference shares via the one-day method (mktcap / price).
    data.reference_shares = transforms.reference_shares(
        data.market_cap, data.last_close, data.shares_traded_class)

    # --- dividends ---
    if not prices.empty and "Dividends" in prices:
        divs = prices.loc[prices["Dividends"] > 0, ["Dividends"]].copy()
        if not divs.empty:
            divs.index.name = "Date"
            data.dividends = divs

    # --- statements ---
    try:
        stmts = sources.get_statements(tk)
    except Exception:  # noqa: BLE001
        stmts = {}
    data.q_income = transforms.trim_to_window(stmts.get("q_income"), cfg.cutoff_date)
    data.q_balance = transforms.trim_to_window(stmts.get("q_balance"), cfg.cutoff_date)
    data.q_cashflow = transforms.trim_to_window(stmts.get("q_cashflow"), cfg.cutoff_date)
    data.a_income = transforms.trim_to_window(stmts.get("a_income"), cfg.cutoff_date)
    data.a_balance = transforms.trim_to_window(stmts.get("a_balance"), cfg.cutoff_date)
    data.a_cashflow = transforms.trim_to_window(stmts.get("a_cashflow"), cfg.cutoff_date)

    balance_for_debt = data.q_balance if not data.q_balance.empty else data.a_balance
    data.debt_schedule = transforms.build_debt_schedule(balance_for_debt)
    if not data.debt_schedule.empty:
        LOG.info("  debt schedule: %d metrics x %d periods", *data.debt_schedule.shape)

    # --- date-aligned model panel ---
    rf_series = None
    if rates is not None and not rates.empty and raw_config.RISK_FREE_SERIES in rates:
        rf_series = rates.set_index("Date")[raw_config.RISK_FREE_SERIES]
    data.panel = alignment.build_panel(
        data.prices, data.reference_shares, balance_for_debt, rf_series)

    # --- EM asset-value estimation (Layer 3) ---
    if cfg.run_credit_model and not data.panel.empty:
        # Import the modelling layer only when used, so Layer 1/2 tooling and
        # CLI help do not require SciPy.
        from signal_construction import config as sig_config, em, measures

        window = data.panel.tail(sig_config.EM_WINDOW_DAYS)
        try:
            res = em.estimate(window["MarketCap_E"], window["DefaultPointDebt_D"],
                              window["RiskFree_R"])
            data.sigma_A = res.sigma_A
            data.eta_A = res.eta_A
            data.asset_value = res.asset_last
            data.em_iters = res.n_iter
            data.em_converged = res.converged
            data.em_warnings = res.warnings
            LOG.info("  EM: sigma_A=%.1f%%  eta_A=%.1f%%  A=%.4g  iters=%d",
                     res.sigma_A * 100, res.eta_A * 100, res.asset_last, res.n_iter)

            # Derived first-passage credit measures (Eq. 11-14).
            m = measures.compute(res.sigma_A, res.asset_last, res.debt_last, res.eta_A)
            data.mu, data.ccm, data.tic, data.risk_score = m.mu, m.ccm, m.tic, m.risk_score
            data.lam, data.dd, data.edf, data.pit_pd = m.lam, m.dd, m.edf, m.pit_pd
            LOG.info("  measures: RiskScore=%.2f  CCM=%.3f  mu=%.1f  DD=%.2f  "
                     "EDF=%.4f  PIT_PD=%.4f",
                     m.risk_score, m.ccm, m.mu, m.dd, m.edf, m.pit_pd)
        except (em.EMError, ValueError) as exc:
            LOG.warning("  EM/measures failed: %s", exc)

    # --- PIT -> TTC -> S&P conversion (local tables; skipped if IP absent) ---
    if data.ccm is not None and data.mu is not None:
        from signal_construction import conversion

        try:
            tables = conversion.load_tables()
            ttc = conversion.ttc_pd(tables, data.ccm, data.mu)
            data.ttc_pd = ttc.value
            data.sp_rating = conversion.sp_rating(tables, ttc.value)
            data.outlook = conversion.outlook(data.pit_pd, ttc.value)
            LOG.info("  rating: TTC_PD=%.4f  S&P=%-4s Outlook=%+.4f%s",
                     data.ttc_pd, data.sp_rating, data.outlook,
                     "  (off-grid)" if ttc.off_grid else "")
        except FileNotFoundError as exc:
            LOG.warning("  TTC/S&P skipped: %s", exc)

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
    carry higher sigma_A than defensive/financial names (deck intuition)."""
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
        try:
            resolved.append(sources.resolve_ticker(raw_query))
        except sources.TickerResolutionError as exc:
            LOG.error("Skipping '%s': %s", raw_query, exc)
    if not resolved:
        LOG.error("No resolvable tickers/companies in %s", list(cfg.tickers))
        return []

    rates = sources.fetch_rates(cfg.years) if cfg.include_rates else pd.DataFrame()

    companies: list[CompanyData] = []
    for i, ticker in enumerate(resolved):
        try:
            data = fetch_company(ticker, cfg, rates)
            if data is not None:
                excel.write_company_workbook(data, cfg.years)
                companies.append(data)
        except Exception as exc:  # noqa: BLE001
            LOG.error("Ticker %s aborted: %s", ticker, exc)
        if i < len(resolved) - 1:
            time.sleep(raw_config.INTER_TICKER_DELAY_SECONDS)

    if companies:
        _log_vol_comparison(companies)
        excel.write_master_workbook(companies, rates)
        longtable.write_long_table(longtable.build_long_table(companies, rates))

    LOG.info("Done. %d/%d companies succeeded. Output: %s",
             len(companies), len(resolved), dashboard_config.OUTPUT_DIR)
    return companies
