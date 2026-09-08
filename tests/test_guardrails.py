# tests/test_guardrails.py
import pytest
from src.core.guardrails import validate_tech_stack

def test_valid_bullet_with_allowed_skills():
    """
    Test that a bullet point with only allowed skills passes with no violations.
    """
    allowed = {"docker"}
    text = "Containerized microservices using Docker for streamlined local development."
    isValid, violations = validate_tech_stack(text, allowed)
    assert isValid
    assert violations == []

def test_hallucinated_skill_is_caught():
    """
    Test that an unapproved technology (kubernetes) is caught as a violation.
    """
    allowed = {"docker"}
    text = "Orchestrated container deployments using Kubernetes across clusters."
    is_valid, violations = validate_tech_stack(text, allowed)
    assert is_valid is False
    assert "kubernetes" in violations

def test_punctuation_stripping():
    """
    Test that punctuation attached to words like '(kubernetes).' does not fool the guardrail.
    """
    allowed = {"docker"}
    text = "Managed infrastructure with (Kubernetes), ensuring 99.9% uptime."
    is_valid, violations = validate_tech_stack(text, allowed)
    assert is_valid is False
    assert "kubernetes" in violations

def test_no_tech_words_passes():
    """
    Test that ordinary descriptive text with no tech keywords passes easily.
    """
    allowed = set()
    text = "Collaborated closely with cross-functional product management teams."
    is_valid, violations = validate_tech_stack(text, allowed)
    assert is_valid is True
    assert violations == []
