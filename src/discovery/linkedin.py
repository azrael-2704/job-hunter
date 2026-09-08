# src/discovery/linkedin.py
import json
import subprocess
from pathlib import Path
from typing import Any

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

def search_linkedin_jobs(query: str, location: str, limit: int = 3) -> list[dict[str, Any]]:
    """
    Calls the Bun LinkedIn CLI to search live jobs and returns structured dictionaries.
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
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        elif isinstance(data, list):
            return data
        return []
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
