# ReguGuard — Exhaustive End-to-End Build & Deploy Runbook
*Provision → Develop → Test → Deploy → Demo. Follow top to bottom.*

This runbook builds the working system described in the Solution Architecture Document. It is organized to match the SAD's phases, and **each phase ends with a test gate** so you always have a running system. Commands assume macOS/Linux with `bash`. Windows users: use WSL.

> **Reality note on platform naming.** Google's agent platform (Gemini Enterprise / Agent Platform / Vertex AI Agent Builder / ADK / Agent Engine) and the newest governance products (Agent Gateway, Agent Identity, Model Armor) evolved rapidly across 2025–2026. Where a CLI/API surface is volatile, this runbook says **VERIFY** and gives a console fallback. The **core path always works**; the managed-governance extras degrade gracefully.

---

## 0. Prerequisites (local workstation)

Install and verify:

```bash
# Google Cloud CLI
gcloud version            # >= 470 recommended
# Python 3.12+
python --version
# Docker (for local container builds; Cloud Build is used in-cloud so optional)
docker --version
# Terraform (optional but recommended)
terraform version         # >= 1.5
# git
git --version
```

Accounts / access you need:
- A **Google Cloud project** with **billing enabled** and **Owner** or (Editor + Project IAM Admin + Service Account Admin).
- Rights to enable APIs, create service accounts, deploy Cloud Run, use Vertex AI.
- **Gemini Enterprise / Agent Platform access** in the project (confirm in console — this is the item most likely to be gated in a hackathon sandbox).

**Access decision gate (do this first):** If you can deploy Cloud Run + use Vertex AI Agent Engine → proceed with the full runbook. If you only have the Gemini Enterprise *app* with no deploy rights → stop and switch to Stream 3 (see the strategy report); Phases 2/4/5 below need deploy access.

---

## 1. Get the code & create the repo

```bash
# Unzip the provided scaffold, or init fresh:
cd reguguard
git init
git add .
git commit -m "chore: ReguGuard scaffold"

# (optional) push to your company Git
# git remote add origin <your-repo-url> && git branch -M main && git push -u origin main
```

Create your environment file:

```bash
cp .env.example .env
# edit .env: set GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, model SKUs, SA emails
```

