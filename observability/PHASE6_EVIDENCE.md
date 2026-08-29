# Phase 6 evidence pack

## Reliability matrix (`eval/eval_results.json`)
```
precision: 1.000
recall:    0.917   (>= 0.8 gate)
f1:        0.957
FPR:       0.000
tp=11 fp=0 tn=3 fn=1
```
One sanctions case (`T-000400`) returned `unknown` (HITL/final-text parse edge); all other planted violations escalated and all cleans cleared.

Re-run:
```bash
source .env && source .venv/bin/activate
export GOOGLE_GENAI_USE_VERTEXAI=true PYTHONUNBUFFERED=1
python -u eval/test_reguguard.py
```

## Cloud Trace
- Console: https://console.cloud.google.com/traces/list?project=hl2-gcpp-ccoe-ge-h-regugu-1745
- Agent Engine playground (otel enabled): https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/us-central1/agent-engines/6351383343673638912/playground?project=hl2-gcpp-ccoe-ge-h-regugu-1745
- Sample captured in `observability/trace_evidence.json` (includes `/mcp` spans from Cloud Run).

Screenshot tip: open Trace explorer → pick a recent audit → expand orchestrator → extraction → policy → synthesis + tool latencies.

## Model Armor DENY
- Cloud Logging filter: `jsonPayload.control="model_armor"`
- Sample entry written during Phase 6 (control=model_armor, action=DENY).
- Local sample: `observability/model_armor_deny_sample.json`

## Known gap
Agent Engine remote still intermittently fails to register MCP tools (`get_transaction not found` — toolset load). Local ADK path + private Cloud Run MCPs are the demo path for Phases 1–4/6 eval; AE resource is deployed with Sessions/Memory/otel for Phase 5 architecture.
