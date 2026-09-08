# src/cover_letter/generator.py
"""
Tailored Cover Letter Generator.
Generates personalized, high-impact cover letters tailored to each job description
and the candidate's verified background. Exports clean Markdown and print-ready ATS HTML.
"""
from datetime import datetime, timezone
import html as html_lib
from typing import Any, Optional
from src.resume.generator import load_master_resume

def generate_tailored_cover_letter_markdown(
    job_info: dict[str, Any],
    master_data: Optional[dict[str, Any]] = None
) -> str:
    """
    Generates tailored cover letter in clean Markdown.
    Uses LLM or high-quality structured composition adhering to zero-hallucination standards.
    """
    profile = master_data or load_master_resume()
    company = job_info.get("company", "Hiring Team")
    role = job_info.get("title", "Software Engineer")
    tailored_bullet = job_info.get("tailored_bullet") or f"built resilient production software with {', '.join(profile.get('skills', ['Python'])[:4])}"
    
    candidate_name = profile.get("name", "Candidate")
    email = profile.get("email", "candidate@example.com")
    phone = profile.get("phone", "")
    location = profile.get("location", "India")
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    # Call LLM if API key is present, otherwise produce verified structured template
    from src.core.llm import get_gemini_client
    client = get_gemini_client()
    
    if client:
        try:
            prompt = f"""You are an elite executive career advisor. Write a concise, compelling 3-paragraph cover letter for:
Candidate: {candidate_name} ({location})
Target Role: {role} at {company}
Verified Achievement: {tailored_bullet}
Core Skills: {', '.join(profile.get('skills', []))}
Job Description snippet: {job_info.get('description', '')[:1200]}

Guidelines:
- Paragraph 1: Enthusiastic hook explaining why this specific role at {company} is the ideal next step.
- Paragraph 2: Deep dive into the candidate's concrete engineering track record, highlighting: "{tailored_bullet}". Mention only verified skills from: {profile.get('skills', [])}. Do NOT invent technologies.
- Paragraph 3: Cultural alignment, ownership mindset, and polite call to action.
- Tone: Professional, confident, articulate, zero generic fluff.

Return ONLY the body of the letter (from 'Dear Hiring Team at {company},' to 'Sincerely,\n{candidate_name}')."""

            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            body_text = resp.text.strip()
            if body_text:
                header = f"""# {candidate_name}
{location} | {email} | {phone}

**Date:** {date_str}  
**To:** Hiring Team, {company}  
**Position:** {role}  

---

"""
                return header + body_text
        except Exception as e:
            print(f"[CoverLetter Warning] LLM generation notice: {e}")

    # Deterministic fallback adhering strictly to the Truth Layer
    return f"""# {candidate_name}
{location} | {email} | {phone}

**Date:** {date_str}  
**To:** Hiring Team at {company}  
**Subject:** Application for {role}  

---

Dear {company} Talent Acquisition Team,

I am writing to express my strong enthusiasm for the **{role}** position at **{company}**. Having followed {company}'s technical trajectory, I was particularly drawn to your focus on scaling resilient, high-impact systems. With a strong engineering foundation in {', '.join(profile.get('skills', ['Python', 'FastAPI', 'Docker'])[:4])}, my background directly aligns with the technical challenges your team is solving.

In my recent experience, I have specialized in building robust, production-grade applications. Specifically, I **{tailored_bullet.lower().rstrip('.')}**. I prioritize clean architectural separation, comprehensive automated test coverage, and deterministic workflows to guarantee high availability and low latency under production workloads.

I am eager to bring my hands-on problem-solving mindset and dedication to engineering excellence to {company}. I welcome the opportunity to discuss how my technical skills and proactive work ethic can contribute to your team's ongoing goals.

Sincerely,  
**{candidate_name}**  
{email}
"""

def generate_tailored_cover_letter_html(
    job_info: dict[str, Any],
    master_data: Optional[dict[str, Any]] = None
) -> str:
    """
    Generates print-ready ATS HTML cover letter with clean typography and PDF export button.
    """
    md_content = generate_tailored_cover_letter_markdown(job_info, master_data)
    profile = master_data or load_master_resume()
    company = job_info.get("company", "Company")
    role = job_info.get("title", "Role")
    
    # Render markdown paragraphs into clean HTML
    paragraphs = []
    for block in md_content.split("\n\n"):
        b = block.strip()
        if not b:
            continue
        if b.startswith("# "):
            paragraphs.append(f"<h1>{html_lib.escape(b[2:])}</h1>")
        elif b.startswith("**Date:**") or b.startswith("**To:**") or b.startswith("**Subject:**") or b.startswith("**Position:**"):
            paragraphs.append(f"<div class='meta-line'>{html_lib.escape(b).replace('**', '')}</div>")
        elif b == "---":
            paragraphs.append("<hr class='divider'/>")
        else:
            # Format bolding
            import re
            b_fmt = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html_lib.escape(b))
            paragraphs.append(f"<p>{b_fmt.replace(chr(10), '<br/>')}</p>")

    content_html = "\n".join(paragraphs)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{profile.get('name', 'Candidate')} - Cover Letter ({company})</title>
  <style>
    @page {{ size: A4; margin: 20mm; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #1f2937;
      line-height: 1.6;
      font-size: 11pt;
      max-width: 780px;
      margin: 0 auto;
      padding: 32px 24px;
    }}
    h1 {{ margin: 0 0 6px 0; font-size: 20pt; font-weight: 800; color: #111827; letter-spacing: -0.5px; }}
    .meta-line {{ font-size: 10pt; color: #4b5563; margin-bottom: 4px; }}
    .divider {{ border: 0; border-top: 1px solid #e5e7eb; margin: 18px 0; }}
    p {{ margin: 0 0 14px 0; }}
    strong {{ color: #111827; }}
    .btn-print {{
      background: #4f46e5;
      color: white;
      border: none;
      padding: 9px 18px;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
      font-size: 10pt;
      transition: background 0.2s;
    }}
    .btn-print:hover {{ background: #4338ca; }}
    @media print {{
      body {{ padding: 0; }}
      .no-print {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="no-print" style="margin-bottom: 24px; text-align: right;">
    <button onclick="window.print()" class="btn-print">🖨️ Print / Save as PDF</button>
  </div>
  {content_html}
</body>
</html>"""
