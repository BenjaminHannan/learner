"""Train the ab_ob_b4_nb sleep LoRA on K2-Horizon-3.7B (bf16) on the Week-2 world, one run per seed, with the project's own sleep code
(backbone/sleep/brain/sleepb.py at the pinned commit). Nothing of the recipe is re-implemented: this only builds the command line of addendum 11's
k2s_bf16 run (same flags; K2 fixes: --tok-budget 1024, names pass with thinking, thinking-closed prompts are built into sleepb for K2).

sleepb saves the final LoRA to <out>/sleep/s<seed>/adapter (peft format) and its result JSON next to it. Resume: a seed whose adapter and result exist is skipped.
  python -m sleep2.recallread.train_sleep --backbone DIR --week PATH --out DIR [--seeds 1 2]
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .world import K2_MODEL, K2_REVISION

ARM = "ab_ob_b4_nb"


def command(backbone: Path, week: Path, out: Path, seed: int, gen_bs: int = 32) -> list[str]:
    return [sys.executable, str(backbone / "sleep/brain/sleepb.py"), "--arm", ARM, "--tok-budget", "1024", "--model", K2_MODEL, "--revision", K2_REVISION,
            "--week", str(week), "--seed", str(seed), "--out", str(out), "--arc-base", "--gen-bs", str(gen_bs)]


def done(o: Path) -> bool:
    return (o / "adapter" / "adapter_model.safetensors").exists() and (o / f"result_{ARM}.json").exists()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backbone", required=True)
    ap.add_argument("--week", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2])
    ap.add_argument("--gen-bs", type=int, default=32)
    a = ap.parse_args()
    env = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")
    for s in a.seeds:
        o = Path(a.out) / "sleep" / f"s{s}"
        if done(o):
            print(f"seed {s}: adapter already there, skipping", flush=True)
            continue
        shutil.rmtree(o, ignore_errors=True)
        o.mkdir(parents=True)
        cmd = command(Path(a.backbone), Path(a.week), o, s, a.gen_bs)
        print("RUN", " ".join(cmd), flush=True)
        with open(o / "sleepb.log", "w") as lg:
            rc = subprocess.run(cmd, env=env, stdout=lg, stderr=subprocess.STDOUT).returncode
        if rc != 0 or not done(o):
            raise SystemExit(f"sleepb failed for seed {s} (rc {rc}); see {o / 'sleepb.log'}")
        print(f"seed {s}: sleep done", flush=True)


if __name__ == "__main__":
    main()
