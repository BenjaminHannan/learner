"""D-only training run for generalization A/B experiments.

  python -m generalize.dtrain_only --root DATA_ROOT --out OUT --steps N [--seed S] [--device cuda]
      [--extra-train DIR ...] [--weight-decay W] [--price-per-hour P --spend-cap C]

D = PremonitionMini.preset("D", "full", decoder_raw_cards=True) (S2 on), trained with the v1 FULL recipe for D: Muon on 2-D hidden
matrices (v1.dtrain.StepTrainer(optimizer="muon")), MAX_TOKENS 55,000, MAX_VISITS 48, LR 1e-3, warmup 100, curriculum by step share,
bf16 autocast on CUDA, checkpoint every 5% of steps, exact resume. NO creative module, NO bridge, NO sleep, NO G1.

Data: train/dev/validation caches via v1.dtrain.open_data. The sealed `test` split is never built or opened (asserted below).

--extra-train DIR (repeatable): extra shard directories (a directory holding shard-*.txt/.jsonl, or one holding a `train/` subdirectory
with them, i.e. write_shards output). Their caches are built with the SAME train-fitted name detector and the label-free regime. They
are mixed into the batch stream at the BATCH level: each step draws its batch from one source stream, chosen by a deterministic
function of (seed, step) with probability proportional to the source's token count (main train first). Every source has its own
shuffled endless stream (seed + 1000*i), so with no extra dirs the stream is exactly v1.dtrain.train_stream. Resume re-derives the
per-source batch counts from the step number, so it is exact. Extra caches are saved under OUT/extra-cache and reused on resume.

Outputs in OUT: dev_evals.jsonl (JSON lines every 10% of steps), wake-ckpt/ (every 5%), final.json, D-final.pt (no "bridge" key).
Exit code 0 = finished, 3 = stopped early by the spend guard, the deadline or a non-finite loss (the last state is judged and saved).
"""
from __future__ import annotations

import os as _os
_os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import argparse
import itertools
import json
import random
import time
from pathlib import Path
from typing import Any, Optional

import torch

from premonition import data as pdata
from premonition import preprocess
from premonition.config import MiniConfig
from premonition.model import PremonitionMini
from premonition.train import mini_config_dict, mini_train_config, validation_hook
from v1 import ckpt as vckpt
from v1 import dtrain
from v1.extra import mixed_stream, open_extra, shard_dir  # noqa: F401  (shared with v1.run; re-exported)
from v1.run import CKPT_FRACTION, DEV_EVAL_VISITS, LR, MAX_TOKENS, MAX_VISITS, WARMUP, make_eval_batches

EVAL_FRACTION = 0.10
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


class Stop(RuntimeError):
    def __init__(self, rule: str, why: str) -> None:
        super().__init__(f"{rule}: {why}")
        self.rule, self.why = rule, why


