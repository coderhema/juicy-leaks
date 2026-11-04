#!/usr/bin/env bash
# Build the Astryx web UI (once) and serve it with the API on http://127.0.0.1:8000
set -e
cd "$(dirname "$0")"
if [ ! -d web/dist ]; then (cd web && npm ci && npm run build); fi
exec uvicorn guardrail_lens.api:app --host 127.0.0.1 --port "${PORT:-8000}"
