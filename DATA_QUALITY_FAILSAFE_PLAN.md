# DATA QUALITY + FAIL-SAFES — Implementation Plan

**Version:** 1.0
**Date:** 2026-05-04
**Status:** READY FOR EXECUTION
**Estimated Time:** 8-12 hours
**Branch:** feature/data-quality-failsafes (create from master)

---

## INSTRUCOES PARA O AGENTE EXECUTOR

### Regras de Ouro

1. **Lê este ficheiro COMPLETO antes de comecar.**
2. **Executa batch a batch, pela ordem numerada (Batch 1, depois 2, etc.).**
3. **No final de cada batch, corre TODOS os CHECKPOINTS desse batch.**
4. **Se TODOS os checkpoints passarem:**
   - Faz commit com a mensagem indicada no fim do batch.
   - Diz ao utilizador: **"BATCH X COMPLETO. Pronto para Batch X+1. Confirmas?"**
   - **NAO avances sem confirmacao explicita do utilizador.**
5. **Se ALGUM checkpoint FALHAR:**
   - PARA imediatamente.
   - NAO tentes corrigir sozinho.
   - Reporta ao utilizador: **"BATCH X FALHOU no checkpoint [nome]. Erro: [mensagem exata]. Como quer que proceda?"**
6. **Nunca facas push para remote sem pedido explicito.**
7. **Nunca facas merge para master sem pedido explicito.**

---

## STEP 0: CRIAR FEATURE BRANCH

```bash
./scripts/create-feature.sh "data-quality-failsafes"
git checkout feature/data-quality-failsafes
```

### CHECKPOINT 0:
```bash
git branch --show-current
# EXPECTED: feature/data-quality-failsafes
# SE FALHAR: Nao criar branch manualmente. Reportar ao utilizador.
```

---

## BATCH 1: SCHEMA CONSISTENCY FIXES (~30 min)

**Problema:** O agente recebe schema errado — IDs com dash (`D-01-1`) em vez de dot (`D-01.1`),
e relacao `HAS_SUBDOMAIN` em vez de `CONTAINS`. O grafo Neo4j usa DOT e CONTAINS.

### T1.1 — Corrigir schema_tool.py

**Ficheiro:** `aegis_agents/tools/schema_tool.py`

**Referencia canónica ( fonte de verdade ):** `aegis_eval/schema_context.py`

**O que fazer:**
1. Abre `aegis_eval/schema_context.py` e usa-o como referencia para TODAS as correcoes abaixo.
2. Abre `aegis_agents/tools/schema_tool.py`.
3. Na string `SCHEMA_DESCRIPTION` (linha ~6 ate ~100):
   - Substitui TODAS as ocorrencias de `D-01-1`, `D-XX-Y`, `D-10-3` por `D-01.1`, `D-XX.Y`, `D-10.3` (DOT separator)
   - Substitui a linha `- Format: D-XX-Y (domain number - subdomain number)` por `- Format: D-XX.Y (DOT separator, e.g., D-01.1, D-02.3, D-10.2)`
   - Substitui `(Domain)-[:HAS_SUBDOMAIN]->(SubDomain)` por `(Domain)-[:CONTAINS]->(SubDomain)` em TODAS as ocorrencias
   - Na seccao "USEFUL QUERIES", o query de Regulatory coverage (linha ~97) usa `HAS_SUBDOMAIN` — mudar para `CONTAINS`
4. Na funcao `schema_explorer()` — ramo `operation == "nodes"` (linha ~130):
   - A lista de SubDomain diz `D-01-1 through D-10-3` → mudar para `D-01.1 through D-10.3`
5. Ramo `operation == "regulatory"` (linha ~186):
   - SubDomain diz `D-01-1 through D-10-3` → `D-01.1 through D-10.3`
   - `(Domain)-[:HAS_SUBDOMAIN]->(SubDomain)` → `(Domain)-[:CONTAINS]->(SubDomain)`
6. Ramo `operation == "identities"` (linha ~203):
   - `SubDomain: "D-01-1" (D-XX-Y format, dash separator)` → `SubDomain: "D-01.1" (D-XX.Y format, DOT separator)`

### T1.2 — Corrigir prompts.py

**Ficheiro:** `aegis_agents/graph/prompts.py`

**O que fazer:**
- Linha ~30, dentro do prompt "cypher_generation":
  - Substitui `5. For the SubDomain ID format use 'D-01-1' (D-XX-Y with leading zeros dropped).`
  - Por: `5. For the SubDomain ID format use 'D-01.1' (DOT separator, D-XX.Y format).`

### T1.3 — Corrigir neo4j_tool.py

**Ficheiro:** `aegis_agents/tools/neo4j_tool.py`

**O que fazer:**
- Linha ~121, dentro da string `system_prompt`:
  - Substitui `5. For the SubDomain ID format use 'D-01-1' (D-XX-Y with leading zeros dropped).`
  - Por: `5. For the SubDomain ID format use 'D-01.1' (DOT separator, D-XX.Y format).`

### CHECKPOINTS BATCH 1:

```bash
# CHECKPOINT T1.1a: Nenhum formato D-XX-Y (dash) no schema_tool
rg "D-\d{2}-\d" aegis_agents/tools/schema_tool.py
# EXPECTED: 0 matches (exit code 1 do rg = sem matches = PASSA)

# CHECKPOINT T1.1b: Formato DOT presente no schema_tool
rg "D-\d{2}\.\d" aegis_agents/tools/schema_tool.py | wc -l
# EXPECTED: >= 3

# CHECKPOINT T1.1c: HAS_SUBDOMAIN removido do schema_tool
rg "HAS_SUBDOMAIN" aegis_agents/tools/schema_tool.py
# EXPECTED: 0 matches

# CHECKPOINT T1.1d: CONTAINS presente no schema_tool
rg "CONTAINS" aegis_agents/tools/schema_tool.py
# EXPECTED: pelo menos 1 match

# CHECKPOINT T1.2: Nenhum D-01-1 no prompts.py
rg "D-01-1" aegis_agents/graph/prompts.py
# EXPECTED: 0 matches

# CHECKPOINT T1.2b: D-01.1 presente no prompts.py
rg "D-01\.1" aegis_agents/graph/prompts.py
# EXPECTED: pelo menos 1 match

# CHECKPOINT T1.3: Nenhum D-01-1 no neo4j_tool.py
rg "D-01-1" aegis_agents/tools/neo4j_tool.py
# EXPECTED: 0 matches

# CHECKPOINT T1.3b: D-01.1 presente no neo4j_tool.py
rg "D-01\.1" aegis_agents/tools/neo4j_tool.py
# EXPECTED: pelo menos 1 match

# CHECKPOINT BATCH 1 CONSOLIDADO:
echo "=== Dash format (deve ser 0) ==="
rg -c "D-01-1" aegis_agents/tools/schema_tool.py aegis_agents/graph/prompts.py aegis_agents/tools/neo4j_tool.py 2>/dev/null || echo "0 matches — OK"
echo "=== HAS_SUBDOMAIN (deve ser 0) ==="
rg -c "HAS_SUBDOMAIN" aegis_agents/tools/schema_tool.py aegis_agents/graph/prompts.py 2>/dev/null || echo "0 matches — OK"
echo "=== DOT format (deve ser >= 3) ==="
rg -l "D-01\.1" aegis_agents/tools/schema_tool.py aegis_agents/graph/prompts.py aegis_agents/tools/neo4j_tool.py | wc -l
```

**Se TUDO passou:**
```bash
git add aegis_agents/tools/schema_tool.py aegis_agents/graph/prompts.py aegis_agents/tools/neo4j_tool.py
git commit -m "fix: sync agent schema to DOT format (D-01.1) and CONTAINS relationship"
```

**Output esperado ao utilizador:** "BATCH 1 COMPLETO. Pronto para Batch 2. Confirmas?"

---

## BATCH 2: API RELATIONSHIP FIX (~15 min)

**Problema:** A API usa `COVERS_SUBDOMAIN` mas o grafo tem `MAPPED_TO`.
Tambem ha um import duplicado e um filtro em propriedade NULL.

### T1.5 — Corrigir API app.py

**Ficheiro:** `aegis_kg/api/app.py`

**O que fazer:**

1. **Remove o `import os` duplicado.** A linha 1 tem `import os` e a linha 9 tambem.
   Apaga a linha 1 (`import os`). Mantem so o da linha 9.

2. **Substitui TODAS as ocorrencias de `COVERS_SUBDOMAIN` por `MAPPED_TO`** nos queries Cypher.
   Procura por cada ocorrencia de `COVERS_SUBDOMAIN` no ficheiro inteiro e substitui por `MAPPED_TO`.
   Nao substituas em comentarios de texto livre — so nos queries Cypher dentro das strings.

