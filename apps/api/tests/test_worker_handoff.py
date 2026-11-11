"""Real disposable-Postgres lock handoff and bounded process lifecycle checks."""

import os
import signal
import subprocess
import sys
import time
from threading import Event

import pytest
from sqlalchemy import text

from app.db.session import get_engine
from app.workers.pipeline import LOCK_ID, acquire_lock


def start_worker():
    # Test environment already enforces loopback-only disposable DB and no providers.
    return subprocess.Popen(
        [sys.executable, "-m", "app.workers.pipeline"],
        env=os.environ.copy(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for(predicate, timeout=12):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.1)
    raise AssertionError("Worker handoff condition did not occur")


def test_once_refuses_second_owner_and_standby_can_stop():
    with get_engine().connect() as owner, get_engine().connect() as standby:
        assert acquire_lock(owner, Event(), once=True)
        try:
            with pytest.raises(SystemExit, match="already owns"):
                acquire_lock(standby, Event(), once=True)
            stopped = Event()
            stopped.set()
            assert not acquire_lock(standby, stopped, once=False)
        finally:
            owner.execute(text("select pg_advisory_unlock(:id)"), {"id": LOCK_ID})
            owner.commit()


def lock_pid():
    with get_engine().connect() as db:
        return db.scalar(
            text(
                "select pid from pg_locks where locktype='advisory' and objid=:id "
                "and database=(select oid from pg_database where datname=current_database())"
            ),
            {"id": LOCK_ID},
        )


@pytest.mark.parametrize("termination", [signal.SIGTERM, signal.SIGKILL])
def test_replacement_waits_then_takes_over_after_owner_exit(termination):
    owner = start_worker()
    standby = None
    try:
        wait_for(lambda: lock_pid() is not None)
        previous_pid = lock_pid()
        standby = start_worker()
        time.sleep(2)
        assert owner.poll() is None and standby.poll() is None
        assert lock_pid() == previous_pid
        owner.send_signal(termination)
        owner.wait(timeout=8)
        wait_for(lambda: lock_pid() is not None and lock_pid() != previous_pid)
        assert standby.poll() is None
        standby.terminate()
        assert standby.wait(timeout=8) == 0
        wait_for(lambda: lock_pid() is None)
    finally:
        for p in (standby, owner):
            if p is not None and p.poll() is None:
                p.kill()
                p.wait(timeout=5)


def test_waiting_replacement_exits_cleanly_on_termination():
    with get_engine().connect() as owner:
        assert acquire_lock(owner, Event(), once=True)
        worker = start_worker()
        try:

            def connected_standby():
                with get_engine().connect() as db:
                    return db.scalar(
                        text(
                            "select exists(select 1 from pg_stat_activity "
                            "where datname=current_database() and pid != :owner "
                            "and application_name='sentinel-pipeline' and state='idle')"
                        ),
                        {"owner": owner.scalar(text("select pg_backend_pid()"))},
                    )

            wait_for(connected_standby)
            assert worker.poll() is None
            worker.terminate()
            assert worker.wait(timeout=8) == 0
        finally:
            if worker.poll() is None:
                worker.kill()
                worker.wait(timeout=5)
            owner.execute(text("select pg_advisory_unlock(:id)"), {"id": LOCK_ID})
            owner.commit()
