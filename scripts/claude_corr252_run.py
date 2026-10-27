#!/usr/bin/env python3
"""Exp 252 runner: one fresh work dir per item; setup turns, turn, followup
in one session (the corrpanel252 schema). Read-only on the agent.

Dev items may also carry "restart": true (the daemon is rebuilt on the same
root between turn and followup) and "extra": [[question, must_not, must]]
(asked after the followup; checked by the scorer, dev only).

usage: claude_corr252_run.py --agent A --config C --cases X.jsonl
                             --work DIR --out rows.jsonl
Row fields = base138k.jsonl's 7 data fields (+ extra_replies, stored_end,
ms_per_turn). base_right / base_wrong_value are left to the scorer.
"""
from __future__ import annotations

import argparse
import gc
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_marks123_all as M  # noqa: E402 (read-only)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    _mod, dcls, _, _ = M.load_agent(args.agent)
    import fable_loop90_agent as L90  # noqa: E402 (after agent import)
    base = M.load_base_cfg(args.config)
    items = [json.loads(line) for line in
             Path(args.cases).read_text(encoding="utf-8").splitlines()
             if line.strip()]
    work = Path(args.work)
    rows = []
    for it in items:
        root = work / it["id"]
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        state = {"d": M.make_daemon(dcls, base, root), "k": 0}
        times: list[float] = []

        def say(text: str) -> str:
            k = state["k"]
            f = root / "inbox" / f"m{k:03d}.txt"
            f.write_text(text, encoding="utf-8")
            t0 = time.perf_counter()
            try:
                state["d"].process_file(f)
                rep = (root / "outbox" / f"m{k:03d}.txt").read_text(
                    encoding="utf-8").strip()
            except Exception as e:  # noqa: BLE001
                rep = f"CRASH {type(e).__name__}: {e}"
            times.append((time.perf_counter() - t0) * 1000.0)
            state["k"] = k + 1
            return rep

        def stored() -> list[list[str]]:
            return [list(map(str, t)) for t in
                    L90.notebook_triples(state["d"].loop.nb)]

        setup_replies = [say(t) for t in it["setup"]]
        s_setup = stored()
        turn_reply = say(it["turn"])
        s_turn = stored()
        if it.get("restart"):
            del state["d"]
            gc.collect()
            state["d"] = M.make_daemon(dcls, base, root)
        followup_reply = say(it["followup"])
        s_follow = stored()
        extra_replies = [say(q[0]) for q in it.get("extra", [])]
        row = {"id": it["id"], "setup_replies": setup_replies,
               "stored_after_setup": s_setup, "turn_reply": turn_reply,
               "stored_after_turn": s_turn, "followup_reply": followup_reply,
               "stored_after_followup": s_follow,
               "extra_replies": extra_replies, "stored_end": stored(),
               "ms_per_turn": times}
        rows.append(row)
        print(f"{it['id']} {it['family']}: {it['turn']!r} -> {turn_reply!r}"
              f" | {it['followup']!r} -> {followup_reply!r}", flush=True)
        del state["d"]
        gc.collect()
    Path(args.out).write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
