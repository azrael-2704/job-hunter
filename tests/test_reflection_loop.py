# tests/test_reflection_loop.py
import pytest
from src.core.reflection_loop import ReflectionLoop
from src.core.guardrails import validate_tech_stack

def test_reflection_loop_success_first_attempt():
    """
    Test when the generator produces a valid candidate on attempt 1.
    """
    def mock_generator(input_text: str, critique: str | None) -> str:
        return "Built microservices using Docker."

    def mock_validator(text: str) -> tuple[bool, str | None]:
        is_valid, violations = validate_tech_stack(text, allowed_skills={"docker"})
        reason = f"Forbidden tech: {violations}" if not is_valid else None
        return is_valid, reason

    loop = ReflectionLoop(
        generate_fn=mock_generator,
        validate_fn=mock_validator,
        max_retries=3,
        name="test_first_try"
    )

    result, success = loop.run(
        input_data="Original bullet",
        fallback_output="Fallback bullet"
    )

    assert success is True
    assert result == "Built microservices using Docker."
    # Verify audit log recorded SUCCESS on attempt 1
    events = [entry["event_type"] for entry in loop.audit_log]
    assert "LOOP_STARTED" in events
    assert "SUCCESS" in events
    assert "CIRCUIT_BREAKER_TRIPPED" not in events


def test_reflection_loop_self_corrects_on_second_attempt():
    """
    Test when attempt 1 hallucinates kubernetes, gets critique,
    and self-corrects on attempt 2.
    """
    def mock_generator(input_text: str, critique: str | None) -> str:
        # On first attempt, critique is None -> hallucinate kubernetes
        if critique is None:
            return "Orchestrated apps with Kubernetes."
        # On second attempt, critique is present -> self-correct to docker
        return "Containerized apps with Docker."

    def mock_validator(text: str) -> tuple[bool, str | None]:
        is_valid, violations = validate_tech_stack(text, allowed_skills={"docker"})
        reason = f"Forbidden tech: {violations}" if not is_valid else None
        return is_valid, reason

    loop = ReflectionLoop(
        generate_fn=mock_generator,
        validate_fn=mock_validator,
        max_retries=3,
        name="test_self_correction"
    )

    result, success = loop.run(
        input_data="Original bullet",
        fallback_output="Fallback bullet"
    )

    assert success is True
    assert result == "Containerized apps with Docker."
    
    # Check the audit trail to confirm reflection occurred
    events = [entry["event_type"] for entry in loop.audit_log]
    assert events.count("GUARDRAIL_VIOLATION") == 1
    assert "SUCCESS" in events


def test_reflection_loop_circuit_breaker_fallback():
    """
    Test that stubborn generator triggers circuit breaker and returns fallback.
    """
    def stubborn_generator(input_text: str, critique: str | None) -> str:
        return "Always using Kubernetes forever."

    def mock_validator(text: str) -> tuple[bool, str | None]:
        is_valid, violations = validate_tech_stack(text, allowed_skills={"docker"})
        reason = f"Forbidden tech: {violations}" if not is_valid else None
        return is_valid, reason

    loop = ReflectionLoop(
        generate_fn=stubborn_generator,
        validate_fn=mock_validator,
        max_retries=2,
        name="test_circuit_breaker"
    )

    result, success = loop.run(
        input_data="Original bullet",
        fallback_output="Safe fallback bullet"
    )

    assert success is False
    assert result == "Safe fallback bullet"
    
    # Verify circuit breaker was logged
    events = [entry["event_type"] for entry in loop.audit_log]
    assert "CIRCUIT_BREAKER_TRIPPED" in events
