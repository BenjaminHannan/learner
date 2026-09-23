"""GPU port of the experiment-2 toy-ladder training run (additive; nothing existing is edited).

Trains exactly what `scripts/premonition_ovn_retrieval.py train` trains (same frozen snapshot, same data,
same curriculum and optimiser), but with a selectable device and a switch for CUDA bf16 autocast, so a GPU
run can be compared against the saved CPU run. Training happens on `--device`; the model is moved back to
the CPU and scored with the untouched `premonition_ovn_retrieval.evaluate` on the VALIDATION split only.

Writes only under artifacts/claude-gpuport-20260919/. It never touches the Opus ledgers.

    PY -B scripts/premonition_gpu_port.py --device cpu  --steps 50   --name smoke-cpu-50
    PY -B scripts/premonition_gpu_port.py --device cuda --autocast off --seed 0 --steps 1500

Runs under Python 3.10 (Windows) and 3.12 (macOS).
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from dataclasses import asdict
import itertools
import json
from pathlib import Path
import platform
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_ovn_ladder as L  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402

OUT = L.ROOT / "artifacts" / "claude-gpuport-20260919"


def _no_autocast(*_args, **_kwargs):
    """Stand-in for torch.autocast that does nothing (true fp32 on CUDA)."""
    return nullcontext()


def cooldown_factor(step: int, fraction: float, horizon: int) -> float:
    """Linear ramp 1.0 -> 0.1 over the final `fraction` of `horizon` steps, held at 0.1 after `horizon`.

    fraction <= 0 (or horizon <= 0) means no cooldown, i.e. a constant factor of 1.0.
    """
    if fraction <= 0.0 or horizon <= 0:
        return 1.0
    start = horizon * (1.0 - fraction)
    span = horizon - start
    if span <= 0:
        progress = 1.0
    else:
        progress = (step - start) / span
    progress = min(1.0, max(0.0, progress))
    return 1.0 - 0.9 * progress


def make_trainer_class(autocast_on: bool, lr_cooldown: float = 0.0, cooldown_steps: int = 0):
    """MiniTrainer subclass; with autocast off, torch.autocast is neutralised for the duration of one
    training step only (the frozen trainer hard-enables bf16 on CUDA and must not be edited).

    With `lr_cooldown > 0` the learning rate returned by `lr_at` is additionally multiplied by a linear
    ramp from 1.0 down to 0.1 over the final `lr_cooldown` fraction of `cooldown_steps` (the REQUESTED
    steps; the run ends on its FLOP budget a few dozen steps later and stays at 0.1 there). The frozen
    trainer is not edited: this is a subclass defined inside our own script.
    """
    from premonition.train import MiniTrainer

    base = MiniTrainer
    if not autocast_on:
        class Fp32MiniTrainer(MiniTrainer):
            def _train_step(self, *args, **kwargs):
                import torch
                real = torch.autocast
                torch.autocast = _no_autocast
                try:
                    return super()._train_step(*args, **kwargs)
                finally:
                    torch.autocast = real

        base = Fp32MiniTrainer

    if lr_cooldown <= 0.0:
        return base

    class CooldownTrainer(base):
        lr_cooldown_fraction = float(lr_cooldown)
        lr_cooldown_horizon = int(cooldown_steps)

        def lr_at(self, step: int) -> float:
            return super().lr_at(step) * cooldown_factor(
                step, self.lr_cooldown_fraction, self.lr_cooldown_horizon)

    return CooldownTrainer


def run(args) -> dict:
    import torch
    from premonition import answer_path
    from premonition.train import Curriculum, budget_for_steps, mini_train_config

    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("cuda requested but torch.cuda.is_available() is False")
    autocast_on = args.autocast == "on"
    name = args.name or "{}-{}-{}-s{}-{}".format(args.arm, args.device,
                                                 "bf16" if autocast_on else "fp32", args.seed, args.steps)
    started = time.perf_counter()
    out_dir = Path(args.out).expanduser() if args.out else OUT
    if args.key_pool and args.ordered_evidence:
        raise SystemExit("--key-pool does not compose with --ordered-evidence")
    if args.width:
        # Screen 7: model width (d_model; key_dim stays d_model / 2 as in both presets). Every builder below
        # goes through R.config_for, so this is the one place the size changes. Same lr, init rule and recipe.
        base_config_for = R.config_for
        R.config_for = lambda arm, early_ans=0.2: base_config_for(arm, early_ans).with_(
            d_model=args.width, key_dim=args.width // 2, check_band=False)
    if args.ordered_evidence:
        # Screen 2: ordered evidence supervision (additive subclass; same init, same state_dict).
        import premonition_ordered_evidence as O
        model = O.build(args.arm, args.seed, args.early_ans, ordered=True)
    elif args.relation_shortcut:
        # Screen 3: learned gated relation shortcut into the ASK query (additive subclass, 3 zero-init tensors).
        import premonition_relation_shortcut as RS
        model = RS.build(args.arm, args.seed, args.early_ans, shortcut=True)
    else:
        model = R.build(args.arm, args.seed, args.early_ans)
    if args.key_pool:
        # Screen 5: a separate softmax pooling scorer for the card KEYS, cloned from the value pool, so the
        # model starts as the baseline. Applied to the model built above, hence it composes with the
        # relation shortcut, and BEFORE the trainer (and its optimizer) is made, so key_pool is trained.
        import premonition_key_pool as KP
        KP.apply_key_pool(model)
    if args.no_step_emb:
        # Ablation: the learned loop-step embedding contributes nothing and is never trained.
        with torch.no_grad():
            model.think.step.weight.zero_()
        model.think.step.weight.requires_grad_(False)
    curriculum = Curriculum(gold_until=args.gold_until, teacher_until=args.teacher_until,
                            ramp_until=args.ramp_until)
    cls = make_trainer_class(autocast_on, args.lr_cooldown, args.steps)
    trainer = cls(model, mini_train_config(lr=args.lr, warmup_steps=args.warmup, log_every=50, eval_every=0),
                  args.device, flop_budget=1.0, seed=args.seed, curriculum=curriculum)
    stream = (item[0] for item in L.checked_train())
    head = [next(stream) for _ in range(2)]
    trainer.calibrate(head)
    trainer.flop_budget = budget_for_steps(trainer, head, args.steps)
    curve = []
    train_started = time.perf_counter()
    report = trainer.train(itertools.chain(head, stream), max_seconds=args.max_seconds,
                           on_log=lambda e: curve.append({k: e.get(k) for k in (
                               "step", "phase", "p_own", "lr", "loss", "lm", "ask", "ans", "halt",
                               "gold_recall_at_4", "answer_acc", "loops_per_question", "halt_rate")}))
    if args.device == "cuda":
        torch.cuda.synchronize()
    train_seconds = time.perf_counter() - train_started
    peak_bytes = torch.cuda.max_memory_allocated() if args.device == "cuda" else None
    reserved_bytes = torch.cuda.max_memory_reserved() if args.device == "cuda" else None

    model = model.to("cpu").float()
    for entry in curve[::max(1, len(curve) // 8)] + curve[-1:]:
        print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in entry.items()}), flush=True)
    validation = R.evaluate(model, L.load_split("validation"))

    ident = (answer_path.identity(answer_path.CARD_BYPASS, model.config) if R.ARMS[args.arm]["bypass"]
             else {"variant": model.config.variant, "purpose": "diagnostic"})
    ident = dict(ident, arm=args.arm, privilege="L_ask trained on oracle evidence lines (as D)",
                 note="GPU port; training device may differ from the reference CPU run")
    if args.relation_shortcut:
        ident = dict(ident, relation_shortcut=True,
                     privilege=ident["privilege"] + " + the question's VISIBLE relation token fed to a "
                               "learned gated shortcut in the ASK query (disclosed structural hint)")
    if args.ordered_evidence:
        ident = dict(ident, ordered_evidence=True,
                     privilege=ident["privilege"] + " + oracle hop ORDER (next reachable gold card only)")
    if args.key_pool:
        ident = dict(ident, key_pool=True,
                     note=ident["note"] + "; card KEYS use their own pooling scorer (writer.key_pool, "
                                          "cloned from writer.pool at init), values unchanged")
    (out_dir / "ckpt").mkdir(parents=True, exist_ok=True)
    (out_dir / "runs").mkdir(parents=True, exist_ok=True)
    path = out_dir / "ckpt" / (name + ".pt")
    torch.save({"state_dict": model.state_dict(), "config": asdict(model.config), "arm": args.arm,
                "identity": ident, "seed": args.seed, "no_step_emb": bool(args.no_step_emb),
                "ordered_evidence": bool(args.ordered_evidence),
                "relation_shortcut": bool(args.relation_shortcut),
                "key_pool": bool(args.key_pool),
                "width": int(args.width) or None,
                "model_class": type(model).__name__,
                "writer_class": type(model.writer).__name__ if model.writer is not None else None,
                "lr_cooldown": float(args.lr_cooldown)}, path)
    result = {
        "name": name, "arm": args.arm,
        "arm_settings": {k: list(v) if isinstance(v, tuple) else v for k, v in R.ARMS[args.arm].items()},
        "max_loops": R.MAX_LOOPS, "seed": args.seed, "steps_requested": args.steps,
        "device": args.device, "autocast": "bf16" if autocast_on else "off",
        "no_step_emb": bool(args.no_step_emb),
        "ordered_evidence": bool(args.ordered_evidence),
        "relation_shortcut": bool(args.relation_shortcut),
        "key_pool": bool(args.key_pool),
        "width": int(args.width) or None,
        "lr_cooldown": float(args.lr_cooldown),
        "trainer_class": cls.__name__,
        "model_class": type(model).__name__,
        "writer_class": type(model.writer).__name__ if model.writer is not None else None,
        "step_emb_absmax_after_training": float(model.think.step.weight.abs().max()),
        "curriculum": {"gold_until": args.gold_until, "teacher_until": args.teacher_until,
                       "ramp_until": args.ramp_until, "early_ans": args.early_ans},
        "torch_version": torch.__version__, "python": sys.version.split()[0], "platform": platform.platform(),
        "gpu_name": torch.cuda.get_device_name(0) if args.device == "cuda" else None,
        "peak_gpu_allocated_bytes": peak_bytes, "peak_gpu_reserved_bytes": reserved_bytes,
        "train_report": {k: v for k, v in report.items() if isinstance(v, (int, float, str, bool, type(None)))},
        "curve": curve, "validation": validation,
        "seconds_train": round(train_seconds, 2), "seconds_total": round(time.perf_counter() - started, 2),
        "identity": ident,
        "ckpt": str(path.relative_to(L.ROOT)) if L.ROOT in path.parents else str(path),
        "ckpt_sha256": L.sha256(path),
        "command": " ".join(sys.argv),
        "evaluated_on": "validation (CPU, premonition_ovn_retrieval.evaluate)",
    }
    (out_dir / "runs" / (name + ".json")).write_text(json.dumps(result, indent=1, default=str))
    R.show(validation)
    print("done {}: device {} autocast {} train {:.1f} s, total {:.1f} s".format(
        name, args.device, result["autocast"], train_seconds, result["seconds_total"]), flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=sorted(R.ARMS), default="bypass-k1")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--autocast", choices=("on", "off"), default="off",
                        help="on = the trainer's bf16 autocast on CUDA; off = true fp32")
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--warmup", type=int, default=100)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--max-seconds", type=float, default=None)
    parser.add_argument("--name")
    parser.add_argument("--gold-until", type=float, default=0.05)
    parser.add_argument("--early-ans", type=float, default=0.2)
    parser.add_argument("--teacher-until", type=float, default=0.30)
    parser.add_argument("--ramp-until", type=float, default=0.60)
    parser.add_argument("--no-step-emb", action="store_true",
                        help="zero the learned loop-step embedding and freeze it (ablation)")
    parser.add_argument("--ordered-evidence", action="store_true",
                        help="supervise ASK with the NEXT REACHABLE gold card only, in gold_lines order, "
                             "and have the teacher insert in that order (training only)")
    parser.add_argument("--relation-shortcut", action="store_true",
                        help="screen 3: add a learned gated shortcut from the question's visible relation "
                             "token embedding into the ASK query (zero-initialised, so init is the baseline)")
    parser.add_argument("--key-pool", action="store_true",
                        help="screen 5: give the card KEYS their own softmax pooling scorer "
                             "(writer.key_pool, cloned from writer.pool, so init is the baseline); the "
                             "VALUES keep the frozen pool. Composes with --relation-shortcut")
    parser.add_argument("--width", type=int, default=0,
                        help="screen 7: d_model (key_dim = d_model / 2); 0 = the frozen tiny preset (32 / 16)")
    parser.add_argument("--lr-cooldown", type=float, default=0.0,
                        help="linear LR ramp from 1.0x down to 0.1x over the final FRACTION of --steps "
                             "(0 = frozen behaviour: constant LR after warmup)")
    parser.add_argument("--out", default=None,
                        help="output directory (default artifacts/claude-gpuport-20260919)")
    parser.add_argument("--ladder6", action="store_true",
                        help="screen 4: train on the 6-relation ladder data "
                             "(artifacts/claude-ladder6-20260919/data) instead of the 3-relation default")
    args = parser.parse_args()
    L.bootstrap()
    if args.ladder6:
        import premonition_ladder6 as L6
        L6.activate()
        if args.out is None:
            args.out = str(L6.OUT)
    import torch
    torch.set_num_threads(args.threads)
    run(args)


if __name__ == "__main__":
    main()
