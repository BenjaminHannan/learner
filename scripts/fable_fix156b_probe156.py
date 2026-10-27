#!/usr/bin/env python3
"""Experiment 156b -- T2 sealed 156-panel replay (Muse). Read-only vs repo.

Reads 156's FROZEN cases156.json (68 cases, sealed in
artifacts/fable-smalltalk156-20260922/, read-only), one message each
through a FRESH in-process loop156b. Predicted: every row identical to
156's sealed behaviour EXCEPT the 9 intentional reply changes --
A01-A05/A09/A11/A12 (laugh words move from 156's "Got it!" to the new
laugh reply) and N20 ("thanks a lot" moves from near-miss to thanks).
All other small-talk rows expect 156's exact class reply with 0 writes;
all other near-miss rows expect byte-identical reply AND stored triples
to fresh loop150.

Verdicts: OK / WRONG-WRITE / WRONG-REPLY / NEAR-DIFF / UNLISTED-CHANGE.
Every case reported, never averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix156b_probe156.py \\
    --out artifacts/fable-smalltalk156b-20260922/probe156b-cases156.json
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

import fable_fix156b_smalltalk as S156b  # noqa: E402 (replies, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)

ROOT = SCRIPTS.parent
ART156 = ROOT / "artifacts" / "fable-smalltalk156-20260922"
ART156b = ROOT / "artifacts" / "fable-smalltalk156b-20260922"

# 156's sealed class replies (unchanged classes stay byte-identical).
GREETING156 = ("Hi! Teach me like \"Tom's boss is Ann.\" "
               "Ask me like \"Who is Tom's boss?\"")
REPLY156 = {"greeting": GREETING156, "thanks": "You're welcome!",
            "ack": "Got it!", "bye": "Bye!"}

# The ONLY intentional changes on 156's panel (sealed in PASSMARKS.md):
# laugh words get the new laugh reply; N20 becomes thanks.
LAUGH_IDS = {"A01", "A02", "A03", "A04", "A05", "A09", "A11", "A12"}
NEAR_TO_THANKS = {"N20"}


def fresh_turn(build_fn, text: str) -> dict:
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="t2b_") as tmp:
        try:
            loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        except Exception as exc:  # noqa: BLE001
            return {"reply": f"BOOT-FAILED {exc!r}", "stored": [],
                    "seconds": round(time.time() - t0, 3)}
        try:
            reply = " ".join(loop.turn(text))
            stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        except Exception as exc:  # noqa: BLE001
            return {"reply": f"HARNESS-CAUGHT {exc!r}", "stored": [],
                    "seconds": round(time.time() - t0, 3)}
    return {"reply": reply, "stored": stored,
            "seconds": round(time.time() - t0, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 156b T2 156-panel replay")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop150_agent as L150  # noqa: E402 (base, read-only)
    import fable_loop156b_agent as L156b  # noqa: E402 (this experiment)
    cfg150 = copy.deepcopy(L150.DEFAULT_CONFIG150)
    cfg156b = copy.deepcopy(L156b.DEFAULT_CONFIG156b)
    build150 = lambda c: L150.build_agent150(dict(cfg150, **c))  # noqa: E731
    build156b = lambda c: L156b.build_agent156b(  # noqa: E731
        dict(cfg156b, **c))

    cases = json.loads((ART156 / "cases156.json").read_text(encoding="utf-8"))
    t0 = time.time()
    out = []
    for row in cases:
        got = fresh_turn(build156b, row["text"])
        rec = {"id": row["id"], "group": row["group"], "kind": row["kind"],
               "text": row["text"], "stored": got["stored"],
               "reply": got["reply"], "seconds": got["seconds"]}
        if row["id"] in LAUGH_IDS:
            rec["want_reply"] = S156b.LAUGH_REPLY
            if got["stored"]:
                rec["verdict"] = "WRONG-WRITE"
            elif got["reply"] == S156b.LAUGH_REPLY:
                rec["verdict"] = "OK"
            else:
                rec["verdict"] = "WRONG-REPLY"
        elif row["id"] in NEAR_TO_THANKS:
            rec["want_reply"] = S156b.THANKS_REPLY
            if got["stored"]:
                rec["verdict"] = "WRONG-WRITE"
            elif got["reply"] == S156b.THANKS_REPLY:
                rec["verdict"] = "OK"
            else:
                rec["verdict"] = "WRONG-REPLY"
        elif row["kind"] == "smalltalk":
            want = REPLY156[row["group"]]
            rec["want_reply"] = want
            if got["stored"]:
                rec["verdict"] = "WRONG-WRITE"
            elif got["reply"] == want:
                rec["verdict"] = "OK"
            else:
                rec["verdict"] = "UNLISTED-CHANGE"
        else:
            base = fresh_turn(build150, row["text"])
            rec["loop150_reply"] = base["reply"]
            rec["loop150_stored"] = base["stored"]
            if (got["reply"] == base["reply"]
                    and got["stored"] == base["stored"]):
                rec["verdict"] = "OK"
            else:
                rec["verdict"] = "NEAR-DIFF"
        out.append(rec)
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload = {"agent": "loop156b", "cases_file": "cases156.json(156)",
               "wall_seconds": wall, "counts": counts, "cases": out}
    dest = Path(args.out) if args.out else ART156b / "probe156b-cases156.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent=loop156b n={len(out)} counts={counts} wall={wall}s")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
