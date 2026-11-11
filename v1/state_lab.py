"""State lab: D ALONE (no creative model, no bridge) with the FULL recipe of v1/run.py (Muon + S2), one architecture arm at a time,
and diagnostics of how the trained D uses its looped state.

  python -m v1.state_lab train --arm NAME --root DATA_ROOT --out OUT --steps N [--seed S] [--device cuda]
  python -m v1.state_lab diag  --ckpt OUT/D-final.pt --root DATA_ROOT --out OUT/diag.json [--max-visits 1000]

Train writes OUT/ckpt (every 10%, exact resume), OUT/dev_evals.jsonl (every 10%, 512 dev visits), OUT/D-final.pt and OUT/final.json.
The sealed `test` split is never opened (dtrain.open_data does not list it). Plain JSON out; no new dependencies.
"""
from __future__ import annotations

import argparse
import collections
import functools
import json
import os as _os
import time
from pathlib import Path
from typing import Any, Callable, Optional

_os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import torch

from learnlab import step1
from premonition import data as pdata
from premonition.config import MiniConfig
from premonition.model import PremonitionMini
from premonition.train import (judge, mini_config_dict, mini_config_from, mini_train_config,
                               validation_hook)
from v1 import ckpt as vckpt, dtrain
from v1.run import DEV_EVAL_VISITS, LR, MAX_TOKENS, MAX_VISITS, WARMUP      # the fixed recipe constants of the FULL arm

DEFAULT_TOKENIZER = Path(__file__).resolve().parent.parent / "data/tokenizer/premonition-tok-v2.json"
FRACTION = 0.10                      # checkpoint and dev-eval interval, as a share of the steps

# arm -> MiniConfig overrides on top of preset("D", "full", decoder_raw_cards=True). `base` with --seed 1 is the noise arm.
ARMS: dict[str, dict[str, Any]] = {
    "base": {},
    "inject": {"think_inject": True},
    "reg16": {"registers": 16},
    "mq4": {"multi_query": 4},
    "lastloss": {"ans_last_only": True},
    "reg16mq4": {"registers": 16, "multi_query": 4},
    "all3": {"registers": 16, "multi_query": 4, "ans_last_only": True},
}

log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def build_d(arm: str, vocab_size: int, seed: int) -> PremonitionMini:
    torch.manual_seed(seed)
    cfg = MiniConfig.preset("D", "full", vocab_size=vocab_size, decoder_raw_cards=True, **ARMS[arm])
    return PremonitionMini(cfg)


def make_eval_batches(cache, n_visits: Optional[int], tokenizer) -> tuple[list, list[int]]:
    chosen = list(range(min(n_visits, len(cache)) if n_visits else len(cache)))
    groups = pdata.length_batches(cache.lengths[chosen].tolist(), MAX_TOKENS, max_visits=MAX_VISITS)
    return [pdata.collate(cache, [chosen[i] for i in g]) for g in groups], sorted(step1.stop_ids(tokenizer)[0])


def summary(r: dict[str, Any]) -> dict[str, Any]:
    return {"accuracy": r["accuracy"], "questions": r["questions"], "loops_mean": r["loops_mean"],
            "gold_recall_at_4": r.get("gold_recall_at_4")}


def with_min_loops(model: PremonitionMini, k: int, fn: Callable[[], Any]) -> Any:
    """Run `fn` with every `model.answer` call using min_loops=k (instance shadow, removed afterwards)."""
    model.answer = functools.partial(PremonitionMini.answer, model, min_loops=k)     # type: ignore[method-assign]
    try:
        return fn()
    finally:
        del model.answer


