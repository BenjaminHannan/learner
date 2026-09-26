#!/usr/bin/env python3
"""y1t-H1 scoring adapter (wrong-as-fact thread, 2026-09-26, written before any y1t-H1 run). New file. Counts only.

scripts/claude_y1t_h1run.py writes one row per ask as {"life_id", "turn_index", "kind": "ask", "reply"}. The 336
scorer (scripts/claude_e2e336_score.py) scores rows of kind "user" and names an arm after its file (arm_<name>.jsonl).
So this copies RUN/rows_A.jsonl and rows_B.jsonl to SCORE/arm_A.jsonl and arm_B.jsonl with kind "user" (nothing else
changes; no confirm rows, no notebook; the scorer also needs "ms" and "notebook_events", set to 0.0 and [],
so its ms and notebook counts mean nothing here), then runs the unchanged scorer on them. Every later step (judge prep with
seed 4013, judges, split, marks) reads SCORE/judge_asks_A.jsonl and judge_asks_B.jsonl.

  python3 scripts/claude_y1tH1_score.py PANEL RUN SCORE
  python3 scripts/claude_y1tH1_score.py --selftest       (DEV bank artifacts/claude-e2e331-dev-20260924; readable)
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ld = lambda p: [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]  # noqa: E731


def adapt(run: Path, score: Path) -> dict:
    score.mkdir(parents=True, exist_ok=True)
    n = {}
    for arm in ("A", "B"):
        rows = ld(run / f"rows_{arm}.jsonl")
        assert all(set(r) == {"life_id", "turn_index", "kind", "reply"} and r["kind"] == "ask" for r in rows), arm
        with open(score / f"arm_{arm}.jsonl", "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps({**r, "kind": "user", "ms": 0.0, "notebook_events": []}) + "\n")
        n[arm] = len(rows)
    return n


def score(panel: Path, run: Path, out: Path) -> int:
    n = adapt(run, out)
    print(json.dumps({"rows": n}))
    return subprocess.call([sys.executable, "-B", str(HERE / "claude_e2e336_score.py"), "--bank", str(panel),
                            "--runs", str(out / "arm_A.jsonl"), str(out / "arm_B.jsonl"), "--out", str(out)])


def selftest() -> int:
    dev = HERE.parent / "artifacts/claude-e2e331-dev-20260924"
    turns = ld(dev / "turns.jsonl")
    asks = [t for t in turns if t["kind"] == "ask"]
    with tempfile.TemporaryDirectory() as d:
        run, out = Path(d) / "run", Path(d) / "score"
        run.mkdir()
        for arm, pick in (("A", lambda t: ", ".join(t["gold"].get("values") or []) or "I don't know."),
                          ("B", lambda t: "I don't know.")):
            with open(run / f"rows_{arm}.jsonl", "w", encoding="utf-8") as fh:
                for t in asks:
                    fh.write(json.dumps({"life_id": t["life_id"], "turn_index": t["turn_index"], "kind": "ask",
                                         "reply": pick(t)}) + "\n")
        rc = subprocess.call([sys.executable, "-B", __file__, str(dev), str(run), str(out)], stdout=subprocess.DEVNULL)
        assert rc == 0, rc
        mech = {r["arm"]: r for r in json.loads((out / "mechanical.json").read_text(encoding="utf-8"))}
        assert mech["A"]["user_rows"] == mech["B"]["user_rows"] == len(asks), mech["A"]["user_rows"]
        right_b = sum(v.get("RIGHT", 0) + v.get("RIGHT_CONFIRM", 0) for k, v in mech["B"]["asks"].items()
                      if k not in ("ALL", "never_told"))
        right_a = sum(v.get("RIGHT", 0) + v.get("RIGHT_CONFIRM", 0) for k, v in mech["A"]["asks"].items()
                      if k not in ("ALL", "never_told"))
        assert right_b == 0 < right_a, (right_a, right_b)
        assert (out / "judge_asks_A.jsonl").exists() and (out / "judge_asks_B.jsonl").exists()
        print(f"y1tH1 score selftest ok: {len(asks)} asks per arm; gold-echo arm right {right_a}, idk arm right 0")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(selftest())
    sys.exit(score(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])))
