# services/api — the creditrating API

FastAPI over `creditrating`, **offline-first**: every endpoint serves from the
committed/populated cache under `data/cache/` with no network; a live fetch
requires the explicit `live` flag per request. The demo deployment does not
depend on a data vendor being up.

The pydantic **domain models are the response models** (no parallel DTOs):
every rating travels inside an envelope carrying basis, determination, drift
regime, applicability (with reason code + text), flags, reason codes, and
provenance — a client cannot render a number without its caveat.

| Endpoint | Purpose |
|---|---|
| `GET /health` | version, workbook presence, cached-ticker count |
| `GET /api/v1/companies/search?q=` | offline search over the universe + cache |
| `POST /api/v1/rate` | one company → RatingEnvelope (`as_of` explicitly rejected) |
| `POST /api/v1/batch` | async job over tickers → job id |
| `GET /api/v1/batch/{job_id}` | status, determinations, results |
| `GET /api/v1/batch/{job_id}/events` | **SSE**: per-company progress incl. EM convergence |
| `GET /api/v1/companies/{t}/diagnostics` | EM asset path, bootstrap CIs, flags |
| `GET /api/v1/universe` | the 150-name run with sector/determination/rated filters |
| `GET /api/v1/validation` | the agency-validation study (discrimination, baselines, sectors) |
| `GET /api/v1/export/workbook?tickers=` | the four-sheet workbook, generated on demand |

Errors are a machine-readable envelope `{error: {code, message,
correlation_id}}`; the correlation id is the structlog run-id and also rides
the `X-Correlation-Id` header. No stack traces to clients. When the licensed
conversion workbook is absent, TTC fields are **null with reason code
`CONVERSION_TABLES_ABSENT`** — never silently missing (contract-tested).

Run it:

```bash
make serve          # docker compose up (multi-stage, non-root, fixtures baked in)
make serve-local    # uvicorn directly, same offline behavior
pytest tests/api/   # httpx.AsyncClient + OpenAPI contract tests
```
