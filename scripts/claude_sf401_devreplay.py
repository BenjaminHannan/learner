#!/usr/bin/env python3
"""sf-401 DEV preview on CPU (no GPU, no weights): replay the readable DEV bank (artifacts/claude-e2e331-dev-20260924)
through the listener-level agent with the lis-319 reader's RECORDED readings of those turns
(artifacts/claude-lis319-20260925/reads_e2edev_B.jsonl on builder-outbox), with and without the stale-fact guard.

  A = 292t base + 298 + 274 + listener stack b (313, 315, 314, 316) at 0.995 + 274 reply-first + 334 agenda
      (claude_lis319_arms._build without the live reader; no 1B layers)
  B = A + claude_sf401_agent.install_sf401 right after the listener stack
Turns the recording lacks (the harness's own "yes"/"no" confirm answers) read as CHAT. The recorded readings were made
with lis-319's own history, not this agent's replies, so this is a plumbing and false-alarm preview, not a result.
The 292t self-question router is stubbed to DECLINE (the cloud has no MiniLM), as in the lis-313/314 CPU tests.

usage: claude_sf401_devreplay.py READS.jsonl OUTDIR   -> OUTDIR/arm_A.jsonl, arm_B.jsonl, sf401_counts.jsonl; then
       python3 scripts/claude_e2e336_score.py --bank artifacts/claude-e2e331-dev-20260924 --runs OUTDIR/arm_A.jsonl
               OUTDIR/arm_B.jsonl --out OUTDIR/score
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fable_self122 as SELF122  # noqa: E402

SELF122.route122 = lambda q: ("DECLINE", {"reason": "sf401-devreplay-stub"})

import claude_e2e336_run as R  # noqa: E402

BANK = HERE.parent / "artifacts/claude-e2e331-dev-20260924"
CHAT = ({"act": "CHAT", "facts": [], "ask": None}, [], "replay-default", 0.0)


class Recorded:
    def __init__(self, by_text):
        self.by_text = by_text

    def read(self, turn, prev_reply=""):
        r = self.by_text.get(str(turn))
        if r is None:
            return CHAT
        return (r["frame"], list(r["conf"] or []), r.get("raw", ""), r.get("ms", 0.0))


def make_builder(reader, guard):
    def build(state_dir, args):
        import claude_age334_agent as A334
        import claude_e2e330_arms as A
        import claude_lis_stackb as STACK
        import claude_loop274_agent as L274
        import claude_sf401_agent as SF
        loop = A._base(state_dir, args)
        STACK.build_stack(loop, reader, 0.995, layers=("313", "315", "314", "316"), log_dir=state_dir)
        if guard:
            SF.install_sf401(loop, loop.lis_memo)
        L274.install_turn_reply_first274(loop)
        A334.install_agenda334(loop)
        if guard:
            counts.append(loop.sf401_stats)
        return loop
    return build


counts: list = []


def main() -> int:
    reads_path, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    turns = R.load(BANK / "turns.jsonl")
    truth = R.load(BANK / "truth.jsonl")
    tx = {"%s:%d" % (t["life_id"], t["turn_index"]): t["user_text"] for t in turns}
    by_text = {}
    for r in R.load(reads_path):
        by_text[tx[r["id"]]] = r
    reader = Recorded(by_text)
    lives: dict = {}
    for t in turns:
        lives.setdefault(t["life_id"], []).append(t)
    for name, guard in (("A", False), ("B", True)):
        rows: list = []
        for lid, ts in lives.items():
            ts.sort(key=lambda x: x["turn_index"])
            R.run_life(make_builder(reader, guard), None, lid, ts,
                       [f for f in truth if f["life_id"] == lid], rows)
        (out / f"arm_{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                               encoding="utf-8")
        print(name, "rows", len(rows), flush=True)
    keys = sorted({k for c in counts for k in c})
    total = {k: sum(c.get(k, 0) for c in counts) for k in keys if k != "doubts_live"}
    (out / "sf401_counts.jsonl").write_text(json.dumps(total, sort_keys=True) + "\n", encoding="utf-8")
    print("sf401 counts (summed over built agents):", json.dumps(total, sort_keys=True))
    return 0


if __name__ == "__main__":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    sys.exit(main())
