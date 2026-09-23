#!/usr/bin/env python3
"""Exp 227c marks driver.

  --m1  fresh identity turns (m1-cases.json): sheet reply, 0 writes, follow-ups
  --m2  user-name near-misses (m2-cases.json): byte-identical to 227b,
        untaught and after "My name is Hedda."
  --m3  227b's own cases (227 m1+m2, 227b m2 sessions): identical to 227b
Rows are written to artifacts/claude-identity227c-20260922/.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
REPO = SCRIPTS.parent
ART = REPO / "artifacts" / "claude-identity227c-20260922"
ART227B = REPO / "artifacts" / "claude-name227b-20260922"
ART227 = REPO / "artifacts" / "fable-identity227-20260922"
ASSIST = "My name is Premonition."

AGENTS = {
    "227c": ("claude_loop227c_agent", ART / "loop227c-config.json"),
    "227b": ("claude_loop227b_agent", ART227B / "loop227b-config.json"),
}


def build(tag: str, state_dir: str):
    mod_name, cfg_path = AGENTS[tag]
    mod = __import__(mod_name)
    cfg_attr = [a for a in dir(mod) if a.startswith("DEFAULT_CONFIG")][0]
    build_attr = [a for a in dir(mod) if a.startswith("build_agent")][0]
    cfg = dict(getattr(mod, cfg_attr))
    cfg.update(json.loads(cfg_path.read_text(encoding="utf-8")))
    cfg["state_dir"] = state_dir
    return getattr(mod, build_attr)(cfg)


def facts(loop) -> list:
    return sorted(
        (f.get("subject"), f.get("relation"),
         json.dumps(f.get("value"), sort_keys=True), f.get("source"),
         bool(loop.nb.active(fid)))
        for fid, f in loop.nb.facts.items())


def run_session(tag: str, turns: list[str]) -> dict:
    import fable_loop90_agent as L90
    loop = build(tag, tempfile.mkdtemp(prefix=f"i227c_{tag}_"))
    replies, writes = [], []
    for t in turns:
        before = facts(loop)
        replies.append(" ".join(loop.turn(t)))
        writes.append(len(set(facts(loop)) - set(before)))
    snap = json.dumps({"facts": facts(loop), "entities": loop.nb.entities},
                      sort_keys=True)
    return {"replies": replies, "writes": writes, "snap": snap,
            "triples": [list(x) for x in L90.notebook_triples(loop.nb)]}


def cmd_m1() -> int:
    data = json.loads((ART / "m1-cases.json").read_text(encoding="utf-8"))
    rows, tally = [], {}
    for c in data["cases"]:
        pre = [c["teach"]] if c.get("teach") else []
        fol = [f[0] for f in c.get("follow", [])]
        turns = pre + [c["text"]] + fol
        new = run_session("227c", turns)
        k = len(pre)
        ok = new["replies"][k] == c["want"] and new["writes"][k] == 0
        fol_ok = []
        for j, (t, want) in enumerate(c.get("follow", [])):
            r = new["replies"][k + 1 + j]
            w = new["writes"][k + 1 + j]
            if want == "ASSIST":
                good = r == ASSIST
            else:
                name = want.split(":", 1)[1]
                good = name in r and "Premonition" not in r
            fol_ok.append(good and w == 0)
        if pre:
            base = run_session("227b", pre)
            teach_same = base["replies"] == new["replies"][:k]
        else:
            teach_same = True
        prem_stored = any("Premonition" in json.dumps(x)
                          for x in new["triples"]) or "Premonition" in new["snap"]
        passed = ok and all(fol_ok) and teach_same and not prem_stored
        t = tally.setdefault(c["intent"], [0, 0])
        t[0] += passed
        t[1] += 1
        rows.append({**c, "replies": new["replies"], "writes": new["writes"],
                     "triples": new["triples"], "reply_ok": ok,
                     "follow_ok": fol_ok, "teach_same": teach_same,
                     "premonition_stored": prem_stored, "pass": passed})
        print(f"{c['id']}({c['intent']}) {'PASS' if passed else 'FAIL'} "
              f"{c['text']!r} -> {new['replies'][k][:60]!r}", flush=True)
    (ART / "m1-rows.json").write_text(json.dumps(rows, indent=1),
                                      encoding="utf-8")
    tot = sum(v[0] for v in tally.values())
    print(f"M1 {tot}/{len(rows)} :: " + "; ".join(
        f"{k} {v[0]}/{v[1]}" for k, v in tally.items()))
    return 0 if tot == len(rows) else 1


def cmd_m2() -> int:
    data = json.loads((ART / "m2-cases.json").read_text(encoding="utf-8"))
    rows, ok_n, n = [], 0, 0
    for c in data["cases"]:
        for teach in (None, "My name is Hedda."):
            turns = ([teach] if teach else []) + [c["text"]]
            new = run_session("227c", turns)
            old = run_session("227b", turns)
            same = (new["replies"] == old["replies"]
                    and new["snap"] == old["snap"])
            n += 1
            ok_n += same
            rows.append({"id": c["id"], "teach": teach, "text": c["text"],
                         "r227c": new["replies"], "r227b": old["replies"],
                         "facts_same": new["snap"] == old["snap"],
                         "pass": same})
            print(f"{c['id']}{'T' if teach else 'U'} "
                  f"{'PASS' if same else 'FAIL'} {c['text']!r} -> "
                  f"{new['replies'][-1][:60]!r}", flush=True)
    (ART / "m2-rows.json").write_text(json.dumps(rows, indent=1),
                                      encoding="utf-8")
    print(f"M2 {ok_n}/{n}")
    return 0 if ok_n == n else 1


def cmd_m3() -> int:
    sessions = []
    for f in ("m1-cases.json", "m2-cases.json"):
        for c in json.loads((ART227 / f).read_text(encoding="utf-8")):
            sessions.append(("227-" + f[:2], c["id"],
                             ([c["teach"]] if c.get("teach") else [])
                             + [c["text"]]))
    for s in json.loads((ART227B / "m2-cases.json").read_text(
            encoding="utf-8")):
        sessions.append(("227b-m2", s["id"], s["turns"]))
    rows, ok_n = [], 0
    for src, sid, turns in sessions:
        new = run_session("227c", turns)
        old = run_session("227b", turns)
        same = (new["replies"] == old["replies"]
                and new["snap"] == old["snap"])
        ok_n += same
        rows.append({"src": src, "id": sid, "turns": turns,
                     "r227c": new["replies"], "r227b": old["replies"],
                     "pass": same})
        print(f"{src}:{sid} {'PASS' if same else 'FAIL'}", flush=True)
    (ART / "m3-rows.json").write_text(json.dumps(rows, indent=1),
                                      encoding="utf-8")
    print(f"M3 {ok_n}/{len(rows)}")
    return 0 if ok_n == len(rows) else 1


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser()
    for m in ("--m1", "--m2", "--m3"):
        p.add_argument(m, action="store_true")
    a = p.parse_args(argv)
    if a.m1:
        return cmd_m1()
    if a.m2:
        return cmd_m2()
    if a.m3:
        return cmd_m3()
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
