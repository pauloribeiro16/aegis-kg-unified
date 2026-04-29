import os
#!/usr/bin/env python3
"""
Create Clause → SubDomain relationships based on AEGIS Phase 1 clause mapping.
Derived from the 06_Clause_Mapping_Matrix.xlsx for TinyTask SaaS.
"""
import requests

NEO4J_HTTP = "http://localhost:7474"
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", ""))

def exec_cypher(statement):
    payload = {"statements": [{"statement": statement}]}
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
        print(f"  Error: {result['errors'][0].get('message', '')[:200]}")
        return 0
    # Get the count of created relationships
    counters = result.get('results', [{}])[0].get('data', [{}])[0].get('row', [0])
    return counters[0] if counters else 0

# Clause → SubDomain mapping for TinyTask (GDPR + CRA)
# Derived from Phase 1 Clause Mapping Matrix
CLAUSE_SUBDOMAIN_MAP = {
    # GDPR Article 32 (Security of Processing) → D-01 (Data Protection), D-02 (Vuln Mgmt), D-04 (Incident), D-10 (Monitoring)
    'GDPR-32-1-a': 'D-01.1',  # Encryption → Encryption
    'GDPR-32-1-b': 'D-01.2',  # Confidentiality → Access Control
    'GDPR-32-1-c': 'D-02.1',  # Restore availability → Incident Response
    'GDPR-32-1-d': 'D-10.1',  # Testing effectiveness → Monitoring & Audit
    'GDPR-32-1-e': 'D-05.1',  # Data minimisation → Data Lifecycle
    'GDPR-32-2':   'D-01.3',  # Privacy by design → Privacy Engineering
    'GDPR-32-3':   'D-09.1',  # Records of processing → Governance
    'GDPR-32-4':   'D-09.2',  # DPO → Governance
    'GDPR-32-5':   'D-01.4',  # DPIA → Risk Assessment

    # GDPR Article 25 (Data Protection by Design) → D-01
    'GDPR-25-1': 'D-01.3',  # By design → Privacy Engineering
    'GDPR-25-2': 'D-05.1',  # By default → Data Minimisation

    # GDPR Article 17 (Data Subject Rights) → D-03 (Access Control), D-05 (Data Lifecycle)
    'GDPR-17-1': 'D-03.1',  # Right to access → Identity & Access
    'GDPR-17-2': 'D-03.2',  # Right to rectification → Access Management
    'GDPR-17-3': 'D-05.3',  # Right to erasure → Data Retention
    'GDPR-17-4': 'D-05.3',  # Erasure notification → Data Retention

    # GDPR Article 13 (Information to be provided) → D-09 (Governance)
    'GDPR-13-5': 'D-09.1',  # Transparency → Governance
    'GDPR-13-6': 'D-09.1',  # Privacy notice → Governance
    'GDPR-13-7': 'D-09.1',  # Information obligations → Governance

    # GDPR Article 7 (Conditions for consent) → D-03 (Access Control)
    'GDPR-7-1': 'D-03.3',   # Consent conditions → Consent Management
    'GDPR-7-2': 'D-03.3',   # Demonstrate consent → Consent Management
    'GDPR-7-3': 'D-03.3',   # Withdraw consent → Consent Management
    'GDPR-7-4': 'D-05.2',   # Consent for children → Data Classification

    # GDPR Article 16 (Right to rectification) → D-03
    'GDPR-16-1': 'D-03.2',  # Rectification → Access Management
    'GDPR-16-2': 'D-03.2',  # Notification of rectification → Access Management

    # GDPR Article 33 (Breach notification) → D-04 (Incident Response)
    'GDPR-33-1': 'D-04.1',  # 72h notification → Incident Detection
    'GDPR-33-2': 'D-04.2',  # Documentation → Incident Documentation

    # GDPR Article 15 (Right of access) → D-03
    'GDPR-15-1': 'D-03.1',  # Access confirmation → Identity & Access
    'GDPR-15-2': 'D-03.1',  # Access to data → Identity & Access

    # GDPR Article 24 (Responsibility of controller) → D-09 (Governance)
    'GDPR-24-1': 'D-09.1',  # Controller responsibility → Governance
    'GDPR-24-2': 'D-09.1',  # Appropriate measures → Governance

    # GDPR Article 19 (Notification obligation) → D-04
    'GDPR-19-1': 'D-04.3',  # Notification to recipients → Incident Communication

    # GDPR Article 5 (Principles) → D-05 (Data Lifecycle)
    'GDPR-5-1': 'D-05.1',  # Lawfulness, fairness → Data Collection
    'GDPR-5-2': 'D-05.1',  # Purpose limitation → Data Collection
    'GDPR-5-3': 'D-05.2',  # Data minimisation → Data Classification
    'GDPR-5-4': 'D-05.3',  # Accuracy → Data Retention

    # GDPR Article 28 (Processor) → D-06 (Supply Chain)
    'GDPR-28-1': 'D-06.1',  # Processor selection → Supplier Assessment
    'GDPR-28-2': 'D-06.2',  # Processor contract → Supplier Contract

    # GDPR Article 14 (Information when not obtained from data subject) → D-09
    'GDPR-14-1': 'D-09.1',  # Information obligations → Governance
    'GDPR-14-2': 'D-09.1',  # Transparency → Governance
    'GDPR-14-3': 'D-09.1',  # Privacy notice → Governance
    'GDPR-14-4': 'D-09.1',  # Timing of information → Governance

    # GDPR Article 11 (Identification) → D-03
    'GDPR-11-1': 'D-03.1',  # Identification processes → Identity & Access
    'GDPR-11-2': 'D-03.1',  # Additional information → Identity & Access

    # GDPR Article 20 (Data portability) → D-05
    'GDPR-20-1': 'D-05.4',  # Portability right → Data Portability
    'GDPR-20-2': 'D-05.4',  # Transfer between controllers → Data Portability

    # CRA Annex I (Security objectives) → D-02 (Vulnerability Management), D-07 (Secure Development)
    'CRA-AnnexI-1': 'D-02.1',  # Vulnerability handling → Vulnerability Identification
    'CRA-AnnexI-2': 'D-07.1',  # Security by design → Secure SDLC
    'CRA-AnnexI-3': 'D-02.2',  # Patch management → Patch Management
    'CRA-AnnexI-4': 'D-07.4',  # Update mechanisms → Secure Deployment

    # CRA Annex II (Essential cybersecurity requirements) → D-02, D-07
    'CRA-AnnexII-1': 'D-02.3',  # Protection against vulnerabilities → Vulnerability Assessment
    'CRA-AnnexII-2': 'D-07.1',  # Secure development → Secure SDLC
    'CRA-AnnexII-3': 'D-02.2',  # Incident detection → Patch Management

    # CRA Annex III (Conformity assessment) → D-09 (Governance)
    'CRA-AnnexIII-1': 'D-09.3',  # Conformity assessment → Compliance Audit
    'CRA-AnnexIII-2': 'D-09.3',  # Technical documentation → Compliance Documentation
    'CRA-AnnexIII-3': 'D-09.4',  # Post-market monitoring → Compliance Monitoring
}


