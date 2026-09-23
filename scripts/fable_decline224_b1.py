#!/usr/bin/env python3
"""Exp 224b mark B1 driver: sealed fresh decline cases, one fresh agent per case.

Each case = optional setup teach turns + one probe turn, in a fresh isolated
state dir under --scratch (never the repo notebook/). Per case it records the
probe reply, the notebook triples before/after the probe turn, and (loop224)
the type the new agent chose.

  --agent 138i : pre-check / baseline (Q2, S1 cases must get the glue today;
                 Q1 control cases must not)
  --agent 224  : B1 (Q2/S1 cases must get their type's sentence, 0 writes;
                 Q1 control cases must be byte-identical to the 138i reply)

  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_decline224_b1.py --agent 224 \\
    --cases artifacts/fable-decline224-20260922/224b/cases224b.json \\
    --baseline <138i json> --scratch <dir> --out <json>
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent
import fable_decline224 as DEC  # noqa: E402
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)

CFG = ROOT / "artifacts" / "fable-agent138i-20260922" / "loop138i-config.json"


def build(agent: str, state_dir: str):
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    cfg["state_dir"] = state_dir
    cfg["sleep_threshold"] = 100000
    if agent == "224":
        import fable_loop224_agent as M
        return M.build_agent224(cfg)
    import fable_loop138i_agent as M
    return M.build_agent138i(cfg)


def trip(loop) -> list:
    return sorted([list(t) for t in L90.notebook_triples(loop.nb)])


def run_case(agent: str, case: dict, scratch: Path) -> dict:
    sd = tempfile.mkdtemp(prefix=f"b1-{agent}-{case['id']}-", dir=scratch)
    loop = build(agent, sd)
    setup = [" ".join(loop.turn(t)) for t in case.get("setup", [])]
    before = trip(loop)
    said = loop.turn(case["text"])
    after = trip(loop)
    kind = None
    if agent == "224" and loop.decline224_log and \
            loop.decline224_log[-1]["text"] == case["text"]:
        kind = loop.decline224_log[-1]["kind"]
    return {"id": case["id"], "type": case["type"], "text": case["text"],
            "setup_replies": setup, "reply": said, "kind": kind,
            "writes": [t for t in after if t not in before]
            + [["-"] + t for t in before if t not in after]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", choices=["138i", "224"], required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--baseline", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))["cases"]
    scratch = Path(args.scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    glue = DEC.GLUE138
    base = {}
    if args.baseline:
        base = {r["id"]: r for r in json.loads(
            Path(args.baseline).read_text(encoding="utf-8"))["rows"]}
    rows, fails = [], []
    for c in cases:
        r = run_case(args.agent, c, scratch)
        if args.agent == "138i":
            want_glue = c["type"] in ("Q2", "S1")
            ok = (r["reply"] == [glue]) == want_glue and not r["writes"]
        elif c["type"] in ("Q2", "S1"):
            ok = (r["reply"] == [DEC.NEW_SENTENCES224[c["type"]]]
                  and r["kind"] == c["type"] and not r["writes"])
            if base:
                ok = ok and base[c["id"]]["reply"] == [glue]
        else:
            ok = (base.get(c["id"], {}).get("reply") == r["reply"]
                  and r["reply"] != [glue] and not r["writes"])
        r["ok"] = ok
        rows.append(r)
        if not ok:
            fails.append(c["id"])
    by = {}
    for r in rows:
        d = by.setdefault(r["type"], {"n": 0, "ok": 0})
        d["n"] += 1
        d["ok"] += int(r["ok"])
    rep = {"agent": args.agent, "by_type": by, "fails": fails,
           "writes_total": sum(len(r["writes"]) for r in rows), "rows": rows}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(rep, indent=1, ensure_ascii=False),
                              encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k != "rows"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
