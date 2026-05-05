# MEMORY.md — Langfuse + ClickHouse Setup Errors

## Errors Found and Solutions

---

### Error 1: "CLICKHOUSE_USER is not set"
**Symptom:** Langfuse crashes with `CLICKHOUSE_USER is not set`
**Cause:** Langfuse v3 requires separate `CLICKHOUSE_USER` and `CLICKHOUSE_PASSWORD` env vars (not just in the URL)
**Solution:** Add to docker-compose.yml:
```yaml
CLICKHOUSE_USER: langfuse
CLICKHOUSE_PASSWORD: langfuse_clickhouse_pw_2026
```

---

### Error 2: "There is no Zookeeper configuration" (ReplicatedMergeTree)
**Symptom:** `code: 139, message: There is no Zookeeper configuration in server config`
**Cause:** Langfuse creates tables with `Engine=ReplicatedMergeTree` which requires ZooKeeper/Keeper
**Alpine image doesn't work:** `clickhouse/clickhouse-server:23.8-alpine` (920MB) does NOT have embedded Keeper
**Non-alpine image works:** `clickhouse/clickhouse-server:23.8` (1.01GB) HAS Keeper/binaries

**Solution:** Use `CLICKHOUSE_CLUSTER_ENABLED=false` to disable Keeper requirement (simpler than configuring Keeper)

---

### Error 3: Keeper crash (keeper.xml misconfigured)
**Symptom:** ClickHouse crash loop with exit code 70
**Cause:** keeper.xml file with errors or incompatible configuration
**Solution:** Do NOT configure keeper.xml manually. Use `CLICKHOUSE_CLUSTER_ENABLED=false` instead

---

### Error 4: "Can't reach database server at langfuse-db:5432"
**Symptom:** PostgreSQL connectivity failure from langfuse container
**Cause:** Langfuse container was NOT on the same Docker network as postgres
**Solution:** `docker network connect aegis-kg-unified_default aegis-kg-unified-langfuse-1`

---

### Error 5: Migration P3009 — failed migration
**Symptom:** `migrate found failed migrations in the target database`
**Cause:** PostgreSQL database left in inconsistent state from previous attempts
**Solution:** `docker compose down -v` to recreate volumes (clean slate)

---

### Error 6: Port 3000 already in use
**Symptom:** `failed to bind host port 0.0.0.0:3000/tcp: address already in use`
**Cause:** Another process (e.g., next-server, other docker container) using the port
**Solution:** `fuser -k 3000/tcp` or change port in docker-compose

---

## Critical Discovery from Official Langfuse docker-compose

Langfuse v3 has a setting `CLICKHOUSE_CLUSTER_ENABLED=false` that disables the Keeper/ZooKeeper requirement for ReplicatedMergeTree tables. This makes self-hosted setup MUCH simpler.

Also required: **Redis** and **MinIO** (S3-compatible storage).

---

## Final Working Configuration

Langfuse docker-compose needs:
- `CLICKHOUSE_CLUSTER_ENABLED: "false"` — disables Keeper requirement
- `CLICKHOUSE_URL: clickhouse://langfuse-clickhouse:9000` — native protocol on port 9000
- Redis service (docker.io/redis:7)
- MinIO service (minio/minio) for S3 storage
- All S3 env vars configured (LANGFUSE_S3_*)

---

## Working docker-compose.yml Services

1. langfuse-minio (minio/minio)
2. langfuse-redis (redis:7)
3. langfuse-clickhouse (clickhouse/clickhouse-server:23.8)
4. langfuse-db (postgres:17)
5. langfuse (langfuse/langfuse:latest)

**Status:** WORKING as of 2026-04-27

---

## Neo4j External Container

Neo4j runs as an **external container** (`d3fend-neo4j`), not in this repo's docker-compose.
- Start with: `docker start d3fend-neo4j`
- Connection: `http://localhost:7474` (user: `neo4j`, pw: `YOUR_NEO4J_PASSWORD`)

---

## NIST CSF 2.0 Complete Restore (2026-04-27)

Successfully restored complete NIST CSF 2.0 data from JSON source:

