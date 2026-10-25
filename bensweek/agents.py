"""Conversations (resumable state machines) and the agents that drive them."""
import copy
import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

MAX_STEPS = 25

# Rough list prices in USD per million tokens (input, output). ESTIMATE, copied from the
# claude-api skill table cached 2026-10-06; Haiku 5.5 is higher above 100K-token prompts
# (not modelled). Cache reads = 0.1x input, cache writes = 1.25x input. Batch API = 50% off.
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-8": (5.00, 25.00),
}


class Usage:
    def __init__(self):
        self.lock = threading.Lock()
        self.by_model = {}

    def add(self, model, inp=0, out=0, cache_read=0, cache_write=0, calls=1):
        with self.lock:
            u = self.by_model.setdefault(model, dict(input=0, output=0, cache_read=0, cache_write=0, calls=0))
            u["input"] += inp or 0
            u["output"] += out or 0
            u["cache_read"] += cache_read or 0
            u["cache_write"] += cache_write or 0
            u["calls"] += calls

    def merge(self, by_model):
        for m, u in by_model.items():
            self.add(m, u["input"], u["output"], u["cache_read"], u["cache_write"], u["calls"])

    def cost(self, batch=True):
        total = 0.0
        for model, u in self.by_model.items():
            pin, pout = PRICES.get(model, (0.0, 0.0))
            total += (u["input"] * pin + u["output"] * pout + u["cache_read"] * pin * 0.1
                      + u["cache_write"] * pin * 1.25) / 1e6
        return total * (0.5 if batch else 1.0)

    def to_dict(self, batch=True):
        return {"by_model": self.by_model, "estimated_cost_usd": round(self.cost(batch), 4),
                "pricing_note": "estimate from PRICES table in agents.py; batch = 50% of list" if batch else "estimate; list price"}


# ---------------------------------------------------------------- conversation

class Conversation:
    """One task chat. next_request() gives what to send; consume(response) advances it."""

    def __init__(self, conv_id, world, system, prompt, tools, kind="task", max_steps=MAX_STEPS):
        self.conv_id = conv_id
        self.world = world
        self.system = system
        self.tools = tools
        self.kind = kind
        self.max_steps = max_steps
        self.messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        self.prompt = prompt
        self.events = []
        self.steps = 0
        self.done = False
        self.error = None
        self.final_text = ""
        self.failures = 0
        self.n_tool_calls = 0

    def next_request(self):
        if self.done:
            return None
        return {"conv_id": self.conv_id, "step": self.steps, "system": self.system,
                "messages": self.messages, "tools": self.tools}

    def fail(self, msg):
        self.done = True
        self.error = msg

    def consume(self, resp):
        self.steps += 1
        text = (resp.get("text") or "").strip()
        calls = resp.get("tool_calls") or []
        msg = {"role": "assistant", "content": text}
        if calls:
            msg["tool_calls"] = [{"id": c["id"], "type": "function",
                                  "function": {"name": c["name"], "arguments": json.dumps(c["args"], ensure_ascii=False)}}
                                 for c in calls]
        if resp.get("raw") is not None:
            msg["_raw"] = resp["raw"]
        self.messages.append(msg)
        if text:
            self.events.append({"kind": "assistant", "text": text})
        if not calls:
            self.final_text = text
            last = text.rstrip().split("\n")[-1] if text else ""
            if (self.kind == "task" and last.endswith("?") and self.world.has_ask_reply
                    and self.world.asks < 2):
                self.world.asks += 1
                reply = self.world.ask_reply
                self.events.append({"kind": "ask_reply", "text": reply})
                self.messages.append({"role": "user", "content": reply})
                if self.steps >= self.max_steps:
                    self.fail("max_steps")
                return
            self.done = True
            return
        for c in calls:
            out = self.world.execute(c["name"], c["args"])
            self.n_tool_calls += 1
            self.events.append({"kind": "tool", "name": c["name"], "args": c["args"], "result": out})
            self.messages.append({"role": "tool", "tool_call_id": c["id"], "name": c["name"], "content": out})
        if self.steps >= self.max_steps:
            self.fail("max_steps")

    def transcript(self):
        return [{k: v for k, v in m.items() if k != "_raw"} for m in self.messages]


