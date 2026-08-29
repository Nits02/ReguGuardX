#!/usr/bin/env bash
# Deploy the ReguGuard agent. Two options — pick one.
set -euo pipefail
source ../.env 2>/dev/null || source .env
REGION="$GOOGLE_CLOUD_LOCATION"

MODE="${1:-agent-engine}"   # agent-engine | cloud-run

if [ "$MODE" = "cloud-run" ]; then
  echo ">> Deploying agent to Cloud Run via ADK"
  adk deploy cloud_run \
    --project "$GOOGLE_CLOUD_PROJECT" \
    --region "$REGION" \
    --service_name reguguard-agent \
    --with_ui \
    agents/reguguard
else
  echo ">> Deploying agent to Vertex AI Agent Engine"
  python agents/deploy_agent_engine.py
fi
