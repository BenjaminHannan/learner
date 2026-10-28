"""Thin client for a local llama-server (OpenAI-compatible /v1/chat/completions), as Probe-5 uses it (PREREG.md).
  - started with --jinja; tools are passed natively; chat_template_kwargs {"enable_thinking": false}; any text up to and including </think> is cut from the reply
  - tool calls: the server's own message.tool_calls when it returns them, else the raw LFM3 text
        <tool_call><function=NAME><parameter=ARG>value</parameter></function></tool_call>
    parsed here (same strictness as Probe-4's parse_k2: an unknown tool, a duplicate or malformed argument anywhere -> NO calls and the text stays the content)
  - per-request LoRA scale: body["lora"] = [{"id": 0, "scale": s}] (llama.cpp: adapters not listed get scale 0.0), so ONE server started with --lora adapter.gguf serves both base (0.0) and tuned (1.0)
  - logprobs: body["logprobs"] = true, "top_logprobs" = N (llama.cpp maps it to n_probs); the reply's top candidates for the FIRST generated token come back in Reply.top_logprobs
Standard library only. CLI:  llm_server.py --url http://127.0.0.1:8080 --check      (health + that the lora field really changes the logits)"""
import argparse, json, math, os, re, sys, time, urllib.error, urllib.request
from dataclasses import dataclass, field
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5common as C  # noqa: E402
from agent_mlx import coerce, schema_types  # noqa: E402  (Probe-4's copy of vLLM's argument coercion)

P = C.P
THINK_END = "</think>"
TOPK = 20


class ServerError(RuntimeError):
    """HTTP error from the server that retrying will not fix (400: prompt longer than the context, bad field, ...)."""

    def __init__(self, status, body):
        super().__init__(f"HTTP {status}: {body[:500]}")
        self.status, self.body = status, body


def cut_think(text):
    """Drop everything up to and including the last </think> (the served base sometimes answers 'Paris</think>Paris' in no-think mode)."""
    text = text or ""
    return text.rpartition(THINK_END)[2] if THINK_END in text else text


# ---------- raw LFM3 tool-call text -> calls ----------
_FUNC_RE = re.compile(r"<function=([^<>\s]+)>(.*?)</function>", re.S)
_PARAM_RE = re.compile(r"<parameter=([^<>\s]+)>(.*?)</parameter>", re.S)
_TAG_RE = re.compile(r"</?tool_call>")


def _props(tools):
    return {t["function"]["name"]: t["function"]["parameters"].get("properties", {}) for t in tools}


def _typed(value, spec):
    """Text value of one <parameter> -> typed value, as vLLM would coerce it for that schema."""
    ty = schema_types(spec)
    if "string" in ty:
        if value.startswith("\n"):
            value = value[1:]
        if value.endswith("\n"):
            value = value[:-1]
        return coerce(value, ty)
    return coerce(value.strip(), ty)


def parse_tool_text(text, tools=None):
    """Raw model text -> dict(content, calls=[{name, arguments(dict)}]). No complete group, unknown tool, duplicate argument, or text inside a group that is not a <function> -> no calls, content = whole text.
    content = the text before and after the group(s)."""
    tools = P.TOOLS if tools is None else tools
    props = _props(tools)
    text = text or ""
    none = dict(content=text.strip(), calls=[])
    if "<function=" not in text:
        return none
    funcs = list(_FUNC_RE.finditer(text))
    if not funcs:
        return none
    start, end = funcs[0].start(), funcs[-1].end()
    m0 = text.rfind("<tool_call>", 0, start + 1)
    if m0 >= 0 and "</tool_call>" not in text[m0:start]:       # the function sits in a <tool_call> opened before it
        if text[m0 + len("<tool_call>"):start].strip():
            return none
        start = m0
    tail = re.match(r"\s*</tool_call>", text[end:])
    if tail:
        end += tail.end()
    # everything between the first and last function must be tags / whitespace
    gap, pos = "", funcs[0].start()
    for f in funcs:
        gap += text[pos:f.start()]
        pos = f.end()
    if _TAG_RE.sub("", gap).strip():
        return none
    calls = []
    for f in funcs:
        name, body = f.group(1), f.group(2)
        if name not in props:
            return none
        args, pos = {}, 0
        for p in _PARAM_RE.finditer(body):
            if body[pos:p.start()].strip():
                return none
            k = p.group(1)
            if k in args:
                return none
            args[k] = _typed(p.group(2), props[name].get(k))
            pos = p.end()
        if body[pos:].strip():
            return none
        calls.append(dict(name=name, arguments=args))
    return dict(content=(text[:start] + text[end:]).strip(), calls=calls)


