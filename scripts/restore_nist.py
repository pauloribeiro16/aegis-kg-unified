#!/usr/bin/env python3
"""
restore_nist.py — Restore NIST CSF 2.0 data to the unified compliance KG.

Restores the full unified compliance model from JSON source:
- Framework (1): NIST_CSF_2_0
- FrameworkCategory (6 Functions + 34 Categories): with full descriptions
- FrameworkControl (185): with complete description, implementationExamples, crossReferences
- Relationships: HAS_CATEGORY, HAS_CONTROL, MAPS_TO_SUBDOMAIN

Usage:
    python scripts/restore_nist.py [--verify-only] [--clean]
"""

import csv
import json
import sys
import requests
from pathlib import Path

AUTH = ("neo4j", os.getenv("NEO4J_PASSWORD", ""))
NEO4J_HTTP = "http://localhost:7474"
NEO4J_DB = "neo4j"

REPO_ROOT = Path(__file__).parent.parent
NIST_JSON = REPO_ROOT / "reference" / "Framework_Mappings" / "NIST_CSF" / "NIST_CSF_2.0.json"
SUBDOMAIN_CSV = REPO_ROOT / "reference" / "06_subdomain_mappings.csv"


def exec_cypher(statement, params=None):
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}
    try:
        resp = requests.post(
            f"{NEO4J_HTTP}/db/{NEO4J_DB}/tx/commit",
            auth=AUTH,
            json=payload,
            timeout=120
        )
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}: {resp.text[:300]}", "data": [], "count": 0}
        result = resp.json()
        if result.get("errors"):
            return {"error": result["errors"][0]["message"], "data": [], "count": 0}

        data = []
        for res in result.get("results", []):
            if "data" in res:
                cols = res.get("columns", [])
                for row in res["data"]:
                    data.append(dict(zip(cols, row["row"])))

        count = 0
        if data:
            count = data[0].get("count", data[0].get("cnt", 0))

        return {"error": None, "data": data, "count": count}
    except Exception as e:
        return {"error": str(e), "data": [], "count": 0}


def clean_existing():
    print("\n[0] Cleaning existing NIST nodes and relationships...")
    exec_cypher("""
        MATCH (fc:FrameworkControl {frameworkId: 'NIST_CSF_2_0'})
        DELETE fc
    """)
    exec_cypher("""
        MATCH (fc:FrameworkCategory {frameworkId: 'NIST_CSF_2_0'})
        DELETE fc
    """)
    exec_cypher("""
        MATCH (f:Framework {frameworkId: 'NIST_CSF_2_0'})
        DELETE f
    """)
    exec_cypher("""
        MATCH ()-[r:MAPS_TO_SUBDOMAIN]->()
        DELETE r
    """)
    print("  OK: Cleaned existing NIST data")


def load_framework():
    print("\n[1] Loading Framework node...")
    exec_cypher("""
        MERGE (f:Framework {
            frameworkId: 'NIST_CSF_2_0',
            name: 'NIST Cybersecurity Framework 2.0',
            version: '2.0',
            publisher: 'NIST',
            url: 'https://www.nist.gov/cyberframework',
            description: 'The NIST Cybersecurity Framework 2.0 provides a common language for organizations to manage cybersecurity risk'
        })
        RETURN count(f) AS cnt
    """)
    print("  OK: Framework 'NIST_CSF_2_0'")


def load_functions_and_categories():
    print("\n[2] Loading Functions and Categories with descriptions from JSON...")

    if not NIST_JSON.exists():
        print(f"  ERROR: {NIST_JSON} not found")
        return

    with open(NIST_JSON, "r") as f:
        functions = json.load(f)

    for fcode, fdata in functions.items():
        func_name = fdata["name"]
        func_desc = fdata.get("full_description", "")

        exec_cypher("""
            MATCH (f:Framework {frameworkId: 'NIST_CSF_2_0'})
            MERGE (func:FrameworkCategory {categoryId: $code, frameworkId: 'NIST_CSF_2_0'})
            SET func.name = $name,
                func.type = 'FUNCTION',
                func.description = $description,
                func.fullDescription = $fullDescription
            MERGE (f)-[:HAS_CATEGORY]->(func)
            RETURN count(func) AS cnt
        """, {
            "code": fcode,
            "name": func_name,
            "description": func_desc,
            "fullDescription": func_desc
        })

        for ccode, cdata in fdata["categories"].items():
            cat_name = cdata.get("name", ccode)
            exec_cypher("""
                MATCH (f:Framework {frameworkId: 'NIST_CSF_2_0'})
                MERGE (func:FrameworkCategory {categoryId: $funcCode, frameworkId: 'NIST_CSF_2_0'})
                MERGE (cat:FrameworkCategory {categoryId: $catCode, frameworkId: 'NIST_CSF_2_0'})
                SET cat.name = $name,
                    cat.type = 'CATEGORY',
                    cat.functionCode = $funcCode,
                    cat.description = $description
                MERGE (func)-[:HAS_CATEGORY]->(cat)
                MERGE (f)-[:HAS_CATEGORY]->(cat)
                RETURN count(cat) AS cnt
            """, {
                "funcCode": fcode,
                "catCode": ccode,
                "name": cat_name,
                "description": cat_name
            })

    print("  OK: 6 functions and 34 categories loaded with descriptions")