3. **Corrige o endpoint `/api/applicability`:**
   O query filtra por `{applicable: true}` mas essa propriedade e NULL em todas as clauses.
   
   ANTES (aproximadamente linha 256):
   ```cypher
   MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause {applicable: true})
   WITH r.regulationId AS regId, r.name AS name,
        count(c) AS applicableClauses, collect(c.clauseId) AS clauses
   RETURN regId, name, applicableClauses, clauses
   ORDER BY applicableClauses DESC
   ```
   
   DEPOIS:
   ```cypher
   MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)
   WITH r.regulationId AS regId, r.name AS name,
        count(c) AS applicableClauses, collect(c.clauseId) AS clauses
   RETURN regId, name, applicableClauses, clauses
   ORDER BY applicableClauses DESC
   ```

### CHECKPOINTS BATCH 2:

```bash
# CHECKPOINT T1.5a: Nenhum COVERS_SUBDOMAIN na API
rg "COVERS_SUBDOMAIN" aegis_kg/api/app.py
# EXPECTED: 0 matches

# CHECKPOINT T1.5b: MAPPED_TO presente na API
rg "MAPPED_TO" aegis_kg/api/app.py | wc -l
# EXPECTED: >= 5

# CHECKPOINT T1.5c: Import os nao duplicado
head -15 aegis_kg/api/app.py | grep -n "import os"
# EXPECTED: exatamente 1 linha com "import os"

# CHECKPOINT T1.5d: Filtro applicable removido
rg "applicable: true" aegis_kg/api/app.py
# EXPECTED: 0 matches
```

**Se TUDO passou:**
```bash
git add aegis_kg/api/app.py
git commit -m "fix: API uses MAPPED_TO instead of COVERS_SUBDOMAIN, remove applicable filter"
```

**Output esperado ao utilizador:** "BATCH 2 COMPLETO. Pronto para Batch 3. Confirmas?"

---

## BATCH 3: DATA CLEANUP (~1-2h)

**Problema:** Propriedades NULL no Neo4j limitam queries. 14 nodos fantasma SubDomainMetrics.

### T1.4 — Criar e executar fix_null_properties.py

**Novo ficheiro:** `scripts/fix_null_properties.py`

**O que o script faz:**
1. Carrega `aegis_kg/data/00_regulations.csv` e popula `Regulation.name`, `Regulation.fullName`, `Regulation.effectiveDate`, `Regulation.lastAmended`
2. Deriva `Article.regulationId` do prefixo de `articleId` (ex: "GDPR-Art5" -> "GDPR")
3. Faz SET `Clause.applicable = true` em todas as 150 clauses
4. Faz DELETE dos 14 nodos `SubDomainMetrics` (todos com propriedades NULL)
5. Verifica contagens apos cada operacao

**Implementacao:**

```python
#!/usr/bin/env python3
"""Fix NULL properties in the AEGIS Knowledge Graph.

Populates missing Regulation, Article, Clause properties.
Deletes phantom SubDomainMetrics nodes.

Usage:
    python scripts/fix_null_properties.py
"""

import csv
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

NEO4J_HTTP = os.getenv("NEO4J_URI", "http://localhost:7474")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
AUTH = (NEO4J_USER, NEO4J_PASSWORD)
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "aegis_kg", "data")


def exec_cypher(statement, params=None):
    url = f"{NEO4J_HTTP}/db/neo4j/tx/commit"
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}
    resp = requests.post(url, auth=AUTH, json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"  ERROR: HTTP {resp.status_code}: {resp.text[:200]}")
        return None
    result = resp.json()
    if result.get("errors"):
        print(f"  ERROR: {result['errors'][0]['message']}")
        return None
    return result.get("results", [])


def query_one(statement):
    r = exec_cypher(statement)
    if r and r[0].get("data"):
        return r[0]["data"][0]["row"]
    return None


def main():
    print("=" * 60)
    print("  AEGIS KG — Fix NULL Properties")
    print("=" * 60)

    # PRE-CHECK: Neo4j connectivity
    try:
        r = requests.get(NEO4J_HTTP, auth=AUTH, timeout=5)
        assert r.status_code == 200, f"Neo4j returned {r.status_code}"
        print("  OK: Neo4j connected")
    except Exception as e:
        print(f"  FATAL: Cannot connect to Neo4j: {e}")
        sys.exit(1)

    # STEP 1: Populate Regulation properties from CSV
    print("\n--- STEP 1: Populate Regulation properties ---")
    csv_path = os.path.join(DATA_DIR, "00_regulations.csv")
    if not os.path.exists(csv_path):
        print(f"  FATAL: CSV not found: {csv_path}")
        sys.exit(1)

    with open(csv_path, newline="", encoding="utf-8") as f:
        regulations = list(csv.DictReader(f))

    print(f"  Loaded {len(regulations)} regulations from CSV")

    for reg in regulations:
        reg_id = reg["regulationId"]
        cypher = """
        MATCH (r:Regulation {regulationId: $regId})
        SET r.name = $name,
            r.fullName = $fullName,
            r.effectiveDate = $effectiveDate,
            r.lastAmended = $lastAmended
        RETURN r.regulationId
        """
        result = exec_cypher(cypher, {
            "regId": reg_id,
            "name": reg.get("name", ""),
            "fullName": reg.get("fullName", ""),
            "effectiveDate": reg.get("effectiveDate", ""),
            "lastAmended": reg.get("lastAmended", ""),
        })
        if result:
            print(f"  Updated {reg_id}: name='{reg.get('name', '')}'")
        else:
            print(f"  WARNING: Failed to update {reg_id}")

    null_names = query_one("MATCH (r:Regulation) WHERE r.name IS NULL RETURN count(r)")
    print(f"  Regulations with NULL name: {null_names[0] if null_names else 'QUERY FAILED'}")

    # STEP 2: Populate Article.regulationId from articleId prefix
    print("\n--- STEP 2: Populate Article.regulationId ---")
    cypher = """
    MATCH (a:Article)
    WHERE a.regulationId IS NULL AND a.articleId IS NOT NULL
    WITH a, split(a.articleId, '-') AS parts
    SET a.regulationId = parts[0]
    RETURN count(a) AS updated
    """
    result = query_one(cypher)
    print(f"  Updated {result[0] if result else '?'} articles with regulationId")

    null_reg = query_one("MATCH (a:Article) WHERE a.regulationId IS NULL RETURN count(a)")
    print(f"  Articles still with NULL regulationId: {null_reg[0] if null_reg else '?'}")

    # STEP 3: Set Clause.applicable = true
    print("\n--- STEP 3: Set Clause.applicable = true ---")
    cypher = """
    MATCH (c:Clause)
    WHERE c.applicable IS NULL
    SET c.applicable = true
    RETURN count(c) AS updated
    """
    result = query_one(cypher)
    print(f"  Updated {result[0] if result else '?'} clauses with applicable=true")

    null_app = query_one("MATCH (c:Clause) WHERE c.applicable IS NULL RETURN count(c)")
    print(f"  Clauses still with NULL applicable: {null_app[0] if null_app else '?'}")

    # STEP 4: Delete phantom SubDomainMetrics nodes
    print("\n--- STEP 4: Delete phantom SubDomainMetrics ---")
    count_before = query_one("MATCH (m:SubDomainMetrics) RETURN count(m)")
    print(f"  SubDomainMetrics before: {count_before[0] if count_before else '?'}")

    cypher = """
    MATCH (m:SubDomainMetrics)
    DETACH DELETE m
    RETURN count(*) AS deleted
    """
    result = query_one(cypher)
    print(f"  Deleted {result[0] if result else '?'} SubDomainMetrics nodes")

    count_after = query_one("MATCH (m:SubDomainMetrics) RETURN count(m)")
    print(f"  SubDomainMetrics after: {count_after[0] if count_after else '?'}")

    # FINAL VERIFICATION
    print("\n" + "=" * 60)
    print("  VERIFICATION")
    print("=" * 60)

    checks = [
        ("Regulation.name NULL", "MATCH (r:Regulation) WHERE r.name IS NULL RETURN count(r)", 0),
        ("Regulation count", "MATCH (r:Regulation) RETURN count(r)", 5),
        ("Article.regulationId NULL", "MATCH (a:Article) WHERE a.regulationId IS NULL RETURN count(a)", 0),
        ("Article count", "MATCH (a:Article) RETURN count(a)", 47),
        ("Clause.applicable NULL", "MATCH (c:Clause) WHERE c.applicable IS NULL RETURN count(c)", 0),
        ("Clause count", "MATCH (c:Clause) RETURN count(c)", 150),
        ("SubDomainMetrics count", "MATCH (m:SubDomainMetrics) RETURN count(m)", 0),
        ("SubDomain count", "MATCH (sd:SubDomain) RETURN count(sd)", 38),
        ("Domain count", "MATCH (d:Domain) RETURN count(d)", 10),
    ]

    all_pass = True
    for name, query, expected in checks:
        result = query_one(query)
        actual = result[0] if result else "QUERY FAILED"
        status = "PASS" if actual == expected else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  [{status}] {name}: {actual} (expected {expected})")

    print()
    if all_pass:
        print("  ALL CHECKS PASSED")
    else:
        print("  SOME CHECKS FAILED — verify manually")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
```

