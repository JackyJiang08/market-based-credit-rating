"""Export the site's static data from committed fixtures and results.

Writes apps/terminal/public/data/:

    manifest.json            what was exported, by whom, from what
    universe.json            the 150-name run (history/15 + taxonomy merge)
    validation.json          the phase-9 study payloads
    companies/<TICKER>.json  full detail for every fixture-cached ticker:
                             measures, intervals, flags, provenance, EM path,
                             bootstrap summary

Every file carries {git_sha, data_vintage, generated_utc, package_version}.

HARD CONSTRAINT (enforced by check_bundle_safety.py, which this script runs
last and which fails the build on violation): the export contains nothing
derived from the licensed grids beyond our computed per-company outputs --
the same status as the committed reconciliation CSVs.

Usage: python apps/terminal/scripts/build_site_data.py   (or make build-site-data)
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "packages", "core"))

from creditrating import __version__  # noqa: E402
from creditrating.data import cache  # noqa: E402
from creditrating.data.pipeline import RunConfig, fetch_company  # noqa: E402
from creditrating.data.sectors import REASON_TEXT  # noqa: E402
from creditrating.io import records  # noqa: E402
from creditrating.model import config as sig_config  # noqa: E402
from creditrating.model import em  # noqa: E402

OUT = os.path.join(ROOT, "apps", "terminal", "public", "data")
HIST = os.path.join(ROOT, "docs", "reconciliation", "history", "15_universe_150.csv")
TAX = os.path.join(ROOT, "docs", "reconciliation", "universe", "taxonomy.csv")
ANALYSIS = os.path.join(ROOT, "docs", "analysis", "data")
AGENCY = os.path.join(ROOT, "docs", "analysis", "agency_ratings.csv")


def _sha() -> str:
    try:
        return (
            subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
            or "unknown"
        )
    except Exception:  # noqa: BLE001
        return "unknown"


def _clean(obj):
    """JSON-safe: NaN -> None, numpy -> python."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if hasattr(obj, "item"):
        return _clean(obj.item())
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


def main() -> None:
    os.makedirs(os.path.join(OUT, "companies"), exist_ok=True)
    sha = _sha()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    hist = pd.read_csv(HIST)
    tax = pd.read_csv(TAX)[["symbol", "category", "detail", "sector", "agency_approx"]]
    agency = pd.read_csv(AGENCY)[["symbol", "sp", "verified"]]
    uni = hist.merge(tax, left_on="Symbol", right_on="symbol", how="left").merge(
        agency, on="symbol", how="left"
    )
    vintage = str(uni["Last Date"].dropna().astype(str).max())

    def meta() -> dict:
        return {
            "git_sha": sha,
            "generated_utc": stamp,
            "package_version": __version__,
            "data_vintage": vintage,
            "source": "committed fixtures and committed run-of-record results",
        }

    cached = sorted(
        d
        for d in os.listdir(cache.cache_dir())
        if os.path.exists(os.path.join(cache.cache_dir(), d, "prices.parquet"))
    )

    # --- universe.json -------------------------------------------------------
    uni_rows = []
    rs_rank = uni["TiC Risk Score"].rank()
    for i, r in uni.iterrows():
        uni_rows.append(
            {
                "ticker": r["Symbol"],
                "name": r["Company"],
                "sector": r.get("sector"),
                "risk_score": r["TiC Risk Score"],
                "risk_rank": rs_rank[i],
                "sigma_a": r["sigma"],
                "dd": r["DD"],
                "letter": r["SP Rating"],
                "interval_low": r["Rating Interval Low"],
                "interval_high": r["Rating Interval High"],
                "interval_notches": r["Rating Interval Notches"],
                "basis": r["Rating Basis"],
                "determination": r["Rating Determination"],
                "firm_type": r["Firm Type"],
                "applicability_reason": r["Applicability Reason"],
                "drift_t": r["Drift t"],
                "weakly_identified": (None if pd.isna(r["Weakly Identified"]) else bool(r["Weakly Identified"])),
                "taxonomy_category": r["category"],
                "taxonomy_detail": r["detail"],
                "agency_sp": r.get("sp"),
                "agency_verified": r.get("verified"),
                "detail_available": r["Symbol"] in cached,
            }
        )
    json.dump(
        _clean({"meta": meta(), "count": len(uni_rows), "rows": uni_rows}),
        open(os.path.join(OUT, "universe.json"), "w"),
        indent=1,
    )

    # --- validation.json -----------------------------------------------------
    val: dict = {"meta": meta()}
    for name in ("discrimination", "baselines", "sector_correlations", "notch_errors"):
        p = os.path.join(ANALYSIS, f"{name}.csv")
        if os.path.exists(p):
            val[name] = json.loads(pd.read_csv(p).to_json(orient="records"))
    json.dump(_clean(val), open(os.path.join(OUT, "validation.json"), "w"), indent=1)

    # --- per-company detail (fixture-cached tickers only) ---------------------
    rates = cache.load_rates()
    exported = []
    for t in cached:
        c = fetch_company(t, RunConfig(tickers=[t]), rates)
        if c is None:
            continue
        rec = records.credit_record(c)
        path = []
        if c.sigma_A is not None and c.panel is not None and not c.panel.empty:
            window = c.panel.tail(sig_config.DRIFT_WINDOW_DAYS)
            res = em.estimate(
                window["MarketCap_E"], window["DefaultPointDebt_D"], window["RiskFree_R"]
            )
            step = max(1, len(res.asset_values) // 260)  # ~weekly granularity
            path = [
                {"date": d.date().isoformat(), "asset_value": float(v)}
                for i, (d, v) in enumerate(res.asset_values.items())
                if i % step == 0 or i == len(res.asset_values) - 1
            ]
        flags = []
        if c.weakly_identified:
            flags.append(
                {
                    "code": "WEAKLY_IDENTIFIED",
                    "text": f"drift t = {c.drift_t_stat:.2f}: read the interval, "
                    "not the point rating",
                }
            )
        if c.drift_regime == "DEFECTIVE":
            flags.append(
                {"code": "DEFECTIVE_DRIFT", "text": "eta - sigma^2/2 <= 0 (Prop. 4.4.1)"}
            )
        if c.ttc_at_floor:
            flags.append(
                {"code": "AT_FLOOR", "text": "TTC PD at the grid's smallest value"}
            )
        if c.rating_determination == "PINNED_AT_SCALE_TOP":
            flags.append(
                {"code": "AT_SCALE_TOP", "text": "RiskScore below the best published grade"}
            )
        if c.model_applicable is False:
            flags.append(
                {
                    "code": c.applicability_reason or "MODEL_NOT_APPLICABLE",
                    "text": REASON_TEXT.get(c.applicability_reason or "", "gated"),
                }
            )
        detail = {
            "meta": meta(),
            "ticker": c.ticker,
            "name": c.name,
            "sector": c.sector,
            "industry": c.industry,
            "firm_type": c.firm_type,
            "as_of": rec["last_date"],
            "measures": {
                "risk_score": c.risk_score,
                "sigma_a": c.sigma_A,
                "asset_value": c.asset_value,
                "eta_a": c.eta_A,
                "dd": c.dd,
                "edf": c.edf,
                "pit_pd": c.pit_pd,
                "ttc_pd": rec["ttc_pd"],
                "ccm": c.ccm,
                "mu": c.mu,
                "lambda": c.lam,
            },
            "rating": {
                "letter": c.sp_rating,
                "basis": c.rating_basis,
                "determination": c.rating_determination,
                "interval_low": c.rating_interval_low,
                "interval_high": c.rating_interval_high,
                "interval_notches": c.rating_interval_notches,
                "outlook": rec["outlook"],
            },
            "drift": {
                "regime": c.drift_regime,
                "t_stat": c.drift_t_stat,
                "se": c.drift_se,
                "span_years": c.drift_span_years,
            },
            "applicability": {
                "model_applicable": c.model_applicable,
                "reason_code": c.applicability_reason,
                "reason_text": REASON_TEXT.get(c.applicability_reason or ""),
            },
            "flags": flags,
            "provenance": {
                "statement_period_end": rec["last_statement_date"],
                "statement_available_at": rec["statement_available_at"],
                "availability_method": rec["availability_method"],
                "st_debt_source": rec["st_debt_source"],
                "lt_debt_source": rec["lt_debt_source"],
                "debt_source_contradictory": rec["debt_source_contradictory"],
                "shares_method": c.shares_method,
                "shares_reference_date": c.shares_reference_date,
                "cache_fetched_at": None,
            },
            "bootstrap": {
                "sigma_p05": c.boot_sigma_lo,
                "sigma_p95": c.boot_sigma_hi,
                "defective_fraction": c.boot_defective_fraction,
            },
            "em_path": path,
        }
        mp = os.path.join(cache.cache_dir(), t, "meta.json")
        if os.path.exists(mp):
            detail["provenance"]["cache_fetched_at"] = json.load(open(mp)).get("fetched_at")
        json.dump(
            _clean(detail), open(os.path.join(OUT, "companies", f"{t}.json"), "w"), indent=1
        )
        exported.append(t)

    # --- manifest.json --------------------------------------------------------
    manifest = {
        **meta(),
        "files": {
            "universe.json": {"rows": len(uni_rows)},
            "validation.json": {"sections": sorted(k for k in val if k != "meta")},
            "companies/": {"tickers": exported, "count": len(exported)},
        },
        "licensing_note": "contains ONLY our computed per-company outputs; "
        "nothing from the licensed grids (enforced by check_bundle_safety.py)",
    }
    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
    print(f"exported {len(exported)} company files + universe({len(uni_rows)}) + validation")

    # --- the hard constraint, enforced ----------------------------------------
    rc = subprocess.run([sys.executable, os.path.join(HERE, "check_bundle_safety.py")])
    if rc.returncode != 0:
        raise SystemExit("bundle-safety check FAILED; export aborted")


if __name__ == "__main__":
    main()
