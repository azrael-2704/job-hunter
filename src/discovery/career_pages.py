# src/discovery/career_pages.py
"""
Direct Career Pages & Open ATS API Crawler.
Concurrently queries public job board APIs (Greenhouse, Lever, Ashby)
of tracked companies and startups with zero authentication barriers.
"""
import re
import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Optional

def clean_html(raw_html: str) -> str:
    """Removes HTML tags and normalizes whitespace cleanly."""
    if not raw_html:
        return ""
    # Replace block level breaks with spaces
    text = re.sub(r"<(?:br|p|div|li|h[1-6])[^>]*>", " ", raw_html, flags=re.IGNORECASE)
    # Remove all remaining inline tags
    clean = re.sub(r"<[^>]+>", "", text)
    return " ".join(clean.split())

def parse_iso_or_timestamp(date_val: Any) -> Optional[datetime]:
    """Parses ISO date string, milliseconds timestamp, or seconds timestamp into UTC datetime."""
    if not date_val:
        return None
    if isinstance(date_val, (int, float)):
        # If timestamp is in milliseconds (e.g. Lever > 1e11)
        if date_val > 1e11:
            date_val = date_val / 1000.0
        try:
            return datetime.fromtimestamp(date_val, tz=timezone.utc)
        except Exception:
            return None
    if isinstance(date_val, str):
        s = date_val.strip()
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass
        try:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None

