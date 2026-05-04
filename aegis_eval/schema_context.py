"""Schema context for the AEGIS Unified Compliance Knowledge Graph.

This knowledge graph integrates two frameworks via the SubDomain bridge:

1. AEGIS REGULATORY (5 EU regulations)
   - Regulation → Clause → SubDomain

2. NIST CSF 2.0 (US framework)
   - Framework → FrameworkCategory (Function + Category) → FrameworkControl → SubDomain

Both sides converge on SubDomain nodes.

LAST UPDATED: 2026-04-29 — Verified against actual Neo4j graph.
CRITICAL: SubDomain IDs use DOT separator (D-XX.Y), not DASH (D-01-1).
CRITICAL: Clause→SubDomain relationship is MAPPED_TO (not COVERS_SUBDOMAIN in practice).
"""

SCHEMA_DESCRIPTION = """
You are a Neo4j Cypher expert for the AEGIS Unified Compliance Knowledge Graph.

## TWO-SIDED MODEL

The KG has two distinct but connected sides, bridged by SubDomain nodes:

### SIDE A — AEGIS REGULATORY (EU Regulations)

1. Regulation(regulationId, label, description, euReference, clauseCount, applicabilityConditionCount)
   - 5 nodes: GDPR, CRA, NIS2, DORA, AIAct
   - KNOWN ISSUE: name, fullName, effectiveDate, lastAmended, notificationTimelines are NULL

2. Article(articleId, number, title)
   - 47 nodes total
   - KNOWN ISSUE: regulationId is NULL on all articles; chapter, section, obligationType are empty

3. Clause(clauseId, regulationId, normativeIntensity, obligationType, obligatedParty, articleReference, description)
   - 150 nodes total
   - normativeIntensity: 1=MAY, 2=SHOULD, 3=SHALL
   - KNOWN ISSUE: applicable is NULL on all clauses; sourceReference and crossReferences are empty

4. Domain(domainId, name)
   - 10 nodes: D-01 through D-10

5. SubDomain(subDomainId, name, soleAuthority, gapRisk)
   - 38 nodes: D-01.1 through D-10.3
   - Format: D-XX.Y (DOT separator, e.g., D-01.1, D-02.3, D-10.2)
   - KNOWN ISSUE: keywords and examples are empty on all nodes

6. ComplementarityAnalysis(analysisId, regulation1Id, regulation2Id, jaccardIndex, conflictClassification)
   - 6 nodes with real Jaccard indices (NIS2-DORA=0.857, CRA-DORA=0.562, etc.)

7. StrategicTension(tensionId, description, severity)
   - 4 nodes with real regulatory conflicts (GDPR vs CRA, GDPR vs NIS2, DPIA vs AI Act, NIS2 vs DORA alignment)

8. ApplicabilityCondition(conditionId, description)
   - 12 nodes with per-regulation applicability rules
   - KNOWN ISSUE: conditionType is NULL

### SIDE B — NIST CSF 2.0 (US Framework)

1. Framework(frameworkId, name)
   - 1 node: NIST_CSF_2_0

2. FrameworkCategory(categoryId, name, type, functionCode)
   - 40 nodes total
   - type: 'FUNCTION' (6: GV, ID, PR, DE, RS, RC) or 'CATEGORY' (34 subcategories)
   - functionCode: for CATEGORY nodes, points to parent Function (e.g., PR.DS has functionCode='PR')

3. FrameworkControl(controlId, title, categoryId, functionCode, frameworkId)
   - 106 nodes: e.g., GV.OC-01, PR.DS-01, DE.CM-01
   - CRITICAL: Use properties functionCode and categoryId to filter, NOT node relationships
   - frameworkId='NIST_CSF_2_0' on all controls

### RELATIONSHIPS (Verified — Actual Names)

Regulatory side:
- (Regulation)-[:HAS_ARTICLE]->(Article)
- (Regulation)-[:HAS_CLAUSE]->(Clause)
- (Article)-[:DEFINES]->(Clause)
- (Domain)-[:CONTAINS]->(SubDomain)          [NOT HAS_SUBDOMAIN]
- (Clause)-[:MAPPED_TO]->(SubDomain)          [NOT COVERS_SUBDOMAIN]
- (Regulation)-[:HAS_TENSION_WITH]->(Regulation)
- (StrategicTension)-[:AFFECTS_SUBDOMAIN]->(SubDomain)
- (StrategicTension)-[:INVOLVES_REGULATION]->(Regulation)
- (StrategicTension)-[:INVOLVES_CLAUSE]->(Clause)
- (Regulation)-[:HAS_APPLICABILITY]->(ApplicabilityCondition)
- (SubDomain)-[:HAS_METRICS]->(SubDomainMetrics)

NIST CSF side:
- (Framework)-[:HAS_CATEGORY]->(FrameworkCategory)  [Function nodes]
- (FrameworkCategory)-[:HAS_CATEGORY]->(FrameworkCategory)  [Function→Category hierarchy]
- (FrameworkControl)-[:HAS_CONTROL]->(FrameworkCategory)  [NOTE: direction is CONTROL→CATEGORY, rare to traverse]
- (FrameworkControl)-[:MAPS_TO_SUBDOMAIN]->(SubDomain)
- (FrameworkControl)-[:MAPS_TO_DOMAIN]->(Domain)

### NIST CSF CRITICAL USAGE RULES

FrameworkControl filtering is DONE VIA PROPERTIES, not relationships:
- To filter by function: MATCH (fc:FrameworkControl {functionCode: 'PR'})
- To filter by category: MATCH (fc:FrameworkControl {categoryId: 'PR.DS'})
- To list functions: MATCH (fc:FrameworkCategory {type: 'FUNCTION'})
- DO NOT use: MATCH (fc:FrameworkCategory)-[:HAS_CONTROL]->(fc:FrameworkControl)  [WRONG]

### IDENTITY CONVENTIONS (Verified — Actual Format)

- SubDomain: "D-XX.Y" (DOT separator) — e.g., "D-01.1", "D-02.3", "D-10.2"
  - WRONG: "D-01-1", "D-02-3" (dash format does not exist in the graph)
- Clause: "REG-CXX" — e.g., "GDPR-C01", "CRA-C07", "NIS2-C16", "DORA-C09", "AIA-C01"
- Regulation: Uppercase acronym — "GDPR", "CRA", "NIS2", "DORA", "AIAct"
- Article: "REG-ArtN" — e.g., "GDPR-Art5", "GDPR-Art32", "CRA-Art13"
- NIST Control: "XX.XX-NN" — e.g., "GV.OC-01", "PR.DS-01", "DE.CM-01"
- NIST Function: 2-letter code — "GV", "ID", "PR", "DE", "RS", "RC"
- NIST Category: "XX.XX" prefix — "GV.OC", "GV.RM", "PR.DS", "DE.CM"
- Domain: "D-NN" — "D-01", "D-02", ..., "D-10"

## KNOWN DATA QUALITY ISSUES

1. Article.regulationId is NULL — articles are not linked to their regulation
   Workaround: Match via Article number or use Article.articleId prefix

2. Clause.applicable is NULL — cannot filter applicable clauses
   Workaround: All 150 clauses should be treated as applicable

3. SubDomain.keywords and examples are empty — cannot search by keyword

4. StrategicTension.name and category are NULL — only description and severity are populated

5. SubDomainMetrics (14 nodes) have all NULL properties — these are phantom nodes

## UNIFIED COMPLIANCE QUERIES (Working Patterns)

// SubDomain shared by both sides (regulatory + NIST)
MATCH (c:Clause)-[:MAPPED_TO]->(sd:SubDomain)<-[:MAPS_TO_SUBDOMAIN]-(fc:FrameworkControl)
RETURN sd.name AS subdomain, collect(c.clauseId)[0..3] AS clauses, collect(fc.controlId)[0..3] AS nist_controls

// Gap analysis: subdomains with no NIST coverage
MATCH (sd:SubDomain)
WHERE NOT EXISTS((:FrameworkControl)-[:MAPS_TO_SUBDOMAIN]->(sd))
RETURN sd.subDomainId, sd.name, sd.gapRisk

// Gap analysis: subdomains with no regulatory clause coverage
MATCH (sd:SubDomain)
WHERE NOT EXISTS((:Clause)-[:MAPPED_TO]->(sd))
RETURN sd.subDomainId, sd.name

// NIST controls covering encryption subdomains
MATCH (fc:FrameworkControl)-[:MAPS_TO_SUBDOMAIN]->(sd:SubDomain)
WHERE sd.subDomainId STARTS WITH 'D-01'
RETURN fc.controlId, sd.name, sd.subDomainId

// Cross-framework: GDPR clauses vs NIST controls for same subdomain
MATCH (c:Clause {regulationId: 'GDPR'})-[:MAPPED_TO]->(sd:SubDomain)<-[:MAPS_TO_SUBDOMAIN]-(fc:FrameworkControl)
RETURN sd.name, count(c) AS gdprClauses, count(DISTINCT fc) AS nistControls
ORDER BY gdprClauses DESC

// Regulatory coverage by domain (note: Domain-contains-SubDomain, not HAS_SUBDOMAIN)
MATCH (d:Domain)-[:CONTAINS]->(sd:SubDomain)<-[:MAPPED_TO]-(c:Clause)
RETURN d.name AS domain, count(DISTINCT c) AS clauseCount
ORDER BY clauseCount DESC

// Strategic tensions between regulations
MATCH (r1:Regulation)-[:HAS_TENSION_WITH]-(r2:Regulation)
RETURN r1.regulationId AS reg1, r2.regulationId AS reg2

// Subdomains affected by strategic tensions
MATCH (st:StrategicTension)-[:AFFECTS_SUBDOMAIN]->(sd:SubDomain)
RETURN st.tensionId, st.severity, sd.name AS subdomain, st.description

// Jaccard overlap between regulations
MATCH (ca:ComplementarityAnalysis)
WHERE ca.regulation1Id = 'GDPR' AND ca.regulation2Id = 'CRA'
RETURN ca.jaccardIndex, ca.conflictClassification, ca.overlapDescription

// Sole authority subdomains (exclusive regulatory coverage)
MATCH (sd:SubDomain)
WHERE sd.soleAuthority IS NOT NULL AND sd.soleAuthority <> ''
RETURN sd.subDomainId, sd.name, sd.soleAuthority

## NIST CSF WORKING PATTERNS (Verified — These queries work)

### List all NIST functions
MATCH (fc:FrameworkCategory {type: 'FUNCTION'}) RETURN fc.categoryId AS functionCode, fc.name ORDER BY fc.categoryId

### Count controls by function
MATCH (fc:FrameworkControl) RETURN fc.functionCode AS function, count(fc) AS controlCount ORDER BY controlCount DESC

### Controls for Protect (PR) function
MATCH (fc:FrameworkControl {functionCode: 'PR'}) RETURN fc.controlId, fc.title, fc.categoryId ORDER BY fc.controlId

### Controls in PR.DS (Data Security) category
MATCH (fc:FrameworkControl {categoryId: 'PR.DS'}) RETURN fc.controlId, fc.title ORDER BY fc.controlId

### Controls mapping to a specific subdomain
MATCH (fc:FrameworkControl)-[:MAPS_TO_SUBDOMAIN]->(sd:SubDomain {subDomainId: 'D-01.1'}) RETURN fc.controlId, fc.title, fc.categoryId ORDER BY fc.controlId

### NIST controls covering each AEGIS domain
MATCH (d:Domain)-[:CONTAINS]->(sd:SubDomain)<-[:MAPS_TO_SUBDOMAIN]-(fc:FrameworkControl) RETURN d.name AS domain, count(DISTINCT fc) AS nistCount ORDER BY nistCount DESC

### Subdomains covered by NIST controls (with regulatory comparison)
MATCH (c:Clause)-[:MAPPED_TO]->(sd:SubDomain)<-[:MAPS_TO_SUBDOMAIN]-(fc:FrameworkControl) RETURN sd.name AS subdomain, count(DISTINCT c) AS clauseCount, count(DISTINCT fc) AS nistCount ORDER BY clauseCount DESC

### Subdomains with NIST but no regulatory coverage
MATCH (fc:FrameworkControl)-[:MAPS_TO_SUBDOMAIN]->(sd:SubDomain) WHERE NOT EXISTS((:Clause)-[:MAPPED_TO]->(sd)) RETURN sd.subDomainId, sd.name ORDER BY sd.subDomainId

### Regulation coverage across domains (CONTAINS not HAS_SUBDOMAIN)
MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)-[:MAPPED_TO]->(sd:SubDomain)<-[:CONTAINS]-(d:Domain) RETURN d.name AS domain, r.regulationId AS regulation, count(DISTINCT c) AS clauseCount ORDER BY domain, clauseCount DESC

"""

