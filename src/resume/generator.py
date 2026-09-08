# src/resume/generator.py
"""
Tailored Resume Generator.
Merges candidate's master profile with guardrail-verified tailored bullets
specifically targeting a job posting. Exports clean ATS Markdown and HTML/PDF.
"""
import json
from pathlib import Path
from typing import Any, Optional

RESUME_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "master_resume.json"

def load_master_resume(data_path: Path = RESUME_DATA_PATH) -> dict[str, Any]:
    """Loads canonical candidate master resume data."""
    if not data_path.exists():
        return {
            "name": "Candidate",
            "title": "Software Engineer",
            "email": "candidate@example.com",
            "location": "India",
            "skills": ["Python", "FastAPI", "Docker", "SQL"],
            "experience": []
        }
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)

USER_RAW_RESUME_PATH = Path(__file__).resolve().parents[2] / "database" / "user_resume_template.md"

def load_raw_resume_template() -> Optional[str]:
    """Loads user's raw master resume format if saved."""
    if USER_RAW_RESUME_PATH.exists():
        try:
            content = USER_RAW_RESUME_PATH.read_text(encoding="utf-8").strip()
            if content:
                return content
        except Exception:
            pass
    return None

def save_raw_resume_template(raw_text: str) -> None:
    """Saves user's raw master resume format."""
    USER_RAW_RESUME_PATH.parent.mkdir(parents=True, exist_ok=True)
    USER_RAW_RESUME_PATH.write_text(raw_text, encoding="utf-8")

def tailor_raw_resume_format(raw_text: str, tailored_bullet: str, role: str, company: str) -> str:
    """
    Surgically injects the tailored bullet into the user's existing resume format
    without altering their layout, section structure, headers, or styling.
    """
    if not tailored_bullet:
        return raw_text

    # 1. If user put an explicit placeholder tag
    if "{{TAILORED_BULLET}}" in raw_text:
        return raw_text.replace("{{TAILORED_BULLET}}", f"- **{tailored_bullet}** *(Targeted: {role} @ {company})*")

    # 2. Surgically insert right at the top of the first experience bullet
    lines = raw_text.splitlines()
    injected = False
    new_lines = []

    # Look for bullet points (- , * , • )
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Find first bullet that looks like an achievement/experience item
        if not injected and (stripped.startswith("- ") or stripped.startswith("* ") or stripped.startswith("• ")):
            prefix = line[:line.find(stripped[0])]
            bullet_char = stripped[0]
            # Insert tailored bullet in the exact same indentation and bullet character
            tailored_line = f"{prefix}{bullet_char} **{tailored_bullet}** *(Targeted: {role} @ {company})*"
            new_lines.append(tailored_line)
            new_lines.append(line)
            injected = True
        else:
            new_lines.append(line)

    if not injected:
        # If no bullet was found, append as a tailored achievement section at bottom
        new_lines.append(f"\n- **{tailored_bullet}** *(Targeted: {role} @ {company})*")

    return "\n".join(new_lines)

def generate_tailored_markdown(job_info: dict[str, Any], master_data: dict[str, Any] | None = None) -> str:
    """
    Generates tailored resume.
    If the user has provided their own raw resume format, preserves their exact format and
    surgically updates only the relevant bullet!
    """
    profile = master_data or load_master_resume()
    company = job_info.get("company", "Target Company")
    role = job_info.get("title", "Target Role")
    tailored_bullet = job_info.get("tailored_bullet", "")

    # Priority 1: User's custom raw resume format
    raw_template = profile.get("raw_resume_text") or load_raw_resume_template()
    if raw_template:
        return tailor_raw_resume_format(raw_template, tailored_bullet, role, company)

    # Priority 2: Standard structured fallback
    lines = []
    lines.append(f"# {profile.get('name')}")
    lines.append(f"**{profile.get('title')}** | {profile.get('location')}")
    
    contacts = []
    if profile.get("email"): contacts.append(profile["email"])
    if profile.get("phone"): contacts.append(profile["phone"])
    if profile.get("linkedin"): contacts.append(f"[{profile['linkedin']}]({profile['linkedin']})")
    if profile.get("github"): contacts.append(f"[{profile['github']}]({profile['github']})")
    lines.append(" • ".join(contacts))
    lines.append("\n---\n")

    lines.append("## Professional Summary")
    lines.append(profile.get("summary", ""))
    lines.append("")

    lines.append("## Core Technical Competencies")
    skills_list = profile.get("skills", [])
    lines.append(", ".join(skills_list))
    lines.append("")

    lines.append("## Professional Experience")
    for idx, exp in enumerate(profile.get("experience", [])):
        lines.append(f"### {exp.get('role')} — **{exp.get('company')}**")
        lines.append(f"*{exp.get('location')} | {exp.get('period')}*")
        
        # In the primary current role, inject the tailored bullet as the top achievement!
        if idx == 0 and tailored_bullet:
            lines.append(f"- **{tailored_bullet}** *(Targeted for {role} at {company})*")
            
        for bullet in exp.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")

    lines.append("## Education")
    for edu in profile.get("education", []):
        lines.append(f"- **{edu.get('degree')}**, {edu.get('institution')} ({edu.get('year')})")

    return "\n".join(lines)

