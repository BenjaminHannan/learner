#!/usr/bin/env python3
"""Exp 290-diag bisect: 16-dialog subset on three partial stacks.
S1 = 138l + install_decline224 (224 alone).
S2 = 138l + 224 + install_q1honest224c (224+224c).
S3 = 138m loop classes WITHOUT the 224/224c instance wrappers
     (233+234+230c/219+227c layers present; exoneration test).
Appends rows to artifacts/claude-diag290-20260923/rows.jsonl with agent
labels 138l+224, 138l+224+224c, 138m-no224. New file only; additive."""
from __future__ import annotations
import copy, json, shutil, sys, tempfile
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import claude_loop138l_agent as L138L
import claude_loop138m_agent as M
import fable_loop224_agent as L224
import claude_loop224c_agent as L224C
import fable_decline224 as DEC
from claude_diag290_run import D as FULL, kind_of, evcount, ART

SUB_IDS = {"t-does-dog", "t-does-mother", "n-does-dog", "n-does-hobby",
           "n-does-unknown", "n-does-brother", "b-does-forget", "b-does-isnot",
           "b-does-mother-isnot", "b-does-replace", "x-where-inv", "x-who-of",
           "x-does-noart", "x-has", "n-what-father", "t-what-mother",
           "x-is", "x-what-of"}
SUB = [d for d in FULL if d[0] in SUB_IDS]
assert len(SUB) == len(SUB_IDS), (len(SUB), len(SUB_IDS))

def build_l224(cfg):
    loop = L138L.build_agent138l(cfg)
    L224.install_decline224(loop)
    return loop

def build_l224224c(cfg):
    loop = L138L.build_agent138l(cfg)
    L224.install_decline224(loop)
    L224C.install_q1honest224c(loop)
    return loop

def build_m_no224(cfg):
    loop = M._with_138m(M.L138K.build_agent138k, cfg)
    return loop

STACKS = [("138l+224", build_l224), ("138l+224+224c", build_l224224c),
          ("138m-no224", build_m_no224)]

def run():
    base = copy.deepcopy(L138L.DEFAULT_CONFIG138L)
    out = ART / "rows.jsonl"
    n = 0
    for tag, builder in STACKS:
        for did, setup, q, arm, shape in SUB:
            sd = Path(tempfile.mkdtemp(prefix="nb290b-"))
            cfg = copy.deepcopy(base); cfg["state_dir"] = str(sd); cfg["sleep_threshold"] = 100000
            loop = builder(cfg)
            # sanity: S3 must lack the wrappers; S1/S2 must have them
            has224 = getattr(loop, "decline224_log", None) is not None
            print(f"{tag} {did}: has224={has224}", flush=True)
            seen = []
            outer = loop.ears.hear
            def hear_wrap(turn, _o=outer):
                a = _o(turn)
                seen.append([dict(x) if isinstance(x, dict) else x for x in (a or [])])
                return a
            loop.ears.hear = hear_wrap
            setup_replies = []
            for t in setup:
                seen.clear()
                setup_replies.append(" ".join(loop.turn(t)))
            seen.clear()
            e0 = evcount(loop)
            reply = " ".join(loop.turn(q))
            e1 = evcount(loop)
            acts = seen[-1] if seen else []
            lr = getattr(loop, "last_routed", None)
            row = {"agent": tag, "id": did, "arm": arm, "shape": shape,
                   "setup": setup, "setup_replies": setup_replies,
                   "question": q, "reply": reply, "kind": kind_of(reply),
                   "stage": str(getattr(loop.ears, "last_stage", "")),
                   "acts": acts,
                   "has_ask": any(isinstance(a, dict) and a.get("act") == "ask" for a in acts),
                   "intent": lr.get("intent") if isinstance(lr, dict) else None,
                   "ev0": e0, "ev1": e1,
                   "d224": loop.decline224_log[-1] if getattr(loop, "decline224_log", None) else None,
                   "q1c": loop.q1honest224c_log[-1] if getattr(loop, "q1honest224c_log", None) else None}
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
            n += 1
            print(f"  kind={row['kind']} ask={row['has_ask']} intent={row['intent']} reply={reply}", flush=True)
            shutil.rmtree(sd, ignore_errors=True)
    print(f"APPENDED {n} rows to {out}")

if __name__ == "__main__":
    run()
