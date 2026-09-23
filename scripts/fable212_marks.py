#!/usr/bin/env python3
"""Exp 212 M1/M2 driver -- G-cases (self reply gone) + S-cases (identical).

M1: every G-case: fresh loop138i routes a NON-DECLINE self reply (evidence
the case was a live hijack), fresh loop212 serves exactly the base's normal
decline (S105.HONEST_DECLINE + L138.DECLINE_SUFFIX) with zero stored facts.
M2: every S-case: fresh loop212 reply + stored facts byte-identical to
fresh loop138i.

Each case runs seed-free single-turn on a fresh loop (isolated temp
notebook dir, sleep_threshold=100000); every case reported, never
averaged. Heavy suites run one at a time; daemon wrappers are not used
here (in-process fresh loops, same as the 138i G3 driver).

Run (Mac CPU, offline; only AFTER PASSMARKS sealed for registered runs;
pilots use --out outside artifacts/):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable212_marks.py --out <dir>
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

import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop138_agent as L138  # noqa: E402 (decline text, read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (base agent, read-only)
import fable_loop212_agent as L212  # noqa: E402 (agent under test)
import fable_self105 as S105  # noqa: E402 (decline text, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-selfgate212-20260922"

DECLINE212 = S105.HONEST_DECLINE + L138.DECLINE_SUFFIX


def fresh(mod):
    d = tempfile.mkdtemp(prefix="m212-")
    if mod is L138I:
        cfg = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
        loop = L138I.build_agent138i({**cfg, "state_dir": d,
                                      "sleep_threshold": 100000})
    else:
        cfg = copy.deepcopy(L212.DEFAULT_CONFIG212)
        loop = L212.build_agent212({**cfg, "state_dir": d,
                                    "sleep_threshold": 100000})
    return loop


def triples(loop) -> list:
    return [list(t) for t in L90.notebook_triples(loop.nb)]


def run_turn(mod, text: str) -> dict:
    loop = fresh(mod)
    said = loop.turn(text)
    routed = None
    try:
        if loop.last_routed is not None:
            routed = loop.last_routed.get("intent")
    except Exception:  # noqa: BLE001
        routed = "?"
    return {"reply": " ".join(said), "routed": routed,
            "facts": triples(loop)}


def run_m1(out: Path) -> dict:
    cases = json.loads((ART / "case212-g.json").read_text(encoding="utf-8"))
    rows, n_pass = [], 0
    for c in cases:
        base = run_turn(L138I, c["turn"])
        new = run_turn(L212, c["turn"])
        hijacked = (base["routed"] not in (None, "DECLINE", "?")
                    and base["reply"] != DECLINE212)
        fixed = (new["reply"] == DECLINE212 and new["facts"] == []
                 and c["expected_class"] == "decline"
                 and c["expected_facts"] == [])
        ok = bool(hijacked and fixed)
        n_pass += int(ok)
        rows.append({"id": c["id"], "turn": c["turn"],
                     "base_routed": base["routed"],
                     "base_reply": base["reply"][:160],
                     "new_reply": new["reply"][:160],
                     "new_facts": new["facts"],
                     "expected_class": c["expected_class"], "pass": ok})
        print(f"M1 {c['id']} pass={ok} base[{base['routed']}] "
              f"new_reply_is_decline={new['reply'] == DECLINE212} "
              f"new_facts={new['facts']}", flush=True)
    (out / "m1-212-g.json").write_text(json.dumps(rows, indent=1,
                                                 ensure_ascii=False),
                                       encoding="utf-8")
    return {"mark": "M1", "n": len(rows), "pass": n_pass,
            "bar": f"{len(cases)}/{len(cases)} G-cases fixed"}


def run_m2(out: Path) -> dict:
    cases = json.loads((ART / "case212-s.json").read_text(encoding="utf-8"))
    rows, n_pass = [], 0
    for c in cases:
        base = run_turn(L138I, c["turn"])
        new = run_turn(L212, c["turn"])
        ok = (new["reply"] == base["reply"]
              and new["facts"] == base["facts"])
        n_pass += int(ok)
        rows.append({"id": c["id"], "src": c["src"], "turn": c["turn"],
                     "base_routed": base["routed"],
                     "reply": base["reply"][:160],
                     "facts": base["facts"], "pass": bool(ok)})
        if not ok:
            print(f"M2 {c['id']} MISMATCH :: {c['turn'][:60]}",
                  flush=True)
    (out / "m2-212-s.json").write_text(json.dumps(rows, indent=1,
                                                 ensure_ascii=False),
                                       encoding="utf-8")
    print(f"M2: {n_pass}/{len(rows)} byte-identical", flush=True)
    return {"mark": "M2", "n": len(rows), "pass": n_pass,
            "bar": f"{len(cases)}/{len(cases)} S-cases byte-identical"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 212 M1/M2")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    t0 = time.time()
    out = Path(args.out) if args.out else ART
    out.mkdir(parents=True, exist_ok=True)
    m1 = run_m1(out)
    m2 = run_m2(out)
    verdict = "PASS" if (m1["pass"] == m1["n"]
                         and m2["pass"] == m2["n"]) else "FAIL"
    summary = {"marks": [m1, m2], "verdict": verdict,
               "seconds": round(time.time() - t0, 1)}
    (out / "marks212-summary.json").write_text(json.dumps(summary, indent=1),
                                               encoding="utf-8")
    print(json.dumps(summary, indent=1), flush=True)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
