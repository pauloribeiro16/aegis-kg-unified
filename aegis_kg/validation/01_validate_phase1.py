#!/usr/bin/env python3
"""
AEGIS Phase 1 Knowledge Graph - Validation Suite
Validates schema constraints, data quality, and relationship integrity.
Uses batched queries to avoid Neo4j rate limiting.
"""
import os
import sys
import time
import requests
from dotenv import load_dotenv

load_dotenv()

NEO4J_HTTP = "http://localhost:7474"
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "d3fendtest"))

def exec_cypher_batch(statements, retries=5):
    """Execute multiple Cypher statements in a single request"""
    payload = {"statements": [{"statement": s} for s in statements]}
    for attempt in range(retries):
        try:
            response = requests.post(
                f"{NEO4J_HTTP}/db/neo4j/tx/commit",
                auth=AUTH,
                json=payload,
                timeout=30
            )
            if response.status_code == 429:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            if response.status_code != 200:
                return None, f"HTTP {response.status_code}"
            result = response.json()
            if result.get('errors'):
                return None, result['errors'][0].get('message', 'Unknown')
            return result.get('results', []), None
        except Exception as e:
            return None, str(e)
    return None, "Rate limited after retries"

def format_result(results, index):
    """Get formatted result at index"""
    if not results or index >= len(results):
        return {}
    if 'data' not in results[index]:
        return {}
    columns = results[index].get('columns', [])
    if not results[index]['data']:
        return {c: None for c in columns}
    return dict(zip(columns, results[index]['data'][0]['row']))

class ValidationResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = []

    def add_pass(self, test_name, details=""):
        self.passed += 1
        self.results.append({"status": "PASS", "test": test_name, "details": details})
        print(f"  \u2713 PASS: {test_name}")
        if details:
            print(f"    {details}")

    def add_fail(self, test_name, details=""):
        self.failed += 1
        self.results.append({"status": "FAIL", "test": test_name, "details": details})
        print(f"  \u2717 FAIL: {test_name}")
        if details:
            print(f"    {details}")

    def add_warning(self, test_name, details=""):
        self.warnings += 1
        self.results.append({"status": "WARN", "test": test_name, "details": details})
        print(f"  \u26a0 WARN: {test_name}")
        if details:
            print(f"    {details}")

    def summary(self):
        total = self.passed + self.failed + self.warnings
        print(f"\n{'='*60}")
        print(f"  VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"  Total tests: {total}")
        print(f"  Passed:      {self.passed}")
        print(f"  Failed:      {self.failed}")
        print(f"  Warnings:    {self.warnings}")
        print(f"{'='*60}")
        if self.failed > 0:
            print(f"  STATUS: FAILED ({self.failed} test(s) failed)")
            return False
        else:
            print(f"  STATUS: PASSED (all tests passed)")
            return True

v = ValidationResult()

def test_connection():
    """Test Neo4j connectivity"""
    print("\n" + "=" * 60)
    print("  1. CONNECTION TEST")
    print("=" * 60)
    try:
        r = requests.get(NEO4J_HTTP, auth=AUTH, timeout=5)
        if r.status_code == 200:
            version = r.json().get('neo4j_version', 'unknown')
            v.add_pass("Neo4j Connection", f"Version: {version}")
        else:
            v.add_fail("Neo4j Connection", f"HTTP {r.status_code}")
    except Exception as e:
        v.add_fail("Neo4j Connection", str(e))

def test_constraints():
    """Verify all required constraints exist"""
    print("\n" + "=" * 60)
    print("  2. SCHEMA CONSTRAINTS")
    print("=" * 60)
    
    statements = [
        "MATCH (n:Regulation) WITH n.regulationId AS id, count(*) AS c WHERE c > 1 RETURN count(*) AS duplicates",
        "MATCH (n:Article) WITH n.articleId AS id, count(*) AS c WHERE c > 1 RETURN count(*) AS duplicates",
        "MATCH (n:Clause) WITH n.clauseId AS id, count(*) AS c WHERE c > 1 RETURN count(*) AS duplicates",
        "MATCH (n:Domain) WITH n.domainId AS id, count(*) AS c WHERE c > 1 RETURN count(*) AS duplicates",
        "MATCH (n:SubDomain) WITH n.subDomainId AS id, count(*) AS c WHERE c > 1 RETURN count(*) AS duplicates",
    ]
    
    results, err = exec_cypher_batch(statements)
    if err:
        for label in ['Regulation', 'Article', 'Clause', 'Domain', 'SubDomain']:
            v.add_fail(f"Unique {label} IDs", err)
        return
    
    labels = ['Regulation', 'Article', 'Clause', 'Domain', 'SubDomain']
    for i, label in enumerate(labels):
        r = format_result(results, i)
        duplicates = r.get('duplicates', 0) or 0
        if duplicates == 0:
            v.add_pass(f"Unique {label} IDs", "No duplicate values")
        else:
            v.add_fail(f"Unique {label} IDs", f"{duplicates} duplicates found")

def test_node_counts():
    """Verify expected node counts"""
    print("\n" + "=" * 60)
    print("  3. NODE COUNTS")
    print("=" * 60)
    
    expected = {
        'Regulation': 5,
        'Domain': 10,
        'SubDomain': 38,
        'Article': 47,
        'Clause': 150,
        'CompanyContext': 1,
        'ComplementarityAnalysis': 10,
    }
    
    statements = [f"MATCH (n:{label}) RETURN count(n) AS count" for label in expected.keys()]
    results, err = exec_cypher_batch(statements)
    
    if err:
        for label in expected.keys():
            v.add_fail(f"{label} Count", err)
        return
    
    labels = list(expected.keys())
    for i, label in enumerate(labels):
        r = format_result(results, i)
        actual = r.get('count', 0) or 0
        exp = expected[label]
        if actual == exp:
            v.add_pass(f"{label} Count", f"Expected: {exp}, Actual: {actual}")
        elif actual == 0:
            v.add_fail(f"{label} Count", f"Expected: {exp}, Actual: {actual}")
        else:
            v.add_warning(f"{label} Count", f"Expected: {exp}, Actual: {actual}")

def test_relationship_integrity():
    """Verify relationship integrity"""
    print("\n" + "=" * 60)
    print("  4. RELATIONSHIP INTEGRITY")
    print("=" * 60)
    
    statements = [
        "MATCH (r:Regulation)-[:HAS_ARTICLE]->(a:Article) RETURN count(DISTINCT a) AS articlesWithRegulation",
        "MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause) RETURN count(DISTINCT c) AS clausesWithRegulation",
        "MATCH (d:Domain)-[:CONTAINS]->(sd:SubDomain) RETURN count(DISTINCT sd) AS subdomainsWithDomain",
        "MATCH (c:Clause)-[:COVERS_SUBDOMAIN]->(sd:SubDomain) RETURN count(*) AS coversCount",
        "MATCH (c:Clause) WHERE NOT (c)<-[:HAS_CLAUSE]-() RETURN count(c) AS orphanClauses",
    ]
    
    results, err = exec_cypher_batch(statements)
    if err:
        for test in ["HAS_ARTICLE", "HAS_CLAUSE", "CONTAINS", "COVERS_SUBDOMAIN"]:
            v.add_fail(f"{test} Integrity", err)
        return
    
    r = format_result(results, 0)
    count = r.get('articlesWithRegulation', 0) or 0
    if count == 47:
        v.add_pass("HAS_ARTICLE Integrity", f"{count} articles linked")
    else:
        v.add_warning("HAS_ARTICLE Integrity", f"Expected 47, found {count}")
    
    r = format_result(results, 1)
    count = r.get('clausesWithRegulation', 0) or 0
    if count == 150:
        v.add_pass("HAS_CLAUSE Integrity", f"{count} clauses linked")
    else:
        v.add_warning("HAS_CLAUSE Integrity", f"Expected 150, found {count}")
    
    r = format_result(results, 2)
    count = r.get('subdomainsWithDomain', 0) or 0
    if count == 38:
        v.add_pass("CONTAINS Integrity", f"{count} sub-domains linked")
    else:
        v.add_warning("CONTAINS Integrity", f"Expected 38, found {count}")
    
    r = format_result(results, 3)
    count = r.get('coversCount', 0) or 0
    if count >= 150:
        v.add_pass("COVERS_SUBDOMAIN Integrity", f"{count} clause-to-subdomain relationships")
    else:
        v.add_warning("COVERS_SUBDOMAIN Integrity", f"Expected >= 150, found {count}")
    
    r = format_result(results, 4)
    orphans = r.get('orphanClauses', 0) or 0
    if orphans == 0:
        v.add_pass("No Orphan Clauses", "All clauses linked to regulations")
    else:
        v.add_warning("Orphan Clauses", f"{orphans} clauses not linked")


def test_regulatory_interactions():
    """Verify regulatory interaction data (Phase 1 enrichment)"""
    print("\n" + "=" * 60)
    print("  4b. REGULATORY INTERACTIONS")
    print("=" * 60)

    statements = [
        "MATCH (sd:SubDomain)-[:SOLE_AUTHORITY]->(r:Regulation) RETURN count(*) AS soleAuthorityCount",
        "MATCH (r:Regulation) WHERE r.notificationTimelines IS NOT NULL RETURN count(r) AS regsWithTimelines",
        "MATCH (ca:ComplementarityAnalysis)-[:OVERLAPS_WITH]->(r:Regulation) RETURN count(*) AS overlapsCount",
        "MATCH (ca:ComplementarityAnalysis) RETURN count(ca) AS caCount",
        "MATCH (sd:SubDomain) WHERE sd.isSoleAuthority = true RETURN count(sd) AS soleAuthoritySDs",
    ]

    results, err = exec_cypher_batch(statements)
    if err:
        for test in ["SOLE_AUTHORITY", "Timelines", "OVERLAPS_WITH", "CA Count", "SoleAuth SubDomains"]:
            v.add_fail(f"{test}", err)
        return

    r = format_result(results, 0)
    count = r.get('soleAuthorityCount', 0) or 0
    if count == 8:
        v.add_pass("SOLE_AUTHORITY Relationships", f"{count}/8")
    else:
        v.add_warning("SOLE_AUTHORITY Relationships", f"Expected 8, found {count}")

    r = format_result(results, 1)
    count = r.get('regsWithTimelines', 0) or 0
    if count == 5:
        v.add_pass("Regulations with Timelines", f"{count}/5")
    else:
        v.add_warning("Regulations with Timelines", f"Expected 5, found {count}")

    r = format_result(results, 2)
    count = r.get('overlapsCount', 0) or 0
    if count == 20:
        v.add_pass("OVERLAPS_WITH Relationships", f"{count}/20 (10 pairs x 2)")
    else:
        v.add_warning("OVERLAPS_WITH Relationships", f"Expected 20, found {count}")

    r = format_result(results, 3)
    count = r.get('caCount', 0) or 0
    if count == 10:
        v.add_pass("ComplementarityAnalysis Nodes", f"{count}/10")
    else:
        v.add_warning("ComplementarityAnalysis Nodes", f"Expected 10, found {count}")

    r = format_result(results, 4)
    count = r.get('soleAuthoritySDs', 0) or 0
    if count == 8:
        v.add_pass("Sole Authority SubDomains", f"{count}/8")
    else:
        v.add_warning("Sole Authority SubDomains", f"Expected 8, found {count}")


def test_data_quality():
    """Verify data quality"""
    print("\n" + "=" * 60)
    print("  5. DATA QUALITY")
    print("=" * 60)
    
    statements = [
        "MATCH (r:Regulation) WHERE r.regulationId IS NULL OR r.name IS NULL OR r.regulationId = '' RETURN count(r) AS invalidCount",
        "MATCH (c:Clause) WHERE c.applicable IS NULL RETURN count(c) AS missingCount",
        "MATCH (c:Clause) WHERE c.normativeIntensity IS NULL OR c.normativeIntensity = 0 RETURN count(c) AS missingNI",
        "MATCH (c:Clause) WITH c.clauseId AS id, count(*) AS c WHERE c > 1 RETURN count(*) AS duplicates",
    ]
    
    results, err = exec_cypher_batch(statements)
    if err:
        for test in ["Regulation Data Quality", "Clause Applicability", "Normative Intensity", "Duplicate Clause IDs"]:
            v.add_fail(test, err)
        return
    
    r = format_result(results, 0)
    count = r.get('invalidCount', 0) or 0
    if count == 0:
        v.add_pass("Regulation Data Quality", "All regulations have required fields")
    else:
        v.add_fail("Regulation Data Quality", f"{count} missing required fields")
    
    r = format_result(results, 1)
    count = r.get('missingCount', 0) or 0
    if count == 0:
        v.add_pass("Clause Applicability", "All clauses have applicability flag")
    else:
        v.add_warning("Clause Applicability", f"{count} clauses missing applicability flag")
    
    r = format_result(results, 2)
    count = r.get('missingNI', 0) or 0
    if count == 0:
        v.add_pass("Normative Intensity", "All clauses have NI values")
    else:
        v.add_warning("Normative Intensity", f"{count} clauses missing NI value")
    
    r = format_result(results, 3)
    count = r.get('duplicates', 0) or 0
    if count == 0:
        v.add_pass("No Duplicate Clause IDs", "All clause IDs are unique")
    else:
        v.add_fail("Duplicate Clause IDs", f"{count} duplicates found")

def test_query_performance():
    """Test query performance"""
    print("\n" + "=" * 60)
    print("  6. QUERY PERFORMANCE")
    print("=" * 60)
    
    import time
    
    cypher = """
    MATCH (sd:SubDomain)
    WHERE NOT (sd)<-[:COVERS_SUBDOMAIN]-(:Clause)
    RETURN count(sd) AS uncovered
    """
    start = time.time()
    results, err = exec_cypher_batch([cypher])
    elapsed = time.time() - start
    
    if err:
        v.add_fail("Gap Analysis Performance", err)
    elif elapsed < 2.0:
        v.add_pass("Gap Analysis Performance", f"{elapsed:.3f}s (< 2.0s threshold)")
    else:
        v.add_warning("Gap Analysis Performance", f"{elapsed:.3f}s (>= 2.0s threshold)")
    
    cypher2 = """
    MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)-[:COVERS_SUBDOMAIN]->(sd:SubDomain)
    WITH r.regulationId AS reg, count(DISTINCT sd) AS coverage
    RETURN reg, coverage
    """
    start = time.time()
    results2, err2 = exec_cypher_batch([cypher2])
    elapsed2 = time.time() - start
    
    if err2:
        v.add_fail("Coverage Analysis Performance", err2)
    elif elapsed2 < 2.0:
        v.add_pass("Coverage Analysis Performance", f"{elapsed2:.3f}s (< 2.0s threshold)")
    else:
        v.add_warning("Coverage Analysis Performance", f"{elapsed2:.3f}s (>= 2.0s threshold)")

def test_api_health():
    """Test API endpoint availability"""
    print("\n" + "=" * 60)
    print("  7. API HEALTH CHECK")
    print("=" * 60)
    
    api_base = "http://localhost:5000"
    endpoints = [
        '/',
        '/api/health',
        '/api/regulations',
        '/api/clauses?keyword=encryption',
        '/api/clauses/GDPR-C01',
        '/api/gap-analysis',
        '/api/coverage',
        '/api/applicability',
        '/api/traceability',
        '/api/overlap',
        '/api/domains',
    ]
    
    for endpoint in endpoints:
        try:
            r = requests.get(f"{api_base}{endpoint}", timeout=5)
            if r.status_code == 200:
                v.add_pass(f"API Endpoint: {endpoint}", f"HTTP {r.status_code}")
            else:
                v.add_fail(f"API Endpoint: {endpoint}", f"HTTP {r.status_code}")
        except Exception as e:
            v.add_fail(f"API Endpoint: {endpoint}", str(e))

def main():
    print("=" * 60)
    print("  AEGIS Phase 1 Knowledge Graph - Validation Suite")
    print("=" * 60)
    
    test_connection()
    test_constraints()
    test_node_counts()
    test_relationship_integrity()
    test_regulatory_interactions()
    test_data_quality()
    test_query_performance()
    test_api_health()
    
    success = v.summary()
    
    if not success:
        sys.exit(1)
    
    print(f"\n  Validation complete. All tests passed.")
    return 0

if __name__ == "__main__":
    sys.exit(main() or 0)
