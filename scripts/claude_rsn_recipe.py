#!/usr/bin/env python3
"""Reasoner recipe entry point for sleep (sleep research thread, 2026-09-25).

Sleep (Fix-sleep thread, plan 363) calls this to train the reasoner on a night's practice episodes. It
is 296's runner (claude_rsn294_run.py: copy phase, then group-relative practice with the code
fact-check) with the practice source swapped:

  python claude_rsn_recipe.py train --episodes night.jsonl --mix 0.5 --base 296 \
      --arm plain --seed 1 --out DIR [--init CKPT] [--copy-steps N] [--rl-steps M] [--workers 0]
  python claude_rsn_recipe.py dev|eval --base 296 ...   (same arguments as claude_rsn294_run.py)

--episodes  JSONL, one rsn-294 episode per line ({"category","notebook","frame","gold"}), e.g. from
            claude_slp363_school.build_night (real school) or placebo() of it (placebo arm).
--mix       share of practice puzzles drawn from --episodes (uniformly, with repeats); the rest come
            from 296's generator (general practice, so old skills keep being practised). 0 = the
            "plain practice" arm (same steps, generator only). Default 0.5.
--base      296 = 296's input (current best, plain arm). 355 = rsn-355's shared chain-step input; use it
            only if rsn-355 PASSES, and only with checkpoints trained with it (its extra weights mean a
            296 checkpoint will not load into it, and the reverse).
--init      start from an existing checkpoint (the reasoner as it was before the night). Without it the
            reasoner is trained from scratch.
The episodes' kind is ignored when drawing from the file. dev and eval never use --episodes.
Arm "loop" works too but does not learn yet (rsn-353 is testing the fix); use --arm plain for now.
"""
import json
import random
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _pop(flag, default=None):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        v = sys.argv[i + 1]
        del sys.argv[i:i + 2]
        return v
    return default


EPISODES = _pop("--episodes")
MIX = float(_pop("--mix", "0.5"))
BASE = _pop("--base", "296")
if BASE not in ("296", "355"):
    raise SystemExit("--base must be 296 or 355")

import claude_rsn294_core as C  # noqa: E402
import claude_rsn296_gen  # noqa: E402,F401  (296's generator)
if BASE == "355":
    import claude_rsn355_run  # noqa: E402,F401  (shared chain-step input)

if len(sys.argv) > 1 and sys.argv[1] == "train" and EPISODES and MIX > 0:
    POOL = [json.loads(l) for l in open(EPISODES) if l.strip()]
    if not POOL:
        raise SystemExit("--episodes file is empty")
    for ep in POOL:                                   # fail early on a malformed episode
        enc, infos = C.encode([ep], random.Random(0))
        if C.gold_action(ep, infos[0]) is None:
            raise SystemExit(f"episode has no gold action: {json.dumps(ep)[:200]}")
    _base = C.gen_episode

    def gen_recipe(rng, kind=None, hops=None, n_rows=None, **kw):
        if rng.random() < MIX:
            return json.loads(json.dumps(rng.choice(POOL)))
        return _base(rng, kind, hops, n_rows, **kw)

    C.gen_episode = gen_recipe

if __name__ == "__main__":
    runpy.run_path(str(HERE / "claude_rsn294_run.py"), run_name="__main__")