**VERIFY the model names** available to you (do NOT hardcode a name you haven't confirmed):

```bash
gcloud ai models list --region="$GOOGLE_CLOUD_LOCATION" 2>/dev/null | head
# or check the console: Vertex AI > Model Garden. Set ORCHESTRATOR_MODEL / WORKER_MODEL in .env.
```

Create and populate the virtualenv:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

---

## PHASE 0 — Foundations (provision GCP)

### 0.1 Authenticate

```bash
gcloud auth login
gcloud config set project "$(grep GOOGLE_CLOUD_PROJECT .env | cut -d'"' -f2)"
source .env
bash scripts/00_setup_gcp.sh    # sets project/region + application-default creds
```

### 0.2 Provision infrastructure — Option A (Terraform, recommended)

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # edit project_id/region
terraform init
terraform plan
terraform apply    # enables APIs, creates 2 service accounts + IAM, BigQuery dataset
terraform output   # note agent_sa_email, mcp_sa_email
cd ../../
```

Copy the two SA emails into `.env` (`SA_AGENT`, `SA_MCP`).

### 0.2 Provision infrastructure — Option B (no Terraform)

```bash
bash scripts/01_enable_apis.sh

# Service accounts
gcloud iam service-accounts create reguguard-agent --display-name="ReguGuard Agent"
gcloud iam service-accounts create reguguard-mcp   --display-name="ReguGuard MCP"

PROJECT="$GOOGLE_CLOUD_PROJECT"
AGENT="reguguard-agent@$PROJECT.iam.gserviceaccount.com"
MCP="reguguard-mcp@$PROJECT.iam.gserviceaccount.com"

for R in roles/aiplatform.user roles/cloudtrace.agent roles/logging.logWriter roles/modelarmor.user roles/run.invoker; do
  gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$AGENT" --role="$R";
done
for R in roles/bigquery.dataViewer roles/bigquery.jobUser roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$MCP" --role="$R";
done

# BigQuery dataset
bq --location="$GOOGLE_CLOUD_LOCATION" mk --dataset "$PROJECT:reguguard"
```

### 0.3 Generate + load data

```bash
source .env
python data/generate_data.py         # -> data/generated/{transactions,labels}.jsonl (504 rows)
python data/load_bigquery.py         # -> BigQuery reguguard.transactions + reguguard.labels
```

### ✅ Phase 0 test gate

```bash
bq query --use_legacy_sql=false \
 'SELECT label, COUNT(*) c FROM `'"$GOOGLE_CLOUD_PROJECT"'.reguguard.labels` GROUP BY label ORDER BY c DESC'
# Expect: clean ~400, velocity_anomaly ~44, structuring ~35, sanctions_hit 15, pep_counterparty 10
```
Also start team certifications now (runs in parallel with everything below).

---

## PHASE 1 — Core vertical slice (MVP): one MCP server + one agent

Goal: prove one agent can reach real data through one governed MCP tool. **This is your fallback demo — protect it.**

### 1.1 Run the Transaction MCP server locally

```bash
source .env
cd mcp_servers/transaction_server
GOOGLE_CLOUD_PROJECT="$GOOGLE_CLOUD_PROJECT" BQ_DATASET=reguguard PORT=8080 python server.py &
cd ../../
# Set in .env: TRANSACTION_MCP_URL=http://localhost:8080/mcp
```

### 1.2 Point the agent at just the transaction toolset

For the MVP you can temporarily comment out the policy/synthesis sub-agents in `agents/reguguard/agent.py` and give the root agent the transaction toolset directly, OR just run the data-extraction sub-agent. Then launch the ADK dev UI:

```bash
source .env
adk web agents        # open the printed localhost URL, pick "reguguard"
```

Prompt: `List the flagged transactions between 2025-01-01 and 2025-12-31 with amount over 5000.`

### ✅ Phase 1 test gate
- The agent calls `list_flagged_transactions` via MCP and returns real BigQuery rows.
- You can see the tool call in the ADK dev UI's trace/events pane.

---

## PHASE 2 — Multi-agent swarm (ADK-native)

Goal: the full orchestrator → extraction → policy → synthesis flow producing a disposition.

### 2.1 Run both MCP servers locally

```bash
source .env
( cd mcp_servers/transaction_server && PORT=8080 GOOGLE_CLOUD_PROJECT="$GOOGLE_CLOUD_PROJECT" BQ_DATASET=reguguard python server.py & )
( cd mcp_servers/sanctions_server  && PORT=8081 WATCHLIST_PATH="$PWD/mcp_servers/sanctions_server/sample_watchlist.csv" python server.py & )
# .env: TRANSACTION_MCP_URL=http://localhost:8080/mcp  SANCTIONS_MCP_URL=http://localhost:8081/mcp
```

### 2.2 Run the full swarm

Restore the full `root_agent` (all three `sub_agents`) if you edited it in Phase 1.

```bash
source .env
adk web agents
```

Prompts to try:
- A clean case: `Audit transaction T-000000 and give me a disposition.`
- A sanctions case: pick a `sanctions_hit` txn_id (query BigQuery labels) → expect **escalate**.

Find labeled txn_ids:
```bash
bq query --use_legacy_sql=false \
 'SELECT txn_id,label FROM `'"$GOOGLE_CLOUD_PROJECT"'.reguguard.labels` WHERE label!="clean" LIMIT 10'
```

### 2.3 Localized retry test (reliability)
Kill the transaction MCP mid-run and confirm the orchestrator retries that step (per the root instruction) rather than restarting the whole audit.

### ✅ Phase 2 test gate
- End-to-end audit returns a structured disposition (escalate/clear/request_info) with a rationale.
- Delegation path visible: orchestrator → extraction → policy → synthesis.

---

## PHASE 3 — Grounding (Vertex RAG) + context caching

Goal: every violation cites a real policy rule; dense rulebook is cached for cost/latency.

### 3.1 Create the RAG corpus and import policies

```bash
source .env
python scripts/02_create_rag_corpus.py
# copy the printed RAG_CORPUS_RESOURCE into .env
```
> **VERIFY**: `vertexai.rag` vs `vertexai.preview.rag` import path depends on SDK version; the script tries both. If import chunking args error, remove them (defaults are fine).

### 3.2 (Optional) Create the policy context cache

```bash
source .env
python -m agents.reguguard.security.context_cache
# note the cache resource name; attach it to the policy agent's model in a follow-up
# iteration if you want to demo the token drop. (Caching wiring is model-version sensitive — VERIFY.)
```

### 3.3 Re-run the swarm
Now the Policy agent should include citations like `AML-SAN-03`, `AML-STR-02`.

### ✅ Phase 3 test gate
- Dispositions contain rule citations traceable to `data/policies/*.md`.
- (If cache wired) capture tokens/audit with cache ON vs OFF for the pitch.

---

## PHASE 4 — Security & governance (the differentiator — protect this)

Goal: two visible denials + private MCP services + per-tool IAM.

### 4.1 Deploy MCP servers to Cloud Run as PRIVATE services

```bash
source .env
bash scripts/03_deploy_mcp.sh
# copy the printed TRANSACTION_MCP_URL / SANCTIONS_MCP_URL (…/mcp) into .env
```
This deploys `--no-allow-unauthenticated`, runs them as `reguguard-mcp` SA, and grants **only** `reguguard-agent` the `run.invoker` role → per-tool IAM. The agent's `mcp_tools.py` auto-mints an OIDC id-token for server-to-server OAuth.

### 4.2 Create the Model Armor template

```bash
source .env
bash scripts/06_create_model_armor.sh
# copy MODEL_ARMOR_TEMPLATE into .env and set MODEL_ARMOR_ENABLED=true
```
> **VERIFY**: if the `gcloud model-armor` subcommand differs, create the template in **Console → Security → Model Armor** with prompt-injection/jailbreak + malicious-URI + sensitive-data filters, then paste its resource name into `.env`. The agent screens every tool call through it via `security/model_armor.py`.

### 4.3 (Target architecture) Managed Agent Gateway + Agent Identity
In a full Gemini Enterprise deployment you route agent egress through the **managed Agent Gateway** (REQUEST_AUTHZ = per-tool IAM, CONTENT_AUTHZ = Model Armor) and assign **Agent Identity** per agent with mTLS. **VERIFY** current setup steps in the Agent Platform console; the primitive implementation in 4.1–4.2 delivers the same enforcement semantics for the demo, so this is an enhancement, not a blocker. Document it on your architecture slide either way.

### 4.4 The two denials (rehearse these for demo)
See `eval/attack_cases.md`. Summary:
```bash
source .env
# (1) Unauthorized MCP call -> 403
curl -s -o /dev/null -w "no-auth: %{http_code}\n" "$TRANSACTION_MCP_URL"
TOKEN=$(gcloud auth print-identity-token --audiences="${TRANSACTION_MCP_URL%/mcp}")
curl -s -o /dev/null -w "auth: %{http_code}\n" -H "Authorization: Bearer $TOKEN" "$TRANSACTION_MCP_URL"

# (2) Prompt-injection audit request in adk web -> Model Armor DENY (see logs)
```

### ✅ Phase 4 test gate
- No-auth MCP call returns 403; authed call reaches the server.
- A poisoned audit prompt is blocked; a `control=model_armor` DENY appears in Cloud Logging.

---

## PHASE 5 — State, memory & human-in-the-loop

Goal: critical violation pauses for approval, then resumes.

### 5.1 Deploy to Agent Engine (managed Sessions + Memory Bank + tracing)

```bash
source .env
# create a staging bucket if needed
gsutil mb -l "$GOOGLE_CLOUD_LOCATION" "gs://$GOOGLE_CLOUD_PROJECT-reguguard-staging" || true
export STAGING_BUCKET="gs://$GOOGLE_CLOUD_PROJECT-reguguard-staging"
python agents/deploy_agent_engine.py
# note the Agent Engine resource_name
```
> **VERIFY**: `reasoning_engines.AdkApp` / `agent_engines.create` signatures and the `enable_tracing` flag are SDK-version sensitive. If `AdkApp` import differs, check `from vertexai.preview import reasoning_engines` vs the current module and adjust.

### 5.2 HITL flow
The Synthesis agent calls `request_human_approval` (a `LongRunningFunctionTool`) on critical/sanctions cases. The run yields with a pending ticket; supply the approval as the tool's completed response to resume. For the demo you can:
- drive it interactively in `adk web` (approve when prompted), or
- script the resume by sending the function-response back through the Runner.

Memory Bank (via Agent Engine) persists the paused session so resume is deterministic; rollback = restore a prior session state.

### ✅ Phase 5 test gate
- A sanctions/critical audit **pauses** with a HITL ticket and does not finalize.
- Supplying approval **resumes** and yields the final escalate disposition.

---

## PHASE 6 — Observability & evaluation (cheap points, high credibility)

### 6.1 Traces & logs
- Agent Engine tracing is on (`enable_tracing=True`). Open **Cloud Trace → Trace explorer**, open one audit, screenshot the delegation path + per-tool latency.
- Model Armor denials: **Cloud Logging**, filter `textPayload=~"DENY tool call"` or `jsonPayload.control="model_armor"`.
- See `observability/dashboard_notes.md` for suggested Monitoring tiles.

### 6.2 Run the evaluation

```bash
source .env
bash eval/run_eval.sh
# -> prints per-case predictions + a precision/recall/false-positive matrix
# -> writes eval/eval_results.json  (use the matrix as a pitch slide)
```

### ✅ Phase 6 test gate
- `eval/eval_results.json` exists with recall ≥ 0.8 on planted violations.
- You have a Trace screenshot and a Model Armor DENY log line.

---

## PHASE 7 — Distillation roadmap (SLIDE ONLY — do not build)
One slide: capture successful reasoning traces → PEFT/LoRA distillation to a smaller Flash/Gemma "student" → route routine, high-volume checks to it for cost/latency. Frame as the long-term EPAM accelerator ROI. **Zero code in-window.**

---

## A2A boundary (extensibility points — do after Phase 2 is solid)

You demonstrate A2A without distributing the whole swarm:

1. **Publish the swarm as an A2A agent.** Expose an Agent Card (well-known metadata describing capabilities) so an external orchestrator can call ReguGuard. ADK/Agent Engine can surface an A2A endpoint; **VERIFY** the current `to_a2a()` / A2A server helper in your ADK version.
2. **Run the sanctions specialist as a standalone A2A service** on Cloud Run and have the orchestrator delegate to it over JSON-RPC 2.0, showing `submitted → working → completed` task states.

Talk to this on the architecture slide even if only #1 is wired live — it proves the interoperability story for the Architecture & Extensibility criterion.

---

## Cost hygiene (avoid sandbox surprises)
- Set Cloud Run `--max-instances` low (done: 3) and `--min-instances 0`.
- Delete the Agent Engine + Cloud Run services after the demo:
```bash
gcloud run services delete reguguard-transaction-mcp --region "$GOOGLE_CLOUD_LOCATION" -q
gcloud run services delete reguguard-sanctions-mcp  --region "$GOOGLE_CLOUD_LOCATION" -q
# delete Agent Engine via console or agent_engines API using the resource_name
```
- Context caching and short eval runs keep token spend down.

---

## Troubleshooting quick table

| Symptom | Likely cause | Fix |
|---|---|---|
| `ADK MCP import failed` | ADK version renamed the connection-params class | Check `mcp_tools.py` fallbacks; `pip show google-adk`; align class name |
| MCP call 403 from agent | agent SA lacks `run.invoker` on the service, or wrong audience | re-run the IAM binding in `03_deploy_mcp.sh`; audience must be service root (no `/mcp`) |
| RAG returns nothing | corpus empty / import still processing / wrong resource name | wait for import; re-check `RAG_CORPUS_RESOURCE` |
| Model Armor create fails | gcloud subcommand differs by SDK | create template in console; set `MODEL_ARMOR_TEMPLATE` |
| Agent Engine deploy errors | `AdkApp`/`create` signature changed | verify `reasoning_engines`/`agent_engines` imports for your SDK |
| Model name error | SKU not available / renamed | `gcloud ai models list`; set real SKU in `.env` |
| BigQuery permission denied | MCP SA missing dataViewer/jobUser | re-apply IAM roles |

---

## Definition of Done (what "working" means at the demo)
1. Live audit over BigQuery data returns a rule-cited disposition. (Phases 1–3)
2. Two governance denials shown live + in logs. (Phase 4)
3. A critical case pauses for human approval and resumes. (Phase 5)
4. Trace screenshot + precision/recall matrix on screen. (Phase 6)
5. Architecture slide covering MCP decoupling, A2A boundary, managed Agent Gateway/Identity target, and the distillation roadmap. (Phases 4/7 + A2A)
