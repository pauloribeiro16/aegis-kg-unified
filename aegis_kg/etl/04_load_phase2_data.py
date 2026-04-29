import os
#!/usr/bin/env python3
"""
AEGIS Phase 2 Knowledge Graph - ETL Script
Loads Obligations, Tensions, Goals, and Rules into Neo4j with full traceability.
"""
import requests
import csv
import time
from pathlib import Path

NEO4J_HTTP = "http://localhost:7474"
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", ""))
BASE_DIR = Path(__file__).parent

def exec_cypher(statement, params=None):
    """Execute a Cypher query using parameterized queries"""
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}
    try:
        response = requests.post(
            f"{NEO4J_HTTP}/db/neo4j/tx/commit",
            auth=AUTH,
            json=payload,
            timeout=30
        )
        if response.status_code != 200:
            print(f"  HTTP {response.status_code}: {response.text[:200]}")
            return 0
        result = response.json()
        if result.get('errors'):
            for err in result['errors']:
                print(f"  DB Error: {err.get('message', '')[:200]}")
            return 0
        try:
            data = result.get('results', [{}])[0].get('data', [{}])[0].get('row', [0])
            return data[0] if data else 0
        except (IndexError, TypeError):
            return 0
    except Exception as e:
        print(f"  Exception: {e}")
        return 0

def exec_cypher_return(statement, params=None):
    """Execute a Cypher query and return results"""
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}
    try:
        response = requests.post(
            f"{NEO4J_HTTP}/db/neo4j/tx/commit",
            auth=AUTH,
            json=payload,
            timeout=30
        )
        if response.status_code != 200:
            return []
        result = response.json()
        if result.get('errors'):
            return []
        return result.get('results', [])
    except:
        return []

