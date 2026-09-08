# src/outreach/sequencer.py
"""
Recruiter Cold Outreach & Follow-up Sequencer.
Inspired by Quickly's automated email sequencing and reply tracking.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

@dataclass
class OutreachMessage:
    job_id: str
    company: str
    recipient_name: str
    recipient_email: str
    subject: str
    body: str
    scheduled_send_at: str
    status: str  # "SCHEDULED", "SENT", "FOLLOWUP_DUE", "FOLLOWUP_SENT", "REPLIED", "STOPPED"
    followup_at: Optional[str] = None
    reply_detected: bool = False

def compose_outreach_email(candidate_name: str, company: str, role: str, recruiter_name: str, tailored_bullet: str) -> tuple[str, str]:
    """Generates concise, personalized, non-generic cold email for recruiters."""
    subject = f"Application: {role} at {company} - {candidate_name}"
    body = (
        f"Hi {recruiter_name},\n\n"
        f"I recently applied for the {role} position at {company}. "
        f"I noticed the team is actively expanding its technical infrastructure, and the role's focus aligned closely with what I have been building.\n\n"
        f"Specifically, {tailored_bullet.lower().rstrip('.')}.\n\n"
        f"I wanted to reach out directly with my tailored application in case you are heading talent acquisition for this opening.\n\n"
        f"Best regards,\n"
        f"{candidate_name}"
    )
    return subject, body

def schedule_outreach_sequence(
    job_id: str,
    company: str,
    role: str,
    candidate_name: str,
    recruiter_name: str,
    recruiter_email: str,
    tailored_bullet: str
) -> dict[str, Any]:
    """
    Schedules Day 0 initial outreach and sets Day 3 follow-up deadline.
    """
    now = datetime.now(timezone.utc)
    # Strategic send time: 10:15 AM recipient time tomorrow
    send_time = now + timedelta(hours=14)
    followup_time = send_time + timedelta(days=3)
    
    subject, body = compose_outreach_email(
        candidate_name=candidate_name,
        company=company,
        role=role,
        recruiter_name=recruiter_name,
        tailored_bullet=tailored_bullet
    )
    
    outreach = OutreachMessage(
        job_id=job_id,
        company=company,
        recipient_name=recruiter_name,
        recipient_email=recruiter_email,
        subject=subject,
        body=body,
        scheduled_send_at=send_time.isoformat(),
        followup_at=followup_time.isoformat(),
        status="SCHEDULED"
    )
    return asdict(outreach)
