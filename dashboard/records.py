"""The single source of truth for every credit record the project publishes.

Before this module three writers -- the submission workbook, the per-company /
master Excel workbooks, and the tidy long table -- each hand-built their own dict
of credit measures. They disagreed: the Asset sheet omitted the asset value `A`
entirely, split `TiC Risk Score` into two columns, and added a diagnostic
`EM iters`; the others named the same quantities differently; and the default
peak `lambda` (Eq. 3/6) was computed in `measures.py` and reached no output at
all.

Everything now projects from `credit_record()`. A new measure is added here once
and appears everywhere, or is deliberately left out of a schema in one place.

`ASSET_SCHEMA` is the deliverable's contract. Its first 23 entries are the
canonical column set of the reference workbook's `Asset` sheet, in order; a
golden-file test pins them. Two columns follow that set:

  - ``lambda``       the default peak (Eq. 3/6), requested for the deliverable
  - ``Rating Basis`` how the rating was reached (GRID_INTERIOR / ANALYTICAL /
                     OFF_GRID / NOT_APPLICABLE)

`Rating Basis` is a judgement call: a blank `SP Rating` is uninterpretable
without it, and sending a reader to a second sheet to find out why the headline
cell is empty defeats the point of the headline cell. It sits after the canonical
23 so the reference prefix stays byte-comparable.
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from data_cleaning.company import CompanyData

# The reference workbook's `Asset` sheet, in order. Do not reorder: downstream
# consumers diff against this prefix.
CANONICAL_ASSET_COLUMNS: tuple[str, ...] = (
    "Company", "Symbol", "Shares Outstanding", "Last Date", "Last Price",
    "Last Statement Date", "Debt/Short Term", "Debt/Long Term", "Total Debt",
    "Interest Rate", "sigma", "A", "R", "eta", "CCM", "mu", "TiC Risk Score",
    "DD", "EDF", "PIT PD", "TTC PD", "SP Rating", "Outlook",
)

# Appended to the canonical set. See the module docstring.
EXTENDED_ASSET_COLUMNS: tuple[str, ...] = ("lambda", "Rating Basis")

ASSET_SCHEMA: tuple[str, ...] = CANONICAL_ASSET_COLUMNS + EXTENDED_ASSET_COLUMNS

# Diagnostics live here, never on the deliverable sheet.
VALIDATION_SCHEMA: tuple[str, ...] = (
    "Symbol", "Data Status", "EM converged", "EM iters", "sigma_A",
    "Drift regime", "Drift SE", "Drift span (y)", "Rating basis",
    "TTC at floor", "Off-grid", "Statement available at", "Availability method",
    "Warnings",
)


def _panel_last(c: CompanyData, col: str) -> Optional[float]:
    """Latest non-null value of a panel column, or None."""
    if c.panel is None or c.panel.empty or col not in c.panel:
        return None
    s = c.panel[col].dropna()
    return None if s.empty else float(s.iloc[-1])


def _panel_last_value(c: CompanyData, col: str):
    """Latest non-null value of a panel column, without coercing to float."""
    if c.panel is None or c.panel.empty or col not in c.panel:
        return None
    s = c.panel[col].dropna()
    return None if s.empty else s.iloc[-1]


def _total_debt(c: CompanyData) -> Optional[float]:
    """Latest reported Total Debt, else short-term + long-term as a fallback.

    This is the **gross** figure as reported, not the model's default point
    `D = ST + 0.5*LT`. The two are different quantities and the distinction is
    recorded in docs/reconciliation/REPORT.md B1.
    """
    if c.debt_schedule is not None and not c.debt_schedule.empty \
            and "Total Debt" in c.debt_schedule.index:
        row = c.debt_schedule.loc["Total Debt"].dropna()
        if not row.empty:
            return float(row.iloc[0])
    st, lt = _panel_last(c, "ShortTermDebt"), _panel_last(c, "LongTermDebt")
    if st is None and lt is None:
        return None
    return float((st or 0.0) + (lt or 0.0))


def credit_record(c: CompanyData) -> dict[str, Any]:
    """Every published quantity for one company, under one set of names.

    Writers project from this; none of them re-derive a field. Keys are the
    internal names -- schema-specific labels are applied by the projections
    below.
    """
    drift = (c.eta_A - 0.5 * c.sigma_A ** 2
             if c.eta_A is not None and c.sigma_A is not None else None)
    last_date = (c.panel.index[-1].date()
                 if c.panel is not None and not c.panel.empty else None)
    # The statement the model ACTUALLY used on the valuation date, which since
    # #19 is not necessarily the latest one downloaded: a statement inside its
    # filing window has not been published yet and is correctly invisible.
    last_stmt = None
    if c.panel is not None and not c.panel.empty and "StatementPeriodEnd" in c.panel:
        used = c.panel["StatementPeriodEnd"].dropna()
        if not used.empty:
            last_stmt = pd.Timestamp(used.iloc[-1]).date()
    if last_stmt is None and c.debt_schedule is not None and not c.debt_schedule.empty:
        last_stmt = c.debt_schedule.columns[0]
    return {
        # Identity and inputs
        "company": c.name,
        "symbol": c.ticker,
        "shares_outstanding": c.reference_shares,
        "last_date": last_date,
        "last_price": c.last_close,
        "last_statement_date": last_stmt,
        "statement_available_at": _panel_last_value(c, "StatementAvailableAt"),
        "availability_method": c.availability_method,
        "short_term_debt": _panel_last(c, "ShortTermDebt"),
        "long_term_debt": _panel_last(c, "LongTermDebt"),
        "total_debt": _total_debt(c),
        "default_point_debt": _panel_last(c, "DefaultPointDebt_D"),
        "interest_rate": _panel_last(c, "RiskFree_R"),
        "equity": _panel_last(c, "MarketCap_E"),
        # EM outputs
        "sigma_A": c.sigma_A,
        "asset_value": c.asset_value,
        "drift": drift,                 # R = eta - sigma^2/2
        "eta_A": c.eta_A,
        # First-passage measures
        "ccm": c.ccm,
        "mu": c.mu,
        "tic": c.tic,
        "risk_score": c.risk_score,     # 100 * TiC -- the "TiC Risk Score" column
        "lam": c.lam,                   # default peak lambda, Eq. (3)/(6)
        "dd": c.dd,
        "edf": c.edf,
        "pit_pd": c.pit_pd,
        # Conversion
        "ttc_pd": c.ttc_pd,
        "sp_rating": c.sp_rating,
        "outlook": c.outlook,
        "rating_basis": c.rating_basis,
        "ttc_at_floor": c.ttc_at_floor,
        "rating_off_grid": c.rating_off_grid,
        # Provenance / diagnostics -- validation sheet only
        "data_status": c.data_status,
        "drift_regime": c.drift_regime,
        "drift_se": c.drift_se,
        "drift_span_years": c.drift_span_years,
        "em_iters": c.em_iters,
        "em_converged": c.em_converged,
        "em_warnings": c.em_warnings,
    }


def asset_row(c: CompanyData) -> dict[str, Any]:
    """One company projected onto `ASSET_SCHEMA`, in order."""
    r = credit_record(c)
    row = {
        "Company": r["company"],
        "Symbol": r["symbol"],
        "Shares Outstanding": r["shares_outstanding"],
        "Last Date": r["last_date"],
        "Last Price": r["last_price"],
        "Last Statement Date": r["last_statement_date"],
        "Debt/Short Term": r["short_term_debt"],
        "Debt/Long Term": r["long_term_debt"],
        "Total Debt": r["total_debt"],
        "Interest Rate": r["interest_rate"],
        "sigma": r["sigma_A"],
        "A": r["asset_value"],
        "R": r["drift"],
        "eta": r["eta_A"],
        "CCM": r["ccm"],
        "mu": r["mu"],
        "TiC Risk Score": r["risk_score"],
        "DD": r["dd"],
        "EDF": r["edf"],
        "PIT PD": r["pit_pd"],
        "TTC PD": r["ttc_pd"],
        "SP Rating": r["sp_rating"],
        "Outlook": r["outlook"],
        "lambda": r["lam"],
        "Rating Basis": r["rating_basis"],
    }
    assert tuple(row) == ASSET_SCHEMA, "asset_row drifted from ASSET_SCHEMA"
    return row


def validation_row(c: CompanyData) -> dict[str, Any]:
    """One company's diagnostics, projected onto `VALIDATION_SCHEMA`."""
    r = credit_record(c)
    flags: list[str] = []

    if r["data_status"] and r["data_status"] != "OK":
        flags.append(f"data status {r['data_status']}")
    if r["sigma_A"] is None and r["data_status"] in (None, "OK"):
        flags.append("EM/measures did not run")
    if r["em_converged"] is False:
        flags.append("EM did not converge")
    if r["drift_regime"] == "DEFECTIVE":
        flags.append("drift regime DEFECTIVE (Prop. 4.4.1 fails) -> mu/CCM/PIT/"
                     "TTC/rating NOT_APPLICABLE")
    if r["rating_basis"] == "OFF_GRID":
        flags.append("(CCM, mu) outside the conversion grid -> no rating reported")
    if r["ttc_at_floor"]:
        flags.append("TTC PD sits on the grid's 2bp floor -> rating is "
                     "floor-determined, not model-determined")
    flags.extend(r["em_warnings"] or [])

    row = {
        "Symbol": r["symbol"],
        "Data Status": r["data_status"],
        "EM converged": r["em_converged"],
        "EM iters": r["em_iters"],
        "sigma_A": r["sigma_A"],
        "Drift regime": r["drift_regime"],
        "Drift SE": r["drift_se"],
        "Drift span (y)": r["drift_span_years"],
        "Rating basis": r["rating_basis"],
        "TTC at floor": bool(r["ttc_at_floor"]),
        "Off-grid": bool(r["rating_off_grid"]),
        "Statement available at": r["statement_available_at"],
        "Availability method": r["availability_method"],
        "Warnings": "; ".join(flags) if flags else "OK",
    }
    assert tuple(row) == VALIDATION_SCHEMA, "validation_row drifted from VALIDATION_SCHEMA"
    return row


def asset_frame(companies: list[CompanyData]) -> pd.DataFrame:
    """The Asset sheet, guaranteed to carry exactly ASSET_SCHEMA in order."""
    frame = pd.DataFrame([asset_row(c) for c in companies])
    return frame.reindex(columns=list(ASSET_SCHEMA))


def validation_frame(companies: list[CompanyData]) -> pd.DataFrame:
    frame = pd.DataFrame([validation_row(c) for c in companies])
    return frame.reindex(columns=list(VALIDATION_SCHEMA))
