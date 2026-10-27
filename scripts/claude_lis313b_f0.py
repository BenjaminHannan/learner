#!/usr/bin/env python3
"""lis-313b: scripts/claude_lis313_f0.py with two changes: the reader is wrapped in MemoReader
(claude_lis_stackb.py; crash fix) and arm D uses claude_lis313b_agent.py (question-word check).

lis-313: copy of scripts/claude_lis312_f0.py with arm D added (A/B/C unchanged).

Arm D = 292t + install_turn313 (scripts/claude_lis313_agent.py: turn310 with a
caching reader proxy + the answer-agreement wrapper outermost) with the reader
given by --model/--threshold. Arm D rows also carry "lis313": the per-turn
change in loop.lis313_stats, and its score adds those counters plus how the
reader-answered turns scored (right/wrong/abstain).

Original lis-312 docstring follows.

lis-312: score "292t + our 1B reader" on the sealed conversation benchmark F0.

Arms (one run each, fresh agent per dialog, same as scripts/claude_convf0_run.py):
  A  292t alone            build_agent292t(DEFAULT_CONFIG292T)
  B  292t + lis-300 reader  install_turn310(loop, Reader(lis300-merged), T=0.995)
  C  292t + lis-301 reader  install_turn310(loop, Reader(lis301-merged), T=lis-301 THRESHOLD.txt)
  D  292t + reader + 313    install_turn313(loop, Reader(--model), T=--threshold)
The reader wrapper is installed outermost, exactly as in lis-311 (read-only imports).

Scoring = claude_convf0_score.py's mechanical rules (imported, not copied), plus
"unexpected saves": new stored triples on a turn whose kind is smalltalk, ask or other.
Benchmark user turns are never printed.

python -B scripts/claude_lis312_f0.py --arm A --out DIR
python -B scripts/claude_lis312_f0.py --arm C --model DIR --threshold 0.93 --out DIR
python -B scripts/claude_lis312_f0.py --score DIR   (writes DIR/summary.json from DIR/arm_*.jsonl)
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
BENCH = ROOT / "artifacts/claude-convbench-f0-20260923/dialogs.jsonl"


LIS313_KEYS = ("asks", "agree", "reader_answered", "disagree", "reader_miss",
               "inverse_skipped", "check_seen", "inner_wrote", "reads")


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def build(arm, reader, threshold, state_dir):
    import claude_loop292t_agent as T292
    cfg = copy.deepcopy(T292.DEFAULT_CONFIG292T)
    cfg["state_dir"] = state_dir
    cfg["sleep_threshold"] = 100000
    loop = T292.build_agent292t(cfg)
    if arm == "D":
        import claude_lis313b_agent as L313
        L313.install_turn313(loop, reader, threshold=threshold,
                             log_path=Path(state_dir) / "lis313-asks.jsonl",
                             log_path310=Path(state_dir) / "lis312-turns.jsonl")
        if getattr(vars(loop).get("turn"), "__name__", "") != "turn313":
            raise RuntimeError("313: turn313 not outermost")
        return loop
    if arm != "A":
        import claude_lis310_agent as L310
        L310.install_turn310(loop, reader, threshold=threshold,
                             log_path=Path(state_dir) / "lis312-turns.jsonl")
        if getattr(vars(loop).get("turn"), "__name__", "") != "turn310":
            raise RuntimeError("312: turn310 not outermost")
    return loop


def run(a):
    import fable_loop90_agent as L90
    reader = None
    if a.arm != "A":
        import claude_lis300_read as READ
        import claude_lis_stackb as STACK
        # lis-313b: the only change from claude_lis313_f0.py. The Reader is wrapped in
        # MemoReader, which keeps it in a closure, so 292t's per-turn snapshot260 walk can't
        # reach the 1B weights (lis-313-f0 crashed with MPS out of memory on that walk).
        reader = STACK.MemoReader(READ.Reader(a.model))
    items = load(BENCH)
    order, by = [], {}
    for it in items:
        d = it["dialog_id"]
        if d not in by:
            by[d] = []
            order.append(d)
        by[d].append(it)
    rows = []
    for d in order:
        tmp = tempfile.mkdtemp(prefix=f"lis313-{a.arm}-")
        loop = build(a.arm, reader, a.threshold, tmp)
        try:
            for it in by[d]:
                text = it.get("user_text") or it.get("user")
                if not isinstance(text, str) or not text.strip():
                    raise SystemExit(f"empty text at {d} {it.get('turn_index')}")
                ev0 = len(loop.nb.events)
                st0 = dict(getattr(loop, "lis313_stats", {}) or {})
                t0 = time.time()
                parts = loop.turn(text)
                ms = (time.time() - t0) * 1000
                extra = {}
                if a.arm == "D":
                    st1 = dict(loop.lis313_stats)
                    extra["lis313"] = {k: st1[k] - st0.get(k, 0) for k in LIS313_KEYS
                                       if st1.get(k, 0) - st0.get(k, 0)}
                rows.append({**extra, "dialog_id": d, "turn_index": it["turn_index"],
                             "reply": " ".join(parts) if parts else "",
                             "notebook_events": [dict(e) for e in list(loop.nb.events)[ev0:]],
                             "stored_triples": sorted([s, r, v] for (s, r, v) in L90.notebook_triples(loop.nb)),
                             "ms": round(ms, 1)})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print(f"[lis313/{a.arm}] {d} turns={len(by[d])}", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"arm_{a.arm}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                            encoding="utf-8")
    print(f"wrote arm_{a.arm}.jsonl rows={len(rows)}")


def score_arm(bench, runs):
    import claude_convf0_score as S
    gold = {(b["dialog_id"], b["turn_index"]): b for b in bench}
    C = Counter()
    prev = {}
    ms = []
    for r in runs:
        b = gold[(r["dialog_id"], r["turn_index"])]
        kind, g, rp = b["kind"], b["gold"], str(r.get("reply", ""))
        C["turns"] += 1
        C["clarify"] += int(S.is_clarify(rp))
        before = prev.get(r["dialog_id"], [])
        new = [t for t in r["stored_triples"] if t not in before]
        prev[r["dialog_id"]] = r["stored_triples"]
        if "ms" in r:
            ms.append(r["ms"])
        l313 = r.get("lis313") or {}
        for k, v in l313.items():
            C["lis313_" + k] += v
        if kind == "ask":
            C["ask"] += 1
            if S.is_abstain_ask(rp):
                C["ask_abstain"] += 1
                res = "abstain"
            elif g and g in rp:
                C["ask_right"] += 1
                res = "right"
            else:
                C["ask_wrong"] += 1
                res = "wrong"
            # P313.2 denominator: the gold value is already stored as some fact's value.
            if g and any(t[2] == g for t in r["stored_triples"]):
                C["ask_gold_stored"] += 1
                C[f"ask_gold_stored_{res}"] += 1
            for k in ("reader_answered", "agree", "disagree", "reader_miss", "inverse_skipped"):
                if l313.get(k):
                    C[f"lis313_{k}_{res}"] += 1
        elif kind == "teach":
            C["teach"] += 1
            if g.count("|") == 2 and g.split("|") in r["stored_triples"]:
                C["teach_match"] += 1
            C["teach_other_new_triples"] += sum(1 for t in new if t != g.split("|"))
        elif kind in ("smalltalk", "other"):
            C[kind] += 1
            C[f"{kind}_clarify"] += int(S.is_clarify(rp))
            if new:
                C["unexpected_save_turns"] += 1
        elif kind == "correct":
            C["correct"] += 1
        if kind == "ask" and new:
            C["unexpected_save_turns"] += 1
    res = dict(C)
    if ms:
        ms.sort()
        res["ms_median"] = ms[len(ms) // 2]
        res["ms_max"] = ms[-1]
    return res


def score(a):
    bench = load(BENCH)
    d = Path(a.score)
    out = {}
    for arm in ("A", "B", "C", "D"):
        p = d / f"arm_{arm}.jsonl"
        if p.exists():
            out[arm] = score_arm(bench, load(p))
    (d / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["A", "B", "C", "D"])
    ap.add_argument("--model")
    ap.add_argument("--threshold", type=float, default=0.995)
    ap.add_argument("--out")
    ap.add_argument("--score")
    a = ap.parse_args()
    if a.score:
        score(a)
    else:
        run(a)


if __name__ == "__main__":
    main()
