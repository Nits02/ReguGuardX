# ReguGuard — one-word entrypoints. Run `make help`.
include .env
export

.PHONY: help venv install data bq rag armor mcp-local agent-local eval deploy-mcp deploy-agent smoke clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

venv: ## Create virtualenv
	python -m venv .venv && . .venv/bin/activate && pip install -U pip

install: ## Install deps
	pip install -r requirements.txt

data: ## Generate synthetic transactions + labels + policies
	python data/generate_data.py

bq: ## Load generated data into BigQuery
	python data/load_bigquery.py

rag: ## Create Vertex RAG corpus and import policy docs
	python scripts/02_create_rag_corpus.py

armor: ## Create Model Armor template
	bash scripts/06_create_model_armor.sh

mcp-local: ## Run both MCP servers locally
	bash scripts/run_mcp_local.sh

agent-local: ## Launch ADK dev UI locally
	adk web agents

eval: ## Run the ADK evaluation suite
	bash eval/run_eval.sh

deploy-mcp: ## Build + deploy MCP servers to Cloud Run
	bash scripts/03_deploy_mcp.sh

deploy-agent: ## Deploy agent to Agent Engine (or Cloud Run)
	bash scripts/04_deploy_agent.sh

smoke: ## Smoke test the deployed stack
	bash scripts/05_smoke_test.sh

clean:
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
