# src/core/guardrails.py
import json
from pathlib import Path

TECH_DICT_PATH = Path(__file__).resolve().parent.parent / "data" / "tech_dict.json"

def load_data(PATH: Path) -> set[str]:
    if not PATH.exists():
        return set()
    with open(PATH, "r", encoding = "utf-8") as f:
        data = json.load(f)
        return {item.lower() for item in data}

tech_dict = load_data(TECH_DICT_PATH)

def validate_tech_stack(tailored_text: str, allowed_skills: set[str]) -> tuple[bool, list[str]]:
    """
    Checks if tailored_text contains technologies not in allowed_skills.
    """
    allowed_lower = {skill.lower() for skill in allowed_skills}
    words = [word.strip(",.;:()[]\"'").lower() for word in tailored_text.split()]
    violations = []
    for word in words:
        if word in tech_dict and word not in allowed_lower:
            violations.append(word)
    isValid = len(violations) == 0
    return isValid, list(set(violations))
    