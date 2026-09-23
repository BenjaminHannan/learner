#!/usr/bin/env python3
"""Experiment 139c -- T1/T2 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN cases139c.json (written by fable_fix139c_cases.py before the
seal). Each case runs its dialog through a FRESH in-process loop
(sleep_threshold=100000), triples via fable_loop90_agent.notebook_triples.

tail mode (139c only): OK iff final stored triples == expect AND (when
set) the correction prompt reply contains prompt_clean, contains no
prompt_dirty, and the final reply contains final_contains.
  MISSED = expected write missing; WRONG-WRITE = any stored triple
  outside the expectation (T2: 0 wrong writes over all cases).
diff mode (139c vs 138b, same dialog, fresh loops): OK iff stored triples
equal AND every reply equal (byte-identical to loop138b).

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix139c_probe.py \\
    --out artifacts/fable-tailwords139c-20260922/probe139c-loop139c.json
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
ART = ROOT / "artifacts" / "fable-tailwords139c-20260922"


def fresh_dialog(build_fn, dialog: list[str]):
    with tempfile.TemporaryDirectory(prefix="p139c_") as tmp:
        loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        replies = [" ".join(loop.turn(t)) for t in dialog]
        stored = [list(t) for t in L90.notebook_triples(loop.nb)]
    return replies, stored


def run_case(row: dict, build_c, build_b) -> dict:
    t0 = time.time()
    out = {"id": row["id"], "group": row["group"], "mode": row["mode"],
           "dialog": row["dialog"], "expect": row["expect"]}
    try:
        replies_c, stored_c = fresh_dialog(build_c, row["dialog"])
    except Exception as exc:  # noqa: BLE001
        out.update({"stored": [], "replies": [],
                    "verdict": "HARNESS-ERROR", "note": repr(exc),
                    "seconds": round(time.time() - t0, 3)})
        return out
    out["stored"] = stored_c
    out["replies"] = replies_c
    notes = []
    if row["mode"] == "tail":
        exp = [list(e) for e in row["expect"]]
        if stored_c == exp:
            verdict = "OK"
        elif not stored_c:
            verdict = "MISSED"
        else:
            verdict = "WRONG-WRITE"
        if verdict == "OK":
            if row.get("prompt_clean"):
                prompt = " ".join(replies_c[1:-1]) if len(replies_c) > 2 \
                    else replies_c[-1]
                if row["prompt_clean"] not in prompt:
                    verdict, notes = "FAIL-PROMPT", [
                        f"prompt missing {row['prompt_clean']!r}"]
                elif row.get("prompt_dirty") and \
                        row["prompt_dirty"] in prompt:
                    verdict, notes = "FAIL-PROMPT", [
                        f"prompt carries dirty {row['prompt_dirty']!r}"]
            if verdict == "OK" and row.get("final_contains"):
                if row["final_contains"] not in replies_c[-1]:
                    verdict, notes = "FAIL-FINAL", [
                        "final reply missing "
                        f"{row['final_contains']!r}"]
        out["verdict"] = verdict
        out["note"] = "; ".join(notes)
    else:
        try:
            replies_b, stored_b = fresh_dialog(build_b, row["dialog"])
        except Exception as exc:  # noqa: BLE001
            out.update({"verdict": "HARNESS-ERROR", "note": repr(exc),
                        "seconds": round(time.time() - t0, 3)})
            return out
        out["stored138b"] = stored_b
        out["replies138b"] = replies_b
        if stored_c == stored_b and replies_c == replies_b:
            out["verdict"], out["note"] = "OK", ""
        else:
            out["verdict"] = "DIFF"
            out["note"] = (
                f"stored139c={stored_c} vs stored138b={stored_b}; "
                f"replies_equal={replies_c == replies_b}")
    out["seconds"] = round(time.time() - t0, 3)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 139c T1/T2 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop139c_agent as L139c  # noqa: E402 (this experiment)
    import fable_loop138b_agent as L138b  # noqa: E402 (frozen base)
    cfg_c = copy.deepcopy(L139c.DEFAULT_CONFIG139C)
    cfg_b = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
    build_c = lambda c: L139c.build_agent139c(dict(cfg_c, **c))  # noqa: E731
    build_b = lambda c: L138b.build_agent138b(dict(cfg_b, **c))  # noqa: E731
    cases = json.loads((ART / "cases139c.json").read_text(encoding="utf-8"))
    t0 = time.time()
    results = [run_case(r, build_c, build_b) for r in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    tails = [r for r in results if r["mode"] == "tail"]
    tail_ok = sum(1 for r in tails if r["verdict"] == "OK")
    wrong_writes = sum(1 for r in results
                       if r["verdict"] == "WRONG-WRITE")
    summary = {"n": len(results), "verdicts": counts,
               "tail_exact": f"{tail_ok}/{len(tails)}",
               "wrong_writes": wrong_writes, "wall_seconds": wall}
    dest = Path(args.out) if args.out else ART / "probe139c-loop139c.json"
    dest.write_text(json.dumps({"summary": summary, "cases": results},
                               indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"n={len(results)} counts={counts} tail_exact={summary['tail_exact']} "
          f"wrong_writes={wrong_writes} wall={wall}s")
    print(f"wrote {dest}")
    return 0 if (wrong_writes == 0 and
                 tail_ok / max(len(tails), 1) >= 0.95 and
                 all(r["verdict"] == "OK" for r in results
                     if r["mode"] == "diff")) else 1


if __name__ == "__main__":
    sys.exit(main())
