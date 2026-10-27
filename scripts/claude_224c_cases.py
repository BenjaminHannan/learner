#!/usr/bin/env python3
"""Exp 224c case driver (M1 B1 replay, M2 taught-fact traps, M3 untaught).

One fresh agent per case in an isolated state dir under --scratch.

Modes:
  natural : setup turns, then the probe turn, exactly as a user would.
  forced  : same, but on the PROBE turn only, the loop instance's _act is
            wrapped so an ears "ask" action returns a "didn't understand"
            clarify record instead of a lookup. This re-creates the 224b
            flake's shape (ears asked, notebook path reported a miss, glue
            reached with an ask captured), which is the only way loop224's
            Q1 branch is reached. Driver-only; no agent file is touched.

Per case it records the probe reply, the loop224 type, the loop224c check
log, the notebook writes of the probe turn, and whether the reply is Q1,
states a stored value, or states the gold value.

  python -B scripts/claude_224c_cases.py --agent 224c --mode forced \\
     --cases <json> --scratch <dir> --out <json>
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent
import fable_decline224 as DEC  # noqa: E402
import fable_loop138_agent as L138  # noqa: E402 (NOT_UNDERSTOOD)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)

CFG = ROOT / "artifacts" / "fable-agent138i-20260922" / "loop138i-config.json"
Q1 = DEC.NEW_SENTENCES224["Q1"]


def build(agent: str, state_dir: str):
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    cfg["state_dir"] = state_dir
    cfg["sleep_threshold"] = 100000
    if agent == "224c":
        import claude_loop224c_agent as M
        return M.build_agent224c(cfg)
    if agent == "224":
        import fable_loop224_agent as M
        return M.build_agent224(cfg)
    import fable_loop138i_agent as M
    return M.build_agent138i(cfg)


def trip(loop) -> list:
    return sorted([list(t) for t in L90.notebook_triples(loop.nb)])


def run_case(agent: str, mode: str, case: dict, scratch: Path) -> dict:
    sd = tempfile.mkdtemp(prefix=f"c-{agent}-{mode}-{case['id']}-",
                          dir=scratch)
    loop = build(agent, sd)
    setup = [" ".join(loop.turn(t)) for t in case.get("setup", [])]
    before = trip(loop)
    forced = {"asks": 0}
    had_inst = "_act" in loop.__dict__
    if mode == "forced":
        orig_act = loop._act

        def act_forced(action):
            if isinstance(action, dict) and action.get("act") == "ask":
                forced["asks"] += 1
                return {"kind": "clarify",
                        "text": f"I {L138.NOT_UNDERSTOOD} that (forced)."}
            return orig_act(action)

        loop._act = act_forced
    said = loop.turn(case["text"])
    if mode == "forced":
        if had_inst:
            loop._act = orig_act
        else:
            del loop._act
    after = trip(loop)
    reply = " ".join(said)
    kind = None
    log224 = getattr(loop, "decline224_log", [])
    if log224 and log224[-1]["text"] == case["text"]:
        kind = log224[-1]["kind"]
    chk = None
    log_c = getattr(loop, "q1honest224c_log", [])
    if log_c and log_c[-1]["text"] == case["text"]:
        chk = log_c[-1]
    low = reply.lower()
    stored_vals = sorted({t[2] for t in before if t[2]})
    qlow = str(case["text"]).lower()
    named = [v for v in stored_vals if v.lower() in low
             and v.lower() not in qlow]
    gold = case.get("gold")
    gold_hit = bool(gold) and gold.lower() in low
    fact_stored = None
    if case.get("stored_check"):
        s, v = case["stored_check"]
        fact_stored = any(t[0].lower() == s.lower() and t[2].lower()
                          == v.lower() for t in before)
    return {"id": case["id"], "set": case.get("set"), "sub": case.get("sub"),
            "text": case["text"],
            "setup_replies": setup, "reply": said, "kind224": kind,
            "check224c": chk, "forced_asks": forced["asks"],
            "is_q1": reply == Q1, "gold_hit": gold_hit,
            "stated_other_value": named if not gold_hit else [],
            "fact_stored": fact_stored,
            "writes": [t for t in after if t not in before]
            + [["-"] + t for t in before if t not in after]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", choices=["138i", "224", "224c"],
                    required=True)
    ap.add_argument("--mode", choices=["natural", "forced"], required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))["cases"]
    scratch = Path(args.scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    rows = [run_case(args.agent, args.mode, c, scratch) for c in cases]
    summ = {"agent": args.agent, "mode": args.mode, "n": len(rows),
            "q1": sum(r["is_q1"] for r in rows),
            "gold_hit": sum(r["gold_hit"] for r in rows),
            "stated_other_value": sum(bool(r["stated_other_value"])
                                      for r in rows),
            "writes_total": sum(len(r["writes"]) for r in rows),
            "fact_not_stored": [r["id"] for r in rows
                                if r["fact_stored"] is False],
            "kinds": {}}
    for r in rows:
        k = str(r["kind224"])
        summ["kinds"][k] = summ["kinds"].get(k, 0) + 1
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"summary": summ, "rows": rows},
                                         indent=1, ensure_ascii=False),
                              encoding="utf-8")
    print(json.dumps(summ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
