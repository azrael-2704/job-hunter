# tests/test_resume_generator.py
from src.resume.generator import generate_tailored_markdown, generate_tailored_html, generate_tailored_resume

def test_tailored_markdown_injection():
    job = {
        "job_id": "job-101",
        "company": "Anthropic",
        "title": "Agentic AI Engineer",
        "tailored_bullet": "Engineered multi-agent state machines in LangGraph with verified truth guardrails."
    }
    sample_profile = {
        "name": "Amartya Dev",
        "raw_resume_text": (
            "# AMARTYA DEV\n"
            "Senior AI Systems Engineer | Bengaluru, India\n\n"
            "## Core Competencies\nPython, FastAPI, Docker, SQL, Redis, LangGraph\n\n"
            "## Professional Experience\n"
            "### Lead AI Engineer - Azrael Dev\n"
            "- Built autonomous multi-agent pipelines with LangGraph\n"
        )
    }
    md = generate_tailored_markdown(job, sample_profile)
    
    assert "Anthropic" in md
    assert "Agentic AI Engineer" in md
    assert "Engineered multi-agent state machines in LangGraph with verified truth guardrails" in md
    assert "Professional Experience" in md
    assert "Core Competencies" in md

def test_tailored_html_generation():
    job = {
        "job_id": "job-102",
        "company": "Scale AI",
        "title": "LLM Systems Engineer",
        "tailored_bullet": "Optimized high-throughput inference caching with Redis."
    }
    html = generate_tailored_html(job)
    
    assert "<!DOCTYPE html>" in html
    assert "Scale AI" in html
    assert "Optimized high-throughput inference caching with Redis" in html
    assert "window.print()" in html

def test_generator_dispatcher():
    job = {"company": "Google", "title": "Software Engineer"}
    sample_profile = {
        "name": "Amartya Dev",
        "raw_resume_text": (
            "# AMARTYA DEV\n"
            "Senior AI Systems Engineer | Bengaluru, India\n\n"
            "## Core Competencies\nPython, FastAPI, Docker, SQL, Redis, LangGraph\n\n"
            "## Professional Experience\n"
            "### Lead AI Engineer - Azrael Dev\n"
            "- Built autonomous multi-agent pipelines with LangGraph\n"
            "- Deployed production backend microservices in FastAPI\n"
        )
    }
    md = generate_tailored_resume(job, "markdown", sample_profile)
    html = generate_tailored_resume(job, "html", sample_profile)
    
    assert isinstance(md, str) and len(md) > 100
    assert isinstance(html, str) and "<html" in html

def test_custom_format_preservation():
    custom_raw = """# MY PERSONAL RESUME FORMAT
John Doe | Bengaluru, India
john@example.com

### SECTION: MY CUSTOM PROJECTS
- Built an autonomous robotics controller in C++
- Designed real-time event streaming pipeline

### SECTION: EDUCATION
- B.Tech in CSE
"""
    job = {
        "company": "DeepMind",
        "title": "Staff AI Researcher",
        "tailored_bullet": "Developed state-of-the-art transformer evaluation benchmarks"
    }
    master_data = {
        "name": "John Doe",
        "raw_resume_text": custom_raw
    }
    tailored = generate_tailored_markdown(job, master_data)
    assert "# MY PERSONAL RESUME FORMAT" in tailored
    assert "### SECTION: MY CUSTOM PROJECTS" in tailored
    assert "### SECTION: EDUCATION" in tailored
    assert "Developed state-of-the-art transformer evaluation benchmarks" in tailored
    assert "(Targeted: Staff AI Researcher @ DeepMind)" in tailored
