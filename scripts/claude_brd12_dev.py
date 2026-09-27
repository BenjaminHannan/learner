#!/usr/bin/env python3
"""DEV only (Creative thread, 2026-09-27): how much could hindsight relabelling give on Sleep research's key games?
For level-1 key games the plain 1B reached 0 of 10 goals in 30 samples (brd-11 DEV-NOTE). Hindsight relabelling
(HER) keeps a failed attempt's legal moves and rewrites the goal to the room those moves actually reached, so every
walk becomes a correct example for some goal. This probe counts, per game, how many samples have at least one legal
move and how many DISTINCT relabelled goals (rooms reached other than the start and the asked goal) they give.
Checked with the world's own simulator (claude_textgames._start_and_moves / check; the world file is not edited).
DEV seeds 900000-900999 only. Writes one JSON summary.

  python -B scripts/claude_brd12_dev.py --model M --out F.json --level 1 --items 10 [--n 30 --temp 1.0]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_latin_dev as L  # noqa: E402
import claude_textgames as G  # noqa: E402


def walk(g, reply):
    """legal prefix of the reply's action lines, with the room after each legal move (keys games)."""
    s, moves, _ = G._start_and_moves(g)
    acts = [re.sub(r"^[\s\-\*\d\.\)]*", "", x).strip().lower().rstrip(".") for x in reply.splitlines()]
    acts = [a for a in acts if re.match(r"^(go|take|make|press)\b", a)]
    rooms = []
    for a in acts:
        nxt = dict((x.lower(), t) for x, t in moves(s)).get(a)
        if nxt is None:
            break
        s = nxt
        rooms.append(s[0])
    return rooms


def relabel(g, reply):
    """HER: goals (rooms) this reply's legal moves reached, other than the start and the asked goal; for each, the
    relabelled game (same maze, goal = that room) must accept the reply (checked by claude_textgames.check)."""
    out = set()
    for r in set(walk(g, reply)) - {g["start"], g["goal"]}:
        h = dict(g, goal=r)
        if G.check(h, reply)["ok"]:
            out.add(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--items", type=int, default=10)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--temp", type=float, default=1.0)
    a = ap.parse_args()
    t0, smp, rows = time.time(), L.Sampler(a.model), []
    for seed in list(L.DEV_SEEDS)[:a.items]:
        g = G.make_game("keys", seed, a.level)
        it = {"prompt": g["text"], "size": 0, "cap": 12 * len(g["plan"]) + 24}
        reps = smp.generate(it, a.n, a.temp)
        goals = set().union(*(relabel(g, t) for t in reps))
        rows.append({"seed": seed, "plan_len": len(g["plan"]), "rooms": len(g["rooms"]),
                     "hits": sum(G.check(g, t)["ok"] for t in reps),
                     "with_legal_move": sum(bool(walk(g, t)) for t in reps),
                     "relabelled_goals": len(goals)})
        print(json.dumps(rows[-1]), flush=True)
        Path(a.out).write_text(json.dumps({"rows": rows}, indent=1), encoding="utf-8")
    res = {"level": a.level, "n": a.n, "temp": a.temp, "items": len(rows), "rows": rows,
           "games_with_hit": sum(r["hits"] > 0 for r in rows),
           "games_with_relabelled_goal": sum(r["relabelled_goals"] > 0 for r in rows),
           "relabelled_goals_total": sum(r["relabelled_goals"] for r in rows),
           "minutes": round((time.time() - t0) / 60, 1)}
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}))


if __name__ == "__main__":
    main()
