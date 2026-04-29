# KG_MANIFEST.md — AEGIS-KG-Unified Registry

**Version:** 1.0
**Created:** 2026-04-27
**Purpose:** Registry for the AEGIS-KG-Unified standalone project

---

## 1. KG SCOPE

This project contains **one knowledge graph**:

| Directory | Node Types | Neo4j Labels | Status |
|-----------|------------|--------------|--------|
| `aegis_kg/` | Regulatory reference (5 EU regulations) | `Regulation`, `Article`, `Clause`, `Domain`, `SubDomain`, `ComplementarityAnalysis` | ✅ Operational |

---

## 2. ISOLATION RULES

### Rule 1 — Single KG, Single Database

All nodes live in the same Neo4j instance. No label-based isolation needed.

### Rule 2 — ETL Is the Only Write Path

All data loading must go through ETL scripts in `aegis_kg/etl/`.

### Rule 3 — API Is Read-Only

The Flask API (`aegis_kg/api/app.py`) provides read-only queries.

---

## 3. NODE LABEL REFERENCE

| Label | Count | Description |
|-------|-------|-------------|
| `Regulation` | 5 | GDPR, CRA, NIS 2, DORA, AI Act |
| `Article` | 47 | Regulatory articles |
| `Clause` | 150 | Atomic normative requirements |
| `Domain` | 10 | D-01 to D-10 |
| `SubDomain` | 38 | D-01.1 to D-10.3 |
| `ComplementarityAnalysis` | 1 | GDPR-CRA overlap analysis |

---

## 4. QUICK START

```bash
# Start Neo4j
docker-compose up -d

# Load schema (via Neo4j Browser at http://localhost:7474)
# Paste contents of aegis_kg/schema/01_create_schema.cypher

# Run ETL (in order)
cd aegis_kg/etl
python 06_load_all_regulations.py
python 08_load_clause_subdomain_mappings.py
python 09_load_regulatory_timelines.py
python 10_load_sole_authority.py
python 11_load_complementarity_analysis.py

# Start API
cd aegis_kg/api && python app.py &

# Query
curl http://localhost:5000/api/regulations

# Validate
cd aegis_kg && python validation/01_validate_phase1.py
```

---

## 5. FILE STRUCTURE

```
aegis-kg-unified/
├── docker-compose.yml
├── requirements.txt
├── README.md
├── KG_MANIFEST.md
├── aegis_rca_ontology.ttl
└── aegis_kg/
    ├── schema/
    ├── data/
    ├── etl/
    ├── api/
    ├── validation/
    └── queries/
```

---

**Version:** 1.0
**Last Updated:** 2026-04-27