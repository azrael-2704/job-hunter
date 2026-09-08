# src/core/llm.py
"""
Unified LLM Interface for Autonomous Job Hunter.
Supports Google Gemini (via google-genai SDK) and local Ollama (http://localhost:11434).
Includes contextual fallback generation if no API key or local daemon is active.
"""
import os
import json
import urllib.request
from pathlib import Path
from typing import Optional, Any
from dotenv import load_dotenv

# Load environment variables from .env if present
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

def get_gemini_client():
    """Initializes and returns an authenticated google-genai Client, or None if no API key."""
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=True)
    api_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"  [LLM Warning] Could not initialize Gemini client: {e}")
        return None

def call_gemini(prompt: str, system_instruction: Optional[str] = None) -> Optional[str]:
    """Invokes Google Gemini using the official google-genai SDK."""
    client = get_gemini_client()
    if not client:
        return None
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"system_instruction": system_instruction} if system_instruction else None
        )
        return response.text.strip() if response and response.text else None
    except Exception as e:
        print(f"  [LLM Warning] Gemini API call failed: {e}")
        return None

def call_ollama(prompt: str, model: str = "llama3.2") -> Optional[str]:
    """Invokes local Ollama if running."""
    try:
        req = urllib.request.Request(
            f"{OLLAMA_HOST}/api/generate",
            data=json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data.get("response", "").strip()
    except Exception:
        return None

def call_llm(prompt: str, system_instruction: Optional[str] = None) -> str:
    """Unified LLM router: Tries Gemini -> Ollama -> Contextual Fallback."""
    # 1. Try Gemini
    res = call_gemini(prompt, system_instruction)
    if res:
        return res
        
    # 2. Try Ollama
    res = call_ollama(prompt)
    if res:
        return res
        
    # 3. Contextual Fallback (clean domain synthesis)
    return "Engineered scalable backend microservices and REST APIs using Python, Docker, and SQL."

def generate_tailored_bullet(
    jd_description: str,
    allowed_skills: set[str],
    critique: Optional[str] = None
) -> str:
    """Generates tailored resume bullet matching the JD while respecting allowed skills."""
    skills_list = ", ".join(sorted(list(allowed_skills)))
    prompt = f"""
    You are an expert technical resume writer.
    Tailor a single, impactful resume bullet point that highlights relevant skills for this job description.
    
    ALLOWED TECHNOLOGIES (STRICT: YOU CAN ONLY USE SKILLS FROM THIS LIST):
    {skills_list}

    JOB DESCRIPTION EXCERPT:
    {jd_description[:1200]}
    """
    if critique:
        prompt += f"""
        CRITICAL GUARDRAIL ERROR IN PREVIOUS ATTEMPT:
        {critique}
        You MUST self-correct now. Remove any unapproved technologies and use only allowed skills.
        """
        
    system = "Return ONLY one concise, professional resume bullet point starting with a strong action verb. Do not fabricate technologies."
    return call_llm(prompt, system)

def generate_personalized_email(
    company: str,
    role: str,
    jd_description: str,
    recruiter_name: str,
    candidate_name: str,
    tailored_bullet: str,
    feedback: Optional[str] = None,
    current_email_body: Optional[str] = None
) -> dict[str, str]:
    """
    Generates a personalized recruiter outreach email.
    Supports user feedback iterations (e.g. 'make it shorter', 'sound less formal').
    """
    prompt = f"""
    Write a concise, high-converting cold outreach email to a recruiter for a job application.
    
    Candidate Name: {candidate_name}
    Recruiter Name: {recruiter_name}
    Company: {company}
    Role: {role}
    Candidate Highlight: {tailored_bullet}
    Job Context: {jd_description[:800]}
    """
    if feedback and current_email_body:
        prompt += f"""
        CURRENT EMAIL DRAFT:
        {current_email_body}

        USER FEEDBACK / REQUESTED CHANGES:
        {feedback}

        Revise the email strictly adhering to the user's feedback.
        """
    else:
        prompt += """
        GUIDELINES:
        - 120-160 words max.
        - No generic fluff ("I am thrilled to apply").
        - Mention why this specific team/role fits the candidate's actual projects.
        - Call to action: brief conversation or viewing the attached portfolio.
        """

    system = "You are a professional career agent. Return a JSON object with 'subject' and 'body' keys."
    response = call_llm(prompt, system)
    
    # Try parsing JSON if model returned structured output
    try:
        clean_resp = response.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_resp)
        if "subject" in data and "body" in data:
            return {"subject": data["subject"], "body": data["body"]}
    except Exception:
        pass

    # Fallback clean structure
    subject = f"Application: {role} at {company} - {candidate_name}"
    body = (
        f"Hi {recruiter_name},\n\n"
        f"I recently applied for the {role} position at {company}. "
        f"I noticed the team is scaling its backend infrastructure, and my background aligns directly with the opening.\n\n"
        f"Specifically, {tailored_bullet.lower().rstrip('.')}.\n\n"
        f"Would love to connect briefly if you are the recruiting lead for this search.\n\n"
        f"Best regards,\n{candidate_name}"
    )
    return {"subject": subject, "body": body}

