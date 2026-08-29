"""
Deploy the ReguGuard root_agent to Vertex AI Agent Engine with tracing enabled.

Preferred (works with ADK 2.x packaging):

    source .env
    export STAGING_BUCKET="${STAGING_BUCKET:-gs://$GOOGLE_CLOUD_PROJECT-reguguard-staging}"
    adk deploy agent_engine \\
      --project="$GOOGLE_CLOUD_PROJECT" \\
      --region="$GOOGLE_CLOUD_LOCATION" \\
      --display_name="ReguGuard-AML-Swarm" \\
      --otel_to_cloud \\
      agents/reguguard

This script is the SDK path (VERIFY). It builds a local wheel so cloudpickle can
import `reguguard` on the remote runtime. GOOGLE_CLOUD_PROJECT/LOCATION env vars
are reserved on Agent Engine and must not be passed in env_vars.
"""
import os
import subprocess
import sys
from pathlib import Path

_AGENTS_DIR = Path(__file__).resolve().parent
_ROOT = _AGENTS_DIR.parent
if str(_AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENTS_DIR))

import vertexai
from vertexai import agent_engines

from reguguard.agent import root_agent

PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
STAGING_BUCKET = os.environ.get("STAGING_BUCKET", f"gs://{PROJECT}-reguguard-staging")
SA_AGENT = os.environ.get(
    "SA_AGENT",
    f"reguguard-agent@{PROJECT}.iam.gserviceaccount.com",
)


def _ensure_wheel() -> Path:
    wheel_dir = _AGENTS_DIR / ".ae_wheels"
    wheel_dir.mkdir(exist_ok=True)
    for old in wheel_dir.glob("reguguard-*.whl"):
        old.unlink()
    subprocess.check_call(
        [sys.executable, "-m", "pip", "wheel", str(_AGENTS_DIR), "-w", str(wheel_dir), "--no-deps"],
        cwd=str(_ROOT),
    )
    wheels = sorted(wheel_dir.glob("reguguard-*.whl"))
    if not wheels:
        raise RuntimeError("Failed to build reguguard wheel for Agent Engine packaging")
    return wheels[-1]


vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=STAGING_BUCKET)

app = agent_engines.AdkApp(agent=root_agent, enable_tracing=True)
wheel = _ensure_wheel()

remote = agent_engines.create(
    app,
    display_name="ReguGuard-AML-Swarm",
    description="AML/sanctions multi-agent swarm with MCP + Model Armor + HITL",
    requirements=[
        "google-adk>=1.0.0",
        "google-cloud-aiplatform[adk,agent_engines]>=1.125.0",
        "fastmcp>=2.0.0",
        "google-cloud-bigquery>=3.20.0",
        "google-cloud-modelarmor>=0.1.0",
        "pydantic>=2.0.0",
    ],
    extra_packages=[str(wheel)],
    service_account=SA_AGENT,
    env_vars={
        "GOOGLE_GENAI_USE_VERTEXAI": "true",
        "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
        "ORCHESTRATOR_MODEL": os.environ.get("ORCHESTRATOR_MODEL", "gemini-2.5-pro"),
        "WORKER_MODEL": os.environ.get("WORKER_MODEL", "gemini-2.5-flash"),
        "TRANSACTION_MCP_URL": os.environ.get("TRANSACTION_MCP_URL", ""),
        "SANCTIONS_MCP_URL": os.environ.get("SANCTIONS_MCP_URL", ""),
        "RAG_CORPUS_RESOURCE": os.environ.get("RAG_CORPUS_RESOURCE", ""),
        "MODEL_ARMOR_TEMPLATE": os.environ.get("MODEL_ARMOR_TEMPLATE", ""),
        "MODEL_ARMOR_ENABLED": os.environ.get("MODEL_ARMOR_ENABLED", "false"),
        "HITL_RISK_THRESHOLD": os.environ.get("HITL_RISK_THRESHOLD", "0.80"),
    },
)
print("Deployed Agent Engine resource:", remote.resource_name)
print(">>> Set in .env: AGENT_ENGINE_RESOURCE=\"%s\"" % remote.resource_name)
