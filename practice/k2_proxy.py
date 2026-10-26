"""OpenAI-compatible proxy in front of mlx_lm.server for K2 (stdlib only).

Why: mlx_lm.server 0.32.2 has no K2 tool-call parser, so K2's native calls
    <ifm|tool_calls><ifm|tool_call>NAME<ifm|arg_key>K</ifm|arg_key><ifm|arg_value>V</ifm|arg_value>...</ifm|tool_call></ifm|tool_calls>
come back as plain text. This proxy
  * forwards /v1/chat/completions upstream (always non-streaming, model forced to the upstream default, stop `</ifm|tool_calls>` added),
  * parses the native calls into OpenAI `tool_calls` and strips them from `content`,
  * converts incoming history so the K2 chat template can render it (assistant tool_calls.arguments must be a dict there; thinking fields are dropped),
  * synthesises an SSE stream when the client asked for stream=true,
  * logs every call (JSONL, one file per try) so a try's turns can be grouped and rendered exactly as served.

Run:  python -m practice.k2_proxy --port 8095 --upstream http://127.0.0.1:18081 --log DIR
A try is keyed by the `X-Practice-Try` header, or a `/t/<key>/v1/...` path prefix, or else a hash of the first user message.
"""
import argparse
import hashlib
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

STOP = "</ifm|tool_calls>"
OPEN_BLOCK = "<ifm|tool_calls>"
OPEN_CALL = "<ifm|tool_call>"
CLOSE_CALL = "</ifm|tool_call>"
THINK_KEYS = ("think", "think_fast", "think_faster", "reasoning", "reasoning_content")
PASS_PARAMS = ("temperature", "top_p", "top_k", "min_p", "repetition_penalty", "seed")

_ARG_RE = re.compile(r"<ifm\|arg_key>(.*?)</ifm\|arg_key>\s*(?:<ifm\|arg_type>.*?</ifm\|arg_type>\s*)?<ifm\|arg_value>(.*?)(?:</ifm\|arg_value>|(?=<ifm\|arg_key>)|\Z)", re.S)
_NAME_RE = re.compile(r"\s*([^\s<{]+)")


# ------------------------------------------------------------------ parsing
def _coerce(value, spec):
    """Coerce a string argument by its JSON-schema type when that is obvious; otherwise keep the string."""
    t = spec.get("type") if isinstance(spec, dict) else None
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), None) if len(t) else None
    s = value.strip()
    try:
        if t == "integer":
            return int(s)
        if t == "number":
            f = float(s)
            return int(f) if f.is_integer() and re.fullmatch(r"-?\d+", s) else f
        if t == "boolean":
            if s.lower() in ("true", "false"):
                return s.lower() == "true"
            return value
        if t in ("array", "object"):
            v = json.loads(s)
            return v if isinstance(v, list if t == "array" else dict) else value
    except (ValueError, TypeError):
        return value
    return value


def _schema_props(tools, name):
    for t in tools or []:
        fn = t.get("function", t) if isinstance(t, dict) else {}
        if fn.get("name") == name:
            p = fn.get("parameters") or {}
            return p.get("properties") or {}
    return {}


def parse_native(text, tools=None):
    """-> (content or None, [{"name", "arguments": dict}]). Tolerates a missing closing tag (stop string dropped or output cut)."""
    i = text.find(OPEN_BLOCK)
    if i < 0:
        i = text.find(OPEN_CALL)
    if i < 0:
        return text, []
    content = text[:i]
    body = text[i:]
    body = body.replace(OPEN_BLOCK, "", 1) if body.startswith(OPEN_BLOCK) else body
    end = body.find(STOP)
    tail = ""
    if end >= 0:
        tail = body[end + len(STOP):]
        body = body[:end]
    calls = []
    for chunk in body.split(OPEN_CALL)[1:]:
        c = chunk.split(CLOSE_CALL, 1)[0]
        stripped = c.strip()
        if stripped.startswith("{"):  # json call format: {"name": ..., "arguments": {...}}
            try:
                o = json.loads(stripped)
                a = o.get("arguments", {})
                calls.append({"name": str(o["name"]), "arguments": a if isinstance(a, dict) else {}})
                continue
            except (ValueError, KeyError, TypeError):
                pass
        m = _NAME_RE.match(c)
        if not m:
            continue
        name = m.group(1)
        props = _schema_props(tools, name)
        args = {}
        for k, v in _ARG_RE.findall(c[m.end():]):
            k = k.strip()
            args[k] = _coerce(v, props.get(k, {}))
        calls.append({"name": name, "arguments": args})
    if tail.strip():
        content += tail
    return (content if content.strip() else None), calls


