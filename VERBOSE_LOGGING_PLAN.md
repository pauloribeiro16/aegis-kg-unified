# Verbose Logging Plan — Eval Pipeline

**Date:** 2026-05-04
**Purpose:** Add verbose logging to understand what the agent/judge pipeline does during eval.

---

## Problem

`run_eval.py --verbose` shows only:
- "Running agent..." / "Agent done" / "Running Minimax judge..." / "Judge done"

It does NOT show:
- Which Cypher was generated
- How many rows returned
- Errors encountered
- Retry attempts
- Fallback usage
- Judge scoring breakdown
- Internal agent decisions

---

## Ficheiros a alterar

### 1. `aegis_agents/graph/nodes.py`

Add prints in `generate_and_execute`:
```python
# After getting raw from Ollama
print(f"[agent] Attempt {attempt}: Ollama response ({elapsed/1000:.1f}s): {cypher[:100] if cypher else 'FAILED'}")
print(f"[agent] Cypher exec ({result.get('latency_ms',0):.0f}ms): rows={result.get('row_count',0)}, error={result.get('error')}")
# If fallback used
print(f"[agent] FALLBACK triggered, used: {fallback_cypher}")
```

In `generate_answer`:
```python
print(f"[agent] Generating answer from {row_count} rows...")
print(f"[agent] Answer generated: {answer[:100]}...")
```

### 2. `aegis_agents/agent.py`

In `run()` pre-flight checks:
```python
print(f"[agent] Pre-flight: Neo4j={'OK' if neo4j_ok else 'DOWN'}, Ollama={'OK' if ollama_ok else 'DOWN'}")
if fallback_cypher:
    print(f"[agent] FALLBACK MODE: using {fallback_cypher}")
```

### 3. `aegis_eval/minimax_judge.py`

Add prints before/after Minimax call:
```python
print(f"[judge] Calling Minimax M2.7 with prompt length: {len(prompt)}")
print(f"[judge] Minimax response ({(time.time()-t0):.1f}s): scores={scores}, error={error}")
```

### 4. `aegis_eval/run_eval.py`

Improve progress tracking:
```python
print(f"[{idx}/{total}] {task['id']} — ETA: {eta_str}")
print(f"  Cypher: {result.get('cypher', 'N/A')[:80]}")
print(f"  Answer: {result.get('llm_answer', '')[:100]}")
```

---

## Output format goal

```
  === Task 3/45: count_gdpr_clauses (trial 1) ===
  Q: How many clauses does GDPR have?
  [agent] Pre-flight: Neo4j=OK, Ollama=OK
  [agent] Attempt 1: Calling Ollama...
  [agent] Ollama response (2.3s): MATCH (c:Clause {regulationId: 'GDPR'}) RETURN count(c) AS total
  [agent] Cypher exec (0.1s): 1 rows, no error
  [agent] Decision: success=True, rows=1 → generate answer
  [agent] Answer generated (1.8s): "GDPR has 30 clauses..."
  [judge] Calling Minimax M2.7...
  [judge] Response (3.2s): scores={cypher_correctness_query: 5, ...}
  [PASS] count_gdpr_clauses_001 | cyph=4.5 quer=3.5 reas=4.0 tool=4.0 feed=3.0 | 7.4s
  [ETA] 2/45 done, ~35 min remaining
```

---

## Prefixes for filtering

- `[agent]` — Agent internal operations
- `[judge]` — Minimax judge operations
- `[ETA]` — Progress / time estimates
- `[API]` — Flask API calls

---

## Notes

- All prints use flush=True for real-time output
- Timestamps in ms for agent operations
- Human-readable durations for user-facing output
- Prefix-based filtering: `grep '\[agent\]\|\\[judge\]' log.txt`
