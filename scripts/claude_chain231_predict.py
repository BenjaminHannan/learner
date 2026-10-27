#!/usr/bin/env python3
"""Exp 231 -- M3 PREDICTED MOVES, worked out before any registered run.

Pure function over the frozen suite INPUTS (rt136 cases, rt143 cases,
sessions152 sessions, the four bench splits; same files as
scripts/fable_fix221_predict.py) and the relation table. No agent is
built and no output row is read.

A case is a PREDICTED MOVE CANDIDATE (vs loop221) iff one of its question
turns Q (text ending in "?") has a unique chain reading:
claude_loop231_agent.unique_chain231(Q) is not None. The 231 stage can
only change such a turn, and only when 221 missed it (or produced a
one-key ask on a never-used key), so this is a superset of real moves.
Predicted direction for every candidate: the 221 not-understood reply /
empty-key abstain becomes either a chain answer built from taught facts or
a targeted abstain ("I don't know X's R." / "..., but I don't know ...").
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent

import claude_loop231_agent as C231  # noqa: E402
import fable_fix221_predict as P221  # noqa: E402 (paths only, read-only)


def _cands(qs):
    out = []
    for q in qs:
        if not q.strip().endswith("?"):
            continue
        rd = C231.unique_chain231(q)
        if rd is not None:
            out.append({"turn": q, "reading": {k: rd[k] for k in
                        ("rel", "kind", "root", "hops", "Y")}})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    pred = {"rule": __doc__.strip(), "suites": {}}
    cases = json.loads((ROOT / "artifacts/fable-redteam136-20260922/"
                        "cases136.json").read_text(encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    pred["suites"]["rt136"] = [{"id": c["id"], **p} for c in cases
                               for p in _cands([c["text"]])]
    s143 = json.loads((ROOT / "artifacts/fable-redteam143-20260922/"
                       "fable_redteam143_cases.json").read_text(
        encoding="utf-8"))
    pred["suites"]["rt143"] = [{"id": c["id"], **p} for c in s143["cases"]
                               for p in _cands([c["question"]])]
    import fable_session152_sessions as S152  # noqa: E402 (data only)
    rows = []
    for s in S152.SESSIONS:
        for i, t in enumerate(x["text"] for x in s["turns"]):
            for p in _cands([t]):
                rows.append({"id": f"{s['id']}#{i}", **p})
    pred["suites"]["sessions152"] = rows
    rows = []
    for stag, path in P221.BENCH:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                it = json.loads(line)
                for p in _cands([it["question"]]):
                    rows.append({"id": it["id"], "split": stag, **p})
    pred["suites"]["bench"] = rows
    pred["counts"] = {k: len({r["id"] for r in v})
                      for k, v in pred["suites"].items()}
    Path(args.out).write_text(json.dumps(pred, indent=1, ensure_ascii=False),
                              encoding="utf-8")
    print(json.dumps(pred["counts"]))
    for k, v in pred["suites"].items():
        for r in v:
            print(k, r["id"], r["turn"][:90], r["reading"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
