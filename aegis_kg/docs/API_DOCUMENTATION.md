# AEGIS Phase 1 Knowledge Graph - API Documentation

## Overview

The AEGIS Phase 1 Knowledge Graph REST API provides programmatic access to the regulatory compliance mapping data stored in Neo4j. The API enables querying regulations, clauses, coverage analysis, gap detection, and traceability.

**Base URL:** `http://localhost:5000`  
**Version:** 1.0.0  
**Status:** Operational

---

## Quick Start

### 1. Start the API Server

```bash
cd phase1_implementation
python api/app.py
```

The server will start on `http://localhost:5000`.

### 2. Test the Connection

```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "neo4j_version": "5.18.1"
}
```

---

## API Endpoints

### 1. List All Regulations

**GET** `/api/regulations`

Returns all regulations loaded in the knowledge graph.

**Example:**
```bash
curl http://localhost:5000/api/regulations
```

**Response:**
```json
[
  {
    "regulationId": "GDPR",
    "name": "GDPR",
    "fullName": "General Data Protection Regulation 2016/679",
    "type": "DATA_PROTECTION",
    "effectiveDate": "2018-05-25",
    "primaryFocus": "Data protection and privacy"
  },
  ...
]
```

---

### 2. Get Regulation Clauses

**GET** `/api/regulations/<reg_id>/clauses`

Returns all clauses for a specific regulation.

**Example:**
```bash
curl http://localhost:5000/api/regulations/GDPR/clauses
```

**Response:**
```json
[
  {
    "clauseId": "GDPR-32-1-a",
    "number": "32(1)(a)",
    "summary": "Encryption at rest for personal data",
    "applicable": true,
    "normativeIntensity": 3,
    "obligationType": "CONTINUOUS",
    "articleId": "GDPR-Art32"
  },
  ...
]
```

---

### 3. Search Clauses

**GET** `/api/clauses?keyword=<term>`

Search clauses by keyword in summary or description.

**Example:**
```bash
curl "http://localhost:5000/api/clauses?keyword=encryption"
```

**Response:**
```json
[
  {
    "regulationId": "GDPR",
    "clauseId": "GDPR-32-1-a",
    "summary": "Encryption at rest for personal data",
    "applicable": true,
    "normativeIntensity": 3,
    "obligationType": "CONTINUOUS"
  },
  ...
]
```

---

### 4. Get Clause Details

**GET** `/api/clauses/<clause_id>`

Returns detailed information about a specific clause, including relationships to articles and sub-domains.

**Example:**
```bash
curl http://localhost:5000/api/clauses/GDPR-32-1-a
```

**Response:**
```json
{
  "clauseId": "GDPR-32-1-a",
  "number": "32(1)(a)",
  "summary": "Encryption at rest for personal data",
  "description": "The controller and the processor shall implement...",
  "applicable": true,
  "normativeIntensity": 3,
  "obligationType": "CONTINUOUS",
  "applicabilityReason": "Company processes personal data of EU data subjects",
  "regulationId": "GDPR",
  "regulationName": "GDPR",
  "articleId": "GDPR-Art32",
  "articleTitle": "Security of processing",
  "subDomains": ["D-01.1"],
  "domains": ["D-01"]
}
```

---

### 5. Gap Analysis

**GET** `/api/gap-analysis`

Identifies sub-domains with NO clause coverage (regulatory gaps).

**Example:**
```bash
curl http://localhost:5000/api/gap-analysis
```

**Response:**
```json
[
  {
    "subDomainId": "D-02.4",
    "name": "Coordinated Disclosure",
    "description": "Coordinated disclosure of vulnerabilities with vendors",
    "domainId": "D-02",
    "domainName": "Vulnerability Management",
    "riskLevel": "NIS2"
  },
  ...
]
```

---

### 6. Coverage Analysis

**GET** `/api/coverage`

Returns coverage analysis by regulation and by domain, plus overall summary.

**Example:**
```bash
curl http://localhost:5000/api/coverage
```

**Response:**
```json
{
  "by_regulation": [
    {
      "reg": "GDPR",
      "regName": "GDPR",
      "regCoverage": 20,
      "totalSD": 38,
      "coveragePct": 52.6
    },
    ...
  ],
  "by_domain": [
    {
      "domain": "D-01",
      "domainName": "Data Protection & Encryption",
      "totalInDomain": 5,
      "covered": 4,
      "coveragePct": 80.0
    },
    ...
  ],
  "summary": {
    "total": 38,
    "covered": 26,
    "overallPct": 68.4
  }
}
```

---

### 7. Applicable Regulations

**GET** `/api/applicability`

Shows which regulations and clauses apply to the company context.

**Example:**
```bash
curl http://localhost:5000/api/applicability
```

**Response:**
```json
[
  {
    "regId": "GDPR",
    "name": "GDPR",
    "applicableClauses": 45,
    "clauses": ["GDPR-32-1-a", "GDPR-32-1-b", ...]
  },
  ...
]
```

