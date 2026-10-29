"""HTTP-only private checks: credentials and exact alias on every request."""
from contextlib import redirect_stdout
import http.server
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from sleepmlx import served


class PrivateHandler(http.server.BaseHTTPRequestHandler):
    requests = []
    alias = "premonition-check-12345678-1234-1234-1234-123456789abc"
    key = "a" * 64
    advertised_alias = alias

    def log_message(self, *args):
        pass

    def respond(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        type(self).requests.append((self.path, self.headers.get("Authorization"), None))
        if self.headers.get("Authorization") != "Bearer " + self.key:
            return self.respond(401, {"error": "private credentials required"})
        if self.path == "/v1/models":
            return self.respond(200, {"data": [{"id": self.advertised_alias}]})
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/redirect-target")
            self.end_headers()
            return
        return self.respond(200, {"status": "ok"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
        type(self).requests.append((self.path, self.headers.get("Authorization"), body))
        if self.headers.get("Authorization") != "Bearer " + self.key:
            return self.respond(401, {"error": "private credentials required"})
        if self.path == "/v1/chat/completions":
            if body.get("model") != self.alias:
                return self.respond(400, {"error": "wrong private model"})
            return self.respond(200, {"choices": [{"message": {"content": "Paris"}}]})
        return self.respond(200, {"ok": True})


class PrivateHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), PrivateHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = "http://127.0.0.1:%d" % cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        PrivateHandler.requests = []
        PrivateHandler.advertised_alias = PrivateHandler.alias
        self.env = patch.dict(os.environ, {"SLEEPMLX_SERVED_PRIVATE_API_KEY": PrivateHandler.key,
                                           "SLEEPMLX_SERVED_PRIVATE_ALIAS": PrivateHandler.alias})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_health_models_chat_and_adapter_controls_all_receive_auth(self):
        self.assertTrue(served._healthy(self.url))
        self.assertEqual(served.ask(self.url, "Answer briefly.", "Capital of France?", 1.0), "Paris")
        with served._http_request(self.url, "/lora-adapters", data=b'{"adapters":[]}', timeout=2) as response:
            self.assertEqual(response.status, 200)
        paths = [request[0] for request in PrivateHandler.requests]
        self.assertEqual(paths, ["/health", "/v1/models", "/v1/chat/completions", "/lora-adapters"])
        self.assertTrue(all(header == "Bearer " + PrivateHandler.key for _, header, _ in PrivateHandler.requests))
        chat = PrivateHandler.requests[2][2]
        self.assertEqual(chat["model"], PrivateHandler.alias)
        self.assertEqual(chat["lora"], [{"id": 0, "scale": 1.0}])

    def test_wrong_alias_never_sends_a_chat_request(self):
        PrivateHandler.advertised_alias = "ordinary-chat-model"
        with self.assertRaisesRegex(ValueError, "alias does not match"):
            served.ask(self.url, "", "Question", 1.0)
        self.assertEqual([request[0] for request in PrivateHandler.requests], ["/v1/models"])

    def test_wrong_key_does_not_retry_anonymously(self):
        with patch.dict(os.environ, {"SLEEPMLX_SERVED_PRIVATE_API_KEY": "wrong-key"}):
            with self.assertRaises(Exception):
                served.ask(self.url, "", "Question", 1.0)
        self.assertEqual(len(PrivateHandler.requests), 1)
        self.assertEqual(PrivateHandler.requests[0][1], "Bearer wrong-key")

    def test_partial_credentials_and_nonloopback_urls_are_rejected_before_network(self):
        for env, url in (({"SLEEPMLX_SERVED_PRIVATE_API_KEY": ""}, self.url),
                         ({"SLEEPMLX_SERVED_PRIVATE_ALIAS": ""}, self.url),
                         ({}, "http://example.com:1234"), ({}, self.url + "/v1")):
            with self.subTest(env=env, url=url), patch.dict(os.environ, env):
                with self.assertRaisesRegex(ValueError, "invalid private"):
                    served.ask(url, "", "Question", 1.0)
        self.assertEqual(PrivateHandler.requests, [])

    def test_redirects_cannot_forward_the_private_key(self):
        with self.assertRaisesRegex(ValueError, "redirects are not allowed"):
            served._http_request(self.url, "/redirect", timeout=2)
        self.assertEqual([request[0] for request in PrivateHandler.requests], ["/redirect"])

    def test_private_loopback_calls_ignore_proxy_environment(self):
        with patch.dict(os.environ, {"http_proxy": "http://127.0.0.1:1", "HTTP_PROXY": "http://127.0.0.1:1", "no_proxy": "", "NO_PROXY": ""}):
            self.assertEqual(served.ask(self.url, "", "Question", 0.0), "Paris")

    def test_served_check_cli_only_reads_snapshot_and_makes_http_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards = Path(tmp) / "held.jsonl"
            cards.write_text(json.dumps({"night": 1, "status": "held_out", "q": "Question", "a": "Answer"}) + "\n")
            result = {"ok": True, "general_n": 8, "held_n": 1}
            with patch("sleepmlx.served.subprocess.Popen", side_effect=AssertionError("the HTTP-only grader must not spawn")), \
                 patch("sleepmlx.served.served_check", return_value=result) as checker, redirect_stdout(io.StringIO()):
                code = served.main(["--server", self.url, "--cards", str(cards), "--private-check-id", "owned-job"])
            self.assertEqual(code, 0)
            self.assertEqual(checker.call_args[0][1], [{"night": 1, "status": "held_out", "q": "Question", "a": "Answer"}])
            self.assertEqual(PrivateHandler.requests[0][1], "Bearer " + PrivateHandler.key)


if __name__ == "__main__":
    unittest.main()
