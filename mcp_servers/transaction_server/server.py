"""
Transaction MCP Server (Layer 2).

Exposes COMPLIANCE-SHAPED, read-only, parameterized tools over the BigQuery
transactions table. The model never sees raw SQL — it calls narrow tools that
return compact results (token optimization + injection surface reduction).

Transport: streamable-http (works locally and on Cloud Run).
Auth on Cloud Run: the service is deployed with --no-allow-unauthenticated, so
only callers presenting a valid Google-signed OIDC id-token for an allowed SA
can invoke it (server-to-server OAuth). See scripts/03_deploy_mcp.sh.
"""
import os
from datetime import datetime, timedelta

from fastmcp import FastMCP
from google.cloud import bigquery

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
DATASET = os.environ.get("BQ_DATASET", "reguguard")
TXN_TABLE = os.environ.get("BQ_TXN_TABLE", "transactions")
PORT = int(os.environ.get("PORT", "8080"))

mcp = FastMCP("transaction-compliance")
_bq = bigquery.Client(project=PROJECT) if PROJECT else None
_TABLE = f"`{PROJECT}.{DATASET}.{TXN_TABLE}`"


def _run(sql: str, params: list) -> list[dict]:
    if _bq is None:
        raise RuntimeError("BigQuery client not configured (set GOOGLE_CLOUD_PROJECT).")
    cfg = bigquery.QueryJobConfig(query_parameters=params)
    return [dict(r) for r in _bq.query(sql, job_config=cfg).result()]


@mcp.tool()
def list_flagged_transactions(start_date: str, end_date: str, min_amount: float = 0.0) -> list[dict]:
    """List transactions already flagged by monitoring within [start_date, end_date] (ISO dates),
    optionally filtered to amount >= min_amount. Returns compact rows for triage."""
    sql = f"""
        SELECT txn_id, timestamp, amount, currency, originator, beneficiary,
               beneficiary_country, vendor_id, channel
        FROM {_TABLE}
        WHERE existing_alert_flag = TRUE
          AND timestamp BETWEEN @start AND @end
          AND amount >= @min_amount
        ORDER BY timestamp DESC
        LIMIT 200
    """
    params = [
        bigquery.ScalarQueryParameter("start", "TIMESTAMP", f"{start_date}T00:00:00Z"),
        bigquery.ScalarQueryParameter("end", "TIMESTAMP", f"{end_date}T23:59:59Z"),
        bigquery.ScalarQueryParameter("min_amount", "FLOAT64", min_amount),
    ]
    return _run(sql, params)


@mcp.tool()
def get_transaction(txn_id: str) -> dict:
    """Fetch a single transaction by its exact txn_id (e.g. 'T-000123')."""
    sql = f"SELECT * FROM {_TABLE} WHERE txn_id = @id LIMIT 1"
    rows = _run(sql, [bigquery.ScalarQueryParameter("id", "STRING", txn_id)])
    return rows[0] if rows else {"error": "not_found", "txn_id": txn_id}


@mcp.tool()
def get_vendor_history(vendor_id: str, lookback_days: int = 90) -> dict:
    """Aggregate a vendor's recent transaction history for context: count, total, distinct
    beneficiaries and countries over the lookback window."""
    since = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat() + "Z"
    sql = f"""
        SELECT COUNT(*) AS txn_count, SUM(amount) AS total_amount,
               COUNT(DISTINCT beneficiary) AS distinct_beneficiaries,
               COUNT(DISTINCT beneficiary_country) AS distinct_countries
        FROM {_TABLE}
        WHERE vendor_id = @vid AND timestamp >= @since
    """
    params = [
        bigquery.ScalarQueryParameter("vid", "STRING", vendor_id),
        bigquery.ScalarQueryParameter("since", "TIMESTAMP", since),
    ]
    rows = _run(sql, params)
    out = rows[0] if rows else {}
    out["vendor_id"] = vendor_id
    return out


@mcp.tool()
def find_related_transactions(beneficiary: str, window_hours: int = 72) -> list[dict]:
    """Return transactions to the same beneficiary within a recent window — used to detect
    structuring (sub-threshold clustering) and velocity patterns."""
    since = (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z"
    sql = f"""
        SELECT txn_id, timestamp, amount, originator, beneficiary, vendor_id
        FROM {_TABLE}
        WHERE beneficiary = @ben AND timestamp >= @since
        ORDER BY timestamp
        LIMIT 100
    """
    params = [
        bigquery.ScalarQueryParameter("ben", "STRING", beneficiary),
        bigquery.ScalarQueryParameter("since", "TIMESTAMP", since),
    ]
    return _run(sql, params)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=PORT)
