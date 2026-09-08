# tests/test_database.py
import tempfile
from pathlib import Path
from src.db.database import (
    init_db, save_job, save_tailored_application, update_tailored_application_status,
    update_tailored_email, save_outreach, load_all_state
)

def test_database_lifecycle():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        init_db(db_path)
        assert db_path.exists()

        # 1. Save Job
        job = {
            "id": "12345",
            "title": "Staff AI Engineer",
            "company": "DeepMind",
            "location": "London, UK",
            "url": "https://example.com/job/12345",
            "description": "Building autonomous agentic workflows in Python.",
            "fit_score": 95,
            "salary_info": {"detected": True, "currency": "USD", "min": 150000, "max": 200000},
            "salary_badge": "$150k - $200k",
            "status": "QUALIFIED"
        }
        save_job(job, db_path)

        # 2. Save Tailored Application
        app = {
            "job_id": "12345",
            "company": "DeepMind",
            "title": "Staff AI Engineer",
            "location": "London, UK",
            "url": "https://example.com/job/12345",
            "description": "Building autonomous agentic workflows in Python.",
            "fit_score": 95,
            "salary_badge": "$150k - $200k",
            "tailored_bullet": "Architected distributed agentic state machines with zero hallucinations.",
            "tailoring_success": True,
            "recruiter_name": "Talent Lead",
            "recruiter_email": "careers@deepmind.com",
            "email_subject": "Application: Staff AI Engineer - Amartya",
            "email_body": "Hi Talent Lead, I built production agentic pipelines.",
            "status": "PENDING_HUMAN_APPROVAL"
        }
        save_tailored_application(app, db_path)

        # 3. Update Email
        update_tailored_email("12345", "Updated Subject", "Updated Body", db_path)

        # 4. Save Outreach
        outreach = {
            "id": "out-1",
            "job_id": "12345",
            "company": "DeepMind",
            "recipient_name": "Talent Lead",
            "recipient_email": "careers@deepmind.com",
            "subject": "Updated Subject",
            "body": "Updated Body",
            "status": "SCHEDULED",
            "scheduled_send_at": "2026-09-08T10:00:00Z",
            "followup_at": "2026-09-11T10:00:00Z"
        }
        save_outreach(outreach, db_path)

        # 5. Load State
        state = load_all_state(db_path)
        assert len(state["discovered_queue"]) == 1
        assert state["discovered_queue"][0]["title"] == "Staff AI Engineer"
        assert len(state["approval_queue"]) == 1
        assert state["approval_queue"][0]["email_subject"] == "Updated Subject"
        assert len(state["outreach_queue"]) == 1

        # 6. Approve Job
        update_tailored_application_status("12345", "APPLIED", db_path)
        state_after_approval = load_all_state(db_path)
        assert len(state_after_approval["approval_queue"]) == 0
        assert len(state_after_approval["applied_queue"]) == 1
