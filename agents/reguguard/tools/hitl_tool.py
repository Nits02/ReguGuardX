"""
Human-in-the-loop pause/resume (Layer 4).

Implemented as an ADK long-running tool: when a CRITICAL disposition is reached,
the agent calls request_human_approval(...). The tool returns status='pending'
and the run yields. An external system (or the demo script) later supplies the
approval as the tool's completed response, and the agent resumes deterministically.
"""
from google.adk.tools import LongRunningFunctionTool


def request_human_approval(audit_id: str, txn_id: str, risk_score: float, summary: str) -> dict:
    """Request a compliance officer's approval for a critical disposition. Returns a
    pending ticket; the run pauses until an approval decision is supplied."""
    return {
        "status": "pending",
        "ticket_id": f"HITL-{audit_id}-{txn_id}",
        "audit_id": audit_id,
        "txn_id": txn_id,
        "risk_score": risk_score,
        "summary": summary,
        "message": "Awaiting human compliance-officer approval before final disposition.",
    }


human_approval_tool = LongRunningFunctionTool(func=request_human_approval)
