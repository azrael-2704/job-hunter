# tests/test_companies_directory.py
import json
import tempfile
from pathlib import Path
from src.db.database import (
    init_db,
    save_target_company,
    get_target_companies,
    seed_target_companies_if_empty
)

def test_companies_directory_json_structure():
    data_path = Path(__file__).resolve().parents[1] / "src" / "data" / "companies_directory.json"
    assert data_path.exists(), "companies_directory.json must exist"
    
    with open(data_path, "r", encoding="utf-8") as f:
        comps = json.load(f)
        
    assert len(comps) >= 500, f"Expected at least 500 companies, found {len(comps)}"
    
    categories = {c.get("category") for c in comps}
    assert "AI Startup" in categories
    assert "Indian Unicorn" in categories
    assert "Tier-1 FinTech" in categories
    assert "Big Tech" in categories

    names = {c["name"].lower() for c in comps}
    assert "anthropic" in names
    assert "razorpay" in names
    assert "american express" in names
    assert "google" in names

def test_database_company_operations():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        db_path = Path(tmp.name)
        init_db(db_path)
        
        # Seed companies
        count = seed_target_companies_if_empty(db_path)
        assert count >= 500
        
        # Query AI Startups
        ai_comps = get_target_companies(category="AI Startup", db_path=db_path)
        assert len(ai_comps) > 30
        
        # Query Indian Unicorns
        indian_comps = get_target_companies(category="Indian Unicorn", db_path=db_path)
        assert len(indian_comps) > 30

        # Save custom startup
        new_startup = {
            "name": "SuperAGI",
            "domain": "superagi.com",
            "category": "AI Startup",
            "ats_type": "ashby",
            "ats_identifier": "superagi",
            "career_url": "https://jobs.ashbyhq.com/superagi",
            "location_tags": ["India", "Bengaluru", "Remote"]
        }
        saved = save_target_company(new_startup, db_path=db_path)
        assert saved["id"] is not None

        # Verify custom startup is queryable
        all_comps = get_target_companies(db_path=db_path)
        names = [c["name"] for c in all_comps]
        assert "SuperAGI" in names
