"""Schema exploration tool for LangChain agent."""

from langchain_core.tools import tool


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
   - soleAuthority: String — regulation ID with sole authority ('CRA','GDPR','NIS2','DORA','AIAct'), null if shared governance
   - gapRisk: String — 'HIGH', 'MEDIUM', or 'LOW'

6. ComplementarityAnalysis(analysisId, regulation1Id, regulation2Id, overlapType, jaccardIndex, overlapDescription)

### SIDE B — NIST CSF 2.0 (US Framework)

1. Framework(frameworkId, name, version, publisher, url, description)
   - 1 node: NIST_CSF_2_0

2. FrameworkCategory(categoryId, frameworkId, name, type, functionCode)
   - 40 nodes total
   - type: 'FUNCTION' (6: GV, ID, PR, DE, RS, RC) or 'CATEGORY' (34 subcategories like GV.OC, PR.DS, DE.CM)
   - functionCode: for CATEGORY nodes, points to parent Function (GV, ID, etc.)

3. FrameworkControl(controlId, frameworkId, categoryId, functionCode, title, description, implementationExamples, references, crossReferences)
   - 106 nodes: e.g., GV.OC-01, PR.DS-01, DE.CM-01, etc.

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
- (FrameworkControl)-[:MAPS_TO_SUBDOMAIN]->(SubDomain)
- (FrameworkControl)-[:MAPS_TO_DOMAIN]->(Domain)

## IDENTITY CONVENTIONS

- SubDomain: "D-01-1" (D-XX-Y format, dash separator)
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

// Regulatory coverage by domain
MATCH (d:Domain)-[:HAS_SUBDOMAIN]->(sd:SubDomain)<-[:MAPPED_TO]-(c:Clause)
RETURN d.name AS domain, count(DISTINCT c) AS clauseCount
ORDER BY clauseCount DESC
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
- (Domain)-[:HAS_SUBDOMAIN]->(SubDomain)
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
- SubDomain: D-01-1 through D-10-3 (38 total)

Relationships:
- (Regulation)-[:HAS_ARTICLE]->(Article)
- (Regulation)-[:HAS_CLAUSE]->(Clause)
- (Article)-[:DEFINES]->(Clause)
- (Domain)-[:HAS_SUBDOMAIN]->(SubDomain)
- (Clause)-[:MAPPED_TO]->(SubDomain)
"""
    elif operation == "identities":
        return """IDENTITY CONVENTIONS:

SubDomain: "D-01-1" (D-XX-Y format, dash separator)
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
