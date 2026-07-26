"""API contract tests: httpx.AsyncClient against the ASGI app, offline.

Everything runs from the committed cache fixtures with no network; the
proprietary-absent behavior is tested explicitly (TTC fields null WITH a
reason code, never silently missing).
"""

from __future__ import annotations

import asyncio
import json
import os

import httpx
import pytest
from creditrating.data import cache

FIXTURES = os.path.exists(os.path.join(cache.cache_dir(), "COST", "prices.parquet"))
pytestmark = pytest.mark.skipif(not FIXTURES, reason="cache fixtures not present")


@pytest.fixture()
def app():
    from creditrating_api.app import create_app

    return create_app()


@pytest.fixture()
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["cached_tickers"] >= 10
    assert body["offline_first"] is True


async def test_openapi_contract(client):
    r = await client.get("/openapi.json")
    spec = r.json()
    paths = set(spec["paths"])
    for expected in (
        "/health",
        "/api/v1/companies/search",
        "/api/v1/rate",
        "/api/v1/batch",
        "/api/v1/batch/{job_id}",
        "/api/v1/batch/{job_id}/events",
        "/api/v1/companies/{ticker}/diagnostics",
        "/api/v1/universe",
        "/api/v1/validation",
        "/api/v1/export/workbook",
    ):
        assert expected in paths, f"missing {expected}"
    # The domain models are the response schema -- no parallel DTOs.
    schemas = spec["components"]["schemas"]
    assert "RatingResult" in schemas and "RiskMeasures" in schemas
    assert "AssetEstimates" in schemas
    env = schemas["RatingEnvelope"]["properties"]
    for field in ("rating", "measures", "drift", "applicability", "provenance"):
        assert field in env


async def test_rate_offline_carries_every_caveat(client):
    r = await client.post("/api/v1/rate", json={"ticker": "COST"})
    assert r.status_code == 200
    e = r.json()
    assert e["rating"]["ticker"] == "COST"
    if e["rating"]["letter"] is not None:
        assert e["rating"]["basis"] and e["rating"]["determination"]
    assert e["drift"]["regime"] in ("VALID", "DEFECTIVE")
    assert e["applicability"]["model_applicable"] is True
    assert e["measures"]["risk_score"] > 0
    assert e["provenance"]["cache_hit"] is True
    assert r.headers["x-correlation-id"]


async def test_uncached_ticker_is_refused_offline(client):
    r = await client.post("/api/v1/rate", json={"ticker": "ZZZQ"})
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "NOT_IN_OFFLINE_CACHE"
    assert err["correlation_id"]


async def test_as_of_is_rejected_not_silently_served(client):
    r = await client.post("/api/v1/rate", json={"ticker": "COST", "as_of": "2025-01-01"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "AS_OF_NOT_SUPPORTED"


async def test_ttc_fields_null_with_reason_when_workbook_absent(client, monkeypatch):
    """The proprietary-absent contract: null + reason code, never missing."""
    from creditrating.model import conversion as conv

    monkeypatch.setattr(
        conv,
        "load_tables",
        lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("simulated absent workbook")),
    )
    real_exists = os.path.exists
    monkeypatch.setattr(
        "creditrating_api.app.os.path.exists",
        lambda p: False if str(p).endswith(".xlsx") else real_exists(p),
    )
    r = await client.post("/api/v1/rate", json={"ticker": "KO"})
    assert r.status_code == 200
    e = r.json()
    assert "ttc_pd" in e["measures"], "field present, not missing"
    assert e["measures"]["ttc_pd"] is None
    assert "CONVERSION_TABLES_ABSENT" in e["reason_codes"]
    assert e["rating"]["letter"] is None


async def test_batch_completes_and_streams_events(client):
    r = await client.post("/api/v1/batch", json={"tickers": ["COST", "KO"]})
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    for _ in range(200):
        s = await client.get(f"/api/v1/batch/{job_id}")
        if s.json()["status"] == "done":
            break
        await asyncio.sleep(0.25)
    body = s.json()
    assert body["status"] == "done" and body["completed"] == 2
    assert sum(body["determinations"].values()) == 2

    events = []
    async with client.stream("GET", f"/api/v1/batch/{job_id}/events") as resp:
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
            if events and events[-1].get("event") == "done":
                break
    kinds = [e["event"] for e in events]
    assert kinds[0] == "start" and kinds[-1] == "done"
    company_events = [e for e in events if e["event"] == "company"]
    assert len(company_events) == 2
    assert all("em_iterations" in e for e in company_events), "EM convergence streams"


async def test_diagnostics_returns_em_path_and_bootstrap(client):
    r = await client.get("/api/v1/companies/COST/diagnostics")
    assert r.status_code == 200
    d = r.json()
    assert len(d["em_path"]) > 200
    assert d["bootstrap"]["sigma_p05"] is not None
    assert d["envelope"]["rating"]["ticker"] == "COST"


async def test_universe_filters(client):
    r = await client.get("/api/v1/universe", params={"determination": "SCALE_RESOLVED"})
    body = r.json()
    assert body["count"] > 0
    assert all(row["Rating Determination"] == "SCALE_RESOLVED" for row in body["rows"])


async def test_validation_serves_the_study(client):
    r = await client.get("/api/v1/validation")
    body = r.json()
    assert any(s["stratum"] == "SCALE_RESOLVED only" for s in body["discrimination"])


async def test_export_workbook(client, tmp_path):
    r = await client.get("/api/v1/export/workbook", params={"tickers": "COST,KO"})
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["content-type"]
    assert len(r.content) > 10_000


async def test_search(client):
    r = await client.get("/api/v1/companies/search", params={"q": "cost"})
    hits = r.json()
    assert any(h["ticker"] == "COST" and h["cached"] for h in hits)