def to_openai_calls(calls):
    return [{"id": "call_" + uuid.uuid4().hex[:24], "type": "function",
             "function": {"name": c["name"], "arguments": json.dumps(c["arguments"], ensure_ascii=False)}} for c in calls]


# ------------------------------------------------------------------ history mapping
def map_messages(messages):
    """OpenAI history -> what the K2 template renders: tool_calls.arguments as dicts, no thinking fields, no tool_call_id/name noise."""
    out = []
    for m in messages:
        m = dict(m)
        role = m.get("role")
        if role == "assistant":
            for k in THINK_KEYS:
                m.pop(k, None)
            if m.get("content") is None:
                m["content"] = ""
            tcs = m.get("tool_calls")
            if tcs:
                new = []
                for tc in tcs:
                    fn = dict(tc.get("function", tc))
                    a = fn.get("arguments")
                    if isinstance(a, str):
                        try:
                            a = json.loads(a) if a.strip() else {}
                        except ValueError:
                            a = {"input": a}
                    fn["arguments"] = a if isinstance(a, dict) else {}
                    new.append({"id": tc.get("id"), "type": "function", "function": fn})
                m["tool_calls"] = new
            else:
                m.pop("tool_calls", None)
        elif role == "developer":
            m["role"] = "system"
        elif role == "tool":
            c = m.get("content")
            if isinstance(c, list):
                m["content"] = "\n".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in c)
            elif c is None:
                m["content"] = ""
        out.append(m)
    return out


def fix_tools(tools):
    out = []
    for t in tools or []:
        t = json.loads(json.dumps(t))
        fn = t.get("function")
        if isinstance(fn, dict) and not isinstance(fn.get("parameters"), dict):
            fn["parameters"] = {"type": "object", "properties": {}}
        out.append(t)
    return out


def tools_hash(tools):
    return hashlib.sha1(json.dumps(tools, sort_keys=True).encode()).hexdigest()[:12]


def first_user_key(messages):
    for m in messages:
        if m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, list):
                c = "".join(p.get("text", "") for p in c if isinstance(p, dict))
            return "msg" + hashlib.sha1(str(c).encode()).hexdigest()[:12]
    return "nouser"


def safe_key(k):
    return re.sub(r"[^A-Za-z0-9_.=-]", "_", k)[:120]


# ------------------------------------------------------------------ SSE
def sse_chunks(result, include_usage=False):
    """Full completion result (dict from `build_response`) -> list of SSE `data:` payload strings ending with [DONE]."""
    msg = result["choices"][0]["message"]
    base = {"id": result["id"], "object": "chat.completion.chunk", "created": result["created"], "model": result["model"]}

    def ch(delta, finish=None):
        return json.dumps({**base, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]})
    out = [ch({"role": "assistant", "content": ""})]
    if msg.get("content"):
        out.append(ch({"content": msg["content"]}))
    for i, tc in enumerate(msg.get("tool_calls") or []):
        out.append(ch({"tool_calls": [{"index": i, "id": tc["id"], "type": "function", "function": tc["function"]}]}))
    out.append(ch({}, result["choices"][0]["finish_reason"]))
    if include_usage:
        out.append(json.dumps({**base, "choices": [], "usage": result["usage"]}))
    out.append("[DONE]")
    return out


