# tests/test_form_filler.py
import pytest
import tempfile
from pathlib import Path
from src.apply.form_filler import detect_ats_type, autofill_ats_application

def test_detect_ats_type():
    assert detect_ats_type("https://boards.greenhouse.io/anthropic/jobs/12345") == "greenhouse"
    assert detect_ats_type("https://jobs.lever.co/scale/56789") == "lever"
    assert detect_ats_type("https://jobs.ashbyhq.com/openai/1111") == "ashby"
    assert detect_ats_type("https://example.myworkdayjobs.com/en-US/careers") == "workday"
    assert detect_ats_type("https://www.linkedin.com/jobs/view/123") == "generic"

def test_autofill_form_on_html_fixture():
    html_content = """<!DOCTYPE html>
    <html>
      <body>
        <form id="application">
          <input type="text" id="first_name" name="first_name" />
          <input type="text" id="last_name" name="last_name" />
          <input type="email" id="email" name="email" />
          <input type="tel" id="phone" name="phone" />
          <input type="text" name="linkedin" placeholder="LinkedIn Profile" />
          <button type="submit">Submit</button>
        </form>
      </body>
    </html>
    """
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html_content)
        temp_file_path = f.name

    file_url = f"file://{temp_file_path}"
    profile = {
        "name": "Amartya Dev",
        "email": "amartya.dev@gmail.com",
        "phone": "+91 98765 43210",
        "linkedin": "https://linkedin.com/in/amartya-dev"
    }

    from src.apply.form_filler import run_autofill_sync
    res = run_autofill_sync(url=file_url, profile_data=profile, headless=True)
    assert res["success"] is True
    assert "first_name" in res["filled_fields"]
    assert "last_name" in res["filled_fields"]
    assert "email" in res["filled_fields"]
    assert "phone" in res["filled_fields"]
    assert "linkedin" in res["filled_fields"]
    assert res["status"] == "STAGED_FOR_REVIEW"

    Path(temp_file_path).unlink(missing_ok=True)
