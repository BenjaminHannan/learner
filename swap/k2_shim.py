#!/usr/bin/env python3
"""OpenAI chat-completions shim for K2-Horizon on mlx_lm.server (which can't parse K2's <ifm|tool_call> format).

Renders the chat with swap/templates/k2_nothink.jinja (thinking off by default; reasoning_effort low/medium/high via
chat_template_kwargs), sends the raw prompt to mlx_lm.server's /v1/completions, and parses the xml tool-call block.

  mlx_lm.server --model <k2 mlx dir> --trust-remote-code --port 8081 &
  python swap/k2_shim.py --model <k2 mlx dir or hf id> --backend http://localhost:8081 --port 8080
"""
from __future__ import annotations

import argparse, json, re, time, urllib.request, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from transformers import AutoTokenizer

TEMPLATE = (Path(__file__).parent / "templates" / "k2_nothink.jinja").read_text()
CALLS = re.compile(r"<ifm\|tool_calls>(.*?)(?:</ifm\|tool_calls>|$)", re.S)
CALL = re.compile(r"<ifm\|tool_call>(.*?)(?:</ifm\|tool_call>|$)", re.S)
ARG = re.compile(r"<ifm\|arg_key>(.*?)</ifm\|arg_key>\s*(?:<ifm\|arg_type>(.*?)</ifm\|arg_type>\s*)?<ifm\|arg_value>(.*?)</ifm\|arg_value>", re.S)
THINK = re.compile(r"^(.*?)</ifm\|think(?:_fast|_faster)?>", re.S)


def _has_str(spec):  # schema (or any anyOf/oneOf/list-type branch of it) allows a string
    if not isinstance(spec, dict):
        return False
    t = spec.get("type")
    return t == "string" or (isinstance(t, list) and "string" in t) or any(_has_str(b) for k in ("anyOf", "oneOf") for b in spec.get(k) or [])


def arg_types(tools):
    return {t["function"]["name"]: {k: "string" if _has_str(v) else v.get("type") for k, v in (t["function"].get("parameters") or {}).get("properties", {}).items()}
            for t in tools or []}


def parse2(text, tools, thinking):
    """-> (reasoning, content, calls, truncated). truncated: think block or a tool call was cut off (incomplete calls are dropped)."""
    reasoning, trunc = None, False
    if thinking:  # the prompt opened a think block; everything up to its close tag is reasoning
        m = THINK.match(text)
        if m:
            reasoning, text = m.group(1).strip(), text[m.end():]
        else:  # never leak unterminated reasoning as content; a complete tool_calls block after it is still honoured
            trunc = True
            b = CALLS.search(text)
            reasoning, text = (text[:b.start()] if b else text).strip(), (text[b.start():] if b else "")
    types = arg_types(tools)
    calls = []
    block = CALLS.search(text)
    if block:
        body = block.group(1)
        if body.count("<ifm|tool_call>") > len(re.findall(r"<ifm\|tool_call>.*?</ifm\|tool_call>", body, re.S)):
            trunc = True  # last call has no close tag
        for c in re.findall(r"<ifm\|tool_call>(.*?)</ifm\|tool_call>", body, re.S):
            c = c.strip()
            if c.startswith("{"):  # json tool_call_format
                try:
                    j = json.loads(c); calls.append((j["name"], j.get("arguments") or {})); continue
                except Exception:
                    pass
            name = c.split("\n", 1)[0].strip()
            pairs = ARG.findall(c)
            if c.count("<ifm|arg_key>") > len(pairs):
                trunc = True; continue  # an arg_key without a closed arg_value: drop the call
            args = {}
            for k, at, v in pairs:
                k, v = k.strip(), v.strip()
                if "string" in at.strip().split("|") or types.get(name, {}).get(k) == "string":  # model's own arg_type wins; then schema
                    args[k] = v
                else:
                    try:
                        args[k] = json.loads(v)
                    except Exception:
                        args[k] = v
            calls.append((name, args))
        text = text[:block.start()]
    return reasoning, text.strip(), calls, trunc


def parse(text, tools, thinking):
    return parse2(text, tools, thinking)[:3]


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        self._send(200, {"object": "list", "data": [{"id": "m", "object": "model"}]})

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        kw = dict(req.get("chat_template_kwargs") or {})
        msgs = []
        for m in req["messages"]:
            m = dict(m)
            for tc in m.get("tool_calls") or []:
                if isinstance(tc["function"].get("arguments"), str):
                    try:
                        tc["function"]["arguments"] = json.loads(tc["function"]["arguments"])
                    except Exception:
                        pass
            msgs.append(m)
        prompt = TOK.apply_chat_template(msgs, tools=req.get("tools"), tokenize=False, add_generation_prompt=True,
                                         chat_template=TEMPLATE, **kw)
        thinking = kw.get("reasoning_effort", "none") != "none"
        body = {"prompt": prompt, "max_tokens": req.get("max_tokens") or 4096, "stop": ["<|ifm|im_end|>"],
                **{k: req[k] for k in ("temperature", "top_p") if k in req}}
        if "temperature" not in body:
            body.update(A.sampling)
        t = time.time()
        r = json.loads(urllib.request.urlopen(urllib.request.Request(A.backend + "/v1/completions", json.dumps(body).encode(),
                                                                     {"Content-Type": "application/json"}), timeout=3600).read())
        text = r["choices"][0]["text"]
        reasoning, content, calls, trunc = parse2(text, req.get("tools"), thinking)
        msg = {"role": "assistant", "content": content or None}
        if reasoning is not None:
            msg["reasoning_content"] = reasoning
        if calls:
            msg["tool_calls"] = [{"id": "call_" + uuid.uuid4().hex[:12], "type": "function",
                                  "function": {"name": n, "arguments": json.dumps(a)}} for n, a in calls]
        usage = r.get("usage") or {}
        length = trunc or r["choices"][0].get("finish_reason") == "length" or (usage.get("completion_tokens") or 0) >= body["max_tokens"]
        with open(A.log, "a") as f:
            f.write(json.dumps({"t": round(time.time() - t, 2), "usage": usage, "calls": len(calls), "raw": text[-400:]}) + "\n")
        self._send(200, {"id": "chatcmpl-" + uuid.uuid4().hex, "object": "chat.completion", "created": int(time.time()), "model": "m",
                         "choices": [{"index": 0, "message": msg, "finish_reason": "length" if length else "tool_calls" if calls else "stop"}], "usage": usage})


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True); p.add_argument("--backend", default="http://localhost:8081")
    p.add_argument("--port", type=int, default=8080); p.add_argument("--log", default="k2_shim.jsonl")
    p.add_argument("--temp", type=float, default=1.0); p.add_argument("--top-p", type=float, default=0.95)
    A = p.parse_args()
    A.sampling = {"temperature": A.temp, "top_p": A.top_p}
    TOK = AutoTokenizer.from_pretrained(A.model, trust_remote_code=True)
    ThreadingHTTPServer(("127.0.0.1", A.port), H).serve_forever()
