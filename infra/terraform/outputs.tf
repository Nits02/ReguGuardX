output "agent_sa_email" { value = google_service_account.agent.email }
output "mcp_sa_email"   { value = google_service_account.mcp.email }
output "bq_dataset"     { value = google_bigquery_dataset.reguguard.dataset_id }
