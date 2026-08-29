#!/usr/bin/env bash
set -euo pipefail
source .env 2>/dev/null || source ../.env
export GOOGLE_GENAI_USE_VERTEXAI="${GOOGLE_GENAI_USE_VERTEXAI:-true}"
export PYTHONUNBUFFERED=1
python -u eval/build_evalset.py
echo ">> Running ADK-native evalset (semantic scoring):"
adk eval agents/reguguard eval/evalset.json || echo "(adk eval optional; falling back to custom harness)"
echo ">> Running deterministic precision/recall harness:"
python -u eval/test_reguguard.py
