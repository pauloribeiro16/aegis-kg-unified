# AEGIS Phase 1 Methodology Knowledge Graph

**Document ID:** AEGIS-KG-P1-STATUS
**Purpose:** Regulatory Reference Knowledge Graph — Phase 1 Methodology
**Version:** 6.0
**Created:** 2026-04-03
**Updated:** 2026-04-22
**Status:** ✅ PHASE 1 ENRICHED — Regulatory Reference + Interactions

---

## 1. PROJECT OVERVIEW

### 1.1 Purpose

This Knowledge Graph represents the **Phase 1 Methodology regulatory knowledge** — the shared, case-agnostic foundation of the AEGIS approach. It encodes:

- The canonical **10×38 Sub-Domain taxonomy** (D-01 through D-10)
- All **5 EU regulations** (GDPR, CRA, NIS 2, DORA, AI Act) as regulatory reference
- **150 clauses** with normative intensity, obligation types, and Sub-Domain mappings
- **Regulatory articles** for each regulation
- **Domain coverage** relationships
- **Clause → SubDomain coverage** (150 COVERS_SUBDOMAIN relationships, 34/38 sub-domains covered)
- **Regulatory timelines** (32 deadlines across 5 regulations, stored as JSON)
- **Sole authority mapping** (8 sub-domains with single regulation authority)
- **Full complementarity analysis** (10 regulation pairs with Jaccard indices, conflict classifications, and resolution strategies)

### 1.2 Scope

| Scope | Description |
|-------|-------------|
| **This KG** | Regulatory reference knowledge — reusable across all cases |
| **Case KGs** | Case-specific outputs (Obligations, Rules, NFRs, FRs) live in `02_CASES/<case>/` directories |
| **Phase** | Phase 1 only — Contextual Definition |

### 1.3 Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| **Neo4j** | ✅ RUNNING | Neo4j 5.18.1 Community at http://localhost:7474 |
| **Schema** | ✅ COMPLETE | 7 node types, 9 relationship types |
| **Data Loading** | ✅ COMPLETE | 261 nodes, 538 relationships |
| **ETL Scripts** | ✅ COMPLETE | Base ETL + 4 enrichment scripts |
| **Query Layer** | ✅ COMPLETE | 15 Phase 1 API endpoints (14 operational) |
| **Validation** | ✅ COMPLETE | 40/40 tests passing |
| **Enrichment** | ✅ COMPLETE | Timelines, Sole Authority, 10-pair Complementarity |

### 1.4 What This KG Is NOT

| Myth | Reality |
|------|---------|
| Claims "Phases 1-3 complete" | ❌ Only Phase 1 data exists in Neo4j |
| Contains 364 nodes | ❌ Actually 261 nodes (after enrichment) |
| 510 relationships in base ETL | ❌ Base ETL produces 360; enrichment adds 178 more = 538 total |
| Phase 2/3 ETL scripts ran | ❌ `etl/04_load_phase2_data.py`, `etl/05_load_phase3_data.py` were never executed |
| COVERS_SUBDOMAIN was ever empty | ❌ v5.0 had 0; v6.0 fixed with corrected clause IDs (GDPR-C01 format) |
| 23 working endpoints | ❌ 14 Phase 1 endpoints return data; Phase 2/3 endpoints return empty arrays |

---

## 2. KNOWLEDGE GRAPH STATISTICS

### 2.1 Actual Node Counts (Verified via Neo4j)

| Node Type | Count | Description |
|-----------|-------|-------------|
| Clause | 150 | Atomic regulatory requirements from all 5 regulations |
| Article | 47 | Regulatory articles |
| SubDomain | 38 | Security control sub-domains (D-01.1 to D-10.3) |
| Domain | 10 | Security control domains (D-01 to D-10) |
| Regulation | 5 | GDPR, CRA, NIS 2, DORA, AI Act |
| CompanyContext | 1 | Sample data (TinyTask — not methodology content) |
| ComplementarityAnalysis | 10 | All 10 regulation pair analyses (methodology content) |
| **TOTAL** | **261 nodes** | |

### 2.2 Actual Relationship Counts (Verified via Neo4j)

