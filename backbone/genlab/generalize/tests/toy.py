"""Tiny CPU fixtures: a data root (train / dev / validation / probes) and a toy D checkpoint."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import torch

from generalize import probes
from learnlab.village.shards import write_shards

PER_SHARD = 25


def build_root(base: Path, *, train_shards: int = 6, dev_shards: int = 2, probe_visits: int = 50, val_visits: int = 50,
               probe_names=tuple(probes.PROBES)) -> tuple[Path, Path]:
    """(data_root, probe_root). Train = seed-0 train shards; dev = the last of them (as v1/split_dirs.py does)."""
    base = Path(base)
    build = base / "build"
    write_shards("train", (train_shards + dev_shards) * PER_SHARD, build, 1, seed=0, visits_per_shard=PER_SHARD, verbose=False)
    write_shards("validation", val_visits, build, 1, seed=0, visits_per_shard=PER_SHARD, verbose=False)
    root = base / "data"
    for name in ("train", "dev", "validation"):
        (root / name).mkdir(parents=True, exist_ok=True)
    for path in sorted((build / "train").iterdir()):
        if path.name.startswith("shard-"):
            number = int(path.name.split("-")[1].split(".")[0])
            os.link(path, root / ("dev" if number >= train_shards else "train") / path.name)
    for name in ("train", "dev"):
        shutil.copy(build / "train" / "manifest.json", root / name / "manifest.json")
    for path in (build / "validation").iterdir():
        os.link(path, root / "validation" / path.name)
    prob = base / "probes"
    for name in probe_names:
        probes.write_probe(name, probes.PROBES[name], probe_visits, prob, 1, visits_per_shard=PER_SHARD, verbose=False)
    return root, prob


def make_caches(root: Path, tokenizer_path):
    from generalize.evaluate import PlainBudget
    from learnlab.tokenizer import Tokenizer
    from premonition import data as pdata, preprocess
    tok = Tokenizer.load(Path(tokenizer_path))
    det = pdata.name_detector(PlainBudget(root.parent), root.name, log=lambda s: None)
    caches = {n: pdata.load_or_build(PlainBudget(root.parent), root.name, n, tok, det, split="train" if n == "dev" else None,
                                     regime=preprocess.LABEL_FREE, log=lambda s: None) for n in ("train", "dev", "validation")}
    return tok, caches


def train_toy_d(root: Path, tokenizer_path, out: Path, steps: int = 30, *, bridge: bool = False) -> Path:
    """A few CPU steps of the real StepTrainer on a tiny D (d_model 32); saves a D-only (or fake-bridge) checkpoint."""
    from premonition.config import MiniConfig
    from premonition.model import PremonitionMini
    from premonition.train import mini_config_dict, mini_train_config
    from premonition import data as pdata
    from v1 import dtrain
    tok, caches = make_caches(root, tokenizer_path)
    torch.manual_seed(0)
    model = PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=tok.vocab_size))
    trainer = dtrain.StepTrainer(model, mini_train_config(lr=1e-3, warmup_steps=5, log_every=10, memory_check_every=10),
                                 torch.device("cpu"), total_steps=steps, seed=0)
    stream = dtrain.train_stream(caches["train"], 8_000, 0, 0, max_visits=4)
    trainer.run(stream, log=lambda s: None)
    saved = {"model": model.state_dict(), "config": mini_config_dict(model.config), "arm": "toy", "steps": steps}
    if bridge:
        from v1.joint import Bridge
        saved["bridge"] = Bridge(model.config.d_model, 48).state_dict()
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(saved, out)
    return out
