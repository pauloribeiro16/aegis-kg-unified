import os
#!/usr/bin/env python3
"""
AEGIS Phase 3 Knowledge Graph - ETL Script
Loads Use Cases, Functional Requirements, NFRs, FRs, Threats, Risks, and Mitigations into Neo4j.
Based on TinyTask SaaS Phase 3 decomposition data.
"""
import requests

NEO4J_HTTP = "http://localhost:7474"
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", ""))

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
            return 0
        result = response.json()
        if result.get('errors'):
            return 0
        try:
            data = result.get('results', [{}])[0].get('data', [{}])[0].get('row', [0])
            return data[0] if data else 0
        except (IndexError, TypeError):
            return 0
    except:
        return 0

def load_nfrs():
    """Load Non-Functional Requirements from TinyTask"""
    print("\n" + "=" * 60)
    print("  Loading Phase 3: NFRs")
    print("=" * 60)
    
    nfrs = [
        # CONFIDENTIALITY (7)
        ("NFR-CONF-001", "All personal data at rest must be encrypted", "CONFIDENTIALITY", "CRITICAL", "AES-256 encryption for all databases", "100% coverage", "Automated scan", "GDPR Art.32"),
        ("NFR-CONF-002", "All network communications must be encrypted", "CONFIDENTIALITY", "CRITICAL", "TLS 1.3 for all endpoints", "0 unencrypted connections", "Network scan", "GDPR Art.32"),
        ("NFR-CONF-003", "Access to personal data must be restricted", "CONFIDENTIALITY", "HIGH", "Role-based access control", "< 5% unauthorized access attempts", "Access log review", "GDPR Art.25"),
        ("NFR-CONF-004", "API keys and secrets must be protected", "CONFIDENTIALITY", "HIGH", "Secrets management system", "0 exposed secrets", "Secret scan", "CRA Annex I"),
        ("NFR-CONF-005", "Session tokens must be secure", "CONFIDENTIALITY", "HIGH", "Secure session management", "0 session hijacking incidents", "Penetration test", "GDPR Art.32"),
        ("NFR-CONF-006", "Backup data must be encrypted", "CONFIDENTIALITY", "MODERATE", "Encrypted backups", "100% encrypted backups", "Backup audit", "GDPR Art.32"),
        ("NFR-CONF-007", "Logs must not contain sensitive data", "CONFIDENTIALITY", "MODERATE", "Log sanitization", "0 PII in logs", "Log review", "GDPR Art.32"),
        # INTEGRITY (7)
        ("NFR-INT-001", "Data must be protected against unauthorized modification", "INTEGRITY", "CRITICAL", "Checksums and digital signatures", "0 unauthorized modifications", "Integrity scan", "GDPR Art.32"),
        ("NFR-INT-002", "Security updates must be verified", "INTEGRITY", "HIGH", "Code signing for updates", "100% signed updates", "Update audit", "CRA Annex I"),
        ("NFR-INT-003", "Audit logs must be tamper-proof", "INTEGRITY", "HIGH", "Immutable logging", "0 log tampering incidents", "Log integrity check", "CRA Annex II"),
        ("NFR-INT-004", "Database records must maintain integrity", "INTEGRITY", "HIGH", "Database constraints and triggers", "0 integrity violations", "Database audit", "GDPR Art.32"),
        ("NFR-INT-005", "Configuration files must be protected", "INTEGRITY", "MODERATE", "File integrity monitoring", "0 unauthorized config changes", "FIM scan", "CRA Annex I"),
        ("NFR-INT-006", "Data exports must maintain integrity", "INTEGRITY", "MODERATE", "Checksums on exports", "100% verified exports", "Export validation", "GDPR Art.20"),
        ("NFR-INT-007", "Software components must be verified", "INTEGRITY", "MODERATE", "SBOM verification", "100% verified components", "SBOM audit", "CRA Annex I"),
        # AVAILABILITY (7)
        ("NFR-AVAIL-001", "System must maintain high availability", "AVAILABILITY", "CRITICAL", "99.9% uptime SLA", "99.9% uptime", "Monitoring", "GDPR Art.32"),
        ("NFR-AVAIL-002", "Data must be recoverable after incidents", "AVAILABILITY", "HIGH", "Backup and restore capability", "RTO < 4h, RPO < 1h", "Disaster recovery test", "GDPR Art.32"),
        ("NFR-AVAIL-003", "System must handle DoS attacks", "AVAILABILITY", "HIGH", "Rate limiting and DDoS protection", "0 successful DoS attacks", "Load testing", "CRA Annex II"),
        ("NFR-AVAIL-004", "Critical functions must be resilient", "AVAILABILITY", "HIGH", "Circuit breakers and failover", "< 1% failure rate", "Chaos testing", "GDPR Art.32"),
        ("NFR-AVAIL-005", "API must handle peak loads", "AVAILABILITY", "MODERATE", "Auto-scaling", "Response time < 2s at peak", "Load testing", "CRA Annex I"),
        ("NFR-AVAIL-006", "Data export must be available on demand", "AVAILABILITY", "MODERATE", "On-demand export capability", "Export available within 48h", "Export testing", "GDPR Art.20"),
        ("NFR-AVAIL-007", "Support must be available during business hours", "AVAILABILITY", "LOW", "Business hours support", "Response within 4h", "Support metrics", "GDPR Art.32"),
        # PRIVACY (10)
        ("NFR-PRIV-001", "Data collection must be minimized", "PRIVACY", "CRITICAL", "Only essential data collected", "< 10 data fields per user", "Data audit", "GDPR Art.5"),
        ("NFR-PRIV-002", "Data retention must be enforced", "PRIVACY", "HIGH", "Automated deletion after 30 days", "0 overdue records", "Retention audit", "GDPR Art.5"),
        ("NFR-PRIV-003", "Users must be able to erase their data", "PRIVACY", "CRITICAL", "Right to erasure within 7 days", "100% erasure within 7 days", "Erasure audit", "GDPR Art.17"),
        ("NFR-PRIV-004", "Users must be able to export their data", "PRIVACY", "HIGH", "Data portability in JSON", "Export within 48h", "Export audit", "GDPR Art.20"),
        ("NFR-PRIV-005", "Privacy notices must be provided", "PRIVACY", "HIGH", "Clear privacy policy", "100% user acknowledgment", "Compliance check", "GDPR Art.13"),
        ("NFR-PRIV-006", "Consent must be obtained and recorded", "PRIVACY", "HIGH", "Explicit consent mechanism", "100% consent records", "Consent audit", "GDPR Art.7"),
        ("NFR-PRIV-007", "DPIA must be conducted for high-risk processing", "PRIVACY", "HIGH", "DPIA process", "100% DPIA coverage", "DPIA review", "GDPR Art.35"),
        ("NFR-PRIV-008", "Data processing must be documented", "PRIVACY", "MODERATE", "Processing activity records", "100% documentation", "Documentation audit", "GDPR Art.30"),
        ("NFR-PRIV-009", "Privacy by design must be implemented", "PRIVACY", "HIGH", "Privacy reviews in design", "100% privacy reviews", "Design review", "GDPR Art.25"),
        ("NFR-PRIV-010", "Third-party data sharing must be controlled", "PRIVACY", "MODERATE", "Data sharing agreements", "100% agreements in place", "Vendor audit", "GDPR Art.28"),
        # ACCESSIBILITY (6)
        ("NFR-ACC-001", "Authentication must be user-friendly", "ACCESSIBILITY", "HIGH", "Simple login process", "< 2 min to authenticate", "Usability testing", "CRA Annex I"),
        ("NFR-ACC-002", "Error messages must be clear", "ACCESSIBILITY", "MODERATE", "User-friendly error messages", "< 5% support tickets for errors", "User testing", "CRA Annex III"),
        ("NFR-ACC-003", "UI must support multiple languages", "ACCESSIBILITY", "MODERATE", "Multi-language support", "EN + PT at launch", "Localization test", "GDPR Art.13"),
        ("NFR-ACC-004", "Data export format must be standard", "ACCESSIBILITY", "MODERATE", "JSON/CSV export", "Standard format compliance", "Format validation", "GDPR Art.20"),
        ("NFR-ACC-005", "API must be well-documented", "ACCESSIBILITY", "MODERATE", "OpenAPI documentation", "100% endpoint coverage", "Doc review", "CRA Annex III"),
        ("NFR-ACC-006", "System must be accessible on mobile", "ACCESSIBILITY", "LOW", "Responsive web design", "Mobile compatibility", "Device testing", "CRA Annex I"),
        # COMPLIANCE (9)
        ("NFR-COMP-001", "All GDPR obligations must be met", "COMPLIANCE", "CRITICAL", "GDPR compliance program", "100% obligation coverage", "Compliance audit", "GDPR"),
        ("NFR-COMP-002", "All CRA requirements must be satisfied", "COMPLIANCE", "CRITICAL", "CRA compliance program", "100% requirement coverage", "Compliance audit", "CRA"),
        ("NFR-COMP-003", "Vulnerability disclosure policy must exist", "COMPLIANCE", "HIGH", "Public disclosure policy", "Policy published", "Policy review", "CRA Annex III"),
        ("NFR-COMP-004", "Security documentation must be maintained", "COMPLIANCE", "HIGH", "Technical documentation", "10 years retention", "Doc audit", "CRA Annex III"),
        ("NFR-COMP-005", "Regular security testing must be performed", "COMPLIANCE", "HIGH", "Quarterly penetration tests", "4 tests per year", "Test reports", "GDPR Art.32"),
        ("NFR-COMP-006", "Breach notification must be timely", "COMPLIANCE", "CRITICAL", "24h notification to authorities", "100% within 24h", "Incident audit", "GDPR Art.33"),
        ("NFR-COMP-007", "Staff must be trained on security", "COMPLIANCE", "HIGH", "Annual security training", "100% staff trained", "Training records", "GDPR Art.39"),
        ("NFR-COMP-008", "SBOM must be maintained", "COMPLIANCE", "HIGH", "Software Bill of Materials", "Updated with each release", "SBOM audit", "CRA Annex I"),
        ("NFR-COMP-009", "Compliance gates must pass", "COMPLIANCE", "CRITICAL", "All gates PASS", "100% gate pass rate", "Gate reports", "GDPR+CRA")
    ]
    
    count = 0
    for nfr_id, desc, category, priority, metric, target, verification, source_reg in nfrs:
        cypher = """
        CREATE (n:NFR {
            nfrId: $nfrId,
            description: $description,
            category: $category,
            priority: $priority,
            metric: $metric,
            target: $target,
            verificationMethod: $verificationMethod,
            sourceRegulation: $sourceRegulation
        })
        RETURN count(n)
        """
        params = {
            "nfrId": nfr_id,
            "description": desc,
            "category": category,
            "priority": priority,
            "metric": metric,
            "target": target,
            "verificationMethod": verification,
            "sourceRegulation": source_reg
        }
        if exec_cypher(cypher, params) > 0:
            count += 1
    
    print(f"  ✓ Created {count} NFRs")
    return count

