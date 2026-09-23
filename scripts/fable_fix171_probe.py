#!/usr/bin/env python3
"""Exp 171 T1 probe runner -- sealed 76-case probe through loop171.

Usage (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix171_probe.py

Case kinds (each case runs on a FRESH in-process loop):
  clarify  (32): one description teach on a name relation -> the exact
           sealed clarify, 0 writes; then a follow-up ask -> finds nothing
           saved (unknown-subject reply, still 0 writes/facts).
  identical (44): 22 real-name teaches + 20 non-name-relation teaches +
           2 two-turn corrections -> replies AND final triples
           byte-identical to loop138d on a fresh loop with the same turns.

T2 (0 wrong writes): every clarify case writes 0 facts; every identical
case writes exactly the taught values (value equality turn by turn).

Self-checks (fail loudly, protect the seal): every clarify value's first
word IS in WORDS/determiners/adverbs; every real-name value's first word
is NOT. Exits nonzero on any case FAIL. Writes probe171.json.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix171_nameval as N171  # noqa: E402 (guard under test)
import fable_loop138d_agent as L138d  # noqa: E402 (base, read-only)
import fable_loop171_agent as L171  # noqa: E402 (agent under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-nameval171-20260922"


def fresh(kind: str):
    d = Path(tempfile.mkdtemp(prefix=f"loop171probe-{kind}-"))
    if kind == "171":
        cfg = copy.deepcopy(L171.DEFAULT_CONFIG171)
        cfg["state_dir"] = str(d)
        cfg["sleep_threshold"] = 100000
        return L171.build_agent171(cfg)
    cfg = copy.deepcopy(L138d.DEFAULT_CONFIG138D)
    cfg["state_dir"] = str(d)
    cfg["sleep_threshold"] = 100000
    return L138d.build_agent138d(cfg)


def triples(loop) -> list:
    return sorted(L90.notebook_triples(loop.nb))


def main() -> int:
    cases = json.loads((ART / "cases171.json").read_text(encoding="utf-8"))
    t0 = time.time()
    rows: list[dict] = []
    rc = 0
    for case in cases:
        cid, kind = case["id"], case["kind"]
        if kind == "clarify":
            loop = fresh("171")
            ev0 = len(loop.nb.events)
            reply = loop.turn(case["teach"])
            exp = N171.clarify_for(case["name"], case["relation"])
            ok_reply = (reply == [exp])
            ok_write = (len(loop.nb.events) == ev0
                        and loop.counters["writes"] == 0)
            # Self-check: the value really is description-shaped.
            first = N171.first_word(case["value"])
            shaped = (first in N171.DETERMINERS
                      or first in N171.PLACE_TIME_ADVERBS
                      or first in N171.WORDS())
            ask_reply = loop.turn(case["followup"])
            ok_find = ("don't know" in " ".join(ask_reply).lower()
                       and len(loop.nb.events) == ev0
                       and triples(loop) == [])
            ok = ok_reply and ok_write and shaped and ok_find
            if not ok:
                rc = 1
            rows.append({"id": cid, "kind": kind, "ok": ok,
                         "reply_ok": ok_reply, "nowrite_ok": ok_write,
                         "shaped_ok": shaped, "followup_ok": ok_find,
                         "reply": reply, "ask_reply": ask_reply,
                         "expected": exp})
        elif kind == "identical":
            loop171, loop138 = fresh("171"), fresh("138")
            ok = True
            got171, got138 = [], []
            for t in case["turns"]:
                r171, r138 = loop171.turn(t), loop138.turn(t)
                got171.append(r171)
                got138.append(r138)
                if r171 != r138:
                    ok = False
            if triples(loop171) != triples(loop138):
                ok = False
            # Self-checks (fail loudly, protect the seal).
            if case.get("sub") == "name":
                # Real-name values really are name-shaped.
                for v in case.get("values", []):
                    first = N171.first_word(v)
                    if (first in N171.DETERMINERS
                            or first in N171.PLACE_TIME_ADVERBS
                            or first in N171.WORDS()):
                        ok = False
            else:
                # Non-name cases really are off the name list: parse each
                # turn on a dry 138d ears (hear is pure, writes nothing).
                dry = fresh("138")
                for t in case["turns"]:
                    for a in dry.ears.hear(t):
                        if (isinstance(a, dict)
                                and a.get("act") in ("teach", "correct")
                                and str(a.get("relation")) in N171.NAME_KEYS):
                            ok = False
            # T2: identical cases wrote exactly the taught values.
            vals171 = sorted(v for _, _, v in triples(loop171))
            if sorted(case.get("values", [])) != vals171:
                ok = False
            if not ok:
                rc = 1
            rows.append({"id": cid, "kind": kind, "ok": ok,
                         "turns": case["turns"], "got171": got171,
                         "got138": got138, "triples171": triples(loop171),
                         "triples138": triples(loop138)})
        else:
            rc = 1
            rows.append({"id": cid, "kind": kind, "ok": False,
                         "note": "unknown kind"})
    n_ok = sum(1 for r in rows if r["ok"])
    out = {"seconds": round(time.time() - t0, 1), "n": len(rows),
           "ok": n_ok, "rc": rc, "rows": rows}
    (ART / "probe171.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    kinds: dict = {}
    for r in rows:
        kinds.setdefault(r["kind"], [0, 0])
        kinds[r["kind"]][1] += 1
        kinds[r["kind"]][0] += int(r["ok"])
    print(f"T1 probe: {n_ok}/{len(rows)} ok {kinds} "
          f"({out['seconds']}s)", flush=True)
    for r in rows:
        if not r["ok"]:
            print(f"  FAIL {r['id']}: {json.dumps(r)[:400]}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
