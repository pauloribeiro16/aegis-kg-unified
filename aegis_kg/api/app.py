#!/usr/bin/env python3
"""
AEGIS Phase 1 Knowledge Graph - REST API
Flask-based API providing endpoints for regulation queries, gap analysis, coverage, and traceability.
"""
from flask import Flask, jsonify, request
import requests as neo4j_requests
import os
from datetime import datetime

app = Flask(__name__)

# Neo4j Configuration
NEO4J_HTTP = os.getenv("NEO4J_URI", "http://localhost:7474")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")
AUTH = (NEO4J_USER, NEO4J_PASSWORD)

# ── Helper Functions ──────────────────────────────────────────────────────

def exec_cypher(statement, params=None):
    """Execute a Cypher query and return results"""
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}
    try:
        response = neo4j_requests.post(
            f"{NEO4J_HTTP}/db/neo4j/tx/commit",
            auth=AUTH,
            json=payload,
            timeout=30
        )
        if response.status_code != 200:
            return {"error": f"Neo4j HTTP {response.status_code}", "details": response.text[:500]}
        result = response.json()
        if result.get('errors'):
            return {"error": result['errors'][0].get('message', 'Unknown error')}
        return result.get('results', [])
    except Exception as e:
        return {"error": str(e)}

def format_results(results):
    """Format Neo4j results into a list of dicts"""
    if not results or 'data' not in results[0]:
        return []
    columns = results[0].get('columns', [])
    data = []
    for row in results[0]['data']:
        data.append(dict(zip(columns, row['row'])))
    return data

# ── API Routes ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """API documentation and health check"""
    return jsonify({
        "name": "AEGIS Knowledge Graph API",
        "version": "3.0.0",
        "status": "operational",
        "phases": {
            "phase1": "Regulations, Clauses, Domains, SubDomains",
            "phase2": "Obligations, Tensions, Goals, Rules",
            "phase3": "NFRs, FRs, Threats, Risks, Mitigations"
        },
        "endpoints": {
            "GET /api/regulations": "List all regulations",
            "GET /api/regulations/<reg_id>/clauses": "List clauses for a regulation",
            "GET /api/clauses": "Search clauses (optional ?keyword=<term>)",
            "GET /api/clauses/<clause_id>": "Get clause details",
            "GET /api/gap-analysis": "Identify uncovered sub-domains",
            "GET /api/coverage": "Coverage analysis by regulation and domain",
            "GET /api/applicability": "Applicable regulations and clauses",
            "GET /api/traceability": "Clause-to-article traceability",
            "GET /api/traceability/full": "Full traceability (Reg→Clause→Obl→Goal→Rule)",
            "GET /api/overlap": "Regulation overlap analysis",
            "GET /api/domains": "List all domains and sub-domains",
            "GET /api/obligations": "List all obligations (Phase 2)",
            "GET /api/obligations/<id>": "Get obligation details with traceability (Phase 2)",
            "GET /api/tensions": "List strategic tensions (Phase 2)",
            "GET /api/goals": "List goals (Phase 2, optional ?category=PRIVACY|SECURITY)",
            "GET /api/rules": "List rules (Phase 2, optional ?category=COMPLIANCE|BEST_PRACTICE)",
            "GET /api/nfrs": "List NFRs (Phase 3, optional ?category=CONFIDENTIALITY|...)",
            "GET /api/frs": "List FRs (Phase 3, optional ?domain=IAM|DP|SEC|DEV|GOV|TRN)",
            "GET /api/threats": "List threats (Phase 3, optional ?framework=STRIDE|LINDDUN)",
            "GET /api/risks": "List risks (Phase 3)",
            "GET /api/mitigations": "List mitigations (Phase 3)",
            "GET /api/risk-dashboard": "Risk dashboard summary (Phase 3)",
            "GET /api/health": "System health check"
        },
        "documentation": "See docs/API_DOCUMENTATION.md"
    })

