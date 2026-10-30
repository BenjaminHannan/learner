"""Fake mlx_lm.server for the K2 proxy tests: scripted K2 native completions (the stop string `</ifm|tool_calls>` is dropped, like the real server does)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CALL = ("I will check it.\n<ifm|tool_calls>\n<ifm|tool_call>bash\n<ifm|arg_key>command</ifm|arg_key>\n<ifm|arg_value>python3 -c 'print(6)'</ifm|arg_value>\n"
        "<ifm|arg_key>description</ifm|arg_key>\n<ifm|arg_value>print six</ifm|arg_value>\n</ifm|tool_call>\n")


def default_script(body):
    """First turn: a bash call; once a tool result is in the history: the final answer."""
    if any(m.get("role") == "tool" for m in body["messages"]):
        return "The tool printed 6.\n<answer>6</answer>"
    return CALL


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

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
        self._json({"object": "list", "data": [{"id": "default_model", "object": "model"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append(body)
        text = self.server.script(body)
        self._json({"id": "x", "object": "chat.completion", "model": "default_model",
                    "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": text}}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 7, "total_tokens": 107}})


def start(port=0, script=default_script):
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    srv.requests, srv.script = [], script
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
