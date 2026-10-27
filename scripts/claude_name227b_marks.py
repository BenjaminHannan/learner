#!/usr/bin/env python3
"""Exp 227b marks driver (M1 all 227 cases vs loop227, M2 Juno sessions).

  python -B scripts/claude_name227b_marks.py --m1   # 68 cases (227 m1+m2)
  python -B scripts/claude_name227b_marks.py --m2   # Juno sessions
Rows are written to artifacts/claude-name227b-20260922/.
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
ART = REPO / "artifacts" / "claude-name227b-20260922"
ART227 = REPO / "artifacts" / "fable-identity227-20260922"


def build(mod_name: str, cfg_path: Path, state_dir: str):
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


def snap(loop) -> str:
    return json.dumps({"facts": facts(loop), "entities": loop.nb.entities},
                      sort_keys=True)


AGENTS = {
    "227b": ("claude_loop227b_agent", ART / "loop227b-config.json"),
    "227": ("fable_loop227_agent", ART227 / "loop227-config.json"),
}


def run_session(tag: str, turns: list[str]) -> dict:
    mod, cfg = AGENTS[tag]
    loop = build(mod, cfg, tempfile.mkdtemp(prefix=f"n227b_{tag}_"))
    replies, writes = [], []
    for t in turns:
        before = facts(loop)
        replies.append(" ".join(loop.turn(t)))
        writes.append(len(set(facts(loop)) - set(before)))
    import fable_loop90_agent as L90
    return {"replies": replies, "writes": writes, "snap": snap(loop),
            "triples": [list(x) for x in L90.notebook_triples(loop.nb)]}


def cmd_m1() -> int:
    import claude_loop227b_agent as B
    c1 = json.loads((ART227 / "m1-cases.json").read_text(encoding="utf-8"))
    c2 = json.loads((ART227 / "m2-cases.json").read_text(encoding="utf-8"))
    cases = ([dict(c, src="227-M1") for c in c1]
             + [dict(c, src="227-M2", intent=None) for c in c2])
    rows, ok = [], 0
    for c in cases:
        turns = ([c["teach"]] if c.get("teach") else []) + [c["text"]]
        new = run_session("227b", turns)
        old = run_session("227", turns)
        is_name = c.get("intent") == "NAME"
        if is_name:
            reply_ok = (new["replies"][-1] == B.NAME_227B
                        and old["replies"][-1] == B.OLD_NAME_227
                        and new["replies"][:-1] == old["replies"][:-1])
        else:
            reply_ok = new["replies"] == old["replies"]
        facts_ok = new["snap"] == old["snap"]
        q_writes = new["writes"][-1]
        wr_ok = (q_writes == 0) if c["src"] == "227-M1" else True
        passed = reply_ok and facts_ok and wr_ok
        ok += passed
        rows.append({"id": c["id"], "src": c["src"], "intent": c.get("intent"),
                     "teach": c.get("teach"), "text": c["text"],
                     "r227b": new["replies"], "r227": old["replies"],
                     "question_writes": q_writes, "reply_ok": reply_ok,
                     "facts_ok": facts_ok, "pass": passed})
        print(f"{c['id']}({c['src']},{c.get('intent')}): "
              f"{'PASS' if passed else 'FAIL'} Q={c['text']!r} :: "
              f"{new['replies'][-1][:70]!r}", flush=True)
    (ART / "m1-rows.json").write_text(json.dumps(rows, indent=1),
                                      encoding="utf-8")
    name_n = sum(1 for r in rows if r["intent"] == "NAME")
    print(f"M1 {ok}/{len(rows)} (NAME cases {name_n}, others "
          f"{len(rows) - name_n})")
    return 0 if ok == len(rows) else 1


def cmd_m2() -> int:
    import claude_loop227b_agent as B
    sess = json.loads((ART / "m2-cases.json").read_text(encoding="utf-8"))
    rows, ok = [], 0
    for s in sess:
        new = run_session("227b", s["turns"])
        good = True
        checks = []
        for i, (t, r, w) in enumerate(zip(s["turns"], new["replies"],
                                          new["writes"])):
            want = s["want"][i]
            if want == "USERNAME":
                c = (s["user"] in r and "Premonition" not in r and w == 0)
            elif want == "PREMONITION":
                c = (r == B.NAME_227B and w == 0)
            else:
                c = True  # teach turn: checked through final facts
            checks.append(c)
            good &= c
        tr = new["triples"]
        user_names = [x[2] for x in tr if x[0] == "USER" and x[1] == "name"]
        prem = "Premonition" in new["snap"] or any(
            "Premonition" in json.dumps(x) for x in tr)
        fact_ok = (user_names == [s["user"]] and not prem)
        good = good and fact_ok
        ok += good
        rows.append({"id": s["id"], "turns": s["turns"],
                     "replies": new["replies"], "writes": new["writes"],
                     "triples": tr, "checks": checks, "user_names": user_names,
                     "premonition_stored": prem, "pass": good})
        print(f"{s['id']}: {'PASS' if good else 'FAIL'}", flush=True)
        for t, r, w in zip(s["turns"], new["replies"], new["writes"]):
            print(f"   {t!r} -> {r!r} (writes {w})", flush=True)
    (ART / "m2-rows.json").write_text(json.dumps(rows, indent=1),
                                      encoding="utf-8")
    print(f"M2 {ok}/{len(rows)}")
    return 0 if ok == len(rows) else 1


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
