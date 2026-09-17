# tests/test_scheduler_and_autorun.py
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from src.server.app import app
from src.db.database import (
    init_db,
    record_pipeline_run_start,
    record_pipeline_run_end,
    get_last_pipeline_run,
    get_pipeline_run_history,
)
from src.scheduler.cron_worker import (
    should_trigger_startup_autorun,
    get_next_scheduled_run,
    execute_pipeline_sync_sync,
)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_scheduler.db"
    monkeypatch.setattr("src.db.database.DB_PATH", test_db)
    monkeypatch.setattr("src.scheduler.cron_worker.get_last_pipeline_run", lambda: get_last_pipeline_run(test_db))
    monkeypatch.setattr("src.db.database.get_last_pipeline_run", lambda: get_last_pipeline_run(test_db))
    init_db(test_db)
    return test_db


def test_database_pipeline_runs_lifecycle(setup_test_db):
    test_db = setup_test_db
    # Record start
    run_id = record_pipeline_run_start("startup_autorun", db_path=test_db)
    assert run_id is not None
    assert run_id > 0

    last_run = get_last_pipeline_run(db_path=test_db)
    assert last_run["status"] == "RUNNING"
    assert last_run["run_type"] == "startup_autorun"

    # Record completion
    record_pipeline_run_end(
        run_id=run_id,
        status="COMPLETED",
        jobs_discovered=5,
        jobs_qualified=3,
        db_path=test_db
    )

    completed_run = get_last_pipeline_run(db_path=test_db)
    assert completed_run["status"] == "COMPLETED"
    assert completed_run["jobs_discovered"] == 5
    assert completed_run["jobs_qualified"] == 3
    assert completed_run["completed_at"] is not None

    history = get_pipeline_run_history(limit=5, db_path=test_db)
    assert len(history) == 1


def test_should_trigger_startup_autorun_logic(setup_test_db, monkeypatch):
    test_db = setup_test_db

    # Case 1: No previous runs in database -> Should autorun
    should_run, reason, hours = should_trigger_startup_autorun(threshold_hours=12.0)
    assert should_run is True
    assert "No previous runs" in reason

    # Case 2: Run was 2 hours ago -> Should NOT autorun
    run_id = record_pipeline_run_start("recent_run", db_path=test_db)
    two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    conn = test_db
    # Update timestamp manually to 2 hours ago
    import sqlite3
    c = sqlite3.connect(str(test_db))
    c.execute("UPDATE pipeline_runs SET started_at = ? WHERE id = ?", (two_hours_ago, run_id))
    c.commit()
    c.close()

    should_run, reason, hours = should_trigger_startup_autorun(threshold_hours=12.0)
    assert should_run is False
    assert hours is not None
    assert 1.9 < hours < 2.5
    assert "under 12.0h threshold" in reason

    # Case 3: Run was 15 hours ago -> Should autorun
    fifteen_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=15)).isoformat()
    c = sqlite3.connect(str(test_db))
    c.execute("UPDATE pipeline_runs SET started_at = ? WHERE id = ?", (fifteen_hours_ago, run_id))
    c.commit()
    c.close()

    should_run, reason, hours = should_trigger_startup_autorun(threshold_hours=12.0)
    assert should_run is True
    assert hours is not None
    assert 14.9 < hours < 15.5
    assert "exceeds 12.0h threshold" in reason


def test_get_next_scheduled_run_calculation():
    sched = get_next_scheduled_run(cron_hours=[1, 13])
    assert "next_run_iso" in sched
    assert "next_run_time_utc" in sched
    assert sched["next_run_time_utc"] in ["01:00 UTC", "13:00 UTC"]
    assert sched["hours_until_next"] >= 0
    assert sched["configured_hours"] == [1, 13]


def test_scheduler_status_endpoint(setup_test_db):
    client = TestClient(app)
    res = client.get("/api/scheduler/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "active"
    assert "next_scheduled_run" in data
    assert "should_startup_autorun" in data
    assert "configured_cron_hours_utc" in data


def test_cron_webhook_trigger_endpoint(setup_test_db, monkeypatch):
    client = TestClient(app)

    # Mock pipeline invoke to prevent calling external LLMs during test
    class MockPipeline:
        def invoke(self, state):
            return dict(state)

    monkeypatch.setattr("src.server.app.build_job_hunter_pipeline", lambda: MockPipeline())

    # 1. Without CRON_SECRET configured -> Open webhook
    monkeypatch.delenv("CRON_SECRET", raising=False)
    res_open = client.post("/api/cron/trigger")
    assert res_open.status_code == 200
    data = res_open.json()
    assert "Autostart webhook executed successfully!" in data["message"]

    # 2. With CRON_SECRET configured
    monkeypatch.setenv("CRON_SECRET", "super-secret-cron-token-123")

    # Unauthorized attempt
    res_unauth = client.post("/api/cron/trigger")
    assert res_unauth.status_code == 401
    assert "Unauthorized" in res_unauth.json()["detail"]

    # Authorized attempt via query parameter
    res_auth_query = client.post("/api/cron/trigger?token=super-secret-cron-token-123")
    assert res_auth_query.status_code == 200

    # Authorized attempt via Bearer header
    res_auth_header = client.get(
        "/api/cron/trigger",
        headers={"Authorization": "Bearer super-secret-cron-token-123"}
    )
    assert res_auth_header.status_code == 200


def test_manual_scheduler_autostart_endpoint(setup_test_db, monkeypatch):
    client = TestClient(app)

    class MockPipeline:
        def invoke(self, state):
            return dict(state)

    monkeypatch.setattr("src.server.app.build_job_hunter_pipeline", lambda: MockPipeline())

    res = client.post("/api/scheduler/autostart")
    assert res.status_code == 200
    data = res.json()
    assert "Manual autostart sync triggered!" in data["message"]
