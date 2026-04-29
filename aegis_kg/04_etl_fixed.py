import os
#!/usr/bin/env python3
"""
Phase 1 ETL Script - Fixed Version
Loads Phase 1 data into Neo4j using REST API with parameterized Cypher queries.
Fixes: SQL injection risk, missing subDomainId column, special character handling.
"""
import requests
import csv
import time
import json
from pathlib import Path

# Configuration
NEO4J_HTTP = "http://localhost:7474"
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", ""))
DATA_DIR = Path(__file__).parent / "data"

def load_csv(file_name):
    """Load CSV file and return data"""
    file_path = DATA_DIR / file_name
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        data = list(reader)
    return data

def exec_cypher(statement, params=None):
    """Execute a Cypher query using the transactional endpoint"""
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}
    response = requests.post(
        f"{NEO4J_HTTP}/db/neo4j/tx/commit",
        auth=AUTH,
        json=payload,
        timeout=30
    )
    if response.status_code != 200:
        print(f"  HTTP {response.status_code}: {response.text[:200]}")
        return False
    result = response.json()
    if result.get('errors'):
        for err in result['errors']:
            print(f"  DB Error: {err.get('message', '')[:200]}")
        return False
    return True

def exec_cypher_return(statement, params=None):
    """Execute a Cypher query and return results"""
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}
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

# ── Node creation ──────────────────────────────────────────────────────────

def create_regulation(row):
    cypher = """
    CREATE (r:Regulation {
        regulationId: $regulationId,
        name: $name,
        fullName: $fullName,
        type: $type,
        effectiveDate: $effectiveDate,
        lastAmended: $lastAmended,
        officialLink: $officialLink,
        primaryFocus: $primaryFocus
    })
    """
    ok = exec_cypher(cypher, {
        "regulationId": row['regulationId'],
        "name": row['name'],
        "fullName": row['fullName'],
        "type": row['type'],
        "effectiveDate": row['effectiveDate'],
        "lastAmended": row.get('lastAmended', ''),
        "officialLink": row['officialLink'],
        "primaryFocus": row['primaryFocus']
    })
    if ok:
        print(f"  ✓ Created {row['regulationId']}")
    return ok

def create_domain(row):
    cypher = """
    CREATE (d:Domain {
        domainId: $domainId,
        name: $name,
        description: $description,
        primaryRegulatoryDriver: $primaryRegulatoryDriver
    })
    """
    ok = exec_cypher(cypher, {
        "domainId": row['domainId'],
        "name": row['name'],
        "description": row['description'],
        "primaryRegulatoryDriver": row['primaryRegulatoryDriver']
    })
    if ok:
        print(f"  ✓ Created {row['domainId']}")
    return ok

def create_subdomain(row):
    keywords = [k.strip() for k in row.get('keywords', '').split(',') if k.strip()]
    examples = [e.strip() for e in row.get('examples', '').split(',') if e.strip()]
    cypher = """
    CREATE (sd:SubDomain {
        subDomainId: $subDomainId,
        name: $name,
        description: $description,
        keywords: $keywords,
        examples: $examples,
        soleAuthority: $soleAuthority,
        gapRisk: $gapRisk
    })
    """
    ok = exec_cypher(cypher, {
        "subDomainId": row['subDomainId'],
        "name": row['name'],
        "description": row['description'],
        "keywords": keywords,
        "examples": examples,
        "soleAuthority": row.get('soleAuthority', ''),
        "gapRisk": row.get('gapRisk', 'MEDIUM')
    })
    if ok:
        print(f"  ✓ Created {row['subDomainId']}")
    return ok

def create_article(row, reg_id):
    cypher = """
    MATCH (reg:Regulation {regulationId: $regId})
    CREATE (a:Article {
        articleId: $articleId,
        number: $number,
        title: $title,
        chapter: $chapter,
        section: $section,
        summary: $summary,
        obligationType: $obligationType
    })
    CREATE (reg)-[:HAS_ARTICLE]->(a)
    """
    ok = exec_cypher(cypher, {
        "regId": reg_id,
        "articleId": row['articleId'],
        "number": row['number'],
        "title": row.get('title', ''),
        "chapter": row.get('chapter', ''),
        "section": row.get('section', ''),
        "summary": row['summary'],
        "obligationType": row['obligationType']
    })
    if ok:
        print(f"  ✓ Created {row['articleId']} → HAS_ARTICLE → {reg_id}")
    return ok

