#!/usr/bin/env python3
"""Exp 266b dev scorer: 49 own dev dialogs on 138m vs 266 vs 266b.

usage:
  claude_266b_devscore.py run --arm 138m|266|266b --dialogs <json> --out <json>
  claude_266b_devscore.py judge --m <138m.json> --n266 <266.json>
      --n266b <266b.json> --dialogs <json> [--out <json>]

judge classes per last reply: RIGHT (holds `value`), MISS ("didn't understand"),
ABSTAIN ("don't know"), else OTHER. Checks: every reply class equals its
expect on all three arms; every `same` dialog byte-identical between 266 and
266b; 0 question writes on any arm (nb.events unchanged across any ?-turn);
equal event counts per dialog across all three arms. Exit 0 iff all pass.
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
    elif arm == "266b":
        import claude_loop266b_agent as A
        cfg = copy.deepcopy(A.DEFAULT_CONFIG266B)
        cfg["state_dir"] = state_dir
        return A.build_agent266b(cfg)
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
        root = tempfile.mkdtemp(prefix=f"dev266b-{args.arm}-")
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
    if "don't know" in r or "do not know" in r \
            or "not someone i can look up" in r:
        # The last pattern is the base 138m reasoner's honest-abstain
        # template for a missing leaf under a three-word-base chain
        # (e.g. "Del Ray Okoro's coach is Reno, which is not someone I
        # can look up."): no guess, no value, no write. Seen on 138m
        # itself for the canonical possessive question, so it is base
        # behaviour served through, not a 266b wording.
        return "ABSTAIN"
    if "didn't understand" in r:
        return "MISS"
    return "OTHER"


def cmd_judge(args) -> int:
    dialogs = json.loads(Path(args.dialogs).read_text(encoding="utf-8"))
    m = json.loads(Path(args.m).read_text(encoding="utf-8"))
    n = json.loads(Path(args.n266).read_text(encoding="utf-8"))
    b = json.loads(Path(args.n266b).read_text(encoding="utf-8"))
    fails, rows = [], []
    qwrites = 0
    for d in dialogs:
        id = d["id"]
        mr, nr, br = m[id]["replies"], n[id]["replies"], b[id]["replies"]
        me, ne, be = m[id]["events"], n[id]["events"], b[id]["events"]
        ok = True
        notes = []
        last = len(d["turns"]) - 1
        cm = classify(mr[last], d["value"])
        cn = classify(nr[last], d["value"])
        cb = classify(br[last], d["value"])
        if cm != d["expect138"]:
            ok = False
            notes.append(f"last 138m {cm}!=expect {d['expect138']}: {mr[last]!r}")
        if cn != d["expect266"]:
            ok = False
            notes.append(f"last 266 {cn}!=expect {d['expect266']}: {nr[last]!r}")
        if cb != d["expect266b"]:
            ok = False
            notes.append(f"last 266b {cb}!=expect {d['expect266b']}: {br[last]!r}")
        for i, t in enumerate(d["turns"]):
            if t.strip().endswith("?"):
                before_m = me[i - 1] if i else 0
                before_n = ne[i - 1] if i else 0
                before_b = be[i - 1] if i else 0
                if me[i] != before_m or ne[i] != before_n or be[i] != before_b:
                    ok = False
                    qwrites += 1
                    notes.append(f"t{i} QUESTION WRITE m{before_m}->{me[i]} "
                                 f"n{before_n}->{ne[i]} b{before_b}->{be[i]}")
        if d["same"] and not (nr == br):
            ok = False
            notes.append(f"same-dialog 266 vs 266b differ: {nr!r} vs {br!r}")
        if not (me == ne == be):
            ok = False
            notes.append(f"event counts differ: {me} vs {ne} vs {be}")
        rows.append((id, "ok" if ok else "FAIL", notes, mr, nr, br))
        if not ok:
            fails.append(id)
    print(f"dialogs={len(dialogs)} fails={len(fails)} question_writes={qwrites}")
    for id, st, notes, mr, nr, br in rows:
        if st == "FAIL":
            print(f"FAIL {id}")
            for x in notes:
                print(f"    {x}")
    moved = [id for id, st, _, _, _, _ in rows
             for d in dialogs if d["id"] == id and st == "ok"
             and n[id]["replies"] != b[id]["replies"]]
    print(f"moved 266->266b (expected lifts): {len(moved)} {moved}")
    if args.out:
        Path(args.out).write_text(json.dumps(
            [{"id": id, "status": st, "notes": notes,
              "replies138m": mr, "replies266": nr, "replies266b": br}
             for id, st, notes, mr, nr, br in rows], indent=1), encoding="utf-8")
    return 0 if not fails else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Exp 266b dev scorer")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--arm", required=True)
    r.add_argument("--dialogs", required=True)
    r.add_argument("--out", required=True)
    j = sub.add_parser("judge")
    j.add_argument("--m", required=True)
    j.add_argument("--n266", required=True)
    j.add_argument("--n266b", required=True)
    j.add_argument("--dialogs", required=True)
    j.add_argument("--out", default=None)
    args = p.parse_args(argv)
    if args.cmd == "run":
        return cmd_run(args)
    return cmd_judge(args)


if __name__ == "__main__":
    sys.exit(main())
