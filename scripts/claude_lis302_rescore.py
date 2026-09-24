#!/usr/bin/env python3
"""lis-302 report-only rescore of lis-301's dev readings (no GPU, no model).

Arms over the SAME reader output (artifacts/claude-lis301-20260923/dev/dev_pred.jsonl):
  A  as built: compile_frame at T, all-or-nothing per turn (lis-310 behaviour).
  B  per-fact release: every fact that passes check_fact and has conf >= T is saved on its own;
     the rest are asked back / held. "we" still asks whose.
  C  B + confirm-at-use pending tier: facts that pass check_fact but have conf < T wait in a
     pending store that never answers; the user is asked "I think you told me X, is that right?"
     when they later ask about it. Scored assuming a truthful yes/no: a correct pending fact
     becomes CONFIRMED, a wrong one costs one question and is retracted (never saved).
Gold = the dev key through the same compiler at T=0 (lis-300 scorer's match rule).
Also: info-parity census (gold ASSERT/CORRECT facts the compiler can never write).

python3 scripts/claude_lis302_rescore.py --gold DEV --pred PRED [--train TRAIN] --out DIR
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis300_compiler import WRITE_MODES, check_fact, compile_frame  # noqa: E402
from claude_lis300_score import match  # noqa: E402

GRID = [0.0, 0.5, 0.8, 0.9, 0.95, 0.98, 0.99, 0.995, 0.999, 1.01]


def load(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def pair(facts, gold):
    """Match facts to gold one-to-one; return list of 'hit'/'broader'/None per fact."""
    used, out = set(), []
    for f in facts:
        lvl = None
        for k, g in enumerate(gold):
            if k not in used:
                lvl = match(f, g)
                if lvl:
                    used.add(k)
                    break
        out.append(lvl)
    return out


def split_facts(frame, turn, prev, conf, T):
    """Per-fact decision for arms B/C: auto (save), pending (writable but conf<T), other."""
    auto, pend = [], []
    facts = (frame or {}).get("facts") or [] if isinstance(frame, dict) else []
    for i, f in enumerate(facts):
        if not isinstance(f, dict):
            continue
        c = conf[i] if i < len(conf) else 0.0
        if check_fact(f, turn, prev) is None:
            (auto if c >= T else pend).append(f)
    return auto, pend


def rescore(gold_rows, pred, T):
    S = Counter()
    fams = Counter()
    for g in gold_rows:
        turn, prev = g["turn"], g.get("prev_reply", "")
        G = compile_frame(g["frame"], turn, prev)["write"]
        p = pred.get(g["id"], {})
        fr, conf = p.get("frame"), p.get("conf") or []
        S["gold"] += len(G)
        # arm A
        W = compile_frame(fr, turn, prev, conf=conf, threshold=T)["write"]
        m = pair(W, G)
        S["A_hit"] += sum(x == "hit" for x in m)
        wa = sum(x is None for x in m)
        S["A_wrong_facts"] += wa
        S["A_wrong_turns"] += int(wa > 0)
        # arms B and C are scored against per-fact gold: every gold fact that passes
        # check_fact on its own (all-or-nothing blocking removed on the gold side too)
        G, _ = split_facts(g["frame"], turn, prev, [1.0] * 99, 0.0)
        S["gold_perfact"] += len(G)
        auto, pend = split_facts(fr, turn, prev, conf, T)
        m = pair(auto, G)
        wb = sum(x is None for x in m)
        S["B_hit"] += sum(x == "hit" for x in m)
        S["B_wrong_facts"] += wb
        S["B_wrong_turns"] += int(wb > 0)
        if wb:
            fams[g.get("src", "?")] += 1
        remaining = [gf for gf, hit in zip(G, [False] * len(G))]
        used = pair(auto, G)
        taken = set()
        for f, lvl in zip(auto, used):
            if lvl:
                for k, gf in enumerate(G):
                    if k not in taken and match(f, gf):
                        taken.add(k)
                        break
        rest = [gf for k, gf in enumerate(G) if k not in taken]
        mp = pair(pend, rest)
        S["C_pending"] += len(pend)
        S["C_confirmed"] += sum(x == "hit" for x in mp)
        S["C_pending_wrong_asked"] += sum(x is None for x in mp)
    r = dict(S)
    r["T"] = T
    for arm in "A":
        r[f"{arm}_recall"] = round(S[f"{arm}_hit"] / max(1, S["gold"]), 4)
    r["C_taught_plus_confirmed"] = S["B_hit"] + S["C_confirmed"]
    r["B_recall"] = round(S["B_hit"] / max(1, S["gold_perfact"]), 4)
    r["C_recall"] = round(r["C_taught_plus_confirmed"] / max(1, S["gold_perfact"]), 4)
    r["B_wrong_turns_by_src"] = dict(fams)
    return r


def parity(rows, src_name):
    C = Counter()
    for r in rows:
        fr = r.get("frame")
        if fr is None and "target" in r:
            fr = json.loads(r["target"].split("\n<END>")[0])
        turn = r.get("turn")
        prev = r.get("prev_reply", "")
        if turn is None:  # train rows carry only the prompt
            pr = r["prompt"]
            prev = pr.split("\nAssistant said: ", 1)[1].split("\nUser said: ", 1)[0]
            prev = "" if prev == "(nothing)" else prev
            turn = pr.split("\nUser said: ", 1)[1].rsplit("\nFrame: ", 1)[0]
        for f in (fr or {}).get("facts") or []:
            if f.get("mode") in WRITE_MODES:
                why = check_fact(f, turn, prev)
                C["gold_write_mode_facts"] += 1
                if why is not None and why != "we":
                    C["unreachable"] += 1
                    C["why:" + why] += 1
    return {src_name: dict(C)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--train")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    gold = load(a.gold)
    pred = {r["id"]: r for r in load(a.pred)}
    res = {"grid": [rescore(gold, pred, T) for T in GRID]}
    res["parity"] = parity(gold, "dev")
    if a.train:
        res["parity"].update(parity(load(a.train), "train"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "rescore.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for r in res["grid"]:
        print(f"T={r['T']:.3f} gold={r['gold']} | A hit {r['A_hit']} wrongT {r['A_wrong_turns']} | "
              f"| perfact gold {r['gold_perfact']} B hit {r['B_hit']} wrongT {r['B_wrong_turns']} | C taught+conf {r['C_taught_plus_confirmed']} "
              f"({r['C_recall']:.1%}) pend {r['C_pending']} pendwrong {r['C_pending_wrong_asked']}")
    print(json.dumps(res["parity"], indent=1))


if __name__ == "__main__":
    main()
