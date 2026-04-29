"""Routing logic for Aegis agent feedback loop."""

from aegis_agents.graph.state import AgentState


def should_continue(state: AgentState) -> str:
    """Decide next action based on query result.

    Routes to:
    - "generate_answer" if success with rows
    - "generate_and_execute" if empty/error and attempts < max_attempts
    - "generate_answer" if max attempts reached (return what we have)
    """
    steps = state.get("steps", [])
    attempt = state.get("attempt", 1)
    max_attempts = state.get("max_attempts", 3)

    if not steps:
        return "generate_and_execute"

    last_step = steps[-1]
    success = last_step.get("error") is None

    if success:
        return "generate_answer"

    if attempt >= max_attempts:
        return "generate_answer"

    return "generate_and_execute"