def load_obligations():
    """Load obligations from hardcoded data"""
    print("\n" + "=" * 60)
    print("  Loading Phase 2 Obligations")
    print("=" * 60)
    
    # Obligations data from TinyTask case
    obligations = [
        ("OBL-D-01.1-001", "Encrypt all personal and sensitive data at rest using industry-standard algorithms", "D-01.1", "CONTINUOUS", 2.667, "CONTROLLER", "2026-04-01", "GDPR-32-1-a,GDPR-32-1-b,CRA-AnnexI-1"),
        ("OBL-D-01.2-001", "Encrypt all data transmitted across networks using TLS 1.3 or equivalent", "D-01.2", "CONTINUOUS", 2.5, "CONTROLLER", "2026-04-01", "GDPR-32-1-b,CRA-AnnexI-2"),
        ("OBL-D-01.3-001", "Implement secure cryptographic key management with authentication and integrity verification", "D-01.3", "CONTINUOUS", 3.0, "MANUFACTURER", "2026-04-01", "CRA-AnnexI-3"),
        ("OBL-D-01.4-001", "Protect data against unauthorised manipulation and accidental loss", "D-01.4", "CONTINUOUS", 3.0, "CONTROLLER", "2026-04-01", "GDPR-32-1-e,CRA-AnnexII-1"),
        ("OBL-D-02.1-001", "Deliver product with no known exploitable vulnerabilities; maintain SBOM", "D-02.1", "ONE_TIME", 3.0, "MANUFACTURER", "2026-04-01", "CRA-AnnexI-1,CRA-AnnexII-2"),
        ("OBL-D-02.2-001", "Enable automatic security updates; remediate vulnerabilities promptly", "D-02.2", "TRIGGERED", 3.0, "MANUFACTURER", "2026-04-01", "CRA-AnnexI-3,CRA-AnnexII-3"),
        ("OBL-D-02.3-001", "Publish coordinated vulnerability disclosure policy; report severe incidents to ENISA/CSIRT", "D-02.3", "CONTINUOUS", 3.0, "MANUFACTURER", "2026-04-01", "CRA-AnnexI-4,CRA-AnnexIII-3"),
        ("OBL-D-03.1-001", "Implement authentication and access control measures for all users", "D-03.1", "ONE_TIME", 3.0, "MANUFACTURER", "2026-04-01", "CRA-AnnexI-2"),
        ("OBL-D-03.2-001", "Enable multi-factor authentication where appropriate", "D-03.2", "ONE_TIME", 2.0, "MANUFACTURER", "2026-04-01", "GDPR-17-2"),
        ("OBL-D-03.3-001", "Restrict access to authorised personnel only; enforce least privilege", "D-03.3", "CONTINUOUS", 3.0, "CONTROLLER", "2026-04-01", "GDPR-7-1,GDPR-7-3"),
        ("OBL-D-03.4-001", "Disable unused ports/services; no default passwords; secure default configuration", "D-03.4", "ONE_TIME", 3.0, "MANUFACTURER", "2026-04-01", "CRA-AnnexI-2"),
        ("OBL-D-04.1-001", "Design system to limit severity of exploits; implement fail-safe mechanisms", "D-04.1", "ONE_TIME", 3.0, "MANUFACTURER", "2026-04-01", "CRA-AnnexII-2"),
        ("OBL-D-04.2-001", "Restore availability after incidents; build resilience against DoS attacks", "D-04.2", "TRIGGERED", 2.5, "CONTROLLER", "2026-04-01", "GDPR-32-1-c,CRA-AnnexII-2"),
        ("OBL-D-04.3-001", "Notify supervisory authority within 72h (GDPR) / 24h (CRA) of breaches", "D-04.3", "TRIGGERED", 3.0, "CONTROLLER", "2026-04-01", "GDPR-33-1,GDPR-33-2,CRA-AnnexIII-3"),
        ("OBL-D-04.4-001", "Ensure ongoing availability and ability to restore data after incident", "D-04.4", "CONTINUOUS", 2.0, "CONTROLLER", "2026-04-01", "GDPR-17-4"),
        ("OBL-D-05.1-001", "Process only data adequate, relevant and limited to what is necessary", "D-05.1", "CONTINUOUS", 3.0, "CONTROLLER", "2026-04-01", "GDPR-5-1,CRA-AnnexI-1"),
        ("OBL-D-05.2-001", "Do not keep personal data longer than necessary for purpose", "D-05.2", "CONTINUOUS", 3.0, "CONTROLLER", "2026-04-01", "GDPR-5-2,GDPR-5-4"),
        ("OBL-D-05.3-001", "Enable complete and secure data deletion on user request", "D-05.3", "TRIGGERED", 3.0, "CONTROLLER", "2026-04-01", "GDPR-17-3,CRA-AnnexI-4"),
        ("OBL-D-05.4-001", "Provide data export in structured, machine-readable format on request", "D-05.4", "TRIGGERED", 3.0, "CONTROLLER", "2026-04-01", "GDPR-20-1"),
        ("OBL-D-06.1-001", "Use only processors providing sufficient guarantees", "D-06.1", "ONE_TIME", 3.0, "CONTROLLER", "2026-04-01", "GDPR-28-1"),
        ("OBL-D-06.2-001", "Document all third-party components in machine-readable format (SBOM)", "D-06.2", "CONTINUOUS", 3.0, "MANUFACTURER", "2026-04-01", "CRA-AnnexI-4"),
        ("OBL-D-06.3-001", "Bind processors to security obligations via Data Processing Agreement", "D-06.3", "ONE_TIME", 3.0, "CONTROLLER", "2026-04-01", "GDPR-28-2"),
        ("OBL-D-07.1-001", "Integrate data protection and security into design from outset; secure by default", "D-07.1", "ONE_TIME", 2.667, "CONTROLLER", "2026-04-01", "GDPR-25-1,CRA-AnnexI-2,CRA-AnnexII-2"),
        ("OBL-D-08.1-001", "Train staff involved in processing operations on security awareness", "D-08.1", "PERIODIC", 3.0, "CONTROLLER", "2026-04-01", "GDPR-16-1"),
        ("OBL-D-08.2-001", "Raise awareness and train staff with role-specific security obligations", "D-08.2", "PERIODIC", 3.0, "CONTROLLER", "2026-04-01", "GDPR-16-2"),
        ("OBL-D-09.1-001", "Implement appropriate technical/organisational measures; document policies", "D-09.1", "CONTINUOUS", 2.75, "CONTROLLER", "2026-04-01", "GDPR-5-1,GDPR-24-1,GDPR-14-1,CRA-AnnexIII-1"),
        ("OBL-D-09.2-001", "Conduct DPIA prior to high-risk processing; cybersecurity risk assessment", "D-09.2", "PERIODIC", 2.667, "CONTROLLER", "2026-04-01", "GDPR-32-5,GDPR-24-2,CRA-AnnexIII-2"),
        ("OBL-D-09.4-001", "Maintain records of processing activities and breach documentation", "D-09.4", "CONTINUOUS", 3.0, "CONTROLLER", "2026-04-01", "GDPR-32-3,GDPR-19-1"),
        ("OBL-D-10.2-001", "Log security-relevant events; maintain audit trail of access", "D-10.2", "CONTINUOUS", 3.0, "MANUFACTURER", "2026-04-01", "CRA-AnnexII-1"),
        ("OBL-D-10.3-001", "Regularly test effectiveness of technical and organisational measures", "D-10.3", "PERIODIC", 2.5, "CONTROLLER", "2026-04-01", "GDPR-32-1-d,CRA-AnnexIII-3")
    ]
    
    count = 0
    for obl_id, desc, subdomain, obl_type, ni, party, date, source_clauses in obligations:
        cypher = """
        CREATE (o:Obligation {
            obligationId: $obligationId,
            description: $description,
            targetSubDomain: $targetSubDomain,
            obligationType: $obligationType,
            normativeIntensity: toFloat($normativeIntensity),
            obligatedParty: $obligatedParty,
            derivationDate: $derivationDate,
            sourceClauses: $sourceClauses
        })
        RETURN count(o)
        """
        params = {
            "obligationId": obl_id,
            "description": desc,
            "targetSubDomain": subdomain,
            "obligationType": obl_type,
            "normativeIntensity": str(ni),
            "obligatedParty": party,
            "derivationDate": date,
            "sourceClauses": source_clauses
        }
        result = exec_cypher(cypher, params)
        if result > 0:
            count += 1
    
    print(f"  ✓ Created {count} obligations")
    return count

