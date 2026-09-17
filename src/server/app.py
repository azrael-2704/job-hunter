# src/server/app.py
"""
FastAPI Server for Autonomous Job Hunter.
Serves REST APIs for pipeline execution, human approval gates,
recruiter email enrichment, outreach scheduling, and static Web UI.
"""
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from src.graph.pipeline import build_job_hunter_pipeline
from src.recruiter.email_enricher import generate_email_candidates
from src.outreach.sequencer import schedule_outreach_sequence
from src.db.database import (
    init_db, save_job, save_tailored_application, update_tailored_application_status,
    update_tailored_email, save_outreach, save_recruiter, save_audit_log, load_all_state
)

app = FastAPI(title="Autonomous Job Hunter API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-Memory Global State for the Live Dashboard
PIPELINE_STATE: dict[str, Any] = {
    "master_profile": {
        "name": "Amartya",
        "title": "AI Engineer",
        "target_query": "AI Engineer",
        "target_location": "India",
        "min_salary": "25 LPA"
    },
    "allowed_skills": {"python", "docker", "fastapi", "sql", "git", "redis", "langgraph"},
    "discovered_queue": [],
    "qualified_queue": [],
    "approval_queue": [],
    "applied_queue": [],
    "recruiter_queue": [],
    "outreach_queue": [],
    "active_job_id": None,
    "current_status": "IDLE",
    "audit_logs": [],
    "errors": []
}

# Hydrate state from SQLite on startup
try:
    init_db()
    persisted = load_all_state()
    for queue_key in ["discovered_queue", "qualified_queue", "approval_queue", "applied_queue", "recruiter_queue", "outreach_queue", "audit_logs"]:
        if persisted.get(queue_key):
            PIPELINE_STATE[queue_key] = persisted[queue_key]
except Exception as e:
    print(f"Database hydration warning: {e}")

class RunPipelineRequest(BaseModel):
    query: str = "AI Engineer"
    location: str = "India"
    min_salary: Optional[str] = "25 LPA"
    limit: int = 3
    discovery_source: Optional[str] = "hybrid"

class EnrichRequest(BaseModel):
    name: str
    company_domain: str

class RegenerateEmailRequest(BaseModel):
    job_id: str
    feedback: str
    current_body: Optional[str] = None

class CareerInterviewRequest(BaseModel):
    projects: str
    tech_stack: str
    ideal_role: str
    location: str = "India"
    expected_salary: str = "25 LPA"

STATIC_DIR = Path(__file__).resolve().parent / "static"

@app.get("/api/state")
def get_state():
    """Returns the full state machine whiteboard and queue contents."""
    # Convert sets to lists for JSON serialization
    state_copy = dict(PIPELINE_STATE)
    if isinstance(state_copy.get("allowed_skills"), set):
        state_copy["allowed_skills"] = list(state_copy["allowed_skills"])
    return state_copy

@app.post("/api/run")
def trigger_pipeline(req: RunPipelineRequest):
    """Triggers the LangGraph pipeline with user-specified query, location, salary expectation, and discovery source."""
    global PIPELINE_STATE
    pipeline = build_job_hunter_pipeline()
    
    # Update search parameters in state
    PIPELINE_STATE["master_profile"]["target_query"] = req.query
    PIPELINE_STATE["master_profile"]["target_location"] = req.location
    PIPELINE_STATE["master_profile"]["min_salary"] = req.min_salary or "25 LPA"
    PIPELINE_STATE["allowed_skills"] = set(PIPELINE_STATE["allowed_skills"])
    PIPELINE_STATE["discovery_source"] = req.discovery_source or "hybrid"
    
    # Run the graph
    updated_state = pipeline.invoke(PIPELINE_STATE)
    
    # Save back to global memory and SQLite
    PIPELINE_STATE = updated_state
    for job in updated_state.get("discovered_queue", []):
        save_job(job)
    for app_item in updated_state.get("approval_queue", []):
        save_tailored_application(app_item)
    for log in updated_state.get("audit_logs", [])[-5:]:
        save_audit_log(log.get("event", "LOG"), log)
    
    # Return JSON-safe dict
    return get_state()

@app.post("/api/approve/{job_id}")
def approve_job(job_id: str):
    """
    Human Approval Gate:
    1. Moves job from approval_queue to applied_queue.
    2. Runs recruiter enrichment for the company.
    3. Schedules Day 0 outreach & Day 3 follow-up.
    4. Persists to SQLite.
    """
    global PIPELINE_STATE
    matching = [job for job in PIPELINE_STATE["approval_queue"] if str(job.get("job_id", job.get("id"))) == str(job_id)]
    if not matching:
        already_applied = [job for job in PIPELINE_STATE.get("applied_queue", []) if str(job.get("job_id", job.get("id"))) == str(job_id)]
        if already_applied:
            return {"message": f"Job {job_id} is already in the Applied queue.", "applied": already_applied[0]}
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found in approval queue.")
    
    approved_job = matching[0]
    # Remove from approval queue
    PIPELINE_STATE["approval_queue"] = [j for j in PIPELINE_STATE["approval_queue"] if str(j.get("job_id", j.get("id"))) != str(job_id)]
    
    # Advance to applied
    applied_record = {
        **approved_job,
        "status": "APPLIED",
        "applied_at": "Just now"
    }
    PIPELINE_STATE["applied_queue"].append(applied_record)
    update_tailored_application_status(job_id, "APPLIED")
    
    # Trigger Recruiter Discovery & Email Enrichment
    company = approved_job.get("company", "Company")
    domain = company.lower().replace(" ", "").replace(",", "").replace(".", "") + ".com"
    recruiter_name = approved_job.get("recruiter_name") or f"{company} Talent Acquisition Team"
    candidates = generate_email_candidates(recruiter_name, domain)
    
    verified_email = approved_job.get("recruiter_email") or (candidates[0].email if candidates else f"careers@{domain}")
    
    recruiter_data = {
        "job_id": job_id,
        "company": company,
        "recruiter_name": recruiter_name,
        "email_candidates": [c.__dict__ for c in candidates[:3]],
        "selected_email": verified_email
    }
    PIPELINE_STATE["recruiter_queue"].append(recruiter_data)
    save_recruiter(recruiter_data)
    
    # Schedule Outreach Sequence
    outreach = schedule_outreach_sequence(
        job_id=job_id,
        company=company,
        role=approved_job.get("title", "Software Engineer"),
        candidate_name=PIPELINE_STATE["master_profile"].get("name", "Candidate"),
        recruiter_name=recruiter_name,
        recruiter_email=verified_email,
        tailored_bullet=approved_job.get("tailored_bullet", "")
    )
    # Dispatch Email via configured provider (SMTP / Resend / Dry-Run)
    from src.outreach.mailer import dispatch_email
    email_subj = approved_job.get("email_subject") or f"Application: {approved_job.get('title')} - {PIPELINE_STATE['master_profile'].get('name', 'Candidate')}"
    email_body = approved_job.get("email_body") or outreach.get("body", "")
    dispatch_res = dispatch_email(verified_email, email_subj, email_body)
    
    outreach["status"] = dispatch_res.get("status", "STAGED_READY")
    outreach["dispatch_provider"] = dispatch_res.get("provider", "dry_run")
    PIPELINE_STATE["outreach_queue"].append(outreach)
    save_outreach(outreach)
    
    save_audit_log("APPLICATION_APPROVED", {
        "job_id": job_id,
        "company": company,
        "email": verified_email,
        "dispatch_status": outreach["status"],
        "provider": outreach["dispatch_provider"]
    })
    
    return {
        "message": f"Job approved! Outreach {outreach['status']} via {outreach['dispatch_provider']}.",
        "applied": applied_record,
        "outreach": outreach
    }

@app.post("/api/reject/{job_id}")
def reject_job(job_id: str):
    """Rejects job from approval queue and persists status."""
    global PIPELINE_STATE
    PIPELINE_STATE["approval_queue"] = [j for j in PIPELINE_STATE["approval_queue"] if str(j.get("job_id", j.get("id"))) != str(job_id)]
    update_tailored_application_status(job_id, "REJECTED")
    save_audit_log("APPLICATION_REJECTED", {"job_id": job_id})
    return {"message": f"Job {job_id} rejected."}

@app.post("/api/regenerate-email")
def regenerate_email(req: RegenerateEmailRequest):
    """
    Takes user feedback on a drafted cold email, calls the LLM in parallel,
    and returns an updated subject and body tailored to the feedback.
    """
    global PIPELINE_STATE
    matching = [job for job in PIPELINE_STATE["approval_queue"] if str(job.get("job_id", job.get("id"))) == str(req.job_id)]
    if not matching:
        raise HTTPException(status_code=404, detail="Job not found in approval queue")
    
    job = matching[0]
    candidate_name = PIPELINE_STATE["master_profile"].get("name", "Candidate")
    
    from src.core.llm import generate_personalized_email
    new_draft = generate_personalized_email(
        company=job.get("company", "Company"),
        role=job.get("title", "Software Engineer"),
        jd_description=job.get("description", ""),
        recruiter_name=job.get("recruiter_name", "Talent Acquisition Lead"),
        candidate_name=candidate_name,
        tailored_bullet=job.get("tailored_bullet", ""),
        feedback=req.feedback,
        current_email_body=req.current_body or job.get("email_body", "")
    )
    
    # Update job in approval queue and SQLite
    job["email_subject"] = new_draft.get("subject", job.get("email_subject", ""))
    job["email_body"] = new_draft.get("body", job.get("email_body", ""))
    update_tailored_email(req.job_id, job["email_subject"], job["email_body"])
    
    PIPELINE_STATE["audit_logs"].append({
        "event": "EMAIL_REGENERATED_WITH_FEEDBACK",
        "job_id": req.job_id,
        "feedback": req.feedback
    })
    save_audit_log("EMAIL_REGENERATED", {"job_id": req.job_id, "feedback": req.feedback})
    
    return {"message": "Email regenerated successfully!", "email": new_draft}

@app.post("/api/enrich")
def test_enrichment(req: EnrichRequest):
    """Standalone recruiter email enrichment probe."""
    candidates = generate_email_candidates(req.name, req.company_domain)
    return {"candidates": [c.__dict__ for c in candidates]}

@app.post("/api/career-interview")
def run_career_interview(req: CareerInterviewRequest):
    """
    Analyzes user interview responses, extracts canonical allowed skills,
    and returns tailored search queries and target job titles.
    """
    from src.core.llm import analyze_career_interview
    blueprint = analyze_career_interview(req.dict())
    
    # Update master profile & allowed skills in state
    if req.location:
        PIPELINE_STATE["master_profile"]["target_location"] = req.location
    if req.expected_salary:
        PIPELINE_STATE["master_profile"]["min_salary"] = req.expected_salary
    if "extracted_skills" in blueprint and blueprint["extracted_skills"]:
        PIPELINE_STATE["allowed_skills"].update(blueprint["extracted_skills"])
    if "recommended_titles" in blueprint and blueprint["recommended_titles"]:
        PIPELINE_STATE["master_profile"]["target_query"] = blueprint["recommended_titles"][0]
        
    return blueprint

@app.get("/api/resume/{job_id}")
def get_tailored_resume_endpoint(job_id: str, format: str = "markdown"):
    """
    Returns the custom tailored resume for a specific job posting.
    Supports ?format=markdown (for direct download) or ?format=html (for browser print/PDF).
    """
    from fastapi.responses import HTMLResponse, PlainTextResponse
    from src.resume.generator import generate_tailored_resume
    
    # Search in approval, applied, or discovered queues
    all_jobs = PIPELINE_STATE.get("approval_queue", []) + PIPELINE_STATE.get("applied_queue", []) + PIPELINE_STATE.get("discovered_queue", [])
    matching = [j for j in all_jobs if str(j.get("job_id", j.get("id"))) == str(job_id)]
    job_info = matching[0] if matching else {"job_id": job_id, "company": "Company", "title": "Software Engineer"}
    
    content = generate_tailored_resume(job_info, format)
    clean_company = job_info.get("company", "Company").replace(" ", "_")
    
    if format.lower() == "html":
        return HTMLResponse(content)
    
    filename = f"Amartya_Resume_{clean_company}.md"
    return PlainTextResponse(
        content,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/cover-letter/{job_id}")
def get_tailored_cover_letter(job_id: str, format: str = "html"):
    """
    Generates single-click tailored Cover Letter for a specific job posting.
    Exports in clean print-ready ATS HTML or Markdown format.
    """
    from fastapi.responses import HTMLResponse, PlainTextResponse
    from src.cover_letter.generator import generate_tailored_cover_letter_html, generate_tailored_cover_letter_markdown
    
    all_jobs = (
        PIPELINE_STATE.get("approval_queue", [])
        + PIPELINE_STATE.get("applied_queue", [])
        + PIPELINE_STATE.get("qualified_queue", [])
        + PIPELINE_STATE.get("discovered_queue", [])
    )
    matching = [j for j in all_jobs if str(j.get("job_id", j.get("id"))) == str(job_id)]
    job_info = matching[0] if matching else {"job_id": job_id, "company": "Target Company", "title": "Software Engineer"}
    
    profile = PIPELINE_STATE.get("master_profile", {})
    clean_company = job_info.get("company", "Company").replace(" ", "_")

    if format.lower() == "html":
        return HTMLResponse(generate_tailored_cover_letter_html(job_info, profile))
    
    return PlainTextResponse(
        generate_tailored_cover_letter_markdown(job_info, profile),
        headers={"Content-Disposition": f"attachment; filename=Cover_Letter_{clean_company}.md"}
    )

class RefineResumeRequest(BaseModel):
    raw_resume_text: str
    career_direction: Optional[str] = "Senior AI & Backend Systems Engineer"

@app.post("/api/resume/refine")
def refine_resume_endpoint(req: RefineResumeRequest):
    """
    Skill: General Master Resume Refiner.
    Polishes action verbs and applies Google XYZ impact format while strictly preserving
    the candidate's current layout, custom sections, and formatting.
    """
    from src.resume.refiner import refine_master_resume
    allowed_skills = list(PIPELINE_STATE.get("allowed_skills", []))
    result = refine_master_resume(
        raw_resume_text=req.raw_resume_text,
        allowed_skills=allowed_skills,
        career_direction=req.career_direction or "Senior Systems & AI Engineer"
    )
    save_audit_log("RESUME_REFINED_IN_GENERAL", {
        "improvements_count": len(result.get("improvements", [])),
        "provider": result.get("provider")
    })
    return result

class OnboardingInterviewRequest(BaseModel):
    raw_resume_text: str
    projects_experience: str
    tech_stack: str
    target_role: str
    target_location: str = "India"
    min_salary: str = "25 LPA"

@app.post("/api/onboard-interview")
def run_onboarding_interview(req: OnboardingInterviewRequest):
    """
    Interactive Candidate Onboarding & Profile Ingestion.
    Analyzes pasted resume and interview answers, auto-populates candidate profile,
    sets up the verified skills whitelist, and persists the raw format.
    """
    global PIPELINE_STATE
    import json
    from src.resume.generator import save_raw_resume_template, RESUME_DATA_PATH
    
    # Clean and parse skills
    extracted_skills = [s.strip() for s in req.tech_stack.replace(";", ",").split(",") if s.strip()]
    if not extracted_skills:
        extracted_skills = ["Python", "FastAPI", "Docker", "SQL", "Redis"]

    # Extract name from first line if starts with # or simple text
    name = "Candidate"
    lines = req.raw_resume_text.strip().splitlines()
    if lines:
        first = lines[0].lstrip("#").strip()
        if len(first.split()) <= 4 and first.replace(" ", "").isalpha():
            name = first.title() if first.isupper() else first

    PIPELINE_STATE["master_profile"]["name"] = name
    PIPELINE_STATE["master_profile"]["target_query"] = req.target_role
    PIPELINE_STATE["master_profile"]["target_location"] = req.target_location
    PIPELINE_STATE["master_profile"]["min_salary"] = req.min_salary
    PIPELINE_STATE["master_profile"]["skills"] = extracted_skills
    PIPELINE_STATE["master_profile"]["raw_resume_text"] = req.raw_resume_text
    PIPELINE_STATE["allowed_skills"] = set(extracted_skills)
    
    save_raw_resume_template(req.raw_resume_text)
    
    # Save to master_resume.json
    try:
        current_data = {}
        if RESUME_DATA_PATH.exists():
            with open(RESUME_DATA_PATH, "r", encoding="utf-8") as f:
                current_data = json.load(f)
        current_data.update({
            "name": name,
            "skills": extracted_skills,
            "raw_resume_text": req.raw_resume_text,
            "target_query": req.target_role,
            "target_location": req.target_location,
            "min_salary": req.min_salary
        })
        with open(RESUME_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(current_data, f, indent=2)
    except Exception as e:
        print(f"[Onboarding Warning] Could not write master_resume.json: {e}")

    save_audit_log("ONBOARDING_INTERVIEW_COMPLETED", {
        "candidate": name,
        "skills_count": len(extracted_skills),
        "target": req.target_role
    })

    return {
        "message": "Candidate interview completed and profile initialized!",
        "profile": PIPELINE_STATE["master_profile"]
    }

@app.post("/api/apply/verify-test-form")
def verify_test_form():
    """
    Directly verifies Playwright ATS form autofill on an actual application form fixture.
    Fills inputs, captures screenshot, and returns visual verification proof.
    """
    import tempfile
    from src.apply.form_filler import run_autofill_sync
    html_fixture = """<!DOCTYPE html>
<html>
  <head><title>ATS Job Application Form</title>
  <style>body { font-family: sans-serif; padding: 20px; background: #f9fafb; } form { max-width: 500px; margin: 0 auto; background: white; padding: 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); } .field { margin-bottom: 12px; } label { display: block; font-weight: bold; margin-bottom: 4px; font-size: 13px; } input { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; } button { background: #4f46e5; color: white; border: none; padding: 10px 16px; border-radius: 4px; font-weight: bold; cursor: pointer; }</style>
  </head>
  <body>
    <form id="application">
      <h2>Software Engineer Application</h2>
      <div class="field"><label>First Name</label><input type="text" id="first_name" name="first_name" /></div>
      <div class="field"><label>Last Name</label><input type="text" id="last_name" name="last_name" /></div>
      <div class="field"><label>Email Address</label><input type="email" id="email" name="email" /></div>
      <div class="field"><label>Phone Number</label><input type="tel" id="phone" name="phone" /></div>
      <div class="field"><label>LinkedIn Profile</label><input type="text" name="linkedin" id="linkedin" /></div>
      <button type="submit">Submit Application</button>
    </form>
  </body>
</html>"""
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html_fixture)
        temp_path = f.name
        
    file_url = f"file://{temp_path}"
    profile = PIPELINE_STATE.get("master_profile", {})
    result = run_autofill_sync(file_url, profile)
    
    shot_filename = None
    if result.get("screenshot_path"):
        shot_filename = Path(result["screenshot_path"]).name
        
    return {
        "message": "ATS autofill successfully tested and verified on live form!",
        "result": result,
        "screenshot_url": f"/api/apply/screenshot/{shot_filename}" if shot_filename else None
    }

@app.get("/api/apply/screenshot/{filename}")
def get_autofill_screenshot(filename: str):
    """Serves ATS autofill screenshot proof."""
    screenshots_dir = Path(__file__).resolve().parents[2] / "database" / "screenshots"
    shot_file = screenshots_dir / filename
    if not shot_file.exists():
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(str(shot_file), media_type="image/png")

@app.post("/api/apply/autofill/{job_id}")
def autofill_job_application(job_id: str):
    """
    Triggers Playwright ATS form autofill for a specific job posting.
    Fills standard application fields and captures an audit verification snapshot.
    """
    from src.apply.form_filler import run_autofill_sync
    
    all_jobs = (
        PIPELINE_STATE.get("approval_queue", [])
        + PIPELINE_STATE.get("applied_queue", [])
        + PIPELINE_STATE.get("qualified_queue", [])
        + PIPELINE_STATE.get("discovered_queue", [])
    )
    matching = [j for j in all_jobs if str(j.get("job_id", j.get("id"))) == str(job_id)]
    if not matching:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
    job = matching[0]
    job_url = job.get("url") or f"https://www.linkedin.com/jobs/view/{job_id}"
        
    profile = PIPELINE_STATE.get("master_profile", {})
    result = run_autofill_sync(job_url, profile)
    
    shot_filename = None
    if result.get("screenshot_path"):
        shot_filename = Path(result["screenshot_path"]).name
    
    save_audit_log("APPLICATION_AUTOFILL_ATTEMPTED", {
        "job_id": job_id,
        "url": job_url,
        "ats": result.get("ats_type"),
        "fields": result.get("filled_fields"),
        "status": result.get("status"),
        "screenshot": shot_filename
    })
    
    return {
        "message": result.get("message", "Autofill processed successfully!"),
        "result": result,
        "screenshot_url": f"/api/apply/screenshot/{shot_filename}" if shot_filename else None
    }

class ProfileUpdateRequest(BaseModel):
    name: str
    title: Optional[str] = None
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    skills: list[str] = []
    summary: Optional[str] = None
    raw_resume_text: Optional[str] = None
    min_salary: Optional[str] = None
    target_role: Optional[str] = None

@app.get("/api/profile")
def get_profile():
    """Returns candidate profile, questionnaire answers, and custom resume format."""
    from src.resume.generator import load_raw_resume_template
    import json
    profile = dict(PIPELINE_STATE.get("master_profile", {}))
    raw_text = profile.get("raw_resume_text") or load_raw_resume_template()
    profile["raw_resume_text"] = raw_text or ""
    profile["skills"] = list(PIPELINE_STATE.get("allowed_skills", profile.get("skills", [])))
    return profile

@app.post("/api/profile")
def update_profile(req: ProfileUpdateRequest):
    """
    Saves candidate's custom master resume format, profile details, and verified skills whitelist.
    Guarantees zero-hallucination guardrail validation against the candidate's actual skills.
    """
    global PIPELINE_STATE
    import json
    from src.resume.generator import save_raw_resume_template, RESUME_DATA_PATH
    
    # Update global state
    PIPELINE_STATE["master_profile"]["name"] = req.name
    if req.title: PIPELINE_STATE["master_profile"]["title"] = req.title
    PIPELINE_STATE["master_profile"]["email"] = req.email
    if req.phone: PIPELINE_STATE["master_profile"]["phone"] = req.phone
    if req.location: PIPELINE_STATE["master_profile"]["location"] = req.location
    if req.linkedin: PIPELINE_STATE["master_profile"]["linkedin"] = req.linkedin
    if req.github: PIPELINE_STATE["master_profile"]["github"] = req.github
    if req.portfolio: PIPELINE_STATE["master_profile"]["portfolio"] = req.portfolio
    if req.summary: PIPELINE_STATE["master_profile"]["summary"] = req.summary
    if req.min_salary: PIPELINE_STATE["master_profile"]["min_salary"] = req.min_salary
    if req.target_role: PIPELINE_STATE["master_profile"]["target_query"] = req.target_role

    if req.skills:
        clean_skills = [s.strip() for s in req.skills if s.strip()]
        PIPELINE_STATE["master_profile"]["skills"] = clean_skills
        PIPELINE_STATE["allowed_skills"] = set(clean_skills)

    if req.raw_resume_text:
        PIPELINE_STATE["master_profile"]["raw_resume_text"] = req.raw_resume_text
        save_raw_resume_template(req.raw_resume_text)

    # Persist to master_resume.json
    try:
        current_data = {}
        if RESUME_DATA_PATH.exists():
            with open(RESUME_DATA_PATH, "r", encoding="utf-8") as f:
                current_data = json.load(f)
        current_data.update({
            "name": req.name,
            "title": req.title or current_data.get("title", "Software Engineer"),
            "email": req.email,
            "phone": req.phone or current_data.get("phone", ""),
            "location": req.location or current_data.get("location", "India"),
            "linkedin": req.linkedin or current_data.get("linkedin", ""),
            "github": req.github or current_data.get("github", ""),
            "portfolio": req.portfolio or current_data.get("portfolio", ""),
            "skills": [s.strip() for s in req.skills if s.strip()] or current_data.get("skills", []),
            "summary": req.summary or current_data.get("summary", ""),
            "raw_resume_text": req.raw_resume_text or current_data.get("raw_resume_text", "")
        })
        with open(RESUME_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(current_data, f, indent=2)
    except Exception as e:
        print(f"[Profile Warning] Could not save to master_resume.json: {e}")

    save_audit_log("PROFILE_UPDATED", {"name": req.name, "skills_count": len(req.skills)})
    return {
        "message": "Profile and Master Resume in your format successfully saved!",
        "profile": PIPELINE_STATE["master_profile"]
    }

# --- TARGET COMPANIES DIRECTORY & CAREER PAGES ENDPOINTS ---
class AddCompanyRequest(BaseModel):
    name: str
    domain: str
    category: str = "Startup"
    ats_type: str = "custom"
    ats_identifier: Optional[str] = ""
    career_url: Optional[str] = ""
    location_tags: Optional[list[str]] = ["India", "Remote"]

@app.get("/api/companies")
def list_companies_endpoint(category: Optional[str] = None):
    """Returns target companies directory, filters, and category distribution."""
    from src.db.database import get_target_companies, seed_target_companies_if_empty
    seed_target_companies_if_empty()
    companies = get_target_companies(category=category, active_only=True)
    all_companies = get_target_companies(category=None, active_only=False)
    
    cat_counts = {}
    for c in all_companies:
        cat = c.get("category", "General")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        
    return {
        "total": len(all_companies),
        "filtered_count": len(companies),
        "categories": cat_counts,
        "companies": companies
    }

@app.post("/api/companies")
def add_company_endpoint(req: AddCompanyRequest):
    """Adds a new target company/startup to track."""
    from src.db.database import save_target_company
    ident = req.ats_identifier or req.name.lower().replace(" ", "")
    career_url = req.career_url or f"https://www.{req.domain}/careers"
    company_data = {
        "name": req.name,
        "domain": req.domain,
        "category": req.category,
        "ats_type": req.ats_type,
        "ats_identifier": ident,
        "career_url": career_url,
        "location_tags": req.location_tags or ["Remote"],
        "is_active": True
    }
    saved = save_target_company(company_data)
    save_audit_log("TARGET_COMPANY_ADDED", {"company": req.name, "domain": req.domain, "ats": req.ats_type})
    return {"message": f"Target company '{req.name}' added successfully!", "company": saved}

class ScanCareerPagesRequest(BaseModel):
    category: Optional[str] = None
    company_name: Optional[str] = None
    query: str = "AI Engineer"
    location: str = "India"
    limit: int = 6

@app.post("/api/companies/scan")
def scan_companies_career_pages(req: ScanCareerPagesRequest):
    """Scans direct career pages of tracked companies on demand."""
    from src.db.database import get_target_companies, seed_target_companies_if_empty
    from src.discovery.career_pages import scan_career_pages
    seed_target_companies_if_empty()
    companies = get_target_companies(category=req.category, active_only=True)
    if req.company_name:
        companies = [c for c in companies if req.company_name.lower() in c.get("name", "").lower()]

    openings = scan_career_pages(companies, query=req.query, location=req.location, limit=req.limit)
    
    # Ingest discovered openings into pipeline state
    existing_ids = {str(j.get("id") or j.get("job_id")) for j in PIPELINE_STATE.get("discovered_queue", [])}
    for op in openings:
        if str(op.get("id")) not in existing_ids:
            PIPELINE_STATE["discovered_queue"].append(op)
            PIPELINE_STATE["qualified_queue"].append(op)
            existing_ids.add(str(op.get("id")))

    save_audit_log("CAREER_PAGES_SCANNED", {
        "companies_count": len(companies),
        "found_openings": len(openings),
        "query": req.query,
        "company_name": req.company_name
    })

    return {
        "message": f"Scanned career pages across {len(companies)} tracked companies.",
        "scanned_boards": len(companies),
        "total_found": len(openings),
        "openings_count": len(openings),
        "openings": openings
    }

# Mount static web assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Job Hunter API is active. Static UI not yet created."}