def parse_native_calls(tool_calls, tools=None):
    """message.tool_calls from the server -> [{name, arguments(dict)}], or None if any call is unusable (unknown tool, arguments not a JSON object)."""
    tools = P.TOOLS if tools is None else tools
    props, out = _props(tools), []
    for tc in tool_calls or []:
        f = tc.get("function") or {}
        name, args = f.get("name"), f.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args) if args.strip() else {}
            except ValueError:
                return None
        if name not in props or not isinstance(args, dict):
            return None
        args = {k: (coerce(v.strip(), schema_types(props[name].get(k))) if isinstance(v, str) and "string" not in schema_types(props[name].get(k)) else v) for k, v in args.items()}
        out.append(dict(name=name, arguments=args))
    return out or None


# ---------- logprobs ----------
def top_from_response(choice):
    """First generated token's candidates -> [(token text, logprob)] from a /v1/chat/completions choice or a /completion reply.
    Handles choices[0].logprobs.content[0].top_logprobs (llama.cpp chat), completion_probabilities[0].top_logprobs (/completion) and the older .probs [{tok_str, prob}]."""
    lp = (choice.get("logprobs") or {}).get("content") if isinstance(choice.get("logprobs"), dict) else None
    first = lp[0] if lp else None
    if first is None:
        cp = choice.get("completion_probabilities")
        first = cp[0] if cp else None
    if first is None:
        return None
    items = first.get("top_logprobs")
    if items is not None:
        out = [(i.get("token", ""), i["logprob"]) for i in items if i.get("logprob") is not None]
    elif first.get("probs") is not None:
        out = [(i.get("tok_str", i.get("token", "")), math.log(i["prob"]) if i.get("prob", 0) > 0 else -1e30) for i in first["probs"]]
    else:
        out = []
    if first.get("token") is not None and first.get("logprob") is not None and not any(t == first["token"] for t, _ in out):
        out.append((first["token"], first["logprob"]))
    return out


def p_yes_from_top(top, topk=TOPK):
    """Pick-1's rule: among the topk candidates by logprob, tokens whose stripped, lower-cased text is yes / no -> P(yes) / (P(yes) + P(no)); None if neither is there."""
    yes = no = 0.0
    for tok, lp in sorted(top or [], key=lambda x: -x[1])[:topk]:
        w = tok.strip().lower()
        if w == "yes":
            yes += math.exp(lp)
        elif w == "no":
            no += math.exp(lp)
    return yes / (yes + no) if yes + no > 0 else None


@dataclass
class Reply:
    content: str
    calls: list
    finish_reason: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    top_logprobs: list = None
    source: str = "none"          # where the tool calls came from: native | text | none
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def hit_max(self):
        return self.finish_reason == "length"


