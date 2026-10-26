"""Render OpenCode tries as K2 would have seen them, for lessons: one (prompt_text, completion_text) per model call.

prompt_text = the K2 chat template (assistant/k2_nothink.jinja, with `tools`) applied to the exact request messages the proxy served, plus the generation
prompt (`<|ifm|im_start|>assistant\n<ifm|think>\n</ifm|think>`); completion_text = the raw text K2 generated for that call, closed with `<|ifm|im_end|>`.
So training on a pair trains on exactly what K2 saw and said. OpenCode prompts are long (tool descriptions alone are ~10k characters), far over the
2048-token lesson cap: use `lengths` to see how long, the cap is not changed here.
"""
import json
from pathlib import Path

from .k2_proxy import STOP, map_messages, fix_tools

IM_END = "<|ifm|im_end|>"
_HERE = Path(__file__).resolve().parent.parent
TEMPLATE_CANDIDATES = (_HERE / "assistant" / "k2_nothink.jinja", Path.home() / "learner-ops" / "assistant" / "k2_nothink.jinja", _HERE / "tests" / "k2_nothink.jinja")


def load_template(template_path=None):
    """The template file the server uses (pass its path; default: assistant/k2_nothink.jinja, then ~/learner-ops/assistant/, then the tests/ copy)."""
    for p in ([Path(template_path)] if template_path else TEMPLATE_CANDIDATES):
        if p.exists():
            return p.read_text()
    raise FileNotFoundError("k2_nothink.jinja not found; pass template_path (the file mlx_lm.server was started with)")


def _env(template_text):
    import jinja2
    from jinja2.ext import Extension
    from jinja2.sandbox import ImmutableSandboxedEnvironment

    class Generation(Extension):  # HF's `{% generation %}...{% endgeneration %}` marker: renders its body unchanged
        tags = {"generation"}

        def parse(self, parser):
            next(parser.stream)
            body = parser.parse_statements(["name:endgeneration"], drop_needle=True)
            return jinja2.nodes.CallBlock(self.call_method("_body"), [], [], body).set_lineno(0)

        def _body(self, caller):
            return caller()

    def raise_exception(msg):
        raise ValueError(msg)

    env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True, extensions=[Generation])
    env.globals["raise_exception"] = raise_exception
    env.filters["tojson"] = lambda x, **kw: json.dumps(x, ensure_ascii=False)
    return env.from_string(template_text)


_cache = {}


def render_prompt(messages, tools, tokenizer=None, template_path=None, bos=None):
    """The exact prompt text for one call. With a tokenizer, its apply_chat_template is used (as the server does); otherwise jinja2 directly."""
    tpl_text = load_template(template_path)
    msgs, tls = map_messages(messages), fix_tools(tools)
    if tokenizer is not None and hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(msgs, tools=tls or None, chat_template=tpl_text, add_generation_prompt=True, tokenize=False)
    tpl = _cache.get(tpl_text) or _cache.setdefault(tpl_text, _env(tpl_text))
    return tpl.render(messages=msgs, tools=tls or None, add_generation_prompt=True, bos_token="" if bos is None else bos)


def render_try(rec, tokenizer=None, template_path=None, tools_by_hash=None):
    """-> [(prompt_text, completion_text)] one per model call of the try. Tools come from rec['proxy_tools'] (or tools_by_hash {hash: tools})."""
    tools = {**rec.get("proxy_tools", {}), **(tools_by_hash or {})}
    out = []
    for c in rec["proxy_calls"]:
        comp = c["completion_text"]
        out.append((render_prompt(c["request_messages"], tools.get(c.get("tools_hash"), []), tokenizer, template_path), comp + IM_END))
    return out


def count_tokens(text, tokenizer):
    return len(tokenizer(text, add_special_tokens=False).input_ids)


def lengths(rec, tokenizer, template_path=None, cap=2048, tools_by_hash=None):
    """-> per call {"prompt_tokens", "completion_tokens", "total", "over_cap"} so the caller can see how far over the lesson cap the try is."""
    rows = []
    for p, c in render_try(rec, tokenizer, template_path, tools_by_hash):
        a, b = count_tokens(p, tokenizer), count_tokens(c, tokenizer)
        rows.append({"prompt_tokens": a, "completion_tokens": b, "total": a + b, "over_cap": a + b > cap})
    return rows
