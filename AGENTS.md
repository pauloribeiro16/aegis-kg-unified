# AGENTS.md — AEGIS Knowledge Graph Unified

**Version:** 2.1
**Last Updated:** 2026-04-29  
**Purpose:** Canonical reference for AI coding agents working on this project.

---

## 1. Project Overview

AEGIS-KG-Unified is a standalone knowledge-graph project for regulatory compliance mapping. It combines:

- **AEGIS Regulatory KG** — 5 EU regulations (GDPR, CRA, NIS 2, DORA, AI Act) mapped to a 10×38 security taxonomy (38 SubDomains across 10 Domains).
- **NIST CSF 2.0** — 106 active controls mapped to the same AEGIS SubDomains, enabling cross-framework gap analysis.
- **LLM Agent & Evaluation Pipeline** — A LangGraph ReAct agent that translates natural-language questions into Cypher queries, plus a Minimax-based LLM-as-a-Judge evaluation system with Langfuse tracing.

The graph lives in **Neo4j Community 5.18.1** and is accessed through a **Flask REST API** (read-only) and directly by agent/eval modules.

---

## 2. Technology Stack

| Layer | Technology | Version / Notes |
|-------|-----------|-----------------|
| Graph DB | Neo4j Community | 5.18.1, external Docker container (`d3fend-neo4j`) |
| API | Flask | 3.x, port 5000 |
| Agent Framework | LangGraph + LangChain | ReAct agent with feedback loop |
| Local LLM | Ollama | `ministral-3:latest` at `http://localhost:11434` |
| Judge LLM | Minimax | `MiniMax-M2.7` via LangChain `MiniMaxChat` |
| Observability | Langfuse | Self-hosted v3 (port 3000) |
| Data Format | CSV | Source-of-truth for ETL |
| Python | CPython | 3.11+ |

---

## 3. Repository Structure

```
aegis-kg-unified/
├── aegis_kg/                  # Knowledge Graph core
│   ├── schema/                # Cypher DDL (constraints, indexes, sample data)
│   ├── data/                  # CSV source files (regulations, clauses, mappings, timelines)
│   ├── etl/                   # ETL scripts (numbered load order)
│   ├── api/                   # Flask REST API (app.py)
│   ├── validation/            # Phase-1 validation suite
│   └── queries/               # Stand-alone analysis queries
├── aegis_agents/              # LangGraph ReAct agent
│   ├── agent.py               # AegisAgent class + callback setup
│   ├── config.py              # Neo4j / Ollama / Langfuse configs
│   ├── tracing.py             # Langfuse logging utilities (log_generation, log_span, score_trace)
│   ├── run_agent_eval.py      # Agent-only eval harness (5-dimension judge)
│   ├── graph/                 # LangGraph nodes, router, state, prompts
│   ├── tools/                 # LangChain tools (cypher_query, schema_explorer)
│   ├── feedback/              # QueryRefiner (error / empty / mismatch refinement)
│   └── judge/                 # Agent-specific judge (agent_judge.py)
├── aegis_eval/                # Primary evaluation pipeline
│   ├── run_eval.py            # Main eval runner (agent + Minimax judge + Langfuse)
│   ├── config.py              # NEO4J / OLLAMA / LANGFUSE / MINIMAX configs
│   ├── schema_context.py      # Schema description string for LLM prompt context
│   ├── task_bank.yaml         # 45 declarative eval tasks
│   ├── minimax_client.py      # LangChain MiniMaxChat wrapper (max_tokens=4096)
│   ├── minimax_judge.py       # Judge orchestration + JSON parsing
│   ├── judge_prompts.py       # 5-dimension evaluation prompts
│   ├── text2cypher.py         # Legacy direct text→Cypher module
│   ├── judge.py               # Legacy Ollama-based judge
│   └── results/               # JSON/JSONL output from eval runs
├── scripts/                   # Helper scripts
│   ├── fix_neo4j_data.py      # Data cleanup / repair utilities
│   └── restore_nist.py        # Reload NIST CSF 2.0 from JSON source
├── docker-compose.yml         # Langfuse v3 stack (Postgres, ClickHouse, Redis, MinIO, Langfuse)
├── requirements.txt           # Root deps (Flask, neo4j, PyYAML, requests, etc.)
├── .env.example               # Template for all env vars
├── MEMORY.md                  # Living error log + tested solutions
└── KG_MANIFEST.md             # KG registry and isolation rules
```

---

## 4. Module Divisions

### 4.1 `aegis_kg` — Knowledge Graph
- **Schema** (`schema/01_create_schema.cypher`) defines node labels, constraints, indexes.
- **ETL** scripts must be run in numerical order (see §5.1).
- **API** (`api/app.py`) provides Phase-1 endpoints; Phase-2/3 endpoints return empty arrays because Obligation/Goal/Rule nodes were never loaded. However, `StrategicTension` (4 nodes) and `ApplicabilityCondition` (12 nodes) DO exist in the graph.
- **Validation** (`validation/01_validate_phase1.py`) is a standalone script that batched-queries Neo4j and asserts counts, constraints, relationship integrity, and API health.