def build_response(text, tools, usage, model):
    content, calls = parse_native(text, tools)
    tcs = to_openai_calls(calls)
    msg = {"role": "assistant", "content": content}
    if tcs:
        msg["tool_calls"] = tcs
    return {"id": "chatcmpl-" + uuid.uuid4().hex[:20], "object": "chat.completion", "created": int(time.time()), "model": model,
            "choices": [{"index": 0, "message": msg, "finish_reason": "tool_calls" if tcs else "stop"}], "usage": usage}, calls


# ------------------------------------------------------------------ server
CONTEXT_ERR = "context_length_exceeded"


class ContextTooLong(Exception):
    pass


class Proxy:
    def __init__(self, upstream, log_dir, timeout=1800, max_prompt_chars=None):
        self.upstream, self.timeout = upstream.rstrip("/"), timeout
        self.max_prompt_chars = max_prompt_chars  # Practice-2 M3 stage 0: a 30k-token prompt OOMed Metal and killed the server, so long prompts are refused
        self.log_dir = Path(log_dir)
        (self.log_dir / "tools").mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.seq = {}
        self._model = None
        self.httpd = None

    def upstream_model(self):
        """mlx_lm.server maps "default_model" to its --model (and --adapter-path). Not the first /v1/models id: that endpoint lists every model in the
        HF cache, and on the M1 a stray Qwen3.5-0.8B came first, so the server loaded Qwen on the fly and 18 pilot tries ran on the wrong model."""
        return self._model or "default_model"

    def upstream_chat(self, body):
        req = urllib.request.Request(self.upstream + "/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.load(r)

    def log(self, key, rec, tools):
        h = rec["tools_hash"]
        with self.lock:
            if tools and not (self.log_dir / "tools" / f"{h}.json").exists():
                (self.log_dir / "tools" / f"{h}.json").write_text(json.dumps(tools))
            rec["seq"] = self.seq[key] = self.seq.get(key, -1) + 1
            with open(self.log_dir / f"try_{safe_key(key)}.jsonl", "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def complete(self, body, key_hint=None):
        """-> (response dict, key). Raises urllib errors on upstream failure."""
        t0 = time.time()
        messages = body.get("messages") or []
        key = key_hint or first_user_key(messages)
        tools = fix_tools(body.get("tools"))
        if self.max_prompt_chars and len(json.dumps(messages)) + len(json.dumps(tools or [])) > self.max_prompt_chars:
            raise ContextTooLong(f"{CONTEXT_ERR}: prompt over {self.max_prompt_chars} characters")
        up = {"model": self.upstream_model(), "messages": map_messages(messages), "stream": False, "stop": [STOP]}
        user_stop = body.get("stop")
        if user_stop:
            up["stop"] = [STOP] + ([user_stop] if isinstance(user_stop, str) else list(user_stop))
        if tools:
            up["tools"] = tools
        mt = body.get("max_tokens") or body.get("max_completion_tokens")
        if mt:
            up["max_tokens"] = mt
        for k in PASS_PARAMS:
            if body.get(k) is not None:
                up[k] = body[k]
        r = self.upstream_chat(up)
        ch = (r.get("choices") or [{}])[0]
        m = ch.get("message") or {}
        text = m.get("content") or ""
        if m.get("tool_calls") and OPEN_BLOCK not in text and OPEN_CALL not in text:  # an upstream that did parse (newer mlx_lm): keep its calls
            calls_up = [{"name": tc["function"]["name"], "arguments": _loads(tc["function"].get("arguments"))} for tc in m["tool_calls"]]
            resp, calls = build_response("", tools, r.get("usage") or {}, r.get("model") or up["model"])
            resp["choices"][0]["message"] = {"role": "assistant", "content": text or None, "tool_calls": to_openai_calls(calls_up)}
            resp["choices"][0]["finish_reason"] = "tool_calls"
            calls = calls_up
        else:
            if (OPEN_BLOCK in text or OPEN_CALL in text) and STOP not in text:
                text = text + STOP
            resp, calls = build_response(text, tools, r.get("usage") or {}, r.get("model") or up["model"])
            if ch.get("finish_reason") == "length" and not calls:
                resp["choices"][0]["finish_reason"] = "length"
        self.log(key, {"ts": round(t0, 3), "key": key, "request_messages": messages, "tools_hash": tools_hash(tools) if tools else None,
                       "completion_text": text, "tool_calls": calls, "response_message": resp["choices"][0]["message"], "finish_reason": resp["choices"][0]["finish_reason"],
                       "usage": r.get("usage"), "latency_s": round(time.time() - t0, 3), "upstream_model": up["model"],
                       "params": {k: up[k] for k in ("max_tokens", *PASS_PARAMS) if k in up}}, tools)
        return resp, key

    def make_server(self, port, host="127.0.0.1"):
        proxy = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def _send(self, code, obj):
                d = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(d)))
                self.end_headers()
                self.wfile.write(d)

            def _route(self):
                m = re.match(r"^/t/([^/]+)(/.*)$", self.path.split("?")[0])
                return (m.group(1), m.group(2)) if m else (None, self.path.split("?")[0])

            def do_GET(self):
                _, path = self._route()
                if path in ("/v1/models", "/models"):
                    return self._send(200, {"object": "list", "data": [{"id": "k2", "object": "model", "created": 0, "owned_by": "k2_proxy"}]})
                if path == "/health":
                    return self._send(200, {"status": "ok"})
                self._send(404, {"error": {"message": "not found"}})

            def do_POST(self):
                pkey, path = self._route()
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n) if n else b""
                if path not in ("/v1/chat/completions", "/chat/completions"):
                    return self._send(404, {"error": {"message": "not found"}})
                try:
                    body = json.loads(raw)
                except ValueError:
                    return self._send(400, {"error": {"message": "bad json"}})
                key = self.headers.get("X-Practice-Try") or pkey
                try:
                    resp, _ = proxy.complete(body, key)
                except ContextTooLong as e:
                    return self._send(400, {"error": {"message": str(e), "code": CONTEXT_ERR}})
                except urllib.error.HTTPError as e:
                    return self._send(e.code, {"error": {"message": f"upstream {e.code}: {e.read()[:500].decode(errors='replace')}"}})
                except Exception as e:  # noqa: BLE001
                    return self._send(502, {"error": {"message": f"upstream failed: {e}"}})
                if not body.get("stream"):
                    return self._send(200, resp)
                inc = bool((body.get("stream_options") or {}).get("include_usage"))
                data = "".join(f"data: {c}\n\n" for c in sse_chunks(resp, inc)).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        class S(ThreadingHTTPServer):
            daemon_threads = True
            allow_reuse_address = True
        self.httpd = S((host, port), H)
        return self.httpd

    def start_thread(self, port=0):
        s = self.make_server(port)
        threading.Thread(target=s.serve_forever, daemon=True).start()
        return s.server_address[1]

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()


def _loads(a):
    try:
        v = json.loads(a) if isinstance(a, str) else a
        return v if isinstance(v, dict) else {}
    except ValueError:
        return {}


def read_try_log(log_dir, key):
    """-> list of logged calls for a try key, in order (tools resolved from the tools store)."""
    f = Path(log_dir) / f"try_{safe_key(key)}.jsonl"
    if not f.exists():
        return []
    out = []
    for line in f.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            th = r.get("tools_hash")
            tf = Path(log_dir) / "tools" / f"{th}.json"
            r["tools"] = json.loads(tf.read_text()) if th and tf.exists() else []
            out.append(r)
    out.sort(key=lambda r: r.get("seq", 0))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8095)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--upstream", default="http://127.0.0.1:18081")
    ap.add_argument("--log", required=True)
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args(argv)
    p = Proxy(a.upstream, a.log, a.timeout)
    s = p.make_server(a.port, a.host)
    print(f"k2_proxy on http://{a.host}:{a.port}/v1 -> {a.upstream}, logs in {a.log}", flush=True)
    try:
        s.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
