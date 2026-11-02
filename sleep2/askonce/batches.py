"""Message Batches helper: submit, poll, collect, price. The API key is read from the environment and never printed."""
import json
import os
import sys
import time

from .config import BATCH_DISCOUNT, DATA, KEY_ENV, PRICES, jdump, jload


def client():
    import anthropic
    key = os.environ.get(KEY_ENV, "").strip()
    if not key:
        raise SystemExit(f"{KEY_ENV} is not set")
    return anthropic.Anthropic(api_key=key)


def req(custom_id, model, prompt, max_tokens=8000, system=None):
    """One Batches request. No temperature/prefill (rejected by current models); effort low keeps adaptive thinking short."""
    params = {"model": model, "max_tokens": max_tokens, "output_config": {"effort": "low"},
              "messages": [{"role": "user", "content": prompt}]}
    if system:
        params["system"] = system
    return {"custom_id": custom_id, "params": params}


def run_batch(requests, label, poll_s=20, max_wait_s=3600, spend_file=None):
    """Submit all requests as one batch, wait, return ({custom_id: text}, usage dict). Spend is appended to data/spend.json."""
    c = client()
    b = c.messages.batches.create(requests=requests)
    print(f"[{label}] batch {b.id} submitted: {len(requests)} requests", flush=True)
    t0 = time.time()
    while True:
        b = c.messages.batches.retrieve(b.id)
        if b.processing_status == "ended":
            break
        if time.time() - t0 > max_wait_s:
            raise SystemExit(f"[{label}] batch {b.id} still running after {max_wait_s}s")
        time.sleep(poll_s)
    out, usage, errors = {}, {}, {}
    for r in c.messages.batches.results(b.id):
        if r.result.type == "succeeded":
            m = r.result.message
            out[r.custom_id] = "".join(bl.text for bl in m.content if bl.type == "text")
            u = usage.setdefault(m.model, [0, 0])
            u[0] += m.usage.input_tokens + (getattr(m.usage, "cache_creation_input_tokens", 0) or 0) + (getattr(m.usage, "cache_read_input_tokens", 0) or 0)
            u[1] += m.usage.output_tokens
        else:
            errors[r.custom_id] = r.result.type
    if errors:
        print(f"[{label}] {len(errors)} requests did not succeed: {sorted(set(errors.values()))}", flush=True)
    cost = cost_of(usage)
    record_spend(label, usage, cost, len(requests), len(errors), spend_file)
    print(f"[{label}] done: {len(out)} ok, est ${cost:.4f}", flush=True)
    return out, usage


def cost_of(usage):
    return sum((i * PRICES[m][0] + o * PRICES[m][1]) / 1e6 * BATCH_DISCOUNT for m, (i, o) in usage.items())


def record_spend(label, usage, cost, n, n_err, spend_file=None):
    p = spend_file or (DATA / "spend.json")
    d = jload(p) if os.path.exists(p) else {"batches": [], "total_usd": 0.0}
    d["batches"].append({"label": label, "n_requests": n, "n_errors": n_err, "usage_in_out": usage, "usd": round(cost, 5)})
    d["total_usd"] = round(sum(x["usd"] for x in d["batches"]), 5)
    jdump(p, d)


def total_spend(spend_file=None):
    p = spend_file or (DATA / "spend.json")
    return jload(p)["total_usd"] if os.path.exists(p) else 0.0


def parse_json(text):
    """Extract the first JSON object/array from a reply (tolerates code fences and chatter)."""
    t = text.strip()
    if "```" in t:
        parts = t.split("```")
        for p in parts[1::2]:
            p = p[4:] if p.startswith("json") else p
            try:
                return json.loads(p)
            except Exception:
                pass
    for o, c in (("{", "}"), ("[", "]")):
        i, j = t.find(o), t.rfind(c)
        if i != -1 and j > i:
            try:
                return json.loads(t[i:j + 1])
            except Exception:
                pass
    raise ValueError("no JSON in reply: " + t[:120])
