#!/usr/bin/env bash
# SatyaVaani setup -- Linux / macOS / WSL / Git Bash
set -e
cd "$(dirname "$0")/.."
echo "=== SatyaVaani setup ==="
python3 -V || { echo "Python 3.10+ required"; exit 1; }

if [ ! -d .venv ]; then
  echo "-- creating .venv"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip -q
echo "-- installing core deps (fast)"
pip install -q -r requirements.txt
echo
echo "Done. Two terminals:"
echo "  1)  bash scripts/run_backend.sh"
echo "  2)  cd frontend && npm install && npm run dev"
echo
echo "No backend yet?  python mocks/mock_server.py"
