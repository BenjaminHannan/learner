"""Fake mlx_lm.server for tests (also runnable: python fake_upstream.py PORT)."""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        d = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(d)))
        self.end_headers()
        self.wfile.write(d)

    def do_GET(self):
        if self.path == "/health":
            return self._json({"status": "ok"})
        self._json({"object": "list", "data": [{"id": "default_model", "object": "model"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append(body)
        usage = {"prompt_tokens": 100, "completion_tokens": 7, "total_tokens": 107,
                 "prompt_tokens_details": {"cached_tokens": 64}}
        if not body.get("stream"):
            return self._json({"id": "x", "object": "chat.completion", "model": "default_model",
                               "choices": [{"index": 0, "finish_reason": "stop", "message": {
                                   "role": "assistant", "content": "The answer is pineapple.",
                                   "reasoning": "hmm"}}], "usage": usage})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()

        def ev(delta, finish=None, **extra):
            c = {"id": "x", "model": "default_model", "choices": [
                {"index": 0, "delta": delta, "finish_reason": finish}]}
            c.update(extra)
            self.wfile.write(b"data: " + json.dumps(c).encode() + b"\n\n")
            self.wfile.flush()

        ev({"role": "assistant", "reasoning": "think "})
        ev({"reasoning": "more"})
        ev({"content": "Hel"})
        self.server.gate.wait(5)  # lets tests prove chunks arrive before the stream ends
        ev({"content": "lo"})
        ev({"tool_calls": [{"index": 0, "id": "c1", "type": "function",
                            "function": {"name": "bash", "arguments": "{\"cmd\":"}}]})
        ev({"tool_calls": [{"index": 0, "function": {"arguments": " \"ls\"}"}}]})
        ev({}, "tool_calls", usage=usage)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


def start(port=0):
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    srv.requests, srv.gate = [], threading.Event()
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":
    s = start(int(sys.argv[1]))
    s.gate.set()
    threading.Event().wait()
