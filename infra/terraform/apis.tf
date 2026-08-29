# Enable every API ReguGuard touches. Idempotent.
locals {
  services = [
    "aiplatform.googleapis.com",         # Vertex AI, Agent Engine, RAG
    "run.googleapis.com",                # Cloud Run (MCP servers, agent)
    "cloudbuild.googleapis.com",         # container builds
    "artifactregistry.googleapis.com",   # image storage
    "bigquery.googleapis.com",           # transaction data
    "cloudtrace.googleapis.com",         # tracing
    "logging.googleapis.com",            # logs
    "modelarmor.googleapis.com",         # Model Armor
    "discoveryengine.googleapis.com",    # Vertex AI Search / grounding
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",     # SA impersonation / token minting
    "secretmanager.googleapis.com",
    "compute.googleapis.com"             # Cloud Armor backend (if used)
  ]
}

resource "google_project_service" "svc" {
  for_each           = toset(local.services)
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}