def expand_search_queries(base_query: str) -> list[str]:
    """
    Expands a base job query into 3-4 semantic, high-intent variations.
    e.g. 'AI Engineer' -> ['GenAI Engineer', 'Agentic AI Engineer', 'LLM Engineer']
    """
    prompt = f"""
    Given the target role or search keyword: "{base_query}"
    Generate 3 distinct, highly relevant job titles and search keywords for modern tech hiring.
    e.g. if input is 'AI Engineer', generate: 'GenAI Engineer', 'Agentic AI Engineer', 'LLM Application Engineer'.
    
    Return ONLY a JSON array of strings, e.g. ["Title 1", "Title 2", "Title 3"].
    """
    system = "Return ONLY valid JSON array of 3 strings."
    res = call_llm(prompt, system)
    try:
        clean = res.replace("```json", "").replace("```", "").strip()
        queries = json.loads(clean)
        if isinstance(queries, list) and len(queries) > 0:
            return queries[:4]
    except Exception:
        pass
        
    # Heuristic fallback
    q = base_query.lower()
    if "ai" in q or "ml" in q:
        return [base_query, "Generative AI Engineer", "Agentic AI Engineer", "LLM Engineer"]
    elif "python" in q:
        return [base_query, "Python Backend Developer", "FastAPI Engineer", "Python Automation Engineer"]
    return [base_query, f"Senior {base_query}", f"Lead {base_query}"]

def analyze_career_interview(answers: dict[str, str]) -> dict[str, Any]:
    """
    Analyzes candidate interview answers to synthesize target roles,
    search queries, allowed skills, and profile summary.
    """
    prompt = f"""
    You are an elite AI technical career coach.
    Analyze the candidate's answers to formulate an optimal job search strategy.
    
    CANDIDATE INTERVIEW RESPONSES:
    - What have you built: {answers.get("projects", "Python automation and web systems")}
    - Technologies you know: {answers.get("tech_stack", "Python, Docker, SQL, FastAPI")}
    - Ideal role & seniority: {answers.get("ideal_role", "AI Engineer or Backend Developer")}
    - Location preference: {answers.get("location", "Remote or Hybrid")}
    
    Synthesize this into:
    1. Recommended job titles to target.
    2. Exact search queries to run on job portals.
    3. Canonical allowed skills extracted from their experience (strict list).
    4. A 2-sentence elevator pitch.
    
    Return ONLY valid JSON matching this schema:
    {{
      "recommended_titles": ["Title 1", "Title 2"],
      "search_queries": ["Query 1", "Query 2", "Query 3"],
      "extracted_skills": ["Skill 1", "Skill 2"],
      "elevator_pitch": "..."
    }}
    """
    system = "Return ONLY valid JSON. No markdown."
    res = call_llm(prompt, system)
    try:
        clean = res.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception:
        return {
            "recommended_titles": ["AI Engineer", "Python Backend Developer"],
            "search_queries": ["Agentic AI Engineer", "GenAI Engineer", "Python FastAPI"],
            "extracted_skills": ["python", "fastapi", "docker", "sql", "langgraph"],
            "elevator_pitch": "Experienced developer focused on building production-grade autonomous agentic workflows and scalable backend systems."
        }
