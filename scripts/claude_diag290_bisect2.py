#!/usr/bin/env python3
"""Exp 290-diag bisect fix: true 138m-classes-minus-224/224c stack.
Builds via the 138m class swap but keeps the ORIGINAL 138j build (no
224/224c instance wrappers). Asserts decline224_log is ABSENT (fail loudly
otherwise). Appends rows labeled 138m-no224v2. New file only; additive.
The earlier '138m-no224' rows in rows.jsonl are VOID (wrappers leaked in)."""
from __future__ import annotations
import copy, json, shutil, sys, tempfile
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import claude_loop138l_agent as L138L
import claude_loop138m_agent as M
from claude_diag290_run import D as FULL, kind_of, evcount, ART

SUB_IDS = {"t-does-dog", "t-does-mother", "n-does-dog", "n-does-hobby",
           "n-does-unknown", "n-does-brother", "b-does-forget", "b-does-isnot",
           "b-does-mother-isnot", "b-does-replace", "x-where-inv", "x-who-of",
           "x-does-noart", "x-has", "n-what-father", "t-what-mother",
           "x-is", "x-what-of"}
SUB = [d for d in FULL if d[0] in SUB_IDS]
assert len(SUB) == len(SUB_IDS), (len(SUB), len(SUB_IDS))

def build_m_no224v2(cfg):
    with M._Swap([(M.L138J, "Loop138jEars", M.Loop138mEars),
                  (M.L138J, "Loop138jAgentLoop", M.Loop138mAgentLoop),
                  (M.L138J, "build_agent138j", M._ORIG_BUILD)]):
        return M.L138K.build_agent138k(cfg)

def run():
    base = copy.deepcopy(L138L.DEFAULT_CONFIG138L)
    out = ART / "rows.jsonl"
    n = 0
    for did, setup, q, arm, shape in SUB:
        sd = Path(tempfile.mkdtemp(prefix="nb290c-"))
        cfg = copy.deepcopy(base); cfg["state_dir"] = str(sd); cfg["sleep_threshold"] = 100000
        loop = build_m_no224v2(cfg)
        has224 = getattr(loop, "decline224_log", None) is not None
        hasq1c = getattr(loop, "q1honest224c_log", None) is not None
        assert not has224 and not hasq1c, f"wrapper leak on {did}"
        # sanity: 138m loop class really in use (233 layer present in MRO)
        mro = [c.__name__ for c in type(loop).__mro__]
        assert "Loop233AgentLoop" in mro, mro[:6]
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
        row = {"agent": "138m-no224v2", "id": did, "arm": arm, "shape": shape,
               "setup": setup, "setup_replies": setup_replies,
               "question": q, "reply": reply, "kind": kind_of(reply),
               "stage": str(getattr(loop.ears, "last_stage", "")),
               "acts": acts,
               "has_ask": any(isinstance(a, dict) and a.get("act") == "ask" for a in acts),
               "intent": lr.get("intent") if isinstance(lr, dict) else None,
               "ev0": e0, "ev1": e1, "d224": None, "q1c": None,
               "mro6": mro[:6]}
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        n += 1
        print(f"138m-no224v2 {did}: kind={row['kind']} ask={row['has_ask']} intent={row['intent']} reply={reply}", flush=True)
        shutil.rmtree(sd, ignore_errors=True)
    print(f"APPENDED {n} rows to {out}")

if __name__ == "__main__":
    run()
