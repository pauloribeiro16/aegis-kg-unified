"""Langfuse tracing utilities for agents.

Provides functions to log prompts, generations, and scores to Langfuse
following best practices from the Langfuse documentation.
"""

import time
from typing import Any, Optional

from aegis_agents.config import LANGFUSE_CONFIG, OLLAMA_CONFIG, PROJECT_NAME, TRACE_NAME


_LANGFUSE_CLIENT = None


def get_langfuse_client():
    """Get Langfuse client singleton with explicit credentials."""
    global _LANGFUSE_CLIENT
    if _LANGFUSE_CLIENT is not None:
        return _LANGFUSE_CLIENT

    if not LANGFUSE_CONFIG.get("public_key") or not LANGFUSE_CONFIG.get("secret_key"):
        import logging
        logging.warning("LANGFUSE keys not configured. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY env vars.")
        return None

    try:
        from langfuse import Langfuse
        _LANGFUSE_CLIENT = Langfuse(
            public_key=LANGFUSE_CONFIG["public_key"],
            secret_key=LANGFUSE_CONFIG["secret_key"],
            host=LANGFUSE_CONFIG["host"],
        )
        return _LANGFUSE_CLIENT
    except ImportError:
        return None


def log_generation(
    name: str,
    input_data: dict,
    output_data: dict,
    model: Optional[str] = None,
    latency_ms: float = 0,
    metadata: Optional[dict] = None
) -> Optional[str]:
    """Log a generation (LLM call) to Langfuse.

    Args:
        name: Name of the generation (e.g., "cypher_generation", "answer_generation")
        input_data: Dict with input keys (e.g., {"question": "...", "schema": "..."})
        output_data: Dict with output keys (e.g., {"cypher": "...", "raw": "..."})
        model: Model name (defaults to OLLAMA_CONFIG model)
        latency_ms: Latency in milliseconds
        metadata: Additional metadata to log

    Returns:
        Trace ID if successful, None otherwise
    """
    langfuse = get_langfuse_client()
    if not langfuse:
        print("  [Langfuse] Client not available")
        return None

    try:
        with langfuse.start_as_current_observation(
            as_type="generation",
            name=name,
            input=input_data,
            output=output_data,
            model=model or OLLAMA_CONFIG["model"],
            metadata=metadata or {}
        ) as generation:
            # Generation is logged automatically via context manager
            pass

        langfuse.flush()
        trace_id = langfuse.get_current_trace_id()
        return trace_id
    except Exception as e:
        print(f"  [Langfuse generation log error: {e}]")
        return None


def log_span(
    name: str,
    input_data: Optional[dict] = None,
    output_data: Optional[dict] = None,
    metadata: Optional[dict] = None
):
    """Context manager for creating a span in Langfuse.

    Usage:
        with log_span("process-request", input={"query": "..."}) as span:
            # ... do work ...
            span.update(output={"result": "..."})
    """
    langfuse = get_langfuse_client()
    if not langfuse:
        yield type('obj', (object,), {'update': lambda s, **k: None, 'end': lambda s: None})()
        return

    try:
        with langfuse.start_as_current_observation(
            as_type="span",
            name=name,
            input=input_data or {},
            output=output_data or {},
            metadata=metadata or {}
        ) as span:
            yield span
    except Exception as e:
        print(f"  [Langfuse span log error: {e}]")
        yield type('obj', (object,), {'update': lambda s, **k: None, 'end': lambda s: None})()


def score_trace(
    scores: dict,
    trace_id: Optional[str] = None,
    observation_id: Optional[str] = None
):
    """Score a trace in Langfuse.

    Args:
        scores: Dict of {score_name: score_value} pairs
        trace_id: Optional trace ID (uses current trace if not provided)
        observation_id: Optional observation ID for the score
    """
    langfuse = get_langfuse_client()
    if not langfuse:
        return

    try:
        for score_name, score_value in scores.items():
            if trace_id:
                langfuse.create_score(
                    trace_id=trace_id,
                    observation_id=observation_id,
                    name=score_name,
                    value=score_value,
                    data_type="NUMERIC"
                )
            else:
                langfuse.score_current_trace(
                    name=score_name,
                    value=score_value,
                    data_type="NUMERIC"
                )
        langfuse.flush()
    except Exception as e:
        print(f"  [Langfuse score error: {e}]")


class AgentTracer:
    """Tracer for agent runs that logs prompts and generations to Langfuse.

    Usage:
        tracer = AgentTracer()

        # Log Cypher generation
        with tracer.log_generation("cypher_generation", input={"question": q}) as gen:
            cypher = generate_cypher(q)
            gen.update(output={"cypher": cypher})

        # Log execution
        with tracer.log_span("cypher_execution") as span:
            result = exec_cypher(cypher)
            span.update(output={"row_count": len(result)})

        # Finalize with scores
        tracer.finalize(scores={"quality": 4.5})
    """

    def __init__(self, session_id: Optional[str] = None, user_id: Optional[str] = None):
        self.langfuse = get_langfuse_client()
        self.session_id = session_id
        self.user_id = user_id
        self.trace_id = None
        self.generations = []

    def log_generation(self, name: str, input_data: dict, metadata: Optional[dict] = None):
        """Context manager for logging a generation.

        Returns a generation object that can be updated with output.
        """
        if not self.langfuse:
            yield type('obj', (object,), {'update': lambda s, **k: None})()
            return

        try:
            with self.langfuse.start_as_current_observation(
                as_type="generation",
                name=name,
                input=input_data,
                model=OLLAMA_CONFIG["model"],
                metadata=metadata or {}
            ) as generation:
                yield generation
        except Exception as e:
            print(f"  [Langfuse generation error: {e}]")
            yield type('obj', (object,), {'update': lambda s, **k: None})()

    def log_span(self, name: str, input_data: Optional[dict] = None, metadata: Optional[dict] = None):
        """Context manager for logging a span."""
        if not self.langfuse:
            yield type('obj', (object,), {'update': lambda s, **k: None, 'end': lambda s: None})()
            return

        try:
            with self.langfuse.start_as_current_observation(
                as_type="span",
                name=name,
                input=input_data or {},
                metadata=metadata or {}
            ) as span:
                yield span
        except Exception as e:
            print(f"  [Langfuse span error: {e}]")
            yield type('obj', (object,), {'update': lambda s, **k: None, 'end': lambda s: None})()

    def finalize(self, scores: Optional[dict] = None, output: Optional[dict] = None):
        """Finalize the trace with optional scores and output."""
        if not self.langfuse:
            return

        if scores:
            self.score_trace(scores)

        if output:
            try:
                self.langfuse.set_current_trace_io(
                    input={"session_id": self.session_id},
                    output=output
                )
            except Exception as e:
                print(f"  [Langfuse finalize error: {e}]")

        self.langfuse.flush()

    def score_trace(self, scores: dict):
        """Score the current trace."""
        score_trace(scores=scores)