### CHECKPOINTS BATCH 3:

```bash
# CHECKPOINT T1.4a: Script existe e e executavel
ls -la scripts/fix_null_properties.py
# EXPECTED: ficheiro existe, > 0 bytes

# CHECKPOINT T1.4b: Script executa sem erros
python3 scripts/fix_null_properties.py
# EXPECTED: "ALL CHECKS PASSED" no final, exit code 0

# CHECKPOINT T1.4c: Verificacao manual pos-execucao
python3 -c "
import requests, os
AUTH = (os.getenv('NEO4J_USER','neo4j'), os.getenv('NEO4J_PASSWORD',''))
url = f'{os.getenv(\"NEO4J_URI\",\"http://localhost:7474\")}/db/neo4j/tx/commit'

def q(c):
    r = requests.post(url, auth=AUTH, json={'statements':[{'statement':c}]}, timeout=10)
    return r.json()['results'][0]['data'][0]['row'] if r.json().get('results') else [-1]

checks = [
    ('Regulation.name NULL', 'MATCH (r:Regulation) WHERE r.name IS NULL RETURN count(r)', 0),
    ('Regulation names', 'MATCH (r:Regulation) RETURN r.regulationId, r.name ORDER BY r.regulationId', 'list'),
    ('Article.regulationId NULL', 'MATCH (a:Article) WHERE a.regulationId IS NULL RETURN count(a)', 0),
    ('Clause.applicable NULL', 'MATCH (c:Clause) WHERE c.applicable IS NULL RETURN count(c)', 0),
    ('SubDomainMetrics', 'MATCH (m:SubDomainMetrics) RETURN count(m)', 0),
]

for name, query, expected in checks:
    result = q(query)
    if expected == 'list':
        for row in result:
            print(f'  {row[0]}: {row[1]}')
    else:
        actual = result[0]
        status = 'PASS' if actual == expected else 'FAIL'
        print(f'[{status}] {name}: {actual} (expected {expected})')
"

# CHECKPOINT T1.4d: Validacao de Phase 1 (suite completa)
cd aegis_kg && python validation/01_validate_phase1.py
# EXPECTED: All tests pass
# SE FALHAR: verificar se algum teste de contagem mudou
```

**Se TUDO passou:**
```bash
git add scripts/fix_null_properties.py
git commit -m "feat: add script to fix NULL properties and remove phantom SubDomainMetrics"
```

**Output esperado ao utilizador:** "BATCH 3 COMPLETO. Pronto para Batch 4. Confirmas?"

---

## BATCH 4: FAIL-SAFES (~2-3h)

**Objetivo:** Adicionar circuit breaker, query linter, fallback queries, retry com backoff,
graceful degradation e validacao de resultados.

### T2.1 — Circuit Breaker para Neo4j

**Novo ficheiro:** `aegis_agents/circuit_breaker.py`

```python
"""Circuit breaker for Neo4j connections.

States: CLOSED (normal) -> OPEN (failing) -> HALF_OPEN (testing)

Usage:
    from aegis_agents.circuit_breaker import Neo4JCircuitBreaker
    cb = Neo4JCircuitBreaker()
    result = cb.call(exec_cypher, query, params)
"""

import time
import threading
from typing import Any, Callable


class CircuitOpenError(Exception):
    """Raised when the circuit breaker is OPEN."""
    pass


class CircuitBreaker:
    """Thread-safe circuit breaker.

    Args:
        failure_threshold: Consecutive failures before opening.
        recovery_timeout: Seconds before attempting HALF_OPEN.
        success_threshold: Successes in HALF_OPEN before closing.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = "CLOSED"
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == "OPEN":
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = "HALF_OPEN"
            return self._state

    @property
    def is_open(self) -> bool:
        return self.state == "OPEN"

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute func through the circuit breaker.

        Raises:
            CircuitOpenError: If the circuit is OPEN.
        """
        current_state = self.state

        if current_state == "OPEN":
            raise CircuitOpenError(
                f"Circuit breaker OPEN — Neo4j unavailable "
                f"(failures={self._failure_count}, "
                f"last_failure={self._last_failure_time:.0f})"
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        with self._lock:
            if self._state == "HALF_OPEN":
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = "CLOSED"
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == "CLOSED":
                self._failure_count = 0

    def _on_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._state == "HALF_OPEN":
                self._state = "OPEN"
            elif self._failure_count >= self.failure_threshold:
                self._state = "OPEN"

    def reset(self):
        with self._lock:
            self._state = "CLOSED"
            self._failure_count = 0
            self._success_count = 0


neo4j_cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0, success_threshold=2)
```

### T2.2 — Query Linter (Read-Only + Validacao)

**Novo ficheiro:** `aegis_agents/query_linter.py`

```python
"""Pre-execution validation for Cypher queries.

Rejects write operations and malformed queries before they reach Neo4j.
"""

import re

WRITE_KEYWORDS = ["CREATE", "MERGE", "DELETE", "DETACH", "DROP", "REMOVE", "SET "]
MAX_QUERY_LENGTH = 2000


def validate_cypher(statement: str, timeout_seconds: int = 10) -> tuple[bool, str]:
    """Validate a Cypher query before execution.

    Checks:
        1. No write operations (CREATE, MERGE, DELETE, DROP, REMOVE, SET)
        2. Has RETURN clause
        3. Length < MAX_QUERY_LENGTH
        4. Contains MATCH or explicit read pattern

    Returns:
        (is_valid, reason) — reason is empty string if valid.
    """
    if not statement or not statement.strip():
        return False, "Empty query"

    upper = statement.upper().strip()

    if len(statement) > MAX_QUERY_LENGTH:
        return False, f"Query too long ({len(statement)} chars, max {MAX_QUERY_LENGTH})"

    for keyword in WRITE_KEYWORDS:
        pattern = r'\b' + keyword.rstrip() + r'\b'
        if re.search(pattern, upper):
            return False, f"Write operation detected: {keyword.rstrip()}"

    if "RETURN" not in upper:
        return False, "Query has no RETURN clause"

    return True, ""
```

### T2.3 — Fallback Cypher Templates

**Novo ficheiro:** `aegis_agents/fallback_queries.py`

```python
"""Fallback Cypher query templates for graceful degradation.

When the LLM fails to generate valid Cypher after multiple attempts,
these templates provide pre-built queries for common question patterns.
"""

import re


FALLBACK_QUERIES = [
    {
        "pattern": r"(?i)(how many|count).*(clause|clauses).*(gdpr|craz|nis2|dora|ai\s*act)",
        "template": "MATCH (c:Clause {{regulationId: '{reg}'}}) RETURN count(c) AS total",
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
```

### T2.4 — Integrar fail-safes no nodes.py

**Ficheiro a editar:** `aegis_agents/graph/nodes.py`

**O que fazer:**

1. Adicionar imports no topo do ficheiro (apos os imports existentes):
```python
import time as _time
from aegis_agents.circuit_breaker import neo4j_cb, CircuitOpenError
from aegis_agents.query_linter import validate_cypher
from aegis_agents.fallback_queries import find_fallback
```

2. Modificar a funcao `exec_cypher` (linha ~48) para incluir linter e circuit breaker:

```python
def exec_cypher(statement: str, params: dict = None) -> dict:
    """Execute Cypher against Neo4j with circuit breaker and linter."""
    is_valid, reason = validate_cypher(statement)
    if not is_valid:
        return {"error": f"Query rejected: {reason}", "data": [], "row_count": 0}

    if neo4j_cb.is_open:
        return {"error": "Circuit breaker OPEN — Neo4j unavailable", "data": [], "row_count": 0}

    import requests as req
    from aegis_agents.config import NEO4J_CONFIG

    url = f"{NEO4J_CONFIG['http_url']}/db/{NEO4J_CONFIG['database']}/tx/commit"
    auth = (NEO4J_CONFIG["user"], NEO4J_CONFIG["password"])
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}

    try:
        resp = req.post(url, auth=auth, json=payload, timeout=10)
        if resp.status_code != 200:
            neo4j_cb._on_failure()
            return {"error": f"HTTP {resp.status_code}", "data": [], "row_count": 0}
        result = resp.json()
        if result.get("errors"):
            return {"error": result["errors"][0]["message"], "data": [], "row_count": 0}
        rows = []
        for res in result.get("results", []):
            if "data" in res:
                cols = res.get("columns", [])
                for row in res["data"]:
                    rows.append(dict(zip(cols, row["row"])))
        neo4j_cb._on_success()
        return {"error": None, "data": rows, "row_count": len(rows)}
    except Exception as e:
        neo4j_cb._on_failure()
        return {"error": str(e), "data": [], "row_count": 0}
```

