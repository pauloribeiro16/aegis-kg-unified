# KG_MANIFEST.md — AEGIS-KG-Unified Registry

**Version:** 2.0
**Created:** 2026-04-27
**Updated:** 2026-04-29
**Purpose:** Canonical registry of the AEGIS-KG-Unified Neo4j knowledge graph.

---

## 1. KG SCOPE

This project contains **one Neo4j knowledge graph** combining:

- **AEGIS Regulatory** — 5 EU regulations mapped to a 10×38 security taxonomy.
- **NIST CSF 2.0** — 106 controls mapped to the same taxonomy for cross-framework gap analysis.

---

## 2. ISOLATION RULES

### Rule 1 — Single KG, Single Database
All nodes live in the same Neo4j instance (`neo4j` database, external container `d3fend-neo4j`).

### Rule 2 — ETL Is the Only Write Path
All data loading must go through ETL scripts in `aegis_kg/etl/`. The Flask API (`aegis_kg/api/app.py`) is read-only.

### Rule 3 — Neo4j Connection
- **Host:** `http://localhost:7474`
- **Auth:** `neo4j / d3fendtest`
- **Database:** `neo4j`
- **Env var:** `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`

---

## 3. NODE LABEL REFERENCE (Verified via Neo4j)

### Phase 1 — Regulatory Core

| Label | Count | Key Properties | Notes |
|-------|-------|----------------|-------|
| `Regulation` | 5 | `regulationId`, `label`, `description`, `euReference`, `clauseCount` | GDPR, CRA, NIS2, DORA, AIAct |
| `Article` | 47 | `articleId`, `number`, `title` | `regulationId` is NULL on all articles |
| `Clause` | 150 | `clauseId`, `regulationId`, `normativeIntensity`, `obligationType`, `obligatedParty` | `applicable` is NULL on all clauses |
| `Domain` | 10 | `domainId`, `name` | D-01 through D-10 |
| `SubDomain` | 38 | `subDomainId`, `name`, `soleAuthority`, `gapRisk` | Format: `D-XX.Y` (dot separator, e.g., `D-01.1`) |
| `CompanyContext` | 1 | All properties populated | TinyTask Lda., Portugal, MICRO |
| `ComplementarityAnalysis` | 6 | `regulation1Id`, `regulation2Id`, `jaccardIndex`, `conflictClassification` | Jaccard: NIS2-DORA=0.857, CRA-DORA=0.562 |

### Phase 1+ — Enrichment Nodes

| Label | Count | Key Properties | Notes |
|-------|-------|----------------|-------|
| `StrategicTension` | 4 | `tensionId`, `description`, `severity` | Real conflict data between regulations |
| `ApplicabilityCondition` | 12 | `conditionId`, `description` | Per-regulation applicability rules; `conditionType` is NULL |

### NIST CSF 2.0 Side

| Label | Count | Key Properties | Notes |
|-------|-------|----------------|-------|
| `Framework` | 1 | `frameworkId`, `name` | NIST_CSF_2_0 |
| `FrameworkCategory` | 40 | `categoryId`, `name`, `type`, `functionCode` | 6 Functions + 34 Categories |
| `FrameworkControl` | 106 | `controlId`, `title`, `categoryId`, `functionCode` | Mapped to SubDomains |

### Phantom Nodes (Defined in Schema, Properties NULL)

| Label | Count | Issue |
|-------|-------|-------|
| `SubDomainMetrics` | 14 | All metric properties (`metricId`, `coverageScore`, `complianceGap`, `riskScore`) are NULL |

### Phase 2/3 — Not Loaded

These node labels are defined in the schema but **no nodes exist** in Neo4j:
- `Obligation`, `Goal`, `Rule`, `ConflictResolution` (Phase 2)
- `UseCase`, `FunctionalNode`, `Vulnerability`, `ComplianceGate`, `NFR`, `FR`, `Threat`, `Risk`, `Mitigation` (Phase 3)

---

## 4. RELATIONSHIP TYPES (Verified via Neo4j)

| Relationship | Count | From → To | Properties |
|--------------|-------|-----------|------------|
| `HAS_ARTICLE` | 47 | Regulation → Article | — |
| `HAS_CLAUSE` | 150 | Regulation → Clause | — |
| `DEFINES` | ? | Article → Clause | — |
| `HAS_CATEGORY` | 74 | Framework → FrameworkCategory | — |
| `HAS_CONTROL` | 106 | FrameworkCategory → FrameworkControl | — |
| `HAS_SUBDOMAIN` | 38 | Domain → SubDomain | — |
| `MAPPED_TO` | 150 | Clause → SubDomain | — |
| `MAPS_TO_SUBDOMAIN` | 88 | FrameworkControl → SubDomain | — |
| `MAPS_TO_DOMAIN` | 39 | FrameworkControl → Domain | — |
| `OVERLAPS_WITH` | 22 | ComplementarityAnalysis → Regulation | — |
| `HAS_TENSION_WITH` | 26 | Regulation → Regulation | — |
| `AFFECTS_SUBDOMAIN` | 4 | StrategicTension → SubDomain | — |
| `INVOLVES_REGULATION` | 4 | StrategicTension → Regulation | — |
| `INVOLVES_CLAUSE` | 4 | StrategicTension → Clause | — |
| `HAS_APPLICABILITY` | 12 | Regulation → ApplicabilityCondition | — |
| `HAS_METRICS` | 14 | SubDomain → SubDomainMetrics | — |