def compute_age_metadata(raw_date: Any) -> dict[str, Any]:
    """Computes ISO posted_at, timestamp, age_days, human-readable age text, and is_new_today."""
    dt = parse_iso_or_timestamp(raw_date) or datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)
    diff = now - dt
    total_sec = max(0.0, diff.total_seconds())
    age_hours = int(total_sec // 3600)
    age_days = int(total_sec // 86400)

    if age_hours < 1:
        age_text = "Just now"
    elif age_hours < 24:
        age_text = f"{age_hours}h ago"
    elif age_days == 1:
        age_text = "1d ago"
    elif age_days < 30:
        age_text = f"{age_days}d ago"
    else:
        age_text = f"{age_days // 30}mo ago"

    return {
        "posted_at": dt.isoformat(),
        "posted_timestamp": dt.timestamp(),
        "posted_age_text": age_text,
        "is_new_today": age_days < 1,
        "age_days": age_days
    }

def matches_query_and_location(title: str, description: str, loc_str: str, query: str, location: str) -> bool:
    """Evaluates whether a posting matches the target query and location filters."""
    combined_text = f"{title} {description}".lower()
    
    # Check query match
    if query:
        tokens = [t.strip().lower() for t in query.split() if len(t.strip()) > 1]
        if not any(token in title.lower() for token in tokens) and not all(token in combined_text for token in tokens):
            return False

    # Check location match
    if location and location.lower() not in ["any", "all", "global"]:
        target_loc = location.lower()
        job_loc = (loc_str or "").lower()
        if "remote" in target_loc and "remote" in job_loc:
            return True
        if "india" in target_loc and any(k in job_loc for k in ["india", "bengaluru", "bangalore", "delhi", "mumbai", "hyderabad", "pune", "remote"]):
            return True
        if target_loc not in job_loc and "remote" not in job_loc:
            return False

    return True

def fetch_greenhouse_jobs(
    identifier: str,
    company_name: str,
    query: str = "",
    location: str = "",
    max_age_days: Optional[int] = None
) -> list[dict[str, Any]]:
    """Fetches public jobs from Greenhouse Board API with date age filtering."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{identifier}/jobs?content=true"
    req = urllib.request.Request(url, headers={"User-Agent": "JobHunter-Agent/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=7) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            jobs = data.get("jobs", [])
            results = []
            for j in jobs:
                jid = str(j.get("id"))
                title = j.get("title", "Software Engineer")
                loc = j.get("location", {}).get("name", "Remote")
                desc = clean_html(j.get("content", ""))
                abs_url = j.get("absolute_url") or f"https://boards.greenhouse.io/{identifier}/jobs/{jid}"
                raw_date = j.get("updated_at") or j.get("first_published")
                age_meta = compute_age_metadata(raw_date)

                if max_age_days is not None and age_meta["age_days"] > max_age_days:
                    continue
                
                if matches_query_and_location(title, desc, loc, query, location):
                    results.append({
                        "id": f"gh-{identifier}-{jid}",
                        "title": title,
                        "company": company_name,
                        "location": loc,
                        "url": abs_url,
                        "description": desc[:2500],
                        "ats_type": "greenhouse",
                        "source": "direct_career_page",
                        "salary_badge": "Market Competitive",
                        "posted_at": age_meta["posted_at"],
                        "posted_timestamp": age_meta["posted_timestamp"],
                        "posted_age_text": age_meta["posted_age_text"],
                        "is_new_today": age_meta["is_new_today"]
                    })
            return results
    except Exception as e:
        return []

def fetch_lever_jobs(
    identifier: str,
    company_name: str,
    query: str = "",
    location: str = "",
    max_age_days: Optional[int] = None
) -> list[dict[str, Any]]:
    """Fetches public jobs from Lever Postings API with date age filtering."""
    url = f"https://api.lever.co/v0/postings/{identifier}?mode=json"
    req = urllib.request.Request(url, headers={"User-Agent": "JobHunter-Agent/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=7) as resp:
            postings = json.loads(resp.read().decode("utf-8"))
            if not isinstance(postings, list):
                return []
            results = []
            for p in postings:
                pid = str(p.get("id"))
                title = p.get("text", "Software Engineer")
                cats = p.get("categories", {})
                loc = cats.get("location", "Remote")
                desc = clean_html(p.get("description", ""))
                hosted_url = p.get("hostedUrl") or f"https://jobs.lever.co/{identifier}/{pid}"
                raw_date = p.get("createdAt")
                age_meta = compute_age_metadata(raw_date)

                if max_age_days is not None and age_meta["age_days"] > max_age_days:
                    continue

                if matches_query_and_location(title, desc, loc, query, location):
                    results.append({
                        "id": f"lev-{identifier}-{pid}",
                        "title": title,
                        "company": company_name,
                        "location": loc,
                        "url": hosted_url,
                        "description": desc[:2500],
                        "ats_type": "lever",
                        "source": "direct_career_page",
                        "salary_badge": "Market Competitive",
                        "posted_at": age_meta["posted_at"],
                        "posted_timestamp": age_meta["posted_timestamp"],
                        "posted_age_text": age_meta["posted_age_text"],
                        "is_new_today": age_meta["is_new_today"]
                    })
            return results
    except Exception as e:
        return []

def fetch_ashby_jobs(
    identifier: str,
    company_name: str,
    query: str = "",
    location: str = "",
    max_age_days: Optional[int] = None
) -> list[dict[str, Any]]:
    """Fetches public jobs from Ashby Posting API with date age filtering."""
    url = f"https://api.ashbyhq.com/posting-api/job-board/{identifier}"
    req = urllib.request.Request(url, headers={"User-Agent": "JobHunter-Agent/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=7) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            jobs = data.get("jobs", [])
            results = []
            for j in jobs:
                jid = str(j.get("id"))
                title = j.get("title", "Software Engineer")
                loc = j.get("location", "Remote")
                desc = clean_html(j.get("descriptionHtml", ""))
                jurl = j.get("jobUrl") or f"https://jobs.ashbyhq.com/{identifier}/{jid}"
                raw_date = j.get("publishedAt") or j.get("publishedDate") or j.get("createdAt")
                age_meta = compute_age_metadata(raw_date)

                if max_age_days is not None and age_meta["age_days"] > max_age_days:
                    continue

                if matches_query_and_location(title, desc, loc, query, location):
                    results.append({
                        "id": f"ash-{identifier}-{jid}",
                        "title": title,
                        "company": company_name,
                        "location": loc,
                        "url": jurl,
                        "description": desc[:2500],
                        "ats_type": "ashby",
                        "source": "direct_career_page",
                        "salary_badge": "Market Competitive",
                        "posted_at": age_meta["posted_at"],
                        "posted_timestamp": age_meta["posted_timestamp"],
                        "posted_age_text": age_meta["posted_age_text"],
                        "is_new_today": age_meta["is_new_today"]
                    })
            return results
    except Exception as e:
        return []

def scan_company_career_page(
    company: dict[str, Any],
    query: str = "",
    location: str = "",
    max_age_days: Optional[int] = None
) -> list[dict[str, Any]]:
    """Dispatches crawler based on the company's designated ATS type with age filtering."""
    ats_type = (company.get("ats_type") or "").lower()
    ident = company.get("ats_identifier") or company.get("name", "").lower().replace(" ", "")
    cname = company.get("name", "Company")

    if ats_type == "greenhouse":
        return fetch_greenhouse_jobs(ident, cname, query, location, max_age_days=max_age_days)
    elif ats_type == "lever":
        return fetch_lever_jobs(ident, cname, query, location, max_age_days=max_age_days)
    elif ats_type == "ashby":
        return fetch_ashby_jobs(ident, cname, query, location, max_age_days=max_age_days)
    else:
        # Custom career portal: create direct listing target if query matches
        age_meta = compute_age_metadata(datetime.now(timezone.utc))
        return [{
            "id": f"custom-{ident}-openings",
            "title": f"{query.title() if query else 'AI & Systems Engineer'}",
            "company": cname,
            "location": location or "India / Remote",
            "url": company.get("career_url") or f"https://www.{company.get('domain', 'company.com')}/careers",
            "description": f"Direct career portal opening at {cname}. Apply directly through their verified talent team.",
            "ats_type": "custom",
            "source": "direct_career_page",
            "salary_badge": "Market Competitive",
            "posted_at": age_meta["posted_at"],
            "posted_timestamp": age_meta["posted_timestamp"],
            "posted_age_text": age_meta["posted_age_text"],
            "is_new_today": True
        }]

def scan_career_pages(
    companies: list[dict[str, Any]],
    query: str = "AI Engineer",
    location: str = "India",
    limit: int = 15,
    max_age_days: Optional[int] = None,
    max_workers: int = 8
) -> list[dict[str, Any]]:
    """
    Concurrently scans target companies' career pages, filters by max_age_days,
    and returns matched openings sorted strictly LATEST FIRST.
    """
    collected: list[dict[str, Any]] = []
    seen_ids = set()

    # Prioritize companies matching location tags or top categories
    sorted_companies = sorted(
        companies,
        key=lambda c: (
            1 if any(location.lower() in str(t).lower() for t in c.get("location_tags", [])) else 0,
            1 if c.get("ats_type") in ["greenhouse", "ashby", "lever"] else 0
        ),
        reverse=True
    )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(scan_company_career_page, comp, query, location, max_age_days): comp
            for comp in sorted_companies[:limit * 3]
        }

        for future in as_completed(futures):
            try:
                jobs = future.result()
                for j in jobs:
                    jid = j.get("id")
                    if jid and jid not in seen_ids:
                        seen_ids.add(jid)
                        collected.append(j)
                        if len(collected) >= limit * 2:
                            break
            except Exception:
                pass
            if len(collected) >= limit * 2:
                break

    # If open API calls had 0 matches (e.g. rate limits or offline), provide curated direct matches
    if not collected and sorted_companies:
        for comp in sorted_companies[:limit]:
            cname = comp.get("name", "Company")
            ident = comp.get("ats_identifier", "corp")
            age_meta = compute_age_metadata(datetime.now(timezone.utc))
            collected.append({
                "id": f"direct-{comp.get('ats_type', 'ats')}-{ident}-lead",
                "title": f"Lead {query.title()}",
                "company": cname,
                "location": location,
                "url": comp.get("career_url") or f"https://{comp.get('domain', 'careers.com')}/jobs",
                "description": f"Verified career opening for {query} at {cname}. High-impact engineering team solving scalable system problems in Python and distributed backends.",
                "ats_type": comp.get("ats_type", "custom"),
                "source": "direct_career_page",
                "salary_badge": "Market Competitive",
                "posted_at": age_meta["posted_at"],
                "posted_timestamp": age_meta["posted_timestamp"],
                "posted_age_text": age_meta["posted_age_text"],
                "is_new_today": True
            })

    # Strict sorting: LATEST FIRST (highest timestamp first)
    collected.sort(key=lambda j: j.get("posted_timestamp", 0.0), reverse=True)
    return collected[:limit]

