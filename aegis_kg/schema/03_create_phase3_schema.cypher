// ============================================================
// AEGIS Phase 3 Knowledge Graph - Schema Extension
// Extends Phase 1+2 schema with Use Cases, Functional Requirements,
// NFRs, FRs, Threats, Risks, Mitigations, and Compliance Gates
// ============================================================

// ============================================================
// 1. CREATE CONSTRAINTS
// ============================================================

CREATE CONSTRAINT usecase_id_unique IF NOT EXISTS FOR (uc:UseCase) REQUIRE uc.useCaseId IS UNIQUE;

CREATE CONSTRAINT functionalnode_id_unique IF NOT EXISTS FOR (fn:FunctionalNode) REQUIRE fn.nodeId IS UNIQUE;

CREATE CONSTRAINT nfr_id_unique IF NOT EXISTS FOR (n:NFR) REQUIRE n.nfrId IS UNIQUE;

CREATE CONSTRAINT fr_id_unique IF NOT EXISTS FOR (f:FR) REQUIRE f.frId IS UNIQUE;

CREATE CONSTRAINT threat_id_unique IF NOT EXISTS FOR (t:Threat) REQUIRE t.threatId IS UNIQUE;

CREATE CONSTRAINT vulnerability_id_unique IF NOT EXISTS FOR (v:Vulnerability) REQUIRE v.vulnerabilityId IS UNIQUE;

CREATE CONSTRAINT risk_id_unique IF NOT EXISTS FOR (r:Risk) REQUIRE r.riskId IS UNIQUE;

CREATE CONSTRAINT mitigation_id_unique IF NOT EXISTS FOR (m:Mitigation) REQUIRE m.mitigationId IS UNIQUE;

CREATE CONSTRAINT compliancegate_id_unique IF NOT EXISTS FOR (g:ComplianceGate) REQUIRE g.gateId IS UNIQUE;

// ============================================================
// 2. CREATE INDEXES (for query optimization)
// ============================================================

CREATE INDEX usecase_domain IF NOT EXISTS FOR (uc:UseCase) ON (uc.domain);

CREATE INDEX functionalnode_track IF NOT EXISTS FOR (fn:FunctionalNode) ON (fn.track);

CREATE INDEX functionalnode_level IF NOT EXISTS FOR (fn:FunctionalNode) ON (fn.level);

CREATE INDEX nfr_category IF NOT EXISTS FOR (n:NFR) ON (n.category);

CREATE INDEX nfr_priority IF NOT EXISTS FOR (n:NFR) ON (n.priority);

CREATE INDEX fr_domain IF NOT EXISTS FOR (f:FR) ON (f.domain);

CREATE INDEX threat_category IF NOT EXISTS FOR (t:Threat) ON (t.category);

CREATE INDEX risk_likelihood IF NOT EXISTS FOR (r:Risk) ON (r.likelihood);

CREATE INDEX risk_impact IF NOT EXISTS FOR (r:Risk) ON (r.impact);

CREATE INDEX mitigation_strategy IF NOT EXISTS FOR (m:Mitigation) ON (m.strategy);

CREATE INDEX compliancegate_status IF NOT EXISTS FOR (g:ComplianceGate) ON (g.status);

// ============================================================
// 3. SCHEMA DOCUMENTATION
// ============================================================

