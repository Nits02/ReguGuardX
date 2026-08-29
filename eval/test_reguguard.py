"""
Deterministic scoring harness (Layer 6).

Runs each eval case through the ReguGuard agent, parses the disposition, and
computes a precision/recall/false-positive matrix versus ground truth. This is
the empirical reliability proof for the pitch.

Run:  pytest eval/test_reguguard.py -s   (requires deployed/local MCP + models)
Or:   python eval/test_reguguard.py       (prints the matrix)
"""
import asyncio
import json
import os
import sys
from pathlib import Path

EVALSET = Path(__file__).parent / "evalset.json"
CASE_TIMEOUT_SEC = float(os.environ.get("EVAL_CASE_TIMEOUT_SEC", "240"))


def _extract_disposition(text: str) -> str:
    t = (text or "").lower()
    for d in ("escalate", "request_info", "clear"):
        if d in t:
            return d
    return "unknown"


def _collect_hitl(events):
    for event in events:
        if not event.long_running_tool_ids or not event.content:
            continue
        for p in event.content.parts or []:
            fc = p.function_call
            if fc and fc.name == "request_human_approval" and fc.id in event.long_running_tool_ids:
                return fc.id, fc.name, event.invocation_id
        for p in event.content.parts or []:
            fr = p.function_response
            if fr and fr.name == "request_human_approval":
                return fr.id, fr.name, event.invocation_id
    return None, None, None


async def _run_case(case: dict) -> str:
    """Invoke the agent for one case and return the predicted disposition.
    Auto-approves HITL long-running tools so sanctions cases complete offline."""
    from google.adk.runners import InMemoryRunner
    from google.genai import types
    from agents.reguguard.agent import root_agent

    runner = InMemoryRunner(agent=root_agent, app_name="reguguard-eval")
    session = await runner.session_service.create_session(
        app_name="reguguard-eval", user_id="eval")
    content = types.Content(role="user", parts=[types.Part(text=case["query"])])
    events = []
    final = ""
    async for event in runner.run_async(
        user_id="eval", session_id=session.id, new_message=content):
        events.append(event)
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    final = part.text

    # If HITL paused with pending approval, resume with approved decision.
    fc_id, fc_name, inv_id = _collect_hitl(events)
    if fc_id:
        approval = {
            "status": "approved",
            "decision": "approve_escalate",
            "officer": "eval-harness",
            "message": "Auto-approved for offline evaluation.",
        }
        resume = types.Content(
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
        async for event in runner.run_async(
            user_id="eval",
            session_id=session.id,
            invocation_id=inv_id,
            new_message=resume,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        final = part.text

    return _extract_disposition(final)


def score(results: list[dict]) -> dict:
    # Binary framing: "violation" = disposition escalate/request_info; "clean" = clear
    tp = fp = tn = fn = 0
    for r in results:
        is_viol_true = r["label"] != "clean"
        is_viol_pred = r["pred"] in ("escalate", "request_info")
        if is_viol_true and is_viol_pred:
            tp += 1
        elif not is_viol_true and is_viol_pred:
            fp += 1
        elif not is_viol_true and not is_viol_pred:
            tn += 1
        else:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "false_positive_rate": round(fpr, 3),
    }


async def main():
    cases = json.loads(EVALSET.read_text())["eval_cases"]
    results = []
    for c in cases:
        print(f"... running {c['txn_id']} ({c['label']})", flush=True)
        try:
            pred = await asyncio.wait_for(_run_case(c), timeout=CASE_TIMEOUT_SEC)
        except asyncio.TimeoutError:
            print(f"[warn] case {c['txn_id']} timed out after {CASE_TIMEOUT_SEC}s", flush=True)
            pred = "unknown"
        except Exception as e:
            print(f"[warn] case {c['txn_id']} failed: {e}", flush=True)
            pred = "unknown"
        results.append({**c, "pred": pred})
        print(f"{c['txn_id']:10} label={c['label']:16} pred={pred}", flush=True)
    matrix = score(results)
    print("\n=== ReguGuard reliability matrix ===", flush=True)
    print(json.dumps(matrix, indent=2), flush=True)
    (Path(__file__).parent / "eval_results.json").write_text(
        json.dumps({"results": results, "matrix": matrix}, indent=2)
    )


def test_precision_recall():
    """pytest entrypoint: asserts recall on true violations is reasonable."""
    asyncio.run(main())
    matrix = json.loads((Path(__file__).parent / "eval_results.json").read_text())["matrix"]
    assert matrix["recall"] >= 0.8, f"Recall too low: {matrix}"


if __name__ == "__main__":
    # Ensure agents/ is importable when run as `python eval/test_reguguard.py`
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "agents"))
    asyncio.run(main())