def create_obligation_relationships():
    """Create relationships between obligations and clauses/subdomains"""
    print("\n" + "=" * 60)
    print("  Creating Obligation Relationships")
    print("=" * 60)
    
    # DERIVES_FROM relationships (Obligation → Clause)
    cypher = """
    MATCH (o:Obligation)
    WITH o, split(o.sourceClauses, ',') AS clauseIds
    UNWIND clauseIds AS clauseId
    MATCH (c:Clause {clauseId: trim(clauseId)})
    MERGE (o)-[:DERIVES_FROM]->(c)
    RETURN count(DISTINCT o) AS obligationsLinked
    """
    result = exec_cypher(cypher)
    print(f"  ✓ Created DERIVES_FROM relationships for {result} obligations")
    
    # TARGETS_SUBDOMAIN relationships (Obligation → SubDomain)
    cypher = """
    MATCH (o:Obligation)-[r:TARGETS_SUBDOMAIN]->()
    DELETE r
    """
    exec_cypher(cypher)
    
    cypher = """
    MATCH (o:Obligation), (sd:SubDomain {subDomainId: o.targetSubDomain})
    MERGE (o)-[:TARGETS_SUBDOMAIN {weight: o.normativeIntensity}]->(sd)
    RETURN count(DISTINCT o) AS obligationsLinked
    """
    result = exec_cypher(cypher)
    print(f"  ✓ Created TARGETS_SUBDOMAIN relationships for {result} obligations")
    
    return result

def load_tensions():
    """Load strategic tensions"""
    print("\n" + "=" * 60)
    print("  Loading Strategic Tensions")
    print("=" * 60)
    
    tensions = [
        ("TEN-001", "TEMPORAL_CONFLICT", "HIGH", "Breach notification timing: GDPR requires 72h, CRA requires 24h", "OBL-D-04.3-001", "OBL-D-04.3-001", "Adopt stricter requirement (24h)", 0.0, "RESOLVED"),
        ("TEN-002", "REQUIREMENT_CONFLICT", "MEDIUM", "Data erasure vs audit logging retention: conflicting deletion obligations", "OBL-D-05.3-001", "OBL-D-10.2-001", "Pseudonymized logging with configurable retention", 0.5, "RESOLVED"),
        ("TEN-003", "FREQUENCY_MISMATCH", "LOW", "DPIA and cybersecurity risk assessment: different trigger events", "OBL-D-09.2-001", "OBL-D-09.2-001", "Unify into single assessment process", 0.0, "RESOLVED"),
        ("TEN-004", "INTENSITY_GAP", "MEDIUM", "Secure by design: GDPR NI=2 vs CRA NI=3, implementation uncertainty", "OBL-D-07.1-001", "OBL-D-07.1-001", "Adopt higher standard (CRA NI=3) as baseline", 0.333, "RESOLVED")
    ]
    
    count = 0
    for ten_id, ten_type, severity, desc, obl1, obl2, strategy, ni_delta, status in tensions:
        cypher = """
        CREATE (t:StrategicTension {
            tensionId: $tensionId,
            tensionType: $tensionType,
            severity: $severity,
            description: $description,
            obligation1Id: $obligation1Id,
            obligation2Id: $obligation2Id,
            resolutionStrategy: $resolutionStrategy,
            normativeIntensityDelta: toFloat($niDelta),
            status: $status
        })
        RETURN count(t)
        """
        params = {
            "tensionId": ten_id,
            "tensionType": ten_type,
            "severity": severity,
            "description": desc,
            "obligation1Id": obl1,
            "obligation2Id": obl2,
            "resolutionStrategy": strategy,
            "niDelta": str(ni_delta),
            "status": status
        }
        result = exec_cypher(cypher, params)
        if result > 0:
            count += 1
    
    print(f"  ✓ Created {count} tensions")
    return count

def create_tension_relationships():
    """Create relationships between tensions and obligations"""
    print("\n" + "=" * 60)
    print("  Creating Tension Relationships")
    print("=" * 60)
    
    # INVOLVES_OBLIGATION relationships
    cypher = """
    MATCH (t:StrategicTension), (o:Obligation {obligationId: t.obligation1Id})
    MERGE (t)-[:INVOLVES_OBLIGATION]->(o)
    RETURN count(DISTINCT t) AS tensionsLinked
    """
    result1 = exec_cypher(cypher)
    
    cypher = """
    MATCH (t:StrategicTension), (o:Obligation {obligationId: t.obligation2Id})
    MERGE (t)-[:INVOLVES_OBLIGATION]->(o)
    RETURN count(DISTINCT t) AS tensionsLinked
    """
    result2 = exec_cypher(cypher)
    
    print(f"  ✓ Created INVOLVES_OBLIGATION relationships for {max(result1, result2)} tensions")
    return max(result1, result2)

