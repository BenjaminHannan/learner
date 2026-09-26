#!/usr/bin/env python3
"""k1c DEV pilot (Creative answers in chat thread, 2026-09-26): is there a better reply among the creative writer's
4 samples than the first one that passes the guards, and can a code score find it? Readable DEV items only
(artifacts/claude-k1a-dev-20260926). Not a registered run.

samples  For every DEV item, the k1a writer's exact prompt (--form W1: the chat as messages, the lead turns answered
         by twin b greedily as in claude_k1a_practice.py; --form W2: the user's earlier words in the system line)
         and the practice seed (seed*1000 + item index), so sample order and the first passing sample match the
         practice row. Saves all 4 samples: raw, trimmed, and the guard that dropped each (None = passes).
packets  One blind line per distinct (item, trimmed passing sample) not already judged in the practice batches.
score    Useful counts: first passing (= the practice reply), oracle (any passing sample useful), and the pick of each
         candidate score (fixed below before any pilot line was judged).

Candidate scores (lower = better; ties keep draw order, as claude_pick403.PickGen does):
  F   form mismatch: |numbered/bulleted items - N| when the request asks for N things, |lines - L| for a limerick (5),
      haiku (3), couplet (2) or a four-line poem (4); 0 when the request names no count or form.
  R   minus the MiniLM cosine between the sample and the user's words in this chat (request + earlier messages).
  FR  F first, then R.

  python -B scripts/claude_k1c_pilot.py samples --form W2 --items DEV/items.jsonl --model <MiniCPM5-1B> --out OUT
  python -B scripts/claude_k1c_pilot.py packets --items DEV/items.jsonl --out OUT --judged J.json
  python -B scripts/claude_k1c_pilot.py score --items DEV/items.jsonl --out OUT --verdicts V.json
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

NUMW = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "a couple of": 2, "a few": 3}
COUNT = re.compile(r"\b(\d{1,2}|two|three|four|five|six|seven|eight|nine|ten)\s+(?:\w+[\s-]){0,2}?"
                   r"(ideas|names|slogans|ways|tips|themes|gifts|suggestions|options|activities|games|titles|"
                   r"taglines|toppings|recipes|places|things|questions|jokes|puns|captions|mottos|dishes|snacks|"
                   r"songs|crafts|costumes|prompts|lines)\b", re.I)
FORMS = [(re.compile(r"\blimerick\b", re.I), 5), (re.compile(r"\bhaiku\b", re.I), 3),
         (re.compile(r"\bcouplet\b", re.I), 2),
         (re.compile(r"\b(four|4)[- ]line\b|\bquatrain\b|\bfour lines\b", re.I), 4)]
ITEM = re.compile(r"^\s*(?:\d{1,2}[.)]|[-*•])\s+\S", re.M)


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def form_target(request: str):
    for rx, n in FORMS:
        if rx.search(request):
            return ("lines", n)
    m = COUNT.search(request)
    if m:
        w = m.group(1).lower()
        return ("items", int(w) if w.isdigit() else NUMW[w])
    return None


def form_penalty(request: str, reply: str) -> int:
    t = form_target(request)
    if t is None:
        return 0
    kind, n = t
    if kind == "items":
        return abs(len(ITEM.findall(reply)) - n)
    lines = [x for x in reply.splitlines() if x.strip() and not x.strip().endswith(":")]
    return abs(len(lines) - n)


def run_samples(a):
    import torch
    import claude_chat338_agent as C38
    import claude_cre333b_agent as CB
    import claude_cre333d_agent as CD
    import claude_k1a_cre as K
    g = CB.Gen333b(a.model)
    gen = C38.Gen338(share=g)
    if a.form == "W1":
        import claude_e2e336_twin as OLD
        import claude_e2e336_twinb as TB
        OLD._CACHE[a.model] = (g.tok, g.model, g.dev)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "samples.jsonl"
    done = {r["item_id"] for r in load(path)} if path.exists() else set()
    items = load(a.items)
    with open(path, "a", encoding="utf-8") as fh:
        for i, it in enumerate(items):
            if it["item_id"] in done:
                continue
            t0 = time.time()
            text, said = it["last"], [s.strip() for s in it["turns"] if s and s.strip()]
            if a.form == "W1":
                hist = []
                with tempfile.TemporaryDirectory() as d:
                    tw = TB.Twin336b(d, a.model)
                    for lead in it["turns"]:
                        hist += [{"role": "user", "content": lead}, {"role": "assistant", "content": tw.turn(lead)[0]}]
                known = C38._words([text, ""] + [m["content"] for m in hist])
                msgs = [{"role": "system", "content": CD.SYSTEM333D}] + hist + [{"role": "user", "content": text}]
            else:
                known = C38._words([text, ""] + said)
                system = CD.SYSTEM333D + (K.SAID_K1A + " ".join(json.dumps(s, ensure_ascii=False) for s in said)
                                          if said else "")
                msgs = [{"role": "system", "content": system}, {"role": "user", "content": text}]
            torch.manual_seed(a.seed * 1000 + i)
            raw = gen.sample_chat(msgs, CD.N333D)
            samples = []
            for c in raw:
                tc = C38.trim(c)
                samples.append({"raw": c, "trimmed": tc, "guard": CD.guard333d(tc, text, known)})
            fh.write(json.dumps({"item_id": it["item_id"], "form": a.form, "samples": samples},
                                ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[k1c-pilot] {it['item_id']} {time.time() - t0:.0f}s", flush=True)


def packets(a):
    items = {it["item_id"]: it for it in load(a.items)}
    judged = json.loads(Path(a.judged).read_text(encoding="utf-8")) if a.judged else {}
    seen, pool = set(), []
    for r in load(Path(a.out) / "samples.jsonl"):
        for s in r["samples"]:
            k = (r["item_id"], s["trimmed"])
            if s["guard"] is None and k not in seen and f"{k[0]}\t{k[1]}" not in judged:
                seen.add(k)
                pool.append(k)
    random.Random(4333).shuffle(pool)
    key, pk = {}, []
    for n, (iid, rep) in enumerate(pool):
        cid = f"S{n:04d}"
        key[cid] = {"item_id": iid, "reply": rep}
        pk.append({"id": cid, "chat": list(items[iid]["turns"]), "request": items[iid]["last"], "reply": rep})
    (Path(a.out) / "packet.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pk),
                                              encoding="utf-8")
    (Path(a.out) / "key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(json.dumps({"new_lines": len(pk)}))


def score(a):
    import claude_ep382_store as EP
    items = {it["item_id"]: it for it in load(a.items)}
    verdict = json.loads(Path(a.verdicts).read_text(encoding="utf-8"))   # {"item\ttext": true/false}
    res = {"items": 0, "first": 0, "oracle": 0, "F": 0, "R": 0, "FR": 0, "no_passing": 0, "unjudged": 0}
    for r in load(Path(a.out) / "samples.jsonl"):
        it = items[r["item_id"]]
        ok = [s for s in r["samples"] if s["guard"] is None]
        res["items"] += 1
        if not ok:
            res["no_passing"] += 1
            continue
        v = [verdict.get(f"{r['item_id']}\t{s['trimmed']}") for s in ok]
        if any(x is None for x in v):
            res["unjudged"] += 1
            continue
        ctx = " ".join([it["last"]] + list(it["turns"]))
        e = EP.embed([ctx] + [s["trimmed"] for s in ok])
        cos = (e[1:] @ e[0]).tolist()
        f = [form_penalty(it["last"], s["trimmed"]) for s in ok]
        pick = {"F": min(range(len(ok)), key=lambda i: (f[i], i)),
                "R": min(range(len(ok)), key=lambda i: (-cos[i], i)),
                "FR": min(range(len(ok)), key=lambda i: (f[i], -cos[i], i))}
        res["first"] += bool(v[0])
        res["oracle"] += any(v)
        for k, i in pick.items():
            res[k] += bool(v[i])
    print(json.dumps(res))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["samples", "packets", "score"])
    ap.add_argument("--items", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--form", choices=["W1", "W2"], default="W2")
    ap.add_argument("--model", default="")
    ap.add_argument("--seed", type=int, default=4111)
    ap.add_argument("--judged", default="")
    ap.add_argument("--verdicts", default="")
    a = ap.parse_args()
    {"samples": run_samples, "packets": packets, "score": score}[a.mode](a)


if __name__ == "__main__":
    main()
