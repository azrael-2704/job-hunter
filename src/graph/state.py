# src/graph/state.py
import operator
from typing import Annotated, Any, Optional
from typing_extensions import TypedDict

class JobHunterState(TypedDict):
    """
    Represents the central state for the state machine. Contains source of truth, queues for each state and audit telemetry.
    """
    # Source of Truth
    master_profile: dict[str, Any]
    allowed_skills: set[str]

    # Stage Queues
    discovered_queue: Annotated[list[dict[str, Any]], operator.add]
    qualified_queue: Annotated[list[dict[str, Any]], operator.add]
    approval_queue: Annotated[list[dict[str, Any]], operator.add]
    applied_queue: Annotated[list[dict[str, Any]], operator.add]
    recruiter_queue: Annotated[list[dict[str, Any]], operator.add]
    outreach_queue: Annotated[list[dict[str, Any]], operator.add]

    # Execution Pointers
    active_job_id: Optional[str]
    current_status: str

    # Telemetry
    audit_logs: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[str], operator.add]