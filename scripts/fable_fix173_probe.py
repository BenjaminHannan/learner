#!/usr/bin/env python3
"""Experiment 173 -- T1 (sealed 166 probe, reused unchanged) + T1b (new
45-dialogue probe) runner (muse). Read-only vs repo.

T1: artifacts/fable-me166-20260922/cases166.json (52 rows) through loop173
AND loop166: stored triples + teach replies + every ask reply must be
byte-identical (0 moves predicted: the 173 frames never fire without a set
name, and no cases166 turn sets one).

T1b: artifacts/fable-username173-20260922/cases173.json (45 rows, each row a
fresh loop, steps in order):
  S (13 statement shapes) -> (USER,name,X) stored, "Saved: your name is X.",
    "What is my name?" answers "Your name is X.", entities <= {USER}.
  L (11 look-alikes) -> 0 writes, byte-identical to loop166.
  R (4 renames) -> change-prompt ("Do you want me to change it to ...?"),
    yes replaces / no keeps, final name answers.
  P (7 name-then-third-person) -> X-head turns store/answer USER facts;
    "Is X Ida's brother?" yes/no/unknown by lookup.
  U (5 unset) -> "I don't know your name yet.", 0 writes.
  O (5 other) -> byte-identical to loop166.
T2: 0 wrong writes over all rows; 0 non-USER entities from name statements
(S/U/L/R rows hold entities <= {USER}).

Verdicts: OK / MISSED / WRONG-WRITE / WRONG-REPLY / ASK-FAIL / BASE-DIFF /
USER-LEAK / ENTITY-LEAK / HARNESS-ERROR. Every seed/case reported.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix173_probe.py --which t1 \\
    --out artifacts/fable-username173-20260922/probe173-t1.json
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix173_probe.py --which t1b \\
    --out artifacts/fable-username173-20260922/probe173-t1b.json
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

SAVED_MARK = "Saved:"
ALREADY_MARK = "already have that"
LEAK_EXEMPT = {"O13"}  # literal-USER control from cases166


def drive_steps(steps, build_fn):
    with tempfile.TemporaryDirectory(prefix="p173_") as tmp:
        loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        replies = [" ".join(loop.turn(t)) for t in steps]
        stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        try:
            entities = sorted(set(loop.nb.entities.values()))
        except Exception:  # noqa: BLE001
            entities = []
    return replies, stored, entities


def check_166_row(row, build_new, build_base):
    """166-format row: byte-identical new-vs-base (T1)."""
    t0 = time.time()
    try:
        replies, stored, _ = drive_steps(row.get("teaches", []),
                                         build_new)
        ask_out = []
        with tempfile.TemporaryDirectory(prefix="p173a_") as tmp:
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
        with tempfile.TemporaryDirectory(prefix="p173b_") as tmp:
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


def check_173_row(row, build_new, build_base):
    """173-format row: teaches/asks semantics + optional base identity."""
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
            return {"id": row["id"], "group": row["group"],
                    "steps": steps, "stored": stored,
                    "base_stored": base_stored, "replies": replies,
                    "base_replies": base_replies, "verdict": "BASE-DIFF",
                    "seconds": round(time.time() - t0, 3)}
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
    return {"id": row["id"], "group": row["group"], "steps": steps,
            "expect": exp, "stored": stored, "replies": replies,
            "entities": entities, "verdict": verdict,
            "seconds": round(time.time() - t0, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 173 T1/T1b probe")
    ap.add_argument("--which", choices=("t1", "t1b"), required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop166_agent as L166  # noqa: E402 (base agent)
    import fable_loop173_agent as L173  # noqa: E402 (this experiment)
    cfg_new = copy.deepcopy(L173.DEFAULT_CONFIG173)
    cfg_base = copy.deepcopy(L166.DEFAULT_CONFIG166)
    build_new = lambda c: L173.build_agent173(dict(cfg_new, **c))  # noqa: E731
    build_base = lambda c: L166.build_agent166(dict(cfg_base, **c))  # noqa: E731
    t0 = time.time()
    if args.which == "t1":
        cases = json.loads((ART166 / "cases166.json").read_text(
            encoding="utf-8"))
        out = [check_166_row(row, build_new, build_base)
               for row in cases]
        payload = {"agent": "loop173", "cases_file": "cases166.json",
                   "mode": "t1-byte-identical-to-loop166"}
    else:
        cases = json.loads((ART173 / "cases173.json").read_text(
            encoding="utf-8"))
        out = [check_173_row(row, build_new, build_base)
               for row in cases]
        payload = {"agent": "loop173", "cases_file": "cases173.json",
                   "mode": "t1b-new-probe"}
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload.update({"wall_seconds": wall, "counts": counts,
                    "ok": sum(1 for r in out if r["verdict"] == "OK"),
                    "n": len(out), "cases": out})
    dest = Path(args.out) if args.out else ART173 / (
        "probe173-t1.json" if args.which == "t1"
        else "probe173-t1b.json")
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False)
                    + "\n", encoding="utf-8")
    print(f"agent=loop173 which={args.which} n={len(out)} counts={counts} "
          f"wall={wall}s")
    for r in out:
        if r["verdict"] != "OK":
            print(f"  {r['verdict']} {r['id']}: "
                  f"{str(r.get('replies', r.get('reply')))[:200]}")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
