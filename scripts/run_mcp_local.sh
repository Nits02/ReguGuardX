#!/usr/bin/env bash
# Run both MCP servers locally in the background for local ADK testing.
set -euo pipefail
source ../.env 2>/dev/null || source .env
export GOOGLE_CLOUD_PROJECT BQ_DATASET

( cd mcp_servers/transaction_server && PORT=8080 python server.py ) &
echo "transaction MCP on :8080 (pid $!)"
( cd mcp_servers/sanctions_server && PORT=8081 WATCHLIST_PATH="$PWD/mcp_servers/sanctions_server/sample_watchlist.csv" python server.py ) &
echo "sanctions MCP on :8081 (pid $!)"
echo "Set in .env:  TRANSACTION_MCP_URL=http://localhost:8080/mcp  SANCTIONS_MCP_URL=http://localhost:8081/mcp"
wait