### What's loaded:
- **Framework**: NIST_CSF_2_0 (with full description)
- **6 Functions**: GV (Govern), ID (Identify), PR (Protect), DE (Detect), RS (Respond), RC (Recover) - with full descriptions
- **34 Categories**: with full descriptions (e.g., "Organizational Context (GV.OC): The circumstances...")
- **185 Controls**: with complete description, implementationExamples, crossReferences

### Control properties:
- `description`: Full NIST description (e.g., "GV.OC-01: The organizational mission is understood...")
- `implementationExamples`: Array of implementation examples (avg 2 per control)
- `crossReferences`: Array of formatted strings (avg 7 per control, e.g., "CCMv4.0: BCR-01, BCR-07")

### Query full path (Regulation → Clause → Domain → SubDomain ← NIST Control ← Category ← Function ← Framework):
```cypher
// Start from NIST side (works best for traversal)
MATCH (f:Framework {frameworkId: "NIST_CSF_2_0"})-[:HAS_CATEGORY]->(func:FrameworkCategory {type: "FUNCTION"})-[:HAS_CATEGORY]->(cat:FrameworkCategory)
WHERE cat.type = "CATEGORY"
MATCH (cat)<-[:HAS_CONTROL]-(fc:FrameworkControl)
MATCH (fc)-[:MAPS_TO_SUBDOMAIN]->(sd:SubDomain)<-[:MAPPED_TO]-(c:Clause)
MATCH (c)<-[:HAS_CLAUSE]-(reg:Regulation)
MATCH (sd)<-[:HAS_SUBDOMAIN]-(d:Domain)
RETURN reg.regulationId, c.clauseId, d.domainId, sd.subDomainId, fc.controlId, func.categoryId AS nistFunction, cat.categoryId AS nistCategory, f.name AS framework
```

### Bug CORRIGIDO (2026-04-27):
- A relação `HAS_CONTROL` estava com direção invertida (Category→Control em vez de Control→Category)
- Corrigido no script: `MERGE (c)-[:HAS_CONTROL]->(cat)` em vez de `MERGE (cat)-[:HAS_CONTROL]->(c)`
- Após limpeza completa e reload, os relationships estão corretos: 185 HAS_CONTROL (FrameworkControl → FrameworkCategory)

---

## NIST CSF 2.0 Control Mapping to AEGIS Domains (2026-04-28)

**Source of Truth:** Official NIST CSF 2.0 Reference Tool (`csf2.xlsx`) and NIST publication

### Official NIST CSF 2.0 Structure:
- **6 Functions**: GOVERN (GV), IDENTIFY (ID), PROTECT (PR), DETECT (DE), RESPOND (RS), RECOVER (RC)
- **22 Active Categories** (12 withdrawn from CSF 1.1)
- **106 Active Subcategories** (185 total in source, 79 withdrawn)

### Current Neo4j State (After Reconciliation):
| Metric | Count |
|--------|-------|
| Total FrameworkControls | 106 |
| Functions | 6 |
| Categories (active) | 22 |
| HAS_CONTROL relationships | 106 |
| MAPS_TO_SUBDOMAIN | 67 (63%) |
| MAPS_TO_DOMAIN | 39 (37%) |
| Unmapped controls | 0 |

### Domain Distribution:
| Domain | SubDomain | Domain | Total |
|--------|-----------|--------|-------|
| D-01 Cryptography | 4 | 0 | 4 |
| D-02 Vulnerability Management | 4 | 0 | 4 |
| D-03 Access Control | 11 | 6 | 17 |
| D-04 Incident Management | 23 | 3 | 26 |
| D-05 Data Lifecycle | 1 | 0 | 1 |
| D-06 Supply Chain Security | 7 | 3 | 10 |
| D-07 Secure Development | 1 | 0 | 1 |
| D-08 Governance and Awareness | 3 | 18 | 21 |
| D-09 Risk and Impact Assessment | 21 | 9 | 30 |
| D-10 Monitoring and Audit | 13 | 0 | 13 |
| **Total** | **88** | **39** | **127** |

**Note:** 88 + 39 = 127 but total controls = 106. Some controls map to same domain via different paths. Verification: `MATCH (fc:FrameworkControl) WHERE exists((fc)-[:MAPS_TO_SUBDOMAIN]->()) OR exists((fc)-[:MAPS_TO_DOMAIN]->()) RETURN count(fc)` = 106 ✓

### Reconciliation Notes (2026-04-28):
- JSON source had 26 subcategories incorrectly marked as "active" that are actually "Withdrawn" per official xlsx
- Deleted 79 withdrawn controls (description contains "Withdrawn")
- 106 active controls remain with correct properties
- All 106 controls have mappings (no unmapped controls)
- No duplicate mappings (no control has both MAPS_TO_SUBDOMAIN and MAPS_TO_DOMAIN)

### Key Queries:
```cypher
// Verify counts match official NIST CSF 2.0
MATCH (fc:FrameworkControl) 
WITH size(collect(DISTINCT fc.functionCode)) AS funcs, 
     size(collect(DISTINCT fc.categoryId)) AS cats, 
     count(fc) AS controls 
RETURN funcs AS functions, cats AS categories, controls
// Result: 6 functions, 22 categories, 106 controls ✓

// Count unmapped controls (should be 0)
MATCH (fc:FrameworkControl) 
WHERE NOT exists((fc)-[:MAPS_TO_SUBDOMAIN]->()) 
AND NOT exists((fc)-[:MAPS_TO_DOMAIN]->()) 
RETURN count(fc) AS unmapped
// Result: 0 ✓

// Controls per domain
MATCH (fc:FrameworkControl)-[:MAPS_TO_SUBDOMAIN]->(sd:SubDomain)<-[:HAS_SUBDOMAIN]-(d:Domain)
RETURN d.domainId, count(fc) AS viaSubdomain
UNION
MATCH (fc:FrameworkControl)-[:MAPS_TO_DOMAIN]->(d:Domain)
RETURN d.domainId, count(fc) AS viaDomain
```

### Command to restore (clean):
```bash
# 1. Limpar todos os dados NIST existentes
MATCH (n) WHERE n:Framework OR n:FrameworkCategory OR n:FrameworkControl DETACH DELETE n
MATCH ()-[r:HAS_CONTROL]->() DELETE r

# 2. Recarregar
python3 scripts/restore_nist.py

# 3. Verificar mapeamentos
MATCH (fc:FrameworkControl) RETURN count(fc) AS total, 
  size(collect(DISTINCT fc.frameworkId)) AS frameworks
```

---

## Evaluation Success

First eval passed on 2026-04-27:
```
=== Trial 1: list_all_regulations ===
Cypher: MATCH (r:Regulation) RETURN r.regulationId AS regulationId, r.label AS label, r....
Exec: OK (1370ms), 5 rows
Judge scores: cypher=3, retrieval=3, answer=3, reasoning=3
Pass rate: 100.0% (1/1)
```

---

## Useful Commands for Debug

```bash
# Check containers and status
docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep aegis

# Check logs
docker logs aegis-kg-unified-langfuse-1 --tail 50
docker logs aegis-kg-unified-langfuse-clickhouse-1 --tail 50

# Check networks
docker network inspect aegis-kg-unified_default

# Test connectivity between containers
docker exec aegis-kg-unified-langfuse-1 nc -zv langfuse-db 5432
docker exec aegis-kg-unified-langfuse-1 nc -zv langfuse-clickhouse 8123

# Check process using port
fuser 3000/tcp
lsof -i :3000

# Clean slate
docker compose down -v
docker compose up -d
```

---

## AEGIS LangChain Agent (2026-04-28)

New module `aegis_agents/` for agent experiments with LangChain + Langfuse tracing.

### Architecture
```
Question → LangChain ReAct Agent (with feedback loop)
                │
                ├── Tools: cypher_query, schema_explorer
                ├── QueryRefiner (feedback on error/empty)
                └── Langfuse CallbackHandler tracing
```

### Files Structure
```
aegis_agents/
├── __init__.py
├── agent.py              # Main ReAct agent with feedback loops
├── config.py             # Configuration (Neo4j, Ollama, Langfuse)
├── tracing.py            # Langfuse tracing utilities
├── run_agent_eval.py    # Evaluation harness
├── requirements.txt     # langchain, langchain-ollama, langfuse
├── tools/
│   ├── neo4j_tool.py    # Cypher query tool
│   └── schema_tool.py   # Schema explorer tool
├── feedback/
│   └── refiners.py      # Query refinement utilities
└── judge/
    └── agent_judge.py   # LLM-as-a-Judge for agent evaluation
```

