#!/usr/bin/env python3
"""OpenAI-compatible gateway in front of two mlx_lm.server processes.

- Maps client model ids (qwen36-auto, qwen36, qwen36-fast, k2-helper) to an upstream.
- qwen36-auto asks the big model (quick judge call) how hard to think, once per user turn.
- Always sends model="default_model" upstream (mlx_lm.server would otherwise
  try to LOAD whatever id it is given).
- Streams SSE straight through, renaming delta.reasoning -> reasoning_content.
- Images in user messages are captioned by a small vision server (mlx_vlm.server) and replaced by
  "[Image N: caption]" text, so the big text-only model never sees image data.
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
# The judge sees only the last user message (no history, no tools): a few hundred tokens.
# Judging on the whole prompt cost a second cold prefill (M1, Oct 27: 49k-token judge, 254 s).
JUDGE_TIMEOUT = 60
JUDGE_MAX_CHARS = 2000
# OpenBot's chat titles go to k2-helper; with no small server they ran on big as a cold 5k-token
# prompt (37 s) that queued ahead of the real turn. On big they get the same tiny treatment.
TITLE_SYSTEM = ("Write a short title (three to five words) for this chat. Reply with the title "
                "only: one line, no quotes, no trailing period. For greetings use \"Greeting\".")
TITLE_MAX_CHARS, TITLE_MAX_TOKENS = 1000, 24
# Qwen3.6 model card, "Instruct (or non-thinking) mode"; used only when the client sends none.
FAST_SAMPLING = {"temperature": 0.7, "top_p": 0.8, "presence_penalty": 1.5}
REWARM_IDLE_S = 60  # after the last request ends, re-send the warm prefix (cheap when still cached)
JUDGE_PROMPT = (
    "(Internal check, not from Ben.) Rate how much careful step-by-step "
    "thinking the user's request needs. Reply with one digit only: 0 = none (chat, simple "
    "fact, a simple tool step), 1 = some, 2 = a lot (math, multi-step planning, debugging, "
    "tricky reasoning).")
CHAT_PATHS = ("/v1/chat/completions", "/chat/completions")
VISION_TIMEOUT = 60
VISION_DOWN_S = 20          # after a failed call, don't retry (and wait again) for this long
VISION_MEM_MAX, VISION_DISK_MAX = 200, 2000
VISION_PROMPT = (
    "Describe this image for someone who cannot see it. Transcribe all visible text exactly. "
    "Note layout, UI elements, numbers, people, objects.")
VISION_OFFLINE = "could not be read, the image reader is offline"


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


def image_url_of(part):
    """If a content part is an image, return (True, url-or-data-URL or None); else (False, None).
    Handles OpenAI image_url (what @ai-sdk/openai-compatible sends), Responses-style input_image,
    and {type:image} with image / url / Anthropic-style source."""
    if not isinstance(part, dict) or part.get("type") not in ("image_url", "input_image", "image"):
        return False, None
    v = part.get("image_url") or part.get("image") or part.get("url")
    if isinstance(v, dict):
        v = v.get("url")
    if not v and isinstance(part.get("source"), dict):
        src = part["source"]
        if src.get("type") == "base64" and src.get("data"):
            v = "data:%s;base64,%s" % (src.get("media_type") or "image/png", src["data"])
        else:
            v = src.get("url")
    return True, (v if isinstance(v, str) and v else None)


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
    def __init__(self, big_url, small_url, diary_dir, prefix_file=None, persist_cache=False,
                 vision_url="", vision_model=""):
        self.persist_cache = persist_cache  # ask mlx_server_persist.py to save the warmed prefix cache
        self.big_url = big_url.rstrip("/")
        self.small_url = (small_url or "").rstrip("/")
        self.diary = Diary(diary_dir)
        self.vision_url = (vision_url or "").rstrip("/")
        self.vision_model = vision_model or ""   # must equal mlx_vlm.server's --model string
        self._vlock = threading.Lock()           # one vision call at a time (also dedupes same image)
        self._vmem = collections.OrderedDict()   # image hash -> caption (LRU)
        self._vdown_until = 0.0
        self._vup = (0.0, False)
        self._vfile = self.diary.root / "vision_cache.json"
        self._vdisk = {}
        try:
            d = json.loads(self._vfile.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                self._vdisk = {k: v for k, v in d.items() if isinstance(v, str)}
        except (OSError, ValueError):
            pass
        self._small = (0.0, False)  # (checked_at, is_up)
        self._lock = threading.Lock()
        self._auto = collections.OrderedDict()  # key -> level; LRU of auto decisions
        self._auto_lock = threading.Lock()
        # Prewarm: the system prompt + tools of the last real chat, kept in mlx_lm's prompt cache
        # so a new chat only prefills its own messages (a cold OpenBot prefix is ~36k tokens).
        self.prefix_file = Path(prefix_file).expanduser() if prefix_file else None
        self._prefix = None
        if self.prefix_file and self.prefix_file.exists():
            try:
                self._prefix = json.loads(self.prefix_file.read_text())
            except ValueError:
                pass
        self._inflight = 0
        self._warm_lock = threading.Lock()
        self._warm_timer = None

    # -- prewarm
    def note_prefix(self, prepped):
        """Remember (and save) the stable prefix of a real big-model request."""
        p = extract_prefix(prepped)
        if p is None or p == self._prefix:
            return
        if self._prefix is not None:
            log("prewarm: prefix changed at char %d of system text" % first_diff(
                prefix_text(self._prefix), prefix_text(p)))
        self._prefix = p
        if self.prefix_file:
            try:
                tmp = self.prefix_file.with_suffix(".tmp")
                tmp.write_text(json.dumps(p, ensure_ascii=False))
                tmp.replace(self.prefix_file)
            except OSError as e:
                log("prewarm: save failed:", repr(e))

    def warm(self, timeout=900):
        """Send the saved prefix with max_tokens=1 so mlx_lm caches it. -> seconds, or None if skipped."""
        p = self._prefix
        if p is None or not self._warm_lock.acquire(blocking=False):
            return None
        t0 = time.time()
        try:
            b = {"model": "default_model", "messages": p["messages"] + [{"role": "user", "content": "."}],
                 "max_tokens": 1, "temperature": 0, "stream": False,
                 "chat_template_kwargs": {"enable_thinking": False}}
            if p.get("tools"):
                b["tools"] = p["tools"]
            u = urlparse(self.big_url)
            conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=timeout)
            try:
                conn.request("POST", "/v1/chat/completions", json.dumps(b).encode(),
                             {"Content-Type": "application/json"})
                r = conn.getresponse()
                data = r.read()
            finally:
                conn.close()
            usage = json.loads(data).get("usage") or {} if r.status == 200 else {}
            log("prewarm: %s prompt=%s cached=%s in %.1fs" % (
                "ok" if r.status == 200 else "HTTP %d" % r.status, usage.get("prompt_tokens"),
                (usage.get("prompt_tokens_details") or {}).get("cached_tokens"), time.time() - t0))
            if r.status == 200 and self.persist_cache:
                self.save_prefix_cache()
            return time.time() - t0
        except (OSError, http.client.HTTPException, ValueError) as e:
            log("prewarm: failed:", repr(e))
            return None
        finally:
            self._warm_lock.release()

    def save_prefix_cache(self, timeout=180):
        """Ask the persist wrapper to write the warmed system-prefix cache to disk. Never raises."""
        try:
            u = urlparse(self.big_url)
            conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=timeout)
            try:
                conn.request("POST", "/v1/internal/save_prefix", b"{}",
                             {"Content-Type": "application/json"})
                r = conn.getresponse()
                data = r.read()
            finally:
                conn.close()
            if r.status == 404:
                log("prewarm: save_prefix not available (server is not mlx_server_persist.py); "
                    "disabling cache persistence")
                self.persist_cache = False
            else:
                log("prewarm: save_prefix HTTP %d %s" % (r.status, data[:200].decode("utf-8", "replace")))
        except (OSError, http.client.HTTPException) as e:
            log("prewarm: save_prefix failed:", repr(e))

    def warm_at_start(self, wait_s=900):
        """Background: once the big server answers, warm the saved prefix."""
        def run():
            end = time.time() + wait_s
            while time.time() < end:
                try:
                    if http_get(self.big_url, "/v1/models", 2)[0] == 200:
                        break
                except (OSError, http.client.HTTPException):
                    pass
                time.sleep(2)
            if self._inflight == 0:
                self.warm()
        threading.Thread(target=run, daemon=True).start()

    def begin(self):
        with self._lock:
            self._inflight += 1
            if self._warm_timer:
                self._warm_timer.cancel()
                self._warm_timer = None

    def end(self):
        """A request finished: re-warm once things are idle (refreshes or restores the prefix)."""
        with self._lock:
            self._inflight -= 1
            if self._inflight == 0 and self._prefix is not None and REWARM_IDLE_S >= 0:
                self._warm_timer = threading.Timer(REWARM_IDLE_S, self._idle_warm)
                self._warm_timer.daemon = True
                self._warm_timer.start()

    def _idle_warm(self):
        if self._inflight == 0:
            self.warm()

    # -- images
    def vision_is_up(self):
        """Probe the vision server's /health (1 s), cached 30 s. For /health only."""
        if not self.vision_url:
            return False
        with self._lock:
            at, up = self._vup
            if time.time() - at < 30:
                return up
        try:
            up = http_get(self.vision_url, "/health", 1)[0] == 200
        except (OSError, http.client.HTTPException):
            up = False
        with self._lock:
            self._vup = (time.time(), up)
        return up

    def _vision_model_name(self):
        if self.vision_model:
            return self.vision_model
        try:  # mlx_vlm.server reloads a model whose name differs from --model, so ask it
            code, data = http_get(self.vision_url, "/health", 3)
            return json.loads(data).get("loaded_model") or "default"
        except (OSError, http.client.HTTPException, ValueError, AttributeError):
            return "default"

    def _vision_save(self):
        try:
            tmp = self._vfile.with_suffix(".tmp")
            self._vfile.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(self._vdisk, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self._vfile)
        except OSError as e:
            log("vision: cache save failed:", repr(e))

    def _vision_call(self, ref):
        """POST one image to the vision server -> caption text. Raises on any failure."""
        b = {"model": self._vision_model_name(), "stream": False, "temperature": 0,
             "max_tokens": 400, "enable_thinking": False,
             "messages": [{"role": "user", "content": [
                 {"type": "image_url", "image_url": {"url": ref}},
                 {"type": "text", "text": VISION_PROMPT}]}]}
        u = urlparse(self.vision_url)
        conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=VISION_TIMEOUT)
        try:
            conn.request("POST", "/v1/chat/completions", json.dumps(b).encode(),
                         {"Content-Type": "application/json"})
            r = conn.getresponse()
            data = r.read()
        finally:
            conn.close()
        if r.status != 200:
            raise ValueError("HTTP %d %s" % (r.status, data[:200].decode("utf-8", "replace")))
        msg = (json.loads(data).get("choices") or [{}])[0].get("message") or {}
        cap = re.sub(r"<think>.*?</think>", "", text_of(msg.get("content")), flags=re.S).strip()
        if not cap:
            raise ValueError("empty caption")
        return cap

    def caption(self, ref, h):
        """Caption for an image (cached by hash). None if the vision server can't deliver one."""
        with self._vlock:
            cap = self._vmem.get(h)
            if cap is None:
                cap = self._vdisk.get(h)
            if cap is not None:
                self._vmem[h] = cap
                self._vmem.move_to_end(h)
                while len(self._vmem) > VISION_MEM_MAX:
                    self._vmem.popitem(last=False)
                return cap
            if not self.vision_url or not ref or time.time() < self._vdown_until:
                return None
            t0 = time.time()
            try:
                cap = self._vision_call(ref)
            except Exception as e:  # refused, timeout, bad image, bad JSON ...
                log("vision: caption failed (%s): %r" % (h[:12], e))
                if not isinstance(e, ValueError):  # server unreachable or too slow
                    self._vdown_until = time.time() + VISION_DOWN_S
                return None
            log("vision: captioned %s in %.1fs (%d chars)" % (h[:12], time.time() - t0, len(cap)))
            self._vmem[h] = cap
            self._vdisk[h] = cap
            while len(self._vdisk) > VISION_DISK_MAX:
                self._vdisk.pop(next(iter(self._vdisk)))
            while len(self._vmem) > VISION_MEM_MAX:
                self._vmem.popitem(last=False)
            self._vision_save()
            return cap

    def replace_images(self, body):
        """-> (body copy with every image part in user/tool messages replaced by a text part
        "[Image N: caption]", [{n, sha256, caption|None}]). Returns (body, []) when no images."""
        msgs = body.get("messages")
        if not isinstance(msgs, list):
            return body, []
        n, records, out, changed = 0, [], [], False
        for m in msgs:
            c = m.get("content") if isinstance(m, dict) else None
            if (isinstance(m, dict) and m.get("role") in ("user", "tool") and isinstance(c, list)
                    and any(image_url_of(p)[0] for p in c)):
                parts = []
                for p in c:
                    is_img, ref = image_url_of(p)
                    if not is_img:
                        parts.append(p)
                        continue
                    n += 1
                    h = hashlib.sha256((ref or "").encode("utf-8")).hexdigest()
                    cap = self.caption(ref, h)
                    parts.append({"type": "text", "text": "[Image %d: %s]" % (n, cap or VISION_OFFLINE)})
                    records.append({"n": n, "sha256": h, "caption": cap,
                                    "source": "data" if (ref or "").startswith("data:") else "url"})
                if all(isinstance(p, dict) and p.get("type", "text") == "text" for p in parts):
                    new = "\n".join(p.get("text") or "" for p in parts)  # a plain string, so dedupe() applies
                else:
                    new = parts
                m = dict(m, content=new)
                changed = True
            out.append(m)
        if not changed:
            return body, []
        return dict(body, messages=out), records

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
            b = {"model": "default_model", "stream": False, "temperature": 0, "max_tokens": 2,
                 "chat_template_kwargs": {"enable_thinking": False},
                 "messages": [{"role": "system", "content": JUDGE_PROMPT},
                              {"role": "user", "content": judge_text(body)}]}
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
# OpenCode lists every Claude Code skill (~7k tokens on Ben's Macs) in its system prompt.
# A local model never needs them, and the extra prefill made cold turns 40-70 s on the M1.
SKILLS_RE = re.compile(
    r"Skills provide specialized instructions and workflows for specific tasks\.\n"
    r"Use the skill tool to load a skill when a task matches its description\.\n"
    r"<available_skills>.*?</available_skills>\n?", re.S)
