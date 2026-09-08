# tests/test_pipeline.py
import pytest
from src.graph.pipeline import build_job_hunter_pipeline

def test_pipeline_execution():
    """
    Tests that the LangGraph state machine compiles, executes nodes,
    updates queues, and routes through conditional edges.
    """
    pipeline = build_job_hunter_pipeline()

    initial_state = {
        "master_profile": {
            "name": "Test Candidate",
            "target_query": "Python Developer",
            "target_location": "Remote"
        },
        "allowed_skills": {"python", "docker", "fastapi"},
        "discovered_queue": [],
        "qualified_queue": [],
        "approval_queue": [],
        "applied_queue": [],
        "active_job_id": None,
        "current_status": "INITIALIZED",
        "audit_logs": [],
        "errors": []
    }

    final_state = pipeline.invoke(initial_state)

    # Assertions
    assert "discovered_queue" in final_state
    assert len(final_state["discovered_queue"]) > 0
    assert "qualified_queue" in final_state
    assert len(final_state["qualified_queue"]) > 0
    assert final_state["current_status"] in ["READY_FOR_APPROVAL", "JOBS_QUALIFIED"]
