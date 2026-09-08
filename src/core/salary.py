# src/core/salary.py
"""
Salary and Compensation Expectation Engine.
Parses salary ranges from job descriptions / titles (INR LPA, Lakhs, USD $k, etc.)
and validates against candidate compensation expectations.
"""
import re
from typing import Optional, Any

def normalize_salary_string(salary_str: str) -> Optional[float]:
    """
    Normalizes a user expectation string into an annual benchmark value in standard units:
    e.g. '25 LPA' -> 25.0 (in Lakhs per annum)
    e.g. '20-30 LPA' -> 20.0 (minimum expectation)
    e.g. '$120k' -> 120.0 (in thousands USD)
    """
    if not salary_str:
        return None
        
    s = salary_str.lower().strip()
    
    # LPA / Lakhs pattern (e.g. "25 LPA", "20-30 LPA", "25 Lakhs")
    lpa_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:-|to)?\s*(?:\d+(?:\.\d+)?)?\s*(?:lpa|lakh|lakhs|lac|lacs|l\b)', s)
    if lpa_match:
        return float(lpa_match.group(1))
        
    # Thousands pattern (e.g. "$120k", "100-150k")
    k_match = re.search(r'\$?(\d+(?:\.\d+)?)\s*k', s)
    if k_match:
        return float(k_match.group(1))
        
    # Raw number
    num_match = re.search(r'(\d+(?:\.\d+)?)', s)
    if num_match:
        val = float(num_match.group(1))
        # If value is e.g. 2500000 -> 25 LPA
        if val > 100000:
            return val / 100000.0
        return val
        
    return None

def extract_job_salary(text: str) -> dict[str, Any]:
    """
    Extracts salary mentions from job descriptions or snippets.
    Returns structured dict with detected currency, min, max, and display string.
    """
    if not text:
        return {"detected": False, "display": "Not Disclosed", "min": None, "max": None}

    # 1. INR / LPA patterns (e.g. ₹20,00,000 - ₹35,00,000 or 20 - 35 LPA)
    inr_range = re.search(r'(?:₹|inr|rs\.?)\s*([\d,]+(?:\.\d+)?)\s*(?:-|to)\s*(?:₹|inr|rs\.?)?\s*([\d,]+(?:\.\d+)?)', text, re.IGNORECASE)
    if inr_range:
        min_val = float(inr_range.group(1).replace(",", ""))
        max_val = float(inr_range.group(2).replace(",", ""))
        min_lpa = min_val / 100000 if min_val > 1000 else min_val
        max_lpa = max_val / 100000 if max_val > 1000 else max_val
        return {
            "detected": True,
            "currency": "INR",
            "min": min_lpa,
            "max": max_lpa,
            "display": f"₹{min_lpa:.1f} - ₹{max_lpa:.1f} LPA"
        }

    lpa_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:lpa|lakh|lakhs|lac|lacs)', text, re.IGNORECASE)
    if lpa_match:
        min_l = float(lpa_match.group(1))
        max_l = float(lpa_match.group(2))
        return {
            "detected": True,
            "currency": "INR",
            "min": min_l,
            "max": max_l,
            "display": f"₹{min_l:.1f} - ₹{max_l:.1f} LPA"
        }

    single_lpa = re.search(r'(\d+(?:\.\d+)?)\s*(?:lpa|lakh|lakhs|lac|lacs)', text, re.IGNORECASE)
    if single_lpa:
        val = float(single_lpa.group(1))
        return {
            "detected": True,
            "currency": "INR",
            "min": val,
            "max": val,
            "display": f"₹{val:.1f} LPA"
        }

    # 2. USD patterns ($120,000 - $160,000 or $120k - $160k)
    usd_range = re.search(r'\$\s*([\d,]+(?:\.\d+)?)\s*(?:k|K)?\s*(?:-|to)\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(?:k|K)?', text)
    if usd_range:
        min_u = float(usd_range.group(1).replace(",", ""))
        max_u = float(usd_range.group(2).replace(",", ""))
        if min_u < 1000 and "k" in text.lower():
            min_u *= 1000
            max_u *= 1000
        return {
            "detected": True,
            "currency": "USD",
            "min": min_u,
            "max": max_u,
            "display": f"${int(min_u):,} - ${int(max_u):,}"
        }

    return {"detected": False, "display": "Not Disclosed / Competitive", "min": None, "max": None}

def evaluate_salary_alignment(job_salary_info: dict[str, Any], expected_min_str: Optional[str]) -> dict[str, Any]:
    """
    Evaluates whether the job compensation satisfies the candidate's minimum expectation.
    """
    expected_min = normalize_salary_string(expected_min_str) if expected_min_str else None
    
    # If candidate has no expectation or job didn't disclose
    if not expected_min or not job_salary_info.get("detected"):
        return {
            "meets_expectation": True,
            "status": "COMPETITIVE_UNDISCLOSED",
            "badge": "Comp: Undisclosed / Market Rate",
            "penalty": 0
        }

    job_max = job_salary_info.get("max") or job_salary_info.get("min")
    if job_max and job_max < expected_min:
        return {
            "meets_expectation": False,
            "status": "BELOW_EXPECTATION",
            "badge": f"⚠️ Below Target ({job_salary_info.get('display')})",
            "penalty": 20
        }
        
    return {
        "meets_expectation": True,
        "status": "MEETS_EXPECTATION",
        "badge": f"💰 Matches Target ({job_salary_info.get('display')})",
        "penalty": 0
    }
