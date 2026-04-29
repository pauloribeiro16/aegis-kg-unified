import os
#!/usr/bin/env python3
"""
Create SubDomain mappings for NIS2, DORA, and AI Act clauses.
Maps new clauses to the appropriate AEGIS SubDomains.
"""
import requests

NEO4J_HTTP = "http://localhost:7474"
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", ""))

def exec_cypher(statement, params=None):
    """Execute a Cypher query"""
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}
    try:
        response = requests.post(f"{NEO4J_HTTP}/db/neo4j/tx/commit", auth=AUTH, json=payload, timeout=30)
        if response.status_code != 200:
            return 0
        result = response.json()
        if result.get('errors'):
            return 0
        try:
            data = result.get('results', [{}])[0].get('data', [{}])[0].get('row', [0])
            return data[0] if data else 0
        except:
            return 0
    except:
        return 0

def create_subdomain_mappings():
    """Create COVERS_SUBDOMAIN relationships for NIS2, DORA, AI Act clauses"""
    print("\n" + "=" * 60)
    print("  Creating SubDomain Mappings for NIS2, DORA, AI Act")
    print("=" * 60)
    
    # NIS2 clause → SubDomain mappings
    nis2_mappings = [
        ("NIS2-21-1", "D-02.1"),  # Risk analysis → Vulnerability Identification
        ("NIS2-21-2", "D-04.1"),  # Incident handling → Incident Detection
        ("NIS2-21-3", "D-04.2"),  # Business continuity → Incident Response
        ("NIS2-21-4", "D-06.1"),  # Supply chain security → Supplier Assessment
        ("NIS2-21-5", "D-07.1"),  # Security in acquisition → Secure SDLC
        ("NIS2-21-6", "D-10.3"),  # Effectiveness assessment → Security Testing
        ("NIS2-21-7", "D-08.1"),  # Basic cyber hygiene → Security Awareness
        ("NIS2-21-8", "D-01.1"),  # Encryption → Encryption at Rest
        ("NIS2-20-1", "D-09.1"),  # Management approval → Security Policies
        ("NIS2-20-2", "D-09.1"),  # Management oversight → Security Policies
        ("NIS2-20-3", "D-08.2"),  # Management training → Role-Based Training
        ("NIS2-23-1", "D-04.3"),  # 24h notification → Breach Notification
        ("NIS2-23-2", "D-04.2"),  # Incident notification → Incident Documentation
        ("NIS2-23-3", "D-04.4"),  # Final reports → Lessons Learned
    ]
    
    count = 0
    for clause_id, sd_id in nis2_mappings:
        cypher = """
        MATCH (c:Clause {clauseId: $clauseId})
        MATCH (sd:SubDomain {subDomainId: $sdId})
        CREATE (c)-[:COVERS_SUBDOMAIN {weight: 1.0, source: 'ARM_NIS2_MAPPING'}]->(sd)
        RETURN count(*)
        """
        params = {"clauseId": clause_id, "sdId": sd_id}
        if exec_cypher(cypher, params) > 0:
            count += 1
    
    print(f"  ✓ Created {count} NIS2 → SubDomain mappings")
    
    # DORA clause → SubDomain mappings
    dora_mappings = [
        ("DORA-9-1", "D-09.1"),   # ICT risk management → Security Policies
        ("DORA-9-2", "D-09.1"),   # ICT governance → Security Policies
        ("DORA-9-3", "D-09.1"),   # ICT asset identification → Security Policies
        ("DORA-9-4", "D-09.2"),   # ICT risk assessment → Risk Assessment
        ("DORA-9-5", "D-07.1"),   # ICT mitigation → Secure SDLC
        ("DORA-9-6", "D-01.1"),   # Backup and recovery → Encryption at Rest
        ("DORA-15-1", "D-10.1"),  # Incident detection → Security Monitoring
        ("DORA-15-2", "D-04.1"),  # Incident classification → Incident Detection
        ("DORA-15-3", "D-04.3"),  # Incident reporting → Breach Notification
        ("DORA-15-4", "D-04.1"),  # Incident response → Incident Detection
        ("DORA-19-1", "D-10.3"),  # Resilience testing → Security Testing
        ("DORA-19-2", "D-02.1"),  # Vulnerability assessment → Vulnerability Identification
        ("DORA-19-3", "D-07.3"),  # TLPT → Independent Security Testing
    ]
    
    for clause_id, sd_id in dora_mappings:
        cypher = """
        MATCH (c:Clause {clauseId: $clauseId})
        MATCH (sd:SubDomain {subDomainId: $sdId})
        CREATE (c)-[:COVERS_SUBDOMAIN {weight: 1.0, source: 'ARM_DORA_MAPPING'}]->(sd)
        RETURN count(*)
        """
        params = {"clauseId": clause_id, "sdId": sd_id}
        if exec_cypher(cypher, params) > 0:
            count += 1
    
    print(f"  ✓ Created {count} total NIS2+DORA → SubDomain mappings")
    
    # AI Act clause → SubDomain mappings
    ai_mappings = [
        ("AI-9-1", "D-09.2"),    # Risk management → Risk Assessment
        ("AI-9-2", "D-09.2"),    # Risk identification → Risk Assessment
        ("AI-9-3", "D-09.2"),    # Risk evaluation → Risk Assessment
        ("AI-9-4", "D-09.2"),    # Residual risk → Risk Assessment
        ("AI-9-5", "D-10.3"),    # Testing and feedback → Security Testing
        ("AI-10-1", "D-05.1"),   # Data governance → Data Collection
        ("AI-10-2", "D-05.2"),   # Bias detection → Data Classification
        ("AI-10-3", "D-05.1"),   # Data relevance → Data Collection
        ("AI-10-4", "D-01.1"),   # Data processing → Encryption at Rest
        ("AI-10-5", "D-05.1"),   # Data governance → Data Collection
        ("AI-15-1", "D-07.1"),   # AI accuracy → Secure SDLC
        ("AI-15-2", "D-07.1"),   # AI robustness → Secure SDLC
        ("AI-15-3", "D-01.1"),   # AI cybersecurity → Encryption at Rest
        ("AI-15-4", "D-07.1"),   # Technical solutions → Secure SDLC
        ("AI-20-1", "D-10.2"),   # AI logging → Security Logging
        ("AI-20-2", "D-10.2"),   # Log retention → Security Logging
    ]
    
    for clause_id, sd_id in ai_mappings:
        cypher = """
        MATCH (c:Clause {clauseId: $clauseId})
        MATCH (sd:SubDomain {subDomainId: $sdId})
        CREATE (c)-[:COVERS_SUBDOMAIN {weight: 1.0, source: 'ARM_AI_ACT_MAPPING'}]->(sd)
        RETURN count(*)
        """
        params = {"clauseId": clause_id, "sdId": sd_id}
        if exec_cypher(cypher, params) > 0:
            count += 1
    
    print(f"  ✓ Created {count} total NIS2+DORA+AI Act → SubDomain mappings")
    return count

