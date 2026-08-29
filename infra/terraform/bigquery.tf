resource "google_bigquery_dataset" "reguguard" {
  project                     = var.project_id
  dataset_id                  = var.bq_dataset
  location                    = var.region
  delete_contents_on_destroy  = true
  description                 = "ReguGuard synthetic AML transactions + ground-truth labels"
}
