"""Anthropic Message Batches helpers (anthropic SDK, key from env LEARNER_ANTHROPIC_API_KEY). Nothing here runs unless a --submit / --collect
flag is given; every script has a --dry-run that only counts requests and estimates cost. Total cap for items + alias tables + grading: $5."""
from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path

from .world import FROZEN

CAP_USD = 5.00
BATCH_DISCOUNT = 0.5
PRICES = {  # $ per 1M tokens (input, output), standard rate; Batches halves it
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}
COST_FILE = FROZEN / "api_cost_estimates.json"


def est_tokens(text: str) -> int:
    return math.ceil(len(text) / 3.2) + 8  # deliberately high for unusual names


def params(model: str, system: str, user: str, max_tokens: int) -> dict:
    p = {"model": model, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": user}]}
    if model == "claude-sonnet-5-5":
        p["thinking"] = {"type": "between_tools"}  # Sonnet 5.5: thinking off is "between_tools", not "disabled" (400)
    elif model == "claude-haiku-5-5":
        p["thinking"] = {"type": "disabled"}
    return p


def estimate(reqs: list[dict], out_tokens: int, margin: float = 1.3) -> dict:
    """reqs: [{'custom_id','params'}]; out_tokens: assumed output tokens per request (max_tokens is the cap)."""
    by = {}
    for r in reqs:
        p = r["params"]
        s = est_tokens(p.get("system", "")) + sum(est_tokens(m["content"]) for m in p["messages"])
        d = by.setdefault(p["model"], {"n": 0, "in": 0, "out": 0})
        d["n"] += 1
        d["in"] += s
        d["out"] += min(out_tokens, p["max_tokens"])
    usd = 0.0
    for m, d in by.items():
        pi, po = PRICES[m]
        d["usd"] = round((d["in"] * pi + d["out"] * po) / 1e6 * BATCH_DISCOUNT * margin, 4)
        usd += d["usd"]
    return {"requests": len(reqs), "by_model": by, "usd_estimate_with_30pct_margin": round(usd, 4)}


def record_estimate(stage: str, est: dict) -> float:
    """Remember each stage's estimate; return the running total. submit() refuses when the total would exceed CAP_USD."""
    COST_FILE.parent.mkdir(parents=True, exist_ok=True)
    d = json.loads(COST_FILE.read_text()) if COST_FILE.exists() else {}
    d[stage] = est["usd_estimate_with_30pct_margin"]
    COST_FILE.write_text(json.dumps(d, indent=1))
    return sum(d.values())


def print_dry_run(stage: str, reqs: list[dict], out_tokens: int):
    est = estimate(reqs, out_tokens)
    total = record_estimate(stage, est)
    print(json.dumps({"stage": stage, **est}, indent=1))
    print(f"running total over recorded stages (cap ${CAP_USD:.2f}): ${total:.2f}")
    return est


def client():
    import anthropic
    key = os.environ.get("LEARNER_ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("LEARNER_ANTHROPIC_API_KEY is not set (the key is never on the GPU box)")
    return anthropic.Anthropic(api_key=key)


def submit(stage: str, reqs: list[dict], out_tokens: int, state: Path, limit: int | None = None) -> str:
    est = estimate(reqs[:limit] if limit else reqs, out_tokens)
    total = record_estimate(stage, est)
    if total > CAP_USD:
        raise SystemExit(f"estimated total ${total:.2f} exceeds the ${CAP_USD:.2f} cap; not submitting")
    if reqs and len({r["custom_id"] for r in reqs}) != len(reqs):
        raise SystemExit("duplicate custom_id")
    b = client().messages.batches.create(requests=reqs[:limit] if limit else reqs)
    st = json.loads(state.read_text()) if state.exists() else {}
    st.setdefault(stage, []).append({"batch_id": b.id, "n": len(reqs[:limit] if limit else reqs), "created": time.strftime("%FT%TZ", time.gmtime())})
    state.write_text(json.dumps(st, indent=1))
    print("submitted", b.id)
    return b.id


def collect(batch_id: str, wait: bool = True, poll_s: int = 60) -> dict[str, str]:
    """custom_id -> reply text (first text block); errored / expired ones map to None. Keyed by custom_id, never by position."""
    c = client()
    while True:
        b = c.messages.batches.retrieve(batch_id)
        if b.processing_status == "ended":
            break
        if not wait:
            raise SystemExit(f"batch {batch_id} is {b.processing_status}")
        time.sleep(poll_s)
    out = {}
    for r in c.messages.batches.results(batch_id):
        if r.result.type == "succeeded":
            out[r.custom_id] = next((blk.text for blk in r.result.message.content if blk.type == "text"), "")
        else:
            out[r.custom_id] = None
    return out


def parse_json(text: str | None):
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("\n") + 1:] if "\n" in t else t
    i, j = min([x for x in (t.find("{"), t.find("[")) if x >= 0] or [0]), max(t.rfind("}"), t.rfind("]"))
    try:
        return json.loads(t[i:j + 1])
    except Exception:
        return None
