"""Read-through disk cache for the acquisition layer.

Every artifact the pipeline downloads (per-ticker info / price history /
statements, and the shared FRED rates frame) can be persisted under
``data/cache/`` and reused, which makes a batch **resumable** (a rerun only
refetches what is missing), makes the demo and the test suite runnable
**offline** (a fixture subset is committed), and takes the vendor's rate
limits out of the inner loop.

Layout (one directory per ticker; parquet for frames, JSON for dicts):

    data/cache/<TICKER>/meta.json          fetched_at (UTC), source
    data/cache/<TICKER>/info.json
    data/cache/<TICKER>/prices.parquet
    data/cache/<TICKER>/stmt_<name>.parquet   (q_income, a_balance, ...)
    data/cache/_rates/rates.parquet + meta.json

Environment switches:
    MDT_CACHE_DIR      override the cache root (tests point this at tmp)
    MDT_CACHE_OFF=1    bypass the cache entirely (always fetch, never write)
    MDT_CACHE_REFRESH=1  ignore existing entries but write fresh ones

Timing note (docs/TIMING_PROTOCOL.md): a cache entry is a **vintage
snapshot** -- ``fetched_at`` records when this system ingested the data
(`ingested_at` in protocol terms). Reusing an entry from an earlier day is
allowed (that is what makes offline fixtures work) but is WARNED about, so a
batch that silently mixes vintages is visible in the log. Force one vintage
with MDT_CACHE_REFRESH=1.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

LOG = logging.getLogger(__name__)

from creditrating._paths import REPO_ROOT as _ROOT  # noqa: E501
STATEMENT_KEYS = ("q_income", "q_balance", "q_cashflow",
                  "a_income", "a_balance", "a_cashflow")


CANONICAL_DATETIME_UNIT = "ns"


def _normalize_datetimes(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce every datetime index/column to the canonical unit (ns).

    The one dtype chokepoint for the cache boundary. Parquet round-trips come
    back as datetime64[us] on pandas >= 2/3 while fresh vendor downloads are
    datetime64[ns]; pandas 3 refuses to merge the two (MergeError in the
    as-of join). Everything leaving this module is therefore [ns], tz
    preserved, regardless of pandas version or storage format.
    """
    if isinstance(df.index, pd.DatetimeIndex) and hasattr(df.index, "as_unit"):
        df.index = df.index.as_unit(CANONICAL_DATETIME_UNIT)
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_datetime64_any_dtype(s) and hasattr(s, "dt"):
            try:
                df[col] = s.dt.as_unit(CANONICAL_DATETIME_UNIT)
            except AttributeError:  # pandas 1.x: ns is the only unit
                pass
    if isinstance(df.columns, pd.DatetimeIndex) and hasattr(df.columns, "as_unit"):
        df.columns = df.columns.as_unit(CANONICAL_DATETIME_UNIT)
    return df


def cache_dir() -> str:
    return os.environ.get("MDT_CACHE_DIR", os.path.join(_ROOT, "data", "cache"))


def enabled() -> bool:
    return os.environ.get("MDT_CACHE_OFF", "0") != "1"


def refresh() -> bool:
    return os.environ.get("MDT_CACHE_REFRESH", "0") == "1"


def _tdir(ticker: str) -> str:
    return os.path.join(cache_dir(), ticker.upper())


def _write_meta(path: str) -> None:
    meta = {"fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "yahoo/fred"}
    with open(os.path.join(path, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh)


def _warn_if_stale(path: str, label: str) -> None:
    try:
        with open(os.path.join(path, "meta.json"), encoding="utf-8") as fh:
            fetched = json.load(fh)["fetched_at"]
        age_days = (datetime.now(timezone.utc)
                    - datetime.strptime(fetched, "%Y-%m-%dT%H:%M:%SZ")
                    .replace(tzinfo=timezone.utc)).days
        if age_days >= 1:
            LOG.warning("%s: cache entry is %dd old (fetched %s) -- a mixed-"
                        "vintage batch is possible; MDT_CACHE_REFRESH=1 forces "
                        "one vintage", label, age_days, fetched)
    except (OSError, KeyError, ValueError):
        pass


# --------------------------------------------------------------------------- #
# Per-ticker artifacts
# --------------------------------------------------------------------------- #
def load_info(ticker: str) -> Optional[dict]:
    p = os.path.join(_tdir(ticker), "info.json")
    if not enabled() or refresh() or not os.path.exists(p):
        return None
    _warn_if_stale(_tdir(ticker), f"{ticker} info")
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def save_info(ticker: str, info: dict) -> None:
    if not enabled():
        return
    d = _tdir(ticker)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "info.json"), "w", encoding="utf-8") as fh:
        json.dump(info, fh, default=str)
    _write_meta(d)


def load_prices(ticker: str) -> Optional[pd.DataFrame]:
    p = os.path.join(_tdir(ticker), "prices.parquet")
    if not enabled() or refresh() or not os.path.exists(p):
        return None
    _warn_if_stale(_tdir(ticker), f"{ticker} prices")
    return _normalize_datetimes(pd.read_parquet(p))


def save_prices(ticker: str, prices: pd.DataFrame) -> None:
    if not enabled() or prices is None or prices.empty:
        return
    d = _tdir(ticker)
    os.makedirs(d, exist_ok=True)
    prices.to_parquet(os.path.join(d, "prices.parquet"))
    _write_meta(d)


def load_statements(ticker: str) -> Optional[dict[str, pd.DataFrame]]:
    d = _tdir(ticker)
    if not enabled() or refresh():
        return None
    out: dict[str, pd.DataFrame] = {}
    found = False
    for key in STATEMENT_KEYS:
        p = os.path.join(d, f"stmt_{key}.parquet")
        if os.path.exists(p):
            df = pd.read_parquet(p)
            # Statement columns are period-end dates, stored as ISO strings
            # (parquet requires string column names).
            df.columns = pd.to_datetime(df.columns)
            out[key] = _normalize_datetimes(df)
            found = True
        else:
            out[key] = pd.DataFrame()
    if not found:
        return None
    _warn_if_stale(d, f"{ticker} statements")
    return out


def save_statements(ticker: str, stmts: dict[str, pd.DataFrame]) -> None:
    if not enabled() or not stmts:
        return
    frames = {k: v for k, v in stmts.items()
              if v is not None and not v.empty}
    if not frames:
        return
    d = _tdir(ticker)
    os.makedirs(d, exist_ok=True)
    for key, df in frames.items():
        out = df.copy()
        out.columns = [pd.Timestamp(c).isoformat() for c in out.columns]
        out.to_parquet(os.path.join(d, f"stmt_{key}.parquet"))
    _write_meta(d)


# --------------------------------------------------------------------------- #
# Shared rates frame
# --------------------------------------------------------------------------- #
def load_rates() -> Optional[pd.DataFrame]:
    p = os.path.join(cache_dir(), "_rates", "rates.parquet")
    if not enabled() or refresh() or not os.path.exists(p):
        return None
    _warn_if_stale(os.path.dirname(p), "FRED rates")
    return _normalize_datetimes(pd.read_parquet(p))


def save_rates(rates: pd.DataFrame) -> None:
    if not enabled() or rates is None or rates.empty:
        return
    d = os.path.join(cache_dir(), "_rates")
    os.makedirs(d, exist_ok=True)
    rates.to_parquet(os.path.join(d, "rates.parquet"))
    _write_meta(d)
