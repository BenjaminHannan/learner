#!/usr/bin/env python3
"""Exp 226 driver + judge.

run:   --agent A --config CFG --cases cases226.json --work DIR --out rows.json
       (in-process daemon per session via fable_marks123_all.make_daemon,
       isolated scratch notebook under DIR; "<RESTART>" rebuilds the daemon
       on the same directory)
judge: --judge --base rows138i.json --new rows226.json --cases cases226.json
       P1 source turns == expected (exact string), new agent
       P2 non-source turns: reply + stored taught triples byte-identical
          to base (138i)
       P5 source turns add 0 notebook events (new agent); stored triples
          after every turn identical to base (0 new wrong writes)
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))


def run(agent, config, cases, work, out):
    import fable_marks123_all as M
    import fable_loop90_agent as L90
    _mod, dcls, _b, _c = M.load_agent(agent)
    base = M.load_base_cfg(config)
    sessions = json.loads(Path(cases).read_text(encoding="utf-8"))
    rows = []
    for sess in sessions:
        root = Path(work) / sess["id"]
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        d = M.make_daemon(dcls, base, root)
        turns = []
        for j, t in enumerate(sess["turns"]):
            if t["text"] == "<RESTART>":
                d = M.make_daemon(dcls, base, root)
                turns.append({"text": "<RESTART>"})
                continue
            ev0 = len(d.loop.nb.events)
            f = root / "inbox" / f"m{j:02d}.txt"
            f.write_text(t["text"], encoding="utf-8")
            d.process_file(f)
            reply = (root / "outbox" / f"m{j:02d}.txt").read_text(
                encoding="utf-8").strip()
            turns.append({"text": t["text"], "reply": reply,
                          "events_added": len(d.loop.nb.events) - ev0,
                          "triples": [list(x) for x in
                                      L90.notebook_triples(d.loop.nb)],
                          "n_facts": len(d.loop.nb.facts)})
        rows.append({"id": sess["id"], "type": sess["type"], "turns": turns})
        print(sess["id"], "done", flush=True)
    Path(out).write_text(json.dumps(rows, indent=1, ensure_ascii=False),
                         encoding="utf-8")


def judge(base_p, new_p, cases_p):
    base = {r["id"]: r for r in json.loads(Path(base_p).read_text())}
    new = {r["id"]: r for r in json.loads(Path(new_p).read_text())}
    cases = json.loads(Path(cases_p).read_text())
    p1 = [0, 0]; p2 = [0, 0]; p5w = [0, 0]; p5t = [0, 0]
    fails = []
    types = {}
    for sess in cases:
        b, n = base[sess["id"]], new[sess["id"]]
        for j, t in enumerate(sess["turns"]):
            if t["text"] == "<RESTART>":
                continue
            bt, nt = b["turns"][j], n["turns"][j]
            if t["expect"] is not None:
                p1[1] += 1
                ok = nt["reply"] == t["expect"]
                p1[0] += ok
                types.setdefault(sess["type"], [0, 0])
                types[sess["type"]][1] += 1
                types[sess["type"]][0] += ok
                if not ok:
                    fails.append(f"P1 {sess['id']} t{j} {t['text']!r}: got {nt['reply']!r} want {t['expect']!r} (base {bt['reply']!r})")
                p5w[1] += 1
                p5w[0] += (nt["events_added"] == 0)
                if nt["events_added"] != 0:
                    fails.append(f"P5 {sess['id']} t{j} source turn added {nt['events_added']} events")
            else:
                p2[1] += 1
                ok = (nt["reply"] == bt["reply"] and nt["triples"] == bt["triples"])
                p2[0] += ok
                if not ok:
                    fails.append(f"P2 {sess['id']} t{j} {t['text']!r}: base {bt['reply']!r} new {nt['reply']!r} triples_equal={nt['triples']==bt['triples']}")
            p5t[1] += 1
            same = nt["triples"] == bt["triples"]
            p5t[0] += same
            if not same:
                fails.append(f"P5 {sess['id']} t{j} stored triples differ from base")
    print(f"P1 source replies exact: {p1[0]}/{p1[1]}")
    for k, v in types.items():
        print(f"   {k}: {v[0]}/{v[1]}")
    print(f"P2 non-source turns identical to 138i: {p2[0]}/{p2[1]}")
    print(f"P5 source turns with 0 notebook events: {p5w[0]}/{p5w[1]}")
    print(f"P5 turns whose stored triples equal 138i: {p5t[0]}/{p5t[1]}")
    for f in fails:
        print("FAIL", f)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent"); ap.add_argument("--config")
    ap.add_argument("--cases"); ap.add_argument("--work"); ap.add_argument("--out")
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--base"); ap.add_argument("--new")
    a = ap.parse_args()
    if a.judge:
        return judge(a.base, a.new, a.cases)
    run(a.agent, a.config, a.cases, a.work, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