def load_fr():
    """Load Functional Requirements from TinyTask"""
    print("\n" + "=" * 60)
    print("  Loading Phase 3: Functional Requirements")
    print("=" * 60)
    
    frs = [
        # IAM (10)
        ("FR-IAM-001", "Implement user registration with email verification", "IAM", "HIGH", "Automated test", "OBL-D-03.1-001", "NFR-ACC-001"),
        ("FR-IAM-002", "Implement login with password validation", "IAM", "HIGH", "Automated test", "OBL-D-03.1-001", "NFR-CONF-005"),
        ("FR-IAM-003", "Implement multi-factor authentication option", "IAM", "MODERATE", "Manual test", "OBL-D-03.2-001", "NFR-CONF-005"),
        ("FR-IAM-004", "Implement role-based access control", "IAM", "HIGH", "Automated test", "OBL-D-03.3-001", "NFR-CONF-003"),
        ("FR-IAM-005", "Implement password reset functionality", "IAM", "HIGH", "Automated test", "OBL-D-03.1-001", "NFR-ACC-001"),
        ("FR-IAM-006", "Implement session management with timeout", "IAM", "HIGH", "Automated test", "OBL-D-03.1-001", "NFR-CONF-005"),
        ("FR-IAM-007", "Implement account lockout after failed attempts", "IAM", "HIGH", "Automated test", "OBL-D-03.4-001", "NFR-CONF-005"),
        ("FR-IAM-008", "Implement user profile management", "IAM", "MODERATE", "Manual test", "OBL-D-03.3-001", "NFR-ACC-001"),
        ("FR-IAM-009", "Implement logout functionality", "IAM", "HIGH", "Automated test", "OBL-D-03.1-001", "NFR-CONF-005"),
        ("FR-IAM-010", "Implement admin user management", "IAM", "MODERATE", "Manual test", "OBL-D-03.3-001", "NFR-CONF-003"),
        # Data Protection (12)
        ("FR-DP-001", "Implement AES-256 encryption for data at rest", "DP", "CRITICAL", "Automated scan", "OBL-D-01.1-001", "NFR-CONF-001"),
        ("FR-DP-002", "Implement TLS 1.3 for data in transit", "DP", "CRITICAL", "Network scan", "OBL-D-01.2-001", "NFR-CONF-002"),
        ("FR-DP-003", "Implement data deletion on user request", "DP", "CRITICAL", "Automated test", "OBL-D-05.3-001", "NFR-PRIV-003"),
        ("FR-DP-004", "Implement data export in JSON format", "DP", "HIGH", "Automated test", "OBL-D-05.4-001", "NFR-PRIV-004"),
        ("FR-DP-005", "Implement data retention policy enforcement", "DP", "HIGH", "Automated test", "OBL-D-05.2-001", "NFR-PRIV-002"),
        ("FR-DP-006", "Implement consent management", "DP", "HIGH", "Manual test", "OBL-D-05.1-001", "NFR-PRIV-006"),
        ("FR-DP-007", "Implement privacy notice display", "DP", "HIGH", "Manual test", "OBL-D-09.1-001", "NFR-PRIV-005"),
        ("FR-DP-008", "Implement data minimization checks", "DP", "HIGH", "Code review", "OBL-D-05.1-001", "NFR-PRIV-001"),
        ("FR-DP-009", "Implement backup encryption", "DP", "MODERATE", "Automated scan", "OBL-D-01.1-001", "NFR-CONF-006"),
        ("FR-DP-010", "Implement audit logging", "DP", "HIGH", "Automated test", "OBL-D-10.2-001", "NFR-INT-003"),
        ("FR-DP-011", "Implement data integrity checksums", "DP", "HIGH", "Automated test", "OBL-D-01.4-001", "NFR-INT-004"),
        ("FR-DP-012", "Implement log sanitization to remove PII", "DP", "MODERATE", "Automated scan", "OBL-D-10.2-001", "NFR-CONF-007"),
        # Security (15)
        ("FR-SEC-001", "Implement vulnerability scanning in CI/CD", "SEC", "HIGH", "Automated test", "OBL-D-02.1-001", "NFR-COMP-005"),
        ("FR-SEC-002", "Implement automated security updates", "SEC", "HIGH", "Manual test", "OBL-D-02.2-001", "NFR-INT-002"),
        ("FR-SEC-003", "Implement rate limiting", "SEC", "HIGH", "Load test", "OBL-D-04.1-001", "NFR-AVAIL-003"),
        ("FR-SEC-004", "Implement input validation", "SEC", "CRITICAL", "Automated test", "OBL-D-03.4-001", "NFR-INT-001"),
        ("FR-SEC-005", "Implement output encoding", "SEC", "HIGH", "Automated test", "OBL-D-03.4-001", "NFR-INT-001"),
        ("FR-SEC-006", "Implement CSRF protection", "SEC", "HIGH", "Automated test", "OBL-D-03.4-001", "NFR-INT-001"),
        ("FR-SEC-007", "Implement secure error handling", "SEC", "HIGH", "Manual test", "OBL-D-03.4-001", "NFR-ACC-002"),
        ("FR-SEC-008", "Implement security headers", "SEC", "MODERATE", "Automated scan", "OBL-D-03.4-001", "NFR-CONF-002"),
        ("FR-SEC-009", "Implement secret management", "SEC", "HIGH", "Automated scan", "OBL-D-01.3-001", "NFR-CONF-004"),
        ("FR-SEC-010", "Implement dependency vulnerability checking", "SEC", "HIGH", "Automated test", "OBL-D-02.1-001", "NFR-INT-007"),
        ("FR-SEC-011", "Implement circuit breakers", "SEC", "MODERATE", "Chaos test", "OBL-D-04.1-001", "NFR-AVAIL-004"),
        ("FR-SEC-012", "Implement health check endpoints", "SEC", "MODERATE", "Automated test", "OBL-D-04.2-001", "NFR-AVAIL-001"),
        ("FR-SEC-013", "Implement breach detection and alerting", "SEC", "CRITICAL", "Manual test", "OBL-D-04.3-001", "NFR-COMP-006"),
        ("FR-SEC-014", "Implement SBOM generation", "SEC", "HIGH", "Automated test", "OBL-D-06.2-001", "NFR-COMP-008"),
        ("FR-SEC-015", "Implement file integrity monitoring", "SEC", "MODERATE", "Automated scan", "OBL-D-01.4-001", "NFR-INT-005"),
        # Development (10)
        ("FR-DEV-001", "Implement secure coding standards", "DEV", "HIGH", "Code review", "OBL-D-07.1-001", "NFR-COMP-002"),
        ("FR-DEV-002", "Implement code review process", "DEV", "HIGH", "Process audit", "OBL-D-07.1-001", "NFR-COMP-002"),
        ("FR-DEV-003", "Implement static analysis in CI/CD", "DEV", "HIGH", "Automated test", "OBL-D-02.1-001", "NFR-COMP-005"),
        ("FR-DEV-004", "Implement dynamic analysis in CI/CD", "DEV", "HIGH", "Automated test", "OBL-D-02.1-001", "NFR-COMP-005"),
        ("FR-DEV-005", "Implement threat modeling in design", "DEV", "HIGH", "Manual review", "OBL-D-07.1-001", "NFR-COMP-002"),
        ("FR-DEV-006", "Implement privacy review in design", "DEV", "HIGH", "Manual review", "OBL-D-07.1-001", "NFR-PRIV-009"),
        ("FR-DEV-007", "Implement DPIA workflow", "DEV", "HIGH", "Manual test", "OBL-D-09.2-001", "NFR-PRIV-007"),
        ("FR-DEV-008", "Implement security documentation", "DEV", "MODERATE", "Manual review", "OBL-D-09.1-001", "NFR-COMP-004"),
        ("FR-DEV-009", "Implement OpenAPI documentation", "DEV", "MODERATE", "Automated validation", "OBL-D-09.1-001", "NFR-ACC-005"),
        ("FR-DEV-010", "Implement change management process", "DEV", "HIGH", "Process audit", "OBL-D-07.1-001", "NFR-COMP-002"),
        # Governance (10)
        ("FR-GOV-001", "Implement privacy policy page", "GOV", "HIGH", "Manual test", "OBL-D-09.1-001", "NFR-PRIV-005"),
        ("FR-GOV-002", "Implement terms of service", "GOV", "MODERATE", "Manual test", "OBL-D-09.1-001", "NFR-COMP-001"),
        ("FR-GOV-003", "Implement processing activity registry", "GOV", "HIGH", "Manual test", "OBL-D-09.4-001", "NFR-PRIV-008"),
        ("FR-GOV-004", "Implement vulnerability disclosure page", "GOV", "HIGH", "Manual test", "OBL-D-02.3-001", "NFR-COMP-003"),
        ("FR-GOV-005", "Implement incident response workflow", "GOV", "HIGH", "Manual test", "OBL-D-04.3-001", "NFR-COMP-006"),
        ("FR-GOV-006", "Implement compliance dashboard", "GOV", "MODERATE", "Manual test", "OBL-D-09.1-001", "NFR-COMP-009"),
        ("FR-GOV-007", "Implement training tracking", "GOV", "MODERATE", "Manual test", "OBL-D-08.1-001", "NFR-COMP-007"),
        ("FR-GOV-008", "Implement vendor assessment workflow", "GOV", "MODERATE", "Manual test", "OBL-D-06.1-001", "NFR-PRIV-010"),
        ("FR-GOV-009", "Implement data processing agreements", "GOV", "HIGH", "Manual test", "OBL-D-06.3-001", "NFR-PRIV-010"),
        ("FR-GOV-010", "Implement compliance gate checks", "GOV", "CRITICAL", "Automated test", "OBL-D-09.1-001", "NFR-COMP-009"),
        # Training (3)
        ("FR-TRN-001", "Implement security awareness training module", "TRN", "HIGH", "Manual test", "OBL-D-08.1-001", "NFR-COMP-007"),
        ("FR-TRN-002", "Implement role-based training tracks", "TRN", "MODERATE", "Manual test", "OBL-D-08.2-001", "NFR-COMP-007"),
        ("FR-TRN-003", "Implement training completion tracking", "TRN", "MODERATE", "Manual test", "OBL-D-08.1-001", "NFR-COMP-007")
    ]
    
    count = 0
    for fr_id, desc, domain, priority, verification, source_obl, source_nfr in frs:
        cypher = """
        CREATE (f:FR {
            frId: $frId,
            description: $description,
            domain: $domain,
            priority: $priority,
            verificationMethod: $verificationMethod,
            sourceObligations: $sourceObligations,
            sourceNFRs: $sourceNFRs
        })
        RETURN count(f)
        """
        params = {
            "frId": fr_id,
            "description": desc,
            "domain": domain,
            "priority": priority,
            "verificationMethod": verification,
            "sourceObligations": source_obl,
            "sourceNFRs": source_nfr
        }
        if exec_cypher(cypher, params) > 0:
            count += 1
    
    print(f"  ✓ Created {count} FRs")
    return count

