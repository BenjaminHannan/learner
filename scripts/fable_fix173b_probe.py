#!/usr/bin/env python3
"""Experiment 173b -- T1 (sealed 166 probe, byte-identical) + T1b (173's
sealed probe, identical except listed S13) + T1c (new 42-dialogue probe).

T1: artifacts/fable-me166-20260922/cases166.json (52 rows) through loop173b
  AND loop173: byte-identical (0 moves predicted).
T1b: artifacts/fable-username173-20260922/cases173.json (45 rows): 44/45
  byte-identical to loop173; S13 ("You can call me lena.") is the ONE
  listed pre-seal difference (173 names Lena; 173b requires Title-case
  after Call-me, so it clarifies with 0 writes like loop166).
T1c: artifacts/fable-username173b-20260922/cases173b.json (42 rows, fresh
  loop per row): 16 word-names save+answer; 14 closed/look-alikes 0 writes
  + identical to loop173; 6 I'm-propernames (5 new names Grace/Grant/Mark/
  Will/Rich set; Aaron identical); 6 other identical.
T2: 0 wrong writes; 0 non-USER entities from name statements.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix173b_probe.py --which t1 \\
    --out artifacts/fable-username173b-20260922/probe173b-t1.json
  ... --which t1b ... probe173b-t1b.json
  ... --which t1c ... probe173b-t1c.json
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
ART173 = ROOT / "artifacts" / "fable-username173-20260922"
ART173B = ROOT / "artifacts" / "fable-username173b-20260922"

LEAK_EXEMPT = {"O13"}
T1B_LISTED_DIFFS = {"S13"}


def drive_steps(steps, build_fn):
    with tempfile.TemporaryDirectory(prefix="p173b_") as tmp:
        loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        replies = [" ".join(loop.turn(t)) for t in steps]
        stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        try:
            entities = sorted(set(loop.nb.entities.values()))
        except Exception:  # noqa: BLE001
            entities = []
    return replies, stored, entities


def check_166_row(row, build_new, build_base):
    t0 = time.time()
    try:
        with tempfile.TemporaryDirectory(prefix="p173ba_") as tmp:
            loop = build_new({"state_dir": tmp,
                              "sleep_threshold": 100000})
            replies = [" ".join(loop.turn(t))
                       for t in row.get("teaches", [])]
            stored = [list(t) for t in L90.notebook_triples(loop.nb)]
            ask_out = [{"q": a["q"], "reply": " ".join(loop.turn(a["q"]))}
                       for a in row.get("asks", [])]
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"],
                "verdict": "HARNESS-ERROR",
                "reply": f"NEW-CAUGHT {exc!r}",
                "seconds": round(time.time() - t0, 3)}
    try:
        with tempfile.TemporaryDirectory(prefix="p173bb_") as tmp:
            loop = build_base({"state_dir": tmp,
                               "sleep_threshold": 100000})
            base_replies = [" ".join(loop.turn(t))
                            for t in row.get("teaches", [])]
            base_stored = [list(t) for t in L90.notebook_triples(loop.nb)]
            base_asks = [{"q": a["q"],
                          "reply": " ".join(loop.turn(a["q"]))}
                         for a in row.get("asks", [])]
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
                "asks": ask_out, "base_asks": base_asks,
                "verdict": "BASE-DIFF",
                "seconds": round(time.time() - t0, 3)}
    return {"id": row["id"], "group": row["group"],
            "verdict": "OK", "seconds": round(time.time() - t0, 3)}


def check_173b_row(row, build_new, build_base, listed_diffs=frozenset()):
    t0 = time.time()
    steps = list(row.get("steps", []))
    try:
        replies, stored, entities = drive_steps(steps, build_new)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"],
                "verdict": "HARNESS-ERROR",
                "reply": f"NEW-CAUGHT {exc!r}",
                "seconds": round(time.time() - t0, 3)}
    if row.get("identical_to_base"):
        try:
            base_replies, base_stored, _ = drive_steps(steps, build_base)
        except Exception as exc:  # noqa: BLE001
            return {"id": row["id"], "group": row["group"],
                    "verdict": "HARNESS-ERROR",
                    "reply": f"BASE-CAUGHT {exc!r}",
                    "seconds": round(time.time() - t0, 3)}
        if stored != base_stored or replies != base_replies:
            if row["id"] in listed_diffs:
                return {"id": row["id"], "group": row["group"],
                        "steps": steps, "stored": stored,
                        "base_stored": base_stored, "replies": replies,
                        "base_replies": base_replies,
                        "verdict": "LISTED-DIFF",
                        "seconds": round(time.time() - t0, 3)}
            return {"id": row["id"], "group": row["group"],
                    "steps": steps, "stored": stored,
                    "base_stored": base_stored, "replies": replies,
                    "base_replies": base_replies, "verdict": "BASE-DIFF",
                    "seconds": round(time.time() - t0, 3)}
    else:
        if row["id"] in listed_diffs:
            # Listed semantic difference: still record base side.
            try:
                base_replies, base_stored, _ = drive_steps(steps, build_base)
            except Exception:  # noqa: BLE001
                base_replies, base_stored = None, None
            row = dict(row)
            row["_base_replies"] = base_replies
            row["_base_stored"] = base_stored
    if row["id"] not in LEAK_EXEMPT:
        leaked = [r for r in replies if M166.USER_KEY in (r or "")]
        if leaked:
            return {"id": row["id"], "group": row["group"],
                    "steps": steps, "stored": stored, "replies": replies,
                    "verdict": "USER-LEAK",
                    "seconds": round(time.time() - t0, 3)}
    if row.get("user_only_entities"):
        if not set(entities) <= {"USER"}:
            return {"id": row["id"], "group": row["group"],
                    "steps": steps, "stored": stored, "replies": replies,
                    "entities": entities, "verdict": "ENTITY-LEAK",
                    "seconds": round(time.time() - t0, 3)}
    exp = row.get("expect")
    verdict = "OK"
    if exp is not None:
        if exp == "nowrite":
            if stored:
                verdict = "WRONG-WRITE"
        else:
            want = sorted([list(t) for t in exp])
            if sorted(stored) != want:
                verdict = "WRONG-WRITE" if stored else "MISSED"
    if verdict == "OK":
        for idx, want in (row.get("wants") or {}).items():
            try:
                rep = replies[int(idx)]
            except (IndexError, ValueError):
                verdict = "WRONG-REPLY"
                break
            if want and want not in (rep or ""):
                verdict = "WRONG-REPLY"
                break
    if row["id"] in listed_diffs and verdict != "OK":
        # The listed S13 difference: report honestly; harness verdict stays
        # non-OK so the bar (LISTED-DIFF only) is checkable in the JSON.
        base_r = row.get("_base_replies")
        base_s = row.get("_base_stored")
        return {"id": row["id"], "group": row["group"], "steps": steps,
                "expect": exp, "stored": stored, "replies": replies,
                "entities": entities, "verdict": "LISTED-DIFF",
                "base_replies": base_r, "base_stored": base_s,
                "seconds": round(time.time() - t0, 3)}
    return {"id": row["id"], "group": row["group"], "steps": steps,
            "expect": exp, "stored": stored, "replies": replies,
            "entities": entities, "verdict": verdict,
            "seconds": round(time.time() - t0, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 173b T1/T1b/T1c probe")
    ap.add_argument("--which", choices=("t1", "t1b", "t1c"), required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop173_agent as L173  # noqa: E402 (base agent)
    import fable_loop173b_agent as L173B  # noqa: E402 (this experiment)
    cfg_new = copy.deepcopy(L173B.DEFAULT_CONFIG173B)
    cfg_base = copy.deepcopy(L173.DEFAULT_CONFIG173)
    build_new = lambda c: L173B.build_agent173b(dict(cfg_new, **c))  # noqa: E731
    build_base = lambda c: L173.build_agent173(dict(cfg_base, **c))  # noqa: E731
    t0 = time.time()
    if args.which == "t1":
        cases = json.loads((ART166 / "cases166.json").read_text(
            encoding="utf-8"))
        out = [check_166_row(row, build_new, build_base)
               for row in cases]
        payload = {"agent": "loop173b", "cases_file": "cases166.json",
                   "mode": "t1-byte-identical-to-loop173"}
    elif args.which == "t1b":
        cases = json.loads((ART173 / "cases173.json").read_text(
            encoding="utf-8"))
        # S13's sealed expectation is loop173's (name Lena); 173b predicts
        # LISTED-DIFF there and OK elsewhere.
        out = [check_173b_row(row, build_new, build_base,
                              T1B_LISTED_DIFFS)
               for row in cases]
        payload = {"agent": "loop173b", "cases_file": "cases173.json",
                   "mode": "t1b-vs-loop173-listed-S13",
                   "listed_diffs": sorted(T1B_LISTED_DIFFS)}
    else:
        cases = json.loads((ART173B / "cases173b.json").read_text(
            encoding="utf-8"))
        out = [check_173b_row(row, build_new, build_base)
               for row in cases]
        payload = {"agent": "loop173b", "cases_file": "cases173b.json",
                   "mode": "t1c-new-probe"}
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload.update({"wall_seconds": wall, "counts": counts,
                    "ok": sum(1 for r in out if r["verdict"] == "OK"),
                    "n": len(out), "cases": out})
    dest = Path(args.out) if args.out else ART173B / (
        {"t1": "probe173b-t1.json", "t1b": "probe173b-t1b.json",
         "t1c": "probe173b-t1c.json"}[args.which])
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False)
                    + "\n", encoding="utf-8")
    print(f"agent=loop173b which={args.which} n={len(out)} counts={counts} "
          f"wall={wall}s")
    for r in out:
        if r["verdict"] not in ("OK", "LISTED-DIFF"):
            print(f"  {r['verdict']} {r['id']}: "
                  f"{str(r.get('replies', r.get('reply')))[:200]}")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
