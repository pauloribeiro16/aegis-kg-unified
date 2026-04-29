import os
"""
Phase 1 Knowledge Graph - Analysis Queries
Gap analysis, coverage analysis, and traceability queries.
"""
import requests
import json

NEO4J_HTTP = "http://localhost:7474"
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", ""))

def exec_query(cypher, params=None):
    """Execute a Cypher query and return results"""
    payload = {"statements": [{"statement": cypher, "parameters": params or {}}]}
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
        print(f"  Query error: {result['errors'][0].get('message', '')[:200]}")
        return []
    return result.get('results', [])

def print_results(title, results, columns=None):
    """Print query results in a readable format"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    if not results or not results[0].get('data'):
        print("  No results")
        return
    for row in results[0]['data']:
        vals = row['row']
        if columns:
            for col, val in zip(columns, vals):
                print(f"  {col}: {val}")
            print()
        else:
            print(f"  {vals}")

# ── Query 1: Gap Analysis ──────────────────────────────────────────────────

def gap_analysis():
    """Identify sub-domains with NO clause coverage"""
    cypher = """
    MATCH (sd:SubDomain)
    WHERE NOT (sd)<-[:COVERS_SUBDOMAIN]-(:Clause)
    OPTIONAL MATCH (d:Domain)-[:CONTAINS]->(sd)
    RETURN sd.subDomainId AS subDomain, sd.name AS name, d.domainId AS domain
    ORDER BY sd.subDomainId
    """
    results = exec_query(cypher)
    print_results("GAP ANALYSIS — Uncovered Sub-Domains", results,
                  ["Sub-Domain", "Name", "Domain"])
    return results

# ── Query 2: Coverage Analysis ─────────────────────────────────────────────

def coverage_analysis():
    """Calculate coverage percentage by regulation and overall"""
    cypher = """
    // Total sub-domains
    MATCH (sd:SubDomain)
    WITH count(sd) AS totalSD

    // Count covered sub-domains via Clause relationships
    MATCH (sd:SubDomain)<-[:COVERS_SUBDOMAIN]-(c:Clause)
    WITH totalSD, count(DISTINCT sd) AS coveredSD

    // Coverage by regulation
    MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)-[:COVERS_SUBDOMAIN]->(sd:SubDomain)
    WITH totalSD, coveredSD, r.regulationId AS reg, count(DISTINCT sd) AS regCoverage
    RETURN reg, regCoverage, totalSD, coveredSD,
           round(100.0 * regCoverage / totalSD, 1) AS regCoveragePct
    ORDER BY regCoverage DESC
    """
    results = exec_query(cypher)
    print_results("COVERAGE ANALYSIS — By Regulation", results,
                  ["Regulation", "Covered SD", "Total SD", "Covered", "%"])
    return results

def coverage_by_domain():
    """Calculate coverage by domain"""
    cypher = """
    MATCH (d:Domain)-[:CONTAINS]->(sd:SubDomain)
    OPTIONAL MATCH (sd)<-[:COVERS_SUBDOMAIN]-(:Clause)
    WITH d.domainId AS domain, d.name AS domainName,
         count(sd) AS totalInDomain,
         count(DISTINCT CASE WHEN (sd)<-[:COVERS_SUBDOMAIN]-(:Clause) THEN sd END) AS covered
    RETURN domain, domainName, totalInDomain, covered,
           round(100.0 * covered / totalInDomain, 1) AS coveragePct
    ORDER BY domain
    """
    results = exec_query(cypher)
    print_results("COVERAGE BY DOMAIN", results,
                  ["Domain", "Name", "Total", "Covered", "%"])
    return results

# ── Query 3: Clause Lookup ─────────────────────────────────────────────────

def clause_lookup(keyword):
    """Search clauses by keyword in summary or description"""
    cypher = """
    MATCH (c:Clause)
    WHERE toLower(c.summary) CONTAINS toLower($kw)
       OR toLower(c.description) CONTAINS toLower($kw)
    MATCH (r:Regulation)-[:HAS_CLAUSE]->(c)
    RETURN r.regulationId AS reg, c.clauseId AS clause, c.summary AS summary,
           c.normativeIntensity AS NI
    ORDER BY NI DESC, c.clauseId
    """
    results = exec_query(cypher, {"kw": keyword})
    print_results(f"CLAUSE LOOKUP — '{keyword}'", results,
                  ["Regulation", "Clause", "Summary", "NI"])
    return results

# ── Query 4: Regulation Overlap ────────────────────────────────────────────

def regulation_overlap():
    """Find sub-domains covered by multiple regulations"""
    cypher = """
    MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)-[:COVERS_SUBDOMAIN]->(sd:SubDomain)
    WITH sd.subDomainId AS subDomain, sd.name AS sdName,
         collect(DISTINCT r.regulationId) AS regulations,
         count(DISTINCT c.clauseId) AS clauseCount
    WHERE size(regulations) > 1
    RETURN subDomain, sdName, regulations, clauseCount
    ORDER BY clauseCount DESC
    """
    results = exec_query(cypher)
    print_results("REGULATION OVERLAP — Sub-Domains with Multiple Regulations", results,
                  ["Sub-Domain", "Name", "Regulations", "Clause Count"])
    return results

# ── Query 5: Clause-to-Article Traceability ────────────────────────────────

def clause_article_traceability():
    """Show which articles define which clauses"""
    cypher = """
    MATCH (a:Article)-[:DEFINES]->(c:Clause)
    MATCH (r:Regulation)-[:HAS_ARTICLE]->(a)
    RETURN r.regulationId AS reg, a.articleId AS article, a.title AS title,
           count(c) AS clauseCount, collect(c.clauseId)[..5] AS sampleClauses
    ORDER BY reg, a.articleId
    """
    results = exec_query(cypher)
    print_results("CLAUSE-ARTICLE TRACEABILITY", results,
                  ["Regulation", "Article", "Title", "Clauses", "Sample"])
    return results

# ── Query 6: Company Context Summary ───────────────────────────────────────

def company_context_summary():
    """Show company profile and applicable regulations"""
    cypher = """
    MATCH (cc:CompanyContext)
    RETURN cc.companyName AS company, cc.industry AS industry,
           cc.size AS size, cc.employeeCount AS employees,
           cc.dataTypes AS dataTypes, cc.specialCategoryData AS specialData,
           cc.aiSystems AS aiSystems
    """
    results = exec_query(cypher)
    print_results("COMPANY CONTEXT SUMMARY", results,
                  ["Company", "Industry", "Size", "Employees", "Data Types", "Special Data", "AI"])
    return results

def applicable_regulations():
    """Show which regulations apply to the company"""
    cypher = """
    MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause {applicable: true})
    WITH r.regulationId AS reg, r.name AS name, count(c) AS clauseCount
    RETURN reg, name, clauseCount
    ORDER BY clauseCount DESC
    """
    results = exec_query(cypher)
    print_results("APPLICABLE REGULATIONS", results,
                  ["Regulation", "Name", "Applicable Clauses"])
    return results

# ── Query 7: Normative Intensity Distribution ──────────────────────────────

def ni_distribution():
    """Show normative intensity distribution by regulation"""
    cypher = """
    MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause {applicable: true})
    WITH r.regulationId AS reg, c.normativeIntensity AS NI, count(c) AS count
    RETURN reg, NI, count
    ORDER BY reg, NI DESC
    """
    results = exec_query(cypher)
    print_results("NORMATIVE INTENSITY DISTRIBUTION", results,
                  ["Regulation", "NI Level", "Count"])
    return results

# ── Run All Queries ────────────────────────────────────────────────────────

def run_all():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   AEGIS Phase 1 Knowledge Graph — Analysis Queries        ║")
    print("╚══════════════════════════════════════════════════════════╝")

    company_context_summary()
    applicable_regulations()
    ni_distribution()
    gap_analysis()
    coverage_analysis()
    coverage_by_domain()
    regulation_overlap()
    clause_article_traceability()

    print("\n" + "=" * 60)
    print("  ALL QUERIES COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_all()