@app.route('/api/health')
def health():
    """Health check endpoint"""
    try:
        r = neo4j_requests.get(NEO4J_HTTP, auth=AUTH, timeout=5)
        if r.status_code == 200:
            version = r.json().get('neo4j_version', 'unknown')
            return jsonify({"status": "healthy", "neo4j_version": version})
        return jsonify({"status": "degraded", "neo4j_http_status": r.status_code})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

@app.route('/api/regulations', methods=['GET'])
def get_regulations():
    """List all regulations"""
    cypher = """
    MATCH (r:Regulation)
    RETURN r.regulationId AS regulationId, r.name AS name,
           r.fullName AS fullName, r.type AS type,
           r.effectiveDate AS effectiveDate, r.primaryFocus AS primaryFocus,
           r.notificationTimelines AS notificationTimelines
    ORDER BY r.name
    """
    results = exec_cypher(cypher)
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    data = format_results(results)
    for row in data:
        if row.get('notificationTimelines'):
            import json
            row['notificationTimelines'] = json.loads(row['notificationTimelines'])
    return jsonify(data)

@app.route('/api/regulations/<reg_id>/clauses', methods=['GET'])
def get_regulation_clauses(reg_id):
    """List all clauses for a specific regulation"""
    cypher = """
    MATCH (r:Regulation {regulationId: $regId})-[:HAS_CLAUSE]->(c:Clause)
    OPTIONAL MATCH (a:Article)-[:DEFINES]->(c)
    RETURN c.clauseId AS clauseId, c.number AS number, c.summary AS summary,
           c.applicable AS applicable, c.normativeIntensity AS normativeIntensity,
           c.obligationType AS obligationType, a.articleId AS articleId
    ORDER BY c.clauseId
    """
    results = exec_cypher(cypher, {"regId": reg_id})
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))

@app.route('/api/clauses', methods=['GET'])
def search_clauses():
    """Search clauses by keyword"""
    keyword = request.args.get('keyword', '')
    if not keyword or len(keyword) < 2:
        return jsonify({"error": "Keyword must be at least 2 characters"}), 400

    cypher = """
    MATCH (c:Clause)
    WHERE toLower(c.summary) CONTAINS toLower($keyword)
       OR toLower(c.description) CONTAINS toLower($keyword)
    MATCH (r:Regulation)-[:HAS_CLAUSE]->(c)
    RETURN r.regulationId AS regulationId, c.clauseId AS clauseId, 
           c.summary AS summary, c.applicable AS applicable,
           c.normativeIntensity AS normativeIntensity,
           c.obligationType AS obligationType
    ORDER BY c.normativeIntensity DESC, c.clauseId
    """
    results = exec_cypher(cypher, {"keyword": keyword})
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))

@app.route('/api/clauses/<clause_id>', methods=['GET'])
def get_clause(clause_id):
    """Get detailed information about a specific clause"""
    cypher = """
    MATCH (c:Clause {clauseId: $clauseId})
    OPTIONAL MATCH (r:Regulation)-[:HAS_CLAUSE]->(c)
    OPTIONAL MATCH (a:Article)-[:DEFINES]->(c)
    OPTIONAL MATCH (c)-[:MAPPED_TO]->(sd:SubDomain)
    OPTIONAL MATCH (d:Domain)-[:HAS_SUBDOMAIN]->(sd)
    RETURN c.clauseId AS clauseId, c.number AS number, c.summary AS summary,
           c.description AS description, c.applicable AS applicable,
           c.normativeIntensity AS normativeIntensity, 
           c.obligationType AS obligationType,
           c.applicabilityReason AS applicabilityReason,
           r.regulationId AS regulationId, r.name AS regulationName,
           a.articleId AS articleId, a.title AS articleTitle,
           collect(DISTINCT sd.subDomainId) AS subDomains,
           collect(DISTINCT d.domainId) AS domains
    """
    results = exec_cypher(cypher, {"clauseId": clause_id})
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    data = format_results(results)
    if not data:
        return jsonify({"error": f"Clause {clause_id} not found"}), 404
    return jsonify(data[0])

