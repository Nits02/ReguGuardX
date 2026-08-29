"""Structured output schema for the final disposition (Synthesis agent)."""
from typing import List, Literal
from pydantic import BaseModel, Field


class Violation(BaseModel):
    type: str = Field(description="e.g. sanctions_hit, structuring, pep_counterparty, velocity_anomaly")
    rule_citation: str = Field(description="Policy rule ID grounding this finding, e.g. AML-SAN-03")
    evidence: str = Field(description="Concrete evidence from transaction/vendor/screening data")


class Disposition(BaseModel):
    audit_id: str
    txn_id: str
    disposition: Literal["escalate", "clear", "request_info"]
    risk_score: float = Field(ge=0.0, le=1.0)
    violations: List[Violation] = []
    requires_human_review: bool = False
    rationale: str = ""
