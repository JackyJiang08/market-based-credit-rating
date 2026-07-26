"""Data-source adapters: Yahoo Finance (equities) and FRED (macro rates).

This layer is the only place that talks to the network. It returns plain
pandas objects so the rest of the pipeline is testable without I/O.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from io import StringIO
from typing import Callable, Optional

import pandas as pd
import requests
import yfinance as yf

from . import provider_config as config
from .errors import DataSourceError, RateLimitedError, SourceUnavailableError, classify

LOG = logging.getLogger(__name__)

# Waiting can only help these two: the source refused us, or the transport
# failed. A delisted symbol and a successful-but-empty answer are terminal.
RETRYABLE = (RateLimitedError, SourceUnavailableError)


# --------------------------------------------------------------------------- #
# Resilience: retry Yahoo calls with exponential backoff
# --------------------------------------------------------------------------- #
def with_retry(label: str) -> Callable:
    """Decorate a network call to retry with exponential backoff."""

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last: Optional[DataSourceError] = None
            for attempt in range(1, config.MAX_RETRIES + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001 - vendor raises bare types
                    last = classify(exc)
                    # A delisted symbol will not become listed by waiting, and a
                    # successful empty answer is not a failure. Only throttling
                    # and transport problems are worth retrying.
                    if not isinstance(last, RETRYABLE):
                        LOG.warning("%s: %s -- not retryable", label, last)
                        raise last from exc
                    if attempt == config.MAX_RETRIES:
                        break
                    wait = config.BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                    LOG.warning(
                        "%s failed (attempt %d/%d): %s -- retry in %.0fs",
                        label,
                        attempt,
                        config.MAX_RETRIES,
                        last,
                        wait,
                    )
                    time.sleep(wait)
            LOG.error("%s permanently failed: %s", label, last)
            raise last  # type: ignore[misc]

        return wrapper

    return decorator


# --------------------------------------------------------------------------- #
# Yahoo Finance (equities)
# --------------------------------------------------------------------------- #
class TickerResolutionError(ValueError):
    """Raised when a company name / query cannot be resolved to one ticker."""


def looks_like_symbol(query: str) -> bool:
    """True when the query is a plain ticker token (no search needed).

    Config files carry exact symbols; probing each one over the network before
    a batch would cost one vendor call per name for no information. A wrong
    symbol still fails loudly in acquisition with a per-company status.
    """
    q = (query or "").strip().upper()
    return (
        bool(q) and " " not in q and len(q) <= 6 and all(c.isalnum() or c in ".-" for c in q)
    )


def resolve_ticker(query: str) -> str:
    """Resolve a ticker symbol or company name to a single Yahoo ticker.

    A plain symbol is validated and returned as-is. A company name is resolved
    via Yahoo search, preferring an exact/space-insensitive name match and
    otherwise the top equity quote. Ambiguity or no match raises
    ``TickerResolutionError`` with an actionable message.
    """
    q = (query or "").strip()
    if not q:
        raise TickerResolutionError("Empty ticker/company query.")

    # Treat a short ticker-like token (no spaces, <=5 chars, optional .-suffix)
    # as a symbol. Keeping this tight avoids mis-firing on words like "Costco".
    candidate = q.upper()
    looks_like_symbol = (
        " " not in q
        and len(candidate) <= 5
        and all(c.isalnum() or c in ".-" for c in candidate)
    )
    if looks_like_symbol:
        try:
            info = yf.Ticker(candidate).info or {}
            if info.get("symbol") or info.get("shortName") or info.get("regularMarketPrice"):
                return str(info.get("symbol", candidate)).upper()
        except Exception as exc:  # noqa: BLE001 - vendor raises bare types
            err = classify(exc)
            # A rate limit here is not evidence that the symbol is wrong, and
            # falling through to a name search would resolve it to something
            # else entirely. Only an actual lookup miss may fall through.
            if isinstance(err, RateLimitedError):
                raise err from exc
            LOG.debug(
                "symbol probe for %s failed (%s); trying name search",
                candidate,
                err.status.value,
            )

    try:
        quotes = getattr(yf.Search(q, max_results=10), "quotes", []) or []
    except Exception as exc:  # noqa: BLE001
        raise TickerResolutionError(f"Search failed for '{query}': {exc}") from exc

    equities = [x for x in quotes if x.get("quoteType") == "EQUITY" and x.get("symbol")]
    if not equities:
        raise TickerResolutionError(
            f"No equity match for '{query}'. Try the exact ticker symbol."
        )

    def _norm(s: str) -> str:
        return "".join(str(s).lower().split())

    def _name(x: dict) -> str:
        return _norm(x.get("shortname") or x.get("longname") or "")

    nq = _norm(q)

    # Prefer an exact normalized name match; otherwise every equity whose name
    # contains the query. Resolve only when a single distinct symbol remains --
    # never silently return a wrong ticker (e.g. "Intuit" vs "Intuitive Surgical").
    exact = {str(x["symbol"]).upper() for x in equities if _name(x) == nq}
    contains = {str(x["symbol"]).upper() for x in equities if nq in _name(x)}
    hits = exact or contains

    # Prefer primary listings (plain symbols) over foreign cross-listings /
    # CEDEARs, which carry an exchange suffix like ".BA" / ".V" / ".F".
    primary = {s for s in hits if "." not in s}
    resolved_set = primary or hits

    if len(resolved_set) == 1:
        return next(iter(resolved_set))
    if len(resolved_set) > 1:
        listing = ", ".join(
            f"{str(x['symbol']).upper()} ({x.get('shortname') or x.get('longname')})"
            for x in equities
            if str(x["symbol"]).upper() in resolved_set
        )
        raise TickerResolutionError(
            f"'{query}' is ambiguous ({listing}). Use the exact ticker symbol."
        )
    raise TickerResolutionError(
        f"No confident equity match for '{query}'. Use the exact ticker symbol."
    )


@with_retry("Ticker.info")
def get_info(tk: yf.Ticker) -> dict:
    return tk.info or {}


@with_retry("Ticker.history")
def get_history(tk: yf.Ticker, start: datetime) -> pd.DataFrame:
    """Daily OHLC + Adj Close + dividend/split actions from `start` onward."""
    return tk.history(start=start.strftime("%Y-%m-%d"), auto_adjust=False, actions=True)


@with_retry("Ticker.statements")
def get_statements(tk: yf.Ticker) -> dict[str, pd.DataFrame]:
    """Quarterly and annual income, balance-sheet, and cash-flow statements."""
    return {
        "q_income": tk.quarterly_income_stmt,
        "q_balance": tk.quarterly_balance_sheet,
        "q_cashflow": tk.quarterly_cashflow,
        "a_income": tk.income_stmt,
        "a_balance": tk.balance_sheet,
        "a_cashflow": tk.cashflow,
    }


# --------------------------------------------------------------------------- #
# FRED (macro rates) -- official CSV API, no key required
# --------------------------------------------------------------------------- #
def fetch_fred_series(series_id: str, start: datetime, end: datetime) -> pd.DataFrame:
    """Download one FRED series as a tidy [Date, <series_id>] frame."""
    url = (
        "https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id={series_id}&cosd={start:%Y-%m-%d}&coed={end:%Y-%m-%d}"
    )
    resp = requests.get(url, timeout=config.REQUEST_TIMEOUT)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    # Locate the date column by name rather than by position: a layout change
    # at the source would otherwise silently mislabel a column.
    named = [c for c in df.columns if str(c).strip().lower() in ("observation_date", "date")]
    if named:
        date_col = named[0]
    elif len(df.columns) >= 2:
        date_col = df.columns[0]
        LOG.warning(
            "FRED %s: no recognised date column in %s; falling back to " "the first column %r",
            series_id,
            list(df.columns),
            date_col,
        )
    else:
        raise SourceUnavailableError(
            f"FRED {series_id}: unexpected CSV layout {list(df.columns)}"
        )
    df = df.rename(columns={date_col: "Date"})
    df["Date"] = pd.to_datetime(df["Date"])
    df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
    return df.dropna(subset=[series_id]).reset_index(drop=True)


def fetch_rates(years: int) -> pd.DataFrame:
    """Combined daily frame of all configured FRED series, columns = series ids."""
    end = datetime.now()
    start = end - timedelta(days=365 * years + 7)
    merged: Optional[pd.DataFrame] = None
    for series_id in config.FRED_SERIES:
        try:
            df = fetch_fred_series(series_id, start, end)
            merged = df if merged is None else merged.merge(df, on="Date", how="outer")
            LOG.info("FRED %s: %d observations", series_id, len(df))
        except Exception as exc:  # noqa: BLE001
            LOG.error("FRED %s failed: %s", series_id, exc)
    if merged is None:
        return pd.DataFrame()
    return merged.sort_values("Date").reset_index(drop=True)