@app.route('/api/gap-analysis', methods=['GET'])
def gap_analysis():
    """Identify sub-domains with NO clause coverage"""
    cypher = """
    MATCH (sd:SubDomain)
    WHERE NOT (sd)<-[:MAPPED_TO]-(:Clause)
    OPTIONAL MATCH (d:Domain)-[:HAS_SUBDOMAIN]->(sd)
    RETURN sd.subDomainId AS subDomainId, sd.name AS name, 
           sd.description AS description, d.domainId AS domainId,
           d.name AS domainName, sd.gapRisk AS riskLevel
    ORDER BY sd.subDomainId
    """
    results = exec_cypher(cypher)
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))

@app.route('/api/coverage', methods=['GET'])
def coverage():
    """Coverage analysis by regulation, domain, and subdomain (Batch 9: dynamic density)"""
    reg_cypher = """
    MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)-[:MAPPED_TO]->(sd:SubDomain)
    WITH r.regulationId AS reg, r.name AS regName,
         count(DISTINCT sd) AS regCoverage,
         r.effectiveCoverageScore AS effectiveCoverageScore,
         r.effectiveCoverageTier AS effectiveCoverageTier
    WITH count(sd) AS totalSD, reg, regName, regCoverage, effectiveCoverageScore, effectiveCoverageTier
    RETURN reg, regName, regCoverage, totalSD,
           round(100.0 * regCoverage / totalSD, 1) AS coveragePct,
           effectiveCoverageScore, effectiveCoverageTier
    ORDER BY effectiveCoverageScore DESC
    """
    reg_results = exec_cypher(reg_cypher)

    domain_cypher = """
    MATCH (d:Domain)-[:HAS_SUBDOMAIN]->(sd:SubDomain)
    OPTIONAL MATCH (sd)<-[:MAPPED_TO]-(:Clause)
    WITH d.domainId AS domain, d.name AS domainName,
         count(sd) AS totalInDomain,
         count(DISTINCT CASE WHEN (sd)<-[:MAPPED_TO]-(:Clause) THEN sd END) AS covered
    RETURN domain, domainName, totalInDomain, covered,
           round(100.0 * covered / totalInDomain, 1) AS coveragePct
    ORDER BY domain
    """
    domain_results = exec_cypher(domain_cypher)

    summary_cypher = """
    MATCH (sd:SubDomain)
    WITH count(sd) AS total
    OPTIONAL MATCH (sd:SubDomain)<-[:MAPPED_TO]-(:Clause)
    WITH total, count(DISTINCT sd) AS covered
    RETURN total, covered, round(100.0 * covered / total, 1) AS overallPct
    """
    summary_results = exec_cypher(summary_cypher)

    subdomain_cypher = """
    MATCH (d:Domain)-[:HAS_SUBDOMAIN]->(sd:SubDomain)
    RETURN d.domainId AS domainId, d.name AS domainName,
           sd.subDomainId AS subDomainId, sd.name AS subDomainName,
           sd.clauseCount AS clauseCount,
           sd.regulationCount AS regulationCount,
           sd.densityScore AS densityScore,
           sd.avgNormativeIntensity AS avgNI,
           sd.weightedDensity AS weightedDensity,
           sd.coveringRegulations AS coveringRegulations,
           sd.effectiveCoverage AS effectiveCoverage,
           sd.effectiveCoverageTier AS effectiveCoverageTier
    ORDER BY domainId, subDomainId
    """
    subdomain_results = exec_cypher(subdomain_cypher)

    response = {
        "by_regulation": format_results(reg_results) if not isinstance(reg_results, dict) or 'error' not in reg_results else [],
        "by_domain": format_results(domain_results) if not isinstance(domain_results, dict) or 'error' not in domain_results else [],
        "by_subdomain": format_results(subdomain_results) if not isinstance(subdomain_results, dict) or 'error' not in subdomain_results else [],
        "summary": format_results(summary_results)[0] if summary_results and not isinstance(summary_results, dict) else {}
    }
    return jsonify(response)

