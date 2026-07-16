"""Submission workbook matching the instructor's `Asset` sheet schema.

Writes one timestamped workbook per run (never overwriting a prior submission)
with two sheets:
  - `Asset`      : one row per company, the instructor's column layout.
  - `validation` : sanity-check flags per company (EM convergence, sigma range,
                   off-grid conversion, missing data).

Outputs are generated artifacts derived from the instructor's conversion tables
and are git-ignored (see .gitignore); they are for coursework use only.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

import numpy as np
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from data_cleaning.company import CompanyData
from signal_construction import config as sig_config

LOG = logging.getLogger("pfpa.submission")

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(_PROJECT_ROOT, "outputs")

HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def _last(series_frame: pd.DataFrame, col: str):
    if series_frame is None or series_frame.empty or col not in series_frame:
        return None
    s = series_frame[col].dropna()
    return None if s.empty else s.iloc[-1]


def _total_debt(c: CompanyData):
    """Latest reported Total Debt, else short-term + long-term as a fallback."""
    if not c.debt_schedule.empty and "Total Debt" in c.debt_schedule.index:
        val = c.debt_schedule.loc["Total Debt"].iloc[0]  # latest period column
        if pd.notna(val):
            return float(val)
    st, lt = _last(c.panel, "ShortTermDebt"), _last(c.panel, "LongTermDebt")
    if st is None and lt is None:
        return None
    return float((st or 0.0) + (lt or 0.0))


def _asset_row(c: CompanyData) -> dict:
    """One company as the instructor's Asset-sheet columns."""
    last_date = c.panel.index[-1].date() if not c.panel.empty else None
    last_stmt = c.debt_schedule.columns[0] if not c.debt_schedule.empty else None
    # R = realized asset log-return over the horizon = eta_A - sigma_A^2/2,
    # the quantity that enters DD (deck DD = [ln(A/D) + (eta_A - sigma^2/2)]/sigma).
    drift = (c.eta_A - 0.5 * c.sigma_A ** 2
             if c.eta_A is not None and c.sigma_A is not None else None)
    return {
        "Company": c.name,
        "Symbol": c.ticker,
        "Shares Outstanding": c.reference_shares,
        "Last Date": last_date,
        "Last Price": c.last_close,
        "Last Statement": last_stmt,
        "Debt/Short Term": _last(c.panel, "ShortTermDebt"),
        "Debt/Long Term": _last(c.panel, "LongTermDebt"),
        "Total Debt": _total_debt(c),
        "Interest Rate": _last(c.panel, "RiskFree_R"),
        "sigma A": c.sigma_A,
        "R": drift,
        "eta": c.eta_A,
        "CCM": c.ccm,
        "mu": c.mu,
        "TiC": c.tic,
        "Risk Score": c.risk_score,
        "DD": c.dd,
        "EDF": c.edf,
        "PIT PD": c.pit_pd,
        "TTC PD": c.ttc_pd,
        "SP Rating": c.sp_rating,
        "Outlook": c.outlook,
        "EM iters": c.em_iters,
    }


def _validation_row(c: CompanyData) -> dict:
    flags: list[str] = []
    if c.sigma_A is None:
        flags.append("EM/measures did not run")
    if c.em_converged is False:
        flags.append("EM did not converge")
    if c.sigma_A is not None and not (
            sig_config.SIGMA_A_WARN_LOW <= c.sigma_A <= sig_config.SIGMA_A_WARN_HIGH):
        flags.append(f"sigma_A={c.sigma_A:.0%} outside typical band")
    if c.rating_off_grid:
        flags.append("(CCM, mu) off conversion grid -> edge-clamped")
    if c.sp_rating in (None, "n/a"):
        flags.append("no S&P rating (conversion tables missing?)")
    flags.extend(c.em_warnings or [])
    return {
        "Symbol": c.ticker,
        "EM converged": c.em_converged,
        "EM iters": c.em_iters,
        "sigma_A": c.sigma_A,
        "Off-grid": bool(c.rating_off_grid),
        "Warnings": "; ".join(flags) if flags else "OK",
    }


def _format(ws) -> None:
    ws.freeze_panes = "B2"
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center")
    for col in ws.columns:
        letter = get_column_letter(col[0].column)
        longest = max((len(str(x.value)) for x in col if x.value is not None), default=10)
        ws.column_dimensions[letter].width = min(max(longest + 2, 12), 40)


def write_submission(companies: list[CompanyData],
                     filename: str | None = None) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if filename is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"submission_{stamp}.xlsx"
    path = os.path.join(OUTPUT_DIR, filename)

    asset = pd.DataFrame([_asset_row(c) for c in companies])
    validation = pd.DataFrame([_validation_row(c) for c in companies])

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        asset.to_excel(writer, sheet_name="Asset", index=False)
        validation.to_excel(writer, sheet_name="validation", index=False)
        _format(writer.book["Asset"])
        _format(writer.book["validation"])

    LOG.info("submission workbook -> %s", os.path.relpath(path, _PROJECT_ROOT))
    return path
