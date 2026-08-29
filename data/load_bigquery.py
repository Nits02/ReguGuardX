"""Load generated transactions + labels into BigQuery."""
import json
import os
from pathlib import Path
from google.cloud import bigquery

PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
DATASET = os.environ.get("BQ_DATASET", "reguguard")
TXN_TABLE = os.environ.get("BQ_TXN_TABLE", "transactions")
LABELS_TABLE = os.environ.get("BQ_LABELS_TABLE", "labels")
GEN = Path(__file__).parent / "generated"

client = bigquery.Client(project=PROJECT)

TXN_SCHEMA = [
    bigquery.SchemaField("txn_id", "STRING"),
    bigquery.SchemaField("timestamp", "TIMESTAMP"),
    bigquery.SchemaField("amount", "FLOAT"),
    bigquery.SchemaField("currency", "STRING"),
    bigquery.SchemaField("originator", "STRING"),
    bigquery.SchemaField("beneficiary", "STRING"),
    bigquery.SchemaField("beneficiary_country", "STRING"),
    bigquery.SchemaField("vendor_id", "STRING"),
    bigquery.SchemaField("channel", "STRING"),
    bigquery.SchemaField("existing_alert_flag", "BOOL"),
]
LABELS_SCHEMA = [
    bigquery.SchemaField("txn_id", "STRING"),
    bigquery.SchemaField("label", "STRING"),
    bigquery.SchemaField("detail", "STRING"),
]


def load(table, schema, path):
    table_id = f"{PROJECT}.{DATASET}.{table}"
    rows = [json.loads(l) for l in open(path)]
    job_config = bigquery.LoadJobConfig(
        schema=schema, write_disposition="WRITE_TRUNCATE",
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    job = client.load_table_from_json(rows, table_id, job_config=job_config)
    job.result()
    print(f"Loaded {len(rows)} rows -> {table_id}")


if __name__ == "__main__":
    load(TXN_TABLE, TXN_SCHEMA, GEN / "transactions.jsonl")
    load(LABELS_TABLE, LABELS_SCHEMA, GEN / "labels.jsonl")