# ---------------------------------------------------------------- shared helpers

def tool_names(tools):
    return [t["function"]["name"] for t in tools]


def _loads(s):
    if isinstance(s, dict):
        return s
    try:
        v = json.loads(s) if s else {}
        return v if isinstance(v, dict) else {}
    except (ValueError, TypeError):
        return {}


def strip_think(text):
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text.strip()


def extract_text_tool_calls(content, names):
    """For models that print tool calls as text. Returns (clean_text, [calls])."""
    calls, spans = [], []

    def add(obj, span):
        if not isinstance(obj, dict):
            return False
        name = obj.get("name") or obj.get("tool")
        args = obj.get("arguments", obj.get("parameters", obj.get("args", {})))
        if name in names:
            calls.append({"name": name, "args": _loads(args)})
            spans.append(span)
            return True
        return False

    for m in re.finditer(r"<tool_call>(.*?)(?:</tool_call>|$)", content, flags=re.S):
        try:
            add(json.loads(m.group(1).strip()), m.span())
        except ValueError:
            pass
    if not calls:
        dec = json.JSONDecoder()
        i = 0
        while True:
            i = content.find("{", i)
            if i < 0:
                break
            try:
                obj, end = dec.raw_decode(content[i:])
            except ValueError:
                i += 1
                continue
            if add(obj, (i, i + end)):
                i += end
            else:
                i += 1
    clean = content
    for a, b in sorted(spans, reverse=True):
        clean = clean[:a] + clean[b:]
    clean = re.sub(r"```(?:json)?\s*```", "", clean).strip()
    return clean, calls


# ---------------------------------------------------------------- driver loop shared by simple agents

class SimpleAgent:
    """Agents that answer one request at a time (OpenAI, scripted)."""
    batch = False

    def __init__(self, concurrency=1):
        self.concurrency = concurrency
        self.usage = Usage()

    def complete(self, req):
        raise NotImplementedError

    def _drive(self, d):
        while True:
            req = d.pump()
            if req is None:
                return
            try:
                resp = self.complete(req)
            except Exception as e:
                d.conv.fail(f"agent error: {type(e).__name__}: {e}")
                continue
            d.consume(resp)

    def run(self, drivers):
        if self.concurrency <= 1 or len(drivers) <= 1:
            for d in drivers:
                self._drive(d)
        else:
            with ThreadPoolExecutor(self.concurrency) as pool:
                list(pool.map(self._drive, drivers))


# ---------------------------------------------------------------- scripted

class ScriptedAgent(SimpleAgent):
    """Replays fixed steps per task id. script = {task_id: [step, ...]}; a step is
    {"text": str, "tool_calls": [{"name":..., "args": {...}}]}. After the script ends it replies 'done'."""
    model = "scripted"

    def __init__(self, script, default_text="done"):
        super().__init__(1)
        self.script = script
        self.default_text = default_text
        self.pos = {}

    def complete(self, req):
        cid = req["conv_id"]
        i = self.pos.get(cid, 0)
        self.pos[cid] = i + 1
        steps = self.script.get(cid, [])
        step = steps[i] if i < len(steps) else {"text": self.default_text}
        calls = [{"id": f"call_{i}_{j}", "name": c["name"], "args": c.get("args", {})}
                 for j, c in enumerate(step.get("tool_calls", []))]
        return {"text": step.get("text", ""), "tool_calls": calls, "raw": None}


# ---------------------------------------------------------------- OpenAI-compatible

def to_openai_messages(messages):
    out = []
    for m in messages:
        if m["role"] == "assistant":
            d = {"role": "assistant", "content": m.get("content") or ""}
            if m.get("tool_calls"):
                d["tool_calls"] = m["tool_calls"]
            out.append(d)
        elif m["role"] == "tool":
            out.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]})
        else:
            out.append({"role": m["role"], "content": m["content"]})
    return out