STRIP_SKILLS = os.environ.get("ASSISTANT_STRIP_SKILLS", "1") != "0"  # config.sh switch


def last_user_bare(body):
    """The last user message without wrapper blocks (OpenBot instructions, tool catalogs)."""
    last = next((m for m in reversed(body.get("messages") or [])
                 if isinstance(m, dict) and m.get("role") == "user"), None)
    t = text_of(last.get("content")) if last else ""
    return WRAPPER_RE.sub("", t).strip() or t.strip()


def judge_text(body):
    return last_user_bare(body)[-JUDGE_MAX_CHARS:]


def title_request(prepped):
    """k2-helper on big: a few-hundred-token title prompt instead of the client's full one."""
    b = {k: v for k, v in prepped.items() if k not in (
        "tools", "tool_choice", "max_completion_tokens", "messages")}
    b.update(max_tokens=TITLE_MAX_TOKENS, temperature=0,
             chat_template_kwargs={"enable_thinking": False},
             messages=[{"role": "system", "content": TITLE_SYSTEM},
                       {"role": "user", "content": last_user_bare(prepped)[:TITLE_MAX_CHARS]}])
    return b


# OpenBot repeats its ~21k-char instructions in every user message and appends a Code Mode
# tool catalog to each one (M1, Oct 27: 6 user msgs = 166k chars for a "hi").
OBI_RE = re.compile(r"<openbot-developer-instructions>.*?</openbot-developer-instructions>\n?", re.S)
CATALOG_RE = re.compile(r"<system-update>\nThe Code Mode tool catalog has changed\..*?</system-update>\n?", re.S)
WRAPPER_RE = re.compile(r"<(openbot-developer-instructions|system-update)>.*?</\1>", re.S)
DEDUPE = os.environ.get("ASSISTANT_DEDUPE", "1") != "0"  # config.sh switch