@app.route('/api/applicability', methods=['GET'])
def applicability():
    """Show applicable regulations and clause counts"""
    cypher = """
    MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)
    WITH r.regulationId AS regId, r.name AS name, 
         count(c) AS applicableClauses, collect(c.clauseId) AS clauses
    RETURN regId, name, applicableClauses, clauses
    ORDER BY applicableClauses DESC
    """
    results = exec_cypher(cypher)
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))

@app.route('/api/traceability', methods=['GET'])
def traceability():
    """Clause-to-article traceability"""
    cypher = """
    MATCH (a:Article)-[:DEFINES]->(c:Clause)
    MATCH (r:Regulation)-[:HAS_ARTICLE]->(a)
    RETURN r.regulationId AS regulationId, a.articleId AS articleId, 
           a.title AS articleTitle, a.number AS articleNumber,
           count(c) AS clauseCount, collect(c.clauseId) AS clauseIds
    ORDER BY r.regulationId, a.articleId
    """
    results = exec_cypher(cypher)
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))

@app.route('/api/overlap', methods=['GET'])
def overlap():
    """Regulation overlap analysis using ComplementarityAnalysis nodes (Batch 9: dynamic Jaccard)"""
    cypher = """
    MATCH (ca:ComplementarityAnalysis)-[:OVERLAPS_WITH]->(r:Regulation)
    WITH ca, collect(r.regulationId) AS regs
    RETURN ca.analysisId AS analysisId,
           regs[0] AS regulation1,
           regs[1] AS regulation2,
           ca.dynamicSharedSubDomainCount AS sharedSubDomains,
           ca.totalUniqueSubDomains AS totalUnique,
           ca.dynamicJaccard AS jaccardIndex,
           ca.complementarityIndex AS complementarityIndex,
           ca.conflictClassification AS conflictType,
           ca.overlapDescription AS overlapDescription,
           ca.conflictDescription AS conflictDescription,
           ca.recommendedApproach AS recommendedApproach,
           ca.jaccardSource AS jaccardSource
    ORDER BY jaccardIndex DESC
    """
    results = exec_cypher(cypher)
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))

@app.route('/api/domains', methods=['GET'])
def get_domains():
    """List all domains and their sub-domains with density metrics (Batch 9)"""
    cypher = """
    MATCH (d:Domain)-[:HAS_SUBDOMAIN]->(sd:SubDomain)
    RETURN d.domainId AS domainId, d.name AS domainName, d.description AS domainDescription,
           sd.subDomainId AS subDomainId, sd.name AS subDomainName,
           sd.description AS subDomainDescription,
           sd.clauseCount AS clauseCount,
           sd.regulationCount AS regulationCount,
           sd.densityScore AS densityScore,
           sd.avgNormativeIntensity AS avgNI,
           sd.weightedDensity AS weightedDensity,
           sd.coveringRegulations AS coveringRegulations,
           CASE WHEN sd.clauseCount > 0 THEN true ELSE false END AS hasCoverage
    ORDER BY domainId, subDomainId
    """
    results = exec_cypher(cypher)
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500

    domains = {}
    for row in format_results(results):
        did = row['domainId']
        if did not in domains:
            domains[did] = {
                "domainId": did,
                "name": row['domainName'],
                "description": row['domainDescription'],
                "subdomains": []
            }
        domains[did]['subdomains'].append({
            "subDomainId": row['subDomainId'],
            "name": row['subDomainName'],
            "description": row['subDomainDescription'],
            "hasCoverage": row['hasCoverage'],
            "clauseCount": row.get('clauseCount') or 0,
            "regulationCount": row.get('regulationCount') or 0,
            "densityScore": row.get('densityScore') or 0.0,
            "avgNormativeIntensity": row.get('avgNI') or 0.0,
            "weightedDensity": row.get('weightedDensity') or 0.0,
            "coveringRegulations": row.get('coveringRegulations') or []
        })

    return jsonify(list(domains.values()))


