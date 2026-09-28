#!/usr/bin/env python3
"""Credit check and channel-use numbers for the general reach-channel design (report-only; PASSMARKS.md "Credit check").

Reads one practised-and-adapted run folder (r1g-pre-s{seed}: adapt.json and the stage checkpoints k*.pt), and the practised source
checkpoint. Writes credit-s{seed}.json and use-s{seed}.json next to --out. DEV panel only: the holdout is never opened here.
  credit: the k = 1,024 net scored on the dev 9x9 mazes with the reach features on (from adapt.json) and switched off at inference
          (Net.REACH_OFF = True: the ten features are replaced by zeros, everything else unchanged)
  use:    mean |mix.weight| of the source checkpoint (after practice) and of k16384.pt (after adaptation), plus gamma and the
          mean |mix.weight| by feature column at each

  python3 scripts/claude_dir_r1g_credit.py --seed 0 --run <eq-runs>/r1g-pre-s0 --source <runs>/r1g-s0 --out <folder> --threads 1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_r1g_net as R  # noqa: E402
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402


def load(path):
    net = R.Net("loop")
    net.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
    return net


def use(net):
    w = net.mix.weight.detach()
    return {"mix_mean_abs": float(w.abs().mean()), "mix_mean_abs_by_feature_column": [round(float(x), 6) for x in w.abs().mean(0)],
            "gamma": float(torch.sigmoid(net.reach_g).detach())}


def main(seed, run, source, out, k=1024):
    B.N = R
    dev = json.loads((run / "adapt.json").read_text())
    if (dev["arm"], dev["seed"], dev["init"]) != ("loop", seed, "pre"):
        raise ValueError("run identity mismatch")
    depth = dev["fixed_depth"]
    panels, _ = D.panels()
    net = load(run / f"k{k}.pt")
    on = B.maze_scores(net, panels["dev"], depth)["9"]["right"]
    if on != dev["rungs"][str(k)]["9"]["right"]:
        raise ValueError(f"reload does not reproduce the recorded dev score: {on} vs {dev['rungs'][str(k)]['9']['right']}")
    R.Net.REACH_OFF = True
    try:
        off = B.maze_scores(net, panels["dev"], depth)["9"]
    finally:
        R.Net.REACH_OFF = False
    out.mkdir(parents=True, exist_ok=True)
    B.dump(out / f"credit-s{seed}.json", {"seed": seed, "k": k, "split": "dev", "dev_9x9_on": on, "dev_9x9_off": off["right"],
                                          "n": off["n"], "drop": on - off["right"], "mean_rounds_off": off["mean_rounds"],
                                          "cap_hits_off": off["cap_hits"]})
    prac, adapted = use(load(source / "source.pt")), use(load(run / "k16384.pt"))
    B.dump(out / f"use-s{seed}.json", {"seed": seed, "mix_mean_abs": {"practice": prac["mix_mean_abs"], "k16384": adapted["mix_mean_abs"]},
                                       "practice": prac, "k16384": adapted})
    print(json.dumps({"seed": seed, "dev_9x9_on": on, "dev_9x9_off": off["right"], "drop": on - off["right"],
                      "mix_mean_abs_practice": prac["mix_mean_abs"], "mix_mean_abs_k16384": adapted["mix_mean_abs"]}))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, choices=(0, 1), required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--threads", type=int, default=1)
    a = p.parse_args()
    torch.set_num_threads(a.threads)
    main(a.seed, a.run, a.source, a.out)