def create_fr_relationships():
    """Create FR to NFR and FR to Obligation relationships"""
    print("\n" + "=" * 60)
    print("  Creating FR Relationships")
    print("=" * 60)
    
    # FR satisfies NFR
    cypher = """
    MATCH (f:FR), (n:NFR)
    WHERE f.sourceNFRs = n.nfrId
    MERGE (f)-[:SATISFIES_NFR]->(n)
    RETURN count(DISTINCT f) AS frsLinked
    """
    result = exec_cypher(cypher)
    print(f"  ✓ Created SATISFIES_NFR for {result} FRs")
    
    # FR derived from Obligation
    cypher = """
    MATCH (f:FR), (o:Obligation)
    WHERE f.sourceObligations = o.obligationId
    MERGE (f)-[:DERIVED_FROM_OBLIGATION]->(o)
    RETURN count(DISTINCT f) AS frsLinked
    """
    result = exec_cypher(cypher)
    print(f"  ✓ Created DERIVED_FROM_OBLIGATION for {result} FRs")
    
    return result

def load_threats():
    """Load Threats from TinyTask (STRIDE + LINDDUN)"""
    print("\n" + "=" * 60)
    print("  Loading Phase 3: Threats")
    print("=" * 60)
    
    threats = [
        # STRIDE (35 threats - sample of key ones)
        ("STRIDE-001", "Attacker spoofs user identity via stolen credentials", "SPOOFING", "STRIDE", "Credential theft", "Authentication system"),
        ("STRIDE-002", "Attacker spoofs system identity via phishing", "SPOOFING", "STRIDE", "Phishing attack", "User interface"),
        ("STRIDE-003", "Attacker tampers with user data in database", "TAMPERING", "STRIDE", "SQL injection", "Database"),
        ("STRIDE-004", "Attacker tampers with data in transit", "TAMPERING", "STRIDE", "Man-in-the-middle", "Network"),
        ("STRIDE-005", "Attacker tampers with application code", "TAMPERING", "STRIDE", "Supply chain attack", "Application"),
        ("STRIDE-006", "User denies performing an action", "REPUDIATION", "STRIDE", "Insufficient logging", "Audit logs"),
        ("STRIDE-007", "System fails to log critical events", "REPUDIATION", "STRIDE", "Logging failure", "Audit logs"),
        ("STRIDE-008", "Attacker accesses personal data via SQL injection", "INFO_DISCLOSURE", "STRIDE", "SQL injection", "Database"),
        ("STRIDE-009", "Attacker intercepts data in transit", "INFO_DISCLOSURE", "STRIDE", "Network sniffing", "Network"),
        ("STRIDE-010", "Attacker accesses backup data", "INFO_DISCLOSURE", "STRIDE", "Backup breach", "Backup system"),
        ("STRIDE-011", "Insider leaks personal data", "INFO_DISCLOSURE", "STRIDE", "Malicious insider", "Database"),
        ("STRIDE-012", "Attacker causes denial of service via resource exhaustion", "DoS", "STRIDE", "Resource exhaustion", "API"),
        ("STRIDE-013", "Attacker causes denial of service via flood", "DoS", "STRIDE", "DDoS attack", "Network"),
        ("STRIDE-014", "System becomes unavailable due to failure", "DoS", "STRIDE", "System failure", "Application"),
        ("STRIDE-015", "Attacker elevates privileges via injection", "ELEVATION_OF_PRIVILEGE", "STRIDE", "Code injection", "Application"),
        ("STRIDE-016", "Attacker elevates privileges via misconfiguration", "ELEVATION_OF_PRIVILEGE", "STRIDE", "Misconfiguration", "Configuration"),
        ("STRIDE-017", "User accesses admin functions via broken access control", "ELEVATION_OF_PRIVILEGE", "STRIDE", "Broken access control", "Authorization"),
        # LINDDUN (7 threats)
        ("LINDDUN-001", "Linkability: Correlate user actions across sessions", "LINKABILITY", "LINDDUN", "Session correlation", "Session management"),
        ("LINDDUN-002", "Identifiability: Identify user from anonymized data", "IDENTIFIABILITY", "LINDDUN", "Data correlation", "Database"),
        ("LINDDUN-003", "Non-repudiation: Prove user performed action", "NON_REPUDIATION", "LINDDUN", "Insufficient anonymity", "Audit logs"),
        ("LINDDUN-004", "Detectability: Detect user presence in system", "DETECTABILITY", "LINDDUN", "Presence detection", "Network"),
        ("LINDDUN-005", "Unidentifiability: Cannot verify user identity when needed", "UNIDENTIFIABILITY", "LINDDUN", "Identity verification failure", "Authentication"),
        ("LINDDUN-006", "Unlinkability: Cannot link related data when legally required", "UNLINKABILITY", "LINDDUN", "Legal compliance failure", "Database"),
        ("LINDDUN-007", "Linkability: Correlate data across different processing activities", "LINKABILITY", "LINDDUN", "Data aggregation", "Database")
    ]
    
    count = 0
    for threat_id, desc, category, framework, vector, component in threats:
        cypher = """
        CREATE (t:Threat {
            threatId: $threatId,
            description: $description,
            category: $category,
            framework: $framework,
            attackVector: $attackVector,
            affectedComponents: $affectedComponents
        })
        RETURN count(t)
        """
        params = {
            "threatId": threat_id,
            "description": desc,
            "category": category,
            "framework": framework,
            "attackVector": vector,
            "affectedComponents": component
        }
        if exec_cypher(cypher, params) > 0:
            count += 1
    
    print(f"  ✓ Created {count} threats")
    return count

