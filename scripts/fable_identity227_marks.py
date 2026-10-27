#!/usr/bin/env python3
"""Exp 227 marks driver: M1 (identity sheet) + M2 (byte-identical to 138i).

Usage (Mac CPU, offline, isolated scratch dirs, one suite at a time):
  python -B scripts/fable_identity227_marks.py --m1
  python -B scripts/fable_identity227_marks.py --m2
Case files live sealed in artifacts/fable-identity227-20260922/.
"""
from __future__ import annotations
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ART = Path("/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-identity227-20260922")


def build(mod_name: str, state_dir: str):
    mod = __import__(mod_name)
    cfg_attr = [a for a in dir(mod) if a.startswith("DEFAULT_CONFIG")][0]
    build_attr = [a for a in dir(mod) if a.startswith("build_agent")][0]
    cfg = dict(getattr(mod, cfg_attr))
    cfg["state_dir"] = state_dir
    return getattr(mod, build_attr)(cfg)


def snap(loop) -> str:
    facts = sorted(
        (f.get("subject"), f.get("relation"), json.dumps(f.get("value"), sort_keys=True),
         f.get("source"), bool(loop.nb.active(fid)))
        for fid, f in loop.nb.facts.items())
    return json.dumps({"facts": facts, "entities": loop.nb.entities}, sort_keys=True)


def run_turns(loop, turns: list[str]) -> tuple[list[str], str]:
    replies = []
    for t in turns:
        replies.append(" ".join(loop.turn(t)))
    return replies, snap(loop)


def cmd_m1() -> int:
    import fable_identity227 as F227
    cases = json.loads((ART / "m1-cases.json").read_text(encoding="utf-8"))
    rows = []
    ok = 0
    for c in cases:
        tmp = tempfile.mkdtemp(prefix="m1_227_")
        loop = build("fable_loop227_agent", tmp)
        pre_replies, pre_snap = [], None
        if c.get("teach"):
            pre_replies, _ = run_turns(loop, [c["teach"]])
            pre_snap = snap(loop)
        else:
            pre_snap = snap(loop)
        replies, post_snap = run_turns(loop, [c["text"]])
        want = F227.SHEET[c["intent"]]
        reply_ok = replies[0] == want
        write_ok = json.loads(post_snap)["facts"] == json.loads(pre_snap)["facts"]
        passed = reply_ok and write_ok
        ok += passed
        rows.append({"id": c["id"], "intent": c["intent"], "text": c["text"],
                     "teach": c.get("teach"), "reply": replies[0],
                     "want": want, "reply_ok": reply_ok, "write_ok": write_ok,
                     "pass": passed})
        print(f"{c['id']}({c['intent']}): {'PASS' if passed else 'FAIL'} Q={c['text'][:50]} :: A={replies[0][:80]}")
    (ART / "m1-rows.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"M1 {ok}/{len(cases)}")
    return 0 if ok == len(cases) else 1


def cmd_m2() -> int:
    cases = json.loads((ART / "m2-cases.json").read_text(encoding="utf-8"))
    rows = []
    ok = 0
    for c in cases:
        turns = ([c["teach"]] if c.get("teach") else []) + [c["text"]]
        outs = {}
        for mod in ("fable_loop227_agent", "fable_loop138i_agent"):
            tmp = tempfile.mkdtemp(prefix="m2_227_")
            loop = build(mod, tmp)
            outs[mod] = run_turns(loop, turns)
        same_reply = outs["fable_loop227_agent"][0] == outs["fable_loop138i_agent"][0]
        same_facts = outs["fable_loop227_agent"][1] == outs["fable_loop138i_agent"][1]
        passed = same_reply and same_facts
        ok += passed
        rows.append({"id": c["id"], "teach": c.get("teach"), "text": c["text"],
                     "r227": outs["fable_loop227_agent"][0],
                     "r138i": outs["fable_loop138i_agent"][0],
                     "same_reply": same_reply, "same_facts": same_facts,
                     "pass": passed})
        print(f"{c['id']}: {'PASS' if passed else 'FAIL'} Q={c['text'][:50]} :: A={outs['fable_loop227_agent'][0][-1][:80]}")
    (ART / "m2-rows.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"M2 {ok}/{len(cases)}")
    return 0 if ok == len(cases) else 1


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--m1", action="store_true")
    p.add_argument("--m2", action="store_true")
    a = p.parse_args(argv)
    if a.m1:
        return cmd_m1()
    if a.m2:
        return cmd_m2()
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
