# tests/test_email_enricher.py
from src.recruiter.email_enricher import generate_email_candidates, is_generic_title

def test_real_human_recruiter_patterns():
    candidates = generate_email_candidates("Priya Sharma", "razorpay.com")
    emails = [c.email for c in candidates]
    
    assert "priya.sharma@razorpay.com" in emails
    assert "priya@razorpay.com" in emails
    assert "psharma@razorpay.com" in emails
    assert "careers@razorpay.com" in emails
    
    # Top candidate should be the highest-probability standard pattern
    assert candidates[0].email == "priya.sharma@razorpay.com"

def test_generic_team_title_routes_to_corporate_inboxes():
    # Should detect generic titles
    assert is_generic_title("Talent Acquisition Lead")
    assert is_generic_title("Hiring Lead at Acme")
    assert is_generic_title("Technical Recruiter")
    assert not is_generic_title("Sarah Jenkins")

    # Generate candidates for generic title
    candidates = generate_email_candidates("Talent Acquisition Lead", "anthropic.com")
    emails = [c.email for c in candidates]
    
    # Crucial guarantee: NEVER produce 'talent.lead@company.com'
    assert "talent.lead@anthropic.com" not in emails
    assert "talent@anthropic.com" in emails
    assert "careers@anthropic.com" in emails
    assert "recruiting@anthropic.com" in emails
