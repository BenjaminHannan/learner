#!/usr/bin/env python3
"""Experiment 160b -- C1 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN dialogues from artifacts/fable-correct160b-20260922/cases160b.json
(56 dialogues: 16 bare-after-save, 16 bare-after-answer, 14 bare-with-no-fact,
10 unrelated), each through FRESH in-process loops (build_agent160b; D-group
also build_agent150 for the byte-identity check), triples via
fable_loop90_agent.notebook_triples. Every seed/case reported, never averaged.

Judgements:
  A (bare right after save): triples(bare arm) == triples(explicit
    "Actually, ..." arm), and turn-2 replies equal. Verdict OK/FAIL.
  B (bare right after an answer): setup+bare vs setup+explicit-"Actually"
    on the stated fact: triples AND last replies equal. Verdict OK/FAIL.
  C (bare with no fact in the previous reply): final reply is exactly the
    sealed clarify AND 0 FACT writes on the bare turn. Verdict OK/FAIL.
  D (unrelated no/wait/sorry): every reply byte-equal loop160b vs loop150
    AND FACT counts equal. Verdict OK/FAIL.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix160b_probe.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix160b_laststated as B160b  # noqa: E402 (clarify text, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
import fable_loop150_agent as L150  # noqa: E402 (base arm, read-only)
import fable_loop160b_agent as L160b  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART160B = ROOT / "artifacts" / "fable-correct160b-20260922"


def fresh(build_fn):
    tmp = tempfile.mkdtemp(prefix="p160b_")
    return build_fn({"state_dir": tmp, "sleep_threshold": 100000})


def run_dialogue(loop, turns: list[str]) -> dict:
    replies, deltas = [], []
    for t in turns:
        facts0 = sum(1 for e in loop.nb.events if e.get("kind") == "FACT")
        replies.append(" ".join(loop.turn(t)))
        facts1 = sum(1 for e in loop.nb.events if e.get("kind") == "FACT")
        deltas.append(facts1 - facts0)
    return {"replies": replies, "fact_writes": sum(deltas),
            "fact_deltas": deltas,
            "triples": sorted(L90.notebook_triples(loop.nb))}


def main() -> int:
    t0 = time.time()
    cases = json.loads((ART160B / "cases160b.json").read_text(encoding="utf-8"))
    rows: list[dict] = []

    for row in cases["A"]:
        bare = run_dialogue(fresh(L160b.build_agent160b),
                            [row["teach"], row["bare"]])
        expl = run_dialogue(fresh(L160b.build_agent160b),
                            [row["teach"], row["explicit"]])
        ok = (bare["triples"] == expl["triples"]
              and bare["replies"][1] == expl["replies"][1]
              and len(bare["triples"]) > 0)
        rows.append({"id": row["id"], "group": "A", "teach": row["teach"],
                     "bare": row["bare"], "explicit": row["explicit"],
                     "bare_triples": bare["triples"],
                     "expl_triples": expl["triples"],
                     "bare_reply2": bare["replies"][1],
                     "expl_reply2": expl["replies"][1],
                     "verdict": "OK" if ok else "FAIL"})

    for row in cases["B"]:
        bare = run_dialogue(fresh(L160b.build_agent160b),
                            list(row["setup"]) + [row["bare"]])
        expl = run_dialogue(fresh(L160b.build_agent160b),
                            list(row["setup"]) + [row["explicit"]])
        ok = (bare["triples"] == expl["triples"]
              and bare["replies"][-1] == expl["replies"][-1]
              and len(bare["triples"]) > 0)
        rows.append({"id": row["id"], "group": "B", "setup": row["setup"],
                     "bare": row["bare"], "explicit": row["explicit"],
                     "bare_triples": bare["triples"],
                     "expl_triples": expl["triples"],
                     "bare_reply_last": bare["replies"][-1],
                     "expl_reply_last": expl["replies"][-1],
                     "verdict": "OK" if ok else "FAIL"})

    for row in cases["C"]:
        got = run_dialogue(fresh(L160b.build_agent160b), row["turns"])
        ok = (got["replies"][-1] == B160b.CLARIFY_MSG
              and got["fact_deltas"][-1] == 0)
        rows.append({"id": row["id"], "group": "C", "turns": row["turns"],
                     "reply_last": got["replies"][-1],
                     "triples": got["triples"],
                     "fact_deltas": got["fact_deltas"],
                     "verdict": "OK" if ok else "FAIL"})

    for row in cases["D"]:
        got = run_dialogue(fresh(L160b.build_agent160b), row["turns"])
        base = run_dialogue(fresh(L150.build_agent150), row["turns"])
        ok = (got["replies"] == base["replies"]
              and got["fact_writes"] == base["fact_writes"])
        rows.append({"id": row["id"], "group": "D", "turns": row["turns"],
                     "replies160b": got["replies"],
                     "replies150": base["replies"],
                     "writes160b": got["fact_writes"],
                     "writes150": base["fact_writes"],
                     "verdict": "OK" if ok else "FAIL"})

    counts: dict = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    groups: dict = {}
    for r in rows:
        g = groups.setdefault(r["group"], {})
        g[r["verdict"]] = g.get(r["verdict"], 0) + 1
    out = {"seconds": round(time.time() - t0, 1), "counts": counts,
           "by_group": groups, "rows": rows}
    (ART160B / "probe160b-loop160b.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"probe160b: {counts} by_group={groups} "
          f"seconds={out['seconds']}", flush=True)
    for r in rows:
        if r["verdict"] != "OK":
            print(f"  FAIL {r['id']}: {json.dumps(r)[:300]}", flush=True)
    return 0 if counts.get("FAIL", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