def build_d(vocab_size: int, seed: int, halt_target: str = "correct") -> PremonitionMini:
    torch.manual_seed(seed)
    return PremonitionMini(MiniConfig.preset("D", "full", vocab_size=vocab_size, decoder_raw_cards=True, halt_target=halt_target))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="data root with train/ dev/ validation/ (the sealed `test` dir is never read)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--extra-train", action="append", default=[], metavar="DIR")
    ap.add_argument("--weight-decay", type=float, default=None, help="default: TrainConfig's 0.1")
    ap.add_argument("--halt-target", default="correct", choices=("correct", "correct_and_evidence"),
                    help="HALT BCE target (premonition.config.MiniConfig.halt_target); 'correct' = v1")
    ap.add_argument("--price-per-hour", type=float, default=0.0)
    ap.add_argument("--spend-cap", type=float, default=3.0)
    ap.add_argument("--stop-at-epoch", type=float, default=None, help="wall-clock deadline (unix s): stop, save and judge before it")
    ap.add_argument("--tokenizer", default=str(Path(__file__).resolve().parent.parent / "data/tokenizer/premonition-tok-v2.json"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--eval-visits", type=int, default=DEV_EVAL_VISITS)
    ap.add_argument("--ckpt-every", type=int, default=None, help="tests only (default 5%% of steps)")
    ap.add_argument("--eval-every", type=int, default=None, help="tests only (default 10%% of steps)")
    a = ap.parse_args(argv)
    t_start = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device(a.device)
    root = Path(a.root)
    data = dtrain.open_data(root, Path(a.tokenizer), workers=a.workers, log=lambda s: None)
    # the sealed split guarantee: only these three caches exist in memory, none from `test`, and no cache file for it was written
    for name, cache in (("train", data.train), ("dev", data.dev), ("validation", data.validation)):
        assert Path(cache.info["source"]).name != dtrain.SEALED, "the sealed split must never be opened"
    assert not any(p.name.startswith(dtrain.SEALED) for p in root.glob("premonition-v*/*")), "a sealed-split cache exists"
    extra = open_extra([Path(d) for d in a.extra_train], data, out, a.workers)
    caches = [data.train] + extra
    d_model = build_d(data.tokenizer.vocab_size, a.seed, a.halt_target)
    d_model.to(device)
    over = {} if a.weight_decay is None else {"weight_decay": a.weight_decay}
    tc = mini_train_config(lr=LR, warmup_steps=WARMUP, log_every=50, memory_check_every=50, **over)
    trainer = dtrain.StepTrainer(d_model, tc, device, total_steps=a.steps, seed=a.seed, optimizer="muon")
    (out / "grouping.json").write_text(json.dumps(trainer.optimizer_grouping(), indent=1))
    ck_dir = out / "wake-ckpt"
    got = vckpt.load(ck_dir)
    if got is not None:
        trainer.restore(got)
        log(f"RESUMED from step {trainer.step}")
    ledger = out / "spend.json"
    prior = json.loads(ledger.read_text()) if ledger.exists() else {}
    elapsed_before = float(prior.get("elapsed_s", 0.0))
    t0 = time.time()
    elapsed = lambda: elapsed_before + (time.time() - t0)

    def save_ledger() -> None:
        ledger.write_text(json.dumps({"elapsed_s": elapsed(), "price_per_hour": a.price_per_hour,
                                      "usd": elapsed() / 3600 * a.price_per_hour}))

    dev_batches, stops = make_eval_batches(data.dev, a.eval_visits, data.tokenizer)
    full_val, _ = make_eval_batches(data.validation, len(data.validation), data.tokenizer)
    full_dev, _ = make_eval_batches(data.dev, len(data.dev), data.tokenizer)

    def score(batches) -> dict[str, Any]:
        r = validation_hook(batches, tokenizer=data.tokenizer, stop=stops)(d_model)
        return {"accuracy": r["accuracy"], "questions": r["questions"], "gold_recall_at_4": r.get("gold_recall_at_4"),
                "loops_mean": r["loops_mean"], "halt_rate": r.get("halt_rate"), "by_depth": r.get("by_depth")}

    evals = out / "dev_evals.jsonl"

    def periodic(model) -> dict[str, Any]:
        row = {"step": trainer.step, "dev512": score(dev_batches), "validation": score(full_val), "usd": elapsed() / 3600 * a.price_per_hour}
        with evals.open("a") as f:
            f.write(json.dumps(row, default=float) + "\n")
        print(json.dumps(row, default=float), flush=True)
        return {"dev512": row["dev512"]["accuracy"], "validation": row["validation"]["accuracy"]}

    def on_step(step: int, res: dict) -> None:
        if a.price_per_hour and elapsed() / 3600 * a.price_per_hour >= a.spend_cap:          # A4-style spend guard
            raise Stop("A4", f"spend cap ${a.spend_cap:.2f} reached (${elapsed() / 3600 * a.price_per_hour:.2f})")
        if a.stop_at_epoch and time.time() >= a.stop_at_epoch:
            raise Stop("DEADLINE", "wall-clock deadline reached")

    ckpt_every = a.ckpt_every or max(1, int(CKPT_FRACTION * a.steps))
    eval_every = a.eval_every or max(1, int(EVAL_FRACTION * a.steps))
    stream = mixed_stream(caches, a.max_tokens, a.seed, trainer.step, MAX_VISITS)
    aborted, stats = None, {"steps": 0, "seconds": 0.0, "tokens_per_s": 0.0}
    if trainer.step < a.steps:
        try:
            stats = trainer.run(stream, ckpt_dir=ck_dir, ckpt_every=ckpt_every, eval_fn=periodic, eval_every=eval_every,
                                log=log, on_step=on_step)
        except Stop as s:
            aborted = {"rule": s.rule, "why": s.why, "step": trainer.step}
            vckpt.save(ck_dir, trainer.step, trainer.checkpoint_payload())        # the last state is the checkpoint that gets judged
        except FloatingPointError as e:                                            # NaN: stop; judge the last good checkpoint
            aborted = {"rule": "NAN", "why": str(e), "step": trainer.step}
            back = vckpt.load(ck_dir)
            if back is None:
                log("non-finite loss before the first checkpoint: nothing to judge")
                (out / "final.json").write_text(json.dumps({"aborted": aborted, "args": vars(a)}, indent=1))
                return 3
            trainer.restore(back)
    save_ledger()
    final_step = trainer.step
    res = {"arm": "d-only", "steps": final_step, "steps_planned": a.steps, "aborted": aborted, "seconds": stats["seconds"],
           "tokens_per_s": stats["tokens_per_s"], "wall_total_s": time.time() - t_start,
           "dev": score(full_dev), "validation": score(full_val),
           "dev_accuracy": None, "validation_accuracy": None, "args": vars(a),
           "extra_train": [{"dir": d, "visits": len(c), "tokens": int(c.lengths.sum())} for d, c in zip(a.extra_train, extra)]}
    res["dev_accuracy"], res["validation_accuracy"] = res["dev"]["accuracy"], res["validation"]["accuracy"]
    torch.save({"model": d_model.state_dict(), "config": mini_config_dict(d_model.config), "arm": "d-only", "steps": final_step,
                "args": vars(a)}, out / "D-final.pt")
    (out / "final.json").write_text(json.dumps(res, indent=1, default=float))
    log("FINAL", json.dumps({k: res[k] for k in ("steps", "dev_accuracy", "validation_accuracy", "aborted")}, default=float))
    return 3 if aborted else 0


if __name__ == "__main__":
    raise SystemExit(main())
