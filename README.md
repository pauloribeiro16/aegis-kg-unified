# AEGIS Knowledge Graph — Unified Regulatory Compliance

A standalone knowledge graph for regulatory compliance mapping across 5 EU regulations (GDPR, CRA, NIS 2, DORA, AI Act) using the AEGIS 10×38 security taxonomy.

---

## Overview

**Purpose:** Canonical, case-agnostic regulatory reference KG. Maps 150+ atomic normative clauses from 5 EU regulations to 38 AEGIS SubDomains across 10 security domains.

**Neo4j:** 5.18.1 Community (via Docker)

---

## Quick Start

```bash
# 1. Start Neo4j
docker-compose up -d

# 2. Verify
curl http://localhost:7474

# 3. Load schema
# Run schema/01_create_schema.cypher manually or via Neo4j Browser

# 4. Run ETL
cd aegis_kg/etl
python 06_load_all_regulations.py
python 08_load_clause_subdomain_mappings.py
python 09_load_regulatory_timelines.py
python 10_load_sole_authority.py
python 11_load_complementarity_analysis.py

# 5. Start API
cd aegis_kg/api
python app.py &

# 6. Query
curl http://localhost:5000/api/regulations
curl http://localhost:5000/api/domains
curl http://localhost:5000/api/gap-analysis

# 7. Validate
cd aegis_kg
python validation/01_validate_phase1.py
```

---

## Architecture

```
aegis_kg/
├── schema/         # Cypher schema (node types, constraints, indexes)
├── data/           # CSV source data (regulations, domains, clauses)
├── etl/             # ETL scripts (load, map, enrich)
├── api/             # Flask REST API (14 endpoints)
├── validation/      # Phase 1 validation tests
└── queries/        # Analysis queries

External: Neo4j 5.18.1 (Docker container)
```

---

## Neo4j Schema

**Node Types:** Regulation, Article, Clause, Domain, SubDomain, ComplementarityAnalysis

**Relationships:**
- `(Regulation)-[:HAS_ARTICLE]->(Article)`
- `(Article)-[:CONTAINS_CLAUSE]->(Clause)`
- `(Clause)-[:MAPS_TO_SUBDOMAIN]->(SubDomain)`
- `(Domain)-[:CONTAINS_SUBDOMAIN]->(SubDomain)`
- `(Regulation)-[:TIMELINE_EVENT]->(Clause)`

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/regulations` | GET | List all 5 regulations |
| `/api/regulations/<id>` | GET | Regulation details + articles |
| `/api/articles` | GET | All articles |
| `/api/clauses` | GET | All 150 clauses (filter by keyword) |
| `/api/clauses/<id>` | GET | Clause details + mapped subdomains |
| `/api/domains` | GET | All 10 domains |
| `/api/subdomains` | GET | All 38 subdomains |
| `/api/subdomain/<id>/clauses` | GET | Clauses mapped to subdomain |
| `/api/gap-analysis` | GET | Subdomains with no clause coverage |
| `/api/timeline/<regulation>` | GET | Regulation timeline events |
| `/api/complementarity` | GET | Overlapping regulations |

Full docs: `aegis_kg/api/app.py`

---

## Data Model

| Regulation | Articles | Clauses | Effective Date |
|------------|----------|---------|----------------|
| GDPR | 99 | ~50 | 2018-05-25 |
| CRA | 58 | ~30 | 2024-09-11 |
| NIS 2 | 41 | ~25 | 2024-10-17 |
| DORA | 51 | ~20 | 2025-01-17 |
| AI Act | 113 | ~25 | 2026-08-01 |

---

## Requirements

- Python 3.10+
- Docker + Docker Compose
- Neo4j 5.18.1 Community

```bash
pip install -r requirements.txt
```

---

## Project Structure

```
aegis-kg-unified/
├── docker-compose.yml     # Neo4j container
├── requirements.txt       # Python dependencies
├── aegis_rca_ontology.ttl # OWL ontology
├── README.md              # This file
├── KG_MANIFEST.md         # KG registry and isolation rules
└── aegis_kg/
    ├── schema/            # Cypher DDL
    ├── data/              # CSV source files
    ├── etl/               # ETL scripts
    ├── api/               # Flask API
    ├── validation/        # Tests
    └── PROJECT_STATUS.md  # Full status
```

---

**Version:** 1.0
**Author:** AEGIS Research Team