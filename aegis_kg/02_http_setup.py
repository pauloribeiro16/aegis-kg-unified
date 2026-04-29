import os
#!/usr/bin/env python3
"""
Phase 1 KG Setup - HTTP API approach
Creates Neo4j schema using HTTP transactions instead of Bolt protocol
"""
import requests
import json

def main():
    # Configuration
    NEO4J_HTTP = "http://localhost:7474"
    AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", ""))

    print("=" * 50)
    print("AEGIS Phase 1 KG - HTTP API Setup")
    print("=" * 50)
    print()

    # Test connection
    print("Testing Neo4j connection...")
    try:
        response = requests.get(f"{NEO4J_HTTP}", auth=AUTH, timeout=5)
        if response.status_code == 200:
            print(f"OK: Neo4j accessible at {NEO4J_HTTP}")
        else:
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
        return 1

    # Create constraints
    print("\nCreating constraints...")
    constraints = [
        {
            "name": "constraint_regulation_id_unique",
            "type": "UNIQUE",
            "entity": "Regulation",
            "properties": ["regulationId"],
            "drop": True
        },
        {
            "name": "constraint_regulation_id_unique",
            "type": "EXIST",
            "entity": "Regulation",
            "properties": ["regulationId"],
            "drop": False
        }
    ]

    response = requests.post(
        f"{NEO4J_HTTP}/db/data/schema/constraints",
        auth=AUTH,
        json=constraints
    )

    if response.status_code == 200:
        print(f"Status: {response.status_code}")
        print(f"Created {len(constraints)} constraints")
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return 1

    print("\n✓ Constraints created")

    # Create indexes
    print("\nCreating indexes...")
    indexes = [
        {
            "name": "index_regulation_name",
            "entity": "Regulation",
            "properties": ["name"],
            "state": "POPULATED"
        }
    ]

    response = requests.post(
        f"{NEO4J_HTTP}/db/data/schema/indexes",
        auth=AUTH,
        json=indexes
    )

    if response.status_code == 200:
        print(f"Status: {response.status_code}")
        print(f"Created {len(indexes)} indexes")
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return 1

    print("\n✓ Indexes created")

    print()
    print("=" * 50)
    print("Setup Complete!")
    print("=" * 50)
    print(f"\nNeo4j Browser: {NEO4J_HTTP}")
    print(f"Authentication: neo4j / <no password>")
    print(f"\nNext: Load data with ETL scripts (coming soon)")

if __name__ == "__main__":
    main()
