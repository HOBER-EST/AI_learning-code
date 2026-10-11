PYTHON ?= python3
VENV := backend/.venv
PY := $(VENV)/bin/python

.PHONY: install dev test test-backend test-frontend e2e build serve desktop clean

install: $(PY)
	$(PY) -m pip install -r backend/requirements-dev.txt
	cd frontend && npm install

$(PY):
	$(PYTHON) -m venv $(VENV)

dev:
	./scripts/dev.sh

test: test-backend test-frontend

test-backend:
	cd backend && .venv/bin/python -m pytest -q

test-frontend:
	cd frontend && npx tsc -b && npx vitest run

e2e:
	cd frontend && npx playwright test

build:
	cd frontend && npm run build

serve: build
	cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000

desktop:
	$(PY) -m pip install pyinstaller pywebview
	$(PY) desktop/build.py
	$(PY) desktop/smoke_test.py

clean:
	rm -rf frontend/dist frontend/test-results backend/.pytest_cache desktop/build desktop/dist desktop/release
