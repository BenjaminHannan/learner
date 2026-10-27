#!/usr/bin/env python3
"""Experiment 43F: push the rank-limited sleep update until it breaks.

43E (confirmed on fresh seeds): cutting each block matrix's total sleep change to rank 4
beat plain replay at 80 training episodes.  Two questions, one knob each:
  episodes  does the gain survive with 50 or 20 episodes (20% always held out)?
  rank      is 4 special?  ranks 1, 2, 8, 16 at 100 episodes.   rank 0 = plain replay.
Runs 43E's code unchanged, only setting its three constants.  Primary score = FINAL update,
so no checkpoint rule is involved.  Imports 43E read-only.  One CPU thread per process.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch

import fable_cardfold_sleep as C
import fable_sleepselect43e as E


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--rank", type=int, required=True, help="0 = plain replay")
    p.add_argument("--episodes", type=int, required=True)
    p.add_argument("--base-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--smoke", action="store_true", help="250 updates, no claim")
    a = p.parse_args()
    torch.set_num_threads(1)
    torch.manual_seed(C.derive_seed("sleep43e/torch", a.seed) & ((1 << 63) - 1))   # same as 43E
    E.EPISODES, E.HELD_OUT, E.RANK = a.episodes, a.episodes // 5, max(a.rank, 1)
    r = E.run(a.seed, "rank4" if a.rank else "plain", a.base_dir, 250 if a.smoke else E.UPDATES)
    r.update(rank=a.rank, episodes=a.episodes, smoke=a.smoke, final=r["checks"][-1],
             script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f"seed{a.seed}-ep{a.episodes}-rank{a.rank}.json").write_text(json.dumps(r, indent=1))
    print(json.dumps({"seed": a.seed, "rank": a.rank, "episodes": a.episodes, "final": r["final"]}))


if __name__ == "__main__":
    main()