class OpenAIAgent(SimpleAgent):
    def __init__(self, base_url, model, api_key=None, max_tokens=2048, temperature=0, concurrency=2,
                 timeout=900, retries=3):
        super().__init__(concurrency)
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.retries = retries

    def _post(self, body):
        data = json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        last = None
        for attempt in range(self.retries):
            try:
                rq = urllib.request.Request(self.base_url + "/chat/completions", data=data, headers=headers)
                with urllib.request.urlopen(rq, timeout=self.timeout) as r:
                    return json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                last = e
                if e.code < 500 and e.code != 429:
                    raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:300]}")
            except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError) as e:
                last = e
            time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"request failed after {self.retries} tries: {last}")

    def complete(self, req):
        body = {"model": self.model, "messages": to_openai_messages(req["messages"]), "tools": req["tools"],
                "tool_choice": "auto", "max_tokens": self.max_tokens, "temperature": self.temperature}
        r = self._post(body)
        msg = r["choices"][0]["message"]           # reasoning_content is deliberately ignored
        u = r.get("usage") or {}
        self.usage.add(self.model, u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
        text = strip_think(msg.get("content") or "")
        calls = []
        for i, tc in enumerate(msg.get("tool_calls") or []):
            fn = tc.get("function", {})
            calls.append({"id": tc.get("id") or f"call_{req['step']}_{i}", "name": fn.get("name", ""),
                          "args": _loads(fn.get("arguments"))})
        if not calls and text:
            text, found = extract_text_tool_calls(text, tool_names(req["tools"]))
            calls = [dict(c, id=f"call_{req['step']}_{i}") for i, c in enumerate(found)]
        return {"text": text, "tool_calls": calls, "raw": None}


# ---------------------------------------------------------------- Claude (Batch API lockstep)

KEEP = {"text": ("type", "text"), "tool_use": ("type", "id", "name", "input"),
        "thinking": ("type", "thinking", "signature"), "redacted_thinking": ("type", "data")}


def to_anthropic_tools(tools):
    out = [{"name": t["function"]["name"], "description": t["function"]["description"],
            "input_schema": t["function"]["parameters"]} for t in tools]
    if out:
        out[-1] = dict(out[-1], cache_control={"type": "ephemeral"})
    return out


def to_anthropic_messages(messages):
    out = []
    for m in messages:
        role = m["role"]
        if role == "system":
            continue
        if role == "user":
            out.append({"role": "user", "content": [{"type": "text", "text": m["content"] or "(empty)"}]})
        elif role == "assistant":
            blocks = copy.deepcopy(m.get("_raw"))
            if blocks is None:
                blocks = []
                if m.get("content"):
                    blocks.append({"type": "text", "text": m["content"]})
                for tc in m.get("tool_calls", []):
                    blocks.append({"type": "tool_use", "id": tc["id"], "name": tc["function"]["name"],
                                   "input": _loads(tc["function"]["arguments"])})
            if not blocks:
                blocks = [{"type": "text", "text": "(no reply)"}]
            out.append({"role": "assistant", "content": blocks})
        elif role == "tool":
            blk = {"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"] or "(empty)"}
            if out and out[-1]["role"] == "user" and out[-1]["content"][-1]["type"] == "tool_result":
                out[-1]["content"].append(blk)
            else:
                out.append({"role": "user", "content": [blk]})
    if out:
        last = out[-1]["content"][-1]
        last["cache_control"] = {"type": "ephemeral"}
    return out


def normalize_anthropic(message):
    text, calls, raw = [], [], []
    for b in message.content:
        d = b.model_dump(exclude_none=True) if hasattr(b, "model_dump") else dict(b)
        t = d.get("type")
        raw.append({k: d[k] for k in KEEP[t] if k in d} if t in KEEP else d)
        if t == "text":
            text.append(d["text"])
        elif t == "tool_use":
            calls.append({"id": d["id"], "name": d["name"], "args": d.get("input") or {}})
    return {"text": "\n".join(text), "tool_calls": calls, "raw": raw}


