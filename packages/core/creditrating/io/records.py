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

import os
import subprocess
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

from ..data import cleaning_config as clean_config
from ..data.company import CompanyData
from ..model import config as sig_config

# The reference workbook's `Asset` sheet, in order. Do not reorder: downstream
# consumers diff against this prefix.
CANONICAL_ASSET_COLUMNS: tuple[str, ...] = (
    "Company",
    "Symbol",
    "Shares Outstanding",
    "Last Date",
    "Last Price",
    "Last Statement Date",
    "Debt/Short Term",
    "Debt/Long Term",
    "Total Debt",
    "Interest Rate",
    "sigma",
    "A",
    "R",
    "eta",
    "CCM",
    "mu",
    "TiC Risk Score",
    "DD",
    "EDF",
    "PIT PD",
    "TTC PD",
    "SP Rating",
    "Outlook",
)

# Appended to the canonical set. See the module docstring.
# Deliberate additions beyond the reference workbook's 23 columns. Kept as a
# separate block, after the canonical set, so the reference prefix stays
# byte-comparable and the deviation is explicit. Documented on the workbook's
# README sheet.
EXTENDED_ASSET_COLUMNS: tuple[str, ...] = (
    "lambda",
    "Rating Basis",
    "Rating Determination",
    "Firm Type",
    "Model Applicable",
    "Applicability Reason",
    "Drift SE",
    "Drift t",
    "Weakly Identified",
    "Rating Interval Low",
    "Rating Interval High",
    "Rating Interval Notches",
)

ASSET_SCHEMA: tuple[str, ...] = CANONICAL_ASSET_COLUMNS + EXTENDED_ASSET_COLUMNS

# Diagnostics live here, never on the deliverable sheet.
VALIDATION_SCHEMA: tuple[str, ...] = (
    "Symbol",
    "Data Status",
    "EM converged",
    "EM iters",
    "sigma_A",
    "Drift regime",
    "Drift SE",
    "Drift t",
    "Drift span (y)",
    "Rating basis",
    "TTC at floor",
    "At scale top",
    "Off-grid",
    "Rating determination",
    "S&P RiskScore",
    "Bootstrap defective %",
    "sigma 5%",
    "sigma 95%",
    "Rating interval",
    "Convention span (notches)",
    "Debt field provenance",
    "Statement available at",
    "Availability method",
    "Warnings",
)

