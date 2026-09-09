# tests/test_career_pages.py
from unittest.mock import patch, MagicMock
from src.discovery.career_pages import (
    clean_html,
    matches_query_and_location,
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
    fetch_ashby_jobs,
    scan_company_career_page,
    scan_career_pages
)

def test_clean_html():
    raw = "<p>Join <strong>Anthropic</strong> as an <em>AI Engineer</em>!<br>Apply now.</p>"
    cleaned = clean_html(raw)
    assert "<p>" not in cleaned
    assert "Join Anthropic as an AI Engineer! Apply now." == cleaned

def test_matches_query_and_location():
    # True matches
    assert matches_query_and_location("Senior AI Engineer", "Building LangGraph agents", "Bengaluru, India", "AI Engineer", "India")
    assert matches_query_and_location("Staff Backend Developer", "Python, FastAPI, Redis", "Remote, Worldwide", "Python Developer", "Remote")
    
    # False matches
    assert not matches_query_and_location("Marketing Lead", "Growth and SEO", "New York, US", "AI Engineer", "US")
    assert not matches_query_and_location("AI Engineer", "Deep learning models", "London, UK", "AI Engineer", "India")

def test_fetch_greenhouse_jobs_mock():
    mock_response = MagicMock()
    mock_response.read.return_value = b"""{
        "jobs": [
            {
                "id": 555,
                "title": "Senior AI Systems Engineer",
                "location": {"name": "Bengaluru, India"},
                "absolute_url": "https://boards.greenhouse.io/razorpay/jobs/555",
                "content": "<p>Build multi-agent platforms with Python and Docker.</p>"
            }
        ]
    }"""
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        jobs = fetch_greenhouse_jobs("razorpay", "Razorpay", "AI Engineer", "India")
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Senior AI Systems Engineer"
        assert jobs[0]["company"] == "Razorpay"
        assert jobs[0]["ats_type"] == "greenhouse"
        assert jobs[0]["source"] == "direct_career_page"

def test_fetch_lever_jobs_mock():
    mock_response = MagicMock()
    mock_response.read.return_value = b"""[
        {
            "id": "lev-777",
            "text": "Lead Backend Developer",
            "categories": {"location": "Bengaluru"},
            "hostedUrl": "https://jobs.lever.co/cred/lev-777",
            "description": "High throughput microservices in Python."
        }
    ]"""
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        jobs = fetch_lever_jobs("cred", "CRED", "Backend", "India")
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Lead Backend Developer"
        assert jobs[0]["company"] == "CRED"
        assert jobs[0]["ats_type"] == "lever"

def test_fetch_ashby_jobs_mock():
    mock_response = MagicMock()
    mock_response.read.return_value = b"""{
        "jobs": [
            {
                "id": "ash-888",
                "title": "Machine Learning Engineer",
                "location": "Remote",
                "jobUrl": "https://jobs.ashbyhq.com/perplexity/ash-888",
                "descriptionHtml": "<p>Search and inference optimization.</p>"
            }
        ]
    }"""
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        jobs = fetch_ashby_jobs("perplexity", "Perplexity AI", "Machine Learning", "Remote")
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Machine Learning Engineer"
        assert jobs[0]["ats_type"] == "ashby"

def test_scan_career_pages_dispatcher():
    companies = [
        {"name": "Razorpay", "ats_type": "greenhouse", "ats_identifier": "razorpay", "location_tags": ["India"]},
        {"name": "Anthropic", "ats_type": "greenhouse", "ats_identifier": "anthropic", "location_tags": ["Remote", "US"]},
        {"name": "Google", "ats_type": "custom", "ats_identifier": "google", "career_url": "https://careers.google.com"}
    ]
    results = scan_career_pages(companies, query="AI Engineer", location="India", limit=2)
    assert len(results) > 0
    assert any("direct_career_page" in r["source"] for r in results)
