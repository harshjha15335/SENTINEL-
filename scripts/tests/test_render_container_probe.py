"""Exercise the container gate's real HTTP probe without Docker or provider access."""

import json
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from scripts.verify_render_staging_container import fixture_http


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
