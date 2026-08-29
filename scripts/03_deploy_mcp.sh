#!/usr/bin/env bash
# Build + deploy both MCP servers to Cloud Run as PRIVATE services (auth required).
set -euo pipefail
source ../.env 2>/dev/null || source .env
REGION="$GOOGLE_CLOUD_LOCATION"
MCP_SA="$SA_MCP"

echo ">> Deploying transaction MCP (private, runs as $MCP_SA)"
gcloud run deploy reguguard-transaction-mcp \
  --source mcp_servers/transaction_server \
  --region "$REGION" \
  --service-account "$MCP_SA" \
  --no-allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,BQ_DATASET=$BQ_DATASET,BQ_TXN_TABLE=$BQ_TXN_TABLE" \
  --port 8080 --cpu 1 --memory 512Mi --max-instances 3

echo ">> Deploying sanctions MCP (private, runs as $MCP_SA)"
gcloud run deploy reguguard-sanctions-mcp \
  --source mcp_servers/sanctions_server \
  --region "$REGION" \
  --service-account "$MCP_SA" \
  --no-allow-unauthenticated \
  --port 8081 --cpu 1 --memory 512Mi --max-instances 3

TXN_URL=$(gcloud run services describe reguguard-transaction-mcp --region "$REGION" --format='value(status.url)')
SAN_URL=$(gcloud run services describe reguguard-sanctions-mcp --region "$REGION" --format='value(status.url)')

echo ">> Allow the AGENT service account to invoke the MCP services (per-tool IAM)"
gcloud run services add-iam-policy-binding reguguard-transaction-mcp --region "$REGION" \
  --member "serviceAccount:$SA_AGENT" --role roles/run.invoker
gcloud run services add-iam-policy-binding reguguard-sanctions-mcp --region "$REGION" \
  --member "serviceAccount:$SA_AGENT" --role roles/run.invoker

echo ""
echo ">>> Put these in your .env:"
echo "export TRANSACTION_MCP_URL=\"$TXN_URL/mcp\""
echo "export SANCTIONS_MCP_URL=\"$SAN_URL/mcp\""