3. Adicionar logica de fallback + retry com backoff em `generate_and_execute`:

No inicio da funcao `generate_and_execute`, apos a definicao de `previous_error` (linha ~88),
adicionar uma variavel para tracking de fallback:

```python
fallback_used = False
```

Antes do bloco `try:` da chamada Ollama (linha ~110), adicionar logica de fallback
quando tentativa >= max_attempts:

```python
    if attempt >= state.get("max_attempts", 3):
        fallback_cypher = find_fallback(question)
        if fallback_cypher:
            result = exec_cypher(fallback_cypher)
            if result.get("row_count", 0) > 0:
                step = {
                    "attempt": attempt,
                    "cypher": fallback_cypher,
                    "error": None,
                    "data": result.get("data", []),
                    "row_count": result.get("row_count", 0),
                    "latency_ms": 0,
                    "fallback": True,
                }
                log_generation(
                    name="fallback_query",
                    input_data={"question": question, "fallback": True},
                    output_data={"cypher": fallback_cypher, "row_count": result.get("row_count", 0)},
                    model="fallback-template",
                    latency_ms=0,
                    metadata={"attempt": attempt, "task": "fallback"}
                )
                return {
                    "steps": state.get("steps", []) + [step],
                    "attempt": attempt + 1,
                    "cypher": fallback_cypher,
                    "fallback_used": True,
                }
```

### T2.5 — Graceful Degradation no agent.py

**Ficheiro a editar:** `aegis_agents/agent.py`

**O que fazer:**

Adicionar dois metodos helper na classe `AegisAgent`, antes do metodo `run`:

```python
    def _check_neo4j(self) -> bool:
        """Check if Neo4j is reachable."""
        try:
            from aegis_agents.config import NEO4J_CONFIG
            import requests as req
            r = req.get(NEO4J_CONFIG["http_url"], auth=(NEO4J_CONFIG["user"], NEO4J_CONFIG["password"]), timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def _check_ollama(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            from aegis_agents.config import OLLAMA_CONFIG
            import requests as req
            r = req.get(f"{OLLAMA_CONFIG['base_url']}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False
```

Modificar o inicio do metodo `run` para incluir pre-flight checks:

No metodo `run`, logo apos a linha `initial_state = ...` e antes de `config = {}`,
adicionar:

```python
        neo4j_ok = self._check_neo4j()
        ollama_ok = self._check_ollama()

        if not neo4j_ok and not ollama_ok:
            return {
                "answer": "Both Neo4j and Ollama are unavailable. Please check infrastructure (docker ps, curl localhost:7474, curl localhost:11434).",
                "cypher": None,
                "steps": [],
                "success": False,
                "attempt_count": 0,
                "trace_id": None,
                "degraded_mode": True,
            }

        if not ollama_ok:
            from aegis_agents.fallback_queries import find_fallback
            from aegis_agents.graph.nodes import exec_cypher
            fallback_cypher = find_fallback(question)
            if fallback_cypher:
                result = exec_cypher(fallback_cypher)
                if result.get("error") is None:
                    data = result.get("data", [])
                    answer = "\n".join(
                        [", ".join(f"{k}={v}" for k, v in row.items() if v is not None) for row in data[:20]]
                    )
                    return {
                        "answer": f"[Fallback mode — Ollama unavailable]\n{answer}",
                        "cypher": fallback_cypher,
                        "steps": [{"attempt": 1, "cypher": fallback_cypher, "error": None, "data": data, "row_count": len(data), "fallback": True}],
                        "success": True,
                        "attempt_count": 1,
                        "trace_id": None,
                        "fallback_used": True,
                        "degraded_mode": True,
                    }
            return {
                "answer": "Ollama is unavailable and no fallback query matches this question. Please start Ollama.",
                "cypher": None,
                "steps": [],
                "success": False,
                "attempt_count": 0,
                "trace_id": None,
                "degraded_mode": True,
            }
```

### T2.6 — Result Validator

**Novo ficheiro:** `aegis_agents/result_validator.py`

```python
"""Post-execution validation for Cypher query results.

Detects suspicious results: excessive rows, NULL-heavy columns, etc.
"""

MAX_ROWS = 500
WARN_ROWS = 200
MAX_NULL_RATIO = 0.8


def validate_result(result: dict, question: str) -> tuple[dict, list[str]]:
    """Validate query results and return warnings.

    Args:
        result: Dict with 'data', 'row_count', 'error' keys.
        question: Original question for context.

    Returns:
        (result, warnings) — result is unchanged, warnings is a list of strings.
    """
    warnings = []

    if result.get("error") is not None:
        return result, warnings

    data = result.get("data", [])
    row_count = result.get("row_count", 0)

    if row_count > MAX_ROWS:
        warnings.append(f"Excessive rows: {row_count} (max {MAX_ROWS}). Query may be too broad.")

    elif row_count > WARN_ROWS:
        warnings.append(f"High row count: {row_count}. Consider narrowing the query.")

    if data:
        keys = list(data[0].keys())
        for key in keys:
            null_count = sum(1 for row in data if row.get(key) is None)
            if null_count > 0 and len(data) > 0:
                ratio = null_count / len(data)
                if ratio >= MAX_NULL_RATIO:
                    warnings.append(f"Column '{key}' is {ratio:.0%} NULL ({null_count}/{len(data)} rows)")

    return result, warnings
```

### T2.7 — Extended Agent State

**Ficheiro a editar:** `aegis_agents/graph/state.py`

Substituir o conteudo inteiro por:

```python
"""Agent state definition for LangGraph."""

from typing import TypedDict, Annotated
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """State for the Aegis agent with feedback loop and failsafe tracking."""

    messages: Annotated[list, add_messages]
    question: str
    attempt: int
    max_attempts: int
    cypher: str | None
    query_result: dict | None
    answer: str | None
    success: bool
    steps: list[dict]
    circuit_breaker_state: str
    last_error_type: str | None
    fallback_used: bool
    total_latency_ms: float
    degraded_mode: bool
```

### CHECKPOINTS BATCH 4:

