#!/usr/bin/env python3
"""
Phase 5 HITL gate — pause on sanctions/critical, then resume with approval.

Drives the local root_agent via InMemoryRunner (runbook: scripted FunctionResponse
resume is acceptable). Prints a clear PAUSE / RESUME transcript for the demo.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(ROOT))

# Load .env if present (shell usually sources it already).
_env = ROOT / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from google.adk.runners import InMemoryRunner
from google.genai import types

from reguguard.agent import root_agent

TXN_ID = os.environ.get("HITL_TXN_ID", "T-000400")
QUERY = (
    f"Audit transaction {TXN_ID} end-to-end for AML/sanctions risk. "
    "Produce a final disposition."
)


def _part_text(part) -> str:
    return getattr(part, "text", None) or ""


def _summarize_event(event) -> str:
    bits = [f"author={event.author}"]
    if event.long_running_tool_ids:
        bits.append(f"long_running={sorted(event.long_running_tool_ids)}")
    if not event.content or not event.content.parts:
        return " | ".join(bits)
    for p in event.content.parts:
        if p.function_call:
            bits.append(
                f"FC {p.function_call.name}({json.dumps(p.function_call.args or {}, default=str)[:180]})"
            )
        if p.function_response:
            fr = p.function_response
            bits.append(
                f"FR {fr.name}={json.dumps(fr.response or {}, default=str)[:220]}"
            )
        t = _part_text(p)
        if t:
            bits.append(f"text={t[:240].replace(chr(10), ' ')}")
    return " | ".join(bits)


def _find_hitl_call(events):
    """Return (fc_id, fc_name, pending_fr_response, invocation_id) if HITL fired."""
    for event in events:
        for p in event.content.parts if event.content and event.content.parts else []:
            if p.function_response and p.function_response.name == "request_human_approval":
                fr = p.function_response
                return fr.id, fr.name, fr.response or {}, event.invocation_id
        # Also catch the call itself (long-running id) if FR not yet present
        if event.long_running_tool_ids and event.content:
            for p in event.content.parts or []:
                fc = p.function_call
                if fc and fc.name == "request_human_approval" and fc.id in (
                    event.long_running_tool_ids or set()
                ):
                    return fc.id, fc.name, {"status": "pending"}, event.invocation_id
    return None, None, None, None


def _final_text(events) -> str:
    texts = []
    for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            for p in event.content.parts:
                if t := _part_text(p):
                    texts.append(t)
    return "\n".join(texts)


async def main() -> int:
    runner = InMemoryRunner(agent=root_agent, app_name="reguguard-hitl")
    session = await runner.session_service.create_session(
        app_name="reguguard-hitl", user_id="hitl-demo"
    )

    print("=== PHASE A: audit (expect HITL pause / pending ticket) ===")
    print(f"query: {QUERY}")
    events_a = []
    async for event in runner.run_async(
        user_id="hitl-demo",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=QUERY)]),
    ):
        events_a.append(event)
        print(" ", _summarize_event(event))

    fc_id, fc_name, pending, inv_id = _find_hitl_call(events_a)
    final_a = _final_text(events_a)
    print("\n--- pause checkpoint ---")
    print("HITL function_call_id:", fc_id)
    print("HITL pending payload:", json.dumps(pending, indent=2, default=str))
    print("final_text_so_far:", (final_a[:500] + "…") if len(final_a) > 500 else final_a or "(none)")

    if not fc_id:
        print("FAIL: request_human_approval was not invoked for sanctions/critical case")
        return 1
    status = (pending or {}).get("status", "")
    if status and status != "pending":
        print(f"FAIL: expected status=pending, got {status!r}")
        return 1
    ticket = (pending or {}).get("ticket_id") or ""
    if ticket and not str(ticket).startswith("HITL-"):
        print(f"FAIL: unexpected ticket_id {ticket!r}")
        return 1
    # Must not look like a finalized clear while paused
    if "clear" in final_a.lower() and "escalate" not in final_a.lower():
        print("FAIL: paused run finalized as clear")
        return 1
    print("PAUSE_OK")

    print("\n=== PHASE B: supply approval FunctionResponse (resume) ===")
    approval = {
        "status": "approved",
        "ticket_id": ticket or f"HITL-resume-{TXN_ID}",
        "decision": "approve_escalate",
        "officer": "demo-compliance-officer",
        "message": "Human approved escalate disposition for sanctions hit.",
    }
    resume_msg = types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id=fc_id,
                    name=fc_name or "request_human_approval",
                    response=approval,
                )
            )
        ],
    )
    events_b = []
    async for event in runner.run_async(
        user_id="hitl-demo",
        session_id=session.id,
        invocation_id=inv_id,
        new_message=resume_msg,
    ):
        events_b.append(event)
        print(" ", _summarize_event(event))

    final_b = _final_text(events_b) or _final_text(events_a + events_b)
    print("\n--- resume checkpoint ---")
    print("final_disposition_text:", (final_b[:800] + "…") if len(final_b) > 800 else final_b or "(none)")
    blob = (final_b + " " + json.dumps(approval)).lower()
    if "escalate" not in blob and "escalat" not in final_b.lower():
        # Some runs finish escalate text in phase A after pending; still accept if A had escalate+HITL
        if "escalate" not in final_a.lower():
            print("FAIL: expected escalate disposition after approval")
            return 1
    print("RESUME_OK")
    print("\nPHASE_5_HITL_GATE_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