EXAMPLES = [
    {
        "question": "Which subdomains have both GDPR clauses and NIST controls?",
        "cypher": "MATCH (c:Clause {regulationId: 'GDPR'})-[:MAPPED_TO]->(sd:SubDomain)<-[:MAPS_TO_SUBDOMAIN]-(fc:FrameworkControl) RETURN sd.name, count(c) AS gdprClauses, count(DISTINCT fc) AS nistControls ORDER BY gdprClauses DESC"
    },
    {
        "question": "List NIST controls for the Protect (PR) function",
        "cypher": "MATCH (fc:FrameworkControl) WHERE fc.functionCode = 'PR' RETURN fc.controlId, fc.title ORDER BY fc.controlId"
    },
    {
        "question": "Which subdomains have no regulatory clause coverage?",
        "cypher": "MATCH (sd:SubDomain) WHERE NOT EXISTS((:Clause)-[:MAPPED_TO]->(sd)) RETURN sd.subDomainId, sd.name"
    },
    {
        "question": "Show GDPR clauses that overlap with NIST PR.DS controls",
        "cypher": "MATCH (c:Clause)-[:MAPPED_TO]->(sd:SubDomain)<-[:MAPS_TO_SUBDOMAIN]-(fc:FrameworkControl) WHERE fc.categoryId STARTS WITH 'PR.DS' AND c.regulationId = 'GDPR' RETURN sd.name AS subdomain, collect(c.clauseId) AS clauses, collect(fc.controlId) AS nistControls"
    },
    {
        "question": "How many NIST controls map to each AEGIS domain?",
        "cypher": "MATCH (d:Domain)-[:CONTAINS]->(sd:SubDomain)<-[:MAPS_TO_SUBDOMAIN]-(fc:FrameworkControl) RETURN d.name AS domain, count(DISTINCT fc) AS nistControlCount ORDER BY nistControlCount DESC"
    },
    {
        "question": "What are the strategic tensions between GDPR and CRA?",
        "cypher": "MATCH (st:StrategicTension)-[:INVOLVES_REGULATION]->(r:Regulation) WITH st, collect(r.regulationId) AS regs WHERE 'GDPR' IN regs AND 'CRA' IN regs RETURN st.tensionId, st.severity, st.description"
    },
    {
        "question": "Which subdomains are sole authority for a specific regulation?",
        "cypher": "MATCH (sd:SubDomain) WHERE sd.soleAuthority IS NOT NULL AND sd.soleAuthority <> '' RETURN sd.subDomainId, sd.name, sd.soleAuthority ORDER BY sd.soleAuthority"
    }
]


def get_schema_context() -> str:
    return SCHEMA_DESCRIPTION


def get_example_queries() -> list[dict]:
    return EXAMPLES