```bash
# CHECKPOINT T2.1: Circuit breaker
python3 -c "
from aegis_agents.circuit_breaker import CircuitBreaker, CircuitOpenError, neo4j_cb

cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5)
assert cb.state == 'CLOSED', f'Initial should be CLOSED, got {cb.state}'

for i in range(3):
    try:
        cb.call(lambda: (_ for _ in ()).throw(ConnectionError('test')))
    except ConnectionError:
        pass

assert cb.state == 'OPEN', f'Should be OPEN after 3 failures, got {cb.state}'
assert cb.is_open, 'is_open should be True'

try:
    cb.call(lambda: 'should fail')
    assert False, 'Should have raised CircuitOpenError'
except CircuitOpenError:
    pass

assert isinstance(neo4j_cb, CircuitBreaker), 'Global neo4j_cb should be CircuitBreaker'
print('OK: Circuit breaker states correct')
print(f'State: {cb.state}, is_open: {cb.is_open}')
"

# CHECKPOINT T2.2: Query linter
python3 -c "
from aegis_agents.query_linter import validate_cypher

tests_pass = [
    ('MATCH (r:Regulation) RETURN r.regulationId', True),
    ('MATCH (c:Clause) WHERE c.regulationId = \"GDPR\" RETURN count(c) AS total', True),
    ('MATCH (sd:SubDomain) WHERE NOT EXISTS((:Clause)-[:MAPPED_TO]->(sd)) RETURN sd.name', True),
]
tests_fail = [
    ('CREATE (n:Test) RETURN n', 'write'),
    ('MERGE (n:Test) RETURN n', 'write'),
    ('MATCH (n:Test) DELETE n', 'write'),
    ('MATCH (n:Test) REMOVE n.prop', 'write'),
    ('MATCH (r:Regulation)', 'RETURN'),
]

for query, should_pass in tests_pass:
    valid, reason = validate_cypher(query)
    assert valid, f'Should pass: {query} — got: {reason}'

for query, expected_keyword in tests_fail:
    valid, reason = validate_cypher(query)
    assert not valid, f'Should fail: {query}'
    assert expected_keyword.lower() in reason.lower(), f'Expected {expected_keyword} in reason: {reason}'

print('OK: Query linter passes all tests')
"

# CHECKPOINT T2.3: Fallback queries
python3 -c "
from aegis_agents.fallback_queries import find_fallback

tests = [
    ('How many clauses does GDPR have?', True, 'MATCH'),
    ('List all regulations', True, 'MATCH'),
    ('Which subdomains have no coverage?', True, 'MATCH'),
    ('Show NIST controls for the PR function', True, 'MATCH'),
    ('What is the meaning of life?', False, None),
]

for question, should_match, expected_kw in tests:
    result = find_fallback(question)
    if should_match:
        assert result is not None, f'Expected fallback for: {question}'
        if expected_kw:
            assert expected_kw in result, f'Expected {expected_kw} in: {result}'
        print(f'OK: \"{question[:40]}...\" -> {result[:50]}...')
    else:
        print(f'OK: \"{question[:40]}...\" -> no fallback (expected)')

print('OK: Fallback queries work correctly')
"

# CHECKPOINT T2.4: nodes.py imports
python3 -c "
from aegis_agents.graph.nodes import exec_cypher, generate_and_execute, evaluate_and_decide, generate_answer
print('OK: nodes.py imports without errors')
"

# CHECKPOINT T2.5: Agent pre-flight
python3 -c "
from aegis_agents.agent import AegisAgent
agent = AegisAgent(max_attempts=3, use_tracing=False)
assert hasattr(agent, '_check_neo4j'), 'Missing _check_neo4j'
assert hasattr(agent, '_check_ollama'), 'Missing _check_ollama'
neo4j_ok = agent._check_neo4j()
ollama_ok = agent._check_ollama()
assert isinstance(neo4j_ok, bool), f'Expected bool, got {type(neo4j_ok)}'
assert isinstance(ollama_ok, bool), f'Expected bool, got {type(ollama_ok)}'
print(f'Neo4j: {\"OK\" if neo4j_ok else \"DOWN\"} | Ollama: {\"OK\" if ollama_ok else \"DOWN\"}')
print('OK: Agent pre-flight checks work')
"

# CHECKPOINT T2.6: Result validator
python3 -c "
from aegis_agents.result_validator import validate_result

result = {'error': None, 'data': [{'id': 'GDPR', 'name': 'GDPR'}], 'row_count': 1}
_, warnings = validate_result(result, 'test')
assert len(warnings) == 0, f'Unexpected warnings: {warnings}'

big_result = {'error': None, 'data': [{'id': i} for i in range(501)], 'row_count': 501}
_, warnings = validate_result(big_result, 'test')
assert len(warnings) > 0, 'Expected warnings for 501 rows'
print(f'OK: Result validator catches excessive rows: {warnings[0]}')
"

# CHECKPOINT T2.7: Extended state
python3 -c "
from aegis_agents.graph.state import AgentState
ann = AgentState.__annotations__
required = ['circuit_breaker_state', 'last_error_type', 'fallback_used', 'total_latency_ms', 'degraded_mode']
for field in required:
    assert field in ann, f'Missing field: {field}'
print(f'OK: AgentState has {len(required)} new fields')
"
```

### CHECKPOINT BATCH 4 (Integration):

```bash
python3 -c "
from aegis_agents.agent import AegisAgent

agent = AegisAgent(max_attempts=3, use_tracing=False)
result = agent.run('How many regulations are in the knowledge graph?')

assert 'answer' in result, 'Missing answer'
assert 'success' in result, 'Missing success'
assert 'steps' in result, 'Missing steps'

print(f'Success: {result[\"success\"]}')
print(f'Answer: {result[\"answer\"][:150]}')
print(f'Attempts: {result.get(\"attempt_count\", \"N/A\")}')
print(f'Steps: {len(result.get(\"steps\", []))}')

if 'degraded_mode' in result:
    print(f'Degraded: {result[\"degraded_mode\"]}')
if 'fallback_used' in result:
    print(f'Fallback used: {result[\"fallback_used\"]}')

print()
print('AGENT INTEGRATION TEST PASSED')
"
```

**Se TUDO passou:**
```bash
git add aegis_agents/circuit_breaker.py aegis_agents/query_linter.py \
        aegis_agents/fallback_queries.py aegis_agents/result_validator.py \
        aegis_agents/graph/nodes.py aegis_agents/graph/state.py \
        aegis_agents/agent.py
git commit -m "feat: add circuit breaker, query linter, fallback queries, graceful degradation"
```

**Output esperado ao utilizador:** "BATCH 4 COMPLETO. Pronto para Batch 5. Confirmas?"

---

## BATCH 5: TESTES DE CONSISTENCIA E FAILSAFES (~1h)

### T3.2 — Teste de Consistencia de Schema

**Novo ficheiro:** `scripts/test_schema_consistency.py`

```python
#!/usr/bin/env python3
"""Schema consistency test — verifies all agent-facing files use the same IDs and relationships.

Usage:
    python scripts/test_schema_consistency.py

Exit code 0 = all checks pass.
"""

import re
import sys


def check_file(filepath, patterns_must_exist, patterns_must_not_exist):
    """Check a file for required and forbidden patterns."""
    with open(filepath) as f:
        content = f.read()

    errors = []

    for pattern, description in patterns_must_exist:
        if not re.search(pattern, content):
            errors.append(f"  MISSING: {description} (pattern: {pattern})")

    for pattern, description in patterns_must_not_exist:
        if re.search(pattern, content):
            errors.append(f"  FORBIDDEN: {description} (pattern: {pattern})")

    return errors


def main():
    print("=" * 60)
    print("  Schema Consistency Test")
    print("=" * 60)

    all_errors = []

    # CHECK 1: SubDomain ID format
    print("\n[1] SubDomain ID format (DOT separator)")

    for filepath in [
        "aegis_agents/tools/schema_tool.py",
        "aegis_agents/graph/prompts.py",
        "aegis_agents/tools/neo4j_tool.py",
        "aegis_eval/schema_context.py",
    ]:
        print(f"  Checking {filepath}...")
        errors = check_file(filepath, [
            (r"D-\d{2}\.\d", "DOT format (D-XX.Y)"),
        ], [
            (r"D-\d{2}-\d", "DASH format (D-XX-Y) — forbidden"),
        ])
        if errors:
            all_errors.extend([(filepath, e) for e in errors])
            for e in errors:
                print(f"    FAIL: {e}")
        else:
            print(f"    OK")

    # CHECK 2: Relationship names
    print("\n[2] Relationship names")

    for filepath in [
        "aegis_agents/tools/schema_tool.py",
        "aegis_agents/graph/prompts.py",
        "aegis_eval/schema_context.py",
    ]:
        print(f"  Checking {filepath}...")
        errors = check_file(filepath, [
            (r"CONTAINS", "CONTAINS relationship"),
        ], [
            (r"HAS_SUBDOMAIN", "HAS_SUBDOMAIN — forbidden (use CONTAINS)"),
        ])
        if errors:
            all_errors.extend([(filepath, e) for e in errors])
            for e in errors:
                print(f"    FAIL: {e}")
        else:
            print(f"    OK")

    # CHECK 3: API uses MAPPED_TO
    print("\n[3] API relationship names")

    errors = check_file("aegis_kg/api/app.py", [
        (r"MAPPED_TO", "MAPPED_TO relationship"),
    ], [
        (r"COVERS_SUBDOMAIN", "COVERS_SUBDOMAIN — forbidden (use MAPPED_TO)"),
    ])
    if errors:
        all_errors.extend([("aegis_kg/api/app.py", e) for e in errors])
        for e in errors:
            print(f"  FAIL: {e}")
    else:
        print("  OK")

    # CHECK 4: Fallback queries use correct format
    print("\n[4] Fallback queries format")

    errors = check_file("aegis_agents/fallback_queries.py", [], [
        (r"D-\d{2}-\d", "DASH format in fallback queries"),
        (r"HAS_SUBDOMAIN", "HAS_SUBDOMAIN in fallback queries"),
        (r"COVERS_SUBDOMAIN", "COVERS_SUBDOMAIN in fallback queries"),
    ])
    if errors:
        all_errors.extend([("aegis_agents/fallback_queries.py", e) for e in errors])
        for e in errors:
            print(f"  FAIL: {e}")
    else:
        print("  OK")

    # SUMMARY
    print("\n" + "=" * 60)
    if all_errors:
        print(f"  FAILED: {len(all_errors)} errors found")
        for filepath, error in all_errors:
            print(f"    {filepath}: {error}")
        return 1
    else:
        print("  ALL CONSISTENCY CHECKS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
```

### T3.1 — Teste de Failsafes

**Novo ficheiro:** `scripts/test_failsafes.py`