---

## 5. PROPERTY POPULATION STATUS

### Fully Populated
- `Regulation`: `regulationId`, `label`, `description`, `clauseCount`, `euReference`
- `Clause`: `clauseId`, `regulationId`, `normativeIntensity`, `obligationType`, `obligatedParty`
- `SubDomain`: `subDomainId`, `name`, `soleAuthority`, `gapRisk`
- `CompanyContext`: all 12 properties populated
- `ComplementarityAnalysis`: `analysisId`, `regulation1Id`, `regulation2Id`, `jaccardIndex`, `conflictClassification`

### NULL / Empty Across All Nodes
- `Regulation`: `name`, `fullName`, `effectiveDate`, `lastAmended`, `notificationTimelines`
- `Article`: `regulationId`, `chapter`, `section`, `obligationType`
- `Clause`: `applicable`, `sourceReference`, `crossReferences`
- `SubDomain`: `keywords`, `examples`
- `ApplicabilityCondition`: `conditionType`
- `StrategicTension`: `name`, `category`
- `SubDomainMetrics`: all properties

### Partially Populated
- `Regulation.clauseCount`: accurate counts (GDPR=28, CRA=26, NIS2=29, DORA=38, AIAct=29)
- `Regulation.applicabilityConditionCount`: GDPR=3, CRA=2, NIS2=3, DORA=2, AIAct=2

---

## 6. IDENTITY CONVENTIONS (Actual — Verified)

| Entity | Format | Examples |
|--------|--------|----------|
| SubDomain ID | `D-XX.Y` (dot) | `D-01.1`, `D-02.3`, `D-10.2` |
| Clause ID | `REG-CXX` | `GDPR-C01`, `CRA-C07`, `NIS2-C16`, `DORA-C09`, `AIA-C01` |
| Regulation ID | Uppercase acronym | `GDPR`, `CRA`, `NIS2`, `DORA`, `AIAct` |
| Article ID | `REG-ArtN` | `GDPR-Art5`, `GDPR-Art32`, `CRA-Art13` |
| NIST Control ID | `XX.XX-NN` | `GV.OC-01`, `PR.DS-01`, `DE.CM-01` |
| NIST Function | 2-letter code | `GV`, `ID`, `PR`, `DE`, `RS`, `RC` |
| NIST Category | `XX.XX` prefix | `GV.OC`, `GV.RM`, `PR.DS`, `DE.CM` |
| Domain ID | `D-NN` | `D-01`, `D-02`, ..., `D-10` |

**WARNING:** The schema context file (`aegis_eval/schema_context.py`) incorrectly uses `D-01-1` (dash) instead of `D-01.1` (dot). Cypher queries using dash-format SubDomain IDs will fail.

---

## 7. RELATIONSHIP NAME CORRECTIONS

The actual relationship types in Neo4j differ from what `aegis_eval/schema_context.py` tells the LLM:

| What Schema Context Says | Actual Relationship |
|------------------------|---------------------|
| `(Clause)-[:MAPPED_TO]->(SubDomain)` | `(Clause)-[:COVERS_SUBDOMAIN]->(SubDomain)` or `[:MAPPED_TO]` |
| `(Domain)-[:HAS_SUBDOMAIN]->(SubDomain)` | `(Domain)-[:CONTAINS]->(SubDomain)` |
| `(FrameworkControl)-[:MAPS_TO_SUBDOMAIN {confidence}]` | No `confidence` property on actual relationships |

---

## 8. QUICK START

```bash
# Neo4j is external — start it
docker start d3fend-neo4j

# Langfuse stack (if needed)
docker compose up -d

# Load/refresh data (in order)
cd aegis_kg/etl
python 06_load_all_regulations.py
python 08_load_clause_subdomain_mappings.py
python 09_load_regulatory_timelines.py
python 10_load_sole_authority.py
python 11_load_complementarity_analysis.py

# Validate
cd aegis_kg && python validation/01_validate_phase1.py

# Start API
cd aegis_kg/api && python app.py
```

---

## 9. FILE STRUCTURE

```
aegis-kg-unified/
├── docker-compose.yml          # Langfuse v3 stack
├── requirements.txt
├── .env.example
├── README.md
├── AGENTS.md                   # Canonical agent reference
├── KG_MANIFEST.md             # This file — KG registry
├── MEMORY.md                  # Error log + solutions
├── aegis_kg/
│   ├── schema/                # Cypher DDL
│   ├── data/                  # CSV source files
│   ├── etl/                   # Numbered ETL loaders
│   ├── api/app.py             # Flask REST API
│   └── validation/            # Phase-1 validation suite
├── aegis_agents/              # LangGraph ReAct agent
├── aegis_eval/                # Evaluation pipeline
│   └── task_bank.yaml        # 45 eval tasks
└── scripts/
    ├── fix_neo4j_data.py
    └── restore_nist.py
```

---

**Version:** 2.0
**Last Updated:** 2026-04-29
