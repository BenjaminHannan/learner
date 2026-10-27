#!/usr/bin/env python3
"""Exp 230 marks driver.

  python -B scripts/claude_yesprefix230_marks.py --m1  # 219's own cases vs live 219
  python -B scripts/claude_yesprefix230_marks.py --m2  # fresh WH / IMP / YN cases
Rows are written to artifacts/claude-yesprefix230-20260922/.
Expected 230 reply for every turn, computed from the live 219 reply:
  if the turn is NOT a yes/no question and a 219 reply line starts with
  "Yes. Your name is ", that line minus "Yes. "; otherwise byte-identical.
Notebook snapshots must be identical to 219 in every session.
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
ART = REPO / "artifacts" / "claude-yesprefix230-20260922"
ART219 = REPO / "artifacts" / "fable-selfname219-20260922"

AGENTS = {
    "230": ("claude_loop230_agent", ART / "loop230-config.json"),
    "219": ("fable_loop219_agent", ART219 / "loop219-config.json"),
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
    loop = build(tag, tempfile.mkdtemp(prefix=f"y230_{tag}_"))
    replies, writes = [], []
    for t in turns:
        before = facts(loop)
        replies.append(list(loop.turn(t)))
        writes.append(len(set(facts(loop)) - set(before)))
    snap = json.dumps({"facts": facts(loop), "entities": loop.nb.entities},
                      sort_keys=True)
    return {"replies": replies, "writes": writes, "snap": snap}


def expected(text: str, base_lines: list[str]) -> list[str]:
    import claude_loop230_agent as Y
    if Y.is_yes_no_question(text):
        return list(base_lines)
    return [ln[len(Y.YES):] if ln.startswith(Y.YES_NAME_PREFIX) else ln
            for ln in base_lines]


def compare(turns: list[str]) -> dict:
    new = run_session("230", turns)
    old = run_session("219", turns)
    per = []
    for t, rn, ro in zip(turns, new["replies"], old["replies"]):
        exp = expected(t, ro)
        per.append({"turn": t, "r219": ro, "r230": rn, "expected": exp,
                    "moved": rn != ro, "ok": rn == exp})
    return {"per": per, "facts_same": new["snap"] == old["snap"],
            "writes230": new["writes"], "writes219": old["writes"]}


def cmd_m1() -> int:
    sessions = []
    c1 = json.loads((ART219 / "m1-cases.json").read_text(encoding="utf-8"))
    for s in c1["sessions"]:
        sessions.append(("M1", s["id"], [s["teach"]] + c1["probes"]))
    c2 = json.loads((ART219 / "m2-cases.json").read_text(encoding="utf-8"))
    for s in c2["sessions"]:
        sessions.append(("M2", s["id"], list(c2["probes"])))
    c3 = json.loads((ART219 / "m3-cases.json").read_text(encoding="utf-8"))
    for s in c3["stored"]:
        sessions.append(("M3", s["id"], [c3["teach_template"].format(
            age=s["age"])] + c3["probes"]))
    for i in range(int(c3["n_empty"])):
        sessions.append(("M3", f"M3-E{i + 1:02d}", list(c3["probes"])))
    rows, n_turn, n_ok, n_moved, n_sess_ok = [], 0, 0, 0, 0
    yn_moved = 0
    import claude_loop230_agent as Y
    for src, sid, turns in sessions:
        cmp = compare(turns)
        ok = cmp["facts_same"] and all(p["ok"] for p in cmp["per"])
        n_sess_ok += ok
        for p in cmp["per"]:
            n_turn += 1
            n_ok += p["ok"]
            n_moved += p["moved"]
            if p["moved"] and Y.is_yes_no_question(p["turn"]):
                yn_moved += 1
            if p["moved"]:
                print(f"  MOVE {sid} {p['turn']!r}: {p['r219']} -> {p['r230']}")
        rows.append({"src": src, "session": sid, **cmp, "pass": ok})
        print(f"{sid}: {'PASS' if ok else 'FAIL'}", flush=True)
    (ART / "m1-rows.json").write_text(json.dumps(rows, indent=1),
                                      encoding="utf-8")
    print(f"M1 sessions {n_sess_ok}/{len(rows)}; turns ok {n_ok}/{n_turn}; "
          f"moved {n_moved} (yes/no turns moved {yn_moved})")
    return 0 if n_sess_ok == len(rows) and yn_moved == 0 else 1


def cmd_m2() -> int:
    import claude_loop230_agent as Y
    data = json.loads((ART / "m2-cases.json").read_text(encoding="utf-8"))
    rows = []
    tally: dict = {}
    for c in data["cases"]:
        name, q, kind = c["name"], c["text"], c["kind"]
        taught = compare([f"My name is {name}.", q])
        untaught = compare([q])
        pt, pu = taught["per"][-1], untaught["per"][-1]
        want_yes = "Yes. Your name is %s." % name
        want_plain = "Your name is %s." % name
        if kind == "YN":
            t_ok = pt["r230"] == pt["r219"]
        else:
            t_ok = (pt["r219"] == [want_yes] and pt["r230"] == [want_plain])
        u_ok = pu["r230"] == pu["r219"]
        w_ok = (taught["writes230"][-1] == 0 and untaught["writes230"][-1] == 0)
        f_ok = taught["facts_same"] and untaught["facts_same"]
        ok = t_ok and u_ok and w_ok and f_ok and taught["per"][0]["ok"]
        k = tally.setdefault(kind, [0, 0])
        k[0] += ok
        k[1] += 1
        rows.append({"id": c["id"], "kind": kind, "text": q, "name": name,
                     "yes_no": Y.is_yes_no_question(q),
                     "taught_r219": pt["r219"], "taught_r230": pt["r230"],
                     "untaught_r219": pu["r219"], "untaught_r230": pu["r230"],
                     "q_writes": [taught["writes230"][-1],
                                  untaught["writes230"][-1]],
                     "taught_ok": t_ok, "untaught_same": u_ok,
                     "writes_ok": w_ok, "facts_same": f_ok, "pass": ok})
        print(f"{c['id']} {'PASS' if ok else 'FAIL'} {q!r}: "
              f"{pt['r219']} -> {pt['r230']}", flush=True)
    (ART / "m2-rows.json").write_text(json.dumps(rows, indent=1),
                                      encoding="utf-8")
    print("M2 " + "; ".join(f"{k} {v[0]}/{v[1]}" for k, v in tally.items()))
    return 0 if all(v[0] == v[1] for v in tally.values()) else 1


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
