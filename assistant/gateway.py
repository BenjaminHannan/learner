#!/usr/bin/env python3
"""OpenAI-compatible gateway in front of two mlx_lm.server processes.

- Maps client model ids (qwen36-auto, qwen36, qwen36-fast, k2-helper) to an upstream.
- qwen36-auto asks the big model (quick judge call) how hard to think, once per user turn.
- Always sends model="default_model" upstream (mlx_lm.server would otherwise
  try to LOAD whatever id it is given).
- Streams SSE straight through, renaming delta.reasoning -> reasoning_content.
- Records every completed chat in a diary (raw JSONL + SQLite FTS5 index).
Stdlib only.
"""
import argparse
import collections
import datetime
import hashlib
import http.client
import json
import os
import queue
import re
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

MODEL_IDS = ["qwen36-auto", "qwen36", "qwen36-fast", "k2-helper"]
BIG_MAX, SMALL_MAX = 8192, 2048
AUTO_CACHE_MAX = 500
JUDGE_TIMEOUT = 20
JUDGE_PROMPT = (
    "(Internal check, not from Ben.) Before answering, rate how much careful step-by-step "
    "thinking the request above needs. Reply with one digit only: 0 = none (chat, simple "
    "fact, a simple tool step), 1 = some, 2 = a lot (math, multi-step planning, debugging, "
    "tricky reasoning).")
