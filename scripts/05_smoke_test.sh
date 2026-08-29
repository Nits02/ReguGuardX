#!/usr/bin/env bash
# Minimal smoke test: send one audit request through the deployed agent.
set -euo pipefail
source ../.env 2>/dev/null || source .env
echo ">> Local smoke via adk run (uses local .env + MCP URLs):"
echo "Audit transaction T-000000 style query. Type a txn_id from BigQuery."
echo "Example prompt: 'Audit the flagged transactions from 2025-01-01 to 2025-12-31 and give me dispositions.'"
adk run agents/reguguard
