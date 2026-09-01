#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
[ -d .venv ] && source .venv/bin/activate
exec uvicorn backend.main:app --reload --port 8000 --host 0.0.0.0
