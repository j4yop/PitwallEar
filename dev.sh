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
echo "PitwallEar starting:"
echo "  Dashboard : http://localhost:5173"
echo "  API       : http://localhost:8000/docs"

# First analysis triggers model loads + data downloads; wait until the API
# answers so users know when the Run button will actually work.
printf "Waiting for API"
for _ in {1..60}; do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo ""
    echo "API is up — open http://localhost:5173 and hit Run."
    break
  fi
  printf "."
  sleep 1
done

echo "Press Ctrl+C to stop."
wait