def load_goals():
    """Load privacy and security goals"""
    print("\n" + "=" * 60)
    print("  Loading Goals")
    print("=" * 60)
    
    goals = [
        ("PG-D-01.1-001", "Encrypt all personal and sensitive data at rest using AES-256 or equivalent", "PRIVACY", "D-01.1", "LOW", "HIGH", "Ensure all personal data is encrypted at rest", "GDPR Art.32", "Implement AES-256 encryption for database storage", "OBL-D-01.1-001"),
        ("PG-D-01.2-001", "Encrypt all personal data in transit using TLS 1.3", "PRIVACY", "D-01.2", "LOW", "HIGH", "Ensure all data transmission is encrypted", "GDPR Art.32", "Implement TLS 1.3 for all network communications", "OBL-D-01.2-001"),
        ("PG-D-01.4-001", "Protect personal data against unauthorised manipulation and accidental loss", "PRIVACY", "D-01.4", "LOW", "HIGH", "Ensure data integrity and availability", "GDPR Art.32", "Implement checksums, backups, access controls", "OBL-D-01.4-001"),
        ("PG-D-05.1-001", "Minimize personal data collection to essential task management fields only", "PRIVACY", "D-05.1", "LOW", "HIGH", "Collect only necessary personal data", "GDPR Art.5", "Implement data minimization in forms and APIs", "OBL-D-05.1-001"),
        ("PG-D-05.2-001", "Retain personal data only for duration of active task + 30 days", "PRIVACY", "D-05.2", "LOW", "MODERATE", "Implement automated data retention policies", "GDPR Art.5", "Build automated deletion workflows", "OBL-D-05.2-001"),
        ("PG-D-05.3-001", "Enable complete data erasure on user request within 7 days", "PRIVACY", "D-05.3", "LOW", "CRITICAL", "Support right to erasure with timely execution", "GDPR Art.17", "Implement erasure API with 7-day SLA", "OBL-D-05.3-001"),
        ("PG-D-05.4-001", "Provide data export in machine-readable format (JSON) on request within 48h", "PRIVACY", "D-05.4", "LOW", "MODERATE", "Enable data portability for users", "GDPR Art.20", "Build JSON export endpoint", "OBL-D-05.4-001"),
        ("PG-D-07.1-001", "Integrate data protection measures into processing design from outset", "PRIVACY", "D-07.1", "LOW", "HIGH", "Privacy by design in all features", "GDPR Art.25", "Conduct privacy reviews in design phase", "OBL-D-07.1-001"),
        ("PG-D-09.1-001", "Maintain comprehensive privacy policies documenting appropriate measures", "PRIVACY", "D-09.1", "LOW", "HIGH", "Document all privacy measures and policies", "GDPR Art.24", "Create privacy policy documentation", "OBL-D-09.1-001"),
        ("PG-D-09.2-001", "Conduct privacy impact assessments (DPIA) prior to high-risk processing", "PRIVACY", "D-09.2", "LOW", "HIGH", "Perform DPIA for high-risk operations", "GDPR Art.35", "Implement DPIA workflow and templates", "OBL-D-09.2-001"),
        ("PG-D-09.4-001", "Maintain records of all personal data processing activities", "PRIVACY", "D-09.4", "LOW", "MODERATE", "Keep comprehensive processing records", "GDPR Art.30", "Build processing activity registry", "OBL-D-09.4-001"),
        ("SG-D-02.1-001", "Deliver product with no known exploitable vulnerabilities", "SECURITY", "D-02.1", "MODERATE", "CRITICAL", "Zero known vulnerabilities in production", "CRA Annex I", "Implement SAST/DAST scanning pipeline", "OBL-D-02.1-001"),
        ("SG-D-02.2-001", "Enable automatic security updates with prompt remediation", "SECURITY", "D-02.2", "MODERATE", "HIGH", "Automated vulnerability remediation", "CRA Annex II", "Build auto-update mechanism", "OBL-D-02.2-001"),
        ("SG-D-02.3-001", "Publish coordinated vulnerability disclosure policy", "SECURITY", "D-02.3", "MODERATE", "HIGH", "Transparent vulnerability management", "CRA Annex III", "Create vulnerability disclosure page", "OBL-D-02.3-001"),
        ("SG-D-03.1-001", "Implement authentication and access control for all users", "SECURITY", "D-03.1", "LOW", "HIGH", "Secure authentication for all access", "CRA Annex I", "Implement OAuth2/OIDC authentication", "OBL-D-03.1-001"),
        ("SG-D-03.2-001", "Enable multi-factor authentication where appropriate", "SECURITY", "D-03.2", "LOW", "MODERATE", "MFA for sensitive operations", "CRA Annex I", "Add TOTP/SMS MFA support", "OBL-D-03.2-001"),
        ("SG-D-03.3-001", "Restrict access to authorised personnel with least privilege", "SECURITY", "D-03.3", "LOW", "HIGH", "Role-based access control", "GDPR Art.25", "Implement RBAC system", "OBL-D-03.3-001"),
        ("SG-D-03.4-001", "Secure default configuration with no default passwords", "SECURITY", "D-03.4", "LOW", "HIGH", "Hardened default configurations", "CRA Annex I", "Remove default credentials, disable unused ports", "OBL-D-03.4-001"),
        ("SG-D-04.1-001", "Design fail-safe mechanisms to limit exploit impact", "SECURITY", "D-04.1", "MODERATE", "HIGH", "Resilient system design", "CRA Annex II", "Implement circuit breakers, rate limiting", "OBL-D-04.1-001"),
        ("SG-D-04.2-001", "Restore availability after incidents with DoS resilience", "SECURITY", "D-04.2", "MODERATE", "HIGH", "Incident recovery and availability", "GDPR Art.32", "Implement backup/failover systems", "OBL-D-04.2-001"),
        ("SG-D-04.3-001", "Notify authorities within required timeframe of breaches", "SECURITY", "D-04.3", "HIGH", "CRITICAL", "Timely breach notification", "GDPR Art.33", "Automated breach detection and alerting", "OBL-D-04.3-001"),
        ("SG-D-04.4-001", "Ensure ongoing data availability and restoration", "SECURITY", "D-04.4", "LOW", "MODERATE", "Data backup and recovery", "GDPR Art.32", "Implement automated backups", "OBL-D-04.4-001"),
        ("SG-D-06.2-001", "Document all third-party components in SBOM format", "SECURITY", "D-06.2", "MODERATE", "HIGH", "Complete software bill of materials", "CRA Annex I", "Generate SBOM with each release", "OBL-D-06.2-001"),
        ("SG-D-10.2-001", "Log security-relevant events with audit trail", "SECURITY", "D-10.2", "MODERATE", "HIGH", "Comprehensive security logging", "CRA Annex II", "Implement structured logging (JSON)", "OBL-D-10.2-001"),
        ("SG-D-10.3-001", "Regularly test effectiveness of security measures", "SECURITY", "D-10.3", "MODERATE", "HIGH", "Continuous security validation", "GDPR Art.32", "Schedule quarterly penetration tests", "OBL-D-10.3-001")
    ]
    
    count = 0
    for goal_id, desc, category, subdomain, risk, priority, statement, source, tech_impl, source_obl in goals:
        cypher = """
        CREATE (g:Goal {
            goalId: $goalId,
            description: $description,
            category: $category,
            targetSubDomain: $targetSubDomain,
            riskProfile: $riskProfile,
            priority: $priority,
            goalStatement: $goalStatement,
            regulatorySource: $regulatorySource,
            technicalImplication: $technicalImplication,
            sourceObligations: $sourceObligations
        })
        RETURN count(g)
        """
        params = {
            "goalId": goal_id,
            "description": desc,
            "category": category,
            "targetSubDomain": subdomain,
            "riskProfile": risk,
            "priority": priority,
            "goalStatement": statement,
            "regulatorySource": source,
            "technicalImplication": tech_impl,
            "sourceObligations": source_obl
        }
        result = exec_cypher(cypher, params)
        if result > 0:
            count += 1
    
    print(f"  ✓ Created {count} goals")
    return count

