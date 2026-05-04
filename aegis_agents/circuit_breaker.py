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