### 4.2 `aegis_agents` — LangGraph Agent
- **`agent.py`** — `AegisAgent` class. Builds a `StateGraph` with three nodes: `generate_and_execute`, `evaluate_and_decide`, `generate_answer`. Uses `langfuse.langchain.CallbackHandler` for parent trace when `use_tracing=True`.
- **`graph/nodes.py`** — Node implementations. Calls Ollama directly via `requests.post()` for Cypher generation and answer generation. Because these are raw HTTP calls (not LangChain LLM calls), manual `log_generation()` calls are injected here for Langfuse visibility.
- **`graph/router.py`** — `should_continue()` decides whether to retry (`generate_and_execute`) or produce final answer (`generate_answer`) based on error/row_count vs `max_attempts`.
- **`tools/`** — `neo4j_tool.py` (`exec_cypher`, `cypher_query` LangChain tool) and `schema_tool.py` (`schema_explorer` tool).
- **`feedback/refiners.py`** — `QueryRefiner` with `refine_on_error`, `refine_on_empty`, `refine_on_mismatch`, `suggest_alternatives`.

### 4.3 `aegis_eval` — Evaluation Pipeline
- **`run_eval.py`** — Main CLI entry point. Loads tasks from YAML, runs each through `AegisAgent`, then calls `minimax_judge.judge_agent_result()`, logs scores and a `judge_evaluation` span back to the agent's Langfuse trace.
- **`minimax_judge.py`** — Orchestrates the judge: builds prompt, calls `call_minimax()`, parses JSON, clamps scores 1–5, computes per-dimension averages.
- **`judge_prompts.py`** — `SYSTEM_JUDGE` rubric + `USER_EVALUATION_TEMPLATE`. Reads `answer` (not `llm_answer`) from `agent_result` and extracts DB results from the last successful step in `steps`.
- **`minimax_client.py`** — Thin wrapper around `langchain_community.chat_models.MiniMaxChat`. **Critical:** `max_tokens=4096` is hardcoded to prevent JSON truncation.

---

## 5. Build, Setup, and Test Commands

### 5.1 Environment Setup

All secrets are injected via environment variables (never hardcoded). Copy `.env.example` and fill in values:

```bash
# Langfuse (self-hosted)
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_BASE_URL=http://localhost:3000

# Minimax (judge)
export MINIMAX_API_KEY=sk-cp-...

# Neo4j (external container: d3fend-neo4j, password: d3fendtest)
export NEO4J_URI=http://localhost:7474
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=d3fendtest

# Ollama
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=ministral-3:latest
```

Python dependencies (use a virtual env, e.g. `/home/epmq/Desktop/Projects/shared-venv`):

```bash
source /home/epmq/Desktop/Projects/shared-venv/bin/activate
pip install -r requirements.txt
pip install -r aegis_agents/requirements.txt
pip install -r aegis_eval/requirements.txt
```

### 5.2 Infrastructure Startup

Neo4j runs in an **external container** (`d3fend-neo4j`), not in this repo's compose:

```bash
docker start d3fend-neo4j
```

Langfuse self-hosted stack (PostgreSQL, ClickHouse, Redis, MinIO, Langfuse web + worker):

```bash
cd /home/epmq/Desktop/Projects/aegis-kg-unified
docker compose up -d
```

Verify:

```bash
curl http://localhost:3000/api/health   # Langfuse
curl http://localhost:7474              # Neo4j
```

### 5.3 ETL (Load Data into Neo4j)

Run in strict numerical order. Schema must already be applied via Neo4j Browser (`schema/01_create_schema.cypher`).

```bash
cd aegis_kg/etl
python 06_load_all_regulations.py
python 08_load_clause_subdomain_mappings.py
python 09_load_regulatory_timelines.py
python 10_load_sole_authority.py
python 11_load_complementarity_analysis.py
```

NIST CSF 2.0 data is loaded separately:

```bash
python scripts/restore_nist.py
```

### 5.4 Validation

```bash
cd aegis_kg
python validation/01_validate_phase1.py
```

### 5.5 API

```bash
cd aegis_kg/api
python app.py        # Runs on http://localhost:5000
```

### 5.6 Evaluation

**Primary pipeline** (LangGraph agent + Minimax judge + Langfuse):

```bash
source /home/epmq/Desktop/Projects/shared-venv/bin/activate
cd /home/epmq/Desktop/Projects/aegis-kg-unified
python aegis_eval/run_eval.py \
  --tasks aegis_eval/task_bank.yaml \
  --task list_all_regulations \
  --trials 1 \
  --verbose
```

**Agent-only harness** (legacy / comparison):

```bash
PYTHONPATH=. python aegis_agents/run_agent_eval.py \
  --tasks aegis_eval/task_bank.yaml \
  --trials 1 \
  --verbose
```

---

## 6. Code Style Guidelines

