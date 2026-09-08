# src/db/database.py
"""
SQLite Persistence Layer for Autonomous Job Hunter.
Stores jobs, tailored applications, recruiter contacts, outreach sequences,
audit logs, and master profile settings to survive server restarts.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DB_DIR = Path(__file__).resolve().parents[2] / "database"
DB_PATH = DB_DIR / "job_hunter.db"

def get_db_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Returns an SQLite connection with Row factory enabled."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: Path = DB_PATH) -> None:
    """Initializes all database tables if they do not exist."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        title TEXT,
        company TEXT,
        location TEXT,
        url TEXT,
        description TEXT,
        fit_score INTEGER DEFAULT 0,
        salary_info TEXT,
        salary_badge TEXT,
        status TEXT DEFAULT 'DISCOVERED',
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS tailored_applications (
        job_id TEXT PRIMARY KEY,
        company TEXT,
        title TEXT,
        location TEXT,
        url TEXT,
        description TEXT,
        fit_score INTEGER DEFAULT 0,
        salary_badge TEXT,
        tailored_bullet TEXT,
        tailoring_success INTEGER DEFAULT 1,
        recruiter_name TEXT,
        recruiter_email TEXT,
        email_subject TEXT,
        email_body TEXT,
        status TEXT DEFAULT 'PENDING_HUMAN_APPROVAL',
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS recruiter_records (
        job_id TEXT PRIMARY KEY,
        company TEXT,
        recruiter_name TEXT,
        selected_email TEXT,
        candidates_json TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS outreach_sequences (
        id TEXT PRIMARY KEY,
        job_id TEXT,
        company TEXT,
        recipient_name TEXT,
        recipient_email TEXT,
        subject TEXT,
        body TEXT,
        status TEXT DEFAULT 'SCHEDULED',
        scheduled_send_at TEXT,
        followup_at TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event TEXT,
        data_json TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS profile_settings (
        key TEXT PRIMARY KEY,
        value_json TEXT
    );
    """)
    conn.commit()
    conn.close()

def save_job(job: dict[str, Any], db_path: Path = DB_PATH) -> None:
    """Inserts or updates a discovered/qualified job."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO jobs (id, title, company, location, url, description, fit_score, salary_info, salary_badge, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(job.get("id")),
        job.get("title", ""),
        job.get("company", ""),
        job.get("location", ""),
        job.get("url", ""),
        job.get("description", ""),
        job.get("fit_score", 0),
        json.dumps(job.get("salary_info", {})),
        job.get("salary_badge", ""),
        job.get("status", "DISCOVERED"),
        job.get("created_at") or datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()

def save_tailored_application(app: dict[str, Any], db_path: Path = DB_PATH) -> None:
    """Inserts or updates a tailored application in the approval queue."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO tailored_applications (
        job_id, company, title, location, url, description, fit_score,
        salary_badge, tailored_bullet, tailoring_success, recruiter_name,
        recruiter_email, email_subject, email_body, status, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(app.get("job_id")),
        app.get("company", ""),
        app.get("title", ""),
        app.get("location", ""),
        app.get("url", ""),
        app.get("description", ""),
        app.get("fit_score", 0),
        app.get("salary_badge", ""),
        app.get("tailored_bullet", ""),
        1 if app.get("tailoring_success", True) else 0,
        app.get("recruiter_name", ""),
        app.get("recruiter_email", ""),
        app.get("email_subject", ""),
        app.get("email_body", ""),
        app.get("status", "PENDING_HUMAN_APPROVAL"),
        app.get("created_at") or datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()

def update_tailored_application_status(job_id: str, status: str, db_path: Path = DB_PATH) -> None:
    """Updates status (e.g. APPLIED, REJECTED) of a tailored application."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE tailored_applications SET status = ? WHERE job_id = ?", (status, str(job_id)))
    conn.commit()
    conn.close()

def update_tailored_email(job_id: str, subject: str, body: str, db_path: Path = DB_PATH) -> None:
    """Updates the revised email subject and body for a tailored application."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE tailored_applications SET email_subject = ?, email_body = ? WHERE job_id = ?", (subject, body, str(job_id)))
    conn.commit()
    conn.close()

def save_outreach(outreach: dict[str, Any], db_path: Path = DB_PATH) -> None:
    """Inserts or updates an outreach sequence."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO outreach_sequences (
        id, job_id, company, recipient_name, recipient_email, subject, body, status, scheduled_send_at, followup_at, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(outreach.get("id")),
        str(outreach.get("job_id", "")),
        outreach.get("company", ""),
        outreach.get("recipient_name", ""),
        outreach.get("recipient_email", ""),
        outreach.get("subject", ""),
        outreach.get("body", ""),
        outreach.get("status", "SCHEDULED"),
        outreach.get("scheduled_send_at", ""),
        outreach.get("followup_at", ""),
        datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()

def save_recruiter(recruiter: dict[str, Any], db_path: Path = DB_PATH) -> None:
    """Saves recruiter discovery record."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO recruiter_records (job_id, company, recruiter_name, selected_email, candidates_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        str(recruiter.get("job_id")),
        recruiter.get("company", ""),
        recruiter.get("recruiter_name", ""),
        recruiter.get("selected_email", ""),
        json.dumps(recruiter.get("email_candidates", [])),
        datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()

def save_audit_log(event: str, data: dict[str, Any], db_path: Path = DB_PATH) -> None:
    """Logs system telemetry to database."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO audit_logs (event, data_json, created_at)
    VALUES (?, ?, ?)
    """, (event, json.dumps(data), datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()

def load_all_state(db_path: Path = DB_PATH) -> dict[str, Any]:
    """Loads all persisted queues from SQLite on server boot."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Discovered & Qualified jobs
    cursor.execute("SELECT * FROM jobs ORDER BY rowid DESC")
    jobs = []
    for r in cursor.fetchall():
        d = dict(r)
        d["salary_info"] = json.loads(d["salary_info"]) if d.get("salary_info") else {}
        jobs.append(d)

    # Approval Queue (PENDING_HUMAN_APPROVAL)
    cursor.execute("SELECT * FROM tailored_applications WHERE status = 'PENDING_HUMAN_APPROVAL' ORDER BY rowid DESC")
    approval_queue = [dict(r) for r in cursor.fetchall()]

    # Applied Queue (APPLIED)
    cursor.execute("SELECT * FROM tailored_applications WHERE status = 'APPLIED' ORDER BY rowid DESC")
    applied_queue = [dict(r) for r in cursor.fetchall()]

    # Recruiter records
    cursor.execute("SELECT * FROM recruiter_records ORDER BY rowid DESC")
    recruiters = []
    for r in cursor.fetchall():
        d = dict(r)
        d["email_candidates"] = json.loads(d["candidates_json"]) if d.get("candidates_json") else []
        recruiters.append(d)

    # Outreach sequences
    cursor.execute("SELECT * FROM outreach_sequences ORDER BY rowid DESC")
    outreach = [dict(r) for r in cursor.fetchall()]

    # Recent audit logs
    cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 50")
    logs = []
    for r in cursor.fetchall():
        d = dict(r)
        d["data"] = json.loads(d["data_json"]) if d.get("data_json") else {}
        logs.append({"event": d["event"], **d["data"]})
    logs.reverse()

    conn.close()

    return {
        "discovered_queue": jobs,
        "qualified_queue": [j for j in jobs if j.get("fit_score", 0) >= 60],
        "approval_queue": approval_queue,
        "applied_queue": applied_queue,
        "recruiter_queue": recruiters,
        "outreach_queue": outreach,
        "audit_logs": logs
    }
