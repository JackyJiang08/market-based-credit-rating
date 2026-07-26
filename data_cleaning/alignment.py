"""Date alignment: fuse three calendars into one model-ready daily panel.

The three series live on different calendars:
  - stock prices       -> trading days (weekdays minus holidays)
  - balance sheets     -> one statement date per quarter
  - interest rates     -> business days, with their own holiday gaps

The credit model needs them on a single row per trading day. We use as-of
(backward) joins: each trading day takes the *most recent* statement and rate
known on or before that day -- exactly how an analyst would have seen the data
in real time (no look-ahead).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, transforms


def total_return_close(close: pd.Series, dividends: pd.Series) -> pd.Series:
    """A reinvested total-return price series anchored at the valuation date.

    The equity series feeding the EM inversion has to satisfy two things at once:

      1. its **log-returns** must be total returns, so an ex-dividend drop is not
         read as a loss of firm value; and
      2. its **last value** must be the real market price, because `A_0`, `D` and
         therefore `ln(A/D)` are all measured on that date.

    The previous construction, `Close + Dividends.cumsum()`, satisfied neither
    cleanly. Its level was `Close` plus every dividend paid *since the first row
    that happened to be downloaded*, so lengthening the history raised every
    value in the series and changed `sigma_A`, `A` and the rating. It also added
    nominal cash to a price level, which mis-scales: a $1 dividend paid five
    years ago is not $1 of today's price.

    This builds the standard reinvested index instead::

        r_t = (Close_t + Div_t) / Close_{t-1} - 1
        I_t = prod(1 + r)  normalised so that I_T = 1
        out = Close_T * I_t

    Each `r_t` depends only on two adjacent days, and the normalisation is to the
    **last** row, so the whole series is invariant to how far back the window
    starts. `out[-1] == Close[-1]` exactly, so the valuation-date market cap is
    the true one.

    Dividends that are `NaN` make the corresponding return unknown. Rather than
    silently treating them as zero, the affected returns propagate `NaN`, and the
    EM step drops those rows and says how many it dropped.
    """
    close = pd.to_numeric(close, errors="coerce")
    div = pd.to_numeric(dividends, errors="coerce")
    if close.empty:
        return close.astype(float)

    if div.isna().all():
        # Nothing is known about distributions, so no total-return series can be
        # built. Returning the price series instead would silently assert the
        # company pays no dividends.
        return pd.Series(np.nan, index=close.index, name="DivAddBackClose")

    prev = close.shift(1)
    daily_tr = (close + div) / prev - 1.0
    # The first row has no prior day, so it is the base of the index rather than
    # a return. That is a definition, not an imputed value.
    if len(daily_tr) > 0:
        daily_tr.iloc[0] = 0.0

    growth = (1.0 + daily_tr).cumprod()
    anchor = growth.dropna()
    if anchor.empty:
        return pd.Series(np.nan, index=close.index, name="DivAddBackClose")

    last_close = close.dropna()
    if last_close.empty:
        return pd.Series(np.nan, index=close.index, name="DivAddBackClose")

    out = growth / anchor.iloc[-1] * float(last_close.iloc[-1])
    out.name = "DivAddBackClose"
    return out


def build_panel(prices: pd.DataFrame,
                reference_shares: float | None,
                balance: pd.DataFrame,
                risk_free: pd.Series | None) -> pd.DataFrame:
    """Construct the aligned daily panel for one company.

    Columns
        Close, AdjClose          : raw and dividend/split-adjusted close
        Dividends                : per-share cash dividend on ex-date (0 otherwise)
        DivAddBackClose          : Close + cumulative dividends added back
                                   (deck slide 61: "add back dividends to stock
                                   prices" so equity reflects total return)
        Shares                   : constant reference share count
        MarketCap_E              : equity value E = Shares x DivAddBackClose
        RawMarketCap             : Shares x Close (actual market cap, reference)
        EquityLogReturn          : ln(MarketCap_E_t / MarketCap_E_{t-1})
        ShortTermDebt, LongTermDebt
        DefaultPointDebt_D       : 1.0*ST + 0.5*LT  (model strike D)
        RiskFree_R               : 1Y Treasury as a decimal (e.g. 0.0498)
        Horizon_T                : credit horizon in years (1.0)

    All statement- and rate-derived columns use as-of (backward) joins so a row
    on date t only ever sees data with observation date <= t (no look-ahead).
    """
    if prices is None or prices.empty:
        return pd.DataFrame()

    panel = pd.DataFrame(index=prices.index.copy())
    panel.index.name = "Date"
    panel["Close"] = prices["Close"]
    panel["AdjClose"] = prices.get("Adj Close", prices["Close"])

    # Dividend add-back (deck slide 61): the equity series must be a total-return
    # series, with no artificial drop on an ex-dividend date.
    #
    # A missing dividend is NOT zero. `NaN` means "we do not know what was paid";
    # `0.0` means "nothing was paid that day". The previous code collapsed the
    # two with `.fillna(0.0)`, so a vendor response with no dividend column was
    # indistinguishable from a company that pays none.
    if "Dividends" in prices:
        panel["Dividends"] = prices["Dividends"]
    else:
        panel["Dividends"] = np.nan
    panel["DivAddBackClose"] = total_return_close(panel["Close"], panel["Dividends"])

    # Equity value E using the constant one-day share count. E feeds the KMV/EM
    # option inversion, so it uses the dividend-added-back price per the deck.
    panel["Shares"] = reference_shares
    if reference_shares:
        panel["MarketCap_E"] = panel["Shares"] * panel["DivAddBackClose"]
        panel["RawMarketCap"] = panel["Shares"] * panel["Close"]
    else:
        panel["MarketCap_E"] = np.nan
        panel["RawMarketCap"] = np.nan

    # Total-return equity log return (used for asset-volatility estimation).
    panel["EquityLogReturn"] = np.log(panel["MarketCap_E"] / panel["MarketCap_E"].shift(1))

    # --- as-of join the quarterly debt onto trading days ---
    term = transforms.split_term_debt(balance)
    if not term.empty:
        term = term.reset_index().rename(columns={"index": "Date"})
        term["Date"] = pd.to_datetime(term["Date"])
        left = panel.reset_index()[["Date"]].sort_values("Date")
        merged = pd.merge_asof(left, term.sort_values("Date"),
                               on="Date", direction="backward")
        merged = merged.set_index("Date")
        panel["ShortTermDebt"] = merged["ShortTermDebt"]
        panel["LongTermDebt"] = merged["LongTermDebt"]
        panel["DefaultPointDebt_D"] = transforms.default_point_debt(
            panel["ShortTermDebt"], panel["LongTermDebt"])
    else:
        panel["ShortTermDebt"] = np.nan
        panel["LongTermDebt"] = np.nan
        panel["DefaultPointDebt_D"] = np.nan

    # --- as-of join the risk-free rate onto trading days ---
    if risk_free is not None and not risk_free.empty:
        rf = risk_free.rename("RiskFree_R").reset_index()
        rf.columns = ["Date", "RiskFree_R"]
        rf["Date"] = pd.to_datetime(rf["Date"])
        rf["RiskFree_R"] = rf["RiskFree_R"] / 100.0  # percent -> decimal
        left = panel.reset_index()[["Date"]].sort_values("Date")
        merged = pd.merge_asof(left, rf.sort_values("Date"),
                               on="Date", direction="backward")
        panel["RiskFree_R"] = merged.set_index("Date")["RiskFree_R"]
    else:
        panel["RiskFree_R"] = np.nan

    panel["Horizon_T"] = config.HORIZON_YEARS
    return panel
