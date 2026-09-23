#!/usr/bin/env python3
"""Experiment 192 -- C1 sealed probe + C2 event identity (Muse).

Reads the FROZEN turn file
(artifacts/fable-correctreply192-20260922/cases192.json, 40 turns, all
fictional names): >= 10 explicit corrections (No, / Actually, /
Correction: / Sorry-I-meant / bench73 auto-correct re-teach), >= 4
yes-to-change answers, >= 12 traps (first teach, repeat,
duplicate-correct, declined change, second-value conflict, pretend/
hearsay, questions, no-pending yes, Forgotten, post-forget ask). Each
turn runs sequentially through ONE fresh in-process loop192 AND ONE
fresh in-process loop167e (same order, temp state dirs):

  - every `want: updated` turn (explicit correction or yes) must reply
    EXACTLY "Updated: {S}'s {R} is {N} (it was {O})." with the sealed
    old/new values from the case file (relation in 167e spaced surface);
  - every `want: same` trap turn must be byte-identical to loop167e;
  - stored triples must be identical between the two runs (reply only);
  - notebook events must be identical between the runs after dropping
    the volatile event_id (uuid hex) and prev hash-chain fields, which
    are random per run by construction (Listening._eid uuid4) -- C2.

Verdicts per turn: OK / TEMPLATE-MISS / TRAP-MOVE; overall OK /
TURN-FAIL / STORE-DIFF / EVENT-DIFF / COUNT-SHORT / HARNESS-ERROR.
Every turn reported, never averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix192_probe.py --out artifacts/fable-correctreply192-20260922/probe192-loop192.json
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
ART192 = ROOT / "artifacts" / "fable-correctreply192-20260922"

VOLATILE_EVENT_KEYS = ("event_id", "prev")


def scrub_events(events: list[dict]) -> list[dict]:
    return [{k: v for k, v in e.items() if k not in VOLATILE_EVENT_KEYS}
            for e in events]


def drive(turns: list[str], build_fn):
    with tempfile.TemporaryDirectory(prefix="192_") as tmp:
        loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        replies = [" ".join(loop.turn(t)) for t in turns]
        stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        events = scrub_events(list(loop.nb.events))
    return replies, stored, events


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 192 C1/C2 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop167e_agent as L167E  # noqa: E402 (base, read-only)
    import fable_loop192_agent as L192  # noqa: E402 (this experiment)
    cfg_new = copy.deepcopy(L192.DEFAULT_CONFIG192)
    cfg_base = copy.deepcopy(L167E.DEFAULT_CONFIG167E)
    build_new = lambda c: L192.build_agent192(dict(cfg_new, **c))  # noqa: E731
    build_base = lambda c: L167E.build_agent167e(dict(cfg_base, **c))  # noqa: E731
    spec = json.loads((ART192 / "cases192.json").read_text(encoding="utf-8"))
    turns = [t["t"] for t in spec["turns"]]
    t0 = time.time()
    try:
        replies, stored, events = drive(turns, build_new)
        replies_b, stored_b, events_b = drive(turns, build_base)
    except Exception as exc:  # noqa: BLE001
        payload = {"agent": "loop192", "verdict": "HARNESS-ERROR",
                   "detail": repr(exc)}
        dest = Path(args.out) if args.out else \
            ART192 / "probe192-loop192.json"
        dest.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(f"HARNESS-ERROR {exc!r}")
        return 1
    rows = []
    for i, t in enumerate(spec["turns"]):
        r, rb = replies[i], replies_b[i]
        if t["want"] == "updated":
            exp = (f"Updated: {t['subj']}'s {t['rel']} is {t['new']} "
                   f"(it was {t['old']}).")
            verdict = "OK" if r == exp else "TEMPLATE-MISS"
            rows.append({"n": i, "turn": t["t"], "kind": t["kind"],
                         "reply": r, "reply_base": rb, "want": exp,
                         "verdict": verdict})
        else:
            verdict = "OK" if r == rb else "TRAP-MOVE"
            rows.append({"n": i, "turn": t["t"], "kind": t["kind"],
                         "reply": r, "reply_base": rb, "verdict": verdict})
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    kinds: dict[str, int] = {}
    for t in spec["turns"]:
        kinds[t["kind"]] = kinds.get(t["kind"], 0) + 1
    verdict_all = "OK"
    if any(r["verdict"] != "OK" for r in rows):
        verdict_all = "TURN-FAIL"
    if stored != stored_b:
        verdict_all = "STORE-DIFF"
    if events != events_b:
        verdict_all = "EVENT-DIFF"
    if not (kinds.get("correction", 0) >= 10 and kinds.get("yes", 0) >= 4
            and kinds.get("trap", 0) >= 12 and len(rows) >= 30):
        verdict_all = "COUNT-SHORT"
    wall = round(time.time() - t0, 1)
    payload = {"agent": "loop192", "cases_file": "cases192.json",
               "n": len(rows), "kinds": kinds, "counts": counts,
               "overall": verdict_all,
               "stored_equal": stored == stored_b,
               "events_equal": events == events_b,
               "wall_seconds": wall, "cases": rows}
    dest = Path(args.out) if args.out else \
        ART192 / "probe192-loop192.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent=loop192 n={len(rows)} kinds={kinds} counts={counts} "
          f"overall={verdict_all} stored_equal={stored == stored_b} "
          f"events_equal={events == events_b} wall={wall}s")
    print(f"wrote {dest}")
    return 0 if verdict_all == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