---

### 8. Traceability

**GET** `/api/traceability`

Returns clause-to-article traceability mapping.

**Example:**
```bash
curl http://localhost:5000/api/traceability
```

**Response:**
```json
[
  {
    "regulationId": "GDPR",
    "articleId": "GDPR-Art32",
    "articleTitle": "Security of processing",
    "articleNumber": "32",
    "clauseCount": 5,
    "clauseIds": ["GDPR-32-1-a", "GDPR-32-1-b", ...]
  },
  ...
]
```

---

### 9. Regulation Overlap

**GET** `/api/overlap`

Identifies sub-domains covered by multiple regulations (overlap analysis).

**Example:**
```bash
curl http://localhost:5000/api/overlap
```

**Response:**
```json
[
  {
    "subDomain": "D-01.1",
    "sdName": "Encryption",
    "regulations": ["GDPR", "CRA"],
    "clauseCount": 3
  },
  ...
]
```

---

### 10. List Domains

**GET** `/api/domains`

Returns all domains and their sub-domains with coverage status.

**Example:**
```bash
curl http://localhost:5000/api/domains
```

**Response:**
```json
[
  {
    "domainId": "D-01",
    "name": "Data Protection & Encryption",
    "description": "Data protection, encryption, pseudonymisation, anonymisation",
    "subdomains": [
      {
        "subDomainId": "D-01.1",
        "name": "Encryption",
        "description": "Data encryption at rest and in transit",
        "hasCoverage": true
      },
      ...
    ]
  },
  ...
]
```

---

## Error Responses

All endpoints return errors in the following format:

```json
{
  "error": "Error message description"
}
```

HTTP status codes:
- `200` - Success
- `400` - Bad request (e.g., invalid parameters)
- `404` - Not found (e.g., clause not found)
- `500` - Internal server error

---

## Query Layer (Direct Neo4j Access)

For advanced users, direct Cypher queries can be executed via the Python query layer:

```bash
python queries/01_analysis_queries.py
```

This runs all 8 built-in analysis queries:
1. Company Context Summary
2. Applicable Regulations
3. Normative Intensity Distribution
4. Gap Analysis
5. Coverage Analysis (by regulation and domain)
6. Regulation Overlap
7. Clause-Article Traceability

---

## Validation

Run the validation suite to verify system health:

```bash
python validation/01_validate_phase1.py
```

This runs 30 tests covering:
- Neo4j connectivity
- Schema constraints (unique IDs)
- Node counts (expected values)
- Relationship integrity
- Data quality
- Query performance
- API endpoint availability

---

## Data Model

### Node Types

| Type | Count | Key Properties |
|------|-------|----------------|
| `Regulation` | 5 | regulationId, name, fullName, type, effectiveDate |
| `Domain` | 10 | domainId, name, description, primaryRegulatoryDriver |
| `SubDomain` | 38 | subDomainId, name, description, keywords, gapRisk |
| `Article` | 9 | articleId, number, title, summary, obligationType |
| `Clause` | 55 | clauseId, number, summary, applicable, normativeIntensity |
| `CompanyContext` | 1 | contextId, companyName, industry, size, dataTypes |
| `ComplementarityAnalysis` | 1 | analysisId, regulation1Id, regulation2Id, jaccardIndex |

### Relationship Types

| Type | Count | Description |
|------|-------|-------------|
| `HAS_ARTICLE` | 9 | Regulation → Article |
| `HAS_CLAUSE` | 55 | Regulation → Clause |
| `DEFINES` | 34 | Article → Clause |
| `CONTAINS` | 38 | Domain → SubDomain |
| `COVERS_SUBDOMAIN` | 55 | Clause → SubDomain |
| `PRIMARY_FOCUS` | 5 | Regulation → Domain |
| `OVERLAPS_WITH` | 2 | ComplementarityAnalysis → Regulation |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `http://localhost:7474` | Neo4j HTTP endpoint |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `neo4j_password` | Neo4j password |

---

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Client    │─────▶│  Flask API   │─────▶│   Neo4j     │
│  (curl,     │◀─────│  (port 5000) │◀─────│  (port 7474)│
│   browser)  │      └──────────────┘      └─────────────┘
└─────────────┘
```

---

## Troubleshooting

### API won't start
- Check Neo4j is running: `curl -u neo4j:neo4j_password http://localhost:7474`
- Check port 5000 is not in use: `lsof -i :5000`

### Queries return empty results
- Run ETL script first: `python 04_etl_fixed.py`
- Run relationship fix: `python etl/03_fix_missing_relationships.py`
- Run clause-subdomain mapping: `python etl/02_create_clause_subdomain_relationships.py`

### Validation fails
- Check Neo4j connection details in validation script
- Verify all ETL scripts have been run successfully
- Check API server is running on port 5000

---

## License

AEGIS Methodology - Internal Use Only
