"""Langfuse prompt management for Aegis agent."""

from aegis_agents.config import LANGFUSE_CONFIG


def get_langfuse_client():
    """Get Langfuse client singleton."""
    try:
        from langfuse import Langfuse
        return Langfuse(
            public_key=LANGFUSE_CONFIG["public_key"],
            secret_key=LANGFUSE_CONFIG["secret_key"],
            host=LANGFUSE_CONFIG["host"],
        )
    except ImportError:
        return None


PROMPTS = {
    "cypher_generation": {
        "name": "aegis-cypher-generation",
        "type": "text",
        "prompt": """You are a Neo4j Cypher expert. Given a question in natural language about the AEGIS regulatory knowledge graph, generate a valid Cypher query.

IMPORTANT RULES:
1. Only output the Cypher query — no explanations, no markdown, no commentary.
2. Use the schema provided. Node labels are: Regulation, Article, Clause, Domain, SubDomain, ComplementarityAnalysis, Framework, FrameworkCategory, FrameworkControl
3. Relationship types: HAS_ARTICLE, HAS_CLAUSE, DEFINES, CONTAINS, MAPPED_TO, OVERLAPS_WITH, HAS_CATEGORY, HAS_CONTROL, MAPS_TO_SUBDOMAIN, MAPS_TO_DOMAIN
4. Property names match exactly as defined in the schema.
5. For the SubDomain ID format use 'D-01.1' (DOT separator, D-XX.Y format).
6. For clause IDs use format like 'GDPR-C01', 'CRA-C07', etc.
7. For regulation IDs use 'GDPR', 'CRA', 'NIS2', 'DORA', 'AIAct'.
8. If the question is ambiguous, pick the most logical interpretation.

## AGGREGATION PATTERNS (use these patterns when the question asks for counts, averages, lists, or grouped data):

// Count total
MATCH (c:Clause) RETURN count(c) AS total

// Count grouped by property
MATCH (c:Clause) RETURN c.regulationId AS regulation, count(c) AS count ORDER BY count DESC

// Filter + count
MATCH (c:Clause {normativeIntensity: 3}) RETURN c.regulationId AS regulation, count(c) AS count ORDER BY count DESC

// Average by group
MATCH (d:Domain)-[:CONTAINS]->(sd:SubDomain)<-[:MAPPED_TO]-(c:Clause)
RETURN d.name AS domain, avg(c.normativeIntensity) AS avgNI ORDER BY avgNI DESC

// Collect related items into list (with limit)
MATCH (c:Clause {normativeIntensity: 3})-[:MAPPED_TO]->(sd:SubDomain)
RETURN c.regulationId AS regulation, count(c) AS criticalCount, collect(DISTINCT sd.name)[0..3] AS subdomains
ORDER BY criticalCount DESC

// Existence check (no rows = valid result, no retry needed)
MATCH (sd:SubDomain) WHERE NOT EXISTS((:Clause)-[:MAPPED_TO]->(sd)) RETURN sd.subDomainId, sd.name

SCHEMA:
{schema}

QUESTION: {question}

Generate the Cypher query:""",
    },
    "answer_generation": {
        "name": "aegis-answer-generation",
        "type": "text",
        "prompt": """You are a regulatory compliance expert answering questions about EU regulations and NIST CSF 2.0.

IMPORTANT: Trust the database results — they are the output of a verified query against the knowledge graph.
Never claim results are empty, missing, or that none exist when data is returned. If you don't understand the data, ask clarifying questions rather than denying the results.

SCHEMA CONTEXT:
- normativeIntensity: 1=MAY, 2=SHOULD, 3=SHALL
- obligationType: ONE_TIME, CONTINUOUS, TRIGGERED

QUESTION: {question}

EXECUTED CYPHER:
{cypher}

DATABASE RESULTS ({row_count} rows):
{results_text}

Provide a clear, concise answer based on the results. You may add regulatory context or interpretation to help the user understand the implications, but never contradict the data returned by the query.""",
    },
    "refinement": {
        "name": "aegis-refinement",
        "type": "text",
        "prompt": """You are a Neo4j Cypher expert. The previous Cypher query failed or returned empty results.

PREVIOUS QUERY: {previous_cypher}
ERROR: {error}
SCHEMA: {schema}
QUESTION: {question}

Generate an improved Cypher query that addresses the error. Only output the Cypher query — no explanations.""",
    },
    "judge_evaluation": {
        "name": "aegis-judge-evaluation",
        "type": "text",
        "prompt": """You are an expert evaluator for a regulatory knowledge graph agent.

Evaluate the following Cypher query and execution result:

QUESTION: {question}
 Cypher: {cypher}
RESULT: {result}
ERROR: {error}

Rate the following aspects on a scale of 1-5:
1. Cypher Correctness: Is the Cypher syntactically correct and semantically appropriate?
2. Query Effectiveness: Would this query likely return relevant results?
3. Feedback Loop Benefit: Would refinement help or is the query already optimal?

Provide your evaluation as a JSON object with these three scores.""",
    },
}


def setup_prompts_in_langfuse():
    """Create or replace prompts in Langfuse (delete existing then recreate)."""
    langfuse = get_langfuse_client()
    if not langfuse:
        print("  [Langfuse] Client not available, skipping prompt setup")
        return

    for key, prompt_config in PROMPTS.items():
        try:
            langfuse.delete_prompt(prompt_config["name"])
            print(f"  [Langfuse] Deleted prompt '{prompt_config['name']}'")
        except Exception:
            pass
        langfuse.create_prompt(
            name=prompt_config["name"],
            type=prompt_config["type"],
            prompt=prompt_config["prompt"],
            labels=["production"],
        )
        print(f"  [Langfuse] Created prompt '{prompt_config['name']}'")


def get_prompt(key: str, **kwargs) -> str:
    """Get a compiled prompt by key."""
    if key not in PROMPTS:
        raise ValueError(f"Unknown prompt key: {key}")

    template = PROMPTS[key]["prompt"]

    # Replace known placeholders directly first
    if "schema" in kwargs:
        template = template.replace("{schema}", kwargs.pop("schema"))
    if "question" in kwargs:
        template = template.replace("{question}", str(kwargs.pop("question")))

    # Escape remaining literal {brace patterns} in template examples
    # (e.g., {normativeIntensity: 3} in aggregation examples)
    # These look like format placeholders but are meant as literal text in Cypher examples
    import re
    for match in re.findall(r'\{[^}]+\}', template):
        template = template.replace(match, match.replace('{', '{{').replace('}', '}}'))

    # Substitute remaining kwargs via direct replace (not str.format(), to avoid {{ }} escaping issues)
    for k, v in kwargs.items():
        placeholder = "{" + k + "}"
        if placeholder in template:
            template = template.replace(placeholder, str(v))

    return template


def get_prompt_for_langfuse(key: str):
    """Get prompt config for Langfuse tracing."""
    if key not in PROMPTS:
        return None
    return PROMPTS[key]