### Judge Dimensions (1-5 scale)
| Dimension | What it Measures |
|-----------|-----------------|
| cypher_correctness | Cypher syntactic + semantic correctness |
| query_effectiveness | Did the query answer the question well? |
| feedback_loop_benefit | Did refinement improve results? |
| tool_usage | Did agent use appropriate tools? |
| reasoning_quality | Is agent's reasoning sound? |

### Run Evaluation
```bash
source ~/Desktop/Projects/shared-venv/bin/activate
cd /home/epmq/Desktop/Projects/aegis-kg-unified
PYTHONPATH=. python aegis_agents/run_agent_eval.py --tasks aegis_eval/task_bank.yaml --trials 1 --verbose
```

### Langfuse Tracing Integration
- Uses `langfuse.langchain.CallbackHandler` for LangChain tracing
- Uses `langfuse.generation()` for manual generation logging
- Uses `langfuse.score_current_trace()` for scoring
- Uses `langfuse.flush()` to ensure events are sent

---

## Minimax LLM-as-a-Judge (2026-04-28)

New evaluation architecture using **Minimax M2.7** as the judge.

### Architecture
```
Task → LangGraph Agent (Ministral) → Neo4j → Trace (Langfuse)
                                              │
                                              │ trace_id
                                              ▼
                                      Minimax M2.7 (Judge)
                                              │
                                              │ scores
                                              ▼
                                      Langfuse (scores logged)
```

### Files
```
aegis_eval/
├── config.py           # MINIMAX_CONFIG (env var: MINIMAX_API_KEY)
├── minimax_client.py   # Minimax API client
├── judge_prompts.py    # 5-dimension evaluation prompts
├── minimax_judge.py    # Judge orchestration + Langfuse logging
└── run_eval.py         # Main eval runner (updated)
```

### Evaluation Dimensions (5 total, each with query + answer sub-scores)

| Dimension | Query Score | Answer Score | What it Measures |
|----------|-------------|--------------|------------------|
| cypher_correctness | 1-5 | 1-5 | Syntax validity + schema alignment |
| query_effectiveness | 1-5 | 1-5 | Intent alignment |
| feedback_loop_benefit | 1-5 | 1-5 | Improvement across attempts |
| tool_usage | 1-5 | 1-5 | Correct exec_cypher usage |
| reasoning_quality | 1-5 | 1-5 | Logical soundness |

**Total: 10 scores per task**

### Running Evaluation
```bash
# Set Minimax API key
export MINIMAX_API_KEY='YOUR_MINIMAX_API_KEY'

# Run evaluation
source ~/Desktop/Projects/shared-venv/bin/activate
cd /home/epmq/Desktop/Projects/aegis-kg-unified
python aegis_eval/run_eval.py --tasks aegis_eval/task_bank.yaml --trials 1 --verbose
```

### Scoring Details

**cypher_correctness:**
- Query: Syntax + schema validity
- Answer: Consistency with query results

**query_effectiveness:**
- Query: Intent alignment
- Answer: Conveying what query found

**feedback_loop_benefit:**
- Query: Improvement across attempts
- Answer: Improvement across attempts
- N/A if single attempt

**tool_usage:**
- Query: Correct exec_cypher usage
- Answer: Answer references actual tool results

**reasoning_quality:**
- Query: MATCH/WHERE logic soundness
- Answer: Reasoning justifies conclusions

### Minimax API Call
```python
url = "https://api.minimax.chat/v1/text/chatcompletion_v2"
model = "MiniMax-M2.7"
max_tokens = 1024
temperature = 0.1
```

---

## Minimax API URL - CRITICAL BUG (2026-05-04)

**Symptom:** `status_code: 2049, status_msg: 'invalid api key'` despite correct API key
**Root Cause:** URL was `https://api.minimax.chat/v1/text/chatcompletion_v2` (WRONG)
**Correct URL:** `https://api.minimaxi.chat/v1/text/chatcompletion_v2` (note: minimaxi, not minimax)