def create_clause_subdomain_relationships():
    """Create COVERS_SUBDOMAIN relationships for all clauses"""
    print("=" * 60)
    print("  Creating Clause → SubDomain Relationships")
    print("=" * 60)

    count = 0
    errors = 0

    for clause_id, subdomain_id in CLAUSE_SUBDOMAIN_MAP.items():
        cypher = f"""
        MATCH (c:Clause {{clauseId: '{clause_id}'}})
        MATCH (sd:SubDomain {{subDomainId: '{subdomain_id}'}})
        CREATE (c)-[:COVERS_SUBDOMAIN {{weight: 1.0, source: 'ARM_PHASE1_MAPPING'}}]->(sd)
        RETURN count(*) AS created
        """
        payload = {"statements": [{"statement": cypher}]}
        response = requests.post(
            f"{NEO4J_HTTP}/db/neo4j/tx/commit",
            auth=AUTH,
            json=payload,
            timeout=30
        )
        if response.status_code == 200 and not response.json().get('errors'):
            count += 1
            print(f"  ✓ {clause_id} → {subdomain_id}")
        else:
            errors += 1
            print(f"  ✗ {clause_id} → {subdomain_id} (FAILED)")

    print(f"\n  Total created: {count}/{len(CLAUSE_SUBDOMAIN_MAP)}")
    print(f"  Errors: {errors}")
    return count


def verify_relationships():
    """Verify all COVERS_SUBDOMAIN relationships"""
    cypher = """
    MATCH (c:Clause)-[r:COVERS_SUBDOMAIN]->(sd:SubDomain)
    RETURN count(DISTINCT c) AS clausesWithCoverage,
           count(DISTINCT sd) AS subdomainsCovered,
           count(r) AS totalRelationships
    """
    payload = {"statements": [{"statement": cypher}]}
    response = requests.post(
        f"{NEO4J_HTTP}/db/neo4j/tx/commit",
        auth=AUTH,
        json=payload,
        timeout=30
    )
    if response.status_code == 200:
        data = response.json().get('results', [{}])[0].get('data', [{}])[0]
        row = data.get('row', [])
        if row:
            print(f"\n  Verification: {row[0]} clauses, {row[1]} sub-domains, {row[2]} relationships")
            return True
    return False


if __name__ == "__main__":
    create_clause_subdomain_relationships()
    verify_relationships()
