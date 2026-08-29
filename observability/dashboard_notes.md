# Observability (Layer 6) — what to show and how

## Traces (Cloud Trace)
- Agent Engine with `enable_tracing=True` emits spans automatically for every
  agent step and tool call. Open **Cloud Trace > Trace explorer**, filter by the
  Agent Engine service, and open one audit's trace to show the delegation path
  (orchestrator -> extraction -> policy -> synthesis) and per-tool latency.
- For Cloud Run agent deploys, enable OpenTelemetry export or view request traces.

## Metrics to surface in the pitch
- **Tokens per audit** (before vs after context caching) — pull from model call
  logs / Vertex token metrics. Show the drop when the policy corpus is cached.
- **Tool-call latency** — from trace spans (MCP round-trips).
- **A2A/delegation path** — visible as nested spans.

## Logs (Cloud Logging)
- Filter `jsonPayload.control="model_armor"` to show DENY events from the security
  callback — this is your live "attack blocked" evidence.
- Query example:
    resource.type="cloud_run_revision" AND textPayload=~"DENY tool call"

## Suggested dashboard tiles (Cloud Monitoring)
1. Audits processed (count)
2. Avg tokens / audit (line, cache on vs off)
3. Avg tool latency (line)
4. Model Armor denials (count)
5. Eval precision / recall (from eval_results.json, shown as a scorecard slide)
