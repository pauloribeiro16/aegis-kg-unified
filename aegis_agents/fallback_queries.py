"""Fallback Cypher query templates for graceful degradation.

When the LLM fails to generate valid Cypher after multiple attempts,
these templates provide pre-built queries for common question patterns.
"""

import re


FALLBACK_QUERIES = [
    {
        "pattern": r"(?i)(how many|count).*(clause|clauses).*(gdpr|craz|nis2|dora|ai\s*act)",
        "template": "MATCH (c:Clause {regulationId: '{reg}'}) RETURN count(c) AS total",
        "extract": {"reg": r"(?i)(gdpr|cra|nis2|dora|aiact)"},
    },
    {
        "pattern": r"(?i)(how many|count|total).*(clause|clauses)",
        "template": "MATCH (c:Clause) RETURN count(c) AS total",
    },
    {
        "pattern": r"(?i)(how many|count).*(article|articles)",
        "template": "MATCH (a:Article) RETURN count(a) AS total",
    },
    {
        "pattern": r"(?i)(list|show|all|what).*(regulation|regulations)",
        "template": "MATCH (r:Regulation) RETURN r.regulationId AS id, r.name AS name, r.primaryFocus AS focus ORDER BY r.regulationId",
    },
    {
        "pattern": r"(?i)(list|show|all|what).*(domain|domains)",
        "template": "MATCH (d:Domain) RETURN d.domainId AS id, d.name AS name ORDER BY d.domainId",
    },
    {
        "pattern": r"(?i)(list|show|all|what).*(subdomain|subdomains|sub-domain|sub-domains)",
        "template": "MATCH (sd:SubDomain) RETURN sd.subDomainId AS id, sd.name AS name ORDER BY sd.subDomainId",
    },
    {
        "pattern": r"(?i)(gap|uncover|not cover|no coverage|missing)",
        "template": "MATCH (sd:SubDomain) WHERE NOT EXISTS((:Clause)-[:MAPPED_TO]->(sd)) OPTIONAL MATCH (d:Domain)-[:CONTAINS]->(sd) RETURN sd.subDomainId AS id, sd.name AS name, d.name AS domain, sd.gapRisk AS risk ORDER BY sd.subDomainId",
    },
    {
        "pattern": r"(?i)(sole authority|exclusive|only one)",
        "template": "MATCH (sd:SubDomain) WHERE sd.soleAuthority IS NOT NULL AND sd.soleAuthority <> '' RETURN sd.subDomainId AS id, sd.name AS name, sd.soleAuthority AS sole ORDER BY sd.soleAuthority",
    },
    {
        "pattern": r"(?i)(overlap|jaccard|complementar)",
        "template": "MATCH (ca:ComplementarityAnalysis)-[:OVERLAPS_WITH]->(r:Regulation) WITH ca, collect(r.regulationId) AS regs RETURN regs[0] AS reg1, regs[1] AS reg2, ca.jaccardIndex AS jaccard, ca.conflictClassification AS conflict ORDER BY ca.jaccardIndex DESC",
    },
    {
        "pattern": r"(?i)(nist).*(function|functions|category|categories)",
        "template": "MATCH (fc:FrameworkCategory {type: 'FUNCTION'}) RETURN fc.functionCode AS code, fc.name AS name ORDER BY fc.functionCode",
    },
    {
        "pattern": r"(?i)(nist).*(control|controls).*(pr|gv|id|de|rs|rc)",
        "template": "MATCH (fc:FrameworkControl) WHERE fc.functionCode = '{func}' RETURN fc.controlId AS id, fc.title AS title ORDER BY fc.controlId",
        "extract": {"func": r"(?i)\b(pr|gv|id|de|rs|rc)\b"},
    },
    {
        "pattern": r"(?i)(how many|count).*(nist).*(control|controls)",
        "template": "MATCH (fc:FrameworkControl) RETURN count(fc) AS total",
    },
    {
        "pattern": r"(?i)(tension|conflict|contradict)",
        "template": "MATCH (st:StrategicTension) RETURN st.tensionId AS id, st.severity AS severity, st.description AS description ORDER BY st.severity DESC",
    },
    {
        "pattern": r"(?i)(timeline|deadline|notification|effective)",
        "template": "MATCH (r:Regulation) WHERE r.notificationTimelines IS NOT NULL RETURN r.regulationId AS regId, r.name AS name, r.notificationTimelines AS timelines ORDER BY regId",
    },
    {
        "pattern": r"(?i)(coverage|cover|mapped|how many).*(domain|subdomain)",
        "template": "MATCH (d:Domain)-[:CONTAINS]->(sd:SubDomain)<-[:MAPPED_TO]-(c:Clause) RETURN d.name AS domain, count(DISTINCT c) AS clauseCount, count(DISTINCT sd) AS coveredSubDomains ORDER BY clauseCount DESC",
    },
]


def _extract_param(question: str, extract_rules: dict) -> dict:
    """Extract parameters from question using regex rules."""
    params = {}
    for param_name, pattern in extract_rules.items():
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            params[param_name] = match.group(1).upper() if param_name == "reg" else match.group(1).upper()
            if param_name == "reg" and params[param_name] == "AIACT":
                params[param_name] = "AIAct"
    return params


def find_fallback(question: str) -> str | None:
    """Find a matching fallback Cypher template for the question.

    Returns:
        Compiled Cypher string, or None if no pattern matches.
    """
    for entry in FALLBACK_QUERIES:
        if re.search(entry["pattern"], question):
            template = entry["template"]
            if "extract" in entry:
                params = _extract_param(question, entry["extract"])
                for key, value in params.items():
                    template = template.replace("{" + key + "}", value)
                if "{" in template and "}" in template:
                    continue
            return template
    return None