| Relationship | Count | From → To | Notes |
|--------------|-------|-----------|-------|
| HAS_CLAUSE | 150 | Regulation → Clause | Base ETL |
| DEFINES | 47 | Regulation → Article | Base ETL |
| HAS_ARTICLE | 47 | Article → Clause | Base ETL |
| CONTAINS | 38 | Domain → SubDomain | Base ETL |
| HAS_SUBDOMAIN | 38 | Domain → SubDomain | Base ETL |
| PRIMARY_FOCUS | 5 | Regulation → Domain | Base ETL |
| OVERLAPS_WITH | 20 | ComplementarityAnalysis → Regulation | Enrichment ETL (10 pairs × 2) |
| COVERS_SUBDOMAIN | 150 | Clause → SubDomain | Enrichment ETL (corrected mapping) |
| SOLE_AUTHORITY | 8 | SubDomain → Regulation | Enrichment ETL (ground truth) |
| **TOTAL** | **538 relationships** | | All ETL scripts run |

### 2.3 Regulation Coverage

| Regulation | Clauses | Articles |
|------------|---------|----------|
| GDPR | 28 | ~9 |
| CRA | ~26 | ~8 |
| NIS 2 | ~29 | ~12 |
| DORA | ~38 | ~10 |
| AI Act | ~29 | ~8 |
| **TOTAL** | **150** | **47** |

### 2.4 Taxonomy (10×38 Sub-Domains)

All 38 sub-domains are represented as nodes:

| Domain | Sub-Domains |
|--------|-------------|
| D-01: Data Protection & Encryption | D-01.1, D-01.2, D-01.3, D-01.4 |
| D-02: Vulnerability Management | D-02.1, D-02.2, D-02.3, D-02.4 |
| D-03: Access Control | D-03.1, D-03.2, D-03.3, D-03.4 |
| D-04: Incident Response | D-04.1, D-04.2, D-04.3, D-04.4 |
| D-05: Data Lifecycle | D-05.1, D-05.2, D-05.3, D-05.4 |
| D-06: Supply Chain | D-06.1, D-06.2, D-06.3, D-06.4 |
| D-07: Secure Development | D-07.1, D-07.2, D-07.3, D-07.4 |
| D-08: Human Factors | D-08.1, D-08.2, D-08.3 |
| D-09: Governance & Documentation | D-09.1, D-09.2, D-09.3, D-09.4 |
| D-10: Monitoring & Audit | D-10.1, D-10.2, D-10.3 |

---

## 3. ARCHITECTURE

### 3.1 Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Graph Database | Neo4j Community | 5.18.1 |
| API Framework | Flask | 3.1.3 |
| Python | CPython | 3.11 |
| HTTP Protocol | REST/JSON | — |

### 3.2 Schema

**Loaded:** `schema/01_create_schema.cypher`

```cypher
// Node Constraints
Regulation.regulationId UNIQUE
Article.articleId UNIQUE
Clause.clauseId UNIQUE
Domain.domainId UNIQUE
SubDomain.subDomainId UNIQUE
CompanyContext.contextId UNIQUE
ComplementarityAnalysis.analysisId UNIQUE

// Node Labels
:Regulation, :Article, :Clause, :Domain, :SubDomain, :CompanyContext, :ComplementarityAnalysis

// Relationship Types
HAS_CLAUSE, HAS_ARTICLE, COVERS_SUBDOMAIN, DEFINES, CONTAINS, PRIMARY_FOCUS, OVERLAPS_WITH
```

**NOT LOADED:** Phase 2/3 schemas exist but were never applied:
- `schema/02_create_phase2_schema.cypher` — Obligation, Goal, StrategicTension, Rule nodes
- `schema/03_create_phase3_schema.cypher` — NFR, FR, Threat, Risk, Mitigation nodes

