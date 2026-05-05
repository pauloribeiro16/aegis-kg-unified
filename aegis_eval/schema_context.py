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

5. SubDomain(subDomainId, name, soleAuthority, gapRisk, clauseCount, regulationCount, densityScore, avgNormativeIntensity, weightedDensity, coveringRegulations, effectiveCoverage, effectiveCoverageTier)
   - 38 nodes: D-01.1 through D-10.3
   - Format: D-XX.Y (DOT separator, e.g., D-01.1, D-02.3, D-10.2)
   - BATCH 9 properties (computed from graph):
     - clauseCount: integer — count of clauses mapped via MAPPED_TO
     - regulationCount: integer — count of distinct regulations covering this subdomain
     - densityScore: float — clauseCount / 5.0 (normalized by max 5 regulations)
     - avgNormativeIntensity: float — average NI of covering clauses (range 0-3.0)
     - weightedDensity: float — sum(NI) / 15.0 (NI-weighted, max 1.0)
     - coveringRegulations: list[string] — regulation IDs covering this subdomain
   - BATCH 10 properties (NI-weighted):
     - effectiveCoverage: float — sum of NI values of all clauses mapped to this SubDomain (higher = stronger regulatory pressure)
     - effectiveCoverageTier: string — 'HIGH' (>=8.0), 'MEDIUM' (>=4.0), 'LOW' (<4.0)

6. ComplementarityAnalysis(analysisId, regulation1Id, regulation2Id, jaccardIndex, conflictClassification, dynamicJaccard, dynamicSharedSubDomainCount, jaccardSource)
   - 10 nodes: all regulation pairs (5 choose 2)
   - BATCH 9: dynamic Jaccard computed from actual graph data
     - dynamicJaccard: float — recomputed from clause mappings (may differ from jaccardIndex)
     - dynamicSharedSubDomainCount: integer — actual shared SubDomain count
     - jaccardSource: 'DYNAMIC' — indicates computed from graph
   - jaccardIndex: original static value (kept for reference)

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
- (Domain)-[:HAS_SUBDOMAIN]->(SubDomain)        [NOT CONTAINS]
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
MATCH (d:Domain)-[:HAS_SUBDOMAIN]->(sd:SubDomain)<-[:MAPS_TO_SUBDOMAIN]-(fc:FrameworkControl) RETURN d.name AS domain, count(DISTINCT fc) AS nistCount ORDER BY nistCount DESC

### Subdomains covered by NIST controls (with regulatory comparison)
MATCH (c:Clause)-[:MAPPED_TO]->(sd:SubDomain)<-[:MAPS_TO_SUBDOMAIN]-(fc:FrameworkControl) RETURN sd.name AS subdomain, count(DISTINCT c) AS clauseCount, count(DISTINCT fc) AS nistCount ORDER BY clauseCount DESC

### Subdomains with NIST but no regulatory coverage
MATCH (fc:FrameworkControl)-[:MAPS_TO_SUBDOMAIN]->(sd:SubDomain) WHERE NOT EXISTS((:Clause)-[:MAPPED_TO]->(sd)) RETURN sd.subDomainId, sd.name ORDER BY sd.subDomainId

### Regulation coverage across domains
MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)-[:MAPPED_TO]->(sd:SubDomain)<-[:HAS_SUBDOMAIN]-(d:Domain) RETURN d.name AS domain, r.regulationId AS regulation, count(DISTINCT c) AS clauseCount ORDER BY domain, clauseCount DESC

### SUBDOMAIN DENSITY PATTERNS (Batch 9)
MATCH (sd:SubDomain) WHERE sd.clauseCount > 0 RETURN sd.subDomainId, sd.name, sd.clauseCount, sd.densityScore ORDER BY sd.densityScore DESC LIMIT 10

MATCH (sd:SubDomain) WHERE sd.regulationCount >= 4 RETURN sd.subDomainId, sd.name, sd.regulationCount, sd.coveringRegulations ORDER BY sd.regulationCount DESC

MATCH (d:Domain)-[:HAS_SUBDOMAIN]->(sd:SubDomain) RETURN d.domainId, d.name, count(sd) AS totalSubdomains, avg(sd.densityScore) AS avgDensity ORDER BY avgDensity DESC

