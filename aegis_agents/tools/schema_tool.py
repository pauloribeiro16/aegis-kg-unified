"""Schema exploration tool for LangChain agent."""

from langchain_core.tools import tool


SCHEMA_DESCRIPTION = """
You are a Neo4j Cypher expert for the AEGIS Unified Compliance Knowledge Graph.

## TWO-SIDED MODEL

The KG has two distinct but connected sides, bridged by SubDomain nodes:

### SIDE A — AEGIS REGULATORY (EU Regulations)

1. Regulation(regulationId, label, description, euReference, clauseCount, effectiveCoverageScore, effectiveCoverageTier, complianceDeadline, enforcementDate, applicationDate, urgencyTier, daysToCompliance, daysToEnforcement, obligationProfile, dominantObligationType, continuousObligationRatio, urgencyIndex)
   - 5 nodes: GDPR, CRA, NIS2, DORA, AIAct
   - effectiveCoverageScore: float — sum of all clause NI values (higher = more regulatory pressure)
   - effectiveCoverageTier: string — 'HIGH' (>=50), 'MEDIUM' (>=25), 'LOW' (<25)
   - Temporal applicability:     - complianceDeadline: date — deadline for organizations to comply
     - enforcementDate: date — date penalties/sanctions begin
     - applicationDate: date — date the regulation starts applying to organizations
     - urgencyTier: string — 'PAST_DUE', 'CRITICAL' (<=90 days), 'URGENT' (<=365 days), 'ON_TRACK' (>365 days)
     - daysToCompliance: integer — days until compliance deadline (negative = past due)
     - daysToEnforcement: integer — days until enforcement date (negative = enforcement active)
   - Obligation type analysis:     - obligationProfile: JSON string — e.g. '{"CONTINUOUS":18,"ONE_TIME":1,"PERIODIC":6,"TRIGGERED":4}'
     - dominantObligationType: most frequent obligation type (CONTINUOUS, ONE_TIME, PERIODIC, TRIGGERED)
     - continuousObligationRatio: CONTINUOUS clauses / total clauses
     - urgencyIndex: float [0..1] — weighted composite: (continuous*1.0 + triggered*0.7 + periodic*0.5 + oneTime*0.3) / total

 2. RegulatoryTimeline(timelineId, eventType, eventDate, description, regulationId)
   - Key milestone events per regulation (e.g., ENTRY_INTO_FORCE, APPLICATION, ENFORCEMENT)
   - Relationship: (Regulation)-[:HAS_TIMELINE_EVENT]->(RegulatoryTimeline)

 2b. RegulatoryAuthority(authorityId, authorityName, authorityType, soleAuthorityCount, totalEffectiveCoverage, avgObligationUrgency, avgContinuousRatio, authorityInfluenceScore, primaryRegulationId)
   - 5 nodes: ENISA, DPAs, NCAs_ENISA, EU_AI_OFFICE, ESAs
   - authorityType: EU_AGENCY | NATIONAL_DPA | NATIONAL_COORDINATION | EU_OFFICE | ESA_BODY
   - authorityInfluenceScore: composite = soleAuthorityCount*5 + totalEC*0.3 + avgUrgency*count*2 + totalHotspotScore*1
   - Relationship: (SubDomain)-[:UNDER_REGULATORY_AUTHORITY]->(RegulatoryAuthority)

 3. Article(articleId, number, title, chapter, summary, obligationType)
   - 47 nodes total

 4. Clause(clauseId, description, normativeIntensity, regulationId, obligationType, obligatedParty, articleReference, clauseLevel, relevance)
   - 150 nodes total
   - normativeIntensity: 1=MAY, 2=SHOULD, 3=SHALL

 5. Domain(domainId, name, description)
   - 10 nodes: D-01 through D-10

 6. SubDomain(subDomainId, name, description, soleAuthority, authorityId, gapRisk, clauseCount, regulationCount, densityScore, avgNormativeIntensity, weightedDensity, coveringRegulations, effectiveCoverage, effectiveCoverageTier, hotspotScore, hotspotTier, gapDensityScore, gapDensityTier, clauseDistribution, missingRegulations, dominantObligationType, continuousObligationRatio, obligationUrgencyIndex)
   - 38 nodes: D-01.1 through D-10.3
   - Format: D-XX.Y (DOT separator, e.g., D-01.1, D-02.3, D-10.2)
   - Computed from graph:     - clauseCount: integer — count of clauses mapped via MAPPED_TO
     - regulationCount: integer — count of distinct regulations covering this subdomain
     - densityScore: float — clauseCount / 5.0 (normalized by max 5 regulations)
     - avgNormativeIntensity: float — average NI of covering clauses (range 0-3.0)
     - weightedDensity: float — sum(NI) / 15.0 (NI-weighted, max 1.0)
     - coveringRegulations: list[string] — regulation IDs covering this subdomain
   - NI-weighted coverage:     - effectiveCoverage: float — sum of NI values of all clauses mapped to this SubDomain (higher = stronger regulatory pressure)
     - effectiveCoverageTier: string — 'HIGH' (>=8.0), 'MEDIUM' (>=4.0), 'LOW' (<4.0)
   - Multi-regulation hotspots:     - hotspotScore: integer — number of regulations covering this SubDomain (same as regulationCount)
     - hotspotTier: string — 'CRITICAL' (>=5 regs), 'HIGH' (>=4), 'MODERATE' (>=3), 'LOW' (<3)
   - Gap density:     - gapDensityScore: float [0..1] — balance of clause distribution across regulations (1=perfectly balanced, 0=highly unbalanced); based on coefficient of variation of clause counts per regulation
     - gapDensityTier: string — 'DENSE' (>=0.5), 'MODERATE' (>=0.2), 'SPARSE' (<0.2)
     - clauseDistribution: JSON string — e.g. '{"GDPR":2,"CRA":1,"NIS2":1,"DORA":1,"AIAct":0}'
     - missingRegulations: list[string] — regulation IDs NOT covering this SubDomain (gaps)
   - Obligation type analysis:     - dominantObligationType: most frequent obligation type of clauses mapped to this SubDomain
     - continuousObligationRatio: CONTINUOUS clauses / total mapped clauses
     - obligationUrgencyIndex: float [0..1] — same formula as Regulation.urgencyIndex applied to SubDomain clauses
   - Authority concentration:     - authorityId: string — ID of the sole regulatory authority for this SubDomain (e.g., 'ENISA', 'DPAs')

7. ComplementarityAnalysis(analysisId, regulation1Id, regulation2Id, overlapType, jaccardIndex, dynamicJaccard, dynamicSharedSubDomainCount, jaccardSource)
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
- (Regulation)-[:HAS_TIMELINE_EVENT]->(RegulatoryTimeline)

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

// Effective coverage ranking
MATCH (sd:SubDomain) WHERE sd.effectiveCoverage IS NOT NULL
RETURN sd.subDomainId, sd.name, sd.effectiveCoverage, sd.effectiveCoverageTier, sd.clauseCount
ORDER BY sd.effectiveCoverage DESC LIMIT 10

// Subdomains by effective coverage tier
MATCH (sd:SubDomain) RETURN sd.effectiveCoverageTier AS tier, count(*) AS count ORDER BY tier

// Regulations by effective coverage score
MATCH (r:Regulation) WHERE r.effectiveCoverageScore IS NOT NULL
RETURN r.regulationId, r.name, r.effectiveCoverageScore, r.effectiveCoverageTier
ORDER BY r.effectiveCoverageScore DESC

// Heatmap: clause count per SubDomain per Regulation
MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)-[:MAPPED_TO]->(sd:SubDomain)
RETURN sd.subDomainId, sd.name AS subdomain, r.regulationId AS regulation,
       count(c) AS clauseCount, sum(c.normativeIntensity) AS totalNI, avg(c.normativeIntensity) AS avgNI
ORDER BY sd.subDomainId, r.regulationId

// Heatmap: which regulations cover each subdomain
MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)-[:MAPPED_TO]->(sd:SubDomain)
WITH sd.subDomainId AS sdId, sd.name AS sdName, collect(r.regulationId) AS regs, count(DISTINCT c) AS totalClauses
RETURN sdId, sdName, regs, totalClauses
ORDER BY totalClauses DESC

// Multi-Regulation Hotspots
MATCH (sd:SubDomain) WHERE sd.hotspotTier IN ['CRITICAL', 'HIGH', 'MODERATE']
RETURN sd.subDomainId, sd.name, sd.hotspotScore, sd.hotspotTier, sd.regulationCount, sd.coveringRegulations
ORDER BY sd.hotspotScore DESC

// Subdomains by hotspot tier
MATCH (sd:SubDomain) RETURN sd.hotspotTier AS tier, count(*) AS count ORDER BY tier

// Strategic Tensions
MATCH (st:StrategicTension)-[:INVOLVES_REGULATION]->(r:Regulation)
WITH st, collect(r.regulationId) AS regs, st.conflictType AS conflictType, st.severity AS severity
RETURN st.tensionId AS tensionId, regs, conflictType, severity, st.description AS description
ORDER BY severity DESC

MATCH (st:StrategicTension)-[:AFFECTS_SUBDOMAIN]->(sd:SubDomain)
RETURN st.tensionId AS tensionId, st.conflictType AS conflictType, st.severity AS severity,
       sd.subDomainId AS subDomainId, sd.name AS subDomainName, st.description AS description
ORDER BY sd.subDomainId

// Conflict Severity
MATCH (ca:ComplementarityAnalysis)
WHERE ca.conflictSeverityScore IS NOT NULL
RETURN ca.analysisId AS analysisId, ca.regulation1Id AS reg1, ca.regulation2Id AS reg2,
       ca.conflictSeverityScore AS severityScore, ca.severityComponents AS components
ORDER BY severityScore DESC

// Gap Density
MATCH (sd:SubDomain)
WHERE sd.gapDensityScore IS NOT NULL
RETURN sd.subDomainId, sd.name, sd.gapDensityScore, sd.gapDensityTier,
       sd.clauseDistribution, sd.missingRegulations
ORDER BY sd.gapDensityScore DESC

// Gap density tier distribution
MATCH (sd:SubDomain)
RETURN sd.gapDensityTier AS tier, count(*) AS count ORDER BY tier

// Most DENSE subdomains (balanced clause distribution)
MATCH (sd:SubDomain) WHERE sd.gapDensityTier = 'DENSE'
RETURN sd.subDomainId, sd.name, sd.gapDensityScore, sd.clauseDistribution
ORDER BY sd.gapDensityScore DESC

// Most SPARSE subdomains (unbalanced, high gaps)
MATCH (sd:SubDomain) WHERE sd.gapDensityTier = 'SPARSE'
RETURN sd.subDomainId, sd.name, sd.gapDensityScore, sd.missingRegulations, sd.coveringRegulations
ORDER BY sd.gapDensityScore ASC, sd.regulationCount DESC

// Temporal Applicability
MATCH (r:Regulation)
RETURN r.regulationId, r.name, r.effectiveDate, r.applicationDate,
       r.complianceDeadline, r.enforcementDate, r.urgencyTier,
       r.daysToCompliance, r.daysToEnforcement
ORDER BY r.daysToCompliance ASC

MATCH (r:Regulation)-[:HAS_TIMELINE_EVENT]->(t:RegulatoryTimeline)
RETURN r.regulationId, t.eventType, t.eventDate, t.description
ORDER BY r.regulationId, t.eventDate

MATCH (r:Regulation)-[:HAS_TIMELINE_EVENT]->(t:RegulatoryTimeline)
WHERE r.regulationId = 'AIAct'
RETURN t.eventType, t.eventDate, t.description
ORDER BY t.eventDate

// Obligation Type Analysis
MATCH (r:Regulation)
RETURN r.regulationId, r.name, r.obligationProfile, r.dominantObligationType,
       r.continuousObligationRatio, r.urgencyIndex
ORDER BY r.urgencyIndex DESC

MATCH (sd:SubDomain)
WHERE sd.dominantObligationType IS NOT NULL
RETURN sd.subDomainId, sd.name, sd.dominantObligationType, sd.continuousObligationRatio, sd.obligationUrgencyIndex
ORDER BY sd.obligationUrgencyIndex DESC

MATCH (sd:SubDomain) WHERE sd.dominantObligationType = 'CONTINUOUS'
RETURN sd.subDomainId, sd.name, sd.obligationUrgencyIndex, sd.continuousObligationRatio
ORDER BY sd.continuousObligationRatio DESC

// Authority Concentration
MATCH (auth:RegulatoryAuthority)
RETURN auth.authorityId, auth.authorityName, auth.authorityType,
       auth.soleAuthorityCount, auth.authorityInfluenceScore
ORDER BY auth.authorityInfluenceScore DESC

MATCH (auth:RegulatoryAuthority)-[:UNDER_REGULATORY_AUTHORITY]->(sd:SubDomain)
WHERE auth.authorityId = 'ENISA'
RETURN sd.subDomainId, sd.name, sd.effectiveCoverage, sd.obligationUrgencyIndex
ORDER BY sd.effectiveCoverage DESC
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