def generate_tailored_html(job_info: dict[str, Any], master_data: dict[str, Any] | None = None) -> str:
    """
    Generates single-column ATS HTML with print-ready CSS for direct PDF saving.
    Preserves user's exact format if custom raw resume is provided!
    """
    import html as html_lib
    import re

    profile = master_data or load_master_resume()
    company = job_info.get("company", "Target Company")
    role = job_info.get("title", "Target Role")
    tailored_bullet = job_info.get("tailored_bullet")

    raw_template = profile.get("raw_resume_text") or load_raw_resume_template()
    if raw_template:
        tailored_md = tailor_raw_resume_format(raw_template, tailored_bullet, role, company)
        html_lines = []
        in_list = False

        for line in tailored_md.splitlines():
            s_line = line.strip()
            if s_line.startswith("# "):
                if in_list: html_lines.append("</ul>"); in_list = False
                html_lines.append(f"<h1>{html_lib.escape(s_line[2:])}</h1>")
            elif s_line.startswith("## "):
                if in_list: html_lines.append("</ul>"); in_list = False
                html_lines.append(f"<h2>{html_lib.escape(s_line[3:])}</h2>")
            elif s_line.startswith("### "):
                if in_list: html_lines.append("</ul>"); in_list = False
                html_lines.append(f"<h3>{html_lib.escape(s_line[4:])}</h3>")
            elif s_line.startswith("- ") or s_line.startswith("* ") or s_line.startswith("• "):
                if not in_list: html_lines.append("<ul style='margin:4px 0 8px 0; padding-left:20px;'>"); in_list = True
                b_content = s_line[2:]
                b_fmt = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html_lib.escape(b_content))
                b_fmt = re.sub(r"\*(.*?)\*", r"<em>\1</em>", b_fmt)
                html_lines.append(f"<li style='margin-bottom:3px;'>{b_fmt}</li>")
            elif s_line == "---":
                if in_list: html_lines.append("</ul>"); in_list = False
                html_lines.append("<hr style='border:0; border-top:1px solid #d1d5db; margin:14px 0;'/>")
            elif not s_line:
                if in_list: html_lines.append("</ul>"); in_list = False
                html_lines.append("<div style='height:6px;'></div>")
            else:
                if in_list: html_lines.append("</ul>"); in_list = False
                p_fmt = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html_lib.escape(line))
                p_fmt = re.sub(r"\*(.*?)\*", r"<em>\1</em>", p_fmt)
                html_lines.append(f"<p style='margin:3px 0;'>{p_fmt}</p>")

        if in_list:
            html_lines.append("</ul>")

        rendered_body = "\n".join(html_lines)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{profile.get('name', 'Candidate')} - Resume ({company})</title>
  <style>
    @page {{ size: A4; margin: 16mm; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #111827; line-height: 1.45; font-size: 10pt; max-width: 820px; margin: 0 auto; padding: 24px;
    }}
    h1 {{ margin: 0 0 4px 0; font-size: 19pt; font-weight: 800; }}
    h2 {{ font-size: 11pt; text-transform: uppercase; border-bottom: 1px solid #d1d5db; padding-bottom: 2px; margin: 14px 0 6px 0; letter-spacing: 0.5px; }}
    h3 {{ font-size: 10.5pt; margin: 8px 0 2px 0; }}
    @media print {{ .no-print {{ display: none; }} }}
  </style>
</head>
<body>
  <div class="no-print" style="margin-bottom: 20px; text-align: right;">
    <button onclick="window.print()" style="background: #2563eb; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer;">
      🖨️ Print / Save as PDF
    </button>
  </div>
  {rendered_body}
</body>
</html>"""

    skills_html = "".join(f"<span class='skill-tag'>{s}</span>" for s in profile.get("skills", []))

    exp_html = ""
    for idx, exp in enumerate(profile.get("experience", [])):
        bullets = []
        if idx == 0 and tailored_bullet:
            bullets.append(f"<li><strong>{tailored_bullet}</strong> <span class='target-tag'>(Targeted: {role} @ {company})</span></li>")
        for b in exp.get("bullets", []):
            bullets.append(f"<li>{b}</li>")
        
        exp_html += f"""
        <div class="exp-block">
          <div class="exp-header">
            <div><strong>{exp.get('role')}</strong> — {exp.get('company')}</div>
            <div class="exp-meta">{exp.get('location')} | {exp.get('period')}</div>
          </div>
          <ul>{''.join(bullets)}</ul>
        </div>
        """

    edu_html = "".join(f"<li><strong>{e.get('degree')}</strong>, {e.get('institution')} ({e.get('year')})</li>" for e in profile.get("education", []))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{profile.get('name')} - Resume ({company})</title>
  <style>
    @page {{ size: A4; margin: 18mm; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #111827;
      line-height: 1.45;
      font-size: 10.5pt;
      margin: 0;
      padding: 24px;
      max-width: 820px;
      margin: 0 auto;
    }}
    h1 {{ margin: 0 0 4px 0; font-size: 20pt; font-weight: 800; letter-spacing: -0.5px; }}
    .subtitle {{ font-size: 11pt; color: #4b5563; margin-bottom: 6px; font-weight: 600; }}
    .contact-row {{ font-size: 9pt; color: #6b7280; margin-bottom: 16px; }}
    .contact-row a {{ color: #2563eb; text-decoration: none; }}
    h2 {{ font-size: 11pt; text-transform: uppercase; border-bottom: 1px solid #d1d5db; padding-bottom: 3px; margin: 16px 0 8px 0; letter-spacing: 0.5px; }}
    p {{ margin: 0 0 8px 0; }}
    .skill-tag {{ display: inline-block; background: #f3f4f6; border: 1px solid #e5e7eb; padding: 2px 7px; border-radius: 4px; font-size: 9pt; margin: 2px 4px 2px 0; }}
    .exp-block {{ margin-bottom: 12px; }}
    .exp-header {{ display: flex; justify-content: space-between; font-size: 10pt; margin-bottom: 4px; }}
    .exp-meta {{ color: #6b7280; font-size: 9pt; }}
    ul {{ margin: 4px 0 8px 0; padding-left: 20px; }}
    li {{ margin-bottom: 4px; }}
    .target-tag {{ color: #059669; font-weight: 600; font-size: 8.5pt; }}
    @media print {{
      body {{ padding: 0; }}
      .no-print {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="no-print" style="margin-bottom: 20px; text-align: right;">
    <button onclick="window.print()" style="background: #2563eb; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer;">
      🖨️ Print / Save as PDF
    </button>
  </div>
  <h1>{profile.get('name')}</h1>
  <div class="subtitle">{profile.get('title')} • {profile.get('location')}</div>
  <div class="contact-row">
    {profile.get('email')} • {profile.get('phone')} • <a href="{profile.get('linkedin')}">LinkedIn</a> • <a href="{profile.get('github')}">GitHub</a>
  </div>

  <h2>Professional Summary</h2>
  <p>{profile.get('summary')}</p>

  <h2>Core Technical Competencies</h2>
  <div>{skills_html}</div>

  <h2>Professional Experience</h2>
  {exp_html}

  <h2>Education</h2>
  <ul>{edu_html}</ul>
</body>
</html>
"""

def generate_tailored_resume(job_info: dict[str, Any], format_type: str = "markdown", master_data: Optional[dict[str, Any]] = None) -> str:
    """Dispatches generation by requested format."""
    if format_type.lower() == "html":
        return generate_tailored_html(job_info, master_data)
    return generate_tailored_markdown(job_info, master_data)
