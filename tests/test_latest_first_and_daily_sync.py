# tests/test_latest_first_and_daily_sync.py
"""
Unit tests for date filtering, age calculation, latest-first sorting,
and daily incremental sync.
"""
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from src.discovery.career_pages import compute_age_metadata, parse_iso_or_timestamp, scan_career_pages
from src.db.database import init_db, is_job_seen, get_seen_job_ids, save_job
from src.server.app import app

def test_parse_iso_or_timestamp():
    # 1. Test ISO string with timezone
    dt1 = parse_iso_or_timestamp("2026-08-21T21:32:54-04:00")
    assert dt1 is not None
    assert dt1.tzinfo is not None

    # 2. Test milliseconds timestamp (Lever style)
    lever_ms = 1782214185805  # ~56 years epoch or future ms
    dt2 = parse_iso_or_timestamp(lever_ms)
    assert dt2 is not None

    # 3. Test YYYY-MM-DD string
    dt3 = parse_iso_or_timestamp("2026-09-15")
    assert dt3 is not None
    assert dt3.year == 2026

def test_compute_age_metadata():
    now = datetime.now(timezone.utc)
    
    # 2 hours ago
    two_hours_ago = (now - timedelta(hours=2)).isoformat()
    meta_2h = compute_age_metadata(two_hours_ago)
    assert meta_2h["age_days"] == 0
    assert meta_2h["is_new_today"] is True
    assert "h ago" in meta_2h["posted_age_text"] or "Just now" in meta_2h["posted_age_text"]

    # 5 days ago
    five_days_ago = (now - timedelta(days=5)).isoformat()
    meta_5d = compute_age_metadata(five_days_ago)
    assert meta_5d["age_days"] == 5
    assert meta_5d["is_new_today"] is False
    assert meta_5d["posted_age_text"] == "5d ago"

def test_career_pages_max_age_and_latest_first_sorting(monkeypatch):
    now = datetime.now(timezone.utc)

    # Mock Greenhouse to return jobs with various dates
    fake_jobs = [
        {
            "id": "1",
            "title": "Old AI Engineer",
            "updated_at": (now - timedelta(days=20)).isoformat(),
            "content": "AI engineer python",
            "location": {"name": "India"}
        },
        {
            "id": "2",
            "title": "Recent AI Engineer",
            "updated_at": (now - timedelta(days=2)).isoformat(),
            "content": "AI engineer python",
            "location": {"name": "India"}
        },
        {
            "id": "3",
            "title": "Brand New AI Engineer",
            "updated_at": (now - timedelta(hours=3)).isoformat(),
            "content": "AI engineer python",
            "location": {"name": "India"}
        }
    ]

    import json
    class MockResp:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return json.dumps({"jobs": fake_jobs}).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=7: MockResp())

    companies = [{
        "name": "TestCorp",
        "ats_type": "greenhouse",
        "ats_identifier": "testcorp",
        "career_url": "https://boards.greenhouse.io/testcorp"
    }]

    # Filter by max_age_days = 7: Old job (20d) must be excluded!
    results = scan_career_pages(companies, query="AI Engineer", location="India", max_age_days=7)
    assert len(results) == 2
    titles = [r["title"] for r in results]
    assert "Old AI Engineer" not in titles
    assert "Brand New AI Engineer" in titles
    assert "Recent AI Engineer" in titles

    # Must be sorted LATEST FIRST: Brand New (3h) before Recent (2d)
    assert results[0]["title"] == "Brand New AI Engineer"
    assert results[1]["title"] == "Recent AI Engineer"
    assert results[0]["posted_timestamp"] > results[1]["posted_timestamp"]

def test_database_is_job_seen(tmp_path):
    db_file = tmp_path / "test_seen.db"
    init_db(db_file)

    assert not is_job_seen("job-101", db_path=db_file)

    save_job({
        "id": "job-101",
        "title": "AI Engineer",
        "company": "DeepTech",
        "location": "India",
        "url": "https://example.com/job/101",
        "posted_at": datetime.now(timezone.utc).isoformat()
    }, db_path=db_file)

    assert is_job_seen("job-101", db_path=db_file)
    seen_ids = get_seen_job_ids(db_path=db_file)
    assert "job-101" in seen_ids

def test_daily_sync_endpoint(monkeypatch):
    client = TestClient(app)

    # Mock pipeline invoke to test endpoint without consuming external Gemini quota
    class MockPipeline:
        def invoke(self, state):
            state = dict(state)
            state["discovered_queue"] = [{
                "id": "fresh-job-999",
                "title": "Fresh AI Engineer",
                "company": "FastAI Corp",
                "location": "India",
                "url": "https://boards.greenhouse.io/fastai/999",
                "description": "Python, Docker, FastAPI AI Engineer building scalable agents",
                "ats_type": "greenhouse",
                "source": "direct_career_page",
                "salary_badge": "Market Rate",
                "posted_at": datetime.now(timezone.utc).isoformat(),
                "posted_timestamp": datetime.now(timezone.utc).timestamp(),
                "posted_age_text": "Just now",
                "is_new_today": True
            }]
            return state

    monkeypatch.setattr("src.server.app.build_job_hunter_pipeline", lambda: MockPipeline())

    res = client.post("/api/pipeline/daily-sync", json={
        "query": "AI Engineer",
        "location": "India",
        "discovery_source": "direct",
        "max_age_days": 1
    })
    assert res.status_code == 200
    data = res.json()
    assert "Daily sync completed" in data.get("message", "")
    assert "state" in data
    disc = data["state"].get("discovered_queue", [])
    assert any(j.get("id") == "fresh-job-999" for j in disc)