def create_goal_relationships():
    """Create relationships between goals and obligations/subdomains"""
    print("\n" + "=" * 60)
    print("  Creating Goal Relationships")
    print("=" * 60)
    
    # FORMALIZES relationships (Obligation → Goal)
    cypher = """
    MATCH (o:Obligation), (g:Goal)
    WHERE g.sourceObligations = o.obligationId
    MERGE (o)-[:FORMALIZES]->(g)
    RETURN count(DISTINCT o) AS obligationsLinked
    """
    result = exec_cypher(cypher)
    print(f"  ✓ Created FORMALIZES relationships for {result} obligations")
    
    # BELONGS_TO_SUBDOMAIN relationships (Goal → SubDomain)
    cypher = """
    MATCH (g:Goal), (sd:SubDomain {subDomainId: g.targetSubDomain})
    MERGE (g)-[:BELONGS_TO_SUBDOMAIN]->(sd)
    RETURN count(DISTINCT g) AS goalsLinked
    """
    result = exec_cypher(cypher)
    print(f"  ✓ Created BELONGS_TO_SUBDOMAIN relationships for {result} goals")
    
    return result

def load_rules():
    """Load compliance and best practice rules"""
    print("\n" + "=" * 60)
    print("  Loading Rules")
    print("=" * 60)
    
    rules = [
        ("CR-001", "Encrypt all personal data at rest using AES-256 or equivalent algorithm", "COMPLIANCE", "D-01.1", 2.667, "REGULATORY", "GDPR Art.32(1)(a), CRA Annex I", True, "", "HIGH", "OBL-D-01.1-001", "PG-D-01.1-001"),
        ("CR-002", "Encrypt all data in transit using TLS 1.3 or equivalent", "COMPLIANCE", "D-01.2", 2.5, "REGULATORY", "GDPR Art.32, CRA Annex I", True, "", "HIGH", "OBL-D-01.2-001", "PG-D-01.2-001"),
        ("CR-003", "Implement secure cryptographic key management with rotation", "COMPLIANCE", "D-01.3", 3.0, "REGULATORY", "CRA Annex I", True, "", "HIGH", "OBL-D-01.3-001", ""),
        ("CR-004", "Protect data integrity against manipulation and accidental loss", "COMPLIANCE", "D-01.4", 3.0, "REGULATORY", "GDPR Art.32, CRA Annex II", True, "", "HIGH", "OBL-D-01.4-001", "PG-D-01.4-001"),
        ("CR-005", "Deliver product without known exploitable vulnerabilities", "COMPLIANCE", "D-02.1", 3.0, "REGULATORY", "CRA Annex I, II", True, "", "HIGH", "OBL-D-02.1-001", "SG-D-02.1-001"),
        ("CR-006", "Enable automatic security updates with prompt remediation", "COMPLIANCE", "D-02.2", 3.0, "REGULATORY", "CRA Annex I, II", True, "", "HIGH", "OBL-D-02.2-001", "SG-D-02.2-001"),
        ("CR-007", "Publish vulnerability disclosure policy and report to ENISA", "COMPLIANCE", "D-02.3", 3.0, "REGULATORY", "CRA Annex III", True, "", "HIGH", "OBL-D-02.3-001", "SG-D-02.3-001"),
        ("CR-008", "Implement authentication and access control for all users", "COMPLIANCE", "D-03.1", 3.0, "REGULATORY", "CRA Annex I", True, "", "HIGH", "OBL-D-03.1-001", "SG-D-03.1-001"),
        ("CR-009", "Enable multi-factor authentication for sensitive operations", "COMPLIANCE", "D-03.2", 2.0, "REGULATORY", "CRA Annex I", False, "", "MEDIUM", "OBL-D-03.2-001", "SG-D-03.2-001"),
        ("CR-010", "Enforce least privilege access control", "COMPLIANCE", "D-03.3", 3.0, "REGULATORY", "GDPR Art.25", True, "", "HIGH", "OBL-D-03.3-001", "SG-D-03.3-001"),
        ("CR-011", "Secure default configuration, disable unused services", "COMPLIANCE", "D-03.4", 3.0, "REGULATORY", "CRA Annex I", True, "", "HIGH", "OBL-D-03.4-001", "SG-D-03.4-001"),
        ("CR-012", "Design fail-safe mechanisms to limit exploit impact", "COMPLIANCE", "D-04.1", 3.0, "REGULATORY", "CRA Annex II", True, "", "HIGH", "OBL-D-04.1-001", "SG-D-04.1-001"),
        ("CR-013", "Implement incident recovery and DoS resilience", "COMPLIANCE", "D-04.2", 2.5, "REGULATORY", "GDPR Art.32, CRA Annex II", True, "", "HIGH", "OBL-D-04.2-001", "SG-D-04.2-001"),
        ("CR-014", "Notify supervisory authority within 24h of breach", "COMPLIANCE", "D-04.3", 3.0, "REGULATORY", "GDPR Art.33, CRA Annex III", True, "", "CRITICAL", "OBL-D-04.3-001", "SG-D-04.3-001"),
        ("CR-015", "Ensure ongoing data availability and restoration capability", "COMPLIANCE", "D-04.4", 2.0, "REGULATORY", "GDPR Art.32", True, "", "MEDIUM", "OBL-D-04.4-001", "SG-D-04.4-001"),
        ("CR-016", "Minimize personal data collection to essential fields", "COMPLIANCE", "D-05.1", 3.0, "REGULATORY", "GDPR Art.5, CRA Annex I", True, "", "HIGH", "OBL-D-05.1-001", "PG-D-05.1-001"),
        ("CR-017", "Implement automated data retention and deletion policies", "COMPLIANCE", "D-05.2", 3.0, "REGULATORY", "GDPR Art.5", True, "", "HIGH", "OBL-D-05.2-001", "PG-D-05.2-001"),
        ("CR-018", "Enable complete data erasure on user request within 7 days", "COMPLIANCE", "D-05.3", 3.0, "REGULATORY", "GDPR Art.17, CRA Annex I", True, "", "CRITICAL", "OBL-D-05.3-001", "PG-D-05.3-001"),
        ("CR-019", "Provide data export in machine-readable format within 48h", "COMPLIANCE", "D-05.4", 3.0, "REGULATORY", "GDPR Art.20", True, "", "HIGH", "OBL-D-05.4-001", "PG-D-05.4-001"),
        ("CR-020", "Use only processors providing sufficient security guarantees", "COMPLIANCE", "D-06.1", 3.0, "REGULATORY", "GDPR Art.28", True, "", "HIGH", "OBL-D-06.1-001", ""),
        ("CR-021", "Document all third-party components in SBOM format", "COMPLIANCE", "D-06.2", 3.0, "REGULATORY", "CRA Annex I", True, "", "HIGH", "OBL-D-06.2-001", "SG-D-06.2-001"),
        ("CR-022", "Bind processors to security obligations via DPA", "COMPLIANCE", "D-06.3", 3.0, "REGULATORY", "GDPR Art.28", True, "", "HIGH", "OBL-D-06.3-001", ""),
        ("CR-023", "Integrate privacy and security into design from outset", "COMPLIANCE", "D-07.1", 2.667, "REGULATORY", "GDPR Art.25, CRA Annex I, II", True, "", "HIGH", "OBL-D-07.1-001", "PG-D-07.1-001"),
        ("CR-024", "Conduct security awareness training for all staff", "COMPLIANCE", "D-08.1", 3.0, "REGULATORY", "GDPR Art.39", True, "", "HIGH", "OBL-D-08.1-001", ""),
        ("CR-025", "Provide role-specific security training", "COMPLIANCE", "D-08.2", 3.0, "REGULATORY", "GDPR Art.39", True, "", "HIGH", "OBL-D-08.2-001", ""),
        ("CR-026", "Implement and document technical/organisational measures", "COMPLIANCE", "D-09.1", 2.75, "REGULATORY", "GDPR Art.24, CRA Annex III", True, "", "HIGH", "OBL-D-09.1-001", "PG-D-09.1-001"),
        ("CR-027", "Conduct DPIA prior to high-risk processing", "COMPLIANCE", "D-09.2", 2.667, "REGULATORY", "GDPR Art.35, CRA Annex III", True, "", "HIGH", "OBL-D-09.2-001", "PG-D-09.2-001"),
        ("CR-028", "Maintain records of processing activities", "COMPLIANCE", "D-09.4", 3.0, "REGULATORY", "GDPR Art.30", True, "", "HIGH", "OBL-D-09.4-001", "PG-D-09.4-001"),
        ("CR-029", "Log security-relevant events with audit trail", "COMPLIANCE", "D-10.2", 3.0, "REGULATORY", "CRA Annex II", True, "", "HIGH", "OBL-D-10.2-001", "SG-D-10.2-001"),
        ("CR-030", "Regularly test effectiveness of security measures", "COMPLIANCE", "D-10.3", 2.5, "REGULATORY", "GDPR Art.32, CRA Annex III", True, "", "HIGH", "OBL-D-10.3-001", "SG-D-10.3-001"),
        ("BP-001", "Implement automated vulnerability scanning in CI/CD pipeline", "BEST_PRACTICE", "D-02.1", 2.5, "BEST_PRACTICE", "NIST SP 800-40, OWASP", False, "NIST SP 800-40", "HIGH", "", "SG-D-02.1-001"),
        ("BP-002", "Implement threat modeling in design phase", "BEST_PRACTICE", "D-07.1", 2.0, "BEST_PRACTICE", "OWASP SAMM, Microsoft SDL", False, "OWASP SAMM", "MEDIUM", "", "PG-D-07.1-001"),
        ("BP-003", "Conduct annual penetration testing by independent party", "BEST_PRACTICE", "D-10.3", 2.5, "BEST_PRACTICE", "ISO 27001, NIST SP 800-115", False, "ISO 27001", "HIGH", "", "SG-D-10.3-001"),
        ("BP-004", "Implement security champions program in development teams", "BEST_PRACTICE", "D-08.1", 2.0, "BEST_PRACTICE", "OWASP SAMM", False, "OWASP SAMM", "MEDIUM", "", ""),
        ("BP-005", "Establish incident response playbooks for common scenarios", "BEST_PRACTICE", "D-04.1", 2.5, "BEST_PRACTICE", "NIST SP 800-61", False, "NIST SP 800-61", "HIGH", "", "SG-D-04.1-001"),
        ("BP-006", "Implement zero-trust network architecture", "BEST_PRACTICE", "D-03.1", 2.0, "BEST_PRACTICE", "NIST SP 800-207", False, "NIST SP 800-207", "MEDIUM", "", ""),
        ("BP-007", "Use infrastructure-as-code with security scanning", "BEST_PRACTICE", "D-07.1", 2.0, "BEST_PRACTICE", "NIST SP 800-218", False, "NIST SP 800-218", "MEDIUM", "", ""),
        ("BP-008", "Implement continuous compliance monitoring dashboard", "BEST_PRACTICE", "D-09.1", 2.5, "BEST_PRACTICE", "ISO 27004", False, "ISO 27004", "HIGH", "", "PG-D-09.1-001")
    ]
    
    count = 0
    for rule_id, desc, category, subdomain, ni, source_type, ref, is_mandatory, framework, confidence, source_obl, source_goal in rules:
        cypher = """
        CREATE (r:Rule {
            ruleId: $ruleId,
            description: $description,
            category: $category,
            targetSubDomain: $targetSubDomain,
            normativeIntensity: toFloat($normativeIntensity),
            sourceType: $sourceType,
            regulatoryReference: $regulatoryReference,
            isMandatory: $isMandatory,
            frameworkReference: $frameworkReference,
            confidenceLevel: $confidenceLevel,
            sourceObligations: $sourceObligations,
            sourceGoals: $sourceGoals
        })
        RETURN count(r)
        """
        params = {
            "ruleId": rule_id,
            "description": desc,
            "category": category,
            "targetSubDomain": subdomain,
            "normativeIntensity": str(ni),
            "sourceType": source_type,
            "regulatoryReference": ref,
            "isMandatory": is_mandatory,
            "frameworkReference": framework,
            "confidenceLevel": confidence,
            "sourceObligations": source_obl,
            "sourceGoals": source_goal
        }
        result = exec_cypher(cypher, params)
        if result > 0:
            count += 1
    
    print(f"  ✓ Created {count} rules")
    return count

