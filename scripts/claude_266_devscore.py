#!/usr/bin/env python3
"""Exp 266 dev scorer: 44 dev dialogs on 138m vs 266.

usage:
  claude_266_devscore.py run --arm 138m|266 --dialogs <json> --out <json>
  claude_266_devscore.py judge --m <138m.json> --n <266.json>
      --dialogs <json> [--out <json>]

judge classes per reply: RIGHT (holds `value`), MISS ("didn't understand"),
ABSTAIN ("don't know"), else OTHER. Checks: every reply class equals its
expect, every `same` dialog byte-identical across arms, 0 question writes
(nb.events unchanged across any ?-turn), and equal write counts per dialog.
Exit 0 iff all checks pass.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _build(arm, state_dir):
    if arm == "138m":
        import claude_loop138m_agent as A
        cfg = copy.deepcopy(A.DEFAULT_CONFIG138M)
        cfg["state_dir"] = state_dir
        return A.build_agent138m(cfg)
    elif arm == "266":
        import claude_loop266_agent as A
        cfg = copy.deepcopy(A.DEFAULT_CONFIG266)
        cfg["state_dir"] = state_dir
        return A.build_agent266(cfg)
    raise ValueError(arm)


def _nevents(loop):
    nb = loop.nb
    for o in (nb, getattr(nb, "nb", None)):
        if o is not None and hasattr(o, "events"):
            return len(o.events)
    return -1


def cmd_run(args) -> int:
    dialogs = json.loads(Path(args.dialogs).read_text(encoding="utf-8"))
    out = {}
    for d in dialogs:
        root = tempfile.mkdtemp(prefix=f"dev266-{args.arm}-")
        loop = _build(args.arm, root)
        replies, events = [], []
        for t in d["turns"]:
            replies.append(" ".join(loop.turn(t)))
            events.append(_nevents(loop))
        out[d["id"]] = {"replies": replies, "events": events}
        del loop
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"Wrote {args.out} ({len(out)} dialogs, arm {args.arm})")
    return 0


def classify(reply, value):
    r = reply.lower()
    if value and value in reply:
        return "RIGHT"
    if "don't know" in r or "do not know" in r:
        return "ABSTAIN"
    if "didn't understand" in r:
        return "MISS"
    return "OTHER"


def cmd_judge(args) -> int:
    dialogs = json.loads(Path(args.dialogs).read_text(encoding="utf-8"))
    m = json.loads(Path(args.m).read_text(encoding="utf-8"))
    n = json.loads(Path(args.n).read_text(encoding="utf-8"))
    fails, rows = [], []
    qwrites = 0
    for d in dialogs:
        id = d["id"]
        mr, nr = m[id]["replies"], n[id]["replies"]
        me, ne = m[id]["events"], n[id]["events"]
        ok = True
        notes = []
        last = len(d["turns"]) - 1
        cm = classify(mr[last], d["value"])
        cn = classify(nr[last], d["value"])
        if cm != d["expect138"]:
            ok = False
            notes.append(f"last 138m {cm}!=expect {d['expect138']}: {mr[last]!r}")
        if cn != d["expect266"]:
            ok = False
            notes.append(f"last 266 {cn}!=expect {d['expect266']}: {nr[last]!r}")
        for i, t in enumerate(d["turns"]):
            if t.strip().endswith("?"):
                before_m = me[i - 1] if i else 0
                before_n = ne[i - 1] if i else 0
                if me[i] != before_m or ne[i] != before_n:
                    ok = False
                    qwrites += 1
                    notes.append(f"t{i} QUESTION WRITE m{before_m}->{me[i]} "
                                 f"n{before_n}->{ne[i]}")
        if d["same"] and mr != nr:
            ok = False
            notes.append(f"same-dialog replies differ: {mr!r} vs {nr!r}")
        if me != ne:
            ok = False
            notes.append(f"event counts differ: {me} vs {ne}")
        rows.append((id, "ok" if ok else "FAIL", notes, mr, nr))
        if not ok:
            fails.append(id)
    print(f"dialogs={len(dialogs)} fails={len(fails)} question_writes={qwrites}")
    for id, st, notes, mr, nr in rows:
        if st == "FAIL":
            print(f"FAIL {id}")
            for x in notes:
                print(f"    {x}")
    moved = [id for id, st, _, _, _ in rows
             for d in dialogs if d["id"] == id and st == "ok"
             and m[id]["replies"] != n[id]["replies"]]
    print(f"moved (expected lifts): {len(moved)} {moved}")
    if args.out:
        Path(args.out).write_text(json.dumps(
            [{"id": id, "status": st, "notes": notes,
              "replies138m": mr, "replies266": nr}
             for id, st, notes, mr, nr in rows], indent=1), encoding="utf-8")
    return 0 if not fails else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Exp 266 dev scorer")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--arm", required=True)
    r.add_argument("--dialogs", required=True)
    r.add_argument("--out", required=True)
    j = sub.add_parser("judge")
    j.add_argument("--m", required=True)
    j.add_argument("--n", required=True)
    j.add_argument("--dialogs", required=True)
    j.add_argument("--out", default=None)
    args = p.parse_args(argv)
    if args.cmd == "run":
        return cmd_run(args)
    return cmd_judge(args)


if __name__ == "__main__":
    sys.exit(main())
