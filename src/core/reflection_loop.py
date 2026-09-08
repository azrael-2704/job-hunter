# src/core/reflection_loop.py
from datetime import datetime, timezone
from typing import Callable, Any, Generic, TypeVar
from src.core.guardrails import validate_tech_stack
import json

T_Input = TypeVar('T_Input')
T_Output = TypeVar('T_Output')

class ReflectionLoop(Generic[T_Input, T_Output]):
    """
    A reflectionn loop with circuit breaking and structured logging.
    """
    def __init__(
        self,
        generate_fn: Callable[[T_Input, str | None], T_Output],
        validate_fn: Callable[[T_Output], tuple[bool, str | None]],
        max_retries: int = 3,
        name: str = "generic_reflection_loop"
    ):

        self.generate_fn = generate_fn
        self.validate_fn = validate_fn
        self.max_retries = max_retries
        self.name = name
        self.audit_log : list[dict[str, Any]] = []

    def _log_event(self, event_type: str, attempt: int, details: dict[str, Any]) -> None:
        """
        Internal helper to log telemetry with UTC Timestamp.
        """
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "loop_name": self.name,
            "event_type": event_type,
            "attempt": attempt,
            **details
        }
        self.audit_log.append(record)
        print("[ReflectionLoop]" + json.dumps(record, indent = 2, default = str))
    
    def run(self, input_data: T_Input, fallback_output: T_Output) -> tuple[T_Output, bool]:
        """
        Executes the reflection loop.
        Returns: (final_output, success_bool)
        """
        critique = None
        self._log_event("LOOP_STARTED", 0, {"input": str(input_data)})

        for attempt in range(1, self.max_retries + 1):
            self._log_event("GENERATION_ATTEMPT", attempt, {})
            candidate = self.generate_fn(input_data, critique)
            isValid, reason = self.validate_fn(candidate)
            
            if isValid:
                self._log_event("SUCCESS", attempt, {
                    "output": str(candidate),
                    "attempts_taken": attempt,
                    "message": "Candidate passed all guardrails"
                })
                return candidate, True
            
            self._log_event("GUARDRAIL_VIOLATION", attempt, {
                "candidate": candidate,
                "reason": reason,
                "action": "Triggering reflection retry" if attempt < self.max_retries else "Tripping circuit breaker"
            })
            critique = reason
        
        self._log_event("CIRCUIT_BREAKER_TRIPPED", self.max_retries, {
            "fallback_used": fallback_output,
            "message": f"Exceeded max retries ({self.max_retries}). Reverting to fallback."
        })
        return fallback_output, False