@app.route('/api/sole-authority', methods=['GET'])
def get_sole_authority():
    """List sub-domains with sole authority (only one regulation covers them)"""
    cypher = """
    MATCH (sd:SubDomain)-[:SOLE_AUTHORITY]->(r:Regulation)
    RETURN sd.subDomainId AS subDomainId,
           sd.name AS subDomainName,
           r.regulationId AS soleAuthorityRegulator,
           r.name AS soleAuthorityRegulatorName,
           sd.gapRisk AS gapRisk
    ORDER BY sd.subDomainId
    """
    results = exec_cypher(cypher)
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))


@app.route('/api/interactions', methods=['GET'])
def get_regulatory_interactions():
    """Full regulatory interaction summary: overlaps, tensions, timelines (Batch 9)"""
    overlap_cypher = """
    MATCH (ca:ComplementarityAnalysis)-[:OVERLAPS_WITH]->(r:Regulation)
    WITH ca, collect(r.regulationId) AS regs
    RETURN ca.analysisId AS id,
           regs[0] AS reg1,
           regs[1] AS reg2,
           ca.dynamicSharedSubDomainCount AS sharedSD,
           ca.dynamicJaccard AS jaccard,
           ca.conflictClassification AS conflictType,
           ca.recommendedApproach AS resolution
    ORDER BY jaccard DESC
    """
    timeline_cypher = """
    MATCH (r:Regulation)
    WHERE r.notificationTimelines IS NOT NULL
    RETURN r.regulationId AS regId,
           r.name AS regName,
           r.notificationTimelines AS timelines
    ORDER BY regId
    """
    overlap_results = exec_cypher(overlap_cypher)
    timeline_results = exec_cypher(timeline_cypher)

    import json
    overlaps = format_results(overlap_results) if not isinstance(overlap_results, dict) else []
    timelines = []
    if not isinstance(timeline_results, dict):
        for row in format_results(timeline_results):
            row['timelines'] = json.loads(row['timelines']) if row.get('timelines') else []
            timelines.append(row)

    return jsonify({
        "regulationPairs": overlaps,
        "timelines": timelines,
        "counts": {
            "pairs": len(overlaps),
            "regulationsWithTimelines": len(timelines)
        }
    })


@app.route('/api/timelines', methods=['GET'])
def get_timelines():
    """Comparative regulatory timelines across all applicable regulations"""
    cypher = """
    MATCH (r:Regulation)
    WHERE r.notificationTimelines IS NOT NULL
    RETURN r.regulationId AS regId,
           r.name AS regName,
           r.notificationTimelines AS timelines
    ORDER BY regId
    """
    results = exec_cypher(cypher)
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    import json
    data = []
    for row in format_results(results):
        row['timelines'] = json.loads(row['timelines']) if row.get('timelines') else []
        data.append(row)
    return jsonify(data)


# ── Phase 2 API Routes ─────────────────────────────────────────────────────

@app.route('/api/obligations', methods=['GET'])
def get_obligations():
    """List all obligations with optional sub-domain filter"""
    subdomain = request.args.get('subdomain', '')
    if subdomain:
        cypher = """
        MATCH (o:Obligation {targetSubDomain: $subdomain})
        RETURN o.obligationId AS obligationId, o.description AS description,
               o.targetSubDomain AS targetSubDomain, o.obligationType AS obligationType,
               o.normativeIntensity AS normativeIntensity, o.obligatedParty AS obligatedParty,
               o.sourceClauses AS sourceClauses
        ORDER BY o.normativeIntensity DESC, o.obligationId
        """
        results = exec_cypher(cypher, {"subdomain": subdomain})
    else:
        cypher = """
        MATCH (o:Obligation)
        RETURN o.obligationId AS obligationId, o.description AS description,
               o.targetSubDomain AS targetSubDomain, o.obligationType AS obligationType,
               o.normativeIntensity AS normativeIntensity, o.obligatedParty AS obligatedParty,
               o.sourceClauses AS sourceClauses
        ORDER BY o.normativeIntensity DESC, o.obligationId
        """
        results = exec_cypher(cypher)
    
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))

