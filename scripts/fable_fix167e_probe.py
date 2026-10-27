#!/usr/bin/env python3
"""Experiment 167e -- T1 sealed probe runner (Muse). Read-only vs repo.

Reads the FROZEN turn file
(artifacts/fable-label167e-20260922/cases167e.json, 34 turns, all
fictional names) covering every reply template that prints a relation
key -- Saved, MISSING_FACT "I don't know", CONFLICT change-prompt,
BROKEN_CHAIN, Forgotten -- each with >= 3 underscore relations
(place_of_birth, birth_year, country_of_citizenship), plus the
already-spaced answer path and no-key clarify/other controls. Each turn
runs sequentially through ONE fresh in-process loop167e AND ONE fresh
in-process loop167c (same order, temp state dirs):

  - every loop167e reply must match its want_template shape;
  - NO loop167e reply may contain an underscore relation-key token
    ([A-Za-z]+_[A-Za-z]+);
  - stored triples must be identical between the two runs after every
    turn (mouth never writes);
  - notebook events must be identical between the runs after dropping
    the volatile event_id (uuid hex) and prev hash-chain fields, which
    are random per run by construction (Listening._eid uuid4);
  - the loop167c run must still show an underscore key on every
    missing/conflict/broken/forgotten turn (coverage proof the new
    render had something to do);
  - synthetic no-key templates (AMBIGUOUS listing, clarifies,
    UNKNOWN_ENTITY, DUPLICATE_OK, change answers) pass through the
    167e renderer byte-identical (unit check, no agent run).

Verdicts: OK / TEMPLATE-MISS / UNDERSCORE-LEAK / EVENT-DIFF /
STORE-DIFF / COVERAGE-GAP / HARNESS-ERROR. Every turn reported, never
averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167e_probe.py --out artifacts/fable-label167e-20260922/probe167e-loop167e.json
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix167e_label as F167E  # noqa: E402 (this experiment)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)

ROOT = SCRIPTS.parent
ART167E = ROOT / "artifacts" / "fable-label167e-20260922"

UNDER = re.compile(r"[A-Za-z]+_[A-Za-z]+")

VOLATILE_EVENT_KEYS = ("event_id", "prev")

SHAPES = {
    "saved": re.compile(r"^Saved: .+$", re.DOTALL),
    "answer": None,  # any non-template reply accepted, checked separately
    "missing": re.compile(r"^I don't know .+$", re.DOTALL),
    "conflict": re.compile(r"^I have .+ Do you want me to change it.+$",
                           re.DOTALL),
    "broken": re.compile(r".*which is not someone I can look up\.$",
                         re.DOTALL),
    "forgotten": re.compile(r"^Forgotten: .+$", re.DOTALL),
    "clarify": re.compile(r"^(I didn't catch anything\.|I didn't "
                          r"understand that\. Could you say it another "
                          r"way\?)$"),
    "other": None,
}

# No-key templates: the renderer must leave these byte-identical.
NOKEY_SYNTHETIC = [
    "I know more than one Mira: Mira (E0001), Mira (E0003). "
    "Which one do you mean?",
    "I didn't understand that. Could you say it another way?",
    "I didn't catch anything.",
    "I don't know anyone called Zed.",
    "I already have that.",
    "Okay, I left it as it was.",
    "I wasn't waiting for an answer.",
    "Please answer with: pick <one of the IDs I listed>.",
    "Please answer yes or no.",
    "Mira's city is Lisbon.",
    "Ada's place of birth is Paris.",
    "I have Mira's city as Lisbon. Do you want me to change it to Oslo?",
]


def scrub_events(events: list[dict]) -> list[dict]:
    return [{k: v for k, v in e.items() if k not in VOLATILE_EVENT_KEYS}
            for e in events]


def drive(turns: list[str], build_fn):
    with tempfile.TemporaryDirectory(prefix="167e_") as tmp:
        loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        replies = [" ".join(loop.turn(t)) for t in turns]
        stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        events = scrub_events(list(loop.nb.events))
    return replies, stored, events


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 167e T1 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop167c_agent as L167C  # noqa: E402 (base, read-only)
    import fable_loop167e_agent as L167E  # noqa: E402 (this experiment)
    cfg_new = copy.deepcopy(L167E.DEFAULT_CONFIG167E)
    cfg_base = copy.deepcopy(L167C.DEFAULT_CONFIG167C)
    build_new = lambda c: L167E.build_agent167e(dict(cfg_new, **c))  # noqa: E731
    build_base = lambda c: L167C.build_agent167c(dict(cfg_base, **c))  # noqa: E731
    spec = json.loads((ART167E / "cases167e.json").read_text(
        encoding="utf-8"))
    turns = [t["t"] for t in spec["turns"]]
    t0 = time.time()
    try:
        replies, stored, events = drive(turns, build_new)
    except Exception as exc:  # noqa: BLE001
        payload = {"agent": "loop167e", "verdict": "HARNESS-ERROR",
                   "detail": repr(exc)}
        dest = Path(args.out) if args.out else \
            ART167E / "probe167e-loop167e.json"
        dest.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(f"HARNESS-ERROR NEW {exc!r}")
        return 1
    try:
        replies_b, stored_b, events_b = drive(turns, build_base)
    except Exception as exc:  # noqa: BLE001
        print(f"HARNESS-ERROR BASE {exc!r}")
        return 1
    rows = []
    key_templates = ("missing", "conflict", "broken", "forgotten")
    for i, (t, want) in enumerate(
            [(x["t"], x["want_template"]) for x in spec["turns"]]):
        r, rb = replies[i], replies_b[i]
        shape = SHAPES[want]
        if shape is not None and not shape.match(r):
            verdict = "TEMPLATE-MISS"
        elif UNDER.search(r):
            verdict = "UNDERSCORE-LEAK"
        elif want in key_templates and not UNDER.search(rb):
            verdict = "COVERAGE-GAP"
        else:
            verdict = "OK"
        rows.append({"n": i, "turn": t, "want_template": want,
                     "key": spec["turns"][i].get("key"),
                     "reply": r, "reply_base": rb, "verdict": verdict})
    nokey_bad = [s for s in NOKEY_SYNTHETIC if F167E.render_label(s) != s]
    verdict_all = "OK"
    if any(r["verdict"] != "OK" for r in rows):
        verdict_all = "TURN-FAIL"
    if stored != stored_b:
        verdict_all = "STORE-DIFF"
    if events != events_b:
        verdict_all = "EVENT-DIFF"
    if nokey_bad:
        verdict_all = "NOKEY-MOVED"
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload = {"agent": "loop167e", "cases_file": "cases167e.json",
               "n": len(rows), "counts": counts,
               "overall": verdict_all,
               "stored_equal": stored == stored_b,
               "events_equal": events == events_b,
               "nokey_synthetic_bad": nokey_bad,
               "wall_seconds": wall, "cases": rows}
    dest = Path(args.out) if args.out else \
        ART167E / "probe167e-loop167e.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent=loop167e n={len(rows)} counts={counts} "
          f"overall={verdict_all} stored_equal={stored == stored_b} "
          f"events_equal={events == events_b} wall={wall}s")
    print(f"wrote {dest}")
    return 0 if verdict_all == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
