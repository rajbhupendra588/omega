#!/usr/bin/env bash
# Start Omega dashboard. Default: dev mode with API + UI auto-reload.
# Usage:
#   ./scripts/start-ui.sh          # dev (Vite HMR + uvicorn --reload)
#   ./scripts/start-ui.sh --prod   # production (built assets on :8765 only)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODE="${1:-dev}"
if [[ "$MODE" != "dev" && "$MODE" != "--prod" && "$MODE" != "prod" ]]; then
  echo "Usage: $0 [dev|--prod]" >&2
  exit 1
fi
[[ "$MODE" == "prod" ]] && MODE="--prod"

echo "Installing Python package…"
pip install -e ".[ui]" -q

cleanup() {
  local pids
  pids=$(jobs -p 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    kill $pids 2>/dev/null || true
    wait 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [[ "$MODE" == "--prod" ]]; then
  if [[ ! -d dashboard/dist ]] || [[ "${OMEGA_FORCE_BUILD:-}" == "1" ]]; then
    echo "Building dashboard…"
    (cd dashboard && npm install && npm run build)
  fi
  echo ""
  echo "  Omega (production) → http://127.0.0.1:8765"
  echo "  Rebuild UI after frontend changes: cd dashboard && npm run build"
  echo ""
  exec python -m omega.api.server
fi

# --- Development: auto-reload API + Vite HMR ---
echo "Installing dashboard dependencies…"
(cd dashboard && npm install --silent 2>/dev/null || (cd dashboard && npm install))

echo ""
echo "  Omega development mode"
echo "  ─────────────────────"
echo "  Dashboard (hot reload) → http://127.0.0.1:5173"
echo "  API (auto-reload)      → http://127.0.0.1:8765"
echo ""
echo "  Press Ctrl+C to stop both servers."
echo ""

export OMEGA_RELOAD=1

uvicorn omega.api.server:app \
  --host 127.0.0.1 \
  --port 8765 \
  --reload \
  --reload-dir "$ROOT/omega" \
  --reload-include "*.py" \
  &

API_PID=$!
sleep 1
if ! kill -0 "$API_PID" 2>/dev/null; then
  echo "Failed to start API server." >&2
  exit 1
fi

cd dashboard
npm run dev
