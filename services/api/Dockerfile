# Multi-stage, non-root. Offline-first: the image carries the committed cache
# fixtures and serves with no network; local/ (licensed material) is excluded
# by .dockerignore and its absence is a tested, first-class state.
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt constraints.txt ./
COPY services/api/requirements.txt ./requirements-api.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels \
      -r requirements.txt -r requirements-api.txt -c constraints.txt

FROM python:3.12-slim
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels \
      yfinance pandas numpy scipy openpyxl requests pyarrow PyYAML \
      pydantic structlog typer fastapi uvicorn && \
    rm -rf /wheels

# The package, the API, the offline fixtures, and the study data the
# universe/validation endpoints serve.
COPY packages/core /app/packages/core
COPY services/api/creditrating_api /app/services/api/creditrating_api
COPY data/cache /app/data/cache
COPY config /app/config
COPY docs/reconciliation/history/15_universe_150.csv \
     /app/docs/reconciliation/history/15_universe_150.csv
COPY docs/reconciliation/universe /app/docs/reconciliation/universe
COPY docs/analysis/data /app/docs/analysis/data

ENV PYTHONPATH=/app/packages/core:/app/services/api \
    CREDITRATING_ROOT=/app \
    MDT_CACHE_DIR=/app/data/cache \
    PYTHONUNBUFFERED=1
RUN mkdir -p /app/outputs /app/data_cleaning/data /app/raw_data_architecture/data && \
    chown -R app:app /app/outputs /app/data_cleaning /app/raw_data_architecture
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["python", "-m", "uvicorn", "creditrating_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