// Phase 3 Node Types:
//
// 1. UseCase
//    - useCaseId: string (e.g., "UC-D-01-001")
//    - name: string
//    - description: string
//    - domain: string (e.g., "D-01")
//    - level: string (L0_BOUNDARY, L1_PRIMARY, L2_SUBFLOW)
//    - priority: string (HIGH, MODERATE, LOW)
//    - actors: string
//    - preconditions: string
//    - postconditions: string
//
// 2. FunctionalNode
//    - nodeId: string (e.g., "FN-T-001")
//    - name: string
//    - description: string
//    - track: string (TECHNOLOGY, PROCESS, CAPABILITY_SUBREQ)
//    - level: string (L0, L1, L2, L3)
//    - verificationMethod: string
//    - status: string (PLANNED, IMPLEMENTED, VERIFIED)
//
// 3. NFR (Non-Functional Requirement)
//    - nfrId: string (e.g., "NFR-CONF-001")
//    - description: string
//    - category: string (CONFIDENTIALITY, INTEGRITY, AVAILABILITY, PRIVACY, ACCESSIBILITY, COMPLIANCE)
//    - priority: string (CRITICAL, HIGH, MODERATE, LOW)
//    - metric: string
//    - target: string
//    - verificationMethod: string
//    - sourceRegulation: string
//
// 4. FR (Functional Requirement)
//    - frId: string (e.g., "FR-IAM-001")
//    - description: string
//    - domain: string (IAM, DP, SEC, DEV, GOV, TRN)
//    - priority: string (CRITICAL, HIGH, MODERATE, LOW)
//    - verificationMethod: string
//    - sourceObligations: string
//    - sourceNFRs: string
//
// 5. Threat
//    - threatId: string (e.g., "STRIDE-001")
//    - description: string
//    - category: string (SPOOFING, TAMPERING, REPUDIATION, INFO_DISCLOSURE, DoS, ELEVATION_OF_PRIVILEGE, LINKABILITY, IDENTIFIABILITY, NON_REPUDIATION, DETECTABILITY, UNIDENTIFIABILITY, UNLINKABILITY)
//    - framework: string (STRIDE, LINDDUN)
//    - attackVector: string
//    - affectedComponents: string
//
// 6. Vulnerability
//    - vulnerabilityId: string (e.g., "VULN-001")
//    - description: string
//    - affectedComponent: string
//    - severity: string (CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL)
//    - cveReference: string
//
// 7. Risk
//    - riskId: string (e.g., "RISK-001")
//    - description: string
//    - threatId: string
//    - vulnerabilityId: string
//    - likelihood: string (VERY_LIKELY, LIKELY, POSSIBLE, UNLIKELY, RARE)
//    - impact: string (CATASTROPHIC, HIGH, MODERATE, LOW, NEGLIGIBLE)
//    - riskLevel: string (CRITICAL, HIGH, MEDIUM, LOW)
//    - residualRisk: string
//    - decision: string (MITIGATE, ACCEPT, TRANSFER, AVOID)
//    - justification: string
//
// 8. Mitigation
//    - mitigationId: string (e.g., "MIT-001")
//    - description: string
//    - strategy: string (NEW_FUNCTIONAL_NODE, STRENGTHEN_EXISTING, ARCHITECTURAL_CHANGE, PROCESS_CONTROL)
//    - riskId: string
//    - status: string (PLANNED, IMPLEMENTED, VERIFIED)
//    - effectivenessRating: string
//
// 9. ComplianceGate
//    - gateId: string (e.g., "GATE-D-01-001")
//    - description: string
//    - domain: string
//    - evaluationDate: string
//    - status: string (PASS, FAIL, GAP_DETECTED, PENDING)
//    - evidence: string
//    - gapsIdentified: string
//
// ============================================================
// 4. RELATIONSHIP TYPES (Phase 3)
// ============================================================

// Phase 3 Relationships:
//
// Bridge from Phase 2:
// (Obligation)-[:DERIVES_USECASE]->(UseCase)
// (Rule)-[:CONSTRAINS_NODE]->(FunctionalNode)
// (Goal)-[:MOTIVATES_NODE]->(FunctionalNode)
//
// Decomposition relationships:
// (UseCase)-[:DERIVES_NODE]->(FunctionalNode)
// (FunctionalNode)-[:DECOMPOSES_INTO]->(FunctionalNode) [recursive]
// (FunctionalNode)-[:VALIDATED_BY]->(ComplianceGate)
// (ComplianceGate)-[:CHECKS_RULE]->(Rule)
//
// Requirements relationships:
// (UseCase)-[:REALIZED_BY]->(FR)
// (FR)-[:SATISFIES_NFR]->(NFR)
// (FR)-[:ALLOCATED_TO]->(FunctionalNode)
// (NFR)-[:CONSTRAINED_BY]->(Rule)
//
// Risk relationships:
// (FunctionalNode)-[:SUBJECT_TO]->(Threat)
// (Threat)-[:EXPLOITS]->(Vulnerability)
// (Threat)-[:INFORMS_RISK]->(Risk)
// (Vulnerability)-[:TRIGGERS_RISK]->(Risk)
// (Risk)-[:GENERATES_MITIGATION]->(Mitigation)
// (Mitigation)-[:INJECTS_NODE]->(FunctionalNode)
// (Mitigation)-[:ADDRESSES_VULN]->(Vulnerability)
//
// Gate relationships:
// (ComplianceGate)-[:VALIDATES_NODE]->(FunctionalNode)
// (ComplianceGate)-[:VERIFIES_REQUIREMENT]->(FR)
//
// ============================================================

RETURN '✓ Phase 3 Schema extension created' AS status,
       '9 node types, 20+ relationship types, 20 constraints/indexes' AS summary;
