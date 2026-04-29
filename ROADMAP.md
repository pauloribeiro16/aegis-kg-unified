# ROADMAP.md — AEGIS Knowledge Graph Unified

**Status:** Future / Not yet scheduled  
**Created:** 2026-04-28  
**Trigger:** Implement when the agent architecture needs multi-tool reasoning or multi-hop query planning.

---

## 1. Context

The current `AegisAgent` uses a **manual `StateGraph`** with three nodes (`generate_and_execute`, `evaluate_and_decide`, `generate_answer`) and a custom retry loop based on `row_count`, `error`, and `max_attempts`.

This architecture is optimal for the **current linear flow** (Question → Cypher → Execute → Retry/Answer) and powers a mature evaluation pipeline (`run_eval.py` + `minimax_judge.py`) that depends on structured `steps`, `cypher`, and `attempt` fields.

However, as requirements grow, a **ReAct pattern** (`create_react_agent` or hybrid tool-calling) may become beneficial.

---

## 2. Trigger Conditions

Only consider this migration when **at least 2 of the following 3** conditions are met:

| # | Condition | Current Status |
|---|-----------|----------------|
| 1 | **Multi-tool complexity:** Agent needs tools beyond Cypher (calculator, external compliance API, comparison engine, web search) | Not yet |
| 2 | **Multi-hop queries:** Tasks requiring sequential queries where the LLM must decide the next step (e.g. "Find regulation X, compare with NIST CSF 2.0, list gaps") | Not yet |
| 3 | **Dynamic schema exploration:** Agent must autonomously decide when to inspect schema vs. execute query directly | Not yet |

---

## 3. Target Architecture (Hybrid ReAct)

Instead of a pure `create_react_agent` (which would break the evaluation pipeline), implement a **hybrid**: keep the manual `StateGraph` and `AgentState`, but let the generation node use LangChain `.bind_tools()`.

```
START
  │
  ▼
┌──────────────────────────┐
│  generate_with_tools     │  ← NEW: LLM.bind_tools([cypher_query, schema_explorer])
│  (LLM decides which tool)│
└───────────┬──────────────┘
            │
            ▼
┌──────────────────────────┐
│   evaluate_and_decide    │  ← KEEP: retry logic based on row_count/error
│   (control preserved)    │
└───────────┬──────────────┘
            │
    ┌───────┴───────┐
    │               │
    ▼               ▼
┌─────────┐   ┌──────────────┐
│  Retry  │   │generate_answer│  ← KEEP: NL answer generation
│ (loop)  │   │              │
└─────────┘   └───────┬──────┘
                      │
                      ▼
                     END
```

---

## 4. Implementation Phases

### Phase 1 — Tool Consolidation & Infrastructure

**Goal:** Prepare tools and LLM wrapper without touching the graph.

- [ ] **Unify `exec_cypher`**: Remove duplication between `aegis_agents/graph/nodes.py` and `aegis_agents/tools/neo4j_tool.py`. Keep only the tool version.
- [ ] **Refine tool descriptions**: Ensure `cypher_query` and `schema_explorer` have clear docstrings/descriptions so the LLM knows when to call each.
- [ ] **Create `aegis_agents/graph/llm.py`**: New module with `get_llm()` returning a `ChatOllama` wrapper (replaces raw `requests.post()`).
- [ ] **Validate `ChatOllama` + `bind_tools()`**: Test that `ministral-3:latest` correctly invokes tools via LangChain.
- [ ] **Regression test**: Run full `run_eval.py` and snapshot scores as baseline.

**Files touched:**
- `aegis_agents/tools/neo4j_tool.py`
- `aegis_agents/tools/schema_tool.py`
- `aegis_agents/graph/llm.py` (new)

---

### Phase 2 — Hybrid Graph Node

**Goal:** Replace `generate_and_execute` with `generate_with_tools` while keeping `AgentState` intact.

- [ ] **Create `generate_with_tools(state) -> AgentState`**: 
  - Uses `get_llm().bind_tools([cypher_query, schema_explorer])`
  - Builds chat messages from `state["question"]` and `state["steps"]`
  - Intercepts tool calls, executes them, appends structured entries to `state["steps"]`
  - Increments `state["attempt"]`
- [ ] **Preserve `steps` structure**: Each step must include:
  ```python
  {
      "attempt": int,
      "tool_name": str,
      "tool_input": dict,
      "tool_output": dict,
      "cypher": str | None,
      "error": str | None,
      "row_count": int,
      "latency_ms": int,
  }
  ```
- [ ] **Preserve `cypher` field**: Extract Cypher from the last successful tool call and write to `state["cypher"]`.

**Files touched:**
- `aegis_agents/graph/nodes.py`
- `aegis_agents/graph/state.py` (if fields need extension)

