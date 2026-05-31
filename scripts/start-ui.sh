#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Installing Python package…"
pip install -e ".[ui]" -q

if [[ ! -d dashboard/dist ]]; then
  echo "Building dashboard (first run)…"
  cd dashboard
  npm install
  npm run build
  cd "$ROOT"
fi

echo ""
echo "  Omega Dashboard → http://127.0.0.1:8765"
echo ""
exec python -m omega.api.server
