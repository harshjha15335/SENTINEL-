"""Exercise the container gate's real HTTP probe without Docker or provider access."""

import json
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from scripts.verify_render_staging_container import container_http, fixture_http


@contextmanager
def fixture_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(503 if self.path == "/not-ready" else 200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"fixture"}')

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Set-Cookie", "fixture=session; Secure; HttpOnly")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {"body": json.loads(body), "cookie": self.headers.get("Cookie")}
                ).encode()
            )

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class ContainerProbeTests(unittest.TestCase):
    def test_isolated_transport_keeps_credentials_off_command_arguments(self):
        from subprocess import CompletedProcess

        with patch("scripts.verify_render_staging_container._execute") as execute:
            execute.return_value = CompletedProcess([], 0, '[503, [], "not ready"]', "")
            status, _, body = container_http(
                "owned-fixture",
                "/login",
                {"password": "fixture-secret"},
                "fixture=session",
            )
        self.assertEqual((status, body), (503, b"not ready"))
        args, kwargs = execute.call_args
        self.assertNotIn("fixture-secret", repr(args))
        self.assertNotIn("fixture=session", repr(args))
        self.assertEqual(
            json.loads(kwargs["input"])["payload"], {"password": "fixture-secret"}
        )
        self.assertIn("fixture_http(8000", args[0][-1])

    def test_transport_failure_does_not_expose_sensitive_output(self):
        from subprocess import CompletedProcess

        with patch("scripts.verify_render_staging_container._execute") as execute:
            execute.return_value = CompletedProcess(
                [], 1, "fixture-secret", "fixture=session"
            )
            with self.assertRaises(ConnectionError) as failure:
                container_http("owned-fixture", "/ready")
        self.assertEqual(
            str(failure.exception), "isolated container HTTP probe unavailable"
        )

    def test_reads_ready_response(self):
        with fixture_server() as port:
            status, _, data = fixture_http(port, "/ready")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data), {"status": "fixture"})

    def test_preserves_not_ready_status(self):
        with fixture_server() as port:
            status, _, data = fixture_http(port, "/not-ready")
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(data), {"status": "fixture"})

    def check_post(self, payload):
        with fixture_server() as port:
            status, headers, data = fixture_http(
                port, "/login", payload, "fixture=prior"
            )
        self.assertEqual(status, 200)
        self.assertIn(("Set-Cookie", "fixture=session; Secure; HttpOnly"), headers)
        self.assertEqual(json.loads(data), {"body": payload, "cookie": "fixture=prior"})

    def test_posts_empty_json(self):
        self.check_post({})

    def test_posts_auth_and_preserves_headers(self):
        self.check_post(
            {"email": "fixture@example.invalid", "password": "fixture-only"}
        )
