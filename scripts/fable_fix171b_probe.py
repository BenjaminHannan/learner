#!/usr/bin/env python3
"""Exp 171b T1+T1b+T2 probe runner -- sealed probes through loop171b.

Usage (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix171b_probe.py

Part A = T1 (artifacts/fable-nameval171-20260922/cases171.json, 76 cases,
fresh in-process loops through loop171b):
  clarify (32): the exact sealed 171 clarify, 0 writes, follow-up ask finds
    nothing -- AND the reply is byte-identical to the sealed loop171 row in
    artifacts/fable-nameval171-20260922/probe171.json (identical to loop171).
  identical (44): replies AND final triples byte-identical to loop138d on a
    fresh loop with the same turns (and equal to the sealed loop171 rows).
Part B = T1b (artifacts/fable-nameval171b-20260922/cases171b.json):
  save (16 incl W15/W16 two-token): word-name teach saves (1 write, stored
    value equal), follow-up ask answers the name.
  save-after-clarify (4: W17-W20): description teach clarifies with the
    agent's own "What is X's name?" text, the word-name answer then saves,
    follow-up ask answers it. This is the exact director scenario.
  clarify (18: C01-C12 lowercase + C13-C18 Title-case closed-list): exact
    sealed clarify, 0 writes, follow-up finds nothing.
  identical (8): byte-identical to loop138d (replies + triples).
T2 (0 wrong writes): every clarify case 0 facts; every save(-after-clarify)
case stores exactly the taught value; every identical case value-equal.
Writes probe171b_T1.json + probe171b.json into the 171b artifact folder.
Exits nonzero on any case FAIL.
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

import fable_fix171_nameval as N171  # noqa: E402 (171 rule + clarify, read-only)
import fable_fix171b_nameval as N171B  # noqa: E402 (rule under test)
import fable_loop138d_agent as L138d  # noqa: E402 (base, read-only)
import fable_loop171b_agent as L171B  # noqa: E402 (agent under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)

ROOT = SCRIPTS.parent
ART171 = ROOT / "artifacts" / "fable-nameval171-20260922"
ART = ROOT / "artifacts" / "fable-nameval171b-20260922"


def fresh(kind: str):
    d = Path(tempfile.mkdtemp(prefix=f"loop171bprobe-{kind}-"))
    if kind == "171b":
        cfg = copy.deepcopy(L171B.DEFAULT_CONFIG171B)
        cfg["state_dir"] = str(d)
        cfg["sleep_threshold"] = 100000
        return L171B.build_agent171b(cfg)
    cfg = copy.deepcopy(L138d.DEFAULT_CONFIG138D)
    cfg["state_dir"] = str(d)
    cfg["sleep_threshold"] = 100000
    return L138d.build_agent138d(cfg)


def triples(loop) -> list:
    return [list(t) for t in sorted(L90.notebook_triples(loop.nb))]


def facts(loop) -> list:
    return sorted(v for _, _, v in triples(loop))


def run_t1() -> tuple[list[dict], int]:
    cases = json.loads((ART171 / "cases171.json").read_text(encoding="utf-8"))
    sealed = {r["id"]: r for r in json.loads(
        (ART171 / "probe171.json").read_text(encoding="utf-8"))["rows"]}
    rows: list[dict] = []
    rc = 0
    for case in cases:
        cid, kind = case["id"], case["kind"]
        if kind == "clarify":
            loop = fresh("171b")
            ev0 = len(loop.nb.events)
            reply = loop.turn(case["teach"])
            exp = N171.clarify_for(case["name"], case["relation"])
            ok_reply = (reply == [exp])
            ok_write = (len(loop.nb.events) == ev0
                        and loop.counters["writes"] == 0)
            ask_reply = loop.turn(case["followup"])
            ok_find = ("don't know" in " ".join(ask_reply).lower()
                       and len(loop.nb.events) == ev0
                       and triples(loop) == [])
            ok_sealed = (sealed[cid]["reply"] == reply
                         and sealed[cid]["ask_reply"] == ask_reply)
            ok = ok_reply and ok_write and ok_find and ok_sealed
            if not ok:
                rc = 1
            rows.append({"id": cid, "kind": kind, "ok": ok,
                         "reply_ok": ok_reply, "nowrite_ok": ok_write,
                         "followup_ok": ok_find, "sealed171_ok": ok_sealed,
                         "reply": reply, "ask_reply": ask_reply})
        elif kind == "identical":
            loopB, loop138 = fresh("171b"), fresh("138")
            ok = True
            gotB, got138 = [], []
            for t in case["turns"]:
                rB, r138 = loopB.turn(t), loop138.turn(t)
                gotB.append(rB)
                got138.append(r138)
                if rB != r138:
                    ok = False
            if triples(loopB) != triples(loop138):
                ok = False
            s = sealed[cid]
            ok_sealed = (s["got171"] == gotB
                         and s["triples171"] == triples(loopB))
            ok = ok and ok_sealed
            if not ok:
                rc = 1
            rows.append({"id": cid, "kind": kind, "ok": ok,
                         "sealed171_ok": ok_sealed,
                         "turns": case["turns"], "gotB": gotB,
                         "got138": got138, "triplesB": triples(loopB),
                         "triples138": triples(loop138)})
        else:
            rc = 1
            rows.append({"id": cid, "kind": kind, "ok": False,
                         "note": "unknown kind"})
    return rows, rc


def run_t1b() -> tuple[list[dict], int]:
    cases = json.loads((ART / "cases171b.json").read_text(encoding="utf-8"))
    rows: list[dict] = []
    rc = 0
    for case in cases:
        cid, kind = case["id"], case["kind"]
        if kind == "save":
            loop = fresh("171b")
            # Self-check: 171 refuses this value; 171b must not.
            refused171 = N171.is_description_value(case["value"])
            shapedB = not N171B.is_description_value_b(case["value"])
            reply = loop.turn(case["teach"])
            ok_save = (facts(loop) == [case["value"]]
                       and loop.counters["writes"] == 1)
            ask = loop.turn(case["followup"])
            ok_ask = (case["value"] in " ".join(ask)
                      and facts(loop) == [case["value"]])
            ok = refused171 and shapedB and ok_save and ok_ask
            if not ok:
                rc = 1
            rows.append({"id": cid, "kind": kind, "ok": ok,
                         "refused171": refused171, "shapedB": shapedB,
                         "save_ok": ok_save, "ask_ok": ok_ask,
                         "reply": reply, "ask": ask,
                         "facts": facts(loop)})
        elif kind == "save-after-clarify":
            loop = fresh("171b")
            ev0 = len(loop.nb.events)
            r1 = loop.turn(case["teach1"])
            exp = N171.clarify_for(case["name"], case["relation"])
            ok_c = (r1 == [exp] and len(loop.nb.events) == ev0
                    and loop.counters["writes"] == 0)
            r2 = loop.turn(case["teach2"])
            ok_s = (facts(loop) == [case["value"]]
                    and loop.counters["writes"] == 1)
            ask = loop.turn(case["followup"])
            ok_a = (case["value"] in " ".join(ask)
                    and facts(loop) == [case["value"]])
            refused171 = N171.is_description_value(case["value"])
            ok = ok_c and ok_s and ok_a and refused171
            if not ok:
                rc = 1
            rows.append({"id": cid, "kind": kind, "ok": ok,
                         "clarify_ok": ok_c, "save_ok": ok_s,
                         "ask_ok": ok_a, "refused171": refused171,
                         "r1": r1, "r2": r2, "ask": ask,
                         "facts": facts(loop)})
        elif kind == "clarify":
            loop = fresh("171b")
            ev0 = len(loop.nb.events)
            reply = loop.turn(case["teach"])
            exp = N171.clarify_for(case["name"], case["relation"])
            ok_reply = (reply == [exp])
            ok_write = (len(loop.nb.events) == ev0
                        and loop.counters["writes"] == 0)
            refused171 = N171.is_description_value(case["value"])
            refusedB = N171B.is_description_value_b(case["value"])
            ask_reply = loop.turn(case["followup"])
            ok_find = ("don't know" in " ".join(ask_reply).lower()
                       and len(loop.nb.events) == ev0
                       and triples(loop) == [])
            ok = ok_reply and ok_write and refused171 and refusedB and ok_find
            if not ok:
                rc = 1
            rows.append({"id": cid, "kind": kind, "ok": ok,
                         "reply_ok": ok_reply, "nowrite_ok": ok_write,
                         "refused171": refused171, "refusedB": refusedB,
                         "followup_ok": ok_find, "reply": reply,
                         "ask_reply": ask_reply})
        elif kind == "identical":
            loopB, loop138 = fresh("171b"), fresh("138")
            ok = True
            gotB, got138 = [], []
            for t in case["turns"]:
                rB, r138 = loopB.turn(t), loop138.turn(t)
                gotB.append(rB)
                got138.append(r138)
                if rB != r138:
                    ok = False
            if triples(loopB) != triples(loop138):
                ok = False
            if sorted(case.get("values", [])) != facts(loopB):
                ok = False
            if not ok:
                rc = 1
            rows.append({"id": cid, "kind": kind, "ok": ok,
                         "turns": case["turns"], "gotB": gotB,
                         "got138": got138, "triplesB": triples(loopB),
                         "triples138": triples(loop138)})
        else:
            rc = 1
            rows.append({"id": cid, "kind": kind, "ok": False,
                         "note": "unknown kind"})
    return rows, rc


def main() -> int:
    t0 = time.time()
    rows1, rc1 = run_t1()
    rowsB, rcB = run_t1b()
    secs = round(time.time() - t0, 1)
    n1 = sum(1 for r in rows1 if r["ok"])
    nB = sum(1 for r in rowsB if r["ok"])
    (ART / "probe171b_T1.json").write_text(
        json.dumps({"seconds": secs, "n": len(rows1), "ok": n1,
                    "rc": rc1, "rows": rows1}, indent=1, ensure_ascii=False),
        encoding="utf-8")
    (ART / "probe171b.json").write_text(
        json.dumps({"seconds": secs, "n": len(rowsB), "ok": nB,
                    "rc": rcB, "rows": rowsB}, indent=1, ensure_ascii=False),
        encoding="utf-8")
    kinds: dict = {}
    for r in rowsB:
        kinds.setdefault(r["kind"], [0, 0])
        kinds[r["kind"]][1] += 1
        kinds[r["kind"]][0] += int(r["ok"])
    print(f"T1: {n1}/{len(rows1)} ok ({secs}s)", flush=True)
    print(f"T1b: {nB}/{len(rowsB)} ok {kinds}", flush=True)
    for r in rows1 + rowsB:
        if not r["ok"]:
            print(f"  FAIL {r['id']}: {json.dumps(r)[:400]}", flush=True)
    return 1 if (rc1 or rcB) else 0


if __name__ == "__main__":
    sys.exit(main())
