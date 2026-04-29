# LLM-as-a-Judge Eval Pipeline — aegis-kg-unified

**Versão:** 1.0
**Data:** 2026-04-27
**Modelo:** `ministral-3:latest` (Ollama)
**Infra:** Neo4j (existente) + Langfuse self-hosted (Docker) + Ollama (existente)

---

## VISÃO GERAL

Pipeline de avaliação que usa o Langfuse para observar e grader LLM-generated Cypher queries contra um knowledge graph regulatório (5 EU regulations → AEGIS 10×38 taxonomy).

```
Task (pergunta em linguagem natural)
  │
  ├─ Span 1: "cypher_generation"     →ministral-3 → Cypher query
  ├─ Span 2: "query_execution"      →Neo4j → resultados
  ├─ Span 3: "answer_generation"    →ministral-3 → resposta em texto
  └─ Span 4: "eval_judge"           →ministral-3 → scores (1-5)

Todos os prompts/outputs/logs guardado no Langfuse.
```

---

## FASES DE EXECUÇÃO

### FASE 0 — Verificação e Correção dos Dados Neo4j

**Problema diagnosticado:**

| Label | Count | Status |
|-------|-------|--------|
| Regulation | 5 | OK |
| Clause | 150 | OK |
| SubDomain | 38 | PARCIAL (props `soleAuthority` null) |
| Domain | 10 | OK |
| Article | **0** | FALTA — CSV tem 47, graph tem 0 |
| NIST*/Framework* | ~250 | **LIXO** — dados de outro KG |
| Unlabeled | 2 | **LIXO** — nós órfãos vazios |

**Relacionamentos:**

| Type | Count | Status |
|------|-------|--------|
| HAS_CLAUSE | 150 | OK |
| MAPPED_TO | 150 | OK |
| HAS_SUBDOMAIN | 38 | OK |
| HAS_CONTROL | 1023 | **LIXO** |
| MAPS_TO_SUBDOMAIN | 239 | **LIXO** |

**Ações:**
1. Limpar nós/rels de outros KGs (NIST, Framework)
2. Limpar nós órfãos (unlabeled)
3. Recarregar 47 Article nodes de `03_articles.csv`
4. Recarregar props de SubDomain (`soleAuthority`, `gapRisk`) de `02_subdomains.csv`
5. Verificar totals finais

### FASE 1 — Infraestrutura Langfuse

**Docker Compose additions:**
- `langfuse-db` (PostgreSQL 15-alpine)
- `langfuse` (langfuse/langfuse:latest, port 3000)

**Verificação:**
```bash
docker-compose up -d
curl http://localhost:3000/api/health
# UI: http://localhost:3000
# Criar project "aegis-kg-eval" → gerar API keys
```

### FASE 2 — Task Bank e Configuração

**Ficheiros:**
- `eval/config.py` — Neo4j, Ollama, Langfuse configs
- `eval/schema_context.py` — Schema description para LLM
- `eval/task_bank.yaml` — 30 tasks declarativas
- `eval/requirements.txt` — `langfuse>=2.0, PyYAML, requests, tabulate, click`

**Categorias de tasks (30 total):**

| Categoria | # | Dificuldade |
|-----------|---|-------------|
| basic_retrieval | 5 | easy |
| clause_lookup | 5 | easy-medium |
| subdomain_mapping | 4 | medium |
| cross_regulation | 5 | medium-hard |
| normative_intensity | 3 | medium |
| gap_analysis | 3 | hard |
| complementarity | 3 | hard |
| complex_reasoning | 2 | hard |

### FASE 3 — Pipeline de Avaliação

**Ficheiros:**
- `eval/text2cypher.py` — Question → Cypher via Ollama
- `eval/judge.py` — LLM-as-a-Judge scoring (4 dimensões)
- `eval/run_eval.py` — Runner principal com Langfuse tracing
- `eval/run_retrieval.py` — Retrieval verification (Fase 0 helper)

**4 Dimensões de Scoring:**

| Dimensão | Método | Escala |
|----------|--------|--------|
| cypher_quality | sintaxe + semântica | 1-5 |
| retrieval_accuracy | comparação com expected | 1-5 |
| answer_quality | LLM judge | 1-5 |
| regulatory_reasoning | LLM judge | 1-5 |

### FASE 4 — Execução e Análise

**Targets:**

| Métrica | Target | Aceitável |
|---------|--------|-----------|
| Cypher Correctness | >80% | >60% |
| Retrieval Accuracy | >70% | >50% |
| Answer Quality | >3.5/5 | >3.0/5 |
| Avg Latency (total) | <15s | <30s |

---

## ESTRUTURA FINAL DO PROJETO

```
aegis-kg-unified/
├── docker-compose.yml              # Neo4j + Langfuse + PostgreSQL
├── requirements.txt
├── README.md
├── KG_MANIFEST.md
├── aegis_rca_ontology.ttl
├── aegis_kg/                       # KG regulatório (já existente)
│   ├── schema/
│   ├── data/
│   ├── etl/
│   ├── api/
│   ├── validation/
│   └── queries/
├── eval/                           # NOVO — pipeline de avaliação
│   ├── config.py
│   ├── schema_context.py
│   ├── task_bank.yaml
│   ├── text2cypher.py
│   ├── judge.py
│   ├── run_eval.py
│   ├── run_retrieval.py
│   └── requirements.txt
└── scripts/                         # NOVO — helpers
    └── fix_neo4j_data.py           # Fase 0: limpeza + recarga
```

---

## COMANDOS DE EXECUÇÃO

```bash
# Verificar dados (Fase 0)
python eval/run_retrieval.py --verify

# Correr eval completo
python eval/run_eval.py --tasks eval/task_bank.yaml --trials 3

# Correr task específica
python eval/run_eval.py --tasks eval/task_bank.yaml --task list_regulations --trials 1 --verbose

# Ver Langfuse
open http://localhost:3000
```

---

## SCHEMA CONTEXT (para LLM)

```cypher
-- Nodes:
Regulation(regulationId, label, description, euReference, clauseCount)
Article(articleId, number, title, chapter, summary)
Clause(clauseId, description, normativeIntensity, regulationId, obligationType, obligatedParty, articleReference)
Domain(domainId, name)
SubDomain(subDomainId, name, description, soleAuthority, gapRisk)
ComplementarityAnalysis(analysisId, regulation1Id, regulation2Id, overlapType, jaccardIndex)

-- Relationships:
(Regulation)-[:HAS_ARTICLE]->(Article)
(Regulation)-[:HAS_CLAUSE]->(Clause)
(Article)-[:DEFINES]->(Clause)
(Domain)-[:HAS_SUBDOMAIN]->(SubDomain)
(Clause)-[:MAPPED_TO]->(SubDomain)

-- Convenções:
subDomainId: "D-01-1" (formato D-XX-Y)
clauseId: "GDPR-C01", "CRA-C01", "NIS2-C01", "DORA-C01", "AIA-C01"
regulationId: "GDPR", "CRA", "NIS2", "DORA", "AIAct"
normativeIntensity: 1 (MAY), 2 (SHOULD), 3 (SHALL)
```

---

**Versão:** 1.0
**Última actualização:** 2026-04-27