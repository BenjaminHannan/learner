#!/usr/bin/env python3
"""333e DEV rehearsal of the writer change only (e1 = 333d writer, e2 = 333d writer + the chat), creative research
thread 2026-09-24. DEV data only (artifacts/claude-cre333e-dev-20260924), never the 333 panel.

The notebook is simulated with the item's own taught facts (an oracle notebook, generous to e1), and the agent's
earlier replies in the chat are the placeholder "Got it." (292t's real replies are not simulated). Same Gen338
sampling (T 0.7, top_p 0.9, 200 tokens, thinking off), 4 samples, first that passes guard333d, else FALLBACK.
Writes OUT/devgen.jsonl rows {item_id, arm, reply, guard_rejects} and OUT/judge_dev.jsonl + OUT/judge_dev_key.json
(e1/e2 shuffled per item, seed 333) for the 333 judge prompt.

  python -B scripts/claude_cre333e_devgen.py --model DIR --dev DIR --out DIR [--limit N]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_chat338_agent as C38  # noqa: E402
import claude_cre333_agent as C  # noqa: E402
import claude_cre333b_agent as CB  # noqa: E402
import claude_cre333d_agent as CD  # noqa: E402


def reply(gen, msgs, text, known):
    rej = {}
    for c in gen.sample_chat(msgs, CD.N333D):
        c = C38.trim(c)
        g = CD.guard333d(c, text, known)
        if g is None:
            return c, rej
        rej[g] = rej.get(g, 0) + 1
    return C.FALLBACK, rej


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--dev", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    items = [json.loads(x) for x in (Path(a.dev) / "items.jsonl").read_text(encoding="utf-8").splitlines() if x]
    items = [it for it in items if it["kind"] == "creative"][: a.limit or None]
    gen = C38.Gen338(share=CB.Gen333b(a.model))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows, done = [], set()
    f = out / "devgen.jsonl"
    if f.exists():
        rows = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x]
        done = {(r["item_id"], r["arm"]) for r in rows}
    for it in items:
        facts = " ".join(C._sentence(("user" if x["owner"] == "USER" else x["owner"], x["relation"], x["value"]))
                         for x in it["facts"])
        system = CD.SYSTEM333D + (" Facts the user has told you: " + facts if facts else "")
        chat = [m for t in it["turns"] for m in ({"role": "user", "content": t},
                                                  {"role": "assistant", "content": "Got it."})]
        for arm, hist in (("e1", []), ("e2", chat)):
            if (it["item_id"], arm) in done:
                continue
            known = C38._words([it["last"], facts] + [m["content"] for m in hist])
            r, rej = reply(gen, [{"role": "system", "content": system}] + hist +
                           [{"role": "user", "content": it["last"]}], it["last"], known)
            rows.append({"item_id": it["item_id"], "arm": arm, "reply": r, "guard_rejects": rej})
            with f.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rows[-1], ensure_ascii=False) + "\n")
            print(f"[devgen] {it['item_id']} {arm}", flush=True)
    by = {(r["item_id"], r["arm"]): r["reply"] for r in rows}
    rng, packets, key = random.Random(333), [], {}
    for it in items:
        pair = [("e1", by[(it["item_id"], "e1")]), ("e2", by[(it["item_id"], "e2")])]
        rng.shuffle(pair)
        key[it["item_id"]] = [pair[0][0], pair[1][0]]
        packets.append({"item_id": it["item_id"], "chat": it["turns"], "request": it["last"],
                        "about_untaught_person": it["about_untaught_person"],
                        "reply_1": pair[0][1], "reply_2": pair[1][1]})
    (out / "judge_dev.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in packets),
                                         encoding="utf-8")
    (out / "judge_dev_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(f"[devgen] done: {len(items)} items, fallbacks e1 "
          f"{sum(1 for r in rows if r['arm'] == 'e1' and r['reply'] == C.FALLBACK)}, e2 "
          f"{sum(1 for r in rows if r['arm'] == 'e2' and r['reply'] == C.FALLBACK)}")


if __name__ == "__main__":
    main()
