#!/usr/bin/env python3
"""Exp 216 panel driver -- P1 world questions + P2 genuine self questions.

Fresh loop per case (base loop138i vs loop216), isolated scratch state
dirs. Reports per-case reply + routed intent; M1 = P1 D-intent replies on
216; M2 = P2 moves vs base.

Run (Mac CPU, offline; registered only AFTER PASSMARKS sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable216_panel.py --out <dir>
Pilots use --out outside artifacts/.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ART216 = ROOT / "artifacts" / "fable-declinecue216-20260922"

import fable_loop138i_agent as L138I  # noqa: E402 (base, read-only)
import fable_loop216_agent as L216  # noqa: E402 (agent under test)


def fresh_loop(builder, scratch: Path, tag: str, i: int):
    d = scratch / ("%s-%03d" % (tag, i))
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    cfg = dict(builder.DEFAULT_CONFIG) if hasattr(builder, "DEFAULT_CONFIG") \
        else None
    import copy
    base_cfg = copy.deepcopy(builder.DEFAULT_CONFIG138I
                             if tag == "base" else builder.DEFAULT_CONFIG216)
    base_cfg["state_dir"] = str(d)
    base_cfg["sleep_threshold"] = 100000
    return (builder.build_agent138i(base_cfg) if tag == "base"
            else builder.build_agent216(base_cfg))


def run_cases(cases: list[dict], scratch: Path) -> dict:
    out: dict = {}
    for tag, builder in (("base", L138I), ("new", L216)):
        rows = []
        for i, c in enumerate(cases):
            loop = fresh_loop(builder, scratch, tag, i)
            reply = " ".join(loop.turn(c["text"]))
            routed = dict(getattr(loop, "last_routed", None) or {})
            rows.append({"id": c["id"], "text": c["text"], "reply": reply,
                         "intent": routed.get("intent"),
                         "gate": routed.get("info", {}).get("gate216")})
        out[tag] = rows
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 216 P1/P2 panels")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cases", default=str(ART216),
                    help="dir holding cases216-p1.jsonl + cases216-p2.jsonl")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    scratch = out / "scratch-panel"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    t0 = time.time()
    summary: dict = {}
    for panel in ("p1", "p2"):
        cases = [json.loads(line) for line in
                 (Path(args.cases) / ("cases216-%s.jsonl" % panel))
                 .read_text(encoding="utf-8").splitlines() if line.strip()]
        res = run_cases(cases, scratch / panel)
        (out / ("panel216-%s.json" % panel)).write_text(
            json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
        import fable_loop216_agent as L216b  # noqa: E402 (D set)
        base_d = sum(1 for r in res["base"] if (r["intent"] or "")
                     in L216b.CUES216)
        new_d = sum(1 for r in res["new"] if (r["intent"] or "")
                    in L216b.CUES216)
        moves = [r["id"] for r, b in zip(res["new"], res["base"])
                 if r["reply"] != b["reply"] or r["intent"] != b["intent"]]
        print("216-%s: n=%d base_D=%d new_D=%d moves=%d %s"
              % (panel, len(cases), base_d, new_d, len(moves), moves),
              flush=True)
        summary[panel] = {"n": len(cases), "base_D": base_d, "new_D": new_d,
                          "moves": moves}
    summary["seconds"] = round(time.time() - t0, 1)
    (out / "panel216-summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    shutil.rmtree(scratch, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