# Per-company rating span (in notches) of the debt-weight convention sweep,
# w in {0, 0.25, 0.5, 0.75, 1.0} on the long-term leg plus the prior statement
# vintage. Source: docs/reconciliation/convention_sweep.py, run 2026-07-26 at
# the same data vintage as history/13-14 (prices through the 2026-07-24 close);
# the full table is in the README results section. A recorded sweep result with
# its date, not a live computation -- regenerate with the script if the data
# vintage moves. A ticker not swept reports no span rather than a guess.
CONVENTION_SWEEP_DATE = "2026-07-26"
CONVENTION_SPANS: dict[str, int] = {
    "COST": 1,
    "KO": 1,
    "DELL": 4,
    "ORCL": 5,
    "PNC": 5,
    "WMT": 1,
    "INTU": 0,
    "AMZN": 2,
    "T": 7,
    "KHC": 0,
}


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
    if (
        c.debt_schedule is not None
        and not c.debt_schedule.empty
        and "Total Debt" in c.debt_schedule.index
    ):
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
    drift = (
        c.eta_A - 0.5 * c.sigma_A**2 if c.eta_A is not None and c.sigma_A is not None else None
    )
    last_date = c.panel.index[-1].date() if c.panel is not None and not c.panel.empty else None
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
        "st_debt_source": _panel_last_value(c, "ShortTermDebtSource"),
        "lt_debt_source": _panel_last_value(c, "LongTermDebtSource"),
        "debt_source_contradictory": _panel_last_value(c, "DebtSourceContradictory"),
        "short_term_debt": _panel_last(c, "ShortTermDebt"),
        "long_term_debt": _panel_last(c, "LongTermDebt"),
        "total_debt": _total_debt(c),
        "default_point_debt": _panel_last(c, "DefaultPointDebt_D"),
        "interest_rate": _panel_last(c, "RiskFree_R"),
        "equity": _panel_last(c, "MarketCap_E"),
        # EM outputs
        "sigma_A": c.sigma_A,
        "asset_value": c.asset_value,
        "drift": drift,  # R = eta - sigma^2/2
        "eta_A": c.eta_A,
        # First-passage measures
        "ccm": c.ccm,
        "mu": c.mu,
        "tic": c.tic,
        "risk_score": c.risk_score,  # 100 * TiC -- the "TiC Risk Score" column
        "lam": c.lam,  # default peak lambda, Eq. (3)/(6)
        "dd": c.dd,
        "edf": c.edf,
        "pit_pd": c.pit_pd,
        # Conversion
        "ttc_pd": c.ttc_pd,
        "sp_rating": c.sp_rating,
        "outlook": c.outlook,
        "rating_basis": c.rating_basis,
        "rating_determination": c.rating_determination,
        "firm_type": c.firm_type,
        "model_applicable": c.model_applicable,
        "applicability_reason": c.applicability_reason,
        "drift_t_stat": c.drift_t_stat,
        "weakly_identified": c.weakly_identified,
        "boot_sigma_lo": c.boot_sigma_lo,
        "boot_sigma_hi": c.boot_sigma_hi,
        "boot_defective_fraction": c.boot_defective_fraction,
        "rating_interval_low": c.rating_interval_low,
        "rating_interval_high": c.rating_interval_high,
        "rating_interval_notches": c.rating_interval_notches,
        "sp_risk_score": c.sp_risk_score,
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
        "em_error": c.em_error,
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
        "Rating Determination": r["rating_determination"],
        "Firm Type": r["firm_type"],
        "Model Applicable": r["model_applicable"],
        "Applicability Reason": r["applicability_reason"],
        "Drift SE": r["drift_se"],
        "Drift t": r["drift_t_stat"],
        "Weakly Identified": r["weakly_identified"],
        "Rating Interval Low": r["rating_interval_low"],
        "Rating Interval High": r["rating_interval_high"],
        "Rating Interval Notches": r["rating_interval_notches"],
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
        flags.append(
            "EM/measures did not run" + (f": {r['em_error']}" if r.get("em_error") else "")
        )
    if r["em_converged"] is False:
        flags.append("EM did not converge")
    if r["drift_regime"] == "DEFECTIVE":
        flags.append(
            "drift regime DEFECTIVE (Prop. 4.4.1 fails) -> mu/CCM/PIT/"
            "TTC/rating NOT_APPLICABLE"
        )
    if r["rating_basis"] == "OFF_GRID":
        flags.append("(CCM, mu) outside the conversion grid -> no rating reported")
    if r["rating_determination"] == "PINNED_AT_FLOOR":
        flags.append(
            "TTC PD sits on the grid's 2bp floor -> rating is "
            "floor-determined, not model-determined"
        )
    if r["rating_determination"] == "PINNED_AT_SCALE_TOP":
        flags.append(
            "RiskScore below the best published grade -> rating is "
            "scale-determined, not model-determined"
        )
    if r["model_applicable"] is False:
        from ..data import sectors as _sectors

        code = r["applicability_reason"]
        flags.append(
            f"MODEL_NOT_APPLICABLE ({code}): "
            f"{_sectors.REASON_TEXT.get(code, 'see docs/adr/0003')}"
        )
    if r["weakly_identified"] and r["drift_regime"] == "VALID":
        t = r["drift_t_stat"]
        flags.append(
            f"WEAKLY_IDENTIFIED: drift t={t:.2f}, |t| < 2 -- mu and CCM divide "
            "by a drift indistinguishable from zero; read the rating interval, "
            "not the point rating"
        )
    if (r["rating_interval_notches"] or 0) > 3:
        flags.append(
            f"rating interval spans {r['rating_interval_notches']} notches "
            f"({r['rating_interval_low']}..{r['rating_interval_high']})"
        )
    flags.extend(r["em_warnings"] or [])

    interval = None
    if r["rating_interval_low"] is not None or r["rating_interval_high"] is not None:
        interval = (
            f"{r['rating_interval_low']}..{r['rating_interval_high']} "
            f"({r['rating_interval_notches']} notches)"
        )
    prov_bits = []
    if r["st_debt_source"] is not None:
        prov_bits.append(f"ST: {r['st_debt_source']}")
    if r["lt_debt_source"] is not None:
        prov_bits.append(f"LT: {r['lt_debt_source']}")
    if r["debt_source_contradictory"]:
        prov_bits.append("CONTRADICTORY (Total < LT in source)")

    row = {
        "Symbol": r["symbol"],
        "Data Status": r["data_status"],
        "EM converged": r["em_converged"],
        "EM iters": r["em_iters"],
        "sigma_A": r["sigma_A"],
        "Drift regime": r["drift_regime"],
        "Drift SE": r["drift_se"],
        "Drift t": r["drift_t_stat"],
        "Drift span (y)": r["drift_span_years"],
        "Rating basis": r["rating_basis"],
        "TTC at floor": bool(r["ttc_at_floor"]),
        "At scale top": r["rating_determination"] == "PINNED_AT_SCALE_TOP",
        "Off-grid": bool(r["rating_off_grid"]),
        "Rating determination": r["rating_determination"],
        "S&P RiskScore": r["sp_risk_score"],
        "Bootstrap defective %": (
            100.0 * r["boot_defective_fraction"]
            if r["boot_defective_fraction"] is not None
            else None
        ),
        "sigma 5%": r["boot_sigma_lo"],
        "sigma 95%": r["boot_sigma_hi"],
        "Rating interval": interval,
        "Convention span (notches)": CONVENTION_SPANS.get(r["symbol"]),
        "Debt field provenance": "; ".join(prov_bits) if prov_bits else None,
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


# --------------------------------------------------------------------------- #
# Ratings sheet: the presentation rule, applied
# --------------------------------------------------------------------------- #
RATINGS_SCHEMA: tuple[str, ...] = (
    "Rank",
    "Symbol",
    "Company",
    "TiC Risk Score",
    "Rating (with interval)",
    "Rating Determination",
    "Drift t",
    "Weakly Identified",
    "Convention span (notches)",
)


def rating_with_interval(r: dict[str, Any]) -> str:
    """The letter, never bare: interval attached, or the reason there is none."""
    if r["sp_rating"]:
        iv = ""
        if r["rating_interval_low"] is not None:
            iv = f" ({r['rating_interval_low']}..{r['rating_interval_high']})"
        return f"{r['sp_rating']}{iv}"
    if r["model_applicable"] is False:
        return f"MODEL_NOT_APPLICABLE ({r['applicability_reason']})"
    if r["rating_determination"] == "NOT_RATED":
        return "NOT_RATED (defective drift, Prop. 4.4.1)"
    return "NOT_RATED"


def ratings_frame(companies: list[CompanyData]) -> pd.DataFrame:
    """The presentation-rule sheet: RiskScore first, letter with interval.

    A letter rating is a derived, wide-interval conversion and is never the
    headline (README results section; docs/UNCERTAINTY.md). This sheet leads
    with RiskScore and the rank ordering -- the quantities that survive both
    parameter and convention uncertainty -- and renders the letter only with
    its interval attached, or with the reason there is none.
    """
    recs = [credit_record(c) for c in companies]
    recs.sort(
        key=lambda r: (
            r["risk_score"] is None,
            r["risk_score"] if r["risk_score"] is not None else 0.0,
        )
    )
    rows = []
    for i, r in enumerate(recs, start=1):
        rows.append(
            {
                "Rank": i if r["risk_score"] is not None else None,
                "Symbol": r["symbol"],
                "Company": r["company"],
                "TiC Risk Score": r["risk_score"],
                "Rating (with interval)": rating_with_interval(r),
                "Rating Determination": r["rating_determination"],
                "Drift t": r["drift_t_stat"],
                "Weakly Identified": r["weakly_identified"],
                "Convention span (notches)": CONVENTION_SPANS.get(r["symbol"]),
            }
        )
        assert tuple(rows[-1]) == RATINGS_SCHEMA, "ratings row drifted from RATINGS_SCHEMA"
    frame = pd.DataFrame(rows)
    return frame.reindex(columns=list(RATINGS_SCHEMA))


# --------------------------------------------------------------------------- #
# Workbook README sheet
# --------------------------------------------------------------------------- #
def _git_sha() -> str:
    """Short SHA of the commit this run was produced from, or 'unknown'."""
    from creditrating._paths import REPO_ROOT as root

    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        sha = out.stdout.strip()
        if out.returncode != 0 or not sha:
            return "unknown"
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return f"{sha}-dirty" if dirty.stdout.strip() else sha
    except Exception:  # noqa: BLE001 - provenance is best-effort, never fatal
        return "unknown"


def _model_version() -> str:
    from creditrating._paths import REPO_ROOT as root

    try:
        with open(os.path.join(root, "pyproject.toml"), encoding="utf-8") as fh:
            for line in fh:
                if line.strip().startswith("version"):
                    return line.split("=", 1)[1].strip().strip("\"'")
    except Exception:  # noqa: BLE001
        pass
    return "unknown"


def readme_frame(companies: list[CompanyData]) -> pd.DataFrame:
    """The workbook's own README: provenance and the conventions in force.

    The Asset sheet deviates from the reference workbook's 23-column layout by
    appending nine columns. That deviation is deliberate and is documented here
    so a reader of the file does not have to consult the repository to discover
    it -- a contract change that is only recorded outside the artifact is a
    silent contract change.
    """
    dates = [
        c.panel.index[-1].date()
        for c in companies
        if c.panel is not None and not c.panel.empty
    ]
    vintage = max(dates).isoformat() if dates else "n/a"
    stmts = [r for c in companies for r in [credit_record(c)["last_statement_date"]] if r]

    rows: list[tuple[str, str]] = [
        ("— PROVENANCE —", ""),
        # Team timestamp standard (docs/TIMING_PROTOCOL.md §10): tz-aware UTC.
        ("Generated (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
        ("Model version", _model_version()),
        ("Git commit", _git_sha()),
        ("Data vintage (latest priced day)", vintage),
        ("Statement dates used", ", ".join(sorted({str(s) for s in stmts}))),
        ("Companies", str(len(companies))),
        ("", ""),
        ("— CONVENTIONS IN FORCE —", ""),
        (
            "Equity series",
            "Reinvested total-return index anchored at the valuation date: "
            "r_t = (Close_t + Div_t)/Close_{t-1} - 1, normalised so the last value "
            "equals the observed market cap. Window-invariant.",
        ),
        ("Missing dividends", "NaN, never 0. A missing dividend is unknown, not 'none paid'."),
        (
            "Statement alignment",
            f"as-of on available_at = period_end + filing lag "
            f"({clean_config.QUARTERLY_FILING_LAG_DAYS}d for a 10-Q, "
            f"{clean_config.ANNUAL_FILING_LAG_DAYS}d for a 10-K). "
            f"availability_method = {clean_config.AVAILABILITY_METHOD}. "
            "No row sees a statement not yet public on that date.",
        ),
        (
            "Default point D",
            "1.0 x short-term debt + 0.5 x long-term debt. The 0.5 is a "
            "convention, not a measurement; its sweep range is w in "
            "{0, 0.25, 0.5, 0.75, 1.0} on the long-term leg plus the prior "
            "statement vintage (docs/reconciliation/convention_sweep.py, run "
            + CONVENTION_SWEEP_DATE
            + "). Per-company rating span from that "
            "sweep is the 'Convention span (notches)' column on the validation "
            "and Ratings sheets.",
        ),
        (
            "Long-term debt field",
            "'Long Term Debt And Capital Lease Obligation' in preference to plain "
            "'Long Term Debt' (includes capitalised leases)",
        ),
        (
            "Shares outstanding",
            "market cap / price on the valuation date, held constant across "
            "history (a modelling assumption; see docs)",
        ),
        ("Volatility window", f"{sig_config.EM_WINDOW_DAYS} trading days"),
        (
            "Drift window",
            f"{sig_config.DRIFT_WINDOW_DAYS} trading days (~5y); the drift's "
            f"standard error falls with calendar span, volatility's does not",
        ),
        ("Trading days per year", str(sig_config.TRADING_DAYS_PER_YEAR)),
        ("Risk-free rate", "FRED DGS1 (1-year), horizon T = 1 year"),
        ("Outlook", "PIT PD - TTC PD, per Prop. 5.3 Eq. (28)"),
        (
            "Conventions not swept",
            "EM window, drift window, trading-day count, risk-free tenor and the "
            "long-term-debt field preference are single values; no sweep has "
            "measured their span. Only the debt weight and statement vintage "
            "have been.",
        ),
        ("", ""),
        ("— HOW TO READ A RATING —", ""),
        (
            "Rating Basis",
            "GRID_INTERIOR (lookup) | ANALYTICAL (Prop. 5.2.1, no table) | "
            "OFF_GRID or NOT_APPLICABLE (no letter reported)",
        ),
        (
            "Rating Determination",
            "SCALE_RESOLVED | PINNED_AT_FLOOR (grid's 2bp floor) | "
            "PINNED_AT_SCALE_TOP (RiskScore below the best published grade) | "
            "MODEL_NOT_APPLICABLE (see Applicability) | NOT_RATED (defective "
            "drift). SCALE_RESOLVED means the scale could tell this value from "
            "its neighbours -- it is NOT a claim that the estimate is precise. "
            "For that, read Drift t and the Rating Interval. The explicit "
            "'TTC at floor' and 'At scale top' flags are on the validation "
            "sheet.",
        ),
        (
            "Applicability",
            "Two gates suppress the letter, never the measures (ADR 0003, rev 1): "
            "a firm-type gate (BANK_DEPOSIT_FUNDED / INSURER_RESERVE_LIABILITIES "
            "/ REIT_ASSET_STRUCTURE -- the debt-barrier construction does not "
            "describe these balance sheets), and a market-based test "
            "(ASSETS_BELOW_TOTAL_DEBT: market-implied A must strictly exceed "
            "ST + 1.0*LT, the most conservative debt convention, so that "
            "applicability cannot depend on the arbitrary long-term weight). "
            "The reason code is in 'Applicability Reason'.",
        ),
        (
            "Convention span",
            "Notch span of the letter over the debt-weight/vintage sweep of "
            + CONVENTION_SWEEP_DATE
            + ". Read it beside the Rating Interval: "
            "the bootstrap interval is parameter uncertainty only and is a lower "
            "bound on total uncertainty. Span 1 with a pinned determination "
            "means the letter is insensitive to its inputs, not precise.",
        ),
        (
            "Weakly Identified",
            f"|drift t| < {sig_config.WEAK_IDENTIFICATION_T}. The rating is still "
            "published, but mu and CCM divide by a drift indistinguishable from "
            "zero. Read the rating interval, not the point rating.",
        ),
        (
            "Rating Interval",
            f"{int(sig_config.BOOTSTRAP_INTERVAL[0]*100)}th-"
            f"{int(sig_config.BOOTSTRAP_INTERVAL[1]*100)}th percentile over "
            f"{sig_config.BOOTSTRAP_REPLICATES} moving-block bootstrap replicates "
            "of the asset returns. Covers estimation error in sigma and eta only; "
            "A and D are held at their observed values.",
        ),
        ("", ""),
        ("— SHEET LAYOUT (contract deviation) —", ""),
        (
            "Ratings sheet",
            "The presentation rule, applied: RiskScore first (the sheet is sorted "
            "by it -- it is the quantity robust to both drift noise and the debt "
            "convention), and the letter only ever appears with its bootstrap "
            "interval attached, or with the reason there is none. The Asset "
            "sheet is the canonical submission form; the Ratings sheet is how "
            "the result should be read.",
        ),
        (
            "Asset columns 1-23",
            "the reference workbook's canonical set, in its exact order: "
            + ", ".join(CANONICAL_ASSET_COLUMNS),
        ),
        (
            "Asset columns 24+",
            "deliberate additions, not in the reference layout: "
            + ", ".join(EXTENDED_ASSET_COLUMNS),
        ),
        (
            "Why they were added",
            "a blank SP Rating is uninterpretable without Rating Basis and Rating "
            "Determination; lambda (Eq. 3/6) was computed and reached no output; "
            "and a point rating without its interval overstates precision.",
        ),
        (
            "Diagnostics",
            "EM iters and every other diagnostic live on the validation sheet, "
            "never on the deliverable sheet.",
        ),
    ]
    return pd.DataFrame(rows, columns=["Field", "Value"])
