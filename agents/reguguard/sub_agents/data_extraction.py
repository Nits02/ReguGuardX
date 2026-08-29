"""Data Extraction Agent — structured retrieval specialist (Layer 1 worker)."""
from google.adk.agents import LlmAgent
from .. import config
from ..tools.mcp_tools import transaction_toolset
from ..security.model_armor import before_tool_callback

INSTRUCTION = """You are the Data Extraction Agent for an AML compliance swarm.
Your ONLY job is to retrieve and normalize transaction and vendor data using the
available transaction tools. You do NOT make compliance decisions.

Given a transaction id or an alert, you MUST call tools before transferring:
1. get_transaction(txn_id)
2. get_vendor_history(vendor_id from the transaction)
3. find_related_transactions(beneficiary from the transaction)

Then return the collected facts as compact structured JSON (never invent data; if a
tool returns not_found, say so). After emitting that JSON, transfer to
policy_assessment_agent so the audit can continue. Do not transfer until the tools
have been called.
"""

def build():
    return LlmAgent(
        name="data_extraction_agent",
        model=config.WORKER_MODEL,
        description="Retrieves transaction, vendor, and related-transaction data via MCP tools.",
        instruction=INSTRUCTION,
        tools=[transaction_toolset()],
        before_tool_callback=before_tool_callback,
    )
