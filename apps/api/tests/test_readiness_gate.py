"""Unit tests for the fail-closed startup and readiness gate."""

import importlib.util
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, ClassVar

import pytest

script_path = Path(__file__).resolve().parents[3] / "scripts" / "wait_for_readiness.py"
spec = importlib.util.spec_from_file_location("wait_for_readiness", str(script_path))
wait_for_readiness = importlib.util.module_from_spec(spec)
sys.modules["wait_for_readiness"] = wait_for_readiness
spec.loader.exec_module(wait_for_readiness)


@pytest.fixture(autouse=True)
def _clean_tables():
    """Readiness gate tests are pure HTTP network mocks and do not use the database."""
    yield


class MockServerHandler(BaseHTTPRequestHandler):
    health_status: ClassVar[int] = 200
    ready_status: ClassVar[int] = 200
    ready_data: ClassVar[dict[str, Any]] = {
        "status": "ready",
        "checks": {
            "database": "ok",
            "schema": "ok",
            "migration": "d105a4143283",
            "pipeline": "ok",
            "supabase_bridge": "ok",
        },
    }
    calls: ClassVar[int] = 0

    def do_GET(self):
        MockServerHandler.calls += 1
        if self.path == "/api/v1/health":
            self.send_response(MockServerHandler.health_status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                b'{"status": "ok"}'
                if MockServerHandler.health_status == 200
                else b'{"status": "error"}'
            )
        elif self.path == "/api/v1/ready":
            self.send_response(MockServerHandler.ready_status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(MockServerHandler.ready_data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Quiet logging in tests


@pytest.fixture
def mock_server():
    server = HTTPServer(("127.0.0.1", 0), MockServerHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    MockServerHandler.health_status = 200
    MockServerHandler.ready_status = 200
    MockServerHandler.calls = 0
    yield port
    server.shutdown()


def test_readiness_gate_success(mock_server):
    port = mock_server
    ready = wait_for_readiness.wait_until_ready(
        host="127.0.0.1",
        port=port,
        timeout_seconds=5.0,
        interval_seconds=0.1,
        expected_revision="d105a4143283",
        require_workers=True,
    )
    assert ready is True


def test_readiness_gate_connection_refused():
    # Pick a port that is not listening
    ready = wait_for_readiness.wait_until_ready(
        host="127.0.0.1",
        port=59999,
        timeout_seconds=1.0,
        interval_seconds=0.1,
    )
    assert ready is False


def test_readiness_gate_503_timeout(mock_server):
    port = mock_server
    MockServerHandler.ready_status = 503
    MockServerHandler.ready_data = {
        "status": "not_ready",
        "checks": {"database": "ok", "schema": "incompatible"},
    }
    ready = wait_for_readiness.wait_until_ready(
        host="127.0.0.1",
        port=port,
        timeout_seconds=1.0,
        interval_seconds=0.1,
    )
    assert ready is False


def test_readiness_gate_wrong_revision(mock_server):
    port = mock_server
    ready = wait_for_readiness.wait_until_ready(
        host="127.0.0.1",
        port=port,
        timeout_seconds=2.0,
        interval_seconds=0.1,
        expected_revision="wrong_expected_revision_hash",
    )
    assert ready is False


def test_readiness_gate_worker_unavailable(mock_server):
    port = mock_server
    MockServerHandler.ready_data = {
        "status": "ready",
        "checks": {
            "database": "ok",
            "schema": "ok",
            "migration": "d105a4143283",
            "pipeline": "ok",
            "supabase_bridge": "not_ready",
        },
    }
    ready = wait_for_readiness.wait_until_ready(
        host="127.0.0.1",
        port=port,
        timeout_seconds=1.0,
        interval_seconds=0.1,
        require_workers=True,
    )
    assert ready is False


def test_readiness_gate_slow_startup_recovery(mock_server):
    port = mock_server
    # Start with 503, then recover
    MockServerHandler.ready_status = 503
    MockServerHandler.ready_data = {
        "status": "not_ready",
        "checks": {"database": "connecting", "schema": "unavailable"},
    }

    def recover():
        import time

        time.sleep(0.4)
        MockServerHandler.ready_status = 200
        MockServerHandler.ready_data = {
            "status": "ready",
            "checks": {
                "database": "ok",
                "schema": "ok",
                "migration": "d105a4143283",
            },
        }

    recovery_thread = threading.Thread(target=recover, daemon=True)
    recovery_thread.start()

    ready = wait_for_readiness.wait_until_ready(
        host="127.0.0.1",
        port=port,
        timeout_seconds=3.0,
        interval_seconds=0.1,
        expected_revision="d105a4143283",
    )
    assert ready is True
