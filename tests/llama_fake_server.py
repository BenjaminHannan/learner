"""Fake llama-server for the render_local tests: GET /health, POST /tokenize (one id per character, id 1 = BOS), POST /completion with a scripted completion.
The real server cuts the matched stop string off `content` and reports it in `stopping_word`; this one does the same."""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BOS = "<|bos|>"
CALL = ("I will check it.\n<ifm|tool_calls>\n<ifm|tool_call>bash\n<ifm|arg_key>command</ifm|arg_key>\n<ifm|arg_value>python3 -c 'print(6)'</ifm|arg_value>\n"
        "<ifm|arg_key>description</ifm|arg_key>\n<ifm|arg_value>print six</ifm|arg_value>\n</ifm|tool_call>\n</ifm|tool_calls>")


def default_script(body):
    """First turn: a bash call ending in the stop string; once the prompt holds that call in its history ("print six"): the final answer, ended by <|ifm|im_end|>."""
    if "print six" in body["prompt"]:
        return "The tool printed 6.\n<answer>6</answer><|ifm|im_end|>"
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
        self._json({"status": "ok"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/tokenize":
            c = body["content"]
            ids = ([1] if body.get("add_special") and self.server.adds_bos else []) + ([1] if c.startswith(BOS) else []) + [ord(ch) % 250 + 2 for ch in c.removeprefix(BOS)]
            return self._json({"tokens": ids})
        self.server.requests.append(body)
        if self.server.fail_ctx:
            return self._json({"error": {"code": 400, "type": "exceed_context_size_error", "message": "the request exceeds the available context size, try increasing it"}}, 400)
        full = self.server.script(body)
        stop_word, text = "", full
        for sw in body["stop"]:
            i = text.find(sw)
            if i >= 0:
                text, stop_word = text[:i], sw
        limit = len(text) > 10_000
        self._json({"content": text, "tokens_predicted": 7, "tokens_evaluated": len(body["prompt"]) // 3, "tokens_cached": 5, "model": "x.gguf", "stop": True,
                    "stop_type": "limit" if limit else ("word" if stop_word else "eos"), "stopping_word": stop_word, "truncated": False,
                    "timings": {"prompt_n": 3, "prompt_ms": 12.0, "predicted_n": 7, "predicted_ms": 70.0, "cache_n": 5}})


def start(port=0, script=default_script, adds_bos=False, fail_ctx=False):
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    srv.requests, srv.script, srv.adds_bos, srv.fail_ctx = [], script, adds_bos, fail_ctx
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":  # `python -m tests.llama_fake_server PORT`: stands in for llama-server.exe in the LlamaServer lifecycle test
    start(int(sys.argv[1]))
    threading.Event().wait()