def verify_coverage():
    """Verify coverage by regulation"""
    print("\n" + "=" * 60)
    print("  Coverage by Regulation")
    print("=" * 60)
    
    cypher = """
    MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)-[:COVERS_SUBDOMAIN]->(sd:SubDomain)
    WITH r.regulationId AS reg, r.name AS name,
         count(DISTINCT c) AS clausesWithCoverage,
         count(DISTINCT sd) AS subDomainsCovered
    RETURN reg, name, clausesWithCoverage, subDomainsCovered
    ORDER BY reg
    """
    
    import requests
    payload = {"statements": [{"statement": cypher}]}
    response = requests.post(f"{NEO4J_HTTP}/db/neo4j/tx/commit", auth=AUTH, json=payload, timeout=30)
    if response.status_code == 200:
        result = response.json()
        if result.get('results') and result['results'][0].get('data'):
            total_clauses = 0
            total_sds = set()
            for row in result['results'][0]['data']:
                reg = row['row'][0]
                name = row['row'][1]
                clauses = row['row'][2]
                sds = row['row'][3]
                total_clauses += clauses
                print(f"  {reg:10s} ({name:10s}): {clauses:3d} clauses → {sds:3d} sub-domains")
            
            print(f"\n  TOTAL: {total_clauses} clauses with SubDomain coverage")
    
    # Overall coverage
    cypher = """
    MATCH (sd:SubDomain)
    WITH count(sd) AS total
    MATCH (sd:SubDomain)<-[:COVERS_SUBDOMAIN]-()
    WITH total, count(DISTINCT sd) AS covered
    RETURN total, covered, round(100.0 * covered / total, 1) AS pct
    """
    payload = {"statements": [{"statement": cypher}]}
    response = requests.post(f"{NEO4J_HTTP}/db/neo4j/tx/commit", auth=AUTH, json=payload, timeout=30)
    if response.status_code == 200:
        result = response.json()
        if result.get('results') and result['results'][0].get('data'):
            row = result['results'][0]['data'][0]['row']
            print(f"\n  Overall: {row[1]}/{row[0]} SubDomains covered ({row[2]}%)")

def main():
    print("=" * 60)
    print("  AEGIS Knowledge Graph - SubDomain Mappings for All Regs")
    print("=" * 60)
    
    # Test connection
    print("\n1. Testing Neo4j connection...")
    try:
        r = requests.get(NEO4J_HTTP, auth=AUTH, timeout=5)
        if r.status_code == 200:
            print(f"   ✓ Neo4j {r.json().get('neo4j_version', 'unknown')}")
        else:
            print(f"   ✗ HTTP {r.status_code}")
            return
    except Exception as e:
        print(f"   ✗ {e}")
        return
    
    create_subdomain_mappings()
    verify_coverage()
    
    print("\n" + "=" * 60)
    print("  ✓ All SubDomain Mappings Complete")
    print("=" * 60)

if __name__ == "__main__":
    import requests
    main()