def get_client():
    import anthropic
    key = os.environ.get("LEARNER_ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("set LEARNER_ANTHROPIC_API_KEY")
    return anthropic.Anthropic(api_key=key)


def submit_and_wait(client, requests, poll=25, sleep=time.sleep, log=print, chunk=2000):
    """Submit Message Batches (all chunks), poll until ended, return {custom_id: result}."""
    ids = []
    for i in range(0, len(requests), chunk):
        b = client.messages.batches.create(requests=requests[i:i + chunk])
        ids.append(b.id)
        log(f"  submitted batch {b.id} ({len(requests[i:i + chunk])} requests)")
    results = {}
    for bid in ids:
        while client.messages.batches.retrieve(bid).processing_status != "ended":
            sleep(poll)
        for r in client.messages.batches.results(bid):
            results[r.custom_id] = r.result
    return results


def safe_custom_id(s):
    s = re.sub(r"[^A-Za-z0-9_-]", "_", s)
    if len(s) > 64:
        s = s[:50] + "_" + hashlib.md5(s.encode()).hexdigest()[:12]
    return s


class ClaudeBatchAgent:
    """Lockstep: every active conversation advances one model turn per Message Batch."""
    batch = True

    def __init__(self, model, live=False, client=None, max_tokens=8000, poll=25, concurrency=4,
                 sleep=time.sleep, log=print):
        self.model = model
        self.live = live
        self._client = client
        self.max_tokens = max_tokens
        self.poll = poll
        self.concurrency = concurrency
        self.sleep = sleep
        self.log = log
        self.usage = Usage()
        self.rounds = 0

    @property
    def client(self):
        if self._client is None:
            self._client = get_client()
        return self._client

    def params(self, req):
        return {"model": self.model, "max_tokens": self.max_tokens,
                "system": [{"type": "text", "text": req["system"], "cache_control": {"type": "ephemeral"}}],
                "tools": to_anthropic_tools(req["tools"]),
                "messages": to_anthropic_messages(req["messages"])}

    def _live_results(self, jobs):
        from types import SimpleNamespace as NS

        def one(item):
            cid, params = item
            try:
                return cid, NS(type="succeeded", message=self.client.messages.create(**params))
            except Exception as e:
                return cid, NS(type="errored", error=str(e))
        with ThreadPoolExecutor(self.concurrency) as pool:
            return dict(pool.map(one, jobs))

    def run(self, drivers):
        while True:
            jobs = []
            for d in drivers:
                req = d.pump()
                if req is not None:
                    jobs.append((d, safe_custom_id(f"{req['conv_id']}-s{req['step']}"), req))
            if not jobs:
                return
            self.rounds += 1
            self.log(f"[claude] round {self.rounds}: {len(jobs)} conversations")
            items = [(cid, self.params(req)) for _, cid, req in jobs]
            if self.live:
                results = self._live_results(items)
            else:
                results = submit_and_wait(self.client, [{"custom_id": c, "params": p} for c, p in items],
                                          poll=self.poll, sleep=self.sleep, log=self.log)
            for d, cid, req in jobs:
                res = results.get(cid)
                if res is not None and res.type == "succeeded":
                    msg = res.message
                    u = msg.usage
                    self.usage.add(self.model, getattr(u, "input_tokens", 0), getattr(u, "output_tokens", 0),
                                   getattr(u, "cache_read_input_tokens", 0) or 0,
                                   getattr(u, "cache_creation_input_tokens", 0) or 0)
                    d.consume(normalize_anthropic(msg))
                else:
                    d.conv.failures += 1
                    why = getattr(res, "type", "missing")
                    self.log(f"  {cid}: {why} (failure {d.conv.failures})")
                    if d.conv.failures >= 3:
                        d.conv.fail(f"batch request {why} 3 times")
