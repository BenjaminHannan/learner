#!/usr/bin/env python3
"""rd-371 verifier training rows, built by plain code from the reader's own (agreed) training data.

yes: every writable gold fact (mode ASSERT/CORRECT, owner not "we") that passes the structural check.
no:  made from the same turn, each passing the structural check and matching no gold writable fact:
     swap      owner and value swapped (owner not "me")
     value     another fact's value put on this fact
     owner     another fact's owner or value used as owner
     rel       another relation (from another fact in the turn, else from the table, never a near-synonym)
     mode      a gold fact in a non-saving mode (PLAN, SUPPOSE, REPORTED, NEGATED, QUESTION, CHECK, UNCLEAR) shown as ASSERT
     we_me     a gold "we" fact shown with owner "me"
Positives are capped at --cap per source; negatives (from the kept turns, round-robin over kinds) at the positives' count. 5% of turns (by id hash) go to dev (loss only).
No DEV bank, panel, bank A/B, LoCoMo or LongMemEval text: input is the reader's train.jsonl only.
python claude_rd371_data.py --reader-train WORK/data/train.jsonl --out WORK/vdata [--seed 371]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from claude_lis300_common import parse_frame  # noqa: E402
from claude_lis300_compiler import REL_NAMES, check_fact  # noqa: E402
from claude_rd371_common import build_vprompt, split_reader_prompt  # noqa: E402

SAVE = {"ASSERT", "CORRECT"}
NOSAVE = {"PLAN", "SUPPOSE", "REPORTED", "NEGATED", "QUESTION", "CHECK", "UNCLEAR"}
SYN = [{"city", "hometown", "work_location", "country_of_origin", "country", "residence", "place_of_birth"},
       {"job", "occupation", "profession", "role", "title"},
       {"parent", "mother", "father"}, {"sibling", "sister", "brother"}, {"spouse", "wife", "husband", "partner"},
       {"child", "son", "daughter"}, {"pet", "dog", "cat", "rabbit", "hamster", "parrot", "horse"},
       {"school", "university", "college"}, {"employer", "company", "workplace"},
       {"favorite_food", "favourite_food"}, {"hobby", "interest", "sport"}]


def norm(x):
    return " ".join(str(x or "").lower().split())


def key(f):
    return (norm(f.get("owner")), f.get("rel"), norm(f.get("value")))


def near(a, b):
    return a == b or any(a in s and b in s for s in SYN)


def negatives(facts, turn, prev, rng):
    gold = [f for f in facts if isinstance(f, dict)]
    W = [f for f in gold if f.get("mode") in SAVE and norm(f.get("owner")) != "we"]
    gold_keys = {key(f) for f in W}
    names = {str(f.get("owner")) for f in gold if norm(f.get("owner")) not in ("me", "we")} | \
            {str(f.get("value")) for f in gold if str(f.get("value", ""))[:1].isupper()}
    out = []

    def add(f, kind):
        f = dict(f, mode=f.get("mode") if f.get("mode") in SAVE else "ASSERT")
        f.pop("old", None)
        if key(f) in gold_keys or check_fact(f, turn, prev) is not None:
            return
        out.append((f, kind))

    for f in W:
        if norm(f.get("owner")) != "me":
            add(dict(f, owner=f.get("value"), value=f.get("owner")), "swap")
        others = [g for g in W if g is not f and norm(g.get("value")) != norm(f.get("value"))]
        if others:
            add(dict(f, value=rng.choice(others).get("value")), "value")
        cands = [n for n in names if norm(n) != norm(f.get("owner")) and norm(n) != norm(f.get("value"))]
        if cands:
            add(dict(f, owner=rng.choice(sorted(cands))), "owner")
        rels = [g.get("rel") for g in W if not near(g.get("rel"), f.get("rel"))]
        if not rels:
            rels = [r for r in sorted(REL_NAMES) if not near(r, f.get("rel"))]
        add(dict(f, rel=rng.choice(rels)), "rel")
    for f in gold:
        if f.get("mode") in NOSAVE:
            add(dict(f, mode="ASSERT"), "mode")
        if norm(f.get("owner")) == "we" and f.get("mode") in SAVE:
            add(dict(f, owner="me"), "we_me")
    return W, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reader-train", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=371)
    ap.add_argument("--cap", type=int, default=8000, help="max positives per source (o0b is synthetic and huge)")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    pos, neg = defaultdict(list), defaultdict(list)
    seen = set()
    c = Counter()
    for line in Path(a.reader_train).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        sp = split_reader_prompt(r["prompt"])
        fr = parse_frame(r["target"])
        if sp is None or not isinstance(fr, dict):
            c["skipped"] += 1
            continue
        prev, turn = sp
        tkey = (turn, prev)
        if tkey in seen:  # the reader data repeats rows (x4); one copy each here
            continue
        seen.add(tkey)
        dev = int(hashlib.sha256(turn.encode()).hexdigest(), 16) % 20 == 0
        W, N = negatives(fr.get("facts") or [], turn, prev, rng)
        src = r.get("src", "?")
        for f in W:
            if check_fact(f, turn, prev) is None:
                pos[src].append((dev, turn, prev, f, "yes", "pos"))
        for f, kind in N:
            neg[src].append((dev, turn, prev, f, "no", kind))
    rows = []
    for src in sorted(pos):
        P, Nn = pos[src], neg[src]
        rng.shuffle(P)
        P = P[: a.cap]
        turns = {(x[1], x[2]) for x in P}
        by_kind = defaultdict(list)
        for x in Nn:
            if (x[1], x[2]) in turns or x[5] in ("mode", "we_me"):
                by_kind[x[5]].append(x)
        for v in by_kind.values():
            rng.shuffle(v)
        Nn, k = [], 0
        while len(Nn) < len(P) and any(by_kind.values()):  # round-robin over kinds
            kinds = sorted(kk for kk, v in by_kind.items() if v)
            Nn.append(by_kind[kinds[k % len(kinds)]].pop())
            k += 1
        rows += P + Nn
        c[f"{src}:yes"] += len(P)
        c[f"{src}:no"] += len(Nn)
        for x in Nn:
            c["no:" + x[5]] += 1
    rng.shuffle(rows)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "train.jsonl", "w", encoding="utf-8") as tr, open(out / "dev.jsonl", "w", encoding="utf-8") as dv:
        for n, (dev, turn, prev, f, lab, kind) in enumerate(rows):
            row = {"id": f"v371-{n:06d}", "prompt": build_vprompt(turn, prev, f), "target": lab,
                   "src": kind, "family": "dev" if dev else "train"}
            (dv if dev else tr).write(json.dumps(row, ensure_ascii=False) + "\n")
            c["dev" if dev else "train"] += 1
    print(json.dumps(dict(sorted(c.items())), indent=1))


if __name__ == "__main__":
    main()