def load_risks():
    """Load Risks from TinyTask"""
    print("\n" + "=" * 60)
    print("  Loading Phase 3: Risks")
    print("=" * 60)
    
    risks = [
        ("RISK-001", "SQL injection leading to data breach", "STRIDE-008", "VULN-001", "LIKELY", "CATASTROPHIC", "CRITICAL", "LOW", "MITIGATE", "Mitigated by FR-SEC-004 input validation"),
        ("RISK-002", "Credential theft enabling unauthorized access", "STRIDE-001", "VULN-002", "LIKELY", "HIGH", "HIGH", "LOW", "MITIGATE", "Mitigated by FR-IAM-002, FR-IAM-003"),
        ("RISK-003", "DoS attack causing service outage", "STRIDE-012", "VULN-003", "POSSIBLE", "HIGH", "HIGH", "LOW", "MITIGATE", "Mitigated by FR-SEC-003 rate limiting"),
        ("RISK-004", "Data breach via network interception", "STRIDE-009", "VULN-004", "UNLIKELY", "CATASTROPHIC", "HIGH", "LOW", "MITIGATE", "Mitigated by FR-DP-002 TLS 1.3"),
        ("RISK-005", "Insider threat leaking personal data", "STRIDE-011", "VULN-005", "POSSIBLE", "HIGH", "HIGH", "LOW", "MITIGATE", "Mitigated by FR-IAM-004 RBAC, FR-DP-010 audit"),
        ("RISK-006", "Backup data breach", "STRIDE-010", "VULN-006", "UNLIKELY", "HIGH", "MODERATE", "LOW", "ACCEPT", "Backups encrypted, access restricted"),
        ("RISK-007", "Third-party dependency vulnerability", "STRIDE-005", "VULN-007", "LIKELY", "MODERATE", "HIGH", "LOW", "MITIGATE", "Mitigated by FR-SEC-010 dependency checking"),
        ("RISK-008", "Breach notification delay", "STRIDE-007", "VULN-008", "POSSIBLE", "HIGH", "HIGH", "LOW", "MITIGATE", "Mitigated by FR-SEC-013 breach detection"),
        ("RISK-009", "Privilege escalation via misconfiguration", "STRIDE-016", "VULN-009", "POSSIBLE", "HIGH", "HIGH", "LOW", "MITIGATE", "Mitigated by FR-SEC-008 security headers"),
        ("RISK-010", "Data linkability across processing activities", "LINDDUN-007", "VULN-010", "POSSIBLE", "MODERATE", "MODERATE", "LOW", "ACCEPT", "Data minimization reduces correlation risk")
    ]
    
    count = 0
    for risk_id, desc, threat_id, vuln_id, likelihood, impact, level, residual, decision, justification in risks:
        cypher = """
        CREATE (r:Risk {
            riskId: $riskId,
            description: $description,
            threatId: $threatId,
            vulnerabilityId: $vulnerabilityId,
            likelihood: $likelihood,
            impact: $impact,
            riskLevel: $riskLevel,
            residualRisk: $residualRisk,
            decision: $decision,
            justification: $justification
        })
        RETURN count(r)
        """
        params = {
            "riskId": risk_id,
            "description": desc,
            "threatId": threat_id,
            "vulnerabilityId": vuln_id,
            "likelihood": likelihood,
            "impact": impact,
            "riskLevel": level,
            "residualRisk": residual,
            "decision": decision,
            "justification": justification
        }
        if exec_cypher(cypher, params) > 0:
            count += 1
    
    print(f"  ✓ Created {count} risks")
    return count