# ----------------------------------------------------------------------------- train
def train(a) -> int:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device(a.device)
    data = dtrain.open_data(Path(a.root), Path(a.tokenizer), workers=a.workers, log=lambda s: None)
    model = build_d(a.arm, data.tokenizer.vocab_size, a.seed).to(device)
    tc = mini_train_config(lr=LR, warmup_steps=WARMUP, log_every=50, memory_check_every=50)
    trainer = dtrain.StepTrainer(model, tc, device, total_steps=a.steps, seed=a.seed, optimizer="muon")
    log(f"arm {a.arm} seed {a.seed} steps {a.steps} params {model.num_parameters():,} config {json.dumps(ARMS[a.arm])}")
    ck_dir = out / "ckpt"
    prior = 0.0
    got = vckpt.load(ck_dir)
    if got is not None:
        trainer.restore(got)
        prior = float((got.get("extra") or {}).get("seconds", 0.0))
        log(f"RESUMED from step {trainer.step}")
    ckpt_every = a.ckpt_every or max(1, int(FRACTION * a.steps))
    eval_every = a.eval_every or max(1, int(FRACTION * a.steps))
    eval_batches, stops = make_eval_batches(data.dev, a.eval_visits, data.tokenizer)
    hook = validation_hook(eval_batches, tokenizer=data.tokenizer, stop=stops)
    evals_path = out / "dev_evals.jsonl"
    t0 = time.time()

    def evaluate(m):
        was = m.training
        m.eval()
        try:
            res = summary(hook(m))
        finally:
            m.train(was)
        with evals_path.open("a") as f:
            f.write(json.dumps({"step": trainer.step, **res}) + "\n")
        return res

    # StepTrainer.checkpoint_payload carries `extra`; keep the wall seconds there so a resume adds up.
    original = trainer.checkpoint_payload
    trainer.checkpoint_payload = lambda extra=None: original({"seconds": prior + time.time() - t0})   # type: ignore[method-assign]
    stream = dtrain.train_stream(data.train, MAX_TOKENS, a.seed, trainer.step, MAX_VISITS)
    trainer.run(stream, ckpt_dir=ck_dir, ckpt_every=ckpt_every, eval_fn=evaluate, eval_every=eval_every, log=log,
                stop_after=a.stop_after)
    if trainer.step < a.steps:
        log("stopped early (testing)")
        return 0
    seconds = prior + time.time() - t0
    vckpt.save(ck_dir, trainer.step, trainer.checkpoint_payload())
    torch.save({"model": model.state_dict(), "config": mini_config_dict(model.config), "arm": a.arm, "seed": a.seed,
                "steps": trainer.step}, out / "D-final.pt")
    model.eval()
    res: dict[str, Any] = {"arm": a.arm, "seed": a.seed, "steps": trainer.step, "seconds": seconds}
    for name, cache in (("dev", data.dev), ("validation", data.validation)):
        batches, stops = make_eval_batches(cache, a.final_visits, data.tokenizer)
        final_hook = validation_hook(batches, tokenizer=data.tokenizer, stop=stops)
        r = final_hook(model)
        res[f"{name}_accuracy"] = r["accuracy"]
        res[f"{name}_loops_mean"] = r["loops_mean"]
        res[f"{name}_gold_recall_at_4"] = r.get("gold_recall_at_4")
        res[f"{name}_questions"] = r["questions"]
        # HALT ignored before loop 8: matters for `lastloss` (not trained to answer early); reported for every arm.
        r8 = with_min_loops(model, model.config.max_loops, lambda: final_hook(model))
        res[f"{name}_accuracy_min_loops8"] = r8["accuracy"]
        res[f"{name}_loops_mean_min_loops8"] = r8["loops_mean"]
        res[f"{name}_gold_recall_at_4_min_loops8"] = r8.get("gold_recall_at_4")
    res["loops_mean"] = res["validation_loops_mean"]
    res["gold_recall_at_4"] = res["validation_gold_recall_at_4"]
    (out / "final.json").write_text(json.dumps(res, indent=1, default=float))
    log("FINAL", json.dumps(res, default=float))
    return 0


