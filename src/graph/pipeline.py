# src/graph/pipeline.py
from typing import Any
from langgraph.graph import StateGraph, START, END
from src.graph.state import JobHunterState
from src.core.guardrails import validate_tech_stack
from src.core.reflection_loop import ReflectionLoop
from src.discovery.linkedin import search_linkedin_jobs, get_linkedin_job_detail

# -----------------
# 1. NODE FUNCTIONS
# -----------------

from src.core.llm import expand_search_queries
from src.core.salary import extract_job_salary, evaluate_salary_alignment

def discovery_node(state: JobHunterState) -> dict[str, Any]:
    """Scrapes live jobs from LinkedIn with AI query expansion (e.g. AI Engineer -> GenAI, Agentic AI)."""
    base_query = state.get("master_profile", {}).get("target_query", "AI Engineer")
    location = state.get("master_profile", {}).get("target_location", "India")
    
    # 1. AI expands search query into high-intent variations
    queries_to_search = expand_search_queries(base_query)
    print(f"\n🔍 [Node: Discovery] Target Location: '{location}' | Base Query: '{base_query}'")
    print(f"   AI expanded query into: {queries_to_search}")
    
    collected_jobs = []
    seen_ids = set()
    
    # Search primary and top variation
    for q in queries_to_search[:2]:
        print(f"   Scraping listings for: '{q}' in '{location}'...")
        jobs = search_linkedin_jobs(query=q, location=location, limit=2)
        for j in jobs:
            jid = j.get("id")
            if jid and jid not in seen_ids:
                seen_ids.add(jid)
                # Ensure direct URL exists
                if not j.get("url"):
                    j["url"] = f"https://www.linkedin.com/jobs/view/{jid}"
                collected_jobs.append(j)
                
    print(f"   Total unique live jobs gathered: {len(collected_jobs)}")
    
    return {
        "discovered_queue": collected_jobs,
        "current_status": "JOBS_DISCOVERED",
        "audit_logs": [{"event": "DISCOVERY_EXPANDED_COMPLETED", "count": len(collected_jobs), "location": location, "queries": queries_to_search[:2]}]
    }

def qualification_node(state: JobHunterState) -> dict[str, Any]:
    """Calculates match score between job requirements, allowed_skills, and salary expectations."""
    expected_salary = state.get("master_profile", {}).get("min_salary", "20 LPA")
    print(f"\n⚖️ [Node: Qualification] Scoring jobs against profile and salary expectation ({expected_salary})...")
    qualified_jobs = []
    
    for job in state.get("discovered_queue", []):
        job_id = job.get("id")
        detail = get_linkedin_job_detail(job_id) if job_id else job
        description = (detail.get("description") or "").lower()
        title = detail.get("title") or ""
        job_url = detail.get("url") or job.get("url") or f"https://www.linkedin.com/jobs/view/{job_id}"
        
        # 1. Calculate skill overlap with candidate's allowed_skills
        matches = [skill for skill in state["allowed_skills"] if skill.lower() in description]
        base_score = min(100, len(matches) * 35)  # 3 matching skills = 100%
        
        # 2. Evaluate salary alignment
        salary_info = extract_job_salary(title + " " + description)
        salary_eval = evaluate_salary_alignment(salary_info, expected_salary)
        final_score = max(0, base_score - salary_eval.get("penalty", 0))
        
        job_record = {
            **detail,
            "url": job_url,
            "fit_score": final_score,
            "matched_skills": matches,
            "salary_info": salary_info,
            "salary_badge": salary_eval.get("badge", "Comp: Market Rate"),
            "salary_status": salary_eval.get("status", "COMPETITIVE_UNDISCLOSED")
        }
        qualified_jobs.append(job_record)
        print(f"   Job: '{title}' at '{job.get('company')}' -> Fit Score: {final_score}/100 | {salary_eval.get('badge')}")
        
    return {
        "qualified_queue": qualified_jobs,
        "current_status": "JOBS_QUALIFIED"
    }

from src.core.llm import generate_tailored_bullet, generate_personalized_email
from src.recruiter.email_enricher import generate_email_candidates