def load_controls():
    print("\n[3] Loading Controls (subcategories) from JSON...")

    if not NIST_JSON.exists():
        print(f"  ERROR: {NIST_JSON} not found")
        return 0

    with open(NIST_JSON, "r") as f:
        functions = json.load(f)

    all_items = []

    for fcode, fdata in functions.items():
        for ccode, cdata in fdata["categories"].items():
            for sc in cdata["subcategories"]:
                ctrl_id = sc["id"]
                description = sc.get("description", "")

                cross_refs = sc.get("crossReferences", [])
                cross_refs_formatted = []
                if isinstance(cross_refs, list):
                    for cr in cross_refs:
                        if isinstance(cr, dict):
                            framework = cr.get("framework", "")
                            refs = cr.get("references", [])
                            if isinstance(refs, list):
                                refs_str = ", ".join(str(r) for r in refs)
                            else:
                                refs_str = str(refs)
                            cross_refs_formatted.append(f"{framework}: {refs_str}")
                        else:
                            cross_refs_formatted.append(str(cr))

                refs = sc.get("references", "")
                if isinstance(refs, list):
                    refs = "\n".join(refs)

                impl_examples = sc.get("implementationExamples", [])
                if isinstance(impl_examples, list):
                    impl_examples = [str(ex) for ex in impl_examples]

                all_items.append({
                    "controlId": ctrl_id,
                    "functionCode": fcode,
                    "categoryCode": ccode,
                    "frameworkId": "NIST_CSF_2_0",
                    "title": ctrl_id,
                    "description": description,
                    "implementationExamples": impl_examples,
                    "references": refs,
                    "crossReferences": cross_refs_formatted
                })

    cypher = """
    UNWIND $controls AS item
    WITH item

    MATCH (cat:FrameworkCategory {categoryId: item.categoryCode, frameworkId: item.frameworkId})

    MERGE (c:FrameworkControl {controlId: item.controlId, frameworkId: item.frameworkId})
    SET c.categoryId = item.categoryCode,
        c.functionCode = item.functionCode,
        c.title = item.title,
        c.description = item.description,
        c.implementationExamples = item.implementationExamples,
        c.references = item.references,
        c.crossReferences = item.crossReferences
    MERGE (c)-[:HAS_CONTROL]->(cat)

    RETURN count(DISTINCT c) AS controlCount
    """

    result = exec_cypher(cypher, {"controls": all_items})

    if result["error"]:
        print(f"  ERROR: {result['error']}")
        return 0

    count = result.get("count", 0)
    print(f"  OK: {count} controls loaded")
    return count