def dedupe(msgs):
    """Drop repeated OpenBot blocks from user messages. Earlier messages keep their first copy
    so the cached history prefix stays the same from turn to turn."""
    users = [i for i, m in enumerate(msgs) if isinstance(m, dict) and m.get("role") == "user"
             and isinstance(m.get("content"), str)]
    seen, out = set(), list(msgs)
    for i in users:
        c = out[i]["content"]
        def keep_first(mo):
            if mo.group() in seen:
                return ""
            seen.add(mo.group())
            return mo.group()
        c = OBI_RE.sub(keep_first, c)
        if i != users[-1]:
            c = CATALOG_RE.sub("", c)
        if c != out[i]["content"]:
            out[i] = dict(out[i], content=c)
    return out


ENV_MARK = "\n\nToday's date:"
STABLE_SYSTEM = os.environ.get("ASSISTANT_STABLE_SYSTEM", "1") != "0"  # config.sh switch


def move_env(msgs):
    """Move OpenCode's system tail (date + <env> with the per-agent working directory) to the
    front of the first user message. mlx_lm can't reuse a cache that diverges inside the system
    message (Qwen3.6 caches can't be trimmed), so this tail made the warm prefix fit one agent
    on one day only (M1, Oct 27: new agent = cold 16k prefill, 86 s)."""
    if not (msgs and isinstance(msgs[0], dict) and msgs[0].get("role") == "system"
            and isinstance(msgs[0].get("content"), str)):
        return msgs
    c = msgs[0]["content"]
    i = c.rfind(ENV_MARK)
    if i < 0 or "<env>" not in c[i:]:
        return msgs
    u = next((k for k, m in enumerate(msgs) if isinstance(m, dict) and m.get("role") == "user"), None)
    if u is None:
        return msgs
    tail, uc = c[i:].strip(), msgs[u].get("content")
    if isinstance(uc, str):
        uc = tail + "\n\n" + uc
    elif isinstance(uc, list):
        uc = [{"type": "text", "text": tail}] + uc
    else:
        return msgs
    out = list(msgs)
    out[0] = dict(out[0], content=c[:i])
    out[u] = dict(out[u], content=uc)
    return out