- **Language:** All code comments, docstrings, and documentation in **English**.
- **Imports:** Standard library → third-party → local modules. Use absolute imports (`aegis_agents.config`, `aegis_eval.config`).
- **Typing:** Use `typing` annotations (`TypedDict`, `Optional`, `dict`, `list`) where practical.
- **Docstrings:** Google-style or concise descriptive style. Every public function should have a docstring.
- **String formatting:** Prefer f-strings. Multi-line SQL/Cypher uses triple-quoted strings.
- **Error handling:** Return structured error dicts rather than raising exceptions across module boundaries, especially in tool and agent code.
- **No hardcoded secrets:** API keys, passwords, and credentials must always read from environment variables via `os.getenv()`.

---

## 7. Testing Strategy

- **Unit-level validation:** `aegis_kg/validation/01_validate_phase1.py` performs batched Neo4j queries and asserts node counts, relationship integrity, constraint uniqueness, data quality, query performance (<2s), and API health.
- **Eval-driven regression:** `aegis_eval/run_eval.py` runs the agent against a frozen task bank (`task_bank.yaml`) and scores output with a deterministic rubric. Results are persisted as timestamped JSON/JSONL in `aegis_eval/results/` and `aegis_agents/results/`.
- **No formal unit-test framework** (pytest/unittest) is currently in use. Validation and eval scripts serve as the functional test suite.

---

## 8. Security Considerations

- **Neo4j password** (`YOUR_NEO4J_PASSWORD`) is a shared dev credential; do not expose externally.
- **Langfuse keys** in `docker-compose.yml` are for local self-hosted instances only. Rotate if the instance is exposed.
- **Minimax API key** (`MINIMAX_API_KEY`) is a billed external service. Never commit it.
- **No input sanitization layer** in the Flask API beyond parameterized Cypher. The API is read-only by design, but agent-generated Cypher is executed with the same privileges as the API.
- **Docker volumes** for Langfuse contain persistent telemetry; treat them as sensitive.

---

## 9. Langfuse Tracing — Mandatory Pattern

**Never change the tracing structure without confirming with the project owner.**

### Architecture

1. **Agent (`aegis_agents/agent.py`)** creates the parent trace via `langfuse.langchain.CallbackHandler` passed to LangGraph as `config["callbacks"] = [handler]`.
2. **Graph nodes (`aegis_agents/graph/nodes.py`)** add manual spans via `log_generation()` from `tracing.py` to capture Ollama LLM calls (raw HTTP, not LangChain).
3. **Eval runner (`aegis_eval/run_eval.py`)** does **NOT** create its own traces. It only adds scores and a `judge_evaluation` span to the **agent's existing trace** via `langfuse.create_score(trace_id=agent_trace_id)` and `langfuse.start_observation(...)`.

### Expected Trace Hierarchy

```
agent_eval_{task_id} (L0 — CallbackHandler)
  ├── cypher_generation (L1 — log_generation, model: ministral-3)
  ├── answer_generation (L1 — log_generation, model: ministral-3)
  └── judge_evaluation (L1 — start_observation, model: MiniMax-M2.7)
        └── output: {scores, full reasoning}
  └── Scores (via create_score with comment=reasoning[:500])
```

### Critical Rules

- `max_tokens=4096` in Minimax client — do not reduce; judge JSON needs space.
- Judge scores use `create_score(trace_id=agent_trace_id)` — never create a separate trace.
- `use_tracing=True` in `AegisAgent` when called by eval.
- Never use `start_as_current_observation()` in `run_eval.py` to avoid duplicate traces.

---

## 10. Key Configuration Files

| File | Purpose |
|------|---------|
| `aegis_agents/config.py` | Agent-side Neo4j, Ollama, Langfuse, LangChain configs |
| `aegis_eval/config.py` | Eval-side Neo4j, Ollama, Langfuse, Minimax configs |
| `docker-compose.yml` | Langfuse v3 stack (Postgres 17, ClickHouse 23.8, Redis 7, MinIO, Langfuse web/worker) |
| `.env.example` | Template for all required environment variables |
| `requirements.txt` (root) | Flask, neo4j, PyYAML, requests, pandas, openpyxl, etc. |
| `aegis_agents/requirements.txt` | langchain, langchain-ollama, langfuse, PyYAML, requests, tabulate, click |
| `aegis_eval/requirements.txt` | langfuse, PyYAML, requests, tabulate, click |

---

## 11. Known Issues & Where to Log Them

If you encounter a new bug, misconfiguration, or infrastructure failure, **append it to `MEMORY.md`** with:

1. Symptom / error message  
2. Root cause  
3. Fix or workaround  
4. Date

The file already contains a living history of ClickHouse/ZooKeeper migration errors, Langfuse credential mismatches, Minimax JSON truncation, and tracing API pitfalls. Check it before spending time debugging.

---

## 12. Quick Reference

```bash
# Container status
docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep aegis

# Langfuse logs
docker logs aegis-kg-unified-langfuse-1 --tail 20

# Restart Langfuse stack
docker compose down && docker compose up -d

# Eval single task
python aegis_eval/run_eval.py --tasks aegis_eval/task_bank.yaml --task list_all_regulations --trials 1 --verbose

# Validate KG data
cd aegis_kg && python validation/01_validate_phase1.py

# Start API
cd aegis_kg/api && python app.py
```

---

**End of AGENTS.md**