```python
#!/usr/bin/env python3
"""Failsafe component tests — verifies circuit breaker, linter, fallbacks, etc.

Usage:
    python scripts/test_failsafes.py

Exit code 0 = all tests pass.
"""

import sys


def test_circuit_breaker():
    """Test circuit breaker state transitions."""
    from aegis_agents.circuit_breaker import CircuitBreaker, CircuitOpenError

    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=2, success_threshold=2)
    assert cb.state == "CLOSED", f"Initial: expected CLOSED, got {cb.state}"

    for _ in range(3):
        try:
            cb.call(lambda: (_ for _ in ()).throw(ConnectionError("test")))
        except ConnectionError:
            pass

    assert cb.state == "OPEN", f"After 3 failures: expected OPEN, got {cb.state}"
    assert cb.is_open, "is_open should be True"

    try:
        cb.call(lambda: "should fail")
        assert False, "Should have raised CircuitOpenError"
    except CircuitOpenError:
        pass

    print("  [PASS] Circuit breaker state transitions")


def test_query_linter():
    """Test query validation."""
    from aegis_agents.query_linter import validate_cypher

    valid_queries = [
        "MATCH (r:Regulation) RETURN r.regulationId",
        "MATCH (c:Clause) WHERE c.regulationId = 'GDPR' RETURN count(c) AS total",
        "MATCH (sd:SubDomain) WHERE NOT EXISTS((:Clause)-[:MAPPED_TO]->(sd)) RETURN sd.name",
    ]
    for q in valid_queries:
        ok, reason = validate_cypher(q)
        assert ok, f"Should be valid: {q} — {reason}"

    invalid_queries = [
        ("CREATE (n:Test) RETURN n", "write"),
        ("MERGE (n:Test) RETURN n", "write"),
        ("MATCH (n) DELETE n", "write"),
        ("MATCH (n) REMOVE n.prop", "write"),
        ("MATCH (n) SET n.x = 1 RETURN n", "write"),
        ("MATCH (r:Regulation)", "RETURN"),
        ("", "Empty"),
    ]
    for q, kw in invalid_queries:
        ok, reason = validate_cypher(q)
        assert not ok, f"Should be invalid: {q}"
        assert kw.lower() in reason.lower() or "return" in reason.lower(), f"Expected '{kw}' in: {reason}"

    print("  [PASS] Query linter")


def test_fallback_queries():
    """Test fallback template matching."""
    from aegis_agents.fallback_queries import find_fallback

    should_match = [
        ("How many clauses does GDPR have?", "MATCH"),
        ("List all regulations", "MATCH"),
        ("Which subdomains have no coverage?", "MATCH"),
        ("Show NIST controls for the PR function", "MATCH"),
        ("What are the strategic tensions?", "MATCH"),
        ("Tell me about gap analysis", "MATCH"),
        ("How many NIST controls are there?", "MATCH"),
    ]
    for question, kw in should_match:
        result = find_fallback(question)
        assert result is not None, f"Should match: {question}"
        assert kw in result, f"Should contain {kw}: {result}"

    should_not_match = [
        "What is the meaning of life?",
        "Tell me a joke",
    ]
    for question in should_not_match:
        result = find_fallback(question)
        assert result is None, f"Should not match: {question} — got: {result}"

    print("  [PASS] Fallback queries")


def test_result_validator():
    """Test result validation."""
    from aegis_agents.result_validator import validate_result

    _, warnings = validate_result({"error": None, "data": [{"x": 1}], "row_count": 1}, "test")
    assert len(warnings) == 0, f"Expected no warnings: {warnings}"

    _, warnings = validate_result({"error": None, "data": [{"x": i} for i in range(501)], "row_count": 501}, "test")
    assert len(warnings) > 0, "Expected warning for 501 rows"

    _, warnings = validate_result({"error": "some error", "data": [], "row_count": 0}, "test")
    assert len(warnings) == 0, "Errors should not generate warnings"

    print("  [PASS] Result validator")


def test_extended_state():
    """Test extended agent state has new fields."""
    from aegis_agents.graph.state import AgentState
    ann = AgentState.__annotations__
    required = ["circuit_breaker_state", "last_error_type", "fallback_used", "total_latency_ms", "degraded_mode"]
    for field in required:
        assert field in ann, f"Missing field: {field}"

    print("  [PASS] Extended agent state")


def main():
    print("=" * 60)
    print("  Failsafe Component Tests")
    print("=" * 60)

    tests = [
        ("Circuit Breaker", test_circuit_breaker),
        ("Query Linter", test_query_linter),
        ("Fallback Queries", test_fallback_queries),
        ("Result Validator", test_result_validator),
        ("Extended State", test_extended_state),
    ]

    failed = []
    for name, test_func in tests:
        print(f"\n[{name}]")
        try:
            test_func()
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed.append((name, str(e)))

    print("\n" + "=" * 60)
    if failed:
        print(f"  FAILED: {len(failed)}/{len(tests)} tests")
        for name, error in failed:
            print(f"    {name}: {error}")
        return 1
    else:
        print(f"  ALL {len(tests)} TESTS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
```

### CHECKPOINTS BATCH 5:

```bash
# CHECKPOINT T3.2: Schema consistency
python3 scripts/test_schema_consistency.py
# EXPECTED: "ALL CONSISTENCY CHECKS PASSED", exit code 0

# CHECKPOINT T3.1: Failsafe tests
python3 scripts/test_failsafes.py
# EXPECTED: "ALL 5 TESTS PASSED", exit code 0

# CHECKPOINT BATCH 5 CONSOLIDADO:
python3 scripts/test_schema_consistency.py && echo "---" && python3 scripts/test_failsafes.py
# EXPECTED: ambos passam, exit code 0
```

**Se TUDO passou:**
```bash
git add scripts/test_schema_consistency.py scripts/test_failsafes.py
git commit -m "test: add schema consistency and failsafe component test suites"
```

**Output esperado ao utilizador:** "BATCH 5 COMPLETO. Pronto para Batch 6. Confirmas?"

---

## BATCH 6: DATA ENRICHMENT (~2-3h)

**Objetivo:** Enriquecer subdominios com keywords e expandir complementarity analysis.

### T1.6 — Enriquecer SubDomain keywords

**Ficheiro a editar:** `aegis_kg/data/02_subdomains.csv`

Adicionar colunas `keywords` e `examples` a TODAS as 38 linhas.

**Mapeamento de keywords por subdominio (referencia):**

| subDomainId | keywords | examples |
|---|---|---|
| D-01.1 | encryption,cryptography,AES,RSA,TLS,data-at-rest,data-in-transit | AES-256 for data at rest\|TLS 1.3 for data in transit |
| D-01.2 | key management,key rotation,HSM,key lifecycle,cryptographic key | RSA key rotation every 90 days\|HSM for master keys |
| D-01.3 | hashing,integrity check,SHA,HMAC,checksum,data integrity | SHA-256 for file integrity\|HMAC for message authentication |
| D-02.1 | access control,RBAC,ABAC,least privilege,identity,authorization | Role-based access for admin panels\|Attribute-based for cloud resources |
| D-02.2 | authentication,MFA,SSO,OAuth,SAML,password,biometric | Multi-factor auth for admin access\|OAuth 2.0 for API access |
| D-02.3 | identity management,IAM,user provisioning,deprovisioning,directory | Automated user provisioning via SCIM\|Centralized directory (LDAP/AD) |
| D-03.1 | logging,audit trail,SIEM,event log,monitoring,log retention | Centralized log collection via SIEM\|90-day audit log retention |
| D-03.2 | incident response,IR plan,incident handling,breach notification | 72-hour breach notification per GDPR\|Quarterly IR tabletop exercises |
| D-03.3 | vulnerability management,patch management,CVE,vulnerability scanning | Monthly vulnerability scans\|Critical patches within 72 hours |
| D-04.1 | network security,firewall,IDS,IPS,network segmentation,DMZ | Network segmentation for PCI zones\|Next-gen firewall with IPS |
| D-04.2 | endpoint security,EDR,antivirus,device management,MDM | EDR on all workstations\|Mobile device management for BYOD |
| D-04.3 | application security,WAF,input validation,secure coding,OWASP | WAF for web applications\|OWASP Top 10 in code review checklist |
| D-05.1 | data classification,data handling,data lifecycle,sensitivity labels | 4-tier data classification (Public/Internal/Confidential/Restricted)\|DLP for Confidential data |
| D-05.2 | data retention,retention policy,data disposal,records management | 7-year retention for financial records\|Secure disposal of media |
| D-05.3 | data backup,recovery,BCP,disaster recovery,RPO,RTO | Daily incremental backups\|RTO 4h / RPO 1h for critical systems |
| D-06.1 | secure SDLC,DevSecOps,code review,static analysis,CI/CD security | SAST in CI pipeline\|Peer code review for all merges |
| D-06.2 | container security,Docker,Kubernetes,image scanning,orchestration | Container image vulnerability scanning\|Kubernetes RBAC policies |
| D-06.3 | API security,rate limiting,authentication,API gateway,OWASP API | API gateway with rate limiting\|OAuth 2.0 token validation |
| D-07.1 | cloud security,IAM policies,cloud configuration,CSPM,multi-tenant | CSPM for cloud misconfiguration\|Least-privilege IAM roles |
| D-07.2 | supply chain security,third-party risk,vendor assessment,SBOM | SBOM for all software components\|Annual vendor security assessments |
| D-07.3 | open source security,dependency scanning,license compliance,SLSA | Automated dependency vulnerability scanning\|SLSA Level 3 build integrity |
| D-08.1 | security training,awareness,phishing simulation,security culture | Annual security awareness training\|Monthly phishing simulations |
| D-08.2 | security governance,risk management,policy framework,CISO,board reporting | Quarterly risk reporting to board\|Annual security policy review |
| D-08.3 | compliance management,regulatory mapping,audit,GDPR compliance,CRA compliance | Continuous compliance monitoring\|Annual external audit |
| D-09.1 | privacy by design,data minimization,PIA,DPIA,consent management | DPIA for high-risk processing\|Privacy-by-design in product development |
| D-09.2 | data subject rights,DSAR,right to erasure,right to access,portability | Automated DSAR handling within 30 days\|Self-service data export |
| D-09.3 | cross-border data transfer,SCCs,BCRs,data localization,adequacy | Standard Contractual Clauses for non-EU transfers\|Data localization assessment |
| D-10.1 | AI governance,algorithmic accountability,AI risk,AI ethics,transparency | AI risk assessment framework\|Algorithmic impact assessment |
| D-10.2 | AI transparency,explainable AI,model interpretability,XAI,right to explanation | Model cards for all ML models\|Explainability dashboards |
| D-10.3 | AI safety,robustness,adversarial testing,model validation,bias detection | Adversarial testing for critical AI systems\|Bias audits for HR AI tools |