def create_rule_relationships():
    """Create relationships between rules and obligations/goals/subdomains"""
    print("\n" + "=" * 60)
    print("  Creating Rule Relationships")
    print("=" * 60)
    
    # DERIVED_FROM_OBLIGATION relationships (Rule → Obligation)
    cypher = """
    MATCH (r:Rule), (o:Obligation)
    WHERE r.sourceObligations = o.obligationId
    MERGE (r)-[:DERIVED_FROM_OBLIGATION {weight: r.normativeIntensity}]->(o)
    RETURN count(DISTINCT r) AS rulesLinked
    """
    result1 = exec_cypher(cypher)
    
    # SATISFIES_GOAL relationships (Rule → Goal)
    cypher = """
    MATCH (r:Rule), (g:Goal)
    WHERE r.sourceGoals = g.goalId
    MERGE (r)-[:SATISFIES_GOAL]->(g)
    RETURN count(DISTINCT r) AS rulesLinked
    """
    result2 = exec_cypher(cypher)
    
    # TARGETS_SUBDOMAIN relationships (Rule → SubDomain)
    cypher = """
    MATCH (r:Rule), (sd:SubDomain {subDomainId: r.targetSubDomain})
    MERGE (r)-[:TARGETS_SUBDOMAIN {weight: r.normativeIntensity}]->(sd)
    RETURN count(DISTINCT r) AS rulesLinked
    """
    result3 = exec_cypher(cypher)
    
    print(f"  ✓ Created DERIVED_FROM_OBLIGATION for {result1} rules")
    print(f"  ✓ Created SATISFIES_GOAL for {result2} rules")
    print(f"  ✓ Created TARGETS_SUBDOMAIN for {result3} rules")
    
    return result3