OBI_OPEN, OBI_CLOSE = "<openbot-developer-instructions>\n", "\n</openbot-developer-instructions>"


def hoist_instructions(msgs):
    """Move the shared head of OpenBot's instruction block (everything before the line that
    introduces <agent_profile>, ~18k chars, the same for every agent) from the first user message
    to the end of the system message, so it is cached with the system prompt for every agent."""
    if not (msgs and isinstance(msgs[0], dict) and msgs[0].get("role") == "system"
            and isinstance(msgs[0].get("content"), str)):
        return msgs
    u = next((k for k, m in enumerate(msgs) if isinstance(m, dict) and m.get("role") == "user"), None)
    c = msgs[u].get("content") if u is not None else None
    if not isinstance(c, str):
        return msgs
    start, prof = c.find(OBI_OPEN), c.find("<agent_profile>")
    if start < 0 or prof < start:
        return msgs
    cut = c.rfind("\n", start, prof - 1) + 1
    if cut <= start + len(OBI_OPEN):
        return msgs
    out = list(msgs)
    out[0] = dict(out[0], content=out[0]["content"] + "\n\n" + OBI_OPEN
                  + c[start + len(OBI_OPEN):cut].rstrip("\n") + OBI_CLOSE)
    out[u] = dict(out[u], content=c[:start] + OBI_OPEN + c[cut:])
    return out


