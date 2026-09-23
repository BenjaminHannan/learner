#!/usr/bin/env python3
"""Experiment 157c -- T1 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN cases from artifacts/fable-title157c-20260922/cases157c.json
(56 cases), each through a FRESH in-process loop. Triples via
fable_loop90_agent.notebook_triples. New loop157c vs base loop157b.

Groups:
  title   filler+Capitalised-possessive titles (A01-A22): the new loop
          must NEVER save under the shortened name (stored empty = safe
          refuse, or every stored subject starts with the lead word).
          Base loop157b's stored triples are recorded to show the bug.
  filler  real fillers with punctuation/lowercase follow (B01-B22):
          replies and stored triples identical to loop157b (questions:
          reply equal + want present).
  same    other turns (C01-C12): replies and stored triples identical.

Verdicts per case: OK / FAIL(+reason). Every case reported, never averaged.
T2: wrong writes over all cases (title case with a shortened-subject
stored triple). Any FAIL fails T1; any wrong write fails T2.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix157c_probe.py \\
    --out artifacts/fable-title157c-20260922/probe157c-loop157c.json
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
ART157C = ROOT / "artifacts" / "fable-title157c-20260922"


def run_turns(turns: list[str], build_fn) -> dict:
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="p157c_") as tmp:
        try:
            loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        except Exception as exc:  # noqa: BLE001
            return {"reply": f"BOOT-FAILED {exc!r}", "stored": [],
                    "seconds": round(time.time() - t0, 3)}
        try:
            replies = [" ".join(loop.turn(t)) for t in turns]
            stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        except Exception as exc:  # noqa: BLE001
            return {"reply": f"HARNESS-CAUGHT {exc!r}", "stored": [],
                    "seconds": round(time.time() - t0, 3)}
    return {"reply": replies[-1] if replies else "", "stored": stored,
            "seconds": round(time.time() - t0, 3)}


def shortened_write(stored: list, lead: str) -> bool:
    """True when a stored subject drops the filler lead word."""
    lead = str(lead or "").lower()
    for t in stored:
        subj = str(t[0]) if t else ""
        if not subj.lower().startswith(lead):
            return True
    return False


def judge(row: dict, build_new, build_base) -> dict:
    out = {"id": row["id"], "group": row["group"]}
    if row["group"] == "title":
        got = run_turns([row["text"]], build_new)
        ref = run_turns([row["text"]], build_base)
        wrong = shortened_write(got["stored"], row.get("lead", ""))
        base_wrong = shortened_write(ref["stored"], row.get("lead", ""))
        ok = not wrong
        out.update({"text": row["text"], "stored157c": got["stored"],
                    "stored157b": ref["stored"], "reply157c": got["reply"],
                    "reply157b": ref["reply"],
                    "base_shortened": bool(base_wrong and ref["stored"]),
                    "verdict": "OK" if ok else "FAIL:shortened-write",
                    "seconds": round(got["seconds"] + ref["seconds"], 3)})
    elif row["group"] == "filler" and row["kind"] == "teach":
        got = run_turns([row["text"]], build_new)
        ref = run_turns([row["text"]], build_base)
        ok = (got["stored"] == ref["stored"]
              and got["reply"] == ref["reply"])
        out.update({"text": row["text"], "stored157c": got["stored"],
                    "stored157b": ref["stored"], "reply157c": got["reply"],
                    "reply157b": ref["reply"],
                    "verdict": "OK" if ok else "FAIL:not-identical",
                    "seconds": round(got["seconds"] + ref["seconds"], 3)})
    elif row["group"] == "filler" and row["kind"] == "question":
        setup = list(row.get("setup", []))
        got = run_turns(setup + [row["text"]], build_new)
        ref = run_turns(setup + [row["text"]], build_base)
        want = str(row.get("want", ""))
        ok = (got["reply"] == ref["reply"]
              and want.lower() in got["reply"].lower())
        out.update({"text": row["text"], "reply157c": got["reply"],
                    "reply157b": ref["reply"], "want": want,
                    "verdict": "OK" if ok else "FAIL:reply-mismatch",
                    "seconds": round(got["seconds"] + ref["seconds"], 3)})
    else:  # same
        got = run_turns([row["text"]], build_new)
        ref = run_turns([row["text"]], build_base)
        ok = (got["reply"] == ref["reply"]
              and got["stored"] == ref["stored"])
        out.update({"text": row["text"], "stored157c": got["stored"],
                    "stored157b": ref["stored"], "reply157c": got["reply"],
                    "reply157b": ref["reply"],
                    "verdict": "OK" if ok else "FAIL:not-identical",
                    "seconds": round(got["seconds"] + ref["seconds"], 3)})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 157c T1 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop157c_agent as L157C  # noqa: E402 (this experiment)
    import fable_loop157b_agent as L157B  # noqa: E402 (base, read-only)
    cfg_new = copy.deepcopy(L157C.DEFAULT_CONFIG157C)
    cfg_base = copy.deepcopy(L157B.DEFAULT_CONFIG157B)
    build_new = lambda c: L157C.build_agent157c(dict(cfg_new, **c))  # noqa: E731
    build_base = lambda c: L157B.build_agent157b(dict(cfg_base, **c))  # noqa: E731
    cases = json.loads((ART157C / "cases157c.json").read_text(encoding="utf-8"))
    t0 = time.time()
    out = [judge(row, build_new, build_base) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    wrong = sum(1 for r in out if r["verdict"] == "FAIL:shortened-write")
    payload = {"agent": "loop157c-vs-loop157b", "cases_file": "cases157c.json",
               "wall_seconds": wall, "counts": counts,
               "wrong_writes": wrong, "cases": out}
    dest = Path(args.out) if args.out else ART157C / "probe157c-loop157c.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"n={len(out)} counts={counts} wrong={wrong} wall={wall}s")
    print(f"wrote {dest}")
    return 0 if counts.get("OK", 0) == len(out) else 1


if __name__ == "__main__":
    sys.exit(main())
