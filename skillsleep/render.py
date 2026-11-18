"""Render tau2 trajectories the way vLLM saw them (k2_nothink template + tau2 tool schemas) and mark the agent's own generated tokens.

Loss mask = tokens the model generated: after the generation prompt (assistant header + empty think block) up to and including <|ifm|im_end|>.
The hard-coded greeting 'Hi! How can I help you today?' (no usage record) is context, not trained.
Self-test: python3 render.py TOKENIZER_DIR   (checks the span finder against incremental prefix rendering; exits non-zero on failure)."""
import json, sys
from pathlib import Path

TEMPLATE = Path(__file__).parent / "templates" / "k2_nothink.jinja"
GEN_PREFIX = "<|ifm|im_start|>assistant\n<ifm|think>\n</ifm|think>"
END = "<|ifm|im_end|>"


def load_tok(path):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(path, trust_remote_code=True)


def to_chat(system, sim_messages):
    """tau2 messages -> OpenAI-style chat dicts (what vLLM got) + list of 'generated' flags per assistant message."""
    chat = [{"role": "system", "content": system}]; gen = []
    for m in sim_messages:
        r = m["role"]
        if r == "user":
            chat.append({"role": "user", "content": m.get("content") or ""})
        elif r == "assistant":
            d = {"role": "assistant", "content": m.get("content") or ""}
            if m.get("tool_calls"):
                d["tool_calls"] = [{"id": t.get("id") or "", "type": "function", "function": {"name": t["name"], "arguments": t.get("arguments") or {}}}
                                   for t in m["tool_calls"]]
            chat.append(d); gen.append(m.get("usage") is not None)
        elif r == "tool":
            chat.append({"role": "tool", "content": m.get("content") or "", "tool_call_id": m.get("id") or ""})
        else:
            raise ValueError("unexpected role " + r)
    return chat, gen


def apply(tok, chat, tools, gen_prompt=False):
    return tok.apply_chat_template(chat, tools=tools, chat_template=TEMPLATE.read_text(), tokenize=False, add_generation_prompt=gen_prompt)


def spans(text, n_assistant, gen):
    """Char spans (start, end) of the generated part of each flagged assistant block, found by scanning the single full render."""
    out = []; pos = 0
    for i in range(n_assistant):
        a = text.find(GEN_PREFIX, pos)
        if a < 0:
            raise ValueError("assistant block %d not found" % i)
        s = a + len(GEN_PREFIX); e = text.find(END, s)
        if e < 0:
            raise ValueError("no end token for block %d" % i)
        e += len(END); pos = e
        if gen[i]:
            out.append((s, e))
    return out


def encode(tok, text, sp):
    enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    ids = enc["input_ids"]; mask = [0] * len(ids); starts = {s for s, _ in sp}; ends = {e for _, e in sp}
    for j, (a, b) in enumerate(enc["offset_mapping"]):
        for s, e in sp:
            if a < s < b or a < e < b:
                raise ValueError("token straddles a span edge")
            if s <= a < e and b > a:
                mask[j] = 1
    return ids, mask


def render_traj(tok, env, sim_messages):
    """-> (ids, mask) for one tau2 simulation under the NORMAL system prompt. Raises ValueError if the layout is unexpected."""
    chat, gen = to_chat(env["system"], sim_messages)
    text = apply(tok, chat, env["tools"])
    n_asst = sum(1 for c in chat if c["role"] == "assistant")
    if text.count(GEN_PREFIX) != n_asst:
        raise ValueError("assistant marker count %d != %d" % (text.count(GEN_PREFIX), n_asst))
    return encode(tok, text, spans(text, n_asst, gen))


def render_chat(tok, user, reply, truncated=False):
    """One anchor example: user prompt -> base-model reply. Returns (ids, mask) with the mask on the reply (no end token if cut off)."""
    chat = [{"role": "user", "content": user}, {"role": "assistant", "content": reply}]
    text = apply(tok, chat, None)
    s = text.find(GEN_PREFIX) + len(GEN_PREFIX); e = text.rfind(END) + (0 if truncated else len(END))
    return encode(tok, text, [(s, e)])


