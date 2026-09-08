# src/resume/refiner.py
"""
General Resume Refiner Engine & Skill.
Refines the candidate's master resume in general (independent of specific applications)
by applying the Google XYZ impact formula, upgrading action verbs, removing passive voice,
and optimizing ATS readability while strictly preserving the candidate's custom format and layout.
"""
import re
from typing import Any, Optional
from src.core.guardrails import validate_tech_stack
from src.resume.generator import load_master_resume

REFINE_SYSTEM_PROMPT = """You are an elite Silicon Valley executive resume coach and ATS optimization specialist.
Your mission: Refine and polish the candidate's master resume to maximize impact, executive presence, and ATS discoverability.

CRITICAL CONSTRAINTS:
1. STRICT FORMAT PRESERVATION:
   - Retain 100% of the candidate's current structure, sections, custom headers, contact details, indentation, and order.
   - Do NOT convert the resume into a generic layout. Return the exact same format (Markdown/Plain Text) with the same bullet characters (- , * , •).

2. BULLET OPTIMIZATION (Google XYZ Formula):
   - Transform passive bullets into active impact: "Accomplished [X] as measured by [Y] by doing [Z]".
   - Replace weak phrases ("Responsible for", "Helped with", "Worked on") with strong verbs ("Architected", "Engineered", "Optimized", "Spearheaded", "Streamlined").
   - Emphasize scale, latency, throughput, reliability, and business impact.

3. ZERO HALLUCINATION (TRUTH LAYER):
   - Do NOT invent fake tools, companies, degrees, or certifications.
   - You may only reference technologies present in the candidate's verified skills: {allowed_skills_str}.

Output MUST be valid JSON with this exact schema:
{
  "refined_resume": "<full refined resume text in the exact original format>",
  "improvements": [
    {
      "original": "<original bullet line>",
      "refined": "<polished bullet line>",
      "rationale": "<brief explanation of why this is stronger>"
    }
  ]
}
"""

def refine_bullet_rule_based(bullet: str, allowed_skills: set[str]) -> tuple[str, Optional[str]]:
    """Deterministic, rule-based fallback polish if LLM is unavailable."""
    weak_verbs_map = {
        r"\b(worked on|worked with)\b": "engineered",
        r"\b(responsible for building|responsible for)\b": "architected",
        r"\b(helped build|assisted with)\b": "collaborated on developing",
        r"\b(did optimization for|did testing)\b": "optimized",
        r"\b(made sure)\b": "ensured",
        r"\b(handled)\b": "orchestrated",
    }
    refined = bullet
    rationale = None
    for pattern, replacement in weak_verbs_map.items():
        if re.search(pattern, refined, re.IGNORECASE):
            refined = re.sub(pattern, replacement, refined, flags=re.IGNORECASE)
            rationale = f"Replaced passive phrasing with active action verb '{replacement}'."
            break
            
    # Capitalize first word after bullet
    return refined, rationale

def refine_master_resume(
    raw_resume_text: str,
    allowed_skills: Optional[list[str]] = None,
    career_direction: str = "Senior Systems & AI Engineer"
) -> dict[str, Any]:
    """
    Refines and polishes the candidate's master resume in general.
    Preserves exact formatting while elevating bullet impact and ATS strength.
    """
    if not raw_resume_text or not raw_resume_text.strip():
        return {
            "refined_resume": "",
            "improvements": [],
            "message": "No resume text provided to refine."
        }

    skills_set = set(allowed_skills or [])
    if not skills_set:
        profile = load_master_resume()
        skills_set = set(profile.get("skills", ["Python", "FastAPI", "Docker", "SQL"]))

    skills_str = ", ".join(sorted(skills_set))

    from src.core.llm import get_gemini_client
    import json
    client = get_gemini_client()

    if client:
        try:
            prompt = f"{REFINE_SYSTEM_PROMPT.format(allowed_skills_str=skills_str)}\n\nCandidate's Target Direction: {career_direction}\n\nORIGINAL RESUME:\n{raw_resume_text}"
            
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            
            data = json.loads(resp.text.strip())
            refined_text = data.get("refined_resume", raw_resume_text)
            improvements = data.get("improvements", [])

            # Run Truth Guardrail on all newly generated bullets
            for imp in improvements:
                ref_bullet = imp.get("refined", "")
                passed, reason = validate_tech_stack(ref_bullet, skills_set)
                if not passed:
                    # Guardrail caught hallucination - revert this bullet to original
                    refined_text = refined_text.replace(ref_bullet, imp.get("original", ref_bullet))
                    imp["rationale"] += f" (Guardrail notice: {reason})"

            return {
                "refined_resume": refined_text,
                "improvements": improvements,
                "provider": "gemini-2.5-flash",
                "message": f"Successfully refined {len(improvements)} bullet points using Google XYZ impact framework!"
            }
        except Exception as e:
            print(f"[ResumeRefiner Warning] LLM call notice: {e}")

    # Deterministic Rule-Based Fallback
    lines = raw_resume_text.splitlines()
    refined_lines = []
    improvements = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* ") or stripped.startswith("• "):
            prefix = line[:line.find(stripped[0])]
            bullet_char = stripped[0]
            bullet_body = stripped[2:].strip()
            
            new_bullet, rationale = refine_bullet_rule_based(bullet_body, skills_set)
            if rationale:
                new_line = f"{prefix}{bullet_char} {new_bullet}"
                refined_lines.append(new_line)
                improvements.append({
                    "original": line,
                    "refined": new_line,
                    "rationale": rationale
                })
            else:
                refined_lines.append(line)
        else:
            refined_lines.append(line)

    return {
        "refined_resume": "\n".join(refined_lines),
        "improvements": improvements,
        "provider": "rule_based_guardrail",
        "message": f"Refined {len(improvements)} bullet points using action-oriented impact rules."
    }
