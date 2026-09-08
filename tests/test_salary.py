# tests/test_salary.py
from src.core.salary import normalize_salary_string, extract_job_salary, evaluate_salary_alignment

def test_normalize_salary():
    assert normalize_salary_string("25 LPA") == 25.0
    assert normalize_salary_string("20-35 LPA") == 20.0
    assert normalize_salary_string("25 Lakhs") == 25.0
    assert normalize_salary_string("$120k") == 120.0
    assert normalize_salary_string("") is None

def test_extract_job_salary_inr():
    text = "We offer a competitive compensation package of ₹20,00,000 - ₹35,00,000 per annum with health insurance."
    salary = extract_job_salary(text)
    assert salary["detected"] is True
    assert salary["currency"] == "INR"
    assert salary["min"] == 20.0
    assert salary["max"] == 35.0

def test_extract_job_salary_usd():
    text = "Base salary is $130,000 - $160,000 with equity."
    salary = extract_job_salary(text)
    assert salary["detected"] is True
    assert salary["currency"] == "USD"
    assert salary["min"] == 130000.0

def test_salary_alignment_evaluation():
    # Scenario 1: Job matches candidate's 25 LPA requirement
    job_salary = {"detected": True, "currency": "INR", "min": 25.0, "max": 35.0, "display": "₹25.0 - ₹35.0 LPA"}
    eval_res = evaluate_salary_alignment(job_salary, "25 LPA")
    assert eval_res["meets_expectation"] is True
    assert eval_res["penalty"] == 0
    assert "Matches Target" in eval_res["badge"]

    # Scenario 2: Job is below candidate's 30 LPA requirement
    low_job = {"detected": True, "currency": "INR", "min": 15.0, "max": 20.0, "display": "₹15.0 - ₹20.0 LPA"}
    eval_low = evaluate_salary_alignment(low_job, "30 LPA")
    assert eval_low["meets_expectation"] is False
    assert eval_low["penalty"] > 0
    assert "Below Target" in eval_low["badge"]

    # Scenario 3: Salary not disclosed
    undisclosed = {"detected": False, "display": "Not Disclosed", "min": None, "max": None}
    eval_undisc = evaluate_salary_alignment(undisclosed, "25 LPA")
    assert eval_undisc["meets_expectation"] is True
    assert eval_undisc["penalty"] == 0
