#!/usr/bin/env python3
"""Experiment 166 -- T1/T2 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN expectations (artifacts/fable-me166-20260922/cases166.json,
52 rows), runs each case through a FRESH in-process loop166 (teaches in
order, then each ask in the same loop). Rows flagged identical_to_base also
run through a FRESH loop162b: stored triples AND the teach reply AND every
ask reply must be byte-identical to the base agent.

First-person rows: stored triples must equal expect (or stay empty for
"nowrite"), the last teach reply must match teach_reply (saved/already/any),
every ask reply must contain want, and NO reply on any row (except the
literal-USER control O13, which is identical to base by construction) may
contain the raw USER key.

Verdicts: OK / MISSED / WRONG-WRITE / WRONG-REPLY / ASK-FAIL / BASE-DIFF /
USER-LEAK / HARNESS-ERROR. Every seed/case reported, never averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix166_probe.py \\
    --out artifacts/fable-me166-20260922/probe166-loop166.json
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

import fable_fix166_me as M166  # noqa: E402 (raw-key scan, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)

ROOT = SCRIPTS.parent
ART166 = ROOT / "artifacts" / "fable-me166-20260922"

SAVED_MARK = "Saved:"
ALREADY_MARK = "already have that"
# O13 teaches/asks the literal string USER; its replies match base
# byte-identically and may contain the raw key by construction.
LEAK_EXEMPT = {"O13"}


def teach_reply_ok(kind: str | None, reply: str) -> bool:
    if kind in (None, "any"):
        return True
    if kind == "saved":
        return SAVED_MARK in reply
    if kind == "already":
        return ALREADY_MARK in reply
    return True


def drive(row: dict, build_fn):
    """Run teaches + asks through a fresh loop. Returns (replies, stored, asks)."""
    with tempfile.TemporaryDirectory(prefix=row["id"] + "_") as tmp:
        loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        replies = [" ".join(loop.turn(t)) for t in row.get("teaches", [])]
        stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        ask_out = [{"q": a["q"], "want": a.get("want"),
                    "reply": " ".join(loop.turn(a["q"]))}
                   for a in row.get("asks", [])]
    return replies, stored, ask_out


def run_case(row: dict, build_new, build_base) -> dict:
    t0 = time.time()
    try:
        replies, stored, ask_out = drive(row, build_new)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"],
                "verdict": "HARNESS-ERROR",
                "reply": f"NEW-CAUGHT {exc!r}",
                "seconds": round(time.time() - t0, 3)}
    base_replies, base_stored, base_asks = None, None, None
    if row.get("identical_to_base"):
        try:
            base_replies, base_stored, base_asks = drive(row, build_base)
        except Exception as exc:  # noqa: BLE001
            return {"id": row["id"], "group": row["group"],
                    "verdict": "HARNESS-ERROR",
                    "reply": f"BASE-CAUGHT {exc!r}",
                    "seconds": round(time.time() - t0, 3)}
        if (stored != base_stored or replies != base_replies
                or [a["reply"] for a in ask_out]
                != [a["reply"] for a in base_asks]):
            return {"id": row["id"], "group": row["group"],
                    "teaches": row.get("teaches", []),
                    "stored": stored, "base_stored": base_stored,
                    "replies": replies, "base_replies": base_replies,
                    "asks": ask_out,
                    "base_asks": base_asks, "verdict": "BASE-DIFF",
                    "seconds": round(time.time() - t0, 3)}
    if row["id"] not in LEAK_EXEMPT:
        leaked = [r for r in replies + [a["reply"] for a in ask_out]
                  if M166.USER_KEY in (r or "")]
        if leaked:
            return {"id": row["id"], "group": row["group"],
                    "teaches": row.get("teaches", []),
                    "stored": stored, "replies": replies, "asks": ask_out,
                    "verdict": "USER-LEAK",
                    "seconds": round(time.time() - t0, 3)}
    exp = row.get("expect")
    verdict = None
    if exp is None:
        verdict = "OK"
    elif exp == "nowrite":
        if stored:
            verdict = "WRONG-WRITE"
        elif not teach_reply_ok(row.get("teach_reply"), replies[-1]
                                if replies else ""):
            verdict = "WRONG-REPLY"
        else:
            bad = [a for a in ask_out
                   if a.get("want") and a["want"] not in (a["reply"] or "")]
            verdict = "ASK-FAIL" if bad else "OK"
    else:
        want = [list(t) for t in exp] if (isinstance(exp, list) and exp
                                          and isinstance(exp[0], list)) \
            else [list(exp)]
        if stored != want:
            verdict = "WRONG-WRITE" if stored else "MISSED"
        elif not teach_reply_ok(row.get("teach_reply"), replies[-1]
                                if replies else ""):
            verdict = "WRONG-REPLY"
        else:
            bad = [a for a in ask_out
                   if a.get("want") and a["want"] not in (a["reply"] or "")]
            verdict = "ASK-FAIL" if bad else "OK"
    return {"id": row["id"], "group": row["group"],
            "teaches": row.get("teaches", []),
            "expect": exp, "teach_reply": row.get("teach_reply"),
            "asks": ask_out, "stored": stored,
            "reply": replies[-1] if replies else "",
            "verdict": verdict, "seconds": round(time.time() - t0, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 166 T1/T2 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop162b_agent as L162B  # noqa: E402 (base agent, read-only)
    import fable_loop166_agent as L166  # noqa: E402 (this experiment)
    cfg_new = copy.deepcopy(L166.DEFAULT_CONFIG166)
    cfg_base = copy.deepcopy(L162B.DEFAULT_CONFIG162B)
    build_new = lambda c: L166.build_agent166(dict(cfg_new, **c))  # noqa: E731
    build_base = lambda c: L162B.build_agent162b(dict(cfg_base, **c))  # noqa: E731
    cases = json.loads((ART166 / "cases166.json").read_text(
        encoding="utf-8"))
    t0 = time.time()
    out = [run_case(row, build_new, build_base) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    fp = [r for r, row in zip(out, cases) if row["group"] == "first-person"]
    ident = [(r, row) for r, row in zip(out, cases)
             if row.get("identical_to_base")]
    payload = {"agent": "loop166", "cases_file": "cases166.json",
               "wall_seconds": wall, "counts": counts,
               "first_person_ok": sum(1 for r in fp
                                      if r["verdict"] == "OK"),
               "first_person_n": len(fp),
               "identical_ok": sum(1 for r, _ in ident
                                   if r["verdict"] == "OK"),
               "identical_n": len(ident),
               "wrong_writes": sum(1 for r in out
                                   if r["verdict"] == "WRONG-WRITE"),
               "cases": out}
    dest = Path(args.out) if args.out else ART166 / "probe166-loop166.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent=loop166 n={len(out)} counts={counts} "
          f"first_person={payload['first_person_ok']}/{len(fp)} "
          f"identical={payload['identical_ok']}/{len(ident)} wall={wall}s")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
