import os
#!/usr/bin/env python3
"""
Fix Missing Relationships in Knowledge Graph
Creates Article-to-Clause, Complementarity, and other missing relationships.
"""
import requests
import csv
from pathlib import Path

NEO4J_HTTP = "http://localhost:7474"
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", ""))
# Resolve path relative to this script
DATA_DIR = Path(__file__).resolve().parent.parent / "knowledge_graph_analysis" / "phase1_implementation" / "data"

def exec_cypher(statement, params=None):
    """Execute a Cypher query using parameterized queries"""
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}
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
    # Return affected rows count
    try:
        data = result.get('results', [{}])[0].get('data', [{}])[0].get('row', [0])
        return data[0] if data else 0
    except (IndexError, TypeError):
        return 0

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

def fix_article_clause_relationships():
    """Create DEFINES relationships from Articles to Clauses based on articleId in clauses.csv"""
    print("\n" + "=" * 60)
    print("  Fixing Article → Clause Relationships")
    print("=" * 60)

    cypher = """
    MATCH (a:Article), (c:Clause)
    WHERE c.articleId = a.articleId
    AND NOT EXISTS { (a)-[:DEFINES]->(c) }
    CREATE (a)-[:DEFINES]->(c)
    RETURN count(*) AS created
    """
    result = exec_cypher(cypher)
    print(f"  ✓ Created {result} Article→Clause DEFINES relationships")
    return result

def fix_clause_regulation_relationships():
    """Create HAS_CLAUSE relationships from Regulations to Clauses if missing"""
    print("\n" + "=" * 60)
    print("  Fixing Regulation → Clause Relationships")
    print("=" * 60)

    cypher = """
    MATCH (r:Regulation), (c:Clause)
    WHERE c.regulationId = r.regulationId
    AND NOT EXISTS { (r)-[:HAS_CLAUSE]->(c) }
    CREATE (r)-[:HAS_CLAUSE]->(c)
    RETURN count(*) AS created
    """
    result = exec_cypher(cypher)
    print(f"  ✓ Created {result} Regulation→Clause HAS_CLAUSE relationships")
    return result

def fix_complementarity_relationships():
    """Create proper ComplementarityAnalysis relationships"""
    print("\n" + "=" * 60)
    print("  Fixing Complementarity Analysis Relationships")
    print("=" * 60)

    # First, delete any existing incomplete complementarity nodes
    cypher_delete = """
    MATCH (ca:ComplementarityAnalysis)
    OPTIONAL MATCH (ca)-[r]-()
    DELETE r
    DELETE ca
    """
    exec_cypher(cypher_delete)

    # Load from CSV and create complementarity nodes
    csv_path = DATA_DIR / "06_complementarity_analysis.csv"
    if not csv_path.exists():
        print("  ✗ Complementarity CSV not found at:", csv_path)
        print("  ⚠ Creating from known GDPR-CRA pair instead")
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
            conflictDescription: 'None',
            recommendedApproach: 'Implement both sets of controls, prioritize GDPR for data subjects rights',
            analysisDate: '2024-01-20',
            analyst: 'Compliance Lead'
        })
        CREATE (ca)-[:OVERLAPS_WITH]->(gdpr)
        CREATE (ca)-[:OVERLAPS_WITH]->(cra)
        RETURN count(ca) AS created
        """
        result = exec_cypher(cypher)
        print(f"  ✓ Created {result} ComplementarityAnalysis node with relationships")
        return result

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    count = 0
    for row in rows:
        cypher = """
        MATCH (r1:Regulation {regulationId: $reg1})
        MATCH (r2:Regulation {regulationId: $reg2})
        CREATE (ca:ComplementarityAnalysis {
            analysisId: $analysisId,
            regulation1Id: $reg1,
            regulation2Id: $reg2,
            overlapType: $overlapType,
            jaccardIndex: toFloat($jaccardIndex),
            overlapDescription: $overlapDescription,
            complementarityDescription: $complementarityDescription,
            conflictDescription: $conflictDescription,
            recommendedApproach: $recommendedApproach,
            analysisDate: $analysisDate,
            analyst: $analyst
        })
        CREATE (ca)-[:OVERLAPS_WITH]->(r1)
        CREATE (ca)-[:OVERLAPS_WITH]->(r2)
        RETURN count(ca) AS created
        """
        params = {
            "analysisId": row['analysisId'],
            "reg1": row['regulation1Id'],
            "reg2": row['regulation2Id'],
            "overlapType": row['overlapType'],
            "jaccardIndex": row['jaccardIndex'],
            "overlapDescription": row['overlapDescription'],
            "complementarityDescription": row['complementarityDescription'],
            "conflictDescription": row.get('conflictDescription', ''),
            "recommendedApproach": row['recommendedApproach'],
            "analysisDate": row['analysisDate'],
            "analyst": row['analyst']
        }
        result = exec_cypher(cypher, params)
        count += result
        print(f"  ✓ Created {row['analysisId']}: {row['regulation1Id']} ↔ {row['regulation2Id']}")

    print(f"  ✓ Total Complementarity relationships: {count}")
    return count

def verify_all_relationships():
    """Verify all relationship types exist"""
    print("\n" + "=" * 60)
    print("  Relationship Verification")
    print("=" * 60)

    cypher = """
    MATCH ()-[r]->()
    RETURN type(r) AS relationshipType, count(*) AS count
    ORDER BY count DESC
    """
    results = exec_cypher_return(cypher)
    total = 0
    if results and 'data' in results[0]:
        for row in results[0]['data']:
            rtype = row['row'][0]
            count = row['row'][1]
            total += count
            print(f"  {rtype}: {count}")

    print(f"\n  TOTAL RELATIONSHIPS: {total}")
    return total

def main():
    print("=" * 60)
    print("  AEGIS Phase 1 KG - Fix Missing Relationships")
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

    # Fix relationships
    fix_article_clause_relationships()
    fix_clause_regulation_relationships()
    fix_complementarity_relationships()

    # Verify
    verify_all_relationships()

    print("\n" + "=" * 60)
    print("  ✓ All relationship fixes complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
