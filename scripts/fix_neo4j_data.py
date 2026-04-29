#!/usr/bin/env python3
"""
fix_neo4j_data.py — Fase 0: Cleanup + Reload missing data

Removes NIST/Framework nodes and unlabeled nodes from the shared Neo4j instance,
then reloads Article nodes and SubDomain properties from the CSV source files.

Usage:
    python scripts/fix_neo4j_data.py [--verify-only]
"""

import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("ERROR: requests library not found. Run: pip install requests")
    sys.exit(1)

NEO4J_HTTP = "http://localhost:7474"
NEO4J_DB = "neo4j"
AUTH = ("neo4j", os.getenv("NEO4J_PASSWORD", ""))

DATA_DIR = Path(__file__).parent.parent / "aegis_kg" / "data"
SCHEMA_DIR = Path(__file__).parent.parent / "aegis_kg" / "schema"

REPORT_LINES = []


def log(msg: str):
    print(f"  {msg}")
    REPORT_LINES.append(msg)


def exec_cypher(statement: str, params: dict | None = None) -> dict:
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}
    try:
        resp = requests.post(
            f"{NEO4J_HTTP}/db/{NEO4J_DB}/tx/commit",
            auth=AUTH,
            json=payload,
            timeout=60
        )
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
        result = resp.json()
        if result.get("errors"):
            return {"error": result["errors"][0].get("message", "Unknown error")}
        return {"results": result.get("results", [])}
    except Exception as e:
        return {"error": str(e)}


def count_by_label() -> dict[str, int]:
    result = exec_cypher("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt ORDER BY cnt DESC")
    if "error" in result:
        return {"ERROR": result["error"]}
    data = {}
    for row in result["results"][0]["data"]:
        lbl = row["row"][0] or "(unlabeled)"
        data[lbl] = row["row"][1]
    return data


def count_rels() -> dict[str, int]:
    result = exec_cypher("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS cnt ORDER BY cnt DESC")
    if "error" in result:
        return {"ERROR": result["error"]}
    data = {}
    for row in result["results"][0]["data"]:
        data[row["row"][0]] = row["row"][1]
    return data


def delete_by_labels(labels: list[str]) -> int:
    if not labels:
        return 0
    label_match = "|".join(f":{l}" for l in labels)
    result = exec_cypher(f"MATCH (n) WHERE labels(n)[0] IN {labels} DETACH DELETE n")
    if "error" in result:
        return -1
    summary = result["results"][0]["data"]
    return summary[0]["row"][0] if summary else 0


def delete_unlabeled() -> int:
    result = exec_cypher("MATCH (n) WHERE size(labels(n)) = 0 DETACH DELETE n")
    if "error" in result:
        return -1
    summary = result["results"][0]["data"]
    return summary[0]["row"][0] if summary else 0


def step_report(step: int, description: str, before: dict, after: dict | None = None, deleted_count: int = -1):
    print(f"\n[Step {step}] {description}")
    log(f"\n[Step {step}] {description}")
    for label, cnt in before.items():
        delta = ""
        if after and label in after:
            d = after[label] - cnt
            delta = f" → {after[label]} ({d:+d})"
        log(f"  {label:30s}: {cnt:5d}{delta}")


print("=" * 60)
print("FASE 0: Neo4j Data Fix — Cleanup + Reload")
print("=" * 60)


print("\n[0] Snapshot BEFORE")
log("\n[BEFORE]")
counts_before = count_by_label()
rels_before = count_rels()
for lbl, cnt in counts_before.items():
    log(f"  {lbl:30s}: {cnt:5d}")
log(f"  {'TOTAL_NODES':30s}: {sum(counts_before.values()):5d}")

NIST_LABELS = ["NISTCategory", "NISTFunction", "Framework", "FrameworkCategory", "FrameworkControl"]
junk_found = [l for l in NIST_LABELS if l in counts_before]
print(f"\n  Junk labels found: {junk_found}")
unlabeled_found = counts_before.get("(unlabeled)", 0)
print(f"  Unlabeled nodes: {unlabeled_found}")



print("\n[1] Delete NIST/Framework labels (other KG data)")
log("\n[DELETE_JUNK]")
deleted_junk = 0
for label in NIST_LABELS:
    cnt = counts_before.get(label, 0)
    if cnt > 0:
        print(f"  Deleting {cnt} {label} nodes...")
        result = exec_cypher(f"MATCH (n:{label}) DETACH DELETE n")
        if "error" not in result:
            deleted_junk += cnt
            log(f"  DELETED {label}: {cnt}")
        else:
            log(f"  ERROR deleting {label}: {result['error']}")
print(f"  Total deleted (junk): {deleted_junk}")


print("\n[2] Delete unlabeled nodes")
deleted_unlabeled = delete_unlabeled()
log(f"  DELETED unlabeled: {deleted_unlabeled}")


print("\n[3] Delete OVERLAPS_WITH and HAS_CONTROL relationships (NIST leftover)")
result = exec_cypher("MATCH ()-[r:HAS_CONTROL|MAPS_TO_SUBDOMAIN]->() DELETE r")
if "error" in result:
    log(f"  WARNING: rel cleanup - {result['error']}")