def strip_non_text(msgs):
    """mlx_lm.server 404s on any content part that is not type 'text'. Replace every such part
    (image, file, audio ...) with a short text placeholder; messages without them are returned as is."""
    out = []
    for m in msgs:
        c = m.get("content") if isinstance(m, dict) else None
        if isinstance(c, list) and any(isinstance(p, dict) and p.get("type", "text") != "text" for p in c):
            parts = []
            for p in c:
                if isinstance(p, dict) and p.get("type", "text") != "text":
                    kind = "image" if image_url_of(p)[0] else str(p.get("type"))
                    p = {"type": "text", "text": "[%s omitted: the model cannot read this]" % kind}
                parts.append(p)
            m = dict(m, content=parts)
        out.append(m)
    return out


def prepare(body, thinking, default_max):
    """Copy of the request body adjusted for mlx_lm.server (system names unified, OpenBot repeats deduped)."""
    b = dict(body)
    b["model"] = "default_model"  # never let mlx try to load another model
    b.pop("reasoning_effort", None)
    if thinking is not None:
        ctk = dict(b.get("chat_template_kwargs") or {})
        ctk["enable_thinking"] = thinking
        b["chat_template_kwargs"] = ctk
        if thinking is False:  # Qwen's card: non-thinking wants these, not serve.sh's thinking ones
            for k, v in FAST_SAMPLING.items():  # (missing presence_penalty -> "Hey!\n\nHey!" repeats)
                b.setdefault(k, v)
    if b.get("max_tokens") is None:
        b["max_tokens"] = b.get("max_completion_tokens") or default_max
    # OpenCode names the model in its system prompt, so "qwen36", "qwen36-fast" and
    # "qwen36-auto" would never share a cached prefix. Use one name (same weights anyway).
    msgs = b.get("messages")
    if isinstance(msgs, list):
        msgs = strip_non_text(msgs)
        fixed = []
        for m in msgs:
            if (isinstance(m, dict) and m.get("role") in ("system", "developer")
                    and isinstance(m.get("content"), str)):
                c = AUTO_FAST_RE.sub("qwen36", m["content"])
                if STRIP_SKILLS:
                    c = SKILLS_RE.sub("", c)
                if c != m["content"]:
                    m = dict(m, content=c)
            fixed.append(m)
        if DEDUPE:  # before hoisting, so later copies still match the first one
            fixed = dedupe(fixed)
        if STABLE_SYSTEM:
            fixed = hoist_instructions(move_env(fixed))
        b["messages"] = fixed
    return b