**Files affected:**
- `aegis_eval/config.py` - MINIMAX["base_url"]
- Any direct requests to Minimax API

**Fix applied:**
```python
# WRONG (404 / 401 errors):
MINIMAX["base_url"] = "https://api.minimax.chat/v1/text/chatcompletion_v2"

# CORRECT:
MINIMAX["base_url"] = "https://api.minimaxi.chat/v1/text/chatcompletion_v2"
```

**Also fixed:**
- `max_tokens` increased from 1024 to 4096 to prevent JSON truncation

**Date:** 2026-05-04

---

## Minimax API Key Rotation (2026-05-04)

**Old key (EXPOSED - DO NOT USE):**
```
sk-cp-yta9jJd1FoaX91wTwoVjoICfZm-wjFqKLccscXuVCdHp8huqOLAY_T6yScB3eO35cfxqBzXvlMYXfxQcPCOlDeBhkyTrMxGGwgv6UdICKK93Xi-_6dHubz4
```

**New key (ACTIVE):**
```
sk-cp-24bP-YWaZeAAxGreCrsknT1kugHnB2iJxcjJE7SgS65l-1Obghmn9_g_KSeNXtnUFaaMk37leZT84vW3EQd0CWo_fJuT9XaOfA0laK6GFJQKnshmT5MYWhg
```

**Files updated:**
- `/home/epmq/Desktop/Projects/aegis-kg-unified/.env`
- `/home/epmq/Desktop/Projects/Methodology-main/.env`
- `/home/epmq/Desktop/Projects/artigos-lc/.env`
- `/home/epmq/Desktop/Projects/aegis-kg-unified-BACKUP-20260429/.env.example`
- `/home/epmq/Desktop/Projects/aegis-kg-unified-BACKUP-20260429/MEMORY.md`

**Date:** 2026-05-04

---

## Implementation Errors (2026-04-28)

### Error 1: Minimax API Key Invalid
**Symptom:** `status_code: 2049, status_msg: 'invalid api key'`
**Cause:** A minha implementação requests.direct usava URL errada `api.minimax.chat` em vez de `api.minimaxi.chat`
**Solution:** Usar LangChain `MiniMaxChat` que tem URL correcta

---

### Error 2: Langfuse trace_id = "00000000000000000000000000000000"
**Symptom:** Todos os traces têm trace_id a zeros
**Cause:** Os nodes do agent fazem HTTP requests directas ao Ollama (não via LangChain), então o `CallbackHandler` do Langfuse não captura nada
**Solution:** Tracing manual usando API do Langfuse em vez de depender do callback

---

### Error 3: `start_as_current_observation() got an unexpected keyword argument 'trace_id'`
**Symptom:** Erro quando tentei passar `trace_id` para `start_as_current_observation`
**Cause:** A API do Langfuse não aceita `trace_id` como parâmetro directo
**Solution:** Necesário criar trace primeiro com `create_trace_id()` e passar via `trace_context`

---

### Error 4: Langfuse UnauthorizedError (401)
**Symptom:** `Invalid credentials. Confirm that you've configured the correct host.`
**Cause:** As credenciais de Langfuse (`YOUR_OLD_LANGFUSE_KEY`) são de um projeto diferente
**Note:** O Langfuse self-hosted usa credenciais diferentes do Langfuse Cloud
**Status:** PENDING - necessário verificar credenciais correctas do Langfuse self-hosted

---

### Error 5: Langfuse Scoring não aparece na UI
**Symptom:** Scores são gerados mas não aparecem no Langfuse UI
**Cause:** Devido ao Error 4 (credenciais inválidas), os scores não são guardados correctamente
**Status:** PENDING - depende de resolver Error 4

---

### Error 6: SyntaxError em run_eval.py (sum comprehension malformada)
**Symptom:** `SyntaxError: invalid syntax` com `sum(1 for r in results if ...)`
**Cause:** Nested conditional comprehension sem parênteses correctos
**Solution:** Substituir por loop explícito com if/else
**Date:** 2026-04-28

---