def tailoring_node(state: JobHunterState) -> dict[str, Any]:
    """Uses LLM + Guardrails to tailor resume bullets and draft personalized cold emails."""
    print("\n📝 [Node: Tailoring] Tailoring resume and drafting recruiter email...")
    tailored_results = []
    candidate_name = state.get("master_profile", {}).get("name", "Amartya")

    for job in state.get("qualified_queue", []):
        if job.get("fit_score", 0) >= 60:
            description = job.get("description", "")
            
            # 1. Reflection Loop with Guardrail for Resume Bullet
            def llm_bullet_gen(desc: str, critique: str | None) -> str:
                return generate_tailored_bullet(desc, state["allowed_skills"], critique)

            def guardrail_val(candidate_text: str) -> tuple[bool, str | None]:
                is_valid, violations = validate_tech_stack(candidate_text, state["allowed_skills"])
                reason = f"Forbidden technologies detected: {violations}" if not is_valid else None
                return is_valid, reason

            loop = ReflectionLoop(
                generate_fn=llm_bullet_gen,
                validate_fn=guardrail_val,
                max_retries=3,
                name="resume_bullet_tailorer"
            )

            final_bullet, success = loop.run(
                input_data=description,
                fallback_output="Engineered scalable backend microservices and REST APIs using Python, Docker, and SQL."
            )

            # 2. Discover Real Recruiter & Infer Corporate Email
            company = job.get("company", "Company")
            from src.recruiter.finder import search_public_recruiters
            real_recruiters = search_public_recruiters(company)
            recruiter_obj = real_recruiters[0] if real_recruiters else {"name": "Talent Acquisition Lead", "title": "Recruiter"}
            recruiter_name = recruiter_obj.get("name", "Talent Acquisition Lead")
            
            domain = company.lower().replace(" ", "").replace(",", "").replace(".", "") + ".com"
            candidates = generate_email_candidates(recruiter_name, domain)
            verified_email = candidates[0].email if candidates else f"careers@{domain}"

            # 3. Personalized Cold Outreach Email
            email_draft = generate_personalized_email(
                company=company,
                role=job.get("title", "Software Engineer"),
                jd_description=description,
                recruiter_name=recruiter_name,
                candidate_name=candidate_name,
                tailored_bullet=final_bullet
            )

            package = {
                "job_id": job.get("id"),
                "company": company,
                "title": job.get("title"),
                "location": job.get("location", "Remote"),
                "url": job.get("url", ""),
                "description": description[:300],
                "fit_score": job.get("fit_score", 100),
                "salary_badge": job.get("salary_badge", "Comp: Market Rate"),
                "salary_info": job.get("salary_info", {}),
                "tailored_bullet": final_bullet,
                "tailoring_success": success,
                "recruiter_name": recruiter_name,
                "recruiter_email": verified_email,
                "email_subject": email_draft.get("subject", ""),
                "email_body": email_draft.get("body", ""),
                "status": "PENDING_HUMAN_APPROVAL"
            }
            tailored_results.append(package)
            print(f"   ✓ Tailored application & email package ready for {company}!")

    return {
        "approval_queue": tailored_results,
        "current_status": "READY_FOR_APPROVAL"
    }

# -----------------
# 2. ROUTING LOGIC
# -----------------

def should_tailor_or_stop(state: JobHunterState) -> str:
    """Checks if any qualified job scored >= 60."""
    qualified = state.get("qualified_queue", [])
    has_high_match = any(job.get("fit_score", 0) >= 60 for job in qualified)
    if has_high_match:
        return "proceed_to_tailor"
    print("   ⚠️ No jobs met the >= 60 fit threshold. Halting pipeline.")
    return "stop"

# -----------------
# 3. GRAPH BUILDER
# -----------------

def build_job_hunter_pipeline():
    """Builds and compiles the full LangGraph pipeline."""
    builder = StateGraph(JobHunterState)
    
    builder.add_node("discovery", discovery_node)
    builder.add_node("qualification", qualification_node)
    builder.add_node("tailoring", tailoring_node)
    
    builder.add_edge(START, "discovery")
    builder.add_edge("discovery", "qualification")
    builder.add_conditional_edges(
        "qualification",
        should_tailor_or_stop,
        {
            "proceed_to_tailor": "tailoring",
            "stop": END
        }
    )
    builder.add_edge("tailoring", END)
    
    return builder.compile()