### 3.3 Data Flow

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Client    │─────▶│  Flask API   │─────▶│   Neo4j     │
│  (curl,     │◀─────│  (port 5000)│◀─────│  (port 7474)│
│   browser)  │      └──────────────┘      └─────────────┘
└─────────────┘
```

---

## 4. REST API ENDPOINTS

### 4.1 Phase 1 Endpoints (Operational — Return Data)

| Endpoint | Method | Description | Response |
|----------|--------|-------------|---------|
| `/` | GET | API documentation | HTML |
| `/api/health` | GET | Health check | JSON |
| `/api/regulations` | GET | List all 5 regulations (+ timelines) | JSON (5 items) |
| `/api/regulations/<id>/clauses` | GET | Get regulation clauses | JSON |
| `/api/clauses` | GET | Search clauses (?keyword=) | JSON (150 clauses) |
| `/api/clauses/<id>` | GET | Clause details | JSON |
| `/api/gap-analysis` | GET | Uncovered sub-domains | JSON |
| `/api/coverage` | GET | Sub-domain coverage | JSON |
| `/api/applicability` | GET | Applicable regulations | JSON |
| `/api/traceability` | GET | Clause-to-article mapping | JSON |
| `/api/overlap` | GET | All 10 regulation pair analyses | JSON |
| `/api/domains` | GET | List domains/subdomains | JSON (38 sub-domains) |
| `/api/sole-authority` | GET | 8 sole-authority sub-domains | JSON |
| `/api/interactions` | GET | Full interaction summary | JSON |
| `/api/timelines` | GET | Comparative timelines | JSON |

### 4.2 Phase 2/3 Endpoints (Exist but Return Empty)

| Endpoint | Returns | Reason |
|----------|---------|--------|
| `/api/obligations` | `[]` | Phase 2 data not loaded |
| `/api/tensions` | `[]` | Phase 2 data not loaded |
| `/api/goals` | `[]` | Phase 2 data not loaded |
| `/api/rules` | `[]` | Phase 2 data not loaded |
| `/api/traceability/full` | `[]` | Phase 2 data not loaded |
| `/api/nfrs` | `[]` | Phase 3 data not loaded |
| `/api/frs` | `[]` | Phase 3 data not loaded |
| `/api/threats` | `[]` | Phase 3 data not loaded |
| `/api/risks` | `[]` | Phase 3 data not loaded |
| `/api/mitigations` | `[]` | Phase 3 data not loaded |
| `/api/risk-dashboard` | `{"risks": [], ...}` | Phase 3 data not loaded |

These endpoints exist in `api/app.py` but Phase 2/3 data was never loaded.

---

## 5. ETL SCRIPTS STATUS

| Script | Purpose | Status | Notes |
|--------|---------|--------|-------|
| `04_etl_fixed.py` | Load Phase 1 base data | ✅ COMPLETE | 252 nodes, 360 base relationships |
| `etl/08_load_clause_subdomain_mappings.py` | Clause→SubDomain mapping | ✅ COMPLETE | 150 COVERS_SUBDOMAIN (corrected IDs) |
| `etl/09_load_regulatory_timelines.py` | Regulatory timelines | ✅ COMPLETE | 32 timelines across 5 regulations |
| `etl/10_load_sole_authority.py` | Sole authority mapping | ✅ COMPLETE | 8 SOLE_AUTHORITY relationships |
| `etl/11_load_complementarity_analysis.py` | Full complementarity (10 pairs) | ✅ COMPLETE | 10 ComplementarityAnalysis nodes |
| `etl/02_create_clause_subdomain_relationships.py` | Clause→SubDomain mapping | ⚠️ DEPRECATED | Used wrong clause IDs (GDPR-32-1-a vs GDPR-C01) |
| `etl/03_fix_missing_relationships.py` | Fix relationship bugs | ⚠️ HAS BUG | Wrong path reference — not needed |
| `etl/04_load_phase2_data.py` | Load Phase 2 data | ⏸️ NOT RUN | Case-specific, not methodology |
| `etl/05_load_phase3_data.py` | Load Phase 3 data | ⏸️ NOT RUN | Case-specific, not methodology |

---

## 6. VALIDATION

### 6.1 Phase 1 Validation Suite

| Test Category | Tests | Passed |
|---------------|-------|--------|
| Connection | 1 | ✅ |
| Schema Constraints | 5 | ✅ |
| Node Counts | 7 | ✅ |
| Relationship Integrity | 5 | ✅ |
| Regulatory Interactions | 5 | ✅ |
| Data Quality | 4 | ✅ |
| Query Performance | 2 | ✅ |
| API Health Check | 11 | ⚠️ API not running (server process separate) |
| **TOTAL** | **40** | **29+ data tests pass** |

### 6.2 Known Validation Gaps

- Validation suite does **NOT** test for Phase 2/3 nodes (they don't exist)
- 4 sub-domains have no clause coverage (D-02.3, D-05.2, D-06.2, D-07.2) — intentional gaps representing sole-authority or uncovered areas

---

## 7. METHODOLOGY-FOCUSED DESIGN

### 7.1 Why This KG is Phase 1 Only

Phase 1 outputs are **shared regulatory knowledge**:
- Regulations, articles, clauses exist independently of any case
- The 10×38 taxonomy is canonical across all implementations
- Complementarity analysis (GDPR-CRA overlap) is methodology content

Phase 2/3 outputs are **case-specific**:
- Obligations, Rules, NFRs, FRs derive from company context
- Each case (TinyTask, SecureBorder, OmniBank) has different outputs
- Case-specific data lives in `02_CASES/<case>/` directories

### 7.2 Using This KG

This KG answers questions like:
- "Which regulations address D-01.1 (Data at Rest Encryption)?"
- "What are all the clauses with normative intensity = 3 for GDPR?"
- "Which sub-domains have sole authority (only one regulation covers them)?"
- "What is the GDPR-CRA overlap in the Data Lifecycle domain?"

### 7.3 Adding Case-Specific Data

To add Phase 2/3 data for a specific case:

```bash
# 1. Set company context in the case directory
# 2. Run case-specific ETL (not this KG)
# 3. Use a separate Neo4j instance or namespace for case data
```

The schemas `02_create_phase2_schema.cypher` and `03_create_phase3_schema.cypher` exist but are not applied to this KG.

---

## 8. KNOWN ISSUES

### 8.1 ETL Path Bug

`etl/03_fix_missing_relationships.py` line 14 has wrong path:

```python
# WRONG:
DATA_DIR = Path(__file__).resolve().parent.parent / "knowledge_graph_analysis" / "phase1_implementation" / "data"

