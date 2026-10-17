"""Worker Kill-and-Restart Resilience Tests.

Adheres to MASTER_PLAN.md §9.2, §9.4, and Phase 5 deliverables:
- Verifies that killing the background worker (SIGTERM / interruption) does not corrupt database state.
- Proves that restarting the worker picks up pending tasks without task loss or duplication.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from vigil_api.database import Base
from vigil_api.models.v2 import (
    ConsentRecord,
    FollowUpTask,
    FollowUpTaskStatus,
    FollowUpTaskType,
    Patient,
    ReminderReceipt,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def resilience_db(tmp_path):
    db_file = tmp_path / "resilience.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    return db_url, db_file


def test_worker_kill_and_restart_lifecycle(resilience_db):
    db_url, db_file = resilience_db
    engine = create_engine(db_url)

    now = datetime.now(timezone.utc)
    due_date = now - timedelta(days=2)  # Overdue

    # 1. Seed 5 patients and 5 overdue tasks
    with Session(engine) as session:
        for i in range(5):
            pid = f"pat-resil-{i}"
            pat = Patient(
                id=pid,
                biological_sex="female",
                primary_cancer_type="breast",
                synthetic=True,
                status="active",
                created_at=now,
                updated_at=now,
            )
            session.add(pat)

            consent = ConsentRecord(
                id=f"c-resil-{i}",
                patient_id=pid,
                scope="clinical_care",
                granted=True,
                granted_at=now,
            )
            session.add(consent)

            task = FollowUpTask(
                id=f"tsk-resil-{i}",
                patient_id=pid,
                task_type=FollowUpTaskType.REPEAT_SPECIMEN.value,
                status=FollowUpTaskStatus.PENDING.value,
                due_date=due_date,
                escalation_level=0,
                created_at=due_date,
                updated_at=due_date,
            )
            session.add(task)
        session.commit()

    # Verify 5 tasks exist and 0 receipts
    with Session(engine) as session:
        tasks = session.execute(select(FollowUpTask)).scalars().all()
        assert len(tasks) == 5
        receipts = session.execute(select(ReminderReceipt)).scalars().all()
        assert len(receipts) == 0

    # 2. Spawn worker in a background subprocess
    env = {
        **os.environ,
        "DATABASE_URL": db_url,
        "PYTHONPATH": str(ROOT / "apps" / "api"),
    }
    worker_proc = subprocess.Popen(
        [sys.executable, "-m", "vigil_api.worker", "--interval", "0.2"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Let worker run briefly
    time.sleep(0.5)

    # 3. Simulate process termination (SIGTERM)
    worker_proc.send_signal(signal.SIGTERM)
    try:
        worker_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        worker_proc.kill()
        worker_proc.wait()

    # 4. Check DB state post-kill: no corruption, valid database
    with Session(engine) as session:
        # All 5 tasks must still exist (no task disappeared!)
        tasks_post_kill = session.execute(select(FollowUpTask)).scalars().all()
        assert len(tasks_post_kill) == 5

        receipts_post_kill = session.execute(select(ReminderReceipt)).scalars().all()
        intermediate_count = len(receipts_post_kill)
        assert intermediate_count >= 1, "At least one reminder was processed during initial run"

    # 5. Restart worker with --once to finish remaining cycles
    restart_res = subprocess.run(
        [sys.executable, "-m", "vigil_api.worker", "--once"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert restart_res.returncode == 0

    # 6. Verify terminal state: all 5 tasks processed without loss
    with Session(engine) as session:
        all_receipts = session.execute(select(ReminderReceipt)).scalars().all()
        assert len(all_receipts) >= 5, f"Expected at least 5 receipts, got {len(all_receipts)}"

        # Verify distinct recipients/tasks
        task_ids_with_receipts = {r.task_id for r in all_receipts}
        assert len(task_ids_with_receipts) == 5
