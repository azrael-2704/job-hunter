# src/discovery/linkedin.py
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from src.discovery.career_pages import compute_age_metadata

# Resolve path to the Bun LinkedIn CLI in upstream/ai-job-search
BUN_CLI_PATH = (
    Path(__file__).resolve().parents[2]
    / "upstream"
    / "ai-job-search"
    / ".agents"
    / "skills"
    / "linkedin-search"
    / "cli"
    / "src"
    / "cli.ts"
)

def search_linkedin_jobs(
    query: str,
    location: str,
    limit: int = 3,
    max_age_days: Optional[int] = 7
) -> list[dict[str, Any]]:
    """
    Calls the Bun LinkedIn CLI to search live jobs filtered by age and returns structured dictionaries
    sorted strictly LATEST FIRST.
    """
    if not BUN_CLI_PATH.exists():
        print(f"Warning: Bun CLI path not found at {BUN_CLI_PATH}")
        return []

    cmd = [
        "bun", "run", str(BUN_CLI_PATH),
        "search",
        "-q", query,
        "-l", location,
        "--limit", str(limit),
        "--format", "json"
    ]
    if max_age_days:
        cmd.extend(["--jobage", str(max_age_days)])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        raw_results = []
        if isinstance(data, dict) and "results" in data:
            raw_results = data["results"]
        elif isinstance(data, list):
            raw_results = data

        enriched = []
        for j in raw_results:
            raw_date = j.get("date") or j.get("posted_at") or j.get("created_at")
            age_meta = compute_age_metadata(raw_date)
            j["posted_at"] = age_meta["posted_at"]
            j["posted_timestamp"] = age_meta["posted_timestamp"]
            j["posted_age_text"] = age_meta["posted_age_text"]
            j["is_new_today"] = age_meta["is_new_today"]
            enriched.append(j)

        # Sort latest first
        enriched.sort(key=lambda x: x.get("posted_timestamp", 0.0), reverse=True)
        return enriched
    except subprocess.CalledProcessError as e:
        print(f"LinkedIn search failed (exit code {e.returncode}): {e.stderr}")
        return []
    except json.JSONDecodeError:
        print("Failed to parse JSON from LinkedIn scraper output.")
        return []

def get_linkedin_job_detail(job_id: str) -> dict[str, Any]:
    """
    Fetches the full description and requirements for a specific LinkedIn job ID.
    """
    if not BUN_CLI_PATH.exists():
        return {}

    cmd = [
        "bun", "run", str(BUN_CLI_PATH),
        "detail", str(job_id),
        "--format", "json"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Error fetching job detail for {job_id}: {e}")
        return {}
