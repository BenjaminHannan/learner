#!/usr/bin/env python3
"""Experiment 166b -- T1b NEW probe (30 dialogues, fictional names) + T2 (Muse).

Reads artifacts/fable-me166b-20260922/cases166b.json (30 rows, sealed):
- C group (12 lower-then-cap, first + third person): stored triples equal
  loop166's, entity counts equal, and every reply from the first
  capitalised mention on (plus every ask reply) contains the capitalised
  display `cap`.
- L group (8 cap-then-lower): display stays capitalised -- every reply
  byte-identical to loop166 AND contains `cap`; stored equal.
- O group (10 other): stored + every reply byte-identical to loop166.
T2: 0 wrong writes (stored equal on every row), 0 new entities (counts
equal on every row).

Verdicts: OK / CAP-MISS / CAP-DIFF / BASE-DIFF / NEW-ENTITY /
HARNESS-ERROR. Every seed/case reported, never averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix166b_probeB.py \\
    --out artifacts/fable-me166b-20260922/probe166b-B.json
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
ART166B = ROOT / "artifacts" / "fable-me166b-20260922"


def drive(row: dict, build_fn):
    with tempfile.TemporaryDirectory(prefix=row["id"] + "_") as tmp:
        loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        replies = [" ".join(loop.turn(t)) for t in row.get("teaches", [])]
        stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        n_entities = len(loop.nb.entities)
        ask_out = [{"q": a["q"], "want": a.get("want"),
                    "reply": " ".join(loop.turn(a["q"]))}
                   for a in row.get("asks", [])]
    return replies, stored, n_entities, ask_out


def run_case(row: dict, build_new, build_base) -> dict:
    t0 = time.time()
    try:
        replies, stored, n_ent, ask_out = drive(row, build_new)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"],
                "verdict": "HARNESS-ERROR",
                "reply": f"NEW-CAUGHT {exc!r}",
                "seconds": round(time.time() - t0, 3)}
    try:
        b_replies, b_stored, b_ent, b_asks = drive(row, build_base)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"],
                "verdict": "HARNESS-ERROR",
                "reply": f"BASE-CAUGHT {exc!r}",
                "seconds": round(time.time() - t0, 3)}
    base = {"stored": stored, "base_stored": b_stored,
            "replies": replies, "base_replies": b_replies,
            "asks": ask_out, "base_asks": b_asks,
            "seconds": round(time.time() - t0, 3)}
    if n_ent != b_ent:
        return {"id": row["id"], "group": row["group"], **base,
                "verdict": "NEW-ENTITY"}
    if stored != b_stored:
        return {"id": row["id"], "group": row["group"], **base,
                "verdict": "BASE-DIFF"}
    group = row["group"]
    cap = row.get("cap", "")
    if group == "other":
        if (replies != b_replies or [a["reply"] for a in ask_out]
                != [a["reply"] for a in b_asks]):
            return {"id": row["id"], "group": group, **base,
                    "verdict": "BASE-DIFF"}
        return {"id": row["id"], "group": group, **base, "verdict": "OK"}
    if group == "cap-then-lower":
        # display stays capitalised: every stored triple and every reply
        # byte-identical to loop166 (the fix must not fire anywhere here).
        if (replies != b_replies or [a["reply"] for a in ask_out]
                != [a["reply"] for a in b_asks]):
            return {"id": row["id"], "group": group, **base,
                    "verdict": "BASE-DIFF"}
        bad = [a for a in ask_out
               if a.get("want") and a["want"] not in (a["reply"] or "")]
        if bad:
            return {"id": row["id"], "group": group, **base,
                    "verdict": "CAP-MISS"}
        return {"id": row["id"], "group": group, **base, "verdict": "OK"}
    if group == "lower-then-cap":
        # replies from the first capitalised mention on must use cap;
        # every ask want-substring must hit; and the fix must visibly fire
        # (some new reply uses cap where loop166 renders lowercase).
        teaches = row.get("teaches", [])
        first = next((i for i, t in enumerate(teaches) if cap in t),
                     len(teaches))
        late = replies[first:]
        if not cap or not all(cap in (r or "") for r in late):
            return {"id": row["id"], "group": group, **base,
                    "verdict": "CAP-MISS"}
        bad = [a for a in ask_out
               if a.get("want") and a["want"] not in (a["reply"] or "")]
        if bad:
            return {"id": row["id"], "group": group, **base,
                    "verdict": "CAP-MISS"}
        base_replies_all = b_replies + [a["reply"] for a in b_asks]
        new_replies_all = late + [a["reply"] for a in ask_out]
        fired = any(cap in (r or "") and r not in base_replies_all
                    for r in new_replies_all)
        if not fired:
            return {"id": row["id"], "group": group, **base,
                    "verdict": "CAP-MISS"}
        return {"id": row["id"], "group": group, **base, "verdict": "OK"}
    return {"id": row["id"], "group": group, **base,
            "verdict": "HARNESS-ERROR", "reply": "unknown-group"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 166b T1b+T2 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop166_agent as L166  # noqa: E402 (base agent, read-only)
    import fable_loop166b_agent as L166B  # noqa: E402 (this experiment)
    cfg_new = copy.deepcopy(L166B.DEFAULT_CONFIG166B)
    cfg_base = copy.deepcopy(L166.DEFAULT_CONFIG166)
    build_new = lambda c: L166B.build_agent166b(dict(cfg_new, **c))  # noqa: E731
    build_base = lambda c: L166.build_agent166(dict(cfg_base, **c))  # noqa: E731
    cases = json.loads((ART166B / "cases166b.json").read_text(
        encoding="utf-8"))
    t0 = time.time()
    out = [run_case(row, build_new, build_base) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    by_group: dict[str, dict[str, int]] = {}
    for r, row in zip(out, cases):
        g = by_group.setdefault(row["group"], {})
        g[r["verdict"]] = g.get(r["verdict"], 0) + 1
    payload = {"agent": "loop166b", "base": "loop166",
               "cases_file": "cases166b.json",
               "wall_seconds": wall, "counts": counts,
               "by_group": by_group,
               "new_entities": sum(1 for r in out
                                   if r["verdict"] == "NEW-ENTITY"),
               "cases": out}
    dest = Path(args.out) if args.out else ART166B / "probe166b-B.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent=loop166b n={len(out)} counts={counts} by_group={by_group} "
          f"wall={wall}s")
    print(f"wrote {dest}")
    return 0 if counts.get("OK", 0) == len(out) else 1


if __name__ == "__main__":
    sys.exit(main())
