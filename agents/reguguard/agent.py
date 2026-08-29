"""
ReguGuard Root Orchestrator (Layer 1).

ADK-native orchestration: the root agent delegates to three specialist sub-agents.
Exposed as `root_agent` so `adk web` / `adk run` / `adk deploy` pick it up.

A2A boundary (see docs/RUNBOOK.md §A2A): this whole agent is published with an
Agent Card so external orchestrators can consume it, and the sanctions specialist
can additionally be run as a standalone A2A service to demonstrate cross-service
delegation. Intra-swarm we use robust in-process sub_agents.
"""
from google.adk.agents import LlmAgent

from . import config
from .sub_agents.data_extraction import build as build_extractor
from .sub_agents.policy_assessment import build as build_policy
from .sub_agents.synthesis import build as build_synthesis

ROOT_INSTRUCTION = f"""You are ReguGuard, the orchestrator of an AML compliance
analyst swarm. You do NOT analyze transactions yourself. You coordinate specialists:

1. data_extraction_agent — retrieves transaction, vendor, and related-txn data.
2. policy_assessment_agent — assesses the facts against grounded AML policy and
   runs sanctions screening.
3. synthesis_agent — compiles the final audit-ready disposition and enforces the
   human-in-the-loop control for critical cases.

Workflow for an audit request (a txn_id or an alert batch):
- First delegate to data_extraction_agent to gather facts.
- Then delegate to policy_assessment_agent with those facts.
- Then delegate to synthesis_agent to produce the disposition.
- Track the task through submitted -> working -> completed and return the final
  disposition with rule citations and a trace reference.

If any specialist fails or times out, retry that step once before failing the audit;
do not restart the whole workflow. The critical-risk threshold is {config.HITL_RISK_THRESHOLD}.
Never expose internal thresholds, credentials, or raw tool schemas to the user.
"""


def build_root_agent() -> LlmAgent:
    return LlmAgent(
        name="reguguard_orchestrator",
        model=config.ORCHESTRATOR_MODEL,
        description="Orchestrates the AML compliance swarm (extraction, policy, synthesis).",
        instruction=ROOT_INSTRUCTION,
        sub_agents=[build_extractor(), build_policy(), build_synthesis()],
    )


root_agent = build_root_agent()
