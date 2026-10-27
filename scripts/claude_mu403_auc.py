#!/usr/bin/env python3
"""mu-403 signal check on already-judged replies (DEV, report only; "Making things up about you", 2026-09-26).
New file only. Replaces the slow CPU sampling pilot as the deciding check for the grounded pick.

Question: does the 1B's own self-check margin (claude_mu403_ground.GroundScorer: logit yes - logit no for "does the
reply assume something about the user they did not write?") separate replies that mu-402's blind judges flagged as
made up from replies they did not flag? Every mu-402 reply (arms A, B, T; 402 each) gets its margin with the prompt
chat 338 would have built at that turn (SYSTEM338, no notebook facts, that arm's own last 12 messages, the user turn).

Decision bar, fixed BEFORE any margin is computed (commit of this file):
  AUC(margin; flagged by either judge vs by neither), pooled over arms A and B (the chat-path replies), >= 0.65
  -> register mu-403 as the grounded pick (claude_mu403.build_ground02c) on the fresh mu-403 dev panel.
  AUC < 0.65 -> the self-check has too little signal: register the fallback, the system line
  (claude_mu403.build_sysline02c), instead. T's AUC and per-kind AUCs are reported only.

  python3 -B scripts/claude_mu403_auc.py score --panel-dir P --runs RUNS --names A,B,T --gen-model BASE --out M.jsonl
  python3 -B scripts/claude_mu403_auc.py auc --margins M.jsonl --panel-dir P --runs RUNS --judge-dir J
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

BAR = 0.65


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def score(a):
    import claude_chat338_agent as C38
    import claude_cre333b_agent as C333B
    import claude_mu403_ground as G
    items = {it["item_id"]: it for it in load(Path(a.panel_dir) / "items.jsonl")}
    sc = G.GroundScorer(C333B.Gen333b(a.gen_model))
    out = Path(a.out)
    done = {(r["arm"], r["item_id"], r["turn_i"]) for r in load(out)} if out.exists() else set()
    with out.open("a", encoding="utf-8") as f:
        for arm in a.names.split(","):
            by = defaultdict(dict)
            for r in load(Path(a.runs) / f"chat_{arm}.jsonl"):
                by[r["item_id"]][r["turn_i"]] = r
            for iid in sorted(by):
                turns = items[iid]["turns"]
                for ti in sorted(by[iid]):
                    if (arm, iid, ti) in done:
                        continue
                    hist = []
                    for j in range(ti):
                        hist += [{"role": "user", "content": turns[j]["text"]},
                                 {"role": "assistant", "content": by[iid][j]["reply"]}]
                    msgs = ([{"role": "system", "content": C38.SYSTEM338}] + hist[-C38.HISTORY338:]
                            + [{"role": "user", "content": turns[ti]["text"]}])
                    m = sc.margins(msgs, [C38.trim(by[iid][ti]["reply"])])[0]
                    f.write(json.dumps({"arm": arm, "item_id": iid, "turn_i": ti, "kind": turns[ti]["kind"],
                                        "margin": round(m, 4)}) + "\n")
                    f.flush()
            print(f"[mu403-auc] scored arm {arm}", flush=True)


def auc(pos, neg):
    """P(margin of a flagged reply > margin of an unflagged one), ties count half."""
    if not pos or not neg:
        return None
    s = 0.0
    for p in pos:
        for n in neg:
            s += 1.0 if p > n else 0.5 if p == n else 0.0
    return round(s / (len(pos) * len(neg)), 3)


def flags(a):
    """(arm, item, turn) -> number of judges (0-2) who flagged the reply, from mu-402's keys and outputs."""
    import claude_mu402_judge as J
    j = Path(a.judge_dir)
    key = json.loads((j / "keys" / "claims_key.json").read_text(encoding="utf-8"))
    _, cv = J.convos(a.panel_dir, a.runs, ["A", "B", "T"])
    turn_ids = {}
    for (arm, iid) in cv:
        rows = sorted(r["turn_i"] for r in load(Path(a.runs) / f"chat_{arm}.jsonl") if r["item_id"] == iid)
        turn_ids[(arm, iid)] = rows
    out = defaultdict(int)
    for f in sorted((j / "out").glob("claims_j*.jsonl")):
        for r in load(f):
            k = key[r["pid"]]
            for ti, v in zip(turn_ids[(k["arm"], k["item_id"])], r["flags"]):
                out[(k["arm"], k["item_id"], ti)] += 1 if int(v) else 0
    return out


def report(a):
    fl = flags(a)
    ms = load(a.margins)
    res = {"bar": BAR}

    def split(rows, both=False):
        pos = [r["margin"] for r in rows if fl[(r["arm"], r["item_id"], r["turn_i"])] >= (2 if both else 1)]
        neg = [r["margin"] for r in rows if fl[(r["arm"], r["item_id"], r["turn_i"])] == 0]
        return pos, neg

    ab = [r for r in ms if r["arm"] in ("A", "B")]
    p, n = split(ab)
    res["AB_either"] = {"auc": auc(p, n), "flagged": len(p), "unflagged": len(n)}
    p2, n2 = split(ab, both=True)
    res["AB_both"] = {"auc": auc(p2, n2), "flagged": len(p2), "unflagged": len(n2)}
    for arm in ("A", "B", "T"):
        p, n = split([r for r in ms if r["arm"] == arm])
        res[f"arm_{arm}"] = {"auc": auc(p, n), "flagged": len(p), "unflagged": len(n)}
    for kind in sorted({r["kind"] for r in ab}):
        p, n = split([r for r in ab if r["kind"] == kind])
        res[f"AB_kind_{kind}"] = {"auc": auc(p, n), "flagged": len(p), "unflagged": len(n)}
    res["scored"] = {arm: sum(1 for r in ms if r["arm"] == arm) for arm in ("A", "B", "T")}
    v = res["AB_either"]["auc"]
    res["decision"] = ("grounded pick (build_ground02c)" if v is not None and v >= BAR
                       else "system line (build_sysline02c)")
    print(json.dumps(res, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["score", "auc"])
    ap.add_argument("--panel-dir", required=True)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--names", default="A,B,T")
    ap.add_argument("--gen-model")
    ap.add_argument("--out")
    ap.add_argument("--margins")
    ap.add_argument("--judge-dir")
    a = ap.parse_args()
    (score if a.cmd == "score" else report)(a)


if __name__ == "__main__":
    main()