def extract_prefix(body):
    """Leading system/developer messages + tools: the part every new chat of an agent shares."""
    lead = []
    for m in body.get("messages") or []:
        if not (isinstance(m, dict) and m.get("role") in ("system", "developer")):
            break
        lead.append({"role": m["role"], "content": m.get("content")})
    if not lead or len(lead) == len(body.get("messages") or []):
        return None
    return {"messages": lead, "tools": body.get("tools") or None}


def prefix_text(p):
    return json.dumps(p, ensure_ascii=False, sort_keys=True)


def first_diff(a, b):
    n = min(len(a), len(b))
    return next((i for i in range(n) if a[i] != b[i]), n)


def request_sizes(body):
    """'system=8863 user=120 ... tools=22823' in chars (about 4 per token), for finding prompt bloat."""
    sizes = {}
    for m in body.get("messages") or []:
        if isinstance(m, dict):
            c = m.get("content")
            n = len(c) if isinstance(c, str) else len(json.dumps(c or ""))
            n += len(json.dumps(m["tool_calls"])) if m.get("tool_calls") else 0
            sizes[m.get("role", "?")] = sizes.get(m.get("role", "?"), 0) + n
    sizes["tools"] = len(json.dumps(body.get("tools") or []))
    return " ".join("%s=%d" % kv for kv in sizes.items()) + " msgs=%d" % len(body.get("messages") or [])


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
            if gw.vision_url:  # tell callers whether images can be read
                try:
                    obj = json.loads(data)
                    obj["vision"] = {"url": gw.vision_url, "up": gw.vision_is_up()}
                    data = json.dumps(obj).encode()
                except (ValueError, TypeError):
                    pass
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
            prepped = prepare(body, thinking, dmax)
            if name == "big" and route_model == "k2-helper":
                prepped = title_request(prepped)
            elif name == "big":
                gw.note_prefix(prepped)
            payload = json.dumps(prepped).encode()
            log("size: " + request_sizes(prepped) + " (before prepare: %d chars, after: %d)" % (
                len(json.dumps(body)), len(payload)))
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
        gw.begin()
        try:
            self._chat(body)
        finally:
            gw.end()

    def _chat(self, body):
        gw = self.server.gw
        t0 = time.time()
        client_model = body.get("model") or "qwen36"
        # Images first: everything after (judge, dedupe, sizes, diary) sees plain text only.
        orig = body
        body, images = gw.replace_images(body)
        if images:
            log("vision: %d image(s) in request (%d bytes raw); %d captioned" % (
                len(images), len(json.dumps(orig)), sum(1 for i in images if i["caption"])))
        route_model, extra = client_model, None
        if client_model == "qwen36-auto":
            route_model, extra = self.decide_auto(body)
        if images:
            extra = dict(extra or {}, images=images)
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


