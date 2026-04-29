import os
#!/usr/bin/env python3
"""
Load missing regulation clauses for NIS2, DORA, and AI Act into the AEGIS Knowledge Graph.
These regulations exist as nodes but have no clauses loaded.
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

def load_nis2_clauses():
    """Load NIS2 Directive clauses"""
    print("\n" + "=" * 60)
    print("  Loading NIS2 Clauses")
    print("=" * 60)
    
    # NIS2 key articles mapped to AEGIS SubDomains
    articles = [
        ("NIS2-Art21", "NIS2", "21", "Cybersecurity risk management measures", "Essential and important entities shall implement appropriate and proportionate technical, organisational and operational measures", "OPERATIONAL"),
        ("NIS2-Art20", "NIS2", "20", "Corporate cybersecurity governance", "Members of management bodies shall approve cybersecurity risk management measures and oversee their implementation", "GOVERNANCE"),
        ("NIS2-Art23", "NIS2", "23", "Incident notification", "Essential and important entities shall notify without undue delay and in any event within 24 hours", "INCIDENT_RESPONSE"),
    ]
    
    for art_id, reg_id, number, title, summary, obl_type in articles:
        cypher = """
        MATCH (r:Regulation {regulationId: $regId})
        CREATE (a:Article {
            articleId: $articleId,
            number: $number,
            title: $title,
            summary: $summary,
            obligationType: $obligationType
        })
        CREATE (r)-[:HAS_ARTICLE]->(a)
        RETURN count(a)
        """
        params = {
            "articleId": art_id,
            "regId": reg_id,
            "number": number,
            "title": title,
            "summary": summary,
            "obligationType": obl_type
        }
        if exec_cypher(cypher, params) > 0:
            print(f"  ✓ Created Article {art_id}")
    
    # NIS2 clauses
    clauses = [
        ("NIS2-21-1", "NIS2-Art21", "NIS2", "21(1)(a)", "Risk analysis and information system security policies", "All-hazard approach to cybersecurity risk management, including risk analysis", "ESSENTIAL_ENTITY", "CONTINUOUS", 3, True, "NIS2 essential entity", "Art.21(1)(a)", ""),
        ("NIS2-21-2", "NIS2-Art21", "NIS2", "21(1)(b)", "Incident handling", "Incident prevention, detection and response", "ESSENTIAL_ENTITY", "CONTINUOUS", 3, True, "NIS2 essential entity", "Art.21(1)(b)", ""),
        ("NIS2-21-3", "NIS2-Art21", "NIS2", "21(1)(c)", "Business continuity and crisis management", "Business continuity, including backup management and disaster recovery", "ESSENTIAL_ENTITY", "CONTINUOUS", 3, True, "NIS2 essential entity", "Art.21(1)(c)", ""),
        ("NIS2-21-4", "NIS2-Art21", "NIS2", "21(1)(d)", "Supply chain security", "Security of network and information systems in supply chain relationships", "ESSENTIAL_ENTITY", "CONTINUOUS", 3, True, "NIS2 essential entity", "Art.21(1)(d)", ""),
        ("NIS2-21-5", "NIS2-Art21", "NIS2", "21(1)(e)", "Security in acquisition and development", "Security in network and information systems acquisition, development and maintenance", "ESSENTIAL_ENTITY", "CONTINUOUS", 3, True, "NIS2 essential entity", "Art.21(1)(e)", ""),
        ("NIS2-21-6", "NIS2-Art21", "NIS2", "21(1)(f)", "Policies and procedures for effectiveness assessment", "Policies and procedures to assess the effectiveness of cybersecurity risk management measures", "ESSENTIAL_ENTITY", "CONTINUOUS", 3, True, "NIS2 essential entity", "Art.21(1)(f)", ""),
        ("NIS2-21-7", "NIS2-Art21", "NIS2", "21(1)(g)", "Basic cyber hygiene and training", "Use of multi-factor authentication, continuous education and training", "ESSENTIAL_ENTITY", "CONTINUOUS", 3, True, "NIS2 essential entity", "Art.21(1)(g)", ""),
        ("NIS2-21-8", "NIS2-Art21", "NIS2", "21(1)(h)", "Encryption and vulnerability handling", "Use of cryptography and vulnerability handling and disclosure policies", "ESSENTIAL_ENTITY", "CONTINUOUS", 3, True, "NIS2 essential entity", "Art.21(1)(h)", ""),
        ("NIS2-20-1", "NIS2-Art20", "NIS2", "20(1)", "Management body approval of cybersecurity measures", "Management bodies of essential and important entities shall approve cybersecurity risk management measures", "ESSENTIAL_ENTITY", "PERIODIC", 3, True, "NIS2 essential entity", "Art.20(1)", ""),
        ("NIS2-20-2", "NIS2-Art20", "NIS2", "20(2)", "Management body oversight and training", "Management bodies shall oversee implementation and can be held liable for non-compliance", "ESSENTIAL_ENTITY", "CONTINUOUS", 3, True, "NIS2 essential entity", "Art.20(2)", ""),
        ("NIS2-20-3", "NIS2-Art20", "NIS2", "20(3)", "Cybersecurity training for management", "Members of management bodies shall follow specific training to gain knowledge on cybersecurity risks", "ESSENTIAL_ENTITY", "PERIODIC", 3, True, "NIS2 essential entity", "Art.20(3)", ""),
        ("NIS2-23-1", "NIS2-Art23", "NIS2", "23(1)", "Early warning (24h notification)", "Essential and important entities shall notify without undue delay and within 24 hours of becoming aware", "ESSENTIAL_ENTITY", "TRIGGERED", 3, True, "NIS2 essential entity", "Art.23(1)", ""),
        ("NIS2-23-2", "NIS2-Art23", "NIS2", "23(2)", "Incident notification content", "The notification shall include information to enable authorities to determine significance and cross-border impact", "ESSENTIAL_ENTITY", "TRIGGERED", 3, True, "NIS2 essential entity", "Art.23(2)", ""),
        ("NIS2-23-3", "NIS2-Art23", "NIS2", "23(3)", "Intermediate and final reports", "Essential entities shall provide intermediate reports and a final report within one month", "ESSENTIAL_ENTITY", "TRIGGERED", 3, True, "NIS2 essential entity", "Art.23(3)", ""),
    ]
    
    count = 0
    for clause_id, art_id, reg_id, number, summary, desc, party, obl_type, ni, applicable, reason, source, cross_ref in clauses:
        cypher = """
        MATCH (r:Regulation {regulationId: $regId})
        OPTIONAL MATCH (a:Article {articleId: $articleId})
        CREATE (c:Clause {
            clauseId: $clauseId,
            number: $number,
            summary: $summary,
            description: $description,
            obligatedParty: $obligatedParty,
            obligationType: $obligationType,
            normativeIntensity: $normativeIntensity,
            applicable: $applicable,
            applicabilityReason: $applicabilityReason,
            sourceReference: $sourceReference,
            crossReferences: $crossReferences
        })
        CREATE (r)-[:HAS_CLAUSE]->(c)
        FOREACH (x IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END |
            CREATE (a)-[:DEFINES]->(c)
        )
        RETURN count(c)
        """
        params = {
            "clauseId": clause_id,
            "articleId": art_id,
            "regId": reg_id,
            "number": number,
            "summary": summary,
            "description": desc,
            "obligatedParty": party,
            "obligationType": obl_type,
            "normativeIntensity": ni,
            "applicable": applicable,
            "applicabilityReason": reason,
            "sourceReference": source,
            "crossReferences": cross_ref
        }
        if exec_cypher(cypher, params) > 0:
            count += 1
    
    print(f"  ✓ Created {count} NIS2 clauses")
    return count

def load_dora_clauses():
    """Load DORA (Digital Operational Resilience Act) clauses"""
    print("\n" + "=" * 60)
    print("  Loading DORA Clauses")
    print("=" * 60)
    
    articles = [
        ("DORA-Art9", "DORA", "9", "ICT risk management framework", "Financial entities shall have in place a sound, comprehensive and well-documented ICT risk management framework", "OPERATIONAL"),
        ("DORA-Art15", "DORA", "15", "ICT incident management", "Financial entities shall establish and maintain an operational resilience management process", "INCIDENT_RESPONSE"),
        ("DORA-Art19", "DORA", "19", "Resilience testing", "Financial entities shall include in their ICT risk management framework a digital operational resilience testing programme", "TESTING"),
    ]
    
    for art_id, reg_id, number, title, summary, obl_type in articles:
        cypher = """
        MATCH (r:Regulation {regulationId: $regId})
        CREATE (a:Article {
            articleId: $articleId,
            number: $number,
            title: $title,
            summary: $summary,
            obligationType: $obligationType
        })
        CREATE (r)-[:HAS_ARTICLE]->(a)
        RETURN count(a)
        """
        params = {
            "articleId": art_id,
            "regId": reg_id,
            "number": number,
            "title": title,
            "summary": summary,
            "obligationType": obl_type
        }
        if exec_cypher(cypher, params) > 0:
            print(f"  ✓ Created Article {art_id}")
    
    clauses = [
        ("DORA-9-1", "DORA-Art9", "DORA", "9(1)", "ICT risk management policy", "Financial entities shall have in place a sound, comprehensive and well-documented ICT risk management framework", "FINANCIAL_ENTITY", "CONTINUOUS", 3, True, "DORA financial entity", "Art.9(1)", ""),
        ("DORA-9-2", "DORA-Art9", "DORA", "9(2)", "ICT governance and oversight", "Management body shall define, approve and oversee implementation of ICT risk management framework", "FINANCIAL_ENTITY", "CONTINUOUS", 3, True, "DORA financial entity", "Art.9(2)", ""),
        ("DORA-9-3", "DORA-Art9", "DORA", "9(3)", "ICT asset identification", "Financial entities shall identify, classify and appropriately document all ICT assets", "FINANCIAL_ENTITY", "CONTINUOUS", 3, True, "DORA financial entity", "Art.9(3)", ""),
        ("DORA-9-4", "DORA-Art9", "DORA", "9(4)", "ICT risk assessment", "Financial entities shall identify all sources of ICT risk and assess impact and probability", "FINANCIAL_ENTITY", "CONTINUOUS", 3, True, "DORA financial entity", "Art.9(4)", ""),
        ("DORA-9-5", "DORA-Art9", "DORA", "9(5)", "ICT risk mitigation strategies", "Financial entities shall implement appropriate ICT security policies and controls", "FINANCIAL_ENTITY", "CONTINUOUS", 3, True, "DORA financial entity", "Art.9(5)", ""),
        ("DORA-9-6", "DORA-Art9", "DORA", "9(6)", "Backup and recovery", "Financial entities shall develop and document policies for ICT backup and recovery", "FINANCIAL_ENTITY", "CONTINUOUS", 3, True, "DORA financial entity", "Art.9(6)", ""),
        ("DORA-15-1", "DORA-Art15", "DORA", "15(1)", "ICT incident detection and monitoring", "Financial entities shall establish and maintain an ICT incident management process", "FINANCIAL_ENTITY", "CONTINUOUS", 3, True, "DORA financial entity", "Art.15(1)", ""),
        ("DORA-15-2", "DORA-Art15", "DORA", "15(2)", "ICT incident classification", "Financial entities shall establish criteria for classifying ICT-related incidents", "FINANCIAL_ENTITY", "CONTINUOUS", 3, True, "DORA financial entity", "Art.15(2)", ""),
        ("DORA-15-3", "DORA-Art15", "DORA", "15(3)", "ICT incident reporting", "Financial entities shall report major ICT-related incidents to competent authorities", "FINANCIAL_ENTITY", "TRIGGERED", 3, True, "DORA financial entity", "Art.15(3)", ""),
        ("DORA-15-4", "DORA-Art15", "DORA", "15(4)", "Incident response procedures", "Financial entities shall have in place procedures to respond to ICT incidents", "FINANCIAL_ENTITY", "CONTINUOUS", 3, True, "DORA financial entity", "Art.15(4)", ""),
        ("DORA-19-1", "DORA-Art19", "DORA", "19(1)", "Digital operational resilience testing programme", "Financial entities shall include in their ICT risk management framework a testing programme", "FINANCIAL_ENTITY", "PERIODIC", 3, True, "DORA financial entity", "Art.19(1)", ""),
        ("DORA-19-2", "DORA-Art19", "DORA", "19(2)", "Testing based on open source penetration tests", "Financial entities shall perform appropriate tests and vulnerability assessments", "FINANCIAL_ENTITY", "PERIODIC", 3, True, "DORA financial entity", "Art.19(2)", ""),
        ("DORA-19-3", "DORA-Art19", "DORA", "19(3)", "Advanced testing (TLPT)", "Financial entities shall, at least every three years, carry out advanced tests based on threat-led penetration testing", "FINANCIAL_ENTITY", "PERIODIC", 3, True, "DORA financial entity", "Art.19(3)", ""),
    ]
    
    count = 0
    for clause_id, art_id, reg_id, number, summary, desc, party, obl_type, ni, applicable, reason, source, cross_ref in clauses:
        cypher = """
        MATCH (r:Regulation {regulationId: $regId})
        OPTIONAL MATCH (a:Article {articleId: $articleId})
        CREATE (c:Clause {
            clauseId: $clauseId,
            number: $number,
            summary: $summary,
            description: $description,
            obligatedParty: $obligatedParty,
            obligationType: $obligationType,
            normativeIntensity: $normativeIntensity,
            applicable: $applicable,
            applicabilityReason: $applicabilityReason,
            sourceReference: $sourceReference,
            crossReferences: $crossReferences
        })
        CREATE (r)-[:HAS_CLAUSE]->(c)
        FOREACH (x IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END |
            CREATE (a)-[:DEFINES]->(c)
        )
        RETURN count(c)
        """
        params = {
            "clauseId": clause_id,
            "articleId": art_id,
            "regId": reg_id,
            "number": number,
            "summary": summary,
            "description": desc,
            "obligatedParty": party,
            "obligationType": obl_type,
            "normativeIntensity": ni,
            "applicable": applicable,
            "applicabilityReason": reason,
            "sourceReference": source,
            "crossReferences": cross_ref
        }
        if exec_cypher(cypher, params) > 0:
            count += 1
    
    print(f"  ✓ Created {count} DORA clauses")
    return count

def load_ai_act_clauses():
    """Load AI Act clauses"""
    print("\n" + "=" * 60)
    print("  Loading AI Act Clauses")
    print("=" * 60)
    
    articles = [
        ("AI-Art9", "AI_ACT", "9", "Risk management system", "A risk management system shall be established, implemented, documented and maintained for high-risk AI systems", "RISK_MANAGEMENT"),
        ("AI-Art10", "AI_ACT", "10", "Data and data governance", "High-risk AI systems shall be developed using training, validation and testing data sets that meet quality criteria", "DATA_GOVERNANCE"),
        ("AI-Art15", "AI_ACT", "15", "Accuracy, robustness and cybersecurity", "High-risk AI systems shall be designed and developed to achieve appropriate levels of accuracy, robustness and cybersecurity", "CYBERSECURITY"),
        ("AI-Art20", "AI_ACT", "20", "Record-keeping", "High-risk AI systems shall be designed and developed with logging capabilities", "RECORD_KEEPING"),
    ]
    
    for art_id, reg_id, number, title, summary, obl_type in articles:
        cypher = """
        MATCH (r:Regulation {regulationId: $regId})
        CREATE (a:Article {
            articleId: $articleId,
            number: $number,
            title: $title,
            summary: $summary,
            obligationType: $obligationType
        })
        CREATE (r)-[:HAS_ARTICLE]->(a)
        RETURN count(a)
        """
        params = {
            "articleId": art_id,
            "regId": reg_id,
            "number": number,
            "title": title,
            "summary": summary,
            "obligationType": obl_type
        }
        if exec_cypher(cypher, params) > 0:
            print(f"  ✓ Created Article {art_id}")
    
    clauses = [
        ("AI-9-1", "AI-Art9", "AI_ACT", "9(1)", "AI risk management system", "A risk management system shall be established, implemented, documented and maintained", "PROVIDER", "CONTINUOUS", 3, True, "AI Act provider", "Art.9(1)", ""),
        ("AI-9-2", "AI-Art9", "AI_ACT", "9(2)", "Risk identification and estimation", "The risk management system shall consist of risk identification and estimation", "PROVIDER", "CONTINUOUS", 3, True, "AI Act provider", "Art.9(2)", ""),
        ("AI-9-3", "AI-Art9", "AI_ACT", "9(3)", "Risk evaluation and mitigation", "The risk management system shall include risk evaluation and adoption of mitigation measures", "PROVIDER", "CONTINUOUS", 3, True, "AI Act provider", "Art.9(3)", ""),
        ("AI-9-4", "AI-Art9", "AI_ACT", "9(4)", "Residual risk assessment", "The residual risks associated with each hazard shall be judged acceptable", "PROVIDER", "CONTINUOUS", 3, True, "AI Act provider", "Art.9(4)", ""),
        ("AI-9-5", "AI-Art9", "AI_ACT", "9(5)", "Testing and feedback", "The risk management system shall be tested and updated throughout the lifecycle", "PROVIDER", "CONTINUOUS", 3, True, "AI Act provider", "Art.9(5)", ""),
        ("AI-10-1", "AI-Art10", "AI_ACT", "10(1)", "Data governance for AI systems", "High-risk AI systems shall be developed using data sets that meet quality criteria", "PROVIDER", "CONTINUOUS", 3, True, "AI Act provider", "Art.10(1)", ""),
        ("AI-10-2", "AI-Art10", "AI_ACT", "10(2)", "Data examination and bias detection", "Training, validation and testing data sets shall be examined in view of possible biases", "PROVIDER", "CONTINUOUS", 3, True, "AI Act provider", "Art.10(2)", ""),
        ("AI-10-3", "AI-Art10", "AI_ACT", "10(3)", "Data relevance and representativeness", "Data sets shall be relevant, representative and of sufficient quality", "PROVIDER", "CONTINUOUS", 3, True, "AI Act provider", "Art.10(3)", ""),
        ("AI-10-4", "AI-Art10", "AI_ACT", "10(4)", "Data processing and storage", "Data processing techniques shall preserve data integrity and confidentiality", "PROVIDER", "CONTINUOUS", 3, True, "AI Act provider", "Art.10(4)", ""),
        ("AI-10-5", "AI-Art10", "AI_ACT", "10(5)", "Data governance for bias mitigation", "Appropriate data governance and management practices shall be implemented", "PROVIDER", "CONTINUOUS", 3, True, "AI Act provider", "Art.10(5)", ""),
        ("AI-15-1", "AI-Art15", "AI_ACT", "15(1)", "AI system accuracy", "High-risk AI systems shall be designed and developed to achieve appropriate levels of accuracy", "PROVIDER", "CONTINUOUS", 3, True, "AI Act provider", "Art.15(1)", ""),
        ("AI-15-2", "AI-Art15", "AI_ACT", "15(2)", "AI system robustness", "High-risk AI systems shall be resilient to errors, faults and inconsistencies", "PROVIDER", "CONTINUOUS", 3, True, "AI Act provider", "Art.15(2)", ""),
        ("AI-15-3", "AI-Art15", "AI_ACT", "15(3)", "AI system cybersecurity", "High-risk AI systems shall be resilient to attempts to alter their use or performance", "PROVIDER", "CONTINUOUS", 3, True, "AI Act provider", "Art.15(3)", ""),
        ("AI-15-4", "AI-Art15", "AI_ACT", "15(4)", "Technical solutions for robustness", "Technical solutions for accuracy and robustness shall be implemented", "PROVIDER", "CONTINUOUS", 3, True, "AI Act provider", "Art.15(4)", ""),
        ("AI-20-1", "AI-Art20", "AI_ACT", "20(1)", "AI system logging", "High-risk AI systems shall be designed and developed with logging capabilities", "PROVIDER", "CONTINUOUS", 3, True, "AI Act provider", "Art.20(1)", ""),
        ("AI-20-2", "AI-Art20", "AI_ACT", "20(2)", "Log retention and access", "Logs shall be retained and made available to authorities upon request", "PROVIDER", "CONTINUOUS", 3, True, "AI Act provider", "Art.20(2)", ""),
    ]
    
    count = 0
    for clause_id, art_id, reg_id, number, summary, desc, party, obl_type, ni, applicable, reason, source, cross_ref in clauses:
        cypher = """
        MATCH (r:Regulation {regulationId: $regId})
        OPTIONAL MATCH (a:Article {articleId: $articleId})
        CREATE (c:Clause {
            clauseId: $clauseId,
            number: $number,
            summary: $summary,
            description: $description,
            obligatedParty: $obligatedParty,
            obligationType: $obligationType,
            normativeIntensity: $normativeIntensity,
            applicable: $applicable,
            applicabilityReason: $applicabilityReason,
            sourceReference: $sourceReference,
            crossReferences: $crossReferences
        })
        CREATE (r)-[:HAS_CLAUSE]->(c)
        FOREACH (x IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END |
            CREATE (a)-[:DEFINES]->(c)
        )
        RETURN count(c)
        """
        params = {
            "clauseId": clause_id,
            "articleId": art_id,
            "regId": reg_id,
            "number": number,
            "summary": summary,
            "description": desc,
            "obligatedParty": party,
            "obligationType": obl_type,
            "normativeIntensity": ni,
            "applicable": applicable,
            "applicabilityReason": reason,
            "sourceReference": source,
            "crossReferences": cross_ref
        }
        if exec_cypher(cypher, params) > 0:
            count += 1
    
    print(f"  ✓ Created {count} AI Act clauses")
    return count

def verify_regulations():
    """Verify all regulations have clauses"""
    print("\n" + "=" * 60)
    print("  Regulation Verification")
    print("=" * 60)
    
    cypher = """
    MATCH (r:Regulation)
    OPTIONAL MATCH (r)-[:HAS_ARTICLE]->(a:Article)
    OPTIONAL MATCH (r)-[:HAS_CLAUSE]->(c:Clause)
    RETURN r.regulationId AS regulation, r.name AS name,
           count(DISTINCT a) AS articles, count(DISTINCT c) AS clauses
    ORDER BY r.regulationId
    """
    
    import requests
    payload = {"statements": [{"statement": cypher}]}
    response = requests.post(f"{NEO4J_HTTP}/db/neo4j/tx/commit", auth=AUTH, json=payload, timeout=30)
    if response.status_code == 200:
        result = response.json()
        if result.get('results') and result['results'][0].get('data'):
            for row in result['results'][0]['data']:
                reg = row['row'][0]
                name = row['row'][1]
                articles = row['row'][2]
                clauses = row['row'][3]
                print(f"  {reg:10s} ({name:10s}): {articles:3d} articles, {clauses:3d} clauses")
    
    # Total
    cypher = """
    MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)
    RETURN count(DISTINCT c) AS totalClauses
    """
    payload = {"statements": [{"statement": cypher}]}
    response = requests.post(f"{NEO4J_HTTP}/db/neo4j/tx/commit", auth=AUTH, json=payload, timeout=30)
    if response.status_code == 200:
        result = response.json()
        if result.get('results') and result['results'][0].get('data'):
            total = result['results'][0]['data'][0]['row'][0]
            print(f"\n  TOTAL CLAUSES: {total}")

def main():
    print("=" * 60)
    print("  AEGIS Knowledge Graph - Load All Regulations")
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
    
    # Load missing regulations
    load_nis2_clauses()
    load_dora_clauses()
    load_ai_act_clauses()
    
    # Verify
    verify_regulations()
    
    print("\n" + "=" * 60)
    print("  ✓ All Regulations Loaded")
    print("=" * 60)

if __name__ == "__main__":
    import requests
    main()