def load_mitigations():
    """Load Mitigation Controls from TinyTask"""
    print("\n" + "=" * 60)
    print("  Loading Phase 3: Mitigations")
    print("=" * 60)
    
    mitigations = [
        ("MIT-001", "Input validation and parameterized queries", "NEW_FUNCTIONAL_NODE", "RISK-001", "IMPLEMENTED", "HIGH"),
        ("MIT-002", "Multi-factor authentication", "STRENGTHEN_EXISTING", "RISK-002", "IMPLEMENTED", "HIGH"),
        ("MIT-003", "Rate limiting and DDoS protection", "NEW_FUNCTIONAL_NODE", "RISK-003", "IMPLEMENTED", "HIGH"),
        ("MIT-004", "TLS 1.3 encryption for all communications", "STRENGTHEN_EXISTING", "RISK-004", "IMPLEMENTED", "HIGH"),
        ("MIT-005", "RBAC with audit logging", "NEW_FUNCTIONAL_NODE", "RISK-005", "IMPLEMENTED", "HIGH"),
        ("MIT-006", "Automated dependency vulnerability scanning", "NEW_FUNCTIONAL_NODE", "RISK-007", "IMPLEMENTED", "MODERATE"),
        ("MIT-007", "Automated breach detection and alerting", "NEW_FUNCTIONAL_NODE", "RISK-008", "IMPLEMENTED", "HIGH"),
        ("MIT-008", "Security configuration hardening", "ARCHITECTURAL_CHANGE", "RISK-009", "IMPLEMENTED", "MODERATE")
    ]
    
    count = 0
    for mit_id, desc, strategy, risk_id, status, effectiveness in mitigations:
        cypher = """
        CREATE (m:Mitigation {
            mitigationId: $mitigationId,
            description: $description,
            strategy: $strategy,
            riskId: $riskId,
            status: $status,
            effectivenessRating: $effectivenessRating
        })
        RETURN count(m)
        """
        params = {
            "mitigationId": mit_id,
            "description": desc,
            "strategy": strategy,
            "riskId": risk_id,
            "status": status,
            "effectivenessRating": effectiveness
        }
        if exec_cypher(cypher, params) > 0:
            count += 1
    
    print(f"  ✓ Created {count} mitigations")
    return count

