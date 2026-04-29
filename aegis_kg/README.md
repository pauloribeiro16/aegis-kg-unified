# AEGIS Phase 1 Regulatory Reference Knowledge Graph

**Status:** ✅ PHASE 1 COMPLETE
**Purpose:** Regulatory reference knowledge (methodology foundation) — not case-specific

---

## Overview

This Knowledge Graph encodes the **Phase 1 Methodology regulatory knowledge** — the canonical, case-agnostic foundation of the AEGIS approach.

### What's in this KG

| Content | Count | Purpose |
|---------|-------|---------|
| Regulations | 5 | GDPR, CRA, NIS 2, DORA, AI Act |
| Articles | 47 | Regulatory articles |
| Clauses | 150 | Atomic requirements with normative intensity |
| Domains | 10 | D-01 to D-10 |
| Sub-Domains | 38 | D-01.1 to D-10.3 (10×38 taxonomy) |
| Complementarity Analysis | 1 | GDPR-CRA overlap |

**Total:** 252 nodes, 510 relationships

### What's NOT in this KG

Phase 2/3 outputs are **case-specific** and NOT loaded here:

- ❌ Obligations, Goals, Strategic Tensions, Rules
- ❌ NFRs, FRs, Threats, Risks, Mitigations
- ❌ Use Cases, Functional Requirements, Compliance Gates

These live in `02_CASES/<case>/` directories per case.

---

## Quick Start

### Neo4j is already running

```bash
# Verify
curl -s http://localhost:7474

# Query actual counts
curl -s -u neo4j:neo4j_password "http://localhost:7474/db/neo4j/tx/commit" \
  -H "Content-Type: application/json" \
  -d '{"statements":[{"statement":"MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY count DESC"}]}'
```

### API (port 5000)

```bash
# Start if not running
cd aegis_kg
python api/app.py &

# Query
curl http://localhost:5000/api/regulations
curl http://localhost:5000/api/clauses?keyword=encryption
curl http://localhost:5000/api/domains
curl http://localhost:5000/api/gap-analysis
```

### Validation

```bash
cd aegis_kg
python validation/01_validate_phase1.py
```

---

## Project Structure

```
aegis_kg/
├── data/
│   ├── 00_regulations.csv           # 5 regulations
│   ├── 01_domains.csv               # 10 domains
│   ├── 02_subdomains.csv            # 38 sub-domains
│   ├── 03_articles.csv             # 47 articles
│   ├── 04_clauses.csv              # 150 clauses
│   ├── 05_company_context.csv       # Sample (TinyTask)
│   └── 06_complementarity_analysis.csv  # GDPR-CRA overlap
├── schema/
│   ├── 01_create_schema.cypher      # ✅ LOADED (Phase 1)
│   ├── 02_create_phase2_schema.cypher  # NOT LOADED (case-specific)
│   └── 03_create_phase3_schema.cypher  # NOT LOADED (case-specific)
├── etl/
│   ├── 04_etl_fixed.py              # ✅ COMPLETE
│   ├── 02_create_clause_subdomain_relationships.py  # ✅ COMPLETE
│   ├── 03_fix_missing_relationships.py  # ⚠️ Has path bug
│   ├── 06_load_all_regulations.py  # ✅ COMPLETE
│   ├── 07_map_all_regulations.py   # ✅ COMPLETE
│   ├── 04_load_phase2_data.py       # NOT RUN (case-specific)
│   └── 05_load_phase3_data.py       # NOT RUN (case-specific)
├── api/
│   └── app.py                       # Flask API (23 endpoints)
├── queries/
│   └── 01_analysis_queries.py       # 8 analysis queries
├── validation/
│   └── 01_validate_phase1.py        # 37 tests
└── docs/
    └── API_DOCUMENTATION.md
```

---

## Key Queries

### Show all regulations
```cypher
MATCH (r:Regulation) RETURN r.regulationId, r.name ORDER BY r.regulationId
```

### Show clause → SubDomain mapping
```cypher
MATCH (c:Clause)-[:COVERS_SUBDOMAIN]->(sd:SubDomain)
RETURN c.clauseId, c.summary, sd.subDomainId
ORDER BY c.clauseId
LIMIT 20
```

### Find sole-authority Sub-Domains
```cypher
MATCH (c:Clause)-[:COVERS_SUBDOMAIN]->(sd:SubDomain)
WITH sd, collect(DISTINCT c.regulationId) as regs
WHERE size(regs) = 1
RETURN sd.subDomainId, sd.name, regs
```

### GDPR article coverage
```cypher
MATCH (a:Article)-[:DEFINES]->(c:Clause)
WHERE a.regulationId = 'GDPR'
RETURN a.articleId, count(c) as clauseCount
ORDER BY clauseCount DESC
```

---

## API Endpoints

### Working (return data)

| Endpoint | Description |
|----------|-------------|
| `GET /api/regulations` | List all 5 regulations |
| `GET /api/regulations/<id>/clauses` | Clauses for a regulation |
| `GET /api/clauses` | Search clauses |
| `GET /api/clauses/<id>` | Clause details |
| `GET /api/domains` | List domains/subdomains |
| `GET /api/gap-analysis` | Uncovered sub-domains |
| `GET /api/coverage` | Coverage analysis |
| `GET /api/overlap` | GDPR-CRA overlap |
| `GET /api/traceability` | Clause→article mapping |
| `GET /api/applicability` | Applicable regulations |

### Return empty (Phase 2/3 not loaded)

| Endpoint | Would return if loaded |
|----------|----------------------|
| `GET /api/obligations` | Case obligations |
| `GET /api/goals` | Privacy/Security goals |
| `GET /api/tensions` | Strategic tensions |
| `GET /api/rules` | Compliance rules |
| `GET /api/nfrs` | Non-functional requirements |
| `GET /api/frs` | Functional requirements |
| `GET /api/threats` | Threats (STRIDE/LINDDUN) |
| `GET /api/risks` | Risk assessments |
| `GET /api/mitigations` | Mitigation controls |

---

## Relationship to Other KGs

| KG | Scope | Data |
|----|-------|------|
| `aegis_kg/` | Methodology (Phase 1) | Regulatory reference |
| `threat_modeling_kg/` | Threat intel | D3FEND, CAPEC, CWE, ATT&CK, ATLAS |
| `compliance_mapping_kg/` | Framework mapping | NIST CSF 2.0, ISO 27001 |

All share the **SubDomain** node as the bridge.

---

## Documentation

| Document | Purpose |
|----------|---------|
| `PROJECT_STATUS.md` | Full project status and verification |
| `docs/API_DOCUMENTATION.md` | API usage guide |
| `00_METHODOLOGY/TEMPLATES/00_Taxonomy_Reference.md` | 10×38 taxonomy definition |
| `00_METHODOLOGY/Class_Models/phase1_contextual_definition.md` | Phase 1 class model |

---

**Last Updated:** 2026-04-15
**Status:** ✅ PHASE 1 REGULATORY REFERENCE COMPLETE