**Depois de editar o CSV, criar script de reload:**

**Novo ficheiro:** `scripts/reload_subdomain_keywords.py`

```python
#!/usr/bin/env python3
"""Reload SubDomain keywords and examples from CSV into Neo4j.

Usage:
    python scripts/reload_subdomain_keywords.py
"""

import csv
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

NEO4J_HTTP = os.getenv("NEO4J_URI", "http://localhost:7474")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
AUTH = (NEO4J_USER, NEO4J_PASSWORD)
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "aegis_kg", "data", "02_subdomains.csv")


def exec_cypher(statement, params=None):
    url = f"{NEO4J_HTTP}/db/neo4j/tx/commit"
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}
    resp = requests.post(url, auth=AUTH, json=payload, timeout=30)
    if resp.status_code != 200:
        return None
    result = resp.json()
    if result.get("errors"):
        print(f"  ERROR: {result['errors'][0]['message']}")
        return None
    return result.get("results", [])


def main():
    print("Loading SubDomain keywords from CSV...")

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    updated = 0
    for row in rows:
        sd_id = row["subDomainId"]
        keywords = row.get("keywords", "")
        examples = row.get("examples", "")

        if not keywords.strip():
            continue

        cypher = """
        MATCH (sd:SubDomain {subDomainId: $sdId})
        SET sd.keywords = $keywords, sd.examples = $examples
        RETURN sd.subDomainId
        """
        result = exec_cypher(cypher, {"sdId": sd_id, "keywords": keywords, "examples": examples})
        if result:
            updated += 1
        else:
            print(f"  WARNING: Failed to update {sd_id}")

    print(f"Updated {updated}/{len(rows)} subdomains with keywords")

    verify = exec_cypher("MATCH (sd:SubDomain) WHERE sd.keywords IS NOT NULL RETURN count(sd)")
    count = verify[0]["data"][0]["row"][0] if verify else 0
    print(f"Verified: {count} subdomains with keywords in Neo4j")

    return 0 if count >= 30 else 1


if __name__ == "__main__":
    sys.exit(main())
```

### CHECKPOINTS T1.6:

```bash
# CHECKPOINT T1.6a: CSV tem novas colunas
python3 -c "
import csv
with open('aegis_kg/data/02_subdomains.csv') as f:
    reader = csv.DictReader(f)
    cols = reader.fieldnames
    assert 'keywords' in cols, f'Missing keywords. Got: {cols}'
    assert 'examples' in cols, f'Missing examples. Got: {cols}'
    rows = list(reader)
    assert len(rows) == 38, f'Expected 38, got {len(rows)}'
    empty_kw = [r['subDomainId'] for r in rows if not r.get('keywords','').strip()]
    assert len(empty_kw) == 0, f'Empty keywords for: {empty_kw}'
    print(f'OK: {len(rows)} subdomains with keywords and examples')
    for r in rows[:3]:
        print(f'  {r[\"subDomainId\"]}: {r[\"keywords\"][:60]}...')
"

# CHECKPOINT T1.6b: Script executa
python3 scripts/reload_subdomain_keywords.py
# EXPECTED: "Verified: 38 subdomains with keywords in Neo4j"

# CHECKPOINT T1.6c: Keywords no Neo4j
python3 -c "
import requests, os
AUTH = (os.getenv('NEO4J_USER','neo4j'), os.getenv('NEO4J_PASSWORD',''))
url = f'{os.getenv(\"NEO4J_URI\",\"http://localhost:7474\")}/db/neo4j/tx/commit'
r = requests.post(url, auth=AUTH, json={'statements':[{'statement':\"MATCH (sd:SubDomain) WHERE sd.keywords IS NOT NULL RETURN sd.subDomainId, sd.keywords ORDER BY sd.subDomainId\"}]}, timeout=10)
results = r.json()['results'][0]['data']
assert len(results) >= 30, f'Expected >= 30, got {len(results)}'
for row in results[:3]:
    print(f'  {row[\"row\"][0]}: {row[\"row\"][1][:60]}')
print(f'OK: {len(results)} subdomains with keywords in Neo4j')
"
```

### T1.7 — Expandir Complementarity Analysis

**Ficheiro a editar:** `aegis_kg/data/06_complementarity_analysis.csv`

Expandir de 1 para 10 linhas (todas as combinacoes de pares de 5 regulamentos):
GDPR-CRA, GDPR-NIS2, GDPR-DORA, GDPR-AIAct, CRA-NIS2, CRA-DORA, CRA-AIAct, NIS2-DORA, NIS2-AIAct, DORA-AIAct.

Cada linha deve ter: analysisId, regulation1Id, regulation2Id, overlapType, jaccardIndex,
overlapDescription, complementarityDescription, conflictDescription, recommendedApproach,
analysisDate, analyst.

**Depois de editar o CSV, re-executar:**
```bash
python aegis_kg/etl/11_load_complementarity_analysis.py
```

### CHECKPOINTS T1.7:

```bash
# CHECKPOINT T1.7a: CSV tem 10 pares
python3 -c "
import csv
with open('aegis_kg/data/06_complementarity_analysis.csv') as f:
    rows = list(csv.DictReader(f))
    assert len(rows) == 10, f'Expected 10, got {len(rows)}'
    for r in rows:
        assert r.get('overlapDescription','').strip(), f'Missing overlapDescription for {r.get(\"regulation1Id\")}-{r.get(\"regulation2Id\")}'
        assert r.get('conflictDescription','').strip(), f'Missing conflictDescription for {r.get(\"regulation1Id\")}-{r.get(\"regulation2Id\")}'
    print(f'OK: {len(rows)} pairs with descriptions')
"

# CHECKPOINT T1.7b: Neo4j actualizado
python3 -c "
import requests, os
AUTH = (os.getenv('NEO4J_USER','neo4j'), os.getenv('NEO4J_PASSWORD',''))
url = f'{os.getenv(\"NEO4J_URI\",\"http://localhost:7474\")}/db/neo4j/tx/commit'
r = requests.post(url, auth=AUTH, json={'statements':[{'statement':'MATCH (ca:ComplementarityAnalysis) RETURN count(ca)'}]}, timeout=10)
cnt = r.json()['results'][0]['data'][0]['row'][0]
assert cnt == 10, f'Expected 10, got {cnt}'
print(f'OK: {cnt} ComplementarityAnalysis nodes')
"
```

### CHECKPOINT BATCH 6:

```bash
# Validacao final de Phase 1 apos enrichment
cd aegis_kg && python validation/01_validate_phase1.py
# EXPECTED: All tests pass (podem ter mudado contagens de keywords)
```

**Se TUDO passou:**
```bash
git add aegis_kg/data/02_subdomains.csv aegis_kg/data/06_complementarity_analysis.csv \
        scripts/reload_subdomain_keywords.py
git commit -m "feat: enrich subdomain keywords (38) and complementarity analysis (10 pairs)"
```

**Output esperado ao utilizador:** "BATCH 6 COMPLETO. Pronto para Batch 7. Confirmas?"

---

## BATCH 7: BASELINE FINAL (~1h)

### T3.3 — Gerar novo baseline e comparar

