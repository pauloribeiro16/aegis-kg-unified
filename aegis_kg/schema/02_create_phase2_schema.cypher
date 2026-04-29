// ============================================================
// AEGIS Phase 2 Knowledge Graph - Schema Extension
// Extends Phase 1 schema with Obligations, Tensions, Goals, and Rules
// ============================================================

// ============================================================
// 1. CREATE CONSTRAINTS
// ============================================================

CREATE CONSTRAINT obligation_id_unique IF NOT EXISTS FOR (o:Obligation) REQUIRE o.obligationId IS UNIQUE;

CREATE CONSTRAINT goal_id_unique IF NOT EXISTS FOR (g:Goal) REQUIRE g.goalId IS UNIQUE;

CREATE CONSTRAINT tension_id_unique IF NOT EXISTS FOR (t:StrategicTension) REQUIRE t.tensionId IS UNIQUE;

CREATE CONSTRAINT rule_id_unique IF NOT EXISTS FOR (r:Rule) REQUIRE r.ruleId IS UNIQUE;

CREATE CONSTRAINT resolution_id_unique IF NOT EXISTS FOR (cr:ConflictResolution) REQUIRE cr.resolutionId IS UNIQUE;

// ============================================================
// 2. CREATE INDEXES (for query optimization)
// ============================================================

CREATE INDEX obligation_subdomain IF NOT EXISTS FOR (o:Obligation) ON (o.targetSubDomain);

CREATE INDEX obligation_type IF NOT EXISTS FOR (o:Obligation) ON (o.obligationType);

CREATE INDEX goal_category IF NOT EXISTS FOR (g:Goal) ON (g.category);

CREATE INDEX goal_priority IF NOT EXISTS FOR (g:Goal) ON (g.priority);

CREATE INDEX goal_risk_profile IF NOT EXISTS FOR (g:Goal) ON (g.riskProfile);

CREATE INDEX tension_severity IF NOT EXISTS FOR (t:StrategicTension) ON (t.severity);

CREATE INDEX tension_type IF NOT EXISTS FOR (t:StrategicTension) ON (t.tensionType);

CREATE INDEX rule_category IF NOT EXISTS FOR (r:Rule) ON (r.category);

CREATE INDEX rule_subdomain IF NOT EXISTS FOR (r:Rule) ON (r.targetSubDomain);

// ============================================================
// 3. SCHEMA DOCUMENTATION
// ============================================================

// Phase 2 Node Types:
// 
// 1. Obligation
//    - obligationId: string (e.g., "OBL-D-01.1-001")
//    - description: string
//    - targetSubDomain: string (e.g., "D-01.1")
//    - obligationType: string (CONTINUOUS, PERIODIC, TRIGGERED, ONE_TIME)
//    - normativeIntensity: float (1.0-3.0)
//    - obligatedParty: string (CONTROLLER, PROCESSOR, MANUFACTURER, etc.)
//    - derivationDate: string
//    - sourceObligationType: string (REGULATORY, BEST_PRACTICE)
//
// 2. Goal (abstract)
//    - goalId: string (e.g., "PG-D-01.1-001" or "SG-D-01.1-001")
//    - description: string
//    - category: string (PRIVACY, SECURITY)
//    - targetSubDomain: string
//    - riskProfile: string (LOW, MODERATE, HIGH, CRITICAL)
//    - priority: string (LOW, MODERATE, HIGH, CRITICAL)
//    - goalStatement: string
//    - regulatorySource: string
//    - technicalImplication: string
//
// 3. StrategicTension
//    - tensionId: string (e.g., "TEN-001")
//    - tensionType: string (TEMPORAL_CONFLICT, REQUIREMENT_CONFLICT, etc.)
//    - severity: string (LOW, MEDIUM, HIGH, CRITICAL)
//    - description: string
//    - resolutionStrategy: string
//    - normativeIntensityDelta: float
//
// 4. Rule (abstract)
//    - ruleId: string (e.g., "CR-001" or "BP-001")
//    - description: string
//    - category: string (COMPLIANCE, BEST_PRACTICE)
//    - targetSubDomain: string
//    - normativeIntensity: float
//    - sourceType: string (REGULATORY, BEST_PRACTICE, HYBRID)
//    - regulatoryReference: string
//    - isMandatory: boolean
//    - frameworkReference: string
//    - confidenceLevel: string
//
// 5. ConflictResolution
//    - resolutionId: string (e.g., "RES-001")
//    - tensionId: string (reference to StrategicTension)
//    - resolutionType: string (HARMONIZATION, PRIORITIZATION, DOCUMENTATION)
//    - justification: string
//    - resolvedDate: string
//    - status: string (RESOLVED, PENDING, ACCEPTED_RISK)
//
// ============================================================
// 4. RELATIONSHIP TYPES (Phase 2)
// ============================================================

// Phase 2 Relationships:
//
// From Phase 1 entities:
// (Clause)-[:DERIVES]->(Obligation)
//
// Core Phase 2 relationships:
// (Obligation)-[:DERIVES_FROM]->(Clause)
// (Obligation)-[:TARGETS_SUBDOMAIN]->(SubDomain)
// (Obligation)-[:FORMALIZES]->(Goal)
// (Obligation)-[:ORIGINATES_TENSION]->(StrategicTension)
//
// Goal relationships:
// (Goal)-[:BELONGS_TO_DOMAIN]->(Domain)
// (Goal)-[:BELONGS_TO_SUBDOMAIN]->(SubDomain)
//
// Tension relationships:
// (StrategicTension)-[:INVOLVES_OBLIGATION]->(Obligation)
// (StrategicTension)-[:ASSIGNED_TO]->(RiskOwner)
// (StrategicTension)-[:REQUIRES]->(ConflictResolution)
//
// Rule relationships:
// (Rule)-[:DERIVED_FROM]->(Clause)
// (Rule)-[:DERIVED_FROM_OBLIGATION]->(Obligation)
// (Rule)-[:SATISFIES_GOAL]->(Goal)
// (Rule)-[:TARGETS_SUBDOMAIN]->(SubDomain)
//
// Resolution relationships:
// (ConflictResolution)-[:RESOLVES]->(StrategicTension)
// (ConflictResolution)-[:GENERATES]->(Rule)
//
// ============================================================

RETURN '✓ Phase 2 Schema extension created' AS status,
       '5 node types, 15 relationship types, 10 constraints/indexes' AS summary;