def verify_phase2():
    """Verify Phase 2 data loading"""
    print("\n" + "=" * 60)
    print("  Phase 2 Verification")
    print("=" * 60)
    
    cypher = """
    MATCH (n)
    WHERE n:Obligation OR n:Goal OR n:StrategicTension OR n:Rule
    WITH labels(n)[0] AS label, count(*) AS count
    RETURN label, count
    ORDER BY label
    """
    results = exec_cypher_return(cypher)
    total = 0
    if results and 'data' in results[0]:
        for row in results[0]['data']:
            label = row['row'][0]
            count = row['row'][1]
            total += count
            print(f"  {label}: {count}")
    
    # Count relationships
    cypher = """
    MATCH ()-[r]->()
    WHERE type(r) IN ['DERIVES_FROM', 'TARGETS_SUBDOMAIN', 'FORMALIZES', 
                       'INVOLVES_OBLIGATION', 'BELONGS_TO_SUBDOMAIN', 
                       'DERIVED_FROM_OBLIGATION', 'SATISFIES_GOAL']
    WITH type(r) AS relType, count(*) AS count
    RETURN relType, count
    ORDER BY count DESC
    """
    results = exec_cypher_return(cypher)
    total_rels = 0
    if results and 'data' in results[0]:
        for row in results[0]['data']:
            relType = row['row'][0]
            count = row['row'][1]
            total_rels += count
            print(f"  [{relType}]: {count}")
    
    print(f"\n  TOTAL PHASE 2 NODES: {total}")
    print(f"  TOTAL PHASE 2 RELATIONSHIPS: {total_rels}")
    return total, total_rels

def main():
    print("=" * 60)
    print("  AEGIS Phase 2 Knowledge Graph - ETL")
    print("=" * 60)
    
    # Test connection
    print("\n1. Testing Neo4j connection...")
    try:
        r = requests.get(NEO4J_HTTP, auth=AUTH, timeout=5)
        if r.status_code == 200:
            print(f"   ✓ Neo4j {r.json().get('neo4j_version', 'unknown')} at {NEO4J_HTTP}")
        else:
            print(f"   ✗ HTTP {r.status_code}")
            return
    except Exception as e:
        print(f"   ✗ {e}")
        return
    
    # Load Phase 2 data
    load_obligations()
    create_obligation_relationships()
    
    load_tensions()
    create_tension_relationships()
    
    load_goals()
    create_goal_relationships()
    
    load_rules()
    create_rule_relationships()
    
    # Verify
    verify_phase2()
    
    print("\n" + "=" * 60)
    print("  ✓ Phase 2 ETL Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