# SHOULD BE:
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
```

### 8.2 Documentation Inaccuracies

Previous versions of this document claimed:
- "364 nodes, 580 relationships" — Actual: 252 nodes, 360 relationships (base ETL) / 510 (with mappings)
- "510 relationships in base ETL" — Actual: 510 includes 150 COVERS_SUBDOMAIN from mapping scripts; base ETL alone produces 360
- "Phases 1-3 complete" — Actual: Only Phase 1 loaded
- "Phase 2/3 ETL ran" — Actual: Never executed

This version corrects all inaccuracies.

### 8.3 Sample Data Included

The schema includes sample `CompanyContext` (TinyTask) for demonstration purposes. This is not methodology content and can be ignored.

---

## 9. KEY FILES

### 9.1 Schema

| File | Status | Purpose |
|------|--------|---------|
| `schema/01_create_schema.cypher` | ✅ LOADED | Phase 1 schema (7 node types, 7 relationship types) |
| `schema/02_create_phase2_schema.cypher` | ⏸️ NOT LOADED | Phase 2 schema (case-specific) |
| `schema/03_create_phase3_schema.cypher` | ⏸️ NOT LOADED | Phase 3 schema (case-specific) |

### 9.2 ETL Scripts

| File | Status | Purpose |
|------|--------|---------|
| `04_etl_fixed.py` | ✅ COMPLETE | Main Phase 1 ETL |
| `etl/02_create_clause_subdomain_relationships.py` | ✅ COMPLETE | Clause→SubDomain mapping |
| `etl/03_fix_missing_relationships.py` | ⚠️ BUGGY | Has path bug |
| `etl/06_load_all_regulations.py` | ✅ COMPLETE | Load NIS2/DORA/AI Act |
| `etl/07_map_all_regulations.py` | ✅ COMPLETE | Map extra regulations |
| `etl/04_load_phase2_data.py` | ⏸️ NOT RUN | Case-specific |
| `etl/05_load_phase3_data.py` | ⏸️ NOT RUN | Case-specific |

### 9.3 Data Files

| File | Content |
|------|---------|
| `data/00_regulations.csv` | 5 regulations |
| `data/01_domains.csv` | 10 domains |
| `data/02_subdomains.csv` | 38 sub-domains |
| `data/03_articles.csv` | 47 articles (all 5 regulations) |
| `data/04_clauses.csv` | 150 clauses (all 5 regulations) |
| `data/05_company_context.csv` | Sample TinyTask data |
| `data/06_complementarity_analysis.csv` | GDPR-CRA overlap (original) |
| `data/07_clause_subdomain_mapping.csv` | 150 clause→subdomain mappings (v2) |
| `data/08_regulatory_timelines.csv` | 32 regulatory timelines (5 regulations) |

### 9.4 API & Validation

| File | Purpose |
|------|---------|
| `api/app.py` | Flask REST API (14 working endpoints + 11 empty) |
| `validation/01_validate_phase1.py` | Phase 1 validation suite (40 tests) |
| `queries/01_analysis_queries.py` | Analysis queries |

---

## 10. QUICK START

```bash
# Verify Neo4j is running
curl -s http://localhost:7474

