#!/usr/bin/env bash
# One-time GCP bootstrap. Run after `gcloud auth login`.
set -euo pipefail
source ../.env 2>/dev/null || source .env

echo ">> Setting project: $GOOGLE_CLOUD_PROJECT"
gcloud config set project "$GOOGLE_CLOUD_PROJECT"
gcloud config set run/region "$GOOGLE_CLOUD_LOCATION"

echo ">> Application default credentials (for local ADK runs)"
gcloud auth application-default login --quiet || true
gcloud auth application-default set-quota-project "$GOOGLE_CLOUD_PROJECT" || true

echo ">> Done. Next: bash scripts/01_enable_apis.sh  (or use Terraform in infra/)"
