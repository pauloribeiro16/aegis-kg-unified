"""Schema context for the AEGIS Unified Compliance Knowledge Graph.

This knowledge graph integrates two frameworks via the SubDomain bridge:

1. AEGIS REGULATORY (5 EU regulations)
   - Regulation → Clause → SubDomain

2. NIST CSF 2.0 (US framework)
   - Framework → FrameworkCategory (Function + Category) → FrameworkControl → SubDomain

Both sides converge on SubDomain nodes.
"""

SCHEMA_DESCRIPTION = """
You are a Neo4j Cypher expert for the AEGIS Unified Compliance Knowledge Graph.

## TWO-SIDED MODEL

The KG has two distinct but connected sides, bridged by SubDomain nodes:

### SIDE A — AEGIS REGULATORY (EU Regulations)

1. Regulation(regulationId, label, description, euReference, clauseCount)
   - 5 nodes: GDPR, CRA, NIS2, DORA, AIAct

2. Article(articleId, number, title, chapter, summary, obligationType)
   - 47 nodes total

3. Clause(clauseId, description, normativeIntensity, regulationId, obligationType, obligatedParty, articleReference, clauseLevel, relevance)
   - 150 nodes total
   - normativeIntensity: 1=MAY, 2=SHOULD, 3=SHALL

4. Domain(domainId, name, description)
   - 10 nodes: D-01 through D-10

5. SubDomain(subDomainId, name, description, soleAuthority, gapRisk)
   - 38 nodes: D-01-1 through D-10-3
   - Format: D-XX-Y (domain number - subdomain number)

6. ComplementarityAnalysis(analysisId, regulation1Id, regulation2Id, overlapType, jaccardIndex, overlapDescription)

### SIDE B — NIST CSF 2.0 (US Framework)

1. Framework(frameworkId, name, version, publisher, url, description)
   - 1 node: NIST_CSF_2_0

2. FrameworkCategory(categoryId, frameworkId, name, type, functionCode)
   - 40 nodes total
   - type: 'FUNCTION' (6: GV, ID, PR, DE, RS, RC) or 'CATEGORY' (34 subcategories like GV.OC, PR.DS, DE.CM)
   - functionCode: for CATEGORY nodes, points to parent Function (GV, ID, etc.)

3. FrameworkControl(controlId, frameworkId, categoryId, functionCode, title, description, implementationExamples, references, crossReferences)
   - 185 nodes: e.g., GV.OC-01, PR.DS-01, DE.CM-01, etc.

### RELATIONSHIPS

Regulatory side:
- (Regulation)-[:HAS_ARTICLE]->(Article)
- (Regulation)-[:HAS_CLAUSE]->(Clause)
- (Article)-[:DEFINES]->(Clause)
- (Domain)-[:HAS_SUBDOMAIN]->(SubDomain)
- (Clause)-[:MAPPED_TO]->(SubDomain)

NIST CSF side:
- (Framework)-[:HAS_CATEGORY]->(FrameworkCategory)  [Function nodes]
- (FrameworkCategory)-[:HAS_CATEGORY]->(FrameworkCategory)  [Function→Category]
- (FrameworkCategory)-[:HAS_CONTROL]->(FrameworkControl)
- (FrameworkControl)-[:MAPS_TO_SUBDOMAIN {confidence: float}]->(SubDomain)

## IDENTITY CONVENTIONS

- SubDomain: "D-01-1" (D-XX-Y format, dash separator)
- Clause: "GDPR-C01", "CRA-C07", "NIS2-C16", "DORA-C09", "AIA-C01"
- Regulation: "GDPR", "CRA", "NIS2", "DORA", "AIAct"
- Article: "GDPR-Art32", "CRA-Art13", "DORA-Art15"
- NIST Control: "GV.OC-01", "PR.DS-01", "DE.CM-01"
- NIST Function: "GV", "ID", "PR", "DE", "RS", "RC"
- NIST Category: "GV.OC", "GV.RM", "PR.DS", "DE.CM" (parent of controls)

## UNIFIED COMPLIANCE QUERIES

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

// Cross-framework analysis: GDPR clauses vs NIST controls for same subdomain
MATCH (c:Clause {regulationId: 'GDPR'})-[:MAPPED_TO]->(sd:SubDomain)<-[:MAPS_TO_SUBDOMAIN]-(fc:FrameworkControl)
RETURN sd.name, count(c) AS gdprClauses, count(DISTINCT fc) AS nistControls
ORDER BY gdprClauses DESC

// Regulatory coverage by domain
MATCH (d:Domain)-[:HAS_SUBDOMAIN]->(sd:SubDomain)<-[:MAPPED_TO]-(c:Clause)
RETURN d.name AS domain, count(DISTINCT c) AS clauseCount
ORDER BY clauseCount DESC

// NIST coverage by function
MATCH (fc:FrameworkCategory {type: 'FUNCTION'})<-[:HAS_CATEGORY*2]-(f:Framework)-[:HAS_CATEGORY]->(fc)
OPTIONAL MATCH (fc)<-[:HAS_CATEGORY]-(cat)<-[:HAS_CONTROL]-(ctrl:FrameworkControl)
RETURN fc.name AS function, count(DISTINCT ctrl) AS controlCount
ORDER BY controlCount DESC
"""

EXAMPLES = [
    {
        "question": "Which subdomains have both GDPR clauses and NIST controls?",
        "cypher": "MATCH (c:Clause {regulationId: 'GDPR'})-[:MAPPED_TO]->(sd:SubDomain)<-[:MAPS_TO_SUBDOMAIN]-(fc:FrameworkControl) RETURN sd.name, count(c) AS gdprClauses, count(DISTINCT fc) AS nistControls ORDER BY gdprClauses DESC"
    },
    {
        "question": "List NIST controls for the Detect function",
        "cypher": "MATCH (fc:FrameworkControl) WHERE fc.functionCode = 'DE' RETURN fc.controlId, fc.description ORDER BY fc.controlId"
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
    }
]


def get_schema_context() -> str:
    return SCHEMA_DESCRIPTION


def get_example_queries() -> list[dict]:
    return EXAMPLES