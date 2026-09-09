# tests/test_server_endpoints.py
import pytest
from fastapi.testclient import TestClient
from src.server.app import app, PIPELINE_STATE

client = TestClient(app)

def test_profile_endpoints():
    res = client.get("/api/profile")
    assert res.status_code == 200
    data = res.json()
    assert "name" in data
    assert "skills" in data

    update_payload = {
        "name": "Amartya Dev",
        "title": "Senior AI Systems Engineer",
        "email": "amartya.test@gmail.com",
        "skills": ["python", "fastapi", "docker", "sql"],
        "raw_resume_text": (
            "# AMARTYA DEV\n"
            "Senior AI Systems Engineer | Bengaluru, India\n\n"
            "## Core Competencies\nPython, FastAPI, Docker, SQL, Redis, LangGraph\n\n"
            "## Professional Experience\n\n"
            "### Lead AI Engineer - Azrael Dev\n"
            "- Built autonomous multi-agent pipelines with LangGraph\n"
            "- Deployed production backend microservices in FastAPI\n"
        )
    }
    post_res = client.post("/api/profile", json=update_payload)
    assert post_res.status_code == 200
    res_data = post_res.json()
    assert res_data["profile"]["name"] == "Amartya Dev"

def test_approve_job_flow():
    test_job = {
        "job_id": "test-job-999",
        "title": "Lead AI Systems Engineer",
        "company": "DeepMind Technologies",
        "url": "https://careers.deepmind.com/jobs/999",
        "tailored_bullet": "Architected resilient multi-agent graph workflows with LangGraph and FastAPI.",
        "fit_score": 95,
        "email_subject": "Application: Lead AI Systems Engineer - Amartya Dev",
        "email_body": "Hi Talent Team, I recently applied..."
    }
    # Ensure job is in approval queue
    PIPELINE_STATE["approval_queue"].append(test_job)

    approve_res = client.post("/api/approve/test-job-999")
    assert approve_res.status_code == 200
    data = approve_res.json()
    assert "Job approved!" in data["message"]
    assert data["applied"]["job_id"] == "test-job-999"
    assert "outreach" in data

    # Subsequent call should report already approved
    reapprove_res = client.post("/api/approve/test-job-999")
    assert reapprove_res.status_code == 200
    assert "already" in reapprove_res.json()["message"]

def test_autofill_linkedin_fastpath():
    test_job = {
        "job_id": "linkedin-job-888",
        "title": "Python Engineer",
        "company": "LinkedIn Company",
        "url": "https://www.linkedin.com/jobs/view/888",
        "tailored_bullet": "Developed scalable microservices in Python."
    }
    PIPELINE_STATE["approval_queue"].append(test_job)

    autofill_res = client.post("/api/apply/autofill/linkedin-job-888")
    assert autofill_res.status_code == 200
    data = autofill_res.json()
    assert data["result"]["ats_type"] == "linkedin"
    assert "LinkedIn job postings require an active authenticated LinkedIn session" in data["result"]["message"]

def test_cover_letter_generation_endpoint():
    test_job = {
        "job_id": "test-cl-123",
        "title": "Staff AI Systems Engineer",
        "company": "DeepMind",
        "tailored_bullet": "Orchestrated autonomous agents in LangGraph with verified truth guardrails."
    }
    PIPELINE_STATE["approval_queue"].append(test_job)
    res_html = client.get("/api/cover-letter/test-cl-123?format=html")
    assert res_html.status_code == 200
    assert "<!DOCTYPE html>" in res_html.text
    assert "DeepMind" in res_html.text

    res_md = client.get("/api/cover-letter/test-cl-123?format=markdown")
    assert res_md.status_code == 200
    assert "Staff AI Systems Engineer" in res_md.text

def test_resume_refine_endpoint():
    payload = {
        "raw_resume_text": "# Amartya Dev\n- Worked on python backend microservices\n- Helped with databases",
        "career_direction": "Senior AI Systems Engineer"
    }
    res = client.post("/api/resume/refine", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "refined_resume" in data
    assert "# Amartya Dev" in data["refined_resume"]
    assert "improvements" in data
    assert len(data["improvements"]) > 0

def test_onboarding_interview_endpoint():
    payload = {
        "raw_resume_text": (
            "# AMARTYA DEV\n"
            "Senior AI Systems Engineer | Bengaluru, India\n\n"
            "## Core Competencies\nPython, FastAPI, Docker, SQL, Redis, LangGraph\n\n"
            "## Professional Experience\n"
            "### Lead AI Systems Engineer - Azrael AI Systems\n"
            "- Built autonomous multi-agent pipelines with LangGraph\n"
            "- Deployed production backend microservices in FastAPI\n"
        ),
        "projects_experience": "Built autonomous pipelines in LangGraph and FastAPI",
        "tech_stack": "Python, Docker, FastAPI, PostgreSQL, Redis, LangGraph",
        "target_role": "Lead AI Engineer",
        "target_location": "India",
        "min_salary": "30 LPA"
    }
    res = client.post("/api/onboard-interview", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "profile" in data
    assert data["profile"]["name"] == "Amartya Dev"
    assert "LangGraph" in data["profile"]["skills"]

def test_verify_test_form_endpoint():
    res = client.post("/api/apply/verify-test-form")
    assert res.status_code == 200
    data = res.json()
    assert "ATS autofill successfully tested and verified" in data["message"]
    assert "result" in data
    assert len(data["result"].get("filled_fields", [])) > 0
    assert data.get("screenshot_url") is not None

def test_list_companies_endpoint():
    res = client.get("/api/companies")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 500
    assert "categories" in data
    assert "AI Startup" in data["categories"]
    assert len(data["companies"]) > 0

    # Test category filter
    res_ai = client.get("/api/companies?category=AI Startup")
    assert res_ai.status_code == 200
    data_ai = res_ai.json()
    assert len(data_ai["companies"]) > 30
    assert all(c["category"] == "AI Startup" for c in data_ai["companies"])

def test_add_company_endpoint():
    payload = {
        "name": "Acme AI Corp",
        "domain": "acme.ai",
        "category": "AI Startup",
        "ats_type": "ashby",
        "ats_identifier": "acme",
        "career_url": "https://jobs.ashbyhq.com/acme"
    }
    res = client.post("/api/companies", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "Acme AI Corp" in data["message"]
    assert data["company"]["domain"] == "acme.ai"

def test_scan_companies_career_pages_endpoint():
    payload = {
        "category": "AI Startup",
        "query": "AI Engineer",
        "location": "India",
        "limit": 2
    }
    res = client.post("/api/companies/scan", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "openings" in data
    assert data["openings_count"] >= 0


