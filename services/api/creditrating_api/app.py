"""FastAPI service over the creditrating package.

Offline-first: every read endpoint serves from the committed/populated cache
under ``data/cache/`` with no network; a live fetch requires the explicit
``live`` flag. Every response embeds the domain models plus basis,
determination, drift, applicability and provenance -- a number cannot be
rendered without its caveat. Errors are a machine-readable envelope with a
correlation id; no stack trace ever reaches a client.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd
import structlog
import yaml
from creditrating import __version__
from creditrating._paths import REPO_ROOT
from creditrating.data import cache
from creditrating.data.company import CompanyData
from creditrating.data.pipeline import RunConfig, fetch_company
from creditrating.data.sectors import REASON_TEXT
from creditrating.domain import AssetEstimates, RatingResult, RiskMeasures
from creditrating.model import conversion
from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import ValidationError

from .jobs import get as get_job
from .jobs import start as start_job
from .models import (
    ApplicabilityInfo,
    BatchRequest,
    BatchStatus,
    DriftInfo,
    ErrorBody,
    ErrorEnvelope,
    HealthStatus,
    Provenance,
    RateRequest,
    RatingEnvelope,
    SearchHit,
)

LOG = structlog.get_logger("creditrating_api")

UNIVERSE_CSV = os.path.join(
    REPO_ROOT, "docs", "reconciliation", "history", "15_universe_150.csv"
)
TAXONOMY_CSV = os.path.join(REPO_ROOT, "docs", "reconciliation", "universe", "taxonomy.csv")
ANALYSIS_DIR = os.path.join(REPO_ROOT, "docs", "analysis", "data")
UNIVERSE_YAML = os.path.join(REPO_ROOT, "config", "universe.yaml")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def _cid() -> str:
    return structlog.contextvars.get_contextvars().get("run_id", uuid.uuid4().hex[:12])


def _cached(ticker: str) -> bool:
    t = ticker.upper()
    return cache.load_info(t) is not None and cache.load_prices(t) is not None


def _require_offline_or_live(ticker: str, live: bool) -> None:
    if not live and not _cached(ticker):
        raise ApiError(
            404,
            "NOT_IN_OFFLINE_CACHE",
            f"{ticker.upper()} is not in the offline cache; pass live=true to "
            "allow a network fetch (the demo deployment is offline-first).",
        )


def _reject_as_of(as_of: Optional[str]) -> None:
    if as_of:
        raise ApiError(
            422,
            "AS_OF_NOT_SUPPORTED",
            "Point-in-time reruns need immutable vintage snapshots "
            "(docs/TIMING_PROTOCOL.md section 9); as_of is rejected rather "
            "than silently served from today's data.",
        )


def _num(x: Any) -> Optional[float]:
    if x is None:
        return None
    f = float(x)
    return None if math.isnan(f) else f


def _envelope(c: CompanyData) -> RatingEnvelope:
    """Compose the domain models + caveats from one finished company."""
    reason_codes: list[str] = []
    flags: list[str] = []

    estimates: Optional[AssetEstimates] = None
    if c.sigma_A is not None and c.asset_value is not None:
        d_last = None
        if c.panel is not None and not c.panel.empty and "DefaultPointDebt_D" in c.panel:
            s = c.panel["DefaultPointDebt_D"].dropna()
            d_last = float(s.iloc[-1]) if not s.empty else None
        try:
            estimates = AssetEstimates(
                ticker=c.ticker,
                asset_value=c.asset_value,
                default_point=d_last or 1e-9,
                sigma_a=c.sigma_A,
                eta_a=c.eta_A or 0.0,
                em_iterations=c.em_iters or 1,
                em_converged=bool(c.em_converged),
            )
        except ValidationError:
            reason_codes.append("DOMAIN_INVARIANT_VIOLATION")

    measures: Optional[RiskMeasures] = None
    if c.risk_score is not None:
        measures = RiskMeasures(
            ticker=c.ticker,
            risk_score=c.risk_score,
            dd=c.dd or 0.0,
            edf=_num(c.edf) or 0.0,
            pit_pd=_num(c.pit_pd) or 0.0,
            ttc_pd=_num(c.ttc_pd),
        )
        if _num(c.ttc_pd) is None and c.model_applicable is not False:
            if not os.path.exists(conversion.DEFAULT_XLSX):
                reason_codes.append("CONVERSION_TABLES_ABSENT")
            elif c.drift_regime == "DEFECTIVE":
                reason_codes.append("DEFECTIVE_DRIFT")
            else:
                reason_codes.append("TTC_UNAVAILABLE")

    if c.model_applicable is False and c.applicability_reason:
        reason_codes.append(c.applicability_reason)
    if c.drift_regime == "DEFECTIVE" and "DEFECTIVE_DRIFT" not in reason_codes:
        reason_codes.append("DEFECTIVE_DRIFT")
    if c.weakly_identified:
        flags.append("WEAKLY_IDENTIFIED")
    if c.ttc_at_floor:
        flags.append("TTC_AT_FLOOR")
    if c.rating_off_grid:
        flags.append("OFF_GRID_CLAMPED")
    if c.em_error:
        flags.append(f"EM: {c.em_error}")

    rating = RatingResult(
        ticker=c.ticker,
        letter=c.sp_rating,
        basis=c.rating_basis,
        determination=c.rating_determination,
        interval_low=c.rating_interval_low,
        interval_high=c.rating_interval_high,
    )

    vintage = None
    stmt = None
    if c.panel is not None and not c.panel.empty:
        vintage = c.panel.index[-1].date().isoformat()
        if "StatementPeriodEnd" in c.panel:
            s = c.panel["StatementPeriodEnd"].dropna()
            if not s.empty:
                stmt = pd.Timestamp(s.iloc[-1]).date().isoformat()

    return RatingEnvelope(
        ticker=c.ticker,
        company=c.name,
        estimates=estimates,
        measures=measures,
        rating=rating,
        drift=DriftInfo(
            regime=c.drift_regime,
            t_stat=_num(c.drift_t_stat),
            se=_num(c.drift_se),
            weakly_identified=c.weakly_identified,
        ),
        applicability=ApplicabilityInfo(
            model_applicable=c.model_applicable,
            reason_code=c.applicability_reason,
            reason_text=REASON_TEXT.get(c.applicability_reason or ""),
            firm_type=c.firm_type,
        ),
        flags=flags,
        reason_codes=reason_codes,
        provenance=Provenance(
            correlation_id=_cid(),
            package_version=__version__,
            data_vintage_last_priced_day=vintage,
            statement_period_end=stmt,
            cache_hit=_cached(c.ticker),
            generated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ),
    )


def _rate_one(ticker: str, live: bool) -> RatingEnvelope:
    _require_offline_or_live(ticker, live)
    rates = cache.load_rates()
    if rates is None:
        raise ApiError(503, "RATES_UNAVAILABLE", "no cached FRED rates and offline mode")
    c = fetch_company(ticker.upper(), RunConfig(tickers=[ticker]), rates)
    if c is None:
        raise ApiError(422, "UNPROCESSABLE_TICKER", f"could not process {ticker!r}")
    return _envelope(c)


def _rate_for_job(ticker: str, live: bool):
    try:
        return _rate_one(ticker, live), None
    except ApiError as exc:
        return None, exc.code
    except Exception:  # noqa: BLE001 - isolation: an error is an event
        LOG.exception("batch.company_failed", ticker=ticker)
        return None, "INTERNAL"


def create_app() -> FastAPI:
    app = FastAPI(
        title="creditrating API",
        version=__version__,
        description="Market-based credit ratings (KMV/Merton + TiC), offline-first. "
        "Every rating carries basis, determination, drift regime, applicability, "
        "interval and provenance -- numbers never travel without their caveats.",
    )

    @app.middleware("http")
    async def correlation(request: Request, call_next):
        cid = uuid.uuid4().hex[:12]
        structlog.contextvars.bind_contextvars(run_id=cid)
        try:
            response = await call_next(request)
        except ApiError:
            raise
        except Exception:  # noqa: BLE001 - envelope, never a stack trace
            LOG.exception("request.failed", path=str(request.url.path))
            return JSONResponse(
                status_code=500,
                content=ErrorEnvelope(
                    error=ErrorBody(
                        code="INTERNAL",
                        message="internal error; see server logs",
                        correlation_id=cid,
                    )
                ).model_dump(),
                headers={"X-Correlation-Id": cid},
            )
        response.headers["X-Correlation-Id"] = cid
        return response

    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError):
        cid = _cid()
        return JSONResponse(
            status_code=exc.status,
            content=ErrorEnvelope(
                error=ErrorBody(code=exc.code, message=exc.message, correlation_id=cid)
            ).model_dump(),
            headers={"X-Correlation-Id": cid},
        )

    @app.get("/health", response_model=HealthStatus)
    async def health() -> HealthStatus:
        root = cache.cache_dir()
        n = 0
        if os.path.isdir(root):
            n = sum(
                1
                for d in os.listdir(root)
                if os.path.exists(os.path.join(root, d, "prices.parquet"))
            )
        return HealthStatus(
            status="ok",
            version=__version__,
            conversion_workbook_present=os.path.exists(conversion.DEFAULT_XLSX),
            cached_tickers=n,
        )

    @app.get("/api/v1/companies/search", response_model=list[SearchHit])
    async def search(q: str = Query(min_length=1)) -> list[SearchHit]:
        ql = q.lower()
        hits: dict[str, SearchHit] = {}
        with open(UNIVERSE_YAML, encoding="utf-8") as fh:
            for e in yaml.safe_load(fh)["companies"]:
                t = str(e["ticker"]).upper()
                info = cache.load_info(t) or {}
                name = info.get("longName") or info.get("shortName")
                if ql in t.lower() or (name and ql in name.lower()):
                    hits[t] = SearchHit(
                        ticker=t, name=name, sector=info.get("sector"), cached=_cached(t)
                    )
        return list(hits.values())[:25]

    @app.post("/api/v1/rate", response_model=RatingEnvelope)
    async def rate(req: RateRequest) -> RatingEnvelope:
        _reject_as_of(req.as_of)
        return await asyncio.to_thread(_rate_one, req.ticker, req.live)

    @app.post("/api/v1/batch", status_code=202)
    async def batch(req: BatchRequest) -> dict[str, str]:
        _reject_as_of(req.as_of)
        job = start_job(req.tickers, _rate_for_job, req.live)
        return {"job_id": job.job_id, "events": f"/api/v1/batch/{job.job_id}/events"}

    @app.get("/api/v1/batch/{job_id}", response_model=BatchStatus)
    async def batch_status(job_id: str) -> BatchStatus:
        job = get_job(job_id)
        if job is None:
            raise ApiError(404, "JOB_NOT_FOUND", f"no batch job {job_id!r}")
        det: dict[str, int] = {}
        for r in job.results:
            key = r.rating.determination or "NONE"
            det[key] = det.get(key, 0) + 1
        return BatchStatus(
            job_id=job.job_id,
            status=job.status,
            total=len(job.tickers),
            completed=job.completed,
            determinations=det,
            results=job.results,
        )

    @app.get("/api/v1/batch/{job_id}/events")
    async def batch_events(job_id: str) -> StreamingResponse:
        job = get_job(job_id)
        if job is None:
            raise ApiError(404, "JOB_NOT_FOUND", f"no batch job {job_id!r}")

        async def stream():
            cursor = 0
            while True:
                while cursor < len(job.events):
                    e = job.events[cursor]
                    cursor += 1
                    yield f"event: {e.get('event', 'message')}\ndata: {json.dumps(e)}\n\n"
                if job.status in ("done", "failed") and cursor >= len(job.events):
                    return
                await asyncio.sleep(0.15)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/v1/companies/{ticker}/diagnostics")
    async def diagnostics(ticker: str, live: bool = False) -> dict[str, Any]:
        _require_offline_or_live(ticker, live)

        def _run() -> dict[str, Any]:
            from creditrating.model import config as sig_config
            from creditrating.model import em

            rates = cache.load_rates()
            c = fetch_company(ticker.upper(), RunConfig(tickers=[ticker]), rates)
            if c is None or c.panel is None or c.panel.empty:
                raise ApiError(422, "UNPROCESSABLE_TICKER", f"no panel for {ticker!r}")
            env = _envelope(c)
            path: list[dict[str, Any]] = []
            if c.sigma_A is not None:
                window = c.panel.tail(sig_config.DRIFT_WINDOW_DAYS)
                res = em.estimate(
                    window["MarketCap_E"], window["DefaultPointDebt_D"], window["RiskFree_R"]
                )
                path = [
                    {"date": d.date().isoformat(), "asset_value": float(v)}
                    for d, v in res.asset_values.items()
                ]
            return {
                "ticker": ticker.upper(),
                "envelope": env.model_dump(),
                "em_path": path,
                "bootstrap": {
                    "sigma_p05": _num(c.boot_sigma_lo),
                    "sigma_p95": _num(c.boot_sigma_hi),
                    "defective_fraction": _num(c.boot_defective_fraction),
                    "letter_interval": [c.rating_interval_low, c.rating_interval_high],
                },
            }

        return await asyncio.to_thread(_run)

    @app.get("/api/v1/universe")
    async def universe(
        sector: Optional[str] = None,
        determination: Optional[str] = None,
        rated: Optional[bool] = None,
    ) -> dict[str, Any]:
        hist = pd.read_csv(UNIVERSE_CSV)
        tax = pd.read_csv(TAXONOMY_CSV)[["symbol", "category", "detail", "sector"]]
        df = hist.merge(tax, left_on="Symbol", right_on="symbol", how="left")
        if sector:
            df = df[df["sector"].str.lower() == sector.lower()]
        if determination:
            df = df[df["Rating Determination"] == determination]
        if rated is not None:
            df = df[df["SP Rating"].notna() == rated]
        rows = json.loads(df.to_json(orient="records"))
        return {
            "run": "2026-07-26 (history/15)",
            "count": len(rows),
            "note": "letters never without determination/basis; see each row",
            "rows": rows,
        }

    @app.get("/api/v1/validation")
    async def validation() -> dict[str, Any]:
        out: dict[str, Any] = {
            "study": "docs/analysis/VALIDATION.md",
            "ground_truth": "docs/analysis/agency_ratings.csv (sourced, per-row citation)",
        }
        for name in ("discrimination", "baselines", "sector_correlations", "notch_errors"):
            p = os.path.join(ANALYSIS_DIR, f"{name}.csv")
            if os.path.exists(p):
                out[name] = json.loads(pd.read_csv(p).to_json(orient="records"))
        return out

    @app.get("/api/v1/export/workbook")
    async def export_workbook(tickers: str = Query(min_length=1)) -> FileResponse:
        wanted = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        for t in wanted:
            _require_offline_or_live(t, live=False)

        def _run() -> str:
            from creditrating.io import workbook

            rates = cache.load_rates()
            companies = [
                c
                for t in wanted
                if (c := fetch_company(t, RunConfig(tickers=[t]), rates)) is not None
            ]
            return workbook.write_submission(companies, filename=f"api_export_{_cid()}.xlsx")

        path = await asyncio.to_thread(_run)
        return FileResponse(
            path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=os.path.basename(path),
        )

    return app


app = create_app()
