#!/usr/bin/env bash
# Enable all required APIs (mirror of infra/terraform/apis.tf for the no-Terraform path).
set -euo pipefail
source ../.env 2>/dev/null || source .env
gcloud services enable \
  aiplatform.googleapis.com run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com bigquery.googleapis.com cloudtrace.googleapis.com \
  logging.googleapis.com modelarmor.googleapis.com discoveryengine.googleapis.com \
  iam.googleapis.com iamcredentials.googleapis.com secretmanager.googleapis.com \
  compute.googleapis.com \
  --project "$GOOGLE_CLOUD_PROJECT"
echo ">> APIs enabled."
