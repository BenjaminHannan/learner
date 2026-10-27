#!/usr/bin/env python3
"""Experiment 167d -- T1 sealed probe + T2 loop167b-probe identity (Muse).

T1: reads FROZEN expectations (artifacts/fable-verb167d-20260922/
cases167d.json, 32 rows), runs each case through a FRESH in-process
loop167d (temp state dir). Teach rows (verb form): verb teach must
store the expected triple; the teach reply must equal expect_reply
EXACTLY; every ask must contain its want; and the possessive-twin
teach through a FRESH base loop167b must store the IDENTICAL triple
list. Ask-after-possessive rows: possessive teach stores the triple,
verb questions answer it. Trap rows (expect nowrite): 0 stored triples
and the reply must equal expect_reply EXACTLY (the base clarify).

T2: runs loop167b's OWN sealed probe
(artifacts/fable-verb167b-20260922/cases167b.json, 64 rows) through a
FRESH loop167d and requires per-case identity with the sealed
registered output
(artifacts/fable-verb167b-20260922/probe167b-loop167b.json): same
stored triples, same teach reply, same ask replies. The added 167d
shapes are disjoint from every 167b-claimed shape, so all 64 must be
identical.

Verdicts T1: OK / MISSED / WRONG-WRITE / WRONG-REPLY / ASK-FAIL /
TWIN-DIFF / HARNESS-ERROR. T2: IDENTICAL / DIFF / HARNESS-ERROR.
Every seed/case reported, never averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix167d_probe.py \\
    --out artifacts/fable-verb167d-20260922/probe167d-loop167d.json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)

ROOT = SCRIPTS.parent
ART167D = ROOT / "artifacts" / "fable-verb167d-20260922"
ART167B = ROOT / "artifacts" / "fable-verb167b-20260922"

DIDNT_MARK = "didn't understand"
SAVED_MARK = "Saved:"


def reply_ok(kind: str | None, reply: str) -> bool:
    if kind in (None, "any"):
        return True
    if kind == "didnt":
        return DIDNT_MARK in reply
    if kind == "saved":
        return SAVED_MARK in reply
    return True


def drive(row: dict, build_fn):
    """Run teaches + asks through a fresh loop. Returns (reply, stored, asks)."""
    with tempfile.TemporaryDirectory(prefix=row["id"] + "_") as tmp:
        loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        teaches = row.get("teaches", [row.get("teach", "")])
        replies = [" ".join(loop.turn(t)) for t in teaches]
        reply = replies[-1] if replies else ""
        stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        asks = row.get("asks", [])
        if row.get("ask") and not asks:
            asks = [{"q": row["ask"], "want": row.get("want")}]
        ask_out = []
        if row.get("expect") != "nowrite":
            for a in asks:
                ask_out.append({"q": a["q"], "want": a.get("want"),
                                "reply": " ".join(loop.turn(a["q"]))})
    return reply, stored, ask_out


def drive_twins(row: dict, build_base):
    """Run the possessive twin teach(es) through a fresh BASE loop."""
    twins = row.get("twins", [row.get("twin", "")])
    with tempfile.TemporaryDirectory(prefix=row["id"] + "_twin_") as tmp:
        loop = build_base({"state_dir": tmp, "sleep_threshold": 100000})
        for t in twins:
            loop.turn(t)
        return [list(t) for t in L90.notebook_triples(loop.nb)]


def run_case(row: dict, build_new, build_base) -> dict:
    t0 = time.time()
    try:
        reply, stored, ask_out = drive(row, build_new)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"],
                "verdict": "HARNESS-ERROR",
                "reply": f"NEW-CAUGHT {exc!r}",
                "seconds": round(time.time() - t0, 3)}
    if row.get("twin") or row.get("twins"):
        try:
            twin_stored = drive_twins(row, build_base)
        except Exception as exc:  # noqa: BLE001
            return {"id": row["id"], "group": row["group"],
                    "verdict": "HARNESS-ERROR",
                    "reply": f"TWIN-CAUGHT {exc!r}",
                    "seconds": round(time.time() - t0, 3)}
        if stored != twin_stored:
            return {"id": row["id"], "group": row["group"],
                    "teaches": row.get("teaches", [row.get("teach", "")]),
                    "stored": stored, "twin_stored": twin_stored,
                    "reply": reply, "verdict": "TWIN-DIFF",
                    "seconds": round(time.time() - t0, 3)}
    exp = row.get("expect")
    want_reply = row.get("reply", "any")
    exact = row.get("expect_reply")
    verdict = None
    if exp == "nowrite":
        if stored:
            verdict = "WRONG-WRITE"
        elif exact is not None and reply != exact:
            verdict = "WRONG-REPLY"
        elif reply_ok(want_reply, reply):
            verdict = "OK"
        else:
            verdict = "WRONG-REPLY"
    else:
        if isinstance(exp, list) and exp and isinstance(exp[0], list):
            want = [list(t) for t in exp]
        else:
            want = [list(exp)]
        if stored == want:
            bad = [a for a in ask_out
                   if a.get("want") and a["want"] not in (a["reply"] or "")]
            if bad:
                verdict = "ASK-FAIL"
            elif exact is not None and reply != exact:
                verdict = "WRONG-REPLY"
            elif not reply_ok(want_reply, reply):
                verdict = "WRONG-REPLY"
            else:
                verdict = "OK"
        elif not stored:
            verdict = "MISSED"
        else:
            verdict = "WRONG-WRITE"
    return {"id": row["id"], "group": row["group"],
            "teaches": row.get("teaches", [row.get("teach", "")]),
            "expect": exp, "want_reply": want_reply,
            "asks": ask_out, "stored": stored, "reply": reply,
            "verdict": verdict, "seconds": round(time.time() - t0, 3)}


def run_t2(build_new, sealed: list[dict], cases: list[dict]) -> list[dict]:
    """Each sealed 167b probe row re-driven through loop167d; identity check."""
    out = []
    sealed_by_id = {r["id"]: r for r in sealed}
    for row in cases:
        t0 = time.time()
        base = sealed_by_id.get(row["id"])
        if base is None:
            out.append({"id": row["id"], "group": row["group"],
                        "verdict": "DIFF", "detail": "missing-sealed-row",
                        "seconds": round(time.time() - t0, 3)})
            continue
        try:
            reply, stored, ask_out = drive(row, build_new)
        except Exception as exc:  # noqa: BLE001
            out.append({"id": row["id"], "group": row["group"],
                        "verdict": "HARNESS-ERROR",
                        "detail": f"CAUGHT {exc!r}",
                        "seconds": round(time.time() - t0, 3)})
            continue
        base_asks = [(a.get("q"), a.get("reply")) for a in base.get("asks", [])]
        new_asks = [(a.get("q"), a.get("reply")) for a in ask_out]
        diffs = []
        if stored != base.get("stored"):
            diffs.append("stored")
        if reply != base.get("reply"):
            diffs.append("reply")
        if new_asks != base_asks:
            diffs.append("asks")
        out.append({"id": row["id"], "group": row["group"],
                    "verdict": "IDENTICAL" if not diffs else "DIFF",
                    "diffs": diffs, "reply": reply, "stored": stored,
                    "seconds": round(time.time() - t0, 3)})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 167d T1/T2 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop167b_agent as L167B  # noqa: E402 (twin base, read-only)
    import fable_loop167d_agent as L167D  # noqa: E402 (this experiment)
    cfg_new = copy.deepcopy(L167D.DEFAULT_CONFIG167D)
    cfg_base = copy.deepcopy(L167B.DEFAULT_CONFIG167B)
    build_new = lambda c: L167D.build_agent167d(dict(cfg_new, **c))  # noqa: E731
    build_base = lambda c: L167B.build_agent167b(dict(cfg_base, **c))  # noqa: E731
    cases = json.loads((ART167D / "cases167d.json").read_text(
        encoding="utf-8"))
    t0 = time.time()
    out = [run_case(row, build_new, build_base) for row in cases]
    wall_t1 = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    by_group: dict[str, list] = {}
    for r, row in zip(out, cases):
        by_group.setdefault(row["group"], []).append(r)
    summary = {g: {"ok": sum(1 for r in rs if r["verdict"] == "OK"),
                   "n": len(rs)} for g, rs in by_group.items()}
    t1 = time.time()
    cases_b = json.loads((ART167B / "cases167b.json").read_text(
        encoding="utf-8"))
    sealed_b = json.loads((ART167B / "probe167b-loop167b.json").read_text(
        encoding="utf-8"))["cases"]
    t2rows = run_t2(build_new, sealed_b, cases_b)
    wall_t2 = round(time.time() - t1, 1)
    t2counts: dict[str, int] = {}
    for r in t2rows:
        t2counts[r["verdict"]] = t2counts.get(r["verdict"], 0) + 1
    payload = {"agent": "loop167d", "cases_file": "cases167d.json",
               "wall_seconds": wall_t1, "counts": counts,
               "by_group": summary, "cases": out,
               "t2_cases_file": "cases167b.json",
               "t2_wall_seconds": wall_t2, "t2_counts": t2counts,
               "t2_cases": t2rows}
    dest = Path(args.out) if args.out else ART167D / "probe167d-loop167d.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"T1 agent=loop167d n={len(out)} counts={counts} "
          f"groups={summary} wall={wall_t1}s")
    print(f"T2 agent=loop167d-on-167b-cases n={len(t2rows)} "
          f"counts={t2counts} wall={wall_t2}s")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