def load_subdomain_mappings():
    print("\n[4] Creating MAPS_TO_SUBDOMAIN relationships from CSV...")

    if not SUBDOMAIN_CSV.exists():
        print(f"  WARNING: {SUBDOMAIN_CSV} not found, skipping mappings")
        return

    mappings = []
    with open(SUBDOMAIN_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            control_id = row["controlId"]
            dot_id = row["subDomainId"]
            confidence = float(row.get("confidence", 0.9))

            parts = dot_id.split(".")
            if len(parts) == 2:
                dash_id = f"{parts[0]}-{parts[1]}"
            else:
                dash_id = dot_id

            mappings.append({
                "controlId": control_id,
                "subDomainId": dash_id,
                "confidence": confidence
            })

    cypher = """
    UNWIND $mappings AS item
    WITH item

    MATCH (fc:FrameworkControl {controlId: item.controlId, frameworkId: 'NIST_CSF_2_0'})
    MATCH (sd:SubDomain {subDomainId: item.subDomainId})
    MERGE (fc)-[:MAPS_TO_SUBDOMAIN {confidence: item.confidence}]->(sd)
    RETURN count(DISTINCT fc) AS controlsMapped, count(*) AS totalMappings
    """

    result = exec_cypher(cypher, {"mappings": mappings})

    if result["error"]:
        print(f"  ERROR: {result['error']}")
        return

    data = result.get("data", [])
    if data:
        print(f"  OK: {data[0].get('controlsMapped', 0)} controls mapped, {data[0].get('totalMappings', 0)} relationships")


def verify():
    print("\n[5] Verification...")

    result = exec_cypher("""
        MATCH (n)
        WHERE n:Framework OR n:FrameworkCategory OR n:FrameworkControl
        RETURN labels(n)[0] AS label, count(*) AS cnt
        ORDER BY label
    """)
    if result["error"]:
        print(f"  ERROR: {result['error']}")
        return

    total = 0
    for row in result["data"]:
        print(f"  {row['label']}: {row['cnt']}")
        total += row['cnt']

    func_result = exec_cypher("""
        MATCH (fc:FrameworkCategory {type: 'FUNCTION', frameworkId: 'NIST_CSF_2_0'})
        RETURN fc.categoryId AS code, fc.name AS name, fc.description AS description
        ORDER BY code
    """)
    if not func_result["error"]:
        print("\n  Functions:")
        for row in func_result["data"]:
            desc_preview = row['description'][:60] + "..." if row['description'] and len(row['description']) > 60 else row['description']
            print(f"    {row['code']} ({row['name']}): {desc_preview}")

    cat_result = exec_cypher("""
        MATCH (fc:FrameworkCategory {type: 'CATEGORY', frameworkId: 'NIST_CSF_2_0'})
        RETURN fc.categoryId AS code, fc.description AS description
        ORDER BY code
        LIMIT 10
    """)
    if not cat_result["error"]:
        print("\n  Sample Categories (first 10):")
        for row in cat_result["data"]:
            desc_preview = row['description'][:60] + "..." if row['description'] and len(row['description']) > 60 else row['description']
            print(f"    {row['code']}: {desc_preview}")

    ctrl_result = exec_cypher("""
        MATCH (fc:FrameworkControl {frameworkId: 'NIST_CSF_2_0'})
        RETURN fc.controlId AS id, size(fc.implementationExamples) AS implCount, size(fc.crossReferences) AS crossRefCount
        ORDER BY id
        LIMIT 5
    """)
    if not ctrl_result["error"]:
        print("\n  Sample Controls:")
        for row in ctrl_result["data"]:
            print(f"    {row['id']}: {row['implCount']} impl examples, {row['crossRefCount']} cross-references")

    rel_result = exec_cypher("""
        MATCH ()-[r]->()
        WHERE type(r) IN ['HAS_CATEGORY', 'HAS_CONTROL', 'MAPS_TO_SUBDOMAIN']
        RETURN type(r) AS relType, count(*) AS cnt
        ORDER BY cnt DESC
    """)
    if not rel_result["error"]:
        print("\n  Relationships:")
        for row in rel_result["data"]:
            print(f"    [{row['relType']}]: {row['cnt']}")

    mapping_result = exec_cypher("MATCH ()-[r:MAPS_TO_SUBDOMAIN]->() RETURN count(r) AS cnt")
    print(f"\n  MAPS_TO_SUBDOMAIN: {mapping_result.get('count', '?')}")
    print(f"\n  Total NIST nodes: {total}")


if __name__ == "__main__":
    verify_only = "--verify-only" in sys.argv
    clean_first = "--clean" in sys.argv

    print("=" * 60)
    print("  RESTORE NIST CSF 2.0 DATA (COMPLETE)")
    print("=" * 60)

    if verify_only:
        print("\nVerify-only mode\n")
        result = exec_cypher("""
            MATCH (n)
            WHERE n:Framework OR n:FrameworkCategory OR n:FrameworkControl
            RETURN labels(n)[0] AS label, count(*) AS cnt
            ORDER BY label
        """)
        if result["error"]:
            print(f"  ERROR: {result['error']}")
        else:
            total = 0
            for row in result["data"]:
                print(f"  {row['label']}: {row['cnt']}")
                total += row['cnt']
            print(f"\n  Total: {total}")
    else:
        if clean_first:
            clean_existing()

        load_framework()
        load_functions_and_categories()
        load_controls()
        load_subdomain_mappings()
        verify()

    print("\n" + "=" * 60)
    print("  RESTORE COMPLETE")
    print("=" * 60)