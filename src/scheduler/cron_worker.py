# src/scheduler/cron_worker.py
"""
Background Scheduler & Autorun Engine.
Handles:
1. Startup threshold check: triggers automatic scrape if last run > 12 hours ago (or no previous run).
2. Recurring daily cron: executes at 1:00 AM and 1:00 PM (configurable via CRON_HOURS).
3. Webhook / autostart execution for Vercel and Render deployments.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import os
from typing import Any, Optional
from src.db.database import (
    record_pipeline_run_start,
    record_pipeline_run_end,
    get_last_pipeline_run,
    save_job,
    save_tailored_application,
    save_audit_log,
)

CRON_HOURS_DEFAULT = [1, 13]  # 1 AM and 1 PM
AUTORUN_LOCK = asyncio.Lock()
_last_executed_slot: Optional[str] = None


def get_configured_cron_hours() -> list[int]:
    """Reads configured cron trigger hours from CRON_HOURS environment variable."""
    raw = os.getenv("CRON_HOURS", "")
    if not raw:
        return CRON_HOURS_DEFAULT
    try:
        hours = [int(h.strip()) for h in raw.split(",") if h.strip()]
        return hours if hours else CRON_HOURS_DEFAULT
    except Exception:
        return CRON_HOURS_DEFAULT


def should_trigger_startup_autorun(threshold_hours: float = 12.0) -> tuple[bool, str, Optional[float]]:
    """
    Checks if the pipeline should autorun on server startup.
    Returns: (should_run, reason_message, hours_since_last_run)
    """
    last_run = get_last_pipeline_run()
    if not last_run:
        return True, "No previous runs found in database. Initializing first startup autorun.", None

    started_at_str = last_run.get("started_at")
    if not started_at_str:
        return True, "Previous run missing timestamp. Running startup pipeline.", None

    try:
        last_dt = datetime.fromisoformat(started_at_str)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
    except Exception:
        return True, "Could not parse previous run timestamp. Running startup pipeline.", None

    now_utc = datetime.now(timezone.utc)
    delta_seconds = (now_utc - last_dt).total_seconds()
    hours_since = delta_seconds / 3600.0

    if hours_since >= threshold_hours:
        return (
            True,
            f"Last pipeline run was {hours_since:.1f} hours ago (exceeds {threshold_hours}h threshold). Autorunning...",
            hours_since,
        )
    return (
        False,
        f"Last pipeline run was {hours_since:.1f} hours ago (under {threshold_hours}h threshold). Skipping startup autorun.",
        hours_since,
    )


def get_next_scheduled_run(cron_hours: Optional[list[int]] = None) -> dict[str, Any]:
    """Calculates the upcoming scheduled cron trigger time in UTC."""
    hours = sorted(cron_hours or get_configured_cron_hours())
    now = datetime.now(timezone.utc)

    candidate_dts = []
    for h in hours:
        dt_today = now.replace(hour=h, minute=0, second=0, microsecond=0)
        if dt_today > now:
            candidate_dts.append(dt_today)
        else:
            dt_tomorrow = dt_today + timedelta(days=1)
            candidate_dts.append(dt_tomorrow)

    candidate_dts.sort()
    next_dt = candidate_dts[0]
    time_remaining_seconds = (next_dt - now).total_seconds()

    return {
        "next_run_iso": next_dt.isoformat(),
        "next_run_time_utc": next_dt.strftime("%H:%M UTC"),
        "hours_until_next": round(time_remaining_seconds / 3600.0, 1),
        "configured_hours": hours,
    }


def execute_pipeline_sync_sync(
    run_type: str = "scheduled_cron",
    query: Optional[str] = None,
    location: Optional[str] = None,
    discovery_source: str = "hybrid",
    max_age_days: int = 1,
) -> dict[str, Any]:
    """
    Synchronous pipeline runner that executes the LangGraph graph with daily sync settings,
    persists results to SQLite, and tracks execution metrics in pipeline_runs.
    """
    from src.server.app import PIPELINE_STATE, build_job_hunter_pipeline

    run_id = record_pipeline_run_start(run_type=run_type)
    try:
        pipeline = build_job_hunter_pipeline()

        target_q = query or PIPELINE_STATE["master_profile"].get("target_query", "AI Engineer")
        target_loc = location or PIPELINE_STATE["master_profile"].get("target_location", "India")

        PIPELINE_STATE["master_profile"]["target_query"] = target_q
        PIPELINE_STATE["master_profile"]["target_location"] = target_loc
        PIPELINE_STATE["discovery_source"] = discovery_source
        PIPELINE_STATE["max_age_days"] = max_age_days
        PIPELINE_STATE["only_new_daily"] = True

        updated_state = pipeline.invoke(PIPELINE_STATE)
        PIPELINE_STATE.clear()
        PIPELINE_STATE.update(updated_state)

        discovered = updated_state.get("discovered_queue", [])
        qualified = updated_state.get("qualified_queue", [])

        for job in discovered:
            save_job(job)
        for app_item in updated_state.get("approval_queue", []):
            save_tailored_application(app_item)
        for log in updated_state.get("audit_logs", [])[-5:]:
            save_audit_log(log.get("event", "LOG"), log)

        record_pipeline_run_end(
            run_id=run_id,
            status="COMPLETED",
            jobs_discovered=len(discovered),
            jobs_qualified=len(qualified),
        )

        return {
            "status": "success",
            "run_id": run_id,
            "run_type": run_type,
            "jobs_discovered": len(discovered),
            "jobs_qualified": len(qualified),
            "approval_queue_count": len(updated_state.get("approval_queue", [])),
        }

    except Exception as e:
        record_pipeline_run_end(
            run_id=run_id,
            status="FAILED",
            error_message=str(e),
        )
        return {
            "status": "failed",
            "run_id": run_id,
            "run_type": run_type,
            "error": str(e),
        }


async def execute_autorun_sync(
    run_type: str = "scheduled_cron",
    query: Optional[str] = None,
    location: Optional[str] = None,
    discovery_source: str = "hybrid",
    max_age_days: int = 1,
) -> dict[str, Any]:
    """Asynchronous wrapper that runs the sync executor in a threadpool to prevent blocking the event loop."""
    async with AUTORUN_LOCK:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            execute_pipeline_sync_sync,
            run_type,
            query,
            location,
            discovery_source,
            max_age_days,
        )


async def background_cron_loop():
    """
    Continuous background loop that wakes up every 30 seconds to evaluate if the current UTC hour
    matches 1:00 AM or 1:00 PM (or configured hours).
    Guarantees exactly one run per scheduled hour slot.
    """
    global _last_executed_slot
    print(f"[Scheduler] Background cron worker active. Configured hours (UTC): {get_configured_cron_hours()}")

    while True:
        try:
            now_utc = datetime.now(timezone.utc)
            hours = get_configured_cron_hours()

            slot_key = now_utc.strftime("%Y-%m-%d-%H")

            if now_utc.hour in hours and _last_executed_slot != slot_key:
                _last_executed_slot = slot_key
                print(f"[Scheduler] Triggering scheduled cron run for slot {slot_key} (hour {now_utc.hour}:00 UTC)...")
                res = await execute_autorun_sync("scheduled_cron")
                print(f"[Scheduler] Scheduled cron run completed: {res}")

            await asyncio.sleep(30)
        except asyncio.CancelledError:
            print("[Scheduler] Background cron worker cancelled.")
            break
        except Exception as e:
            print(f"[Scheduler Error] Background cron loop exception: {e}")
            await asyncio.sleep(60)