### DYNAMIC JACCARD (Batch 9)
MATCH (ca:ComplementarityAnalysis) WHERE ca.jaccardSource = 'DYNAMIC' RETURN ca.regulation1Id, ca.regulation2Id, ca.dynamicJaccard AS jaccardIndex, ca.dynamicSharedSubDomainCount AS shared ORDER BY jaccardIndex DESC

### NI-WEIGHTED COVERAGE PATTERNS (Batch 10)
MATCH (sd:SubDomain) WHERE sd.effectiveCoverageTier = 'HIGH' RETURN sd.subDomainId, sd.name, sd.effectiveCoverage, sd.effectiveCoverageTier ORDER BY sd.effectiveCoverage DESC LIMIT 10

MATCH (sd:SubDomain) WHERE sd.effectiveCoverage >= 10.0 RETURN sd.subDomainId, sd.name, sd.effectiveCoverage, sd.effectiveCoverageTier, sd.clauseCount ORDER BY sd.effectiveCoverage DESC

MATCH (r:Regulation) WHERE r.effectiveCoverageTier IS NOT NULL RETURN r.regulationId, r.name, r.effectiveCoverageScore, r.effectiveCoverageTier ORDER BY r.effectiveCoverageScore DESC

### HEATMAP PATTERNS (Batch 11)
MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)-[:MAPPED_TO]->(sd:SubDomain)
RETURN sd.subDomainId, sd.name AS subdomain, r.regulationId AS regulation,
       count(c) AS clauseCount, sum(c.normativeIntensity) AS totalNI, avg(c.normativeIntensity) AS avgNI
ORDER BY sd.subDomainId, r.regulationId

MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)-[:MAPPED_TO]->(sd:SubDomain)
WITH sd.subDomainId AS sdId, sd.name AS sdName, collect(r.regulationId) AS regs, count(DISTINCT c) AS totalClauses
RETURN sdId, sdName, regs, totalClauses ORDER BY totalClauses DESC

### HOTSPOT PATTERNS (Batch 12)
MATCH (sd:SubDomain) WHERE sd.hotspotScore >= 3
RETURN sd.subDomainId, sd.name, sd.hotspotScore, sd.hotspotTier, sd.regulationCount, sd.coveringRegulations
ORDER BY sd.hotspotScore DESC

MATCH (sd:SubDomain) RETURN sd.hotspotTier AS tier, count(*) AS count ORDER BY tier

MATCH (d:Domain)-[:HAS_SUBDOMAIN]->(sd:SubDomain)
RETURN d.name AS domain, sd.hotspotTier AS tier, count(sd) AS count
ORDER BY domain, tier

### STRATEGIC TENSION PATTERNS (Batch 13)
MATCH (st:StrategicTension)-[:INVOLVES_REGULATION]->(r:Regulation)
WITH st, collect(r.regulationId) AS regs, st.conflictType AS conflictType, st.severity AS severity
RETURN st.tensionId AS tensionId, regs, conflictType, severity, st.description AS description
ORDER BY severity DESC

MATCH (st:StrategicTension)-[:AFFECTS_SUBDOMAIN]->(sd:SubDomain)
RETURN st.tensionId AS tensionId, st.conflictType AS conflictType, st.severity AS severity,
       sd.subDomainId AS subDomainId, sd.name AS subDomainName, st.description AS description
ORDER BY sd.subDomainId

### CONFLICT SEVERITY PATTERNS (Batch 14)
MATCH (ca:ComplementarityAnalysis)
WHERE ca.conflictSeverityScore IS NOT NULL
RETURN ca.analysisId AS analysisId, ca.regulation1Id AS reg1, ca.regulation2Id AS reg2,
       ca.conflictSeverityScore AS severityScore, ca.severityComponents AS components
ORDER BY severityScore DESC

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
        "cypher": "MATCH (d:Domain)-[:HAS_SUBDOMAIN]->(sd:SubDomain)<-[:MAPS_TO_SUBDOMAIN]-(fc:FrameworkControl) RETURN d.name AS domain, count(DISTINCT fc) AS nistControlCount ORDER BY nistControlCount DESC"
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
