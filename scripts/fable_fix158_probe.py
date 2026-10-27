#!/usr/bin/env python3
"""Experiment 158 -- Q1 paired question-surface probe (Muse). Read-only vs repo.

Reads FROZEN cases from artifacts/fable-qform158-20260922/cases158.json:

  pairs: teach a fact on a FRESH loop, ask the surface variant, ask the
    canonical "What is X's R?" on another FRESH loop; OK iff both replies
    are byte-identical, contain the taught value, and neither question
    wrote (0 FACT delta on both).
  nonquestions: run the text on loop158 and on loop150 (same setup
    teaches); OK iff replies byte-identical, FACT deltas identical, and
    loop158 wrote nothing.

Every case reported, never averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix158_probe.py \\
    --out artifacts/fable-qform158-20260922/probe158-loop158.json
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

ROOT = SCRIPTS.parent
ART158 = ROOT / "artifacts" / "fable-qform158-20260922"


def fact_count(loop) -> int:
    return sum(1 for e in loop.nb.events if e.get("kind") == "FACT")


def fresh_loop(build_fn, cfg):
    tmp = tempfile.TemporaryDirectory(prefix="q158_")
    c = dict(cfg)
    c["state_dir"] = tmp.name
    c["sleep_threshold"] = 100000
    loop = build_fn(c)
    return tmp, loop


def ask_once(build_fn, cfg, teaches: list[str], question: str) -> dict:
    tmp, loop = fresh_loop(build_fn, cfg)
    try:
        for t in teaches:
            loop.turn(t)
        before = fact_count(loop)
        reply = " ".join(loop.turn(question))
        writes = fact_count(loop) - before
    except Exception as exc:  # noqa: BLE001 -- observed, never raised
        reply, writes = f"HARNESS-CAUGHT {type(exc).__name__}: {exc}", -1
    finally:
        tmp.cleanup()
    return {"reply": reply, "writes": writes}


def run_pair(row: dict, build158, cfg158) -> dict:
    teaches = row["teaches"]
    var = ask_once(build158, cfg158, teaches, row["variant"])
    can = ask_once(build158, cfg158, teaches, row["canonical"])
    want = row["want"]
    ok = (var["reply"] == can["reply"]
          and want.lower() in var["reply"].lower()
          and var["writes"] == 0 and can["writes"] == 0)
    verdict = "OK" if ok else "FAIL"
    return {"id": row["id"], "kind": "pair", "variant": row["variant"],
            "canonical": row["canonical"], "want": want,
            "variant_reply": var["reply"], "canonical_reply": can["reply"],
            "variant_writes": var["writes"],
            "canonical_writes": can["writes"], "verdict": verdict}


def run_nonquestion(row: dict, build158, cfg158,
                    build150, cfg150) -> dict:
    teaches = row.get("teaches", [])
    got158 = ask_once(build158, cfg158, teaches, row["text"])
    got150 = ask_once(build150, cfg150, teaches, row["text"])
    ok = (got158["reply"] == got150["reply"]
          and got158["writes"] == got150["writes"] == 0)
    verdict = "OK" if ok else "FAIL"
    return {"id": row["id"], "kind": "nonquestion", "text": row["text"],
            "reply158": got158["reply"], "reply150": got150["reply"],
            "writes158": got158["writes"], "writes150": got150["writes"],
            "verdict": verdict}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 158 Q1 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop158_agent as L158  # noqa: E402 (this experiment)
    import fable_loop150_agent as L150  # noqa: E402 (base, read-only)
    cfg158 = copy.deepcopy(L158.DEFAULT_CONFIG158)
    cfg150 = copy.deepcopy(L150.DEFAULT_CONFIG150)
    cases = json.loads((ART158 / "cases158.json").read_text(encoding="utf-8"))
    t0 = time.time()
    out = []
    for row in cases:
        if row.get("kind", "pair") == "pair":
            out.append(run_pair(row, L158.build_agent158, cfg158))
        else:
            out.append(run_nonquestion(row, L158.build_agent158, cfg158,
                                       L150.build_agent150, cfg150))
        r = out[-1]
        print(f"{r['id']}: {r['verdict']}", flush=True)
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload = {"agent": "loop158", "cases_file": "cases158.json",
               "wall_seconds": wall, "counts": counts, "cases": out}
    dest = Path(args.out) if args.out else ART158 / "probe158-loop158.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"n={len(out)} counts={counts} wall={wall}s")
    print(f"wrote {dest}")
    return 0 if counts.get("FAIL", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