# ----------------------------------------------------------------------------- diag
def _groups(model: PremonitionMini) -> dict[str, slice]:
    c = model.config
    return {"question": slice(0, c.question_rows), "slots": slice(c.question_rows, model._card_base),
            "cards": slice(model._card_base, model._register_base),
            "registers": slice(model._register_base, model._register_base + c.registers)}


class Recorder:
    """Instance-level shadows on `model` (removed on exit): per-loop state change, loop-0 question rows, lesions."""

    def __init__(self, model: PremonitionMini) -> None:
        self.model = model
        self.change: dict[tuple[int, str], list[float]] = collections.defaultdict(lambda: [0.0, 0])   # (loop, group) -> [sum, n]
        self.record = False
        self.lesion: Optional[str] = None        # None | "registers_1plus" | "registers_all" | "question_reset"
        self.start_rows: Optional[torch.Tensor] = None

    def __enter__(self) -> "Recorder":
        m, groups = self.model, _groups(self.model)
        step, start, greedy = m._step, m._start, m._greedy

        def _start(batch, hidden, store, mentions):
            episode = start(batch, hidden, store, mentions)
            self.start_rows = episode.x[:, :m.config.question_rows].clone()        # the question rows at loop 0
            return episode

        def _step(episode, index, loop, store):
            if not self.record:
                return step(episode, index, loop, store)
            before, valid = episode.x[index][:, :m.config.rows].clone(), episode.valid[index][:, :m.config.rows]
            result = step(episode, index, loop, store)
            after = episode.x[index][:, :m.config.rows]
            for name, sl in groups.items():
                keep = valid[:, sl].unsqueeze(-1).float()
                num = ((after[:, sl] - before[:, sl]) * keep).float().flatten(1).norm(dim=1)
                den = (before[:, sl] * keep).float().flatten(1).norm(dim=1)
                ok = den > 0
                if ok.any():
                    entry = self.change[(loop + 1, name)]
                    entry[0] += float((num[ok] / den[ok]).sum())
                    entry[1] += int(ok.sum())
            return result

        def _greedy(batch, episode, mentions, stop):
            if self.lesion:
                x, base, regs = episode.x.clone(), m._register_base, m.config.registers
                if self.lesion == "registers_1plus":
                    x[:, base + 1:base + regs] = 0
                elif self.lesion == "registers_all":
                    x[:, base:base + regs] = 0
                elif self.lesion == "question_reset":
                    x[:, :m.config.question_rows] = self.start_rows.to(x.dtype)
                episode.x = x
            return greedy(batch, episode, mentions, stop)

        m._start, m._step, m._greedy = _start, _step, _greedy      # type: ignore[method-assign]
        return self

    def __exit__(self, *exc: Any) -> None:
        for name in ("_start", "_step", "_greedy"):
            delattr(self.model, name)