CHAT_PATHS = ("/v1/chat/completions", "/chat/completions")


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def text_of(content):
    """Message content may be a string or a list of {type:text,text} parts."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for p in content:
            if isinstance(p, str):
                out.append(p)
            elif isinstance(p, dict) and p.get("type", "text") == "text":
                out.append(p.get("text") or "")
        return "\n".join(out)
    return ""


def sha(obj):
    """sha256 of canonical JSON."""
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def http_get(url, path, timeout):
    """GET url+path; returns (status, body bytes). Raises OSError on failure."""
    u = urlparse(url)
    conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=timeout)
    try:
        conn.request("GET", path)
        r = conn.getresponse()
        return r.status, r.read()
    finally:
        conn.close()


# ---------------------------------------------------------------- diary

class Diary:
    """Background writer: raw JSONL + blobs + SQLite FTS5. Never raises."""

    def __init__(self, root):
        self.root = Path(root).expanduser()
        self.raw = self.root / "raw"
        self.blobs = self.raw / "blobs"
        self.db = None
        self.q = queue.Queue()
        threading.Thread(target=self._run, daemon=True).start()

    def submit(self, rec, blobs, row):
        self.q.put((rec, blobs, row))

    def flush(self):
        self.q.join()

    def _run(self):
        while True:
            item = self.q.get()
            try:
                self._write(*item)
            except Exception as e:  # never kill the writer
                log("diary: write failed:", repr(e))
            finally:
                self.q.task_done()

    def _write(self, rec, blobs, row):
        self.blobs.mkdir(parents=True, exist_ok=True)
        try:
            for h, obj in blobs.items():  # write-once, deduplicated by hash
                p = self.blobs / (h + ".json")
                if not p.exists():
                    tmp = p.with_suffix(".tmp")
                    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
                    os.replace(tmp, p)
            day = rec["ts"][:10]
            with open(self.raw / (day + ".jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception as e:
            log("diary: raw write failed:", repr(e))
        try:
            if row:
                self._index(row)
        except Exception as e:
            log("diary: index write failed:", repr(e))

    def _index(self, row):
        if self.db is None:
            db = sqlite3.connect(str(self.root / "diary.sqlite"), timeout=5)
            db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS turns USING fts5("
                "text, user_text UNINDEXED, assistant_text UNINDEXED, title UNINDEXED, "
                "conv_id UNINDEXED, model UNINDEXED, ts UNINDEXED, date UNINDEXED, "
                "tokenize='porter unicode61')")
            db.commit()
            self.db = db
        self.db.execute(
            "INSERT INTO turns(text,user_text,assistant_text,title,conv_id,model,ts,date) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (row["text"], row["user"], row["assistant"], row["title"],
             row["conv_id"], row["model"], row["ts"], row["date"]))
        self.db.commit()


# ---------------------------------------------------------------- streaming helpers

class Assembler:
    """Rebuilds the full assistant reply from stream deltas."""

    def __init__(self):
        self.content, self.reasoning, self.tcs = [], [], {}
        self.finish = None
        self.usage = None
        self.first_t = None

    def feed(self, chunk):
        if chunk.get("usage"):
            self.usage = chunk["usage"]
        for ch in chunk.get("choices") or []:
            d = ch.get("delta") or {}
            got = False
            if d.get("content"):
                self.content.append(d["content"])
                got = True
            r = d.get("reasoning") or d.get("reasoning_content")
            if r:
                self.reasoning.append(r)
                got = True
            for i, tc in enumerate(d.get("tool_calls") or []):
                cur = self.tcs.setdefault(tc.get("index", i), {
                    "id": None, "type": "function",
                    "function": {"name": "", "arguments": ""}})
                if tc.get("id"):
                    cur["id"] = tc["id"]
                if tc.get("type"):
                    cur["type"] = tc["type"]
                fn = tc.get("function") or {}
                if fn.get("name"):
                    cur["function"]["name"] = fn["name"]
                a = fn.get("arguments")
                if a:  # concatenate argument fragments
                    cur["function"]["arguments"] += a if isinstance(a, str) else json.dumps(a)
                got = True
            if ch.get("finish_reason"):
                self.finish = ch["finish_reason"]
            if got and self.first_t is None:
                self.first_t = time.time()

    def result(self):
        tcs = [self.tcs[k] for k in sorted(self.tcs)]
        return {"content": "".join(self.content), "reasoning": "".join(self.reasoning),
                "tool_calls": tcs}


def fix_reasoning(obj):
    """delta/message 'reasoning' -> 'reasoning_content' (in place)."""
    for ch in obj.get("choices") or []:
        for key in ("delta", "message"):
            m = ch.get(key)
            if isinstance(m, dict) and "reasoning" in m:
                r = m.pop("reasoning")
                if r is not None:
                    m.setdefault("reasoning_content", r)


# ---------------------------------------------------------------- gateway core

class Gateway:
    def __init__(self, big_url, small_url, diary_dir):
        self.big_url = big_url.rstrip("/")
        self.small_url = (small_url or "").rstrip("/")
        self.diary = Diary(diary_dir)
        self._small = (0.0, False)  # (checked_at, is_up)
        self._lock = threading.Lock()
        self._auto = collections.OrderedDict()  # key -> level; LRU of auto decisions
        self._auto_lock = threading.Lock()

    def small_up(self):
        """Probe small server's /v1/models (1 s timeout), cached 30 s."""
        if not self.small_url:
            return False
        with self._lock:
            at, up = self._small
            if time.time() - at < 30:
                return up
        try:
            up = http_get(self.small_url, "/v1/models", 1)[0] == 200
        except (OSError, http.client.HTTPException):
            up = False
        self.mark_small(up)
        return up

    def mark_small(self, up):
        with self._lock:
            self._small = (time.time(), up)

    def route(self, model):
        """-> (upstream name, url, enable_thinking or None, default max_tokens)."""
        if model == "k2-helper":
            if self.small_up():
                return ("small", self.small_url, None, SMALL_MAX)
            log("warning: small server down, k2-helper falling back to big (thinking off)")
            return ("big", self.big_url, False, BIG_MAX)
        if model == "qwen36-fast":
            return ("big", self.big_url, False, BIG_MAX)
        return ("big", self.big_url, True, BIG_MAX)  # qwen36 and unknown ids

    def auto_get(self, key):
        with self._auto_lock:
            lvl = self._auto.get(key)
            if lvl is not None:
                self._auto.move_to_end(key)
            return lvl

    def auto_put(self, key, level):
        with self._auto_lock:
            self._auto[key] = level
            self._auto.move_to_end(key)
            while len(self._auto) > AUTO_CACHE_MAX:
                self._auto.popitem(last=False)

    def judge(self, body):
        """Ask the big model how hard to think -> (level 0-2, seconds). Defaults to 1 on error."""
        t0 = time.time()
        level = 1
        try:
            b = prepare(body, False, BIG_MAX)  # same prefix (and tools) as the real request
            b["messages"] = list(b.get("messages") or []) + [
                {"role": "user", "content": JUDGE_PROMPT}]
            b.update(stream=False, temperature=0, max_tokens=2, tool_choice="none")
            for k in ("stream_options", "max_completion_tokens", "top_p", "top_k", "min_p"):
                b.pop(k, None)
            u = urlparse(self.big_url)
            conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=JUDGE_TIMEOUT)
            try:
                conn.request("POST", "/v1/chat/completions", json.dumps(b).encode(),
                             {"Content-Type": "application/json"})
                r = conn.getresponse()
                data = r.read()
            finally:
                conn.close()
            if r.status == 200:
                msg = (json.loads(data).get("choices") or [{}])[0].get("message") or {}
                m = re.search(r"\d", text_of(msg.get("content")))
                if m:
                    level = min(int(m.group()), 2)
        except Exception as e:  # timeout, refused, bad JSON ... all mean "think"
            log("auto: judge failed:", repr(e))
        return level, time.time() - t0

    def models(self):
        ids = [m for m in MODEL_IDS if m != "k2-helper" or self.small_up()]
        return {"object": "list", "data": [
            {"id": m, "object": "model", "created": 0, "owned_by": "premonition"} for m in ids]}


