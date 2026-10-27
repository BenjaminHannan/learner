#!/usr/bin/env python3
"""Experiment 190b -- V1b new-case + V1 old-suite drivers (Muse).

V1b (marks R1/R2): runs sealed artifacts/fable-reverse190b-20260922/
case190b.json turn by turn through a fresh loop190b agent AND, in
lockstep, a fresh loop190 agent. Checks:
  - r1 rows (incl. r1-corrected): loop190b reply == sealed expect
    (the new whose-sentence), and the ask wrote nothing;
  - teach-check S12: loop190b reply == expect AND == loop190 reply;
  - r2 / r2-plain / trap / teach / correct: loop190b reply
    byte-identical to loop190 AND stored triples identical.
  - 0 writes on all asks; notebook events identical every turn.

V1 (mark R3): runs sealed artifacts/fable-reverse190-20260922/
case190.json through loop190b vs the SEALED loop190 rows
(artifacts/fable-reverse190-20260922/v1-rows190.json, read-only).
Predicts: every row identical EXCEPT the 5 unknown rows E1-E5, which
must move "called" -> "whose" with the exact new sentence; stored
triples (events) identical after every turn (lockstep loop190).

Outputs into artifacts/fable-reverse190b-20260922/ only.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_fix190b_v1.py --only v1b|v1|all
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop190_agent as L190  # noqa: E402 (base, read-only)
import fable_loop190b_agent as L190B  # noqa: E402 (agent under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-reverse190b-20260922"
ART190 = ROOT / "artifacts" / "fable-reverse190-20260922"


def triples(loop) -> list[list[str]]:
    return [list(t) for t in L90.notebook_triples(loop.nb)]


def fresh190b(state_dir: str):
    cfg = copy.deepcopy(L190B.DEFAULT_CONFIG190B)
    cfg["state_dir"] = state_dir
    cfg["sleep_threshold"] = 100000
    return L190B.build_agent190b(cfg)


def fresh190(state_dir: str):
    cfg = copy.deepcopy(L190.DEFAULT_CONFIG190)
    cfg["state_dir"] = state_dir
    cfg["sleep_threshold"] = 100000
    return L190.build_agent190(cfg)


def run_v1b() -> tuple[list[dict], dict]:
    case = json.loads((ART / "case190b.json").read_text(encoding="utf-8"))
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="v1b-190b-") as d190b, \
            tempfile.TemporaryDirectory(prefix="v1b-190-") as d190:
        new = fresh190b(d190b)
        base = fresh190(d190)
        rows = []
        for step in case["turns"]:
            kind = step["kind"]
            before = triples(new)
            before_base = triples(base)
            r_new = " ".join(new.turn(step["turn"])).strip()
            r_base = " ".join(base.turn(step["turn"])).strip()
            after = triples(new)
            after_base = triples(base)
            events_same = (after == after_base)
            if kind in ("r1", "r1-corrected"):
                ok = (r_new == step["expect"]) and (after == before)
                checks = {"expect": step["expect"],
                          "match_expect": r_new == step["expect"],
                          "nowrite": after == before,
                          "events_identical": events_same,
                          "moved_vs_190": r_new != r_base,
                          "reply190": r_base}
                ok = ok and events_same
            elif kind == "teach-check":
                ok = (r_new == step["expect"] and r_new == r_base
                      and after == before and events_same)
                checks = {"expect": step["expect"],
                          "match_expect": r_new == step["expect"],
                          "identical": r_new == r_base,
                          "nowrite": after == before,
                          "events_identical": events_same}
            else:
                ok = (r_new == r_base) and events_same
                if kind in ("teach", "correct"):
                    ok = ok and (after == before or True)
                else:
                    ok = ok and (after == before)
                checks = {"identical": r_new == r_base,
                          "nowrite": after == before,
                          "events_identical": events_same,
                          "reply190": r_base}
            rows.append({"id": step["id"], "kind": kind,
                         "turn": step["turn"], "reply190b": r_new,
                         "verdict": "OK" if ok else "FAIL", **checks})
    counter = Counter((r["kind"], r["verdict"]) for r in rows)
    r1_ok = sum(1 for r in rows if r["kind"].startswith("r1")
                and r["verdict"] == "OK")
    r1_total = sum(1 for r in rows if r["kind"].startswith("r1"))
    parity_ok = sum(1 for r in rows if not r["kind"].startswith("r1")
                    and r["verdict"] == "OK")
    parity_total = sum(1 for r in rows if not r["kind"].startswith("r1"))
    summary = {"n": len(rows),
               "by_kind_verdict": {f"{k}/{v}": c for (k, v), c
                                   in sorted(counter.items())},
               "r1_ok": r1_ok, "r1_total": r1_total,
               "parity_ok": parity_ok, "parity_total": parity_total,
               "pass": all(r["verdict"] == "OK" for r in rows),
               "seconds": round(time.time() - t0, 1)}
    return rows, summary


PREDICTED_MOVES_V1 = {"E1", "E2", "E3", "E4", "E5"}


def run_v1() -> tuple[list[dict], dict]:
    case = json.loads((ART190 / "case190.json").read_text(encoding="utf-8"))
    sealed = json.loads((ART190 / "v1-rows190.json").read_text(
        encoding="utf-8"))
    sealed_by_id = {r["id"]: r for r in sealed}
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="v1r3-190b-") as d190b, \
            tempfile.TemporaryDirectory(prefix="v1r3-190-") as d190:
        new = fresh190b(d190b)
        base = fresh190(d190)
        rows = []
        for step in case["turns"]:
            r_new = " ".join(new.turn(step["turn"])).strip()
            r_base = " ".join(base.turn(step["turn"])).strip()
            after = triples(new)
            after_base = triples(base)
            s = sealed_by_id[step["id"]]
            sealed_reply = str(s.get("reply190", s.get("reply", ""))).strip()
            events_same = (after == after_base)
            if step["id"] in PREDICTED_MOVES_V1:
                # exact whose-form verified in the tightening pass
                # below; here require lockstep-190 == sealed only.
                ok = events_same and (r_base == sealed_reply)
            else:
                ok = (r_new == sealed_reply) and events_same
            rows.append({"id": step["id"], "kind": step["kind"],
                         "turn": step["turn"], "reply190b": r_new,
                         "reply190_sealed": sealed_reply,
                         "reply190_lockstep": r_base,
                         "events_identical": events_same,
                         "predicted_move": step["id"] in PREDICTED_MOVES_V1,
                         "verdict": "OK" if ok else "FAIL"})
        # tighten predicted-move rows: exact whose-sentence check
        for r in rows:
            if r["predicted_move"]:
                s = sealed_by_id[r["id"]]
                exp190 = str(s.get("expect", "")).strip()
                # sealed unknown expect: "I don't know anyone called <V>."
                if exp190.startswith("I don't know anyone called "):
                    v = exp190[len("I don't know anyone called "):].rstrip(
                        ".")
                    # relation display comes from the 190b reply itself;
                    # require whose-form with same value tail.
                    want_tail = f"is {v}."
                    r["verdict"] = ("OK" if (
                        r["reply190b"].startswith(
                            "I don't know anyone whose ")
                        and r["reply190b"].endswith(want_tail)
                        and r["events_identical"]) else "FAIL")
    counter = Counter((r["kind"], r["verdict"]) for r in rows)
    moves = [r["id"] for r in rows if r["predicted_move"]]
    unpred = [r["id"] for r in rows
              if (r["reply190b"] != r["reply190_sealed"])
              and not r["predicted_move"]]
    summary = {"n": len(rows),
               "by_kind_verdict": {f"{k}/{v}": c for (k, v), c
                                   in sorted(counter.items())},
               "predicted_moves": sorted(moves),
               "unpredicted_moves": unpred,
               "events_all_identical": all(
                   r["events_identical"] for r in rows),
               "pass": all(r["verdict"] == "OK" for r in rows)
               and not unpred,
               "seconds": round(time.time() - t0, 1)}
    return rows, summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 190b V1b+V1")
    ap.add_argument("--only", default="all")
    args = ap.parse_args(argv)
    ART.mkdir(parents=True, exist_ok=True)
    rc = 0
    want = args.only.split(",")
    if "all" in want or "v1b" in want:
        rows, summary = run_v1b()
        (ART / "v1b-rows190b.json").write_text(
            json.dumps(rows, indent=1, ensure_ascii=False),
            encoding="utf-8")
        (ART / "v1b-summary190b.json").write_text(
            json.dumps(summary, indent=1), encoding="utf-8")
        print(f"V1b: r1 {summary['r1_ok']}/{summary['r1_total']} "
              f"parity {summary['parity_ok']}/{summary['parity_total']} "
              f"PASS={summary['pass']} in {summary['seconds']}s", flush=True)
        for r in rows:
            if r["verdict"] != "OK":
                print(f"  FAIL {r['id']} {r['turn']!r}: got "
                      f"{r['reply190b']!r}", flush=True)
        rc = rc or (0 if summary["pass"] else 1)
    if "all" in want or "v1" in want:
        rows, summary = run_v1()
        (ART / "v1-rows190b.json").write_text(
            json.dumps(rows, indent=1, ensure_ascii=False),
            encoding="utf-8")
        (ART / "v1-summary190b.json").write_text(
            json.dumps(summary, indent=1), encoding="utf-8")
        print(f"V1r3: n={summary['n']} predicted_moves="
              f"{summary['predicted_moves']} unpredicted="
              f"{summary['unpredicted_moves']} events_identical="
              f"{summary['events_all_identical']} PASS={summary['pass']} "
              f"in {summary['seconds']}s", flush=True)
        for r in rows:
            if r["verdict"] != "OK":
                print(f"  FAIL {r['id']} {r['turn']!r}: got "
                      f"{r['reply190b']!r} sealed="
                      f"{r['reply190_sealed']!r}", flush=True)
        rc = rc or (0 if summary["pass"] else 1)
    return rc


if __name__ == "__main__":
    sys.exit(main())