**NOTA:** Este batch requer Ollama e Minimax API operacionais. Se nao estiverem disponiveis,
reportar ao utilizador e saltar.

```bash
# CHECKPOINT PRE-FLIGHT: Servicos disponiveis
python3 -c "
import requests
try:
    r = requests.get('http://localhost:11434/api/tags', timeout=3)
    assert r.status_code == 200
    print('Ollama: OK')
except Exception as e:
    print(f'Ollama: DOWN ({e})')

try:
    r = requests.get('http://localhost:7474', auth=('neo4j', 'd3fendtest'), timeout=3)
    assert r.status_code == 200
    print('Neo4j: OK')
except Exception as e:
    print(f'Neo4j: DOWN ({e})')

import os
key = os.getenv('MINIMAX_API_KEY', '')
if len(key) > 20:
    print('Minimax: OK (key configured)')
else:
    print('Minimax: NOT CONFIGURED')
"
```

Se todos os servicos estao OK:

```bash
# Correr eval (1 trial para velocidade)
cd /home/epmq/Desktop/Projects/aegis-kg-unified
python aegis_eval/run_eval.py \
  --tasks aegis_eval/task_bank.yaml \
  --trials 1 \
  --verbose 2>&1 | tee baseline_v2_run.log
```

### CHECKPOINTS BATCH 7:

```bash
# CHECKPOINT T3.3a: Resultado gerado
latest=$(ls -t aegis_eval/results/summary_task_bank_*.json 2>/dev/null | head -1)
if [ -z "$latest" ]; then
    echo "FATAL: No summary file generated"
    exit 1
fi
echo "Latest: $latest"
ls -la "$latest"
# EXPECTED: ficheiro recente, > 1KB

# CHECKPOINT T3.3b: Copiar para baseline oficial
cp "$latest" aegis_eval/results/baseline_stable_v2.json
ls -la aegis_eval/results/baseline_stable_v2.json

# CHECKPOINT T3.3c: Comparar com v1
python3 -c "
import json

v1 = json.load(open('aegis_eval/results/baseline_stable_v1.json'))
v2 = json.load(open('aegis_eval/results/baseline_stable_v2.json'))

print('=== BASELINE COMPARISON ===')
print(f'Pass Rate:  {v1[\"pass_rate\"]*100:.1f}% -> {v2[\"pass_rate\"]*100:.1f}%')
print()

for dim in v1['by_dimension']:
    old = v1['by_dimension'][dim]['overall_avg']
    new = v2['by_dimension'][dim]['overall_avg']
    delta = new - old
    arrow = '+' if delta > 0.05 else ('-' if delta < -0.05 else '=')
    print(f'  {dim:30s} {old:.2f} -> {new:.2f} [{arrow}] ({delta:+.2f})')

print()

if 'nist_retrieval' in v2['by_category'] and 'nist_retrieval' in v1['by_category']:
    nist_old = v1['by_category']['nist_retrieval']['avg_scores']
    nist_new = v2['by_category']['nist_retrieval']['avg_scores']
    print('NIST Retrieval (weakest in v1):')
    for metric in nist_old:
        o, n = nist_old[metric], nist_new[metric]
        arrow = '+' if n > o + 0.1 else ('-' if n < o - 0.1 else '=')
        print(f'  {metric:30s} {o:.2f} -> {n:.2f} [{arrow}]')

improvement = v2['pass_rate'] - v1['pass_rate']
if improvement > 0.05:
    print(f'\nSIGNIFICANT IMPROVEMENT: pass rate +{improvement*100:.1f}%')
elif improvement > 0:
    print(f'\nSLIGHT IMPROVEMENT: pass rate +{improvement*100:.1f}%')
elif improvement >= -0.05:
    print(f'\nSTABLE: pass rate {improvement*100:+.1f}%')
else:
    print(f'\nREGRESSION: pass rate {improvement*100:+.1f}% — investigate!')
"
```

**Se baseline gerado com sucesso:**
```bash
git add aegis_eval/results/baseline_stable_v2.json
git commit -m "eval: add baseline v2 with data quality + failsafe improvements"
```

**Output esperado ao utilizador:**
"BATCH 7 COMPLETO. Todos os batches executados. Pronto para merge em master quando quiseres."

**Se servicos NAO estao disponiveis:**
Reportar ao utilizador: "BATCH 7 requer Ollama + Minimax + Neo4j operacionais. Baseline adiado. Todos os outros batches estao completos."

---

## CHECKLIST FINAL (Correr TUDO)

```bash
echo "=== F1: No dash format ==="
rg "D-01-1" aegis_agents/ aegis_eval/schema_context.py 2>/dev/null || echo "PASS"

echo "=== F2: DOT format everywhere ==="
rg -l "D-01\.1" aegis_agents/ aegis_eval/schema_context.py | wc -l
# EXPECTED: >= 4

echo "=== F3: No COVERS_SUBDOMAIN in API ==="
rg "COVERS_SUBDOMAIN" aegis_kg/api/app.py || echo "PASS"

echo "=== F4: No HAS_SUBDOMAIN in agent ==="
rg "HAS_SUBDOMAIN" aegis_agents/ || echo "PASS"

echo "=== F5: Regulation names populated ==="
python3 -c "
import requests, os
AUTH = (os.getenv('NEO4J_USER','neo4j'), os.getenv('NEO4J_PASSWORD',''))
url = f'{os.getenv(\"NEO4J_URI\",\"http://localhost:7474\")}/db/neo4j/tx/commit'
r = requests.post(url, auth=AUTH, json={'statements':[{'statement':'MATCH (r:Regulation) WHERE r.name IS NULL RETURN count(r)'}]}, timeout=10)
cnt = r.json()['results'][0]['data'][0]['row'][0]
print(f'{\"PASS\" if cnt == 0 else \"FAIL\"}: {cnt} regulations with NULL name')
"

echo "=== F6: SubDomainMetrics deleted ==="
python3 -c "
import requests, os
AUTH = (os.getenv('NEO4J_USER','neo4j'), os.getenv('NEO4J_PASSWORD',''))
url = f'{os.getenv(\"NEO4J_URI\",\"http://localhost:7474\")}/db/neo4j/tx/commit'
r = requests.post(url, auth=AUTH, json={'statements':[{'statement':'MATCH (m:SubDomainMetrics) RETURN count(m)'}]}, timeout=10)
cnt = r.json()['results'][0]['data'][0]['row'][0]
print(f'{\"PASS\" if cnt == 0 else \"FAIL\"}: {cnt} SubDomainMetrics nodes')
"

echo "=== F7-F9: Files exist ==="
ls aegis_agents/circuit_breaker.py && echo "F7: PASS" || echo "F7: FAIL"
ls aegis_agents/fallback_queries.py && echo "F8: PASS" || echo "F8: FAIL"
ls aegis_agents/query_linter.py && echo "F9: PASS" || echo "F9: FAIL"

echo "=== F10-F11: Test suites ==="
python3 scripts/test_schema_consistency.py && echo "F10: PASS" || echo "F10: FAIL"
python3 scripts/test_failsafes.py && echo "F11: PASS" || echo "F11: FAIL"

echo "=== F12: Phase 1 validation ==="
cd aegis_kg && python validation/01_validate_phase1.py && echo "F12: PASS" || echo "F12: FAIL"

echo "=== F13: Baseline v2 exists ==="
ls aegis_eval/results/baseline_stable_v2.json && echo "F13: PASS" || echo "F13: SKIP (no services)"

echo "=== F15: No secrets ==="
git diff --stat master | grep -i "\.env" && echo "F15: FAIL - .env in diff!" || echo "F15: PASS"
```

---

## ROLLBACK PLAN

Se algo correr mal em qualquer batch:

```bash
# Ver quais commits foram feitos
git log --oneline feature/data-quality-failsafes --not master

# Reverter ultimo commit (mantem alteracoes como unstaged)
git reset --soft HEAD~1

# Descartar TODAS as alteracoes e voltar ao estado do ultimo commit
git checkout -- .

# Reverter TUDO e voltar a master
git checkout master
git branch -D feature/data-quality-failsafes
```

---

## RESUMO DE COMMITS ESPERADOS

| Batch | Commit Message |
|-------|---------------|
| 1 | `fix: sync agent schema to DOT format (D-01.1) and CONTAINS relationship` |
| 2 | `fix: API uses MAPPED_TO instead of COVERS_SUBDOMAIN, remove applicable filter` |
| 3 | `feat: add script to fix NULL properties and remove phantom SubDomainMetrics` |
| 4 | `feat: add circuit breaker, query linter, fallback queries, graceful degradation` |
| 5 | `test: add schema consistency and failsafe component test suites` |
| 6 | `feat: enrich subdomain keywords (38) and complementarity analysis (10 pairs)` |
| 7 | `eval: add baseline v2 with data quality + failsafe improvements` |
