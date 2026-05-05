"""Schema exploration tool for LangChain agent."""

from langchain_core.tools import tool


SCHEMA_DESCRIPTION = """
You are a Neo4j Cypher expert for the AEGIS Unified Compliance Knowledge Graph.

## TWO-SIDED MODEL

The KG has two distinct but connected sides, bridged by SubDomain nodes:

### SIDE A — AEGIS REGULATORY (EU Regulations)

1. Regulation(regulationId, label, description, euReference, clauseCount, effectiveCoverageScore, effectiveCoverageTier)
   - 5 nodes: GDPR, CRA, NIS2, DORA, AIAct
   - effectiveCoverageScore: float — sum of all clause NI values (higher = more regulatory pressure)
   - effectiveCoverageTier: string — 'HIGH' (>=50), 'MEDIUM' (>=25), 'LOW' (<25)

2. Article(articleId, number, title, chapter, summary, obligationType)
   - 47 nodes total

3. Clause(clauseId, description, normativeIntensity, regulationId, obligationType, obligatedParty, articleReference, clauseLevel, relevance)
   - 150 nodes total
   - normativeIntensity: 1=MAY, 2=SHOULD, 3=SHALL

4. Domain(domainId, name, description)
   - 10 nodes: D-01 through D-10

5. SubDomain(subDomainId, name, description, soleAuthority, gapRisk, clauseCount, regulationCount, densityScore, avgNormativeIntensity, weightedDensity, coveringRegulations, effectiveCoverage, effectiveCoverageTier)
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

6. ComplementarityAnalysis(analysisId, regulation1Id, regulation2Id, overlapType, jaccardIndex, dynamicJaccard, dynamicSharedSubDomainCount, jaccardSource)
   - 10 nodes: all regulation pairs (5 choose 2)
   - dynamicJaccard: float — recomputed from clause mappings (may differ from jaccardIndex)
   - dynamicSharedSubDomainCount: integer — actual shared SubDomain count
   - jaccardSource: 'DYNAMIC' or 'STATIC'

### SIDE B — NIST CSF 2.0 (US Framework)

1. Framework(frameworkId, name, version, publisher, url, description)
   - 1 node: NIST_CSF_2_0

2. FrameworkCategory(categoryId, frameworkId, name, type, functionCode)
   - 40 nodes total
   - type: 'FUNCTION' (6: GV, ID, PR, DE, RS, RC) or 'CATEGORY' (34 subcategories like GV.OC, PR.DS, DE.CM)
   - functionCode: for CATEGORY nodes, points to parent Function (GV, ID, etc.)

3. FrameworkControl(controlId, frameworkId, categoryId, functionCode, title, description, implementationExamples, references, crossReferences)
   - 106 nodes: e.g., GV.OC-01, PR.DS-01, DE.CM-01, etc.

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
- (Regulation)-[:HAS_APPLICABILITY]->(ApplicabilityCondition)

NIST CSF side:
- (Framework)-[:HAS_CATEGORY]->(FrameworkCategory)  [Function nodes]
- (FrameworkCategory)-[:HAS_CATEGORY]->(FrameworkCategory)  [Function→Category hierarchy]
- (FrameworkControl)-[:HAS_CONTROL]->(FrameworkCategory)  [rare to traverse]
- (FrameworkControl)-[:MAPS_TO_SUBDOMAIN]->(SubDomain)
- (FrameworkControl)-[:MAPS_TO_DOMAIN]->(Domain)

## IDENTITY CONVENTIONS

- SubDomain: "D-01.1" (D-XX.Y format, DOT separator)
- Clause: "GDPR-C01", "CRA-C07", "NIS2-C16", "DORA-C09", "AIA-C01"
- Regulation: "GDPR", "CRA", "NIS2", "DORA", "AIAct"
- Article: "GDPR-Art32", "CRA-Art13", "DORA-Art15"
- NIST Control: "GV.OC-01", "PR.DS-01", "DE.CM-01"
- NIST Function: "GV", "ID", "PR", "DE", "RS", "RC"
- NIST Category: "GV.OC", "GV.RM", "PR.DS", "DE.CM" (parent of controls)

## USEFUL QUERIES

// SubDomain shared by both sides (regulatory + NIST)
MATCH (c:Clause)-[:MAPPED_TO]->(sd:SubDomain)<-[:MAPS_TO_SUBDOMAIN]-(fc:FrameworkControl)
RETURN sd.name AS subdomain, collect(c.clauseId)[0..3] AS clauses, collect(fc.controlId)[0..3] AS nist_controls

// Gap analysis: subdomains with no NIST coverage
MATCH (sd:SubDomain)
WHERE NOT EXISTS((:FrameworkControl)-[:MAPS_TO_SUBDOMAIN]->(sd))
RETURN sd.subDomainId, sd.name, sd.gapRisk

// NIST controls covering encryption subdomains
MATCH (fc:FrameworkControl)-[:MAPS_TO_SUBDOMAIN]->(sd:SubDomain)
WHERE sd.subDomainId STARTS WITH 'D-01'
RETURN fc.controlId, sd.name, sd.subDomainId

// Cross-framework analysis: GDPR clauses vs NIST controls for same subdomain
MATCH (c:Clause {regulationId: 'GDPR'})-[:MAPPED_TO]->(sd:SubDomain)<-[:MAPS_TO_SUBDOMAIN]-(fc:FrameworkControl)
RETURN sd.name, count(c) AS gdprClauses, count(DISTINCT fc) AS nistControls
ORDER BY gdprClauses DESC

// Regulatory coverage by domain (HAS_SUBDOMAIN, not CONTAINS)
MATCH (d:Domain)-[:HAS_SUBDOMAIN]->(sd:SubDomain)<-[:MAPPED_TO]-(c:Clause)
RETURN d.name AS domain, count(DISTINCT c) AS clauseCount
ORDER BY clauseCount DESC

// Effective coverage ranking (Batch 10)
MATCH (sd:SubDomain) WHERE sd.effectiveCoverage IS NOT NULL
RETURN sd.subDomainId, sd.name, sd.effectiveCoverage, sd.effectiveCoverageTier, sd.clauseCount
ORDER BY sd.effectiveCoverage DESC LIMIT 10

// Subdomains by effective coverage tier
MATCH (sd:SubDomain) RETURN sd.effectiveCoverageTier AS tier, count(*) AS count ORDER BY tier

// Regulations by effective coverage score
MATCH (r:Regulation) WHERE r.effectiveCoverageScore IS NOT NULL
RETURN r.regulationId, r.name, r.effectiveCoverageScore, r.effectiveCoverageTier
ORDER BY r.effectiveCoverageScore DESC

// Heatmap: clause count per SubDomain per Regulation (Batch 11)
MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)-[:MAPPED_TO]->(sd:SubDomain)
RETURN sd.subDomainId, sd.name AS subdomain, r.regulationId AS regulation,
       count(c) AS clauseCount, sum(c.normativeIntensity) AS totalNI, avg(c.normativeIntensity) AS avgNI
ORDER BY sd.subDomainId, r.regulationId

// Heatmap: which regulations cover each subdomain
MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)-[:MAPPED_TO]->(sd:SubDomain)
WITH sd.subDomainId AS sdId, sd.name AS sdName, collect(r.regulationId) AS regs, count(DISTINCT c) AS totalClauses
RETURN sdId, sdName, regs, totalClauses
ORDER BY totalClauses DESC
"""