def selftest(tok, env, sim_messages):
    """render(prefix) + assistant tokens == full render, for every generated turn."""
    chat, gen = to_chat(env["system"], sim_messages)
    ids, mask = render_traj(tok, env, sim_messages)
    text = apply(tok, chat, env["tools"]); assert tok(text, add_special_tokens=False)["input_ids"] == ids
    idx = [i for i, c in enumerate(chat) if c["role"] == "assistant"]; k = 0; n = 0
    for gi, i in enumerate(idx):
        if not gen[gi]:
            continue
        p = apply(tok, chat[:i], env["tools"], gen_prompt=True); q = apply(tok, chat[:i + 1], env["tools"])
        assert q.startswith(p) and text.startswith(q), "prefix render not a prefix of the full render (turn %d)" % i
        pi = tok(p, add_special_tokens=False)["input_ids"]; qi = tok(q, add_special_tokens=False)["input_ids"]
        assert qi[:len(pi)] == pi and ids[:len(qi)] == qi, "tokenization not prefix-stable (turn %d)" % i
        assert all(m == 0 for m in mask[k:len(pi)]), "mask leaks into prompt (turn %d)" % i
        assert all(m == 1 for m in mask[len(pi):len(qi)]), "mask misses assistant tokens (turn %d)" % i
        k = len(qi); n += len(qi) - len(pi)
    assert sum(mask) == n, "mask has %d tokens, turns have %d" % (sum(mask), n)
    return len(ids), n


def demo_messages():
    """A tau2-style trajectory: greeting (not generated), user, tool call, tool result, reply, user, final reply."""
    u = {"usage": {"completion_tokens": 5}}
    return [{"role": "assistant", "content": "Hi! How can I help you today?"},
            {"role": "user", "content": "I'm yusuf_rossi_9620@example.com and want to return an item."},
            {"role": "assistant", "content": None, "tool_calls": [{"id": "c1", "name": "find_user_id_by_email", "arguments": {"email": "yusuf_rossi_9620@example.com"}}], **u},
            {"role": "tool", "id": "c1", "content": "yusuf_rossi_9620"},
            {"role": "assistant", "content": "Thanks, I found your account. Which order?", **u},
            {"role": "user", "content": "Order #W2378156."},
            {"role": "assistant", "content": None, "tool_calls": [{"id": "c2", "name": "get_order_details", "arguments": {"order_id": "#W2378156"}},
                                                                   {"id": "c3", "name": "get_user_details", "arguments": {"user_id": "yusuf_rossi_9620"}}], **u},
            {"role": "tool", "id": "c2", "content": '{"order_id": "#W2378156", "status": "delivered"}'},
            {"role": "tool", "id": "c3", "content": '{"user_id": "yusuf_rossi_9620"}'},
            {"role": "assistant", "content": "Your order was delivered; I can start the return. Please confirm (yes/no).", **u}]


if __name__ == "__main__":
    tok = load_tok(sys.argv[1])
    if len(sys.argv) > 2:  # env json from dump_env.py
        env = json.load(open(sys.argv[2]))
    else:
        env = {"system": "<instructions>\nYou are a retail agent.\n</instructions>\n<policy>\nBe nice.\n</policy>",
               "tools": [{"type": "function", "function": {"name": n, "description": "d", "parameters": {"type": "object", "properties": {p: {"type": "string", "description": "x"}}, "required": [p]}}}
                         for n, p in [("find_user_id_by_email", "email"), ("get_order_details", "order_id"), ("get_user_details", "user_id")]]}
    n, a = selftest(tok, env, demo_messages())
    ids, mask = render_traj(tok, env, demo_messages())
    print("RENDER SELFTEST OK tokens=%d assistant_tokens=%d" % (n, a))
    print("trained text:", repr(tok.decode([i for i, m in zip(ids, mask) if m])[:400]))
    r, m = render_chat(tok, "Say hi.", "Hi there!"); print("anchor:", repr(tok.decode([i for i, k in zip(r, m) if k])))