def create_clause(row, reg_articles_map, subdomain_lookup):
    """Create a Clause with relationships to Article and SubDomain"""
    # Parse normativeIntensity - handle both numeric and text values
    ni_raw = row.get('normativeIntensity', '3').strip()
    try:
        ni = int(ni_raw)
    except ValueError:
        # Map text values to numeric
        ni_map = {'MANDATORY': 3, 'SHALL': 3, 'RECOMMENDED': 2, 'SHOULD': 2, 'BEST_PRACTICE': 1, 'MAY': 1}
        ni = ni_map.get(ni_raw.upper(), 3)

    # Parse applicable
    app_raw = row.get('applicable', 'YES').strip().upper()
    applicable = app_raw in ('YES', 'TRUE', 'Y')

    # Determine articleId from the CSV
    article_id = row.get('articleId', '')
    regulation_id = row.get('regulationId', '')

    cypher = """
    MATCH (reg:Regulation {regulationId: $regId})
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
    CREATE (reg)-[:HAS_CLAUSE]->(c)
    """
    params = {
        "regId": regulation_id,
        "clauseId": row['clauseId'],
        "number": row.get('number', ''),
        "summary": row['summary'],
        "description": row.get('description', ''),
        "obligatedParty": row.get('obligatedParty', ''),
        "obligationType": row.get('obligationType', ''),
        "normativeIntensity": ni,
        "applicable": applicable,
        "applicabilityReason": row.get('applicabilityReason', ''),
        "sourceReference": row.get('sourceReference', ''),
        "crossReferences": row.get('crossReferences', '')
    }

    # Add relationship to Article if available
    if article_id:
        cypher += """
    WITH c
    OPTIONAL MATCH (a:Article {articleId: $articleId})
    FOREACH (x IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END |
        CREATE (a)-[:DEFINES]->(c)
    )
    """
        params["articleId"] = article_id

    # Add relationship to SubDomain if available
    sd_id = row.get('subDomainId', '').strip()
    if sd_id:
        cypher += """
    WITH c
    OPTIONAL MATCH (sd:SubDomain {subDomainId: $subDomainId})
    FOREACH (x IN CASE WHEN sd IS NOT NULL THEN [1] ELSE [] END |
        CREATE (c)-[:COVERS_SUBDOMAIN {weight: 1.0}]->(sd)
    )
    """
        params["subDomainId"] = sd_id
    elif regulation_id and article_id:
        # Try to derive subDomain from the taxonomy lookup
        # For TinyTask, use the clause mapping from the Excel
        pass

    cypher += " RETURN c"

    ok = exec_cypher(cypher, params)
    if ok:
        print(f"  ✓ Created {row['clauseId']} (NI={ni})")
    return ok

def create_company_context(row):
    # dataTypes is semicolon-separated in a single column
    data_types_raw = row.get('dataTypes', '')
    data_types = [dt.strip() for dt in data_types_raw.split(';') if dt.strip()]

    cypher = """
    CREATE (cc:CompanyContext {
        contextId: $contextId,
        companyName: $companyName,
        assessmentDate: $assessmentDate,
        industry: $industry,
        size: $size,
        location: $location,
        employeeCount: $employeeCount,
        revenue: $revenue,
        dataTypes: $dataTypes,
        specialCategoryData: $specialCategoryData,
        aiSystems: $aiSystems,
        criticalInfrastructure: $criticalInfrastructure,
        financialEntity: $financialEntity
    })
    """
    ok = exec_cypher(cypher, {
        "contextId": row['contextId'],
        "companyName": row['companyName'],
        "assessmentDate": row['assessmentDate'],
        "industry": row['industry'],
        "size": row['size'],
        "location": row['location'],
        "employeeCount": int(row.get('employeeCount', 0)),
        "revenue": row['revenue'],
        "dataTypes": data_types,
        "specialCategoryData": row['specialCategoryData'],
        "aiSystems": row['aiSystems'],
        "criticalInfrastructure": row['criticalInfrastructure'],
        "financialEntity": row['financialEntity']
    })
    if ok:
        print(f"  ✓ Created CompanyContext: {row['companyName']}")
    return ok

def create_complementarity_analysis():
    cypher = """
    MATCH (gdpr:Regulation {regulationId: 'GDPR'})
    MATCH (cra:Regulation {regulationId: 'CRA'})
    CREATE (ca:ComplementarityAnalysis {
        analysisId: 'GDPR-CRA-001',
        regulation1Id: 'GDPR',
        regulation2Id: 'CRA',
        overlapType: 'COMPLEMENTARY',
        jaccardIndex: 0.367,
        overlapDescription: 'Both regulations require data protection, encryption, and security controls',
        complementarityDescription: 'GDPR focuses on privacy rights, CRA focuses on product security',
        recommendedApproach: 'Implement both sets of controls, prioritize GDPR for data subjects rights',
        analysisDate: '2024-01-20',
        analyst: 'Compliance Lead'
    })
    CREATE (ca)-[:OVERLAPS_WITH]->(gdpr)
    CREATE (ca)-[:OVERLAPS_WITH]->(cra)
    """
    ok = exec_cypher(cypher)
    if ok:
        print(f"  ✓ Created ComplementarityAnalysis: GDPR-CRA-001")
    return ok

# ── Relationship creation ──────────────────────────────────────────────────

def create_domain_subdomain_relationships():
    """Create CONTAINS relationships from Domain to SubDomain"""
    cypher = """
    MATCH (d:Domain), (sd:SubDomain)
    WHERE sd.subDomainId STARTS WITH d.domainId + '.'
    CREATE (d)-[:CONTAINS]->(sd)
    """
    result = exec_cypher_return(cypher)
    print(f"  ✓ Domain → SubDomain relationships created")