else:
    log("  Deleted HAS_CONTROL and MAPS_TO_SUBDOMAIN rels")


counts_after_cleanup = count_by_label()
rels_after_cleanup = count_rels()
print("\n[4] Snapshot AFTER cleanup")
log("\n[AFTER_CLEANUP]")
for lbl, cnt in counts_after_cleanup.items():
    log(f"  {lbl:30s}: {cnt:5d}")
log(f"  {'TOTAL_NODES':30s}: {sum(counts_after_cleanup.values()):5d}")


print("\n[5] Load Article nodes from 03_articles.csv")
log("\n[LOAD_ARTICLES]")
articles_csv = DATA_DIR / "03_articles.csv"
if not articles_csv.exists():
    print(f"  ERROR: {articles_csv} not found")
    sys.exit(1)

article_count = 0
with open(articles_csv, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        article_id = row.get("articleId") or row.get("id", "")
        if not article_id:
            continue

        number = row.get("number", "")
        title = row.get("title", "")
        chapter = row.get("chapter", "")
        section = row.get("section", "")
        summary = row.get("summary", "")
        obligation_type = row.get("obligationType", "")
        regulation_id = row.get("regulationId", row.get("regulation", ""))

        cypher = """
        MATCH (r:Regulation {regulationId: $regId})
        CREATE (a:Article {
            articleId: $articleId,
            number: $number,
            title: $title,
            chapter: $chapter,
            section: $section,
            summary: $summary,
            obligationType: $obligationType
        })
        CREATE (r)-[:HAS_ARTICLE]->(a)
        """
        result = exec_cypher(cypher, {
            "regId": regulation_id,
            "articleId": article_id,
            "number": number,
            "title": title,
            "chapter": chapter,
            "section": section,
            "summary": summary,
            "obligationType": obligation_type
        })
        if "error" not in result:
            article_count += 1

log(f"  Loaded {article_count} Article nodes")


print("\n[6] Load Article-Clause links (DEFINES) from 04_clauses.csv")
log("\n[LOAD_DEFINES]")
clause_count = 0
with open(DATA_DIR / "04_clauses.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        clause_id = row.get("clauseId", "")
        article_ref = row.get("articleReference", row.get("articleId", ""))
        if not clause_id or not article_ref:
            continue

        cypher = """
        MATCH (a:Article {articleId: $articleRef})
        MATCH (c:Clause {clauseId: $clauseId})
        MERGE (a)-[:DEFINES]->(c)
        """
        result = exec_cypher(cypher, {"articleRef": article_ref, "clauseId": clause_id})
        if "error" not in result:
            clause_count += 1

log(f"  Created {clause_count} DEFINES relationships")


print("\n[7] Load/Update SubDomain properties")
log("\n[UPDATE_SUBDOMAINS]")
subdomain_count = 0
with open(DATA_DIR / "02_subdomains.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        sd_id = row.get("subDomainId", "")
        name = row.get("name", "")
        description = row.get("description", "")
        sole_authority = row.get("soleAuthority", "")
        gap_risk = row.get("gapRisk", "")
        keywords = row.get("keywords", "")
        examples = row.get("examples", "")

        if not sd_id:
            continue

        cypher = """
        MATCH (sd:SubDomain {subDomainId: $sdId})
        SET sd.name = $name,
            sd.description = $description,
            sd.soleAuthority = $soleAuth,
            sd.gapRisk = $gapRisk,
            sd.keywords = $keywords,
            sd.examples = $examples
        """
        result = exec_cypher(cypher, {
            "sdId": sd_id,
            "name": name,
            "description": description,
            "soleAuth": sole_authority,
            "gapRisk": gap_risk,
            "keywords": keywords,
            "examples": examples
        })
        if "error" not in result:
            subdomain_count += 1

log(f"  Updated {subdomain_count} SubDomain nodes")


print("\n[8] Verify final state")
log("\n[FINAL_VERIFY]")
counts_final = count_by_label()
rels_final = count_rels()
log(f"\n  Nodes by label:")
for lbl, cnt in counts_final.items():
    log(f"    {lbl:30s}: {cnt:5d}")
log(f"    {'TOTAL_NODES':30s}: {sum(counts_final.values()):5d}")

log(f"\n  Relationships by type:")
for rtype, cnt in rels_final.items():
    log(f"    {rtype:30s}: {cnt:5d}")
log(f"    {'TOTAL_RELS':30s}: {sum(rels_final.values()):5d}")

EXPECTED = {
    "Regulation": 5,
    "Article": 47,
    "Clause": 150,
    "Domain": 10,
    "SubDomain": 38,
}
print("\n  Verification:")
all_ok = True
for label, expected in EXPECTED.items():
    actual = counts_final.get(label, 0)
    status = "OK" if actual == expected else "FAIL"
    if actual != expected:
        all_ok = False
    print(f"    {label}: {actual}/{expected} [{status}]")

if all_ok:
    print("\n  ALL CHECKS PASSED")
else:
    print("\n  SOME CHECKS FAILED — review above")

print("\n" + "=" * 60)
print("FASE 0 COMPLETE")
print("=" * 60)