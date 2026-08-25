#!/bin/zsh
# Starts PitwallEar backend (:8000) + frontend (:5173) together.
set -e
cd "$(dirname "$0")"

trap 'kill 0' EXIT INT TERM

echo "Starting backend on :8000 ..."
(cd backend && ./.venv/bin/uvicorn app.main:app --reload --port 8000) &

echo "Starting frontend on :5173 ..."
(cd frontend && npm run dev) &

echo ""
echo "PitwallEar running:"
echo "  Dashboard : http://localhost:5173"
echo "  API       : http://localhost:8000/docs"
echo "Press Ctrl+C to stop."
wait
