#!/usr/bin/env python3
"""Can the open-weights teacher label idea blurts like the blind judges? (creative research thread, 2026-09-25; DEV only)

Why: the 1B cannot pick its own good ideas (claude_blurt_selfjudge.py on the 300 blurt-1 idea blurts: its top pick was
good on 2/10 requests; chance 1.47, a good one existed on 9/10; AUC 0.691). A trained judge needs labels. Claude-written
labels may break provider terms if used to train our model; the teacher Ben approved (OpenRouter, GLM, open weights) does
not have that problem. This script asks the teacher for the same two labels the blind Opus judges gave (same rubric),
one call per request with all 30 blurts, then reports agreement with the Opus labels. No training here.

Key rules: the key is read from ~/.config/openrouter/key into memory only. Never printed, logged or written.

  python -B scripts/claude_ideajudge_teacher.py --dev artifacts/claude-cre333e-dev-20260924 \
      --blurts artifacts/claude-blurt1-dev-20260925/run/ideas_t10.jsonl \
      --labels artifacts/claude-blurt1-dev-20260925/labels/labels0.jsonl,artifacts/claude-blurt1-dev-20260925/labels/labels1.jsonl \
      --out artifacts/claude-blurt2-20260925/teacher [--model z-ai/glm-5.3-flash]
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

RUBRIC = """You are a blind judge. Below is one request: chat (earlier messages from a user to a personal assistant), request (the user's last message, asking for ideas or a short piece of writing), and 30 quick one-idea answers from a small model, numbered 0..29.

For EVERY answer decide:
- good: true if it is a genuinely usable, specific, on-topic idea for this request that a reasonable user would be glad to hear (it can be unusual or bold; wild is fine if it would actually work). False if off topic, a non-answer, a refusal, confused, incoherent, generic filler, or not something the user could act on.
- invented: true if it states AS TRUE a fact about a named person or pet (or the user) that the chat never gave.
Judge each answer on its own.

Reply with ONLY a JSON list of 30 objects in order: [{"n": 0, "good": true, "invented": false}, ...]. No other text.

"""


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def call(key, model, text, tries=4):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": text}], "temperature": 0,
                       "max_tokens": 4000, "reasoning": {"enabled": False}}).encode()
    for i in range(tries):
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body, headers={
            "Authorization": "Bearer " + key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read().decode())
            return d["choices"][0]["message"]["content"] or "", d.get("usage", {})
        except Exception as e:                        # the message of an HTTP error never carries the key
            print(f"[teacher] try {i + 1} failed: {type(e).__name__} {str(e)[:120]}", flush=True)
            time.sleep(2 ** (i + 1))
    return "", {}


def parse(txt):
    m = re.search(r"\[.*\]", txt, re.S)
    if not m:
        return None
    try:
        rows = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    out = {int(r["n"]): (bool(r["good"]), bool(r["invented"])) for r in rows if "n" in r}
    return out if len(out) == 30 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", required=True)
    ap.add_argument("--blurts", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="z-ai/glm-5.3-flash")
    a = ap.parse_args()
    key = (Path.home() / ".config" / "openrouter" / "key").read_text().strip()
    items = {it["item_id"]: it for it in load(Path(a.dev) / "items.jsonl")}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows, usage, failed = [], [], []
    for r in load(a.blurts):
        it = items[r["item_id"]]
        packet = {"chat": it["turns"], "request": it["last"],
                  "answers": [{"n": n, "text": t} for n, t in enumerate(r["blurts"])]}
        got = None
        for _ in range(2):
            txt, u = call(key, a.model, RUBRIC + json.dumps(packet, ensure_ascii=False))
            usage.append(u)
            got = parse(txt)
            if got:
                break
        if not got:
            failed.append(r["item_id"])
            print(f"[teacher] {r['item_id']} unparsed", flush=True)
            continue
        rows += [{"item_id": r["item_id"], "n": n, "good": g, "invented": v} for n, (g, v) in sorted(got.items())]
        print(f"[teacher] {r['item_id']} good {sum(g for g, _ in got.values())}/30", flush=True)
    del key
    (out / "labels_teacher.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
    ref = {(x["item_id"], x["n"]): x for p in a.labels.split(",") for x in load(p)}
    both = [(x, ref[(x["item_id"], x["n"])]) for x in rows if (x["item_id"], x["n"]) in ref]
    n = len(both)
    tp = sum(t["good"] and o["good"] for t, o in both)
    agree = sum(t["good"] == o["good"] for t, o in both)
    pt, po = sum(t["good"] for t, _ in both) / max(1, n), sum(o["good"] for _, o in both) / max(1, n)
    pe = pt * po + (1 - pt) * (1 - po)
    kappa = (agree / max(1, n) - pe) / (1 - pe) if pe < 1 else 0.0
    inv_agree = sum(t["invented"] == o["invented"] for t, o in both)
    cost = sum(float(u.get("cost", 0) or 0) for u in usage)
    rep = {"model": a.model, "requests_unparsed": failed, "blurts_compared": n,
           "teacher_good": sum(t["good"] for t, _ in both), "opus_good": sum(o["good"] for _, o in both),
           "both_good": tp, "good_agree": agree, "good_kappa": round(kappa, 3), "invented_agree": inv_agree,
           "teacher_invented": sum(t["invented"] for t, _ in both), "opus_invented": sum(o["invented"] for _, o in both),
           "calls": len(usage), "cost_usd": round(cost, 4)}
    (out / "agreement.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