AUTO_FAST_RE = re.compile(r"qwen36-(?:auto|fast)")


def prepare(body, thinking, default_max):
    """Copy of the request body adjusted for mlx_lm.server. Messages untouched."""
    b = dict(body)
    b["model"] = "default_model"  # never let mlx try to load another model
    b.pop("reasoning_effort", None)
    if thinking is not None:
        ctk = dict(b.get("chat_template_kwargs") or {})
        ctk["enable_thinking"] = thinking
        b["chat_template_kwargs"] = ctk
    if b.get("max_tokens") is None:
        b["max_tokens"] = b.get("max_completion_tokens") or default_max
    # OpenCode names the model in its system prompt, so "qwen36", "qwen36-fast" and
    # "qwen36-auto" would never share a cached prefix. Use one name (same weights anyway).
    msgs = b.get("messages")
    if isinstance(msgs, list):
        fixed = []
        for m in msgs:
            if (isinstance(m, dict) and m.get("role") in ("system", "developer")
                    and isinstance(m.get("content"), str) and AUTO_FAST_RE.search(m["content"])):
                m = dict(m, content=AUTO_FAST_RE.sub("qwen36", m["content"]))
            fixed.append(m)
        b["messages"] = fixed
    return b


class Handler(BaseHTTPRequestHandler):
    server_version = "premonition-gateway"

    def log_message(self, *a):  # silence default access log
        pass

    # -- small response helpers
    def send_json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_503(self, why=""):
        log("upstream unavailable:", why)
        self.send_json(503, {"error": {
            "message": "model server not running; start it with Start Assistant",
            "type": "service_unavailable"}})

    # -- routes
    def do_GET(self):
        gw = self.server.gw
        path = self.path.split("?")[0]
        if path in ("/v1/models", "/models"):
            self.send_json(200, gw.models())
        elif path == "/health":
            try:
                code, data = http_get(gw.big_url, "/health", 3)
            except (OSError, http.client.HTTPException) as e:
                return self.send_503(repr(e))
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_json(404, {"error": {"message": "not found"}})

    def do_POST(self):
        if self.path.split("?")[0] not in CHAT_PATHS:
            return self.send_json(404, {"error": {"message": "not found"}})
        try:
            raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            body = json.loads(raw)
            assert isinstance(body, dict)
        except Exception:
            return self.send_json(400, {"error": {"message": "invalid JSON body"}})
        self.chat(body)

    def open_upstream(self, body, route_model):
        """Pick a route and connect; if small is unreachable, retry on big."""
        gw = self.server.gw
        for _ in range(2):
            name, url, thinking, dmax = gw.route(route_model)
            payload = json.dumps(prepare(body, thinking, dmax)).encode()
            u = urlparse(url)
            conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=3600)
            try:
                conn.request("POST", "/v1/chat/completions", payload,
                             {"Content-Type": "application/json"})
                return name, thinking, conn, conn.getresponse()
            except (OSError, http.client.HTTPException) as e:
                conn.close()
                if name == "small":
                    gw.mark_small(False)
                    continue
                log("upstream connect failed:", repr(e))
        return None

    def chat(self, body):
        gw = self.server.gw
        t0 = time.time()
        client_model = body.get("model") or "qwen36"
        route_model, extra = client_model, None
        if client_model == "qwen36-auto":
            route_model, extra = self.decide_auto(body)
        opened = self.open_upstream(body, route_model)
        if not opened:
            return self.send_503()
        upstream, thinking, conn, resp = opened
        asm, status, out_obj = Assembler(), "ok", None
        try:
            if resp.status != 200:  # pass upstream errors through
                data = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.getheader("Content-Type") or "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                log("upstream error", resp.status, data[:200])
                return
            if body.get("stream"):
                status = self.relay_stream(resp, asm, client_model)
            else:
                out_obj = self.relay_plain(resp, asm, client_model)
        finally:
            conn.close()
        self.record(body, client_model, upstream, thinking, asm, t0, status, out_obj, extra)

    def decide_auto(self, body):
        """qwen36-auto -> (model id to route as, diary extras). One decision per user turn."""
        gw = self.server.gw
        msgs = body.get("messages") or []
        last_user = next((m for m in reversed(msgs)
                          if isinstance(m, dict) and m.get("role") == "user"), None)
        if last_user is None:
            log("auto: no user message -> thinking off")
            return "qwen36-fast", {"auto_level": 0, "judge_s": None}
        key = sha([conv_id_of(msgs), text_of(last_user.get("content"))])
        level, judge_s = gw.auto_get(key), None
        if level is None:
            level, judge_s = gw.judge(body)
            gw.auto_put(key, level)
        think = level > 0
        log("auto: level %d -> thinking %s (%s)" % (
            level, "on" if think else "off",
            "cached" if judge_s is None else "judge %.2fs" % judge_s))
        return ("qwen36" if think else "qwen36-fast"), {
            "auto_level": level, "judge_s": None if judge_s is None else round(judge_s, 3)}

    def relay_stream(self, resp, asm, client_model):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        try:
            while True:
                line = resp.readline()
                if not line:
                    return "ok"
                self.wfile.write(self.rewrite_line(line, asm, client_model))  # unbuffered socket
        except (BrokenPipeError, ConnectionResetError):
            return "client_disconnect"
        except (OSError, http.client.HTTPException) as e:
            log("stream error:", repr(e))
            return "upstream_error"

    @staticmethod
    def rewrite_line(line, asm, client_model):
        """Parse one SSE line; rename reasoning key, echo model id."""
        if not line.startswith(b"data:"):
            return line
        payload = line[5:].strip()
        if payload == b"[DONE]":
            return line
        try:
            obj = json.loads(payload)
        except ValueError:
            return line
        if not isinstance(obj, dict):
            return line
        asm.feed(obj)
        fix_reasoning(obj)
        if "model" in obj:
            obj["model"] = client_model
        return b"data: " + json.dumps(obj, ensure_ascii=False).encode() + b"\n"

    def relay_plain(self, resp, asm, client_model):
        data = resp.read()
        obj = None
        try:
            obj = json.loads(data)
            asm.usage = obj.get("usage")
            for ch in obj.get("choices") or []:
                m = ch.get("message") or {}
                asm.content.append(text_of(m.get("content")))
                asm.reasoning.append(m.get("reasoning") or m.get("reasoning_content") or "")
                for tc in m.get("tool_calls") or []:
                    asm.tcs[len(asm.tcs)] = tc
                asm.finish = ch.get("finish_reason") or asm.finish
            fix_reasoning(obj)
            if "model" in obj:
                obj["model"] = client_model
            data = json.dumps(obj, ensure_ascii=False).encode()
        except ValueError:
            pass  # not JSON: send as is
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass
        return obj

    # -- logging + diary
    def record(self, body, client_model, upstream, thinking, asm, t0, status, out_obj,
               extra=None):
        gw = self.server.gw
        now = time.time()
        usage = asm.usage or {}
        ttft = (asm.first_t - t0) if asm.first_t else None
        ptok = usage.get("prompt_tokens")
        ctok = usage.get("completion_tokens")
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
        # a tool call arrives in one chunk at the end, so first_t ~ now; time from t0 then
        gen_time = now - (t0 if asm.tcs and not "".join(asm.content).strip() else (asm.first_t or t0))
        tps = (ctok / gen_time) if ctok and gen_time > 0 else None
        fmt = lambda v, f="%s": "-" if v is None else f % v
        log("%s %s [%s] prompt=%s cached=%s completion=%s ttft=%s %s%s" % (
            time.strftime("%H:%M:%S"), client_model, upstream, fmt(ptok), fmt(cached),
            fmt(ctok), fmt(ttft, "%.2fs"), fmt(tps, "%.1f tok/s"),
            "" if status == "ok" else " (%s)" % status))
        try:
            rec, blobs, row = build_diary(body, client_model, upstream, thinking, asm, status,
                                          now - t0, ttft, extra)
            gw.diary.submit(rec, blobs, row)
        except Exception as e:
            log("diary: build failed:", repr(e))