@app.route('/api/obligations/<obligation_id>', methods=['GET'])
def get_obligation(obligation_id):
    """Get detailed obligation with traceability"""
    cypher = """
    MATCH (o:Obligation {obligationId: $obligationId})
    OPTIONAL MATCH (o)-[:DERIVES_FROM]->(c:Clause)
    OPTIONAL MATCH (o)-[:TARGETS_SUBDOMAIN]->(sd:SubDomain)
    OPTIONAL MATCH (o)-[:FORMALIZES]->(g:Goal)
    OPTIONAL MATCH (o)<-[:INVOLVES_OBLIGATION]-(t:StrategicTension)
    RETURN o.obligationId AS obligationId, o.description AS description,
           o.targetSubDomain AS targetSubDomain, o.obligationType AS obligationType,
           o.normativeIntensity AS normativeIntensity, o.obligatedParty AS obligatedParty,
           o.sourceClauses AS sourceClauses,
           collect(DISTINCT c.clauseId) AS derivedFromClauses,
           collect(DISTINCT sd.subDomainId) AS targetSubDomains,
           collect(DISTINCT g.goalId) AS formalizedGoals,
           collect(DISTINCT {tensionId: t.tensionId, type: t.tensionType, severity: t.severity}) AS tensions
    """
    results = exec_cypher(cypher, {"obligationId": obligation_id})
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    data = format_results(results)
    if not data:
        return jsonify({"error": f"Obligation {obligation_id} not found"}), 404
    return jsonify(data[0])

@app.route('/api/tensions', methods=['GET'])
def get_tensions():
    """List all strategic tensions"""
    severity = request.args.get('severity', '')
    if severity:
        cypher = """
        MATCH (t:StrategicTension {severity: $severity})
        RETURN t.tensionId AS tensionId, t.tensionType AS tensionType,
               t.severity AS severity, t.description AS description,
               t.resolutionStrategy AS resolutionStrategy, t.status AS status,
               t.obligation1Id AS obligation1Id, t.obligation2Id AS obligation2Id
        ORDER BY t.severity DESC, t.tensionId
        """
        results = exec_cypher(cypher, {"severity": severity})
    else:
        cypher = """
        MATCH (t:StrategicTension)
        RETURN t.tensionId AS tensionId, t.tensionType AS tensionType,
               t.severity AS severity, t.description AS description,
               t.resolutionStrategy AS resolutionStrategy, t.status AS status,
               t.obligation1Id AS obligation1Id, t.obligation2Id AS obligation2Id
        ORDER BY t.severity DESC, t.tensionId
        """
        results = exec_cypher(cypher)
    
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))

@app.route('/api/goals', methods=['GET'])
def get_goals():
    """List all goals with optional category filter"""
    category = request.args.get('category', '')
    if category:
        cypher = """
        MATCH (g:Goal {category: $category})
        RETURN g.goalId AS goalId, g.description AS description,
               g.category AS category, g.priority AS priority,
               g.riskProfile AS riskProfile, g.targetSubDomain AS targetSubDomain,
               g.goalStatement AS goalStatement, g.sourceObligations AS sourceObligations
        ORDER BY g.priority DESC, g.goalId
        """
        results = exec_cypher(cypher, {"category": category})
    else:
        cypher = """
        MATCH (g:Goal)
        RETURN g.goalId AS goalId, g.description AS description,
               g.category AS category, g.priority AS priority,
               g.riskProfile AS riskProfile, g.targetSubDomain AS targetSubDomain,
               g.goalStatement AS goalStatement, g.sourceObligations AS sourceObligations
        ORDER BY g.priority DESC, g.goalId
        """
        results = exec_cypher(cypher)
    
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))