---

### Phase 3 — Router & Answer Node

**Goal:** Keep existing control flow.

- [ ] **Keep `evaluate_and_decide`**: Logic remains unchanged (checks last step for `error` and `row_count`).
- [ ] **Keep `should_continue`**: Routes to retry or answer based on `attempt` vs `max_attempts`.
- [ ] **Update `generate_answer`**: Switch from raw Ollama HTTP to `ChatOllama.invoke()` via `get_llm()`.

**Files touched:**
- `aegis_agents/graph/nodes.py`
- `aegis_agents/graph/router.py`

---

### Phase 4 — Graph Wiring

**Goal:** Update `build_agent_graph()` to use the new node.

```python
def build_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("generate_with_tools", generate_with_tools)  # was: generate_and_execute
    graph.add_node("evaluate_and_decide", evaluate_and_decide)
    graph.add_node("generate_answer", generate_answer)
    
    graph.add_edge(START, "generate_with_tools")
    graph.add_edge("generate_with_tools", "evaluate_and_decide")
    graph.add_conditional_edges("evaluate_and_decide", should_continue)
    graph.add_edge("generate_answer", END)
    
    return graph.compile()
```

**Files touched:**
- `aegis_agents/agent.py`

---

### Phase 5 — Langfuse Tracing Decision

**Goal:** Ensure observability is preserved.

**Option A (Recommended initially):** Keep manual `log_generation()` calls inside `generate_with_tools` and `generate_answer`. This preserves the current trace hierarchy (`cypher_generation`, `answer_generation` spans).

**Option B (Simpler):** Rely on LangChain's `CallbackHandler` for automatic tracing. This is less granular but requires zero code.

**Decision:** Start with Option A to avoid breaking the evaluation pipeline's trace expectations. Migrate to Option B only if maintenance burden becomes too high.

**Files touched:**
- `aegis_agents/graph/nodes.py`
- `aegis_agents/tracing.py` (if extending)

---

### Phase 6 — Evaluation Pipeline Validation

**Goal:** Prove the migration does not regress quality.

- [ ] Run `python aegis_eval/run_eval.py --tasks aegis_eval/task_bank.yaml --trials 1 --verbose`
- [ ] Compare scores with Phase 1 baseline
- [ ] Verify `minimax_judge.py` can still read `result["steps"]`, `result["cypher"]`, `result["answer"]`
- [ ] Verify Langfuse traces show correct hierarchy and scores
- [ ] **Acceptance criteria:**
  - Zero crashes in eval
  - Average judge score does not drop >5% vs. baseline
  - Latency does not increase >20% vs. baseline

**Files touched:**
- `aegis_eval/run_eval.py` (if adjustments needed)
- `aegis_eval/minimax_judge.py` (if adjustments needed)

---

## 5. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `ministral-3` handles tool-calling poorly | Medium | High | Test `bind_tools()` extensively in Phase 1; upgrade model if needed |
| `bind_tools()` unsupported or buggy with local Ollama | Low | High | Validate with unit tests before graph integration; fallback to manual tool parsing |
| Evaluation pipeline breaks | Medium | Critical | Keep `main` branch backup; run side-by-side comparison |
| Latency increases due to chat format overhead | Medium | Medium | Benchmark in Phase 1; optimize prompt templates |
| Increased complexity without clear benefit | High (if triggers not met) | Medium | **Do NOT start this migration unless triggers are met** |

---

## 6. Alternative: Pure `create_react_agent` (NOT Recommended for AEGIS)

If future requirements justify a fully dynamic agent (e.g. 5+ tools, complex planning), a pure `create_react_agent` could be considered. However, this would require:

1. **Rewriting `AgentState`** to only contain `messages` (losing `steps`, `attempt`, `cypher`)
2. **Rewriting `run_eval.py`** and `minimax_judge.py` to parse tool calls from message history
3. **Accepting generic Langfuse tracing** instead of named spans

**Verdict:** Only pursue if the hybrid approach proves insufficient.

---

## 7. References

- `aegis_agents/agent.py` — Current StateGraph builder
- `aegis_agents/graph/nodes.py` — Nodes to refactor
- `aegis_agents/graph/router.py` — Routing logic to preserve
- `aegis_agents/graph/state.py` — State schema to maintain
- `aegis_agents/tools/neo4j_tool.py` — Cypher tool to integrate
- `aegis_agents/tools/schema_tool.py` — Schema tool to integrate
- `aegis_agents/tracing.py` — Langfuse utilities
- `aegis_eval/run_eval.py` — Eval runner to validate
- `aegis_eval/minimax_judge.py` — Judge that depends on `steps` and `cypher`
- `AGENTS.md` §9 — Langfuse tracing rules (do not change without owner approval)

---

**End of ROADMAP**
