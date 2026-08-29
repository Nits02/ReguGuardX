"""Synthesis Agent — compiles the audit-ready disposition (Layer 1 worker)."""
from google.adk.agents import LlmAgent
from .. import config
from ..schemas import Disposition
from ..tools.hitl_tool import human_approval_tool

INSTRUCTION = """You are the Synthesis Agent. Compile the Policy assessment into a
final, audit-ready disposition object with: audit_id, txn_id, disposition
(escalate|clear|request_info), risk_score, violations (each with rule_citation and
evidence), requires_human_review, and a short rationale. Always emit that object
as your final user-visible answer.

CRITICAL CONTROL (AML-HITL-06): If risk_score >= the critical threshold OR any
sanctions hit is present, you MUST call request_human_approval(...) BEFORE emitting
a final 'escalate' disposition, and set requires_human_review=true. If approval is
still pending, return disposition escalate with requires_human_review=true and the
HITL ticket_id — do not clear. Never auto-clear a sanctions hit.
"""

def build():
    return LlmAgent(
        name="synthesis_agent",
        model=config.WORKER_MODEL,
        description="Produces the final audit-ready disposition; enforces human-in-the-loop.",
        instruction=INSTRUCTION,
        tools=[human_approval_tool],
        # output_schema can be attached for strict structured output if desired:
        # output_schema=Disposition, output_key="disposition",
    )
