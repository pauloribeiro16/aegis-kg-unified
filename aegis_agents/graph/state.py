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
