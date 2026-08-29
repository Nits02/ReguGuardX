# Two least-privilege service accounts: one for the agent, one for the MCP servers.

resource "google_service_account" "agent" {
  project      = var.project_id
  account_id   = "reguguard-agent"
  display_name = "ReguGuard Agent (orchestrator + workers)"
}

resource "google_service_account" "mcp" {
  project      = var.project_id
  account_id   = "reguguard-mcp"
  display_name = "ReguGuard MCP servers (data tools)"
}

# Agent needs: Vertex AI user, Trace/Log writer, Model Armor user, and to invoke MCP Cloud Run.
locals {
  agent_roles = [
    "roles/aiplatform.user",
    "roles/cloudtrace.agent",
    "roles/logging.logWriter",
    "roles/modelarmor.user",
    "roles/run.invoker"           # to call the MCP Cloud Run services (OAuth id-token)
  ]
  # MCP servers only need to read BigQuery + write logs. NO write to source by default.
  mcp_roles = [
    "roles/bigquery.dataViewer",
    "roles/bigquery.jobUser",
    "roles/logging.logWriter"
  ]
}

resource "google_project_iam_member" "agent" {
  for_each = toset(local.agent_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.agent.email}"
}

resource "google_project_iam_member" "mcp" {
  for_each = toset(local.mcp_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.mcp.email}"
}