@tool
def schema_explorer(operation: str) -> str:
    """Explore the AEGIS knowledge graph schema to understand node types and relationships.

    Use this tool to get information about:
    - Node labels and their properties
    - Relationship types between nodes
    - ID formats and conventions
    - Example queries for common patterns

    Args:
        operation: What schema information to retrieve. Options:
          - "full": Returns the complete schema description
          - "nodes": Returns just the node labels and properties
          - "relationships": Returns just the relationship types
          - "nist": Returns NIST CSF 2.0 specific schema
          - "regulatory": Returns AEGIS regulatory side schema
          - "identities": Returns ID format conventions

    Returns:
        A string containing the requested schema information
    """
    operation = operation.lower().strip()

    if operation == "full":
        return SCHEMA_DESCRIPTION
    elif operation == "nodes":
        return """NODE LABELS AND PROPERTIES:

AEGIS REGULATORY:
- Regulation(regulationId, label, description, euReference, clauseCount)
- Article(articleId, number, title, chapter, summary, obligationType)
- Clause(clauseId, description, normativeIntensity, regulationId, obligationType, obligatedParty, articleReference, clauseLevel, relevance)
- Domain(domainId, name, description)
- SubDomain(subDomainId, name, description, soleAuthority, gapRisk)
- ComplementarityAnalysis(analysisId, regulation1Id, regulation2Id, overlapType, jaccardIndex, overlapDescription)

NIST CSF 2.0:
- Framework(frameworkId, name, version, publisher, url, description)
- FrameworkCategory(categoryId, frameworkId, name, type, functionCode)
- FrameworkControl(controlId, frameworkId, categoryId, functionCode, title, description, implementationExamples, references, crossReferences)
"""
    elif operation == "relationships":
        return """RELATIONSHIP TYPES:

REGULATORY SIDE:
- (Regulation)-[:HAS_ARTICLE]->(Article)
- (Regulation)-[:HAS_CLAUSE]->(Clause)
- (Article)-[:DEFINES]->(Clause)
- (Domain)-[:CONTAINS]->(SubDomain)
- (Clause)-[:MAPPED_TO]->(SubDomain)

NIST CSF SIDE:
- (Framework)-[:HAS_CATEGORY]->(FrameworkCategory)  [Function nodes]
- (FrameworkCategory)-[:HAS_CATEGORY]->(FrameworkCategory)  [Function→Category]
- (FrameworkCategory)-[:HAS_CONTROL]->(FrameworkControl)
- (FrameworkControl)-[:MAPS_TO_SUBDOMAIN]->(SubDomain)
- (FrameworkControl)-[:MAPS_TO_DOMAIN]->(Domain)
"""
    elif operation == "nist":
        return """NIST CSF 2.0 SCHEMA:

Nodes:
- Framework: NIST_CSF_2_0 (version 2.0)
- FrameworkCategory (FUNCTION): GV, ID, PR, DE, RS, RC
- FrameworkCategory (CATEGORY): GV.OC, GV.RM, PR.DS, DE.CM, etc.
- FrameworkControl: 106 subcategories like GV.OC-01, PR.DS-01

Properties on FrameworkControl:
- controlId: "GV.OC-01" format
- categoryId: "GV.OC" format
- functionCode: "GV", "PR", etc.
- title: short title
- description: full description
- implementationExamples: array of examples
- crossReferences: array of references to other frameworks

Relationships:
- (Framework)-[:HAS_CATEGORY]->(FrameworkCategory [FUNCTION])
- (FrameworkCategory [FUNCTION])-[:HAS_CATEGORY]->(FrameworkCategory [CATEGORY])
- (FrameworkCategory [CATEGORY])-[:HAS_CONTROL]->(FrameworkControl)
- (FrameworkControl)-[:MAPS_TO_SUBDOMAIN]->(SubDomain)
"""
    elif operation == "regulatory":
        return """AEGIS REGULATORY SCHEMA:

Nodes:
- Regulation: GDPR, CRA, NIS2, DORA, AIAct
- Article: links to clauses
- Clause: 150 total with normativeIntensity (1=MAY, 2=SHOULD, 3=SHALL)
- Domain: D-01 through D-10
- SubDomain: D-01.1 through D-10.3 (38 total)

Relationships:
- (Regulation)-[:HAS_ARTICLE]->(Article)
- (Regulation)-[:HAS_CLAUSE]->(Clause)
- (Article)-[:DEFINES]->(Clause)
- (Domain)-[:CONTAINS]->(SubDomain)
- (Clause)-[:MAPPED_TO]->(SubDomain)
"""
    elif operation == "identities":
        return """IDENTITY CONVENTIONS:

SubDomain: "D-01.1" (D-XX.Y format, DOT separator)
Clause: "GDPR-C01", "CRA-C07", "NIS2-C16", "DORA-C09", "AIA-C01"
Regulation: "GDPR", "CRA", "NIS2", "DORA", "AIAct"
Article: "GDPR-Art32", "CRA-Art13", "DORA-Art15"
NIST Control: "GV.OC-01", "PR.DS-01", "DE.CM-01"
NIST Function: "GV", "ID", "PR", "DE", "RS", "RC"
NIST Category: "GV.OC", "GV.RM", "PR.DS", "DE.CM"
"""
    else:
        return f"Unknown operation: {operation}. Use: full, nodes, relationships, nist, regulatory, or identities."


def get_schema_tool():
    """Get the configured schema explorer tool for LangChain agent."""
    return schema_explorer
