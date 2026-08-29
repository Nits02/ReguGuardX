# ReguGuard — Demo-Day Golden Path (7 minutes)

Rehearse this exact sequence. Have two browser tabs ready: **ADK/Agent Engine UI** and **Cloud Trace/Logging**. Pre-warm the services (send one throwaway audit) so there are no cold-start pauses.

| # | Beat | What you do | What the judges see | Rubric hit |
|---|------|-------------|---------------------|-----------|
| 1 | **The pain (30s)** | State AML false-positive rates (>90%) and analyst-hour cost; give your one-line ROI model. | A crisp, quantified business problem. | Use-Case 25% |
| 2 | **Live clean audit (60s)** | Run `Audit T-000000`. | Orchestrator delegates → extraction → policy → synthesis; returns `clear`. | Architecture 15% |
| 3 | **Live violation (75s)** | Run an audit on a sanctions txn_id. | Disposition `escalate` with **rule citations** (AML-SAN-03) pulled from RAG. | Reliability 15%, Use-Case 25% |
| 4 | **Break it #1 (45s)** | `curl` the private MCP with no token → 403. | Per-tool IAM denial. | Security 30% |
| 5 | **Break it #2 (45s)** | Send the prompt-injection audit request. | Model Armor **DENY**; show the log line. | Security 30% |
| 6 | **Human-in-the-loop (60s)** | Trigger a critical case; it pauses with a HITL ticket; you approve; it resumes. | Interruptible, stateful, governed workflow. | Reliability 15% |
| 7 | **Prove it (45s)** | Show the Cloud Trace delegation path + the precision/recall matrix + tokens-with-cache. | Empirical reliability + optimization. | Security 30%, Reliability 15% |
| 8 | **Future value (30s)** | One slide: distillation roadmap → cheaper/faster student model; EPAM marketplace accelerator. | Long-term org fit and ROI. | Use-Case 25% |

## Backup plan (if cloud flakes)
- Keep MCP servers running **locally** as a fallback (`make mcp-local`) and demo via `adk web` against localhost.
- Pre-capture screenshots of the Trace path, the Model Armor DENY log, and `eval_results.json` so beats 5–7 survive a network issue.
- If Model Armor isn't wired, lead beat 5 with the parameterized-query defense (no raw SQL reaches BigQuery) + the IAM denial as your two-layer security story.

## One-liners to have on a slide
- "Agents never touch a database — only governed MCP tools. New legacy source = new MCP server, zero agent changes."
- "Every tool call passes identity → gateway → Model Armor before it runs."
- "Sanctions hits can never auto-clear — the swarm pauses for a human by policy AML-HITL-06."
- "Reliability isn't a claim — here's the precision/recall matrix on planted violations."