def make_server(big_url, small_url, port, diary_dir, host="127.0.0.1", prefix_file=None,
                persist_cache=False, vision_url="", vision_model=""):
    srv = ThreadingHTTPServer((host, port), Handler)
    srv.daemon_threads = True
    srv.gw = Gateway(big_url, small_url, diary_dir, prefix_file, persist_cache,
                     vision_url, vision_model)
    return srv


def main():
    e = os.environ.get
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--big-url", default=e("GATEWAY_BIG_URL", "http://127.0.0.1:18080"))
    ap.add_argument("--small-url", default=e("GATEWAY_SMALL_URL", "http://127.0.0.1:18081"))
    ap.add_argument("--port", type=int, default=int(e("GATEWAY_PORT", "8090")))
    ap.add_argument("--diary-dir", default=e("DIARY_DIR", "~/learner-ops/diary"))
    ap.add_argument("--vision-url", default=e("GATEWAY_VISION_URL", "http://127.0.0.1:18082"),
                    help="mlx_vlm.server that captions images (empty = no image reader)")
    ap.add_argument("--vision-model", default=e("GATEWAY_VISION_MODEL", ""),
                    help="the vision server's --model string (default: ask its /health)")
    ap.add_argument("--prefix-file", default=e("GATEWAY_PREFIX_FILE"),
                    help="save the last chat's system prompt + tools here and prewarm it at start")
    ap.add_argument("--persist-cache", action="store_true",
                    default=e("ASSISTANT_PERSIST_CACHE") == "1",
                    help="after a successful warm, POST /v1/internal/save_prefix to the big server "
                         "(needs assistant/mlx_server_persist.py)")
    a = ap.parse_args()
    srv = make_server(a.big_url, a.small_url, a.port, a.diary_dir, prefix_file=a.prefix_file,
                      persist_cache=a.persist_cache,
                      vision_url=a.vision_url, vision_model=a.vision_model)
    if a.prefix_file:
        srv.gw.warm_at_start()
    log("gateway on 127.0.0.1:%d  big=%s small=%s vision=%s diary=%s" % (
        a.port, a.big_url, a.small_url, a.vision_url or "off", srv.gw.diary.root))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.gw.diary.flush()


if __name__ == "__main__":
    main()