@torch.no_grad()
def diagnose(model: PremonitionMini, batches: list, tokenizer, stops: list[int]) -> dict[str, Any]:
    device = next(model.parameters()).device
    max_loops = model.config.max_loops
    acc: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])          # name -> [correct, n]
    loops_hist: collections.Counter = collections.Counter()
    by_loops: dict[int, list[int]] = collections.defaultdict(lambda: [0, 0])
    rec_cls = Recorder(model)
    with rec_cls as rec:
        for batch in batches:
            batch = batch.to(device)
            if batch.q_visit.shape[0] == 0:
                continue

            def score(name: str, **kw) -> list[bool]:
                answers = model.answer(batch, stop=stops, **kw)
                correct, _ = judge(answers, batch, tokenizer=tokenizer, stop=stops, eos=model.config.eos_id)
                acc[name][0] += sum(correct)
                acc[name][1] += len(correct)
                return correct, answers

            correct, answers = score("default")
            for ok, used in zip(correct, answers.loops.tolist()):
                loops_hist[used] += 1
                by_loops[used][0] += int(ok)
                by_loops[used][1] += 1
            for k in (1, 3, 5, 8):
                score(f"min_loops_{k}", min_loops=min(k, max_loops))
            for k in range(1, 5):
                score(f"stop_at_loop_{k}", max_loops=k)
            rec.record = True
            score("forced_8_loops", min_loops=max_loops)
            rec.record = False
            for lesion in ("registers_1plus", "registers_all", "question_reset"):
                rec.lesion = lesion
                score(f"lesion_{lesion}", min_loops=None)
                rec.lesion = None
    rate = lambda v: v[0] / v[1] if v[1] else None
    total = sum(loops_hist.values())
    return {
        "questions": acc["default"][1],
        "accuracy": {name: rate(v) for name, v in acc.items()},
        "accuracy_min_loops": {str(k): rate(acc[f"min_loops_{k}"]) for k in (1, 3, 5, 8)},
        "accuracy_stop_at_loop": {str(k): rate(acc[f"stop_at_loop_{k}"]) for k in range(1, 5)},
        "loops_histogram": {str(k): loops_hist[k] for k in sorted(loops_hist)},
        "loops_mean": sum(k * v for k, v in loops_hist.items()) / max(total, 1),
        "accuracy_by_loops_used": {str(k): {"n": v[1], "accuracy": rate(v)} for k, v in sorted(by_loops.items())},
        "state_change_per_loop": {name: {str(loop): (rec.change[(loop, name)][0] / rec.change[(loop, name)][1]
                                                     if rec.change[(loop, name)][1] else None)
                                         for loop in range(1, max_loops + 1)} for name in _groups(model)},
        "lesions": {"registers_1plus_zeroed": rate(acc["lesion_registers_1plus"]),
                    "registers_all_zeroed": rate(acc["lesion_registers_all"]),
                    "question_rows_reset_to_loop0": rate(acc["lesion_question_reset"]),
                    "no_lesion": rate(acc["default"])},
    }


def diag(a) -> int:
    saved = torch.load(a.ckpt, map_location="cpu", weights_only=False)
    model = PremonitionMini(mini_config_from(saved["config"]))
    model.load_state_dict(saved["model"])
    device = torch.device(a.device)
    model.to(device).eval()
    data = dtrain.open_data(Path(a.root), Path(a.tokenizer), workers=a.workers, log=lambda s: None)
    res: dict[str, Any] = {"arm": saved.get("arm"), "seed": saved.get("seed"), "steps": saved.get("steps"),
                           "max_visits": a.max_visits}
    for name, cache in (("validation", data.validation), ("dev", data.dev)):
        batches, stops = make_eval_batches(cache, a.max_visits, data.tokenizer)
        t0 = time.time()
        res[name] = diagnose(model, batches, data.tokenizer, stops)
        log(f"diag {name}: {res[name]['questions']} questions in {time.time() - t0:.0f}s")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1, default=float))
    log("DIAG written", a.out)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--arm", choices=sorted(ARMS), required=True)
    t.add_argument("--root", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--steps", type=int, required=True)
    t.add_argument("--seed", type=int, default=0)
    t.add_argument("--eval-visits", type=int, default=DEV_EVAL_VISITS, help="dev visits per periodic eval")
    t.add_argument("--final-visits", type=int, default=None, help="testing only: score only this many dev/validation visits at the end")
    t.add_argument("--ckpt-every", type=int, default=None, help="testing only")
    t.add_argument("--eval-every", type=int, default=None, help="testing only")
    t.add_argument("--stop-after", type=int, default=None, help="testing only: stop after this many steps (resume test)")
    d = sub.add_parser("diag")
    d.add_argument("--ckpt", required=True)
    d.add_argument("--root", required=True)
    d.add_argument("--out", required=True)
    d.add_argument("--max-visits", type=int, default=1000, help="visits per split (speed cap)")
    for p in (t, d):
        p.add_argument("--tokenizer", default=str(DEFAULT_TOKENIZER))
        p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
        p.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    return train(a) if a.cmd == "train" else diag(a)


if __name__ == "__main__":
    raise SystemExit(main())
