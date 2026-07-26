"""Pure data transformations (no I/O): statement parsing, the debt schedule,
the default-point debt rule, and the reference share count.

Every function here is deterministic and unit-testable.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from . import config


def _norm(s: object) -> str:
    """Normalise a label for fuzzy matching (lowercase, no whitespace)."""
    return "".join(str(s).lower().split())


def pick_row(frame: pd.DataFrame, candidates: Iterable[str]) -> Optional[pd.Series]:
    """Return the first frame row whose index matches a candidate label."""
    row, _ = pick_row_named(frame, candidates)
    return row


def pick_row_named(frame: pd.DataFrame, candidates: Iterable[str]
                   ) -> tuple[Optional[pd.Series], Optional[str]]:
    """As `pick_row`, but also return which candidate label matched.

    Two companies in the same batch can have the same metric sourced from
    different line items, and nothing recorded which. That is the single largest
    input difference against a peer implementation -- ORCL and AMZN differ from
    it by exactly their capital-lease rows, purely because we take the
    lease-inclusive candidate first (#16).
    """
    if frame is None or frame.empty:
        return None, None
    norm_index = {_norm(idx): idx for idx in frame.index}
    for cand in candidates:
        hit = norm_index.get(_norm(cand))
        if hit is not None:
            return frame.loc[hit], str(hit)
    return None, None


def trim_to_window(frame: pd.DataFrame, cutoff: datetime) -> pd.DataFrame:
    """Keep statement columns (period-end dates) within the trailing window.

    Always retains at least the two most recent periods so a sparse company
    never yields an empty statement.
    """
    if frame is None or frame.empty:
        return pd.DataFrame()
    cols = list(frame.columns)
    try:
        keep = [c for c in cols if pd.to_datetime(c) >= pd.Timestamp(cutoff)]
    except Exception:  # noqa: BLE001
        keep = cols
    if len(keep) < 2:
        keep = cols[:2]
    return frame[keep]


def build_debt_schedule(balance: pd.DataFrame) -> pd.DataFrame:
    """Extract the six requested debt & liability line items as a time series
    (metrics as rows, period-end dates as ISO-string columns).
    """
    if balance is None or balance.empty:
        return pd.DataFrame()
    rows: dict[str, pd.Series] = {}
    for metric, candidates in config.BALANCE_SHEET_MAP.items():
        series = pick_row(balance, candidates)
        if series is not None:
            rows[metric] = series
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows).T
    out.columns = [pd.to_datetime(c).strftime("%Y-%m-%d") for c in out.columns]
    return out


def reference_shares(market_cap: Optional[float], last_close: Optional[float],
                     fallback: Optional[float]) -> tuple[Optional[float], str]:
    """Shares outstanding via the one-day method, and how it was obtained.

    Pick one day (the latest), shares = market cap / price, then hold this
    constant when computing daily market cap = shares x price. For dual-class
    names (e.g. DELL) this recovers the *total* shares so market cap reconciles,
    which a single share-class figure would not.

    Returns `(shares, method)`. `docs/TIMING_PROTOCOL.md` §3 permits a constant
    reference-share assumption "only when it is explicitly identified as a
    modelling assumption and its reference date is stored", so the caller
    records both the method and the date it belongs to.

    The fallback matters more than it looks: `sharesOutstanding` is a *single
    share class*, so for a dual-class issuer it is a different quantity from
    market cap / price -- exactly the case the primary method exists to handle.
    It is labelled distinctly so that substitution is never invisible.
    """
    if market_cap and last_close:
        return market_cap / last_close, "market_cap_over_price"
    if fallback:
        return fallback, "shares_outstanding_single_class"
    return None, "unavailable"


def split_term_debt(balance: pd.DataFrame) -> pd.DataFrame:
    """Short-term and long-term debt per period, with robust fallbacks.

    Returns a frame indexed by period-end Timestamp with columns
    ['ShortTermDebt', 'LongTermDebt']. Some issuers (and all banks) do not
    report a clean current/non-current split, so:
      - missing short-term debt  -> max(Total Debt - Long-term Debt, 0)
      - missing long-term debt   -> max(Total Debt - Short-term Debt, 0)
    """
    if balance is None or balance.empty:
        return pd.DataFrame(columns=["ShortTermDebt", "LongTermDebt"])

    total, f_total = pick_row_named(balance, config.BALANCE_SHEET_MAP["Total Debt"])
    short, f_short = pick_row_named(balance, config.BALANCE_SHEET_MAP["Short-term / Current Debt"])
    long_, f_long = pick_row_named(balance, config.BALANCE_SHEET_MAP["Long-term Debt"])

    periods = balance.columns
    st = short.reindex(periods) if short is not None else pd.Series(index=periods, dtype=float)
    lt = long_.reindex(periods) if long_ is not None else pd.Series(index=periods, dtype=float)
    tot = total.reindex(periods) if total is not None else pd.Series(index=periods, dtype=float)

    # Complements, BEFORE clipping, so a contradictory source is visible rather
    # than silently flattened to zero (#16). `Total < Long-term` means the two
    # rows disagree; `.clip(lower=0)` used to turn that into `ShortTermDebt = 0`,
    # which is what produced PNC's 36% default-point difference against a peer
    # and made its entire barrier depend on the long-term weight.
    st_complement = tot - lt
    lt_complement = tot - st
    st_contradictory = st.isna() & st_complement.notna() & (st_complement < 0)
    lt_contradictory = lt.isna() & lt_complement.notna() & (lt_complement < 0)

    st_imputed = st.isna() & st_complement.notna()
    lt_imputed = lt.isna() & lt_complement.notna()

    st = st.where(st.notna(), st_complement.clip(lower=0))
    lt = lt.where(lt.notna(), lt_complement.clip(lower=0))

    out = pd.DataFrame({
        "ShortTermDebt": st,
        "LongTermDebt": lt,
        # Provenance, per period. Which line item supplied each leg, whether it
        # was imputed from the complement, and whether that complement was
        # negative (i.e. the source contradicts itself).
        "ShortTermDebtSource": np.where(st_imputed, "imputed:Total-LongTerm",
                                        f_short or "missing"),
        "LongTermDebtSource": np.where(lt_imputed, "imputed:Total-ShortTerm",
                                       f_long or "missing"),
        "TotalDebtSource": f_total or "missing",
        "DebtSourceContradictory": (st_contradictory | lt_contradictory),
    })
    out.index = pd.to_datetime(out.index)
    return out.sort_index()


def union_balance_sheets(quarterly: pd.DataFrame,
                         annual: pd.DataFrame) -> pd.DataFrame:
    """Union two balance sheets on their period-end columns, quarterly winning.

    Both frames are line items x period-end columns. Where a period end appears
    in both, the quarterly figure is kept (it is the finer observation of the
    same date). Where it appears only in the annual sheet -- typically further
    back than the free-tier quarterly history reaches -- the annual column is
    carried in. No value is invented and no date is shifted, so the as-of join
    downstream still only ever sees real statements at their own period end.
    """
    q = quarterly if quarterly is not None else pd.DataFrame()
    a = annual if annual is not None else pd.DataFrame()
    if q.empty:
        return a
    if a.empty:
        return q
    extra = [c for c in a.columns if c not in set(q.columns)]
    if not extra:
        return q
    merged = q.join(a[extra], how="outer")
    # Columns are period-end dates; keep them newest-first as the rest of the
    # code assumes (e.g. `debt_schedule.columns[0]` is the latest period).
    return merged[sorted(merged.columns, reverse=True)]


def statement_available_at(quarterly: pd.DataFrame,
                           annual: pd.DataFrame) -> dict:
    """Map each statement period end to the date it is assumed to be public.

    `period_end` is when the accounting period closed; `available_at` is the
    earliest date the figure could legitimately have been known. They differ by
    the filing lag, and `docs/TIMING_PROTOCOL.md` §3 is explicit that the first
    is not a substitute for the second.

    A period end present in the quarterly sheet gets the 10-Q lag; one that only
    appears in the annual sheet gets the longer 10-K lag. Returns
    `{period_end: available_at}` as Timestamps.
    """
    out: dict = {}
    a_cols = set(annual.columns) if annual is not None and not annual.empty else set()
    q_cols = set(quarterly.columns) if quarterly is not None and not quarterly.empty else set()

    for col in sorted(q_cols | a_cols):
        period_end = pd.to_datetime(col, errors="coerce")
        if pd.isna(period_end):
            continue
        lag = (config.QUARTERLY_FILING_LAG_DAYS if col in q_cols
               else config.ANNUAL_FILING_LAG_DAYS)
        out[period_end] = period_end + pd.Timedelta(days=lag)
    return out


def default_point_debt(short_term: pd.Series, long_term: pd.Series) -> pd.Series:
    """D = 100% short-term debt + 50% long-term debt (the model's strike).

    A row with **neither** figure known -- typically a trading day before the
    earliest statement we hold -- yields `NaN`, not `0`. Filling it with zero
    would assert the firm had no debt on that date, which is a fabricated value
    (engineering rule 2) and, because the EM step filters on `D > 0`, silently
    truncated the estimation window instead of reporting a missing input.
    Backfilling it from the earliest statement is not an option either: that is
    a later observation, forbidden by docs/TIMING_PROTOCOL.md §2.
    """
    both_missing = short_term.isna() & long_term.isna()
    d = (config.SHORT_TERM_DEBT_WEIGHT * short_term.fillna(0)
         + config.LONG_TERM_DEBT_WEIGHT * long_term.fillna(0))
    return d.where(~both_missing)


# --------------------------------------------------------------------------- #
# Default-point variants (financial firms)
# --------------------------------------------------------------------------- #
def default_point_variants(balance: pd.DataFrame,
                           short_term: pd.Series,
                           long_term: pd.Series) -> dict:
    """Every default-point definition, side by side, per period.

    The shipped convention `ST + 0.5*LT` looks at *debt*. For a deposit-funded
    bank that is a small fraction of what the firm owes -- PNC's is about $33bn
    against $539bn of total liabilities -- so two liability-based alternatives
    are offered for comparison:

      standard                      1.0*ST + 0.5*LT   (the deck's rule)
      total_liabilities             all liabilities treated as the barrier
      total_liabilities_ex_deposits liabilities less deposits

    Returns `{variant: Series}`, with a variant absent from the mapping when its
    inputs are not in the source. Notably, the free-tier balance sheet carries
    no deposits line for PNC, so `total_liabilities_ex_deposits` is **not
    computable** there -- reported as absent rather than silently equal to
    `total_liabilities`.
    """
    out: dict = {"standard": default_point_debt(short_term, long_term)}

    tl, _ = pick_row_named(balance, config.BALANCE_SHEET_MAP["Total Liabilities"])
    if tl is not None:
        tl_series = pd.to_numeric(tl, errors="coerce")
        tl_series.index = pd.to_datetime(tl_series.index)
        out["total_liabilities"] = tl_series.sort_index()

        dep, _ = pick_row_named(balance, config.DEPOSIT_ROWS)
        if dep is not None:
            dep_series = pd.to_numeric(dep, errors="coerce")
            dep_series.index = pd.to_datetime(dep_series.index)
            net = (tl_series.sort_index() - dep_series.sort_index()).clip(lower=0)
            out["total_liabilities_ex_deposits"] = net
    return out