def create_regulation_focus_relationships():
    """Create PRIMARY_FOCUS relationships based on regulation type"""
    focus_map = {
        'GDPR': 'D-01',
        'CRA': 'D-02',
        'NIS2': 'D-04',
        'DORA': 'D-09',
        'AI_ACT': 'D-10'
    }
    count = 0
    for reg_id, domain_id in focus_map.items():
        cypher = """
        MATCH (r:Regulation {regulationId: $regId})
        MATCH (d:Domain {domainId: $domainId})
        CREATE (r)-[:PRIMARY_FOCUS]->(d)
        """
        ok = exec_cypher(cypher, {"regId": reg_id, "domainId": domain_id})
        if ok:
            count += 1
    print(f"  ✓ {count} Regulation PRIMARY_FOCUS relationships created")

def create_clause_clause_relationships():
    """Create RELATED_TO relationships between clauses from the same regulation
    that cover the same sub-domain"""
    cypher = """
    MATCH (c1:Clause)-[:COVERS_SUBDOMAIN]->(sd:SubDomain)<-[:COVERS_SUBDOMAIN]-(c2:Clause)
    WHERE c1.clauseId < c2.clauseId
    MERGE (c1)-[r:RELATED_TO {via: sd.subDomainId}]-(c2)
    """
    exec_cypher(cypher)
    print(f"  ✓ Clause → Clause (RELATED_TO) relationships created")

# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("AEGIS Phase 1 KG - ETL (Fixed)")
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

    # Clear existing data for fresh load
    print("\n2. Clearing existing data...")
    clear_cypher = """
    MATCH (n) DETACH DELETE n
    """
    exec_cypher(clear_cypher)
    print("   ✓ Database cleared")

    # Load Regulations
    print("\n3. Loading Regulations...")
    regulations = load_csv("00_regulations.csv")
    reg_count = sum(1 for r in regulations if create_regulation(r))
    print(f"   Total: {reg_count}/{len(regulations)}")

    # Load Domains
    print("\n4. Loading Domains...")
    domains = load_csv("01_domains.csv")
    dom_count = sum(1 for d in domains if create_domain(d))
    print(f"   Total: {dom_count}/{len(domains)}")

    # Load SubDomains
    print("\n5. Loading SubDomains...")
    subdomains = load_csv("02_subdomains.csv")
    sd_count = sum(1 for sd in subdomains if create_subdomain(sd))
    print(f"   Total: {sd_count}/{len(subdomains)}")

    # Load Articles
    print("\n6. Loading Articles...")
    articles = load_csv("03_articles.csv")
    art_count = 0
    for art in articles:
        reg_id = art.get('regulationId', '')
        if reg_id and create_article(art, reg_id):
            art_count += 1
    print(f"   Total: {art_count}/{len(articles)}")

    # Load Clauses
    print("\n7. Loading Clauses...")
    clauses = load_csv("04_clauses.csv")
    print(f"   CSV columns: {list(clauses[0].keys()) if clauses else 'N/A'}")
    clause_count = 0
    for clause in clauses:
        if create_clause(clause, {}, {}):
            clause_count += 1
    print(f"   Total: {clause_count}/{len(clauses)}")

    # Load Company Context
    print("\n8. Loading Company Context...")
    ctx = load_csv("05_company_context.csv")
    if ctx and create_company_context(ctx[0]):
        print("   ✓ Company Context loaded")

    # Load Complementarity Analysis
    print("\n9. Loading Complementarity Analysis...")
    if create_complementarity_analysis():
        print("   ✓ Complementarity Analysis loaded")

    # Create relationships
    print("\n10. Creating relationships...")
    create_domain_subdomain_relationships()
    create_regulation_focus_relationships()
    create_clause_clause_relationships()

    # Final summary
    print("\n" + "=" * 60)
    print("ETL COMPLETE - Summary")
    print("=" * 60)
    result = exec_cypher_return("MATCH (n) RETURN labels(n) AS label, count(*) AS count ORDER BY count DESC")
    total = 0
    if result and 'data' in result[0]:
        for row in result[0]['data']:
            label = row['row'][0][0]
            count = row['row'][1]
            total += count
            print(f"   {label}: {count}")

    # Count relationships
    rel_result = exec_cypher_return("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY count DESC")
    total_rels = 0
    if rel_result and 'data' in rel_result[0]:
        for row in rel_result[0]['data']:
            rtype = row['row'][0]
            count = row['row'][1]
            total_rels += count
            print(f"   [{rtype}]: {count}")

    print(f"\n   TOTAL NODES: {total}")
    print(f"   TOTAL RELATIONSHIPS: {total_rels}")
    print(f"\n   Neo4j Browser: {NEO4J_HTTP}/browser")
    print(f"   Auth: neo4j / $NEO4J_PASSWORD (env var)")

if __name__ == "__main__":
    main()
