# Developer entry points. `make setup` then `make demo` works on a fresh
# clone with no network (committed cache fixtures).

PY ?= python3

.PHONY: setup test lint run batch serve demo

setup:
	$(PY) -m pip install -r requirements.txt -r requirements-dev.txt -c constraints.txt

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check packages tests
	$(PY) -m black --check -q packages tests
	$(PY) -m mypy

run:
	$(PY) -m mdt rate $(or $(TICKER),COST)

batch:
	$(PY) -m mdt batch config/universe.yaml --workers $(or $(WORKERS),6)

serve:
	@echo "services/api arrives in phase 11 -- nothing to serve yet." && exit 1

demo:
	@echo "== offline demo from committed fixtures (no network) =="
	$(PY) -m mdt rate COST
