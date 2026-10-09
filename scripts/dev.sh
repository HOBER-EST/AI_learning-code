#!/usr/bin/env bash
# Starts the backend (:8000) and the frontend dev server (:5173) together.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT/backend/.venv/bin/python}"

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

(cd "$ROOT/backend" && "$PYTHON" -m uvicorn app.main:app --port 8000 --reload) &
(cd "$ROOT/frontend" && npx vite --port 5173) &

echo "后端: http://localhost:8000   前端: http://localhost:5173"
wait