def create_risk_relationships():
    """Create relationships between threats, risks, and mitigations"""
    print("\n" + "=" * 60)
    print("  Creating Risk Relationships")
    print("=" * 60)
    
    # Risk informed by Threat
    cypher = """
    MATCH (r:Risk), (t:Threat {threatId: r.threatId})
    MERGE (t)-[:INFORMS_RISK]->(r)
    RETURN count(DISTINCT r) AS risksLinked
    """
    result1 = exec_cypher(cypher)
    print(f"  ✓ Created INFORMS_RISK for {result1} risks")
    
    # Risk generates Mitigation
    cypher = """
    MATCH (r:Risk), (m:Mitigation {riskId: r.riskId})
    MERGE (r)-[:GENERATES_MITIGATION]->(m)
    RETURN count(DISTINCT r) AS risksLinked
    """
    result2 = exec_cypher(cypher)
    print(f"  ✓ Created GENERATES_MITIGATION for {result2} risks")
    
    # Mitigation addresses Vulnerability (via risk)
    cypher = """
    MATCH (m:Mitigation), (r:Risk {riskId: m.riskId})
    MERGE (m)-[:ADDRESSES_RISK]->(r)
    RETURN count(DISTINCT m) AS mitigationsLinked
    """
    result3 = exec_cypher(cypher)
    print(f"  ✓ Created ADDRESSES_RISK for {result3} mitigations")
    
    return result3

def verify_phase3():
    """Verify Phase 3 data loading"""
    print("\n" + "=" * 60)
    print("  Phase 3 Verification")
    print("=" * 60)
    
    cypher = """
    MATCH (n)
    WHERE n:NFR OR n:FR OR n:Threat OR n:Risk OR n:Mitigation
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
    
    # Count Phase 3 relationships
    cypher = """
    MATCH ()-[r]->()
    WHERE type(r) IN ['SATISFIES_NFR', 'DERIVED_FROM_OBLIGATION', 'INFORMS_RISK', 
                       'GENERATES_MITIGATION', 'ADDRESSES_RISK']
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
    
    print(f"\n  TOTAL PHASE 3 NODES: {total}")
    print(f"  TOTAL PHASE 3 RELATIONSHIPS: {total_rels}")
    return total, total_rels

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

def main():
    print("=" * 60)
    print("  AEGIS Phase 3 Knowledge Graph - ETL")
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
    
    # Load Phase 3 data
    load_nfrs()
    load_fr()
    create_fr_relationships()
    
    load_threats()
    load_risks()
    load_mitigations()
    create_risk_relationships()
    
    # Verify
    verify_phase3()
    
    print("\n" + "=" * 60)
    print("  ✓ Phase 3 ETL Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
