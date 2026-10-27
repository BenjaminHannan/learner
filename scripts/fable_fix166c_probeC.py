#!/usr/bin/env python3
"""Experiment 166c -- T1c NEW probe (24 dialogues, fictional names) + T2 (Muse).

Reads artifacts/fable-me166c-20260922/cases166c.json (24 rows, sealed,
written before any registered run, fictional names only):
- shout group (8 ALL-CAPS mentions, incl. the director's ana/ANA case):
  display stays lowercase -- stored triples AND every reply
  byte-identical to loop166, and the late reply still shows the
  lowercase display.
- embed group (8 lowercase names inside capitalised multi-word
  titles/teams/events, 166b-adjacency shapes): display unchanged --
  stored + every reply byte-identical to loop166.
- title group (8 genuine Title-case mentions, first + third person):
  stored equal, every reply from the first Title-case mention on (plus
  every ask reply) contains the Title-case display `cap`, and the fix
  visibly fires vs loop166.
T2: 0 wrong writes (stored equal on every row), 0 new entities (counts
equal on every row).

Verdicts: OK / CAP-MISS / BASE-DIFF / NEW-ENTITY / HARNESS-ERROR.
Every seed/case reported, never averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix166c_probeC.py \\
    --out artifacts/fable-me166c-20260922/probe166c-C.json
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
ART166C = ROOT / "artifacts" / "fable-me166c-20260922"


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


def _identical(new_replies, new_asks, b_replies, b_asks) -> bool:
    return (new_replies == b_replies
            and [a["reply"] for a in new_asks]
            == [a["reply"] for a in b_asks])


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
    low = row.get("low", "")
    if group in ("shout", "embed"):
        # Display must NOT change: everything byte-identical to loop166,
        # and the lowercase display still shows in the late reply.
        if not _identical(replies, ask_out, b_replies, b_asks):
            return {"id": row["id"], "group": group, **base,
                    "verdict": "BASE-DIFF"}
        teaches = row.get("teaches", [])
        first = next((i for i, t in enumerate(teaches)
                      if row.get("shout", "") in t or low in t.lower()),
                     len(teaches))
        late = replies[first:] + [a["reply"] for a in ask_out
                                  if a.get("want") != "SKIP"]
        if low and not any(low in (r or "") for r in late):
            return {"id": row["id"], "group": group, **base,
                    "verdict": "CAP-MISS"}
        return {"id": row["id"], "group": group, **base, "verdict": "OK"}
    if group == "title":
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
    ap = argparse.ArgumentParser(description="Exp 166c T1c+T2 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop166_agent as L166  # noqa: E402 (base agent, read-only)
    import fable_loop166c_agent as L166C  # noqa: E402 (this experiment)
    cfg_new = copy.deepcopy(L166C.DEFAULT_CONFIG166C)
    cfg_base = copy.deepcopy(L166.DEFAULT_CONFIG166)
    build_new = lambda c: L166C.build_agent166c(dict(cfg_new, **c))  # noqa: E731
    build_base = lambda c: L166.build_agent166(dict(cfg_base, **c))  # noqa: E731
    cases = json.loads((ART166C / "cases166c.json").read_text(
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
    payload = {"agent": "loop166c", "base": "loop166",
               "cases_file": "cases166c.json",
               "wall_seconds": wall, "counts": counts,
               "by_group": by_group,
               "new_entities": sum(1 for r in out
                                   if r["verdict"] == "NEW-ENTITY"),
               "cases": out}
    dest = Path(args.out) if args.out else ART166C / "probe166c-C.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent=loop166c n={len(out)} counts={counts} by_group={by_group} "
          f"wall={wall}s")
    print(f"wrote {dest}")
    return 0 if counts.get("OK", 0) == len(out) else 1


if __name__ == "__main__":
    sys.exit(main())