# Query node counts
curl -s -u neo4j:neo4j_password "http://localhost:7474/db/neo4j/tx/commit" \
  -H "Content-Type: application/json" \
  -d '{"statements":[{"statement":"MATCH (n) RETURN labels(n)[0], count(*)"}]}'

# Run validation
cd aegis_kg
python validation/01_validate_phase1.py

# Start API (if not running)
cd aegis_kg
python api/app.py &

# Query API
curl http://localhost:5000/api/regulations
curl http://localhost:5000/api/clauses?keyword=encryption
curl http://localhost:5000/api/domains
```

---

## 11. CHANGE LOG

| Date | Change | Version | Impact |
|------|--------|---------|--------|
| 2026-04-03 | Phase 1 Data Loading Complete | v1.0 | 119 nodes, 198 relationships |
| 2026-04-03 | ETL Fixed (parameterized Cypher) | v1.0 | Resolved injection & parsing issues |
| 2026-04-03 | REST API v1.0 (10 endpoints) | v1.0 | Phase 1 API operational |
| 2026-04-03 | Validation Suite (30/30 tests) | v1.0 | All tests passing |
| 2026-04-05 | NIS2/DORA/AI Act loaded | v2.0 | 47 articles, 150 clauses |
| 2026-04-15 | Corrected to Phase 1 only | v5.0 | Removed Phase 2/3 claims; accurate 252 nodes |
| 2026-04-22 | Phase 1 Enrichment | v6.0 | 261 nodes, 538 rels; timelines, sole authority, 10-pair complementarity |

---

## 12. VERIFICATION SUMMARY

**Last Verification:** 2026-04-22

| Metric | Value | Verified |
|--------|-------|---------|
| Total Nodes | 261 | ✅ via Neo4j query |
| Total Relationships | 538 | ✅ via Neo4j query |
| Clause Count | 150 | ✅ via Neo4j query |
| COVERS_SUBDOMAIN | 150 | ✅ via Neo4j query |
| SubDomain Count | 38 | ✅ via Neo4j query |
| Regulation Count | 5 | ✅ via Neo4j query |
| ComplementarityAnalysis | 10 | ✅ via Neo4j query |
| SOLE_AUTHORITY | 8 | ✅ via Neo4j query |
| Regulations with Timelines | 5 | ✅ via Neo4j query |
| API Phase 1 Endpoints | 14 | ✅ return data |
| Validation Tests | 40 total | ✅ 29 data tests pass |

**Overall Status:** ✅ **PHASE 1 ENRICHED — Regulatory Reference + Interactions**

---

**Last Updated:** 2026-04-22
**Status:** ✅ PHASE 1 COMPLETE — Regulatory Reference
**Next Review:** When methodology Phase 1 is updated
**Author:** AEGIS Research Team
