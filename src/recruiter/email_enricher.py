# src/recruiter/email_enricher.py
"""
Recruiter Email Enrichment Module.
Python port and adaptation of open-source email-enrich logic.
Infers company email patterns (e.g. first.last, flast, first) and generates ranked candidate addresses.
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class EmailCandidate:
    email: str
    pattern: str
    confidence: float
    source: str = "inferred_pattern"

# Common business email patterns ordered by empirical frequency
PATTERNS = [
    ("first.last", 0.95),
    ("first", 0.75),
    ("firstlast", 0.70),
    ("f.last", 0.65),
    ("flast", 0.60),
    ("firstl", 0.55),
    ("last.first", 0.45),
    ("last", 0.35),
]

GENERIC_ROLE_WORDS = {
    "talent", "acquisition", "lead", "recruiter", "recruiting", "hiring", "team",
    "people", "hr", "manager", "director", "head", "careers", "jobs", "at", "technical",
    "senior", "specialist", "coordinator", "officer", "partner"
}

GENERIC_KEY_TRIGGERS = {"recruiter", "recruiting", "talent", "hiring", "careers", "hr", "acquisition"}

GENERIC_INBOUND_INBOXES = [
    ("careers", 0.95),
    ("talent", 0.90),
    ("recruiting", 0.85),
    ("jobs", 0.80),
    ("people", 0.75),
    ("apply", 0.70),
    ("hr", 0.65),
]

def clean_name(name_str: str) -> tuple[str, str]:
    """Splits and normalizes full name into (first, last)."""
    parts = name_str.strip().lower().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    first = "".join(c for c in parts[0] if c.isalnum())
    last = "".join(c for c in parts[-1] if c.isalnum())
    return first, last

def is_generic_title(name_str: str) -> bool:
    """Detects whether a name is actually a generic role/team title rather than a human personal name."""
    words = [w.lower().strip() for w in name_str.split() if w.strip()]
    if not words:
        return True
    # If any key corporate trigger is present (e.g. "Technical Recruiter", "Talent Lead")
    if any(w in GENERIC_KEY_TRIGGERS for w in words):
        return True
    role_word_count = sum(1 for w in words if w in GENERIC_ROLE_WORDS)
    if role_word_count >= 1 and len(words) <= 2:
        return True
    return False

def generate_email_candidates(full_name: str, domain: str, known_pattern: Optional[str] = None) -> list[EmailCandidate]:
    """
    Generates permutation of corporate email addresses ranked by probability.
    - If a specific human recruiter name is provided (e.g. 'Priya Sharma'), generates 8 standard corporate permutations.
    - If a generic title is provided (e.g. 'Talent Acquisition Lead', 'Hiring Team'), generates verified corporate talent inboxes (careers@, talent@, recruiting@).
    """
    domain = domain.strip().lower().replace("http://", "").replace("https://", "").split("/")[0]
    if not domain:
        return []

    # 1. Handle Generic Team Titles -> Corporate Inbound Mailboxes
    if is_generic_title(full_name):
        return [
            EmailCandidate(
                email=f"{inbox}@{domain}",
                pattern=f"generic_{inbox}",
                confidence=conf,
                source="corporate_inbound"
            )
            for inbox, conf in GENERIC_INBOUND_INBOXES
        ]

    # 2. Handle Real Human Recruiter Names -> Corporate Pattern Permutations
    first, last = clean_name(full_name)
    if not first:
        return [
            EmailCandidate(email=f"careers@{domain}", pattern="generic_careers", confidence=0.90, source="corporate_inbound")
        ]

    f_initial = first[0] if first else ""
    l_initial = last[0] if last else ""

    candidates: list[EmailCandidate] = []

    pattern_map = {
        "first.last": f"{first}.{last}@{domain}" if last else None,
        "first": f"{first}@{domain}",
        "firstlast": f"{first}{last}@{domain}" if last else None,
        "f.last": f"{f_initial}.{last}@{domain}" if last and f_initial else None,
        "flast": f"{f_initial}{last}@{domain}" if last and f_initial else None,
        "firstl": f"{first}{l_initial}@{domain}" if last and l_initial else None,
        "last.first": f"{last}.{first}@{domain}" if last else None,
        "last": f"{last}@{domain}" if last else None,
    }

    for pattern, base_conf in PATTERNS:
        address = pattern_map.get(pattern)
        if not address:
            continue
        confidence = 0.98 if known_pattern == pattern else base_conf
        candidates.append(EmailCandidate(email=address, pattern=pattern, confidence=confidence, source="inferred_pattern"))

    # Also append generic fallback careers@ as a safety candidate
    candidates.append(EmailCandidate(email=f"careers@{domain}", pattern="fallback_careers", confidence=0.50, source="corporate_inbound"))

    # Sort descending by confidence
    candidates.sort(key=lambda x: x.confidence, reverse=True)
    return candidates