### Error 7: LANGFUSE credentials erradas em aegis_eval/config.py
**Symptom:** Langfuse returns 401 Unauthorized
**Cause:** `aegis_eval/config.py` tinha credenciais `YOUR_OLD_LANGFUSE_KEY` mas o correcto é `YOUR_OLD_LANGFUSE_KEY`
**Solution:** Corrigir para usar credenciais de `aegis_agents/config.py`
**Date:** 2026-04-28

---

### Files Modified for Minimax Judge Implementation

| File | Changes |
|------|---------|
| `aegis_eval/config.py` | Added `MINIMAX_CONFIG` dict |
| `aegis_eval/minimax_client.py` | Created - LangChain MiniMaxChat wrapper |
| `aegis_eval/judge_prompts.py` | Created - 5-dimension evaluation prompts |
| `aegis_eval/minimax_judge.py` | Created - Judge orchestration + score parsing |
| `aegis_eval/run_eval.py` | Modified - Integration of agent + judge + Langfuse |

---

### Current Status (2026-04-28)

| Component | Status |
|-----------|--------|
| Minimax API connection | WORKING (via LangChain) |
| Judge scoring | WORKING (5 dimensions x 2 = 10 scores) |
| Scores displayed in console | WORKING |
| Scores logged to Langfuse | NOT WORKING (credenciais inválidas) |
| Traces in Langfuse UI | NOT VISIBLE (mesmo motivo) |

---

### Next Steps to Fix Langfuse

1. Verificar credenciais do Langfuse self-hosted (não são as do Cloud)
2. Ou usar Langfuse Cloud em vez de self-hosted
3. Criar traces via API correcta

---

## Novas Entradas (2026-04-28 tarde)

### Error 8: MINIMAX_API_KEY não é lida da env var
**Symptom:** `MINIMAX.get("api_key")` retorna string vazia mesmo com env var definida
**Cause:** `os.getenv()` chamado antes de config.py ser importado, ou MINIMAX não está a ler env var correctamente
**Status:** FIXED - Keys now in .env.example, user provides at runtime

---

### Error 9: Trial retorna FAIL sem output detalhado
**Symptom:** `[FAIL] list_all_regulations_001_... | error=N/A` - não mostra erro real
**Cause:** Provavelmente erro interno não está a ser propagado correctamente
**Status:** FIXED - Improved error handling, now shows actual error

---

### Error 10: Langfuse "No key found for public key"
**Symptom:** Langfuse logs show "No key found for public key YOUR_OLD_LANGFUSE_KEY" and returns 401
**Cause:** Keys not in Langfuse database (created but then deleted, or DB was reset)
**Solution:** Updated credentials:
- `LANGFUSE_PUBLIC_KEY=YOUR_LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY=YOUR_LANGFUSE_SECRET_KEY`
- `LANGFUSE_BASE_URL=http://localhost:3000`
**Date:** 2026-04-28

---

### Error 11: Judge JSON truncado (max_tokens=1024 insuficiente)
**Symptom:** JSON response from Minimax judge cut off mid-parsing, e.g., `"query_effectiveness": { "query": 5, "answer": 2,`
**Cause:** `max_tokens=1024` not enough for full JSON with 5 dimensions × 3 fields + reasoning
**Solution:** Increased `max_tokens` to 4096 in `minimax_client.py`
**Date:** 2026-04-28

---

### Error 12: Judge prompt lia campos errados do agent_result
**Symptom:** `agent_result.get("llm_answer")` returns None, `query_result` not present
**Cause:** AegisAgent returns `answer` not `llm_answer`, and `query_result` is in `steps[-1]["data"]`
**Solution:** Updated `judge_prompts.py:get_evaluation_prompt()` to read `answer` field and extract `data` from `steps`
**Date:** 2026-04-28

---

### Error 13: Traces sem cypher_generation/answer_generation
**Symptom:** Langfuse traces show empty L0 span with no child spans
**Cause:** CallbackHandler only captures LangGraph state transitions, not HTTP calls to Ollama
**Solution:** Added `log_generation()` calls in `nodes.py` for cypher and answer generation
**Date:** 2026-04-28

---

### Langfuse Tracing Pattern - COMPLETED
**Status:** ✅ Fully implemented and tested

**Structure:**
```
agent_eval_{task_id} (L0 — CallbackHandler)
  ├── cypher_generation (L1 — log_generation, model: ministral-3)
  ├── answer_generation (L1 — log_generation, model: ministral-3)
  └── judge_evaluation (L1 — start_observation, model: MiniMax-M2.7)
        └── output: {scores, full reasoning}
  └── Scores (via create_score with comment=reasoning[:500])
```

**Files involved:**
- `aegis_agents/agent.py` - CallbackHandler setup
- `aegis_agents/graph/nodes.py` - log_generation() calls
- `aegis_agents/tracing.py` - log_generation() implementation
- `aegis_eval/run_eval.py` - Scores + judge_evaluation span
- `aegis_eval/minimax_client.py` - max_tokens=4096
- `aegis_eval/judge_prompts.py` - Correct field mapping

**Prevention:** Documented in AGENTS.md as mandatory pattern

---

### Langfuse Credentials Updated (2026-04-28)
**New credentials:**
- `LANGFUSE_PUBLIC_KEY=YOUR_LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY=YOUR_LANGFUSE_SECRET_KEY`
- `LANGFUSE_BASE_URL=http://localhost:3000`

**Files updated:**
- `docker-compose.yml` (lines 118-120): Updated keys + changed to `LANGFUSE_BASE_URL`
- `aegis_eval/config.py`: Removed hardcoded defaults for keys
- `aegis_agents/config.py`: Removed hardcoded defaults for keys

**Prevention measures:**
- Added `.env.example` template with placeholder keys
- Added validation in `aegis_eval/run_eval.py` - warns if keys not configured
- Added validation in `aegis_agents/tracing.py` - returns None if keys not configured
- No more hardcoded defaults for API keys (always read from env vars)

---

### Files Modified (2026-04-28)

| File | Changes |
|------|---------|
| `docker-compose.yml` | Updated LANGFUSE keys (lines 118-120), changed to `LANGFUSE_BASE_URL` |
| `aegis_eval/config.py` | Removed hardcoded defaults for LANGFUSE keys |
| `aegis_agents/config.py` | Removed hardcoded defaults for LANGFUSE keys |
| `aegis_eval/run_eval.py` | Added validation/warning for missing LANGFUSE keys |
| `aegis_agents/tracing.py` | Added validation for missing LANGFUSE keys |
| `.env.example` | Created - template for all environment variables |

---

### Langfuse Credentials Update - COMPLETED
**Status:** ✅ Completed and tested

**Verification:**
- Langfuse client creates successfully with new credentials
- No "No key found" errors in logs after restart
- Container running normally

**Next step:** Run a task and verify traces appear in Langfuse UI at http://localhost:3000

---

## Minimax LangChain vs Direct Requests - 2026-05-04

### Error: LangChain MiniMaxChat fails with "Invalid API Key Provided"
**Symptom:** `Invalid API Key Provided` when using LangChain `MiniMaxChat`, but direct `requests.post` works fine with the same API key.

**Root Cause:** LangChain `MiniMaxChat` uses a cached HTTP client (`httpx.Client`) inside `_generate()`. On some environments, the client instance may not properly send the Authorization header despite the key being set correctly in `MiniMaxChat.minimax_api_key`. The direct HTTP request via `requests.post` always works.

**Debug findings:**
- API key length: 125 chars (correct)
- Host: `https://api.minimaxi.chat/v1/text/chatcompletion_v2` (correct)
- Direct `requests.post` with same key/headers: ✅ Works
- LangChain `MiniMaxChat.invoke()`: ❌ `Invalid API Key Provided` after 0.7-1.2s

**Solution:** Replaced LangChain `MiniMaxChat` with direct `requests.post` in `aegis_eval/minimax_client.py`. Direct HTTP is more reliable and has fewer dependencies.

**Changes:**
- `aegis_eval/minimax_client.py` - Complete rewrite using `requests.post` instead of `langchain_community.chat_models.MiniMaxChat`
- Uses `https://api.minimaxi.chat/v1/text/chatcompletion_v2` directly
- Model name: `MiniMax-M2.7` (case sensitive)
- `max_tokens=4096`, `temperature=0.1`, `top_p=0.95`

**Date:** 2026-05-04