def conv_id_of(msgs):
    """Stable id for a conversation: system prompt + first user message."""
    sys_text = "\n".join(text_of(m.get("content")) for m in msgs
                         if isinstance(m, dict) and m.get("role") in ("system", "developer"))
    first_user = next((text_of(m.get("content")) for m in msgs
                       if isinstance(m, dict) and m.get("role") == "user"), "")
    return hashlib.sha256((sys_text + first_user).encode("utf-8")).hexdigest()[:16]


def build_diary(body, client_model, upstream, thinking, asm, status, latency, ttft, extra=None):
    """-> (jsonl record, {hash: blob}, index row or None)."""
    msgs = body.get("messages") or []
    blobs = {}
    first_user = next((text_of(m.get("content")) for m in msgs
                       if isinstance(m, dict) and m.get("role") == "user"), "")
    conv_id = conv_id_of(msgs)

    out_msgs = []
    for m in msgs:  # system content is stored once as a blob, referenced by hash
        if isinstance(m, dict) and m.get("role") in ("system", "developer"):
            h = sha(m.get("content"))
            blobs[h] = m.get("content")
            m = dict(m, content={"$blob": h})
        out_msgs.append(m)
    tools = body.get("tools")
    tools_hash = None
    if tools:
        tools_hash = sha(tools)
        blobs[tools_hash] = tools

    ts = datetime.datetime.now(datetime.timezone.utc)
    resp = asm.result()
    rec = {
        "ts": ts.isoformat(), "model": client_model, "upstream": upstream,
        "thinking": thinking, "conv_id": conv_id, "messages": out_msgs,
        "tools_hash": tools_hash,
        "sampling": {k: v for k, v in body.items() if k not in ("messages", "tools")},
        "response": resp, "finish_reason": asm.finish, "usage": asm.usage,
        "latency_s": round(latency, 3),
        "ttft_s": None if ttft is None else round(ttft, 3),
        "status": status,
    }
    rec.update(extra or {})  # auto_level, judge_s
    last = msgs[-1] if msgs else {}
    user = text_of(last.get("content")).strip() if isinstance(last, dict) and last.get("role") == "user" else ""
    asst = resp["content"].strip()
    row = None
    if user or asst:
        text = "\n".join(p for p in ("user: " + user if user else "",
                                     "assistant: " + asst if asst else "") if p)
        row = {"text": text, "user": user, "assistant": asst, "conv_id": conv_id,
               "title": re.sub(r"\s+", " ", first_user).strip()[:80],
               "model": client_model, "ts": rec["ts"], "date": rec["ts"][:10]}
    return rec, blobs, row


def make_server(big_url, small_url, port, diary_dir, host="127.0.0.1"):
    srv = ThreadingHTTPServer((host, port), Handler)
    srv.daemon_threads = True
    srv.gw = Gateway(big_url, small_url, diary_dir)
    return srv


def main():
    e = os.environ.get
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--big-url", default=e("GATEWAY_BIG_URL", "http://127.0.0.1:18080"))
    ap.add_argument("--small-url", default=e("GATEWAY_SMALL_URL", "http://127.0.0.1:18081"))
    ap.add_argument("--port", type=int, default=int(e("GATEWAY_PORT", "8090")))
    ap.add_argument("--diary-dir", default=e("DIARY_DIR", "~/learner-ops/diary"))
    a = ap.parse_args()
    srv = make_server(a.big_url, a.small_url, a.port, a.diary_dir)
    log("gateway on 127.0.0.1:%d  big=%s small=%s diary=%s" % (
        a.port, a.big_url, a.small_url, srv.gw.diary.root))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.gw.diary.flush()


if __name__ == "__main__":
    main()
