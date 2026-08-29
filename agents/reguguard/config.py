"""Central config pulled from environment (see .env.example)."""
import os

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

ORCHESTRATOR_MODEL = os.environ.get("ORCHESTRATOR_MODEL", "gemini-2.5-pro")
WORKER_MODEL = os.environ.get("WORKER_MODEL", "gemini-2.5-flash")

TRANSACTION_MCP_URL = os.environ.get("TRANSACTION_MCP_URL", "http://localhost:8080/mcp")
SANCTIONS_MCP_URL = os.environ.get("SANCTIONS_MCP_URL", "http://localhost:8081/mcp")

RAG_CORPUS_RESOURCE = os.environ.get("RAG_CORPUS_RESOURCE", "")

MODEL_ARMOR_TEMPLATE = os.environ.get("MODEL_ARMOR_TEMPLATE", "")
MODEL_ARMOR_ENABLED = os.environ.get("MODEL_ARMOR_ENABLED", "false").lower() == "true"

HITL_RISK_THRESHOLD = float(os.environ.get("HITL_RISK_THRESHOLD", "0.80"))
