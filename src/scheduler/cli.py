# src/scheduler/cli.py
"""
Job Hunter Autostart CLI.
Allows triggering the automated pipeline sync from terminal, Docker CMD, or cloud cron jobs (e.g. Render Cron Job).

Usage:
    python -m src.scheduler.cli
    python -m src.scheduler.cli --source direct --max-age 1
    python -m src.scheduler.cli --check-startup
"""
import argparse
import sys
from src.db.database import init_db
from src.scheduler.cron_worker import (
    should_trigger_startup_autorun,
    execute_pipeline_sync_sync,
    get_next_scheduled_run,
)


def main():
    parser = argparse.ArgumentParser(description="Autonomous Job Hunter Autostart CLI")
    parser.add_argument("--source", default="hybrid", choices=["hybrid", "direct", "linkedin"], help="Discovery source")
    parser.add_argument("--max-age", type=int, default=1, help="Max age in days for job discovery")
    parser.add_argument("--query", default=None, help="Override target job search query")
    parser.add_argument("--location", default=None, help="Override target location")
    parser.add_argument("--check-startup", action="store_true", help="Only run if last run was > 12 hours ago")
    parser.add_argument("--status", action="store_true", help="Print scheduler status and exit")

    args = parser.parse_args()
    init_db()

    if args.status:
        sched = get_next_scheduled_run()
        print(f"[Scheduler Status]")
        print(f"  Next Scheduled Run: {sched['next_run_time_utc']} (in ~{sched['hours_until_next']}h)")
        print(f"  Configured Hours:   {sched['configured_hours']}")
        sys.exit(0)

    if args.check_startup:
        should_run, reason, hours_since = should_trigger_startup_autorun(threshold_hours=12.0)
        print(f"[Startup Check] {reason}")
        if not should_run:
            print("[Startup Check] Execution skipped because threshold not reached.")
            sys.exit(0)

    print(f"[CLI Autostart] Initiating automated pipeline sync...")
    print(f"  Source: {args.source} | Max Age: {args.max_age}d | Query: {args.query or 'from profile'}")

    res = execute_pipeline_sync_sync(
        run_type="cli",
        query=args.query,
        location=args.location,
        discovery_source=args.source,
        max_age_days=args.max_age,
    )
    print(f"[CLI Autostart] Result: {res}")
    if res.get("status") == "success":
        print(f"  Discovered: {res.get('jobs_discovered', 0)} jobs")
        print(f"  Qualified:  {res.get('jobs_qualified', 0)} jobs")
        print(f"  Approval:   {res.get('approval_queue_count', 0)} jobs ready for review")
        sys.exit(0)
    else:
        print(f"  Error: {res.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