class LlamaServer:
    def __init__(self, url=C.DEFAULT_URL, model="lfm3", timeout=900.0, lora_id=C.LORA_ID, retries=5, opener=None):
        self.url, self.model, self.timeout, self.lora_id, self.retries = url.rstrip("/"), model, timeout, lora_id, retries
        self.open = opener or urllib.request.urlopen

    # ---- plumbing
    def _post(self, path, body):
        data = json.dumps(body).encode()
        for attempt in range(self.retries):
            req = urllib.request.Request(self.url + path, data=data, headers={"Content-Type": "application/json"})
            try:
                with self.open(req, timeout=self.timeout) as r:
                    return json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                text = e.read().decode(errors="replace")
                if e.code < 500 and e.code != 429:
                    raise ServerError(e.code, text)
                err = ServerError(e.code, text)
            except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
                err = e
            if attempt == self.retries - 1:
                raise err
            time.sleep(min(2 ** attempt, 30))

    def get(self, path):
        with self.open(urllib.request.Request(self.url + path), timeout=30) as r:
            return json.loads(r.read().decode())

    def healthy(self):
        try:
            return self.get("/health").get("status") == "ok"
        except Exception:  # noqa
            return False

    def lora_field(self, scale):
        return [dict(id=self.lora_id, scale=float(scale))]

    # ---- chat
    def chat(self, messages, tools=None, *, temperature=0.7, top_p=0.95, max_tokens=512, seed=None, lora_scale=None, top_logprobs=0, extra=None):
        """One assistant turn. messages: OpenAI format (assistant tool_calls with arguments as JSON strings, tool results as role "tool"). -> Reply.
        lora_scale: None = leave the server's global scale; a number = this request only (always pass it explicitly when the server was started with --lora)."""
        body = dict(model=self.model, messages=messages, temperature=temperature, top_p=top_p, max_tokens=max_tokens, stream=False,
                    chat_template_kwargs=dict(enable_thinking=False))
        if tools:
            body["tools"] = tools
        if seed is not None:
            body["seed"] = int(seed)
        if lora_scale is not None:
            body["lora"] = self.lora_field(lora_scale)
        if top_logprobs:
            body.update(logprobs=True, top_logprobs=int(top_logprobs))
        body.update(extra or {})
        resp = self._post("/v1/chat/completions", body)
        return parse_reply(resp, tools)

    def p_yes(self, prompt, lora_scale=0.0, topk=TOPK):
        """SELF judge: the prompt is one user message (no tools, thinking off), greedy, one token; -> (P(yes), prompt tokens, candidates)."""
        r = self.chat([dict(role="user", content=prompt)], None, temperature=0.0, top_p=1.0, max_tokens=1, lora_scale=lora_scale, top_logprobs=topk)
        return p_yes_from_top(r.top_logprobs, topk), r.prompt_tokens, r.top_logprobs


def parse_reply(resp, tools=None):
    ch = resp["choices"][0]
    msg = ch.get("message") or {}
    content = cut_think(msg.get("content") or "")
    calls, source = [], "none"
    if msg.get("tool_calls"):
        calls = parse_native_calls(msg["tool_calls"], tools) or []
        source = "native" if calls else "none"
        if not calls:      # unusable native calls: keep whatever text there was, as parse_k2 would
            content = content.strip()
    else:
        out = parse_tool_text(content, tools)
        calls, content = out["calls"], out["content"]
        source = "text" if calls else "none"
    u = resp.get("usage") or {}
    return Reply(content=content.strip(), calls=calls, finish_reason=ch.get("finish_reason") or "", prompt_tokens=int(u.get("prompt_tokens", 0)),
                 completion_tokens=int(u.get("completion_tokens", 0)), top_logprobs=top_from_response(ch), source=source, raw=resp)


def check_lora(client, prompt="Reply with one word: what colour is the sky on a clear day?"):
    """Send the same greedy one-token request with the adapter at scale 0.0 (twice) and 1.0. -> (max |logprob difference| scale 1 vs 0 over the top candidates, the same for 0 vs 0 = run-to-run noise, base top, tuned top).
    diff ~ 0 means the server ignores the lora field (or no adapter is loaded): a TEST-B vs TEST-T comparison would then be meaningless."""
    tops = []
    for s in (0.0, 0.0, 1.0):
        r = client.chat([dict(role="user", content=prompt)], None, temperature=0.0, max_tokens=1, lora_scale=s, top_logprobs=TOPK)
        tops.append(dict(r.top_logprobs or []))
    gap = lambda a, b: max((abs(a[k] - b[k]) for k in set(a) & set(b)), default=0.0)    # noqa
    return gap(tops[0], tops[2]), gap(tops[0], tops[1]), tops[0], tops[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=C.DEFAULT_URL)
    ap.add_argument("--check", action="store_true", help="health + lora-scale effect + logprobs shape")
    ap.add_argument("--min-diff", type=float, default=1e-4)
    a = ap.parse_args()
    cl = LlamaServer(a.url)
    if not cl.healthy():
        print("server not healthy at", a.url)
        return 2
    if a.check:
        diff, noise, b, t = check_lora(cl)
        print(f"max |logprob(scale 1) - logprob(scale 0)| = {diff:.6f} (repeat of scale 0 differs by {noise:.6f}); candidates {len(b)}")
        if not b:
            print("no logprobs in the reply (server too old?)")
            return 3
        if diff < max(a.min_diff, 5 * noise):
            print("LoRA scale has no effect: adapter not loaded (--lora) or the request field is ignored")
            return 4
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