@app.route('/api/rules', methods=['GET'])
def get_rules():
    """List all rules with optional category filter"""
    category = request.args.get('category', '')
    if category:
        cypher = """
        MATCH (r:Rule {category: $category})
        RETURN r.ruleId AS ruleId, r.description AS description,
               r.category AS category, r.normativeIntensity AS normativeIntensity,
               r.targetSubDomain AS targetSubDomain, r.isMandatory AS isMandatory,
               r.regulatoryReference AS regulatoryReference, r.sourceType AS sourceType,
               r.sourceObligations AS sourceObligations, r.sourceGoals AS sourceGoals
        ORDER BY r.normativeIntensity DESC, r.ruleId
        """
        results = exec_cypher(cypher, {"category": category})
    else:
        cypher = """
        MATCH (r:Rule)
        RETURN r.ruleId AS ruleId, r.description AS description,
               r.category AS category, r.normativeIntensity AS normativeIntensity,
               r.targetSubDomain AS targetSubDomain, r.isMandatory AS isMandatory,
               r.regulatoryReference AS regulatoryReference, r.sourceType AS sourceType,
               r.sourceObligations AS sourceObligations, r.sourceGoals AS sourceGoals
        ORDER BY r.normativeIntensity DESC, r.ruleId
        """
        results = exec_cypher(cypher)
    
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))

@app.route('/api/traceability/full', methods=['GET'])
def full_traceability():
    """Full traceability: Regulation → Clause → Obligation → Goal → Rule"""
    cypher = """
    MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)
    OPTIONAL MATCH (c)<-[:DERIVES_FROM]-(o:Obligation)
    OPTIONAL MATCH (o)-[:FORMALIZES]->(g:Goal)
    OPTIONAL MATCH (r2:Rule)-[:DERIVED_FROM_OBLIGATION]->(o)
    RETURN r.regulationId AS regulation, c.clauseId AS clause,
           o.obligationId AS obligation, g.goalId AS goal,
           r2.ruleId AS rule, r2.category AS ruleCategory
    ORDER BY r.regulationId, c.clauseId, o.obligationId
    """
    results = exec_cypher(cypher)
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))

# ── Phase 3 API Routes ─────────────────────────────────────────────────────

@app.route('/api/nfrs', methods=['GET'])
def get_nfrs():
    """List all NFRs with optional category filter"""
    category = request.args.get('category', '')
    if category:
        cypher = """
        MATCH (n:NFR {category: $category})
        RETURN n.nfrId AS nfrId, n.description AS description,
               n.category AS category, n.priority AS priority,
               n.metric AS metric, n.target AS target,
               n.verificationMethod AS verificationMethod,
               n.sourceRegulation AS sourceRegulation
        ORDER BY n.priority DESC, n.nfrId
        """
        results = exec_cypher(cypher, {"category": category})
    else:
        cypher = """
        MATCH (n:NFR)
        RETURN n.nfrId AS nfrId, n.description AS description,
               n.category AS category, n.priority AS priority,
               n.metric AS metric, n.target AS target,
               n.verificationMethod AS verificationMethod,
               n.sourceRegulation AS sourceRegulation
        ORDER BY n.priority DESC, n.nfrId
        """
        results = exec_cypher(cypher)
    
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))

@app.route('/api/frs', methods=['GET'])
def get_frs():
    """List all FRs with optional domain filter"""
    domain = request.args.get('domain', '')
    if domain:
        cypher = """
        MATCH (f:FR {domain: $domain})
        RETURN f.frId AS frId, f.description AS description,
               f.domain AS domain, f.priority AS priority,
               f.verificationMethod AS verificationMethod,
               f.sourceObligations AS sourceObligations,
               f.sourceNFRs AS sourceNFRs
        ORDER BY f.priority DESC, f.frId
        """
        results = exec_cypher(cypher, {"domain": domain})
    else:
        cypher = """
        MATCH (f:FR)
        RETURN f.frId AS frId, f.description AS description,
               f.domain AS domain, f.priority AS priority,
               f.verificationMethod AS verificationMethod,
               f.sourceObligations AS sourceObligations,
               f.sourceNFRs AS sourceNFRs
        ORDER BY f.priority DESC, f.frId
        """
        results = exec_cypher(cypher)
    
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))

