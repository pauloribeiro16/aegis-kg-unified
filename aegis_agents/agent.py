"""LangGraph ReAct agent with feedback loops and Langfuse tracing."""

from langgraph.graph import StateGraph, START, END

from aegis_agents.config import LANGFUSE_CONFIG
from aegis_agents.graph.state import AgentState
from aegis_agents.graph.nodes import (
    generate_and_execute,
    evaluate_and_decide,
    generate_answer,
)
from aegis_agents.graph.router import should_continue
from aegis_agents.graph.prompts import setup_prompts_in_langfuse


def get_langfuse_callback():
    """Create and return Langfuse callback handler."""
    try:
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler
        langfuse = Langfuse(
            public_key=LANGFUSE_CONFIG["public_key"],
            secret_key=LANGFUSE_CONFIG["secret_key"],
            host=LANGFUSE_CONFIG["host"],
        )
        handler = CallbackHandler()
        return handler, langfuse
    except ImportError as e:
        print(f"  [Langfuse] Not available: {e}")
        return None, None


def build_agent_graph():
    """Build and compile the LangGraph agent."""
    graph = StateGraph(AgentState)

    graph.add_node("generate_and_execute", generate_and_execute)
    graph.add_node("evaluate_and_decide", evaluate_and_decide)
    graph.add_node("generate_answer", generate_answer)

    graph.add_edge(START, "generate_and_execute")
    graph.add_edge("generate_and_execute", "evaluate_and_decide")
    graph.add_conditional_edges("evaluate_and_decide", should_continue)
    graph.add_edge("generate_answer", END)

    return graph.compile()


class AegisAgent:
    """LangGraph ReAct agent for AEGIS KG with feedback loops."""

    def __init__(self, max_attempts: int = 3, use_tracing: bool = True):
        self.max_attempts = max_attempts
        self.use_tracing = use_tracing

        self.langfuse_handler = None
        self.langfuse = None

        if use_tracing:
            self.langfuse_handler, self.langfuse = get_langfuse_callback()
            setup_prompts_in_langfuse()

        self.graph = build_agent_graph()

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

    def run(self, question: str) -> dict:
        """Run the agent with feedback loop."""
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

        initial_state: AgentState = {
            "messages": [],
            "question": question,
            "attempt": 1,
            "max_attempts": self.max_attempts,
            "cypher": None,
            "query_result": None,
            "answer": None,
            "success": False,
            "steps": [],
        }

        config = {}
        if self.langfuse_handler:
            config["callbacks"] = [self.langfuse_handler]

        try:
            result = self.graph.invoke(initial_state, config=config)
        except Exception as e:
            return {
                "answer": f"Agent error: {str(e)}",
                "cypher": None,
                "steps": initial_state.get("steps", []),
                "success": False,
                "attempt_count": 1,
                "trace_id": None,
            }

        if self.langfuse:
            self.langfuse.flush()

        steps = result.get("steps", [])
        best_cypher = None
        for step in reversed(steps):
            if step.get("cypher"):
                best_cypher = step["cypher"]
                break

        return {
            "answer": result.get("answer", "No answer generated"),
            "cypher": best_cypher,
            "steps": steps,
            "success": result.get("success", False),
            "attempt_count": result.get("attempt", 1),
            "trace_id": getattr(self.langfuse_handler, "last_trace_id", None) if self.langfuse_handler else None,
        }


def run_agent(question: str, max_attempts: int = 3) -> dict:
    """Convenience function to run the agent."""
    agent = AegisAgent(max_attempts=max_attempts, use_tracing=False)
    return agent.run(question)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = "How many clauses does GDPR have?"

    print(f"Question: {question}")
    result = run_agent(question)

    print(f"\nSuccess: {result['success']}")
    print(f"Attempts: {result['attempt_count']}")
    print(f"Cypher: {result['cypher']}")
    print(f"\nAnswer: {result['answer']}")

    if result.get("steps"):
        print(f"\n--- Steps ---")
        for s in result["steps"]:
            print(f"  Attempt {s['attempt']}: rows={s.get('row_count')}, error={s.get('error')}")
