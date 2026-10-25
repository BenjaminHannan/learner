"""Async OpenAI-compatible chat client + tool-call parsing (OpenAI tool_calls, LFM pythonic, <tool_call> JSON)."""
import ast, asyncio, json, re, uuid
import httpx

SAMPLING = dict(temperature=0.7, top_p=0.95, max_tokens=512)
LFM_RE = re.compile(r"<\|tool_call_start\|>(.*?)<\|tool_call_end\|>", re.S)
JSON_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.S)
MARKUP_RE = re.compile(r"<\|tool_call_start\|>.*?(?:<\|tool_call_end\|>|$)|<tool_call>.*?(?:</tool_call>|$)", re.S)
THINK_RE = re.compile(r"<think>.*?</think>", re.S)


def _val(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return ast.unparse(node)


def parse_pythonic(body):
    """'[fn(a="x", b=2), g()]' -> [{'name','arguments'}]; [] if it does not parse."""
    try:
        tree = ast.parse(body.strip(), mode="eval").body
    except SyntaxError:
        return []
    nodes = tree.elts if isinstance(tree, (ast.List, ast.Tuple)) else [tree]
    out = []
    for n in nodes:
        if isinstance(n, ast.Call):
            name = n.func.id if isinstance(n.func, ast.Name) else ast.unparse(n.func).split(".")[-1]
            out.append(dict(name=name, arguments={k.arg: _val(k.value) for k in n.keywords if k.arg}))
    return out


def parse_text_calls(text):
    calls = []
    for m in LFM_RE.finditer(text):
        calls += parse_pythonic(m.group(1))
    for m in JSON_RE.finditer(text):
        try:
            d = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        for d in d if isinstance(d, list) else [d]:
            if isinstance(d, dict) and "name" in d:
                calls.append(dict(name=d["name"], arguments=d.get("arguments", d.get("parameters", {}))))
    return calls


def strip_markup(text):
    return MARKUP_RE.sub("", text or "").strip()


def strip_planning(text):
    """For logging only. Scoring always uses the reply as returned (minus tool-call markup)."""
    return THINK_RE.sub("", text or "").strip()


def parse_message(msg):
    """OpenAI-format assistant message -> dict(content, tool_calls=[{id,name,arguments}])."""
    text = msg.get("content") or ""
    calls = []
    for tc in msg.get("tool_calls") or []:
        f = tc.get("function", {})
        a = f.get("arguments", {})
        if isinstance(a, str):
            try:
                a = json.loads(a) if a.strip() else {}
            except json.JSONDecodeError:
                pass  # keep the raw string; the sandbox reports "arguments must be a JSON object"
        calls.append(dict(id=tc.get("id") or "", name=f.get("name", ""), arguments=a))
    if not calls:
        calls = [dict(id="", **c) for c in parse_text_calls(text)]
    for c in calls:
        c["id"] = c["id"] or "call_" + uuid.uuid4().hex[:8]
    return dict(content=strip_markup(text), tool_calls=calls)


class Client:
    def __init__(self, base_url, model, api_key="none", retries=5, timeout=300):
        self.base, self.model, self.retries = base_url.rstrip("/"), model, retries
        self.http = httpx.AsyncClient(timeout=timeout, headers={"Authorization": f"Bearer {api_key}"})

    async def models(self):
        r = await self.http.get(self.base + "/models")
        r.raise_for_status()
        return r.json()

    async def chat(self, messages, tools=None):
        """-> dict(content, tool_calls, usage). Retries on HTTP errors with exponential backoff."""
        body = dict(model=self.model, messages=messages, **SAMPLING)
        if tools:
            body["tools"] = tools
        for i in range(self.retries + 1):
            try:
                r = await self.http.post(self.base + "/chat/completions", json=body)
                r.raise_for_status()
                j = r.json()
                return parse_message(j["choices"][0]["message"]) | dict(usage=j.get("usage") or {})
            except (httpx.HTTPError, KeyError, ValueError):
                if i == self.retries:
                    raise
                await asyncio.sleep(min(2 ** i, 30))