@app.route('/api/threats', methods=['GET'])
def get_threats():
    """List all threats with optional framework filter"""
    framework = request.args.get('framework', '')
    if framework:
        cypher = """
        MATCH (t:Threat {framework: $framework})
        RETURN t.threatId AS threatId, t.description AS description,
               t.category AS category, t.framework AS framework,
               t.attackVector AS attackVector,
               t.affectedComponents AS affectedComponents
        ORDER BY t.category, t.threatId
        """
        results = exec_cypher(cypher, {"framework": framework})
    else:
        cypher = """
        MATCH (t:Threat)
        RETURN t.threatId AS threatId, t.description AS description,
               t.category AS category, t.framework AS framework,
               t.attackVector AS attackVector,
               t.affectedComponents AS affectedComponents
        ORDER BY t.category, t.threatId
        """
        results = exec_cypher(cypher)
    
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))

@app.route('/api/risks', methods=['GET'])
def get_risks():
    """List all risks"""
    cypher = """
    MATCH (r:Risk)
    RETURN r.riskId AS riskId, r.description AS description,
           r.threatId AS threatId, r.vulnerabilityId AS vulnerabilityId,
           r.likelihood AS likelihood, r.impact AS impact,
           r.riskLevel AS riskLevel, r.residualRisk AS residualRisk,
           r.decision AS decision, r.justification AS justification
    ORDER BY r.riskLevel DESC, r.riskId
    """
    results = exec_cypher(cypher)
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))

@app.route('/api/mitigations', methods=['GET'])
def get_mitigations():
    """List all mitigations"""
    cypher = """
    MATCH (m:Mitigation)
    RETURN m.mitigationId AS mitigationId, m.description AS description,
           m.strategy AS strategy, m.riskId AS riskId,
           m.status AS status, m.effectivenessRating AS effectivenessRating
    ORDER BY m.effectivenessRating DESC, m.mitigationId
    """
    results = exec_cypher(cypher)
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify(format_results(results))

@app.route('/api/risk-dashboard', methods=['GET'])
def risk_dashboard():
    """Risk dashboard with summary statistics"""
    cypher = """
    MATCH (r:Risk)
    WITH r.riskLevel AS level, count(*) AS count
    RETURN level, count
    ORDER BY count DESC
    """
    risk_counts = exec_cypher(cypher)
    
    cypher = """
    MATCH (m:Mitigation)
    WITH m.status AS status, count(*) AS count
    RETURN status, count
    """
    mitigation_counts = exec_cypher(cypher)
    
    cypher = """
    MATCH (t:Threat)
    WITH t.framework AS framework, count(*) AS count
    RETURN framework, count
    """
    threat_counts = exec_cypher(cypher)
    
    return jsonify({
        "risk_levels": format_results(risk_counts) if not isinstance(risk_counts, dict) or 'error' not in risk_counts else [],
        "mitigation_status": format_results(mitigation_counts) if not isinstance(mitigation_counts, dict) or 'error' not in mitigation_counts else [],
        "threat_frameworks": format_results(threat_counts) if not isinstance(threat_counts, dict) or 'error' not in threat_counts else []
    })

# ── Error Handlers ─────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("  AEGIS Phase 1 Knowledge Graph API")
    print("=" * 60)
    print(f"  Starting server on http://localhost:5000")
    print(f"  Neo4j URI: {NEO4J_HTTP}")
    print(f"  API Documentation: http://localhost:5000/")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
