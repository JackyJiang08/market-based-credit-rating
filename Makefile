# Developer entry points. `make setup` then `make demo` works on a fresh
# clone with no network (committed cache fixtures).

PY ?= python3

.PHONY: setup test lint run batch serve demo

setup:
	$(PY) -m pip install -r requirements.txt -r requirements-dev.txt -c constraints.txt

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check packages tests services
	$(PY) -m black --check -q packages tests services
	$(PY) -m mypy

run:
	$(PY) -m mdt rate $(or $(TICKER),COST)

batch:
	$(PY) -m mdt batch config/universe.yaml --workers $(or $(WORKERS),6)

serve:
	docker compose up --build -d api
	@echo "API on http://localhost:8000 (offline-first, from committed fixtures)"

serve-local:
	PYTHONPATH=packages/core:services/api $(PY) -m uvicorn creditrating_api.app:app --port 8000

build-site-data:
	$(PY) apps/terminal/scripts/build_site_data.py

site:
	cd apps/terminal && npm run build

demo:
	@echo "== offline demo from committed fixtures (no network) =="
	$(PY) -m mdt rate COST
