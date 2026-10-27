#!/usr/bin/env python3
"""Experiment 139d -- T1/T2 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN cases139d.json (written by fable_fix139d_cases.py before the
seal). Each case runs its dialog through a FRESH in-process loop
(sleep_threshold=100000), triples via fable_loop90_agent.notebook_triples.

tailu mode (139d only): OK iff final stored triples == expect_stored AND
the LAST reply == expect_reply EXACTLY (byte-identical clarify).
  MISSED = expected write missing; WRONG-WRITE = any stored triple
  outside the expectation (T2: 0 wrong writes over all cases).
diff mode (139d vs 139c, same dialog, fresh loops): OK iff stored triples
equal AND every reply equal (byte-identical to loop139c).

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix139d_probe.py \\
    --out artifacts/fable-tail139d-20260922/probe139d-loop139d.json
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
ART = ROOT / "artifacts" / "fable-tail139d-20260922"


def fresh_dialog(build_fn, dialog: list[str]):
    with tempfile.TemporaryDirectory(prefix="p139d_") as tmp:
        loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        replies = [" ".join(loop.turn(t)) for t in dialog]
        stored = [list(t) for t in L90.notebook_triples(loop.nb)]
    return replies, stored


def run_case(row: dict, build_d, build_c) -> dict:
    t0 = time.time()
    out = {"id": row["id"], "group": row["group"], "mode": row["mode"],
           "dialog": row["dialog"], "expect_stored": row["expect_stored"],
           "expect_reply": row["expect_reply"]}
    try:
        replies_d, stored_d = fresh_dialog(build_d, row["dialog"])
    except Exception as exc:  # noqa: BLE001
        out.update({"stored": [], "replies": [],
                    "verdict": "HARNESS-ERROR", "note": repr(exc),
                    "seconds": round(time.time() - t0, 3)})
        return out
    out["stored"] = stored_d
    out["replies"] = replies_d
    notes = []
    if row["mode"] == "tailu":
        exp = [list(e) for e in row["expect_stored"]]
        if stored_d == exp:
            verdict = "OK"
        elif any(t not in exp for t in stored_d) or (
                len(stored_d) > len(exp)):
            verdict = "WRONG-WRITE"
        else:
            verdict = "MISSED"
        if verdict == "OK":
            if replies_d[-1] != row["expect_reply"]:
                verdict = "FAIL-REPLY"
                notes = [f"last reply {replies_d[-1]!r} != "
                         f"expect {row['expect_reply']!r}"]
        out["verdict"] = verdict
        out["note"] = "; ".join(notes)
    else:
        try:
            replies_c, stored_c = fresh_dialog(build_c, row["dialog"])
        except Exception as exc:  # noqa: BLE001
            out.update({"verdict": "HARNESS-ERROR", "note": repr(exc),
                        "seconds": round(time.time() - t0, 3)})
            return out
        out["stored139c"] = stored_c
        out["replies139c"] = replies_c
        if stored_d == stored_c and replies_d == replies_c:
            out["verdict"], out["note"] = "OK", ""
        else:
            out["verdict"] = "DIFF"
            out["note"] = (
                f"stored139d={stored_d} vs stored139c={stored_c}; "
                f"replies_equal={replies_d == replies_c}")
    out["seconds"] = round(time.time() - t0, 3)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 139d T1/T2 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop139d_agent as L139d  # noqa: E402 (this experiment)
    import fable_loop139c_agent as L139c  # noqa: E402 (frozen base)
    cfg_d = copy.deepcopy(L139d.DEFAULT_CONFIG139D)
    cfg_c = copy.deepcopy(L139c.DEFAULT_CONFIG139C)
    build_d = lambda c: L139d.build_agent139d(dict(cfg_d, **c))  # noqa: E731
    build_c = lambda c: L139c.build_agent139c(dict(cfg_c, **c))  # noqa: E731
    cases = json.loads((ART / "cases139d.json").read_text(encoding="utf-8"))
    t0 = time.time()
    results = [run_case(r, build_d, build_c) for r in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    tails = [r for r in results if r["mode"] == "tailu"]
    tail_ok = sum(1 for r in tails if r["verdict"] == "OK")
    wrong_writes = sum(1 for r in results
                       if r["verdict"] == "WRONG-WRITE")
    summary = {"n": len(results), "verdicts": counts,
               "tail_exact": f"{tail_ok}/{len(tails)}",
               "wrong_writes": wrong_writes, "wall_seconds": wall}
    dest = Path(args.out) if args.out else ART / "probe139d-loop139d.json"
    dest.write_text(json.dumps({"summary": summary, "cases": results},
                               indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"n={len(results)} counts={counts} tail_exact={summary['tail_exact']} "
          f"wrong_writes={wrong_writes} wall={wall}s")
    print(f"wrote {dest}")
    return 0 if (wrong_writes == 0 and
                 tail_ok == len(tails) and
                 all(r["verdict"] == "OK" for r in results
                     if r["mode"] == "diff")) else 1


if __name__ == "__main__":
    sys.exit(main())
