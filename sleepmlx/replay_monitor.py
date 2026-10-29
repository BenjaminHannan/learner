"""Independent retention monitor and isolated paired replay experiment.

Run only with already-cached local weights, for example:
python -m sleepmlx.replay_monitor --profile lfm3_cpu --model-dir /cached/model --output /tmp/replay-report.json

This short synthetic experiment neither promotes adapters nor establishes
real-world learning quality. Its questions are excluded from both replay arms
and are never used as training targets or to write teacher continuations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import tempfile
import threading
import time
from pathlib import Path

from . import gate
from . import grading
from . import replay

MONITOR_QA = [
    ("A tray holds 13 rows of 4 beads. How many beads are on the tray?", ["52", "fifty two", "fifty-two"]),
    ("A packet has 96 sheets. After removing 18 sheets, how many remain?", ["78", "seventy eight", "seventy-eight"]),
    ("A train leaves at 09:10 and arrives at 09:55. How many minutes is the journey?", ["45", "forty five", "forty-five"]),
    ("Which is heavier: one kilogram of cork or two kilograms of steel?", ["steel"]),
    ("Complete the sequence with one number: 2, 5, 8, 11, __.", ["14", "fourteen"]),
    ("The word 'lantern' starts with which letter?", ["l"]),
    ("In the list teal, copper, violet, which word appears second?", ["copper"]),
    ("A note reads: 'The meeting room is Juniper.' What is the meeting room called?", ["juniper"]),
    ("If every glint is a pebble and every pebble is solid, is every glint solid?", ["yes"]),
    ("A rectangle measures 7 cm by 3 cm. What is its area in square centimetres?", ["21", "twenty one", "twenty-one"]),
    ("Which punctuation mark usually ends a direct question?", ["question mark", "question marks"]),
    ("A book is placed above a cup. Is the cup above or below the book?", ["below"]),
]

# Fictional training and differently worded learning probes, separate from the
# monitor and public replay list. These are harness data, never real user notes.
LEARNING = [
    ("What is the fictional Lumen observatory's access word?", "Cedar", "Name the access word assigned to the Lumen observatory."),
    ("What is the fictional Vela ferry's home dock?", "Mossbank", "Name the home dock assigned to the Vela ferry."),
    ("What is the fictional Thistle robot's call sign?", "Amberfin", "Name the call sign assigned to the Thistle robot."),
    ("What is the fictional Pelican archive's room name?", "Silverleaf", "Name the room assigned to the Pelican archive."),
]


MONITOR_REVISION = "retention-monitor-2"
SYMBOL_ALIASES = {"Which punctuation mark usually ends a direct question?": ("?",)}
MONITOR_ID = hashlib.sha256(json.dumps({"revision": MONITOR_REVISION, "questions": MONITOR_QA, "symbols": SYMBOL_ALIASES}, sort_keys=True).encode()).hexdigest()


def measure(backend, renderer, max_tokens=32):
    prompts = [renderer.render(gate.GATE_SYS, q) for q, _ in MONITOR_QA]
    answers = []
    for start in range(0, len(prompts), max(1, backend.gen_batch)):
        answers.extend(backend.generate(prompts[start:start + max(1, backend.gen_batch)], max_tokens, temp=0.0, adapter=True))
    if len(answers) != len(prompts):
        raise ValueError("incomplete independent replay monitor")
    flags = [gate.correct(answer, accepted, q, literal_symbols=SYMBOL_ALIASES.get(q, ())) for answer, (q, accepted) in zip(answers, MONITOR_QA)]
    return {**grading.binding(), "monitor_revision": MONITOR_REVISION, "monitor_identity": MONITOR_ID, "n": len(flags), "hits": sum(flags), "flags": flags,
            "samples": [{"q": q, "out": a} for (q, _), a in zip(MONITOR_QA, answers)]}


def paired_experiment(backend, renderer, root, *, steps=12, lr=2e-4, seed=0, max_seq_len=640,
                      replay_max_tokens=128, monitor_tokens=32):
    """Two short arms from identical adapter tensors and fresh optimizers.

    Fixed exploratory pass marks: no previously correct monitor answer lost,
    and at least one held-out synthetic fact gained. Passing is necessary to
    consider a larger experiment, not authorization to enable or promote.
    """
    from .recipe import GENERIC_PROMPTS
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    initial = root / "initial-adapter"
    backend.save_adapter(initial)
    baseline = measure(backend, renderer, monitor_tokens)
    held = [{"q": q, "a": a} for _, a, q in LEARNING]
    pre = gate.score_recall(backend, renderer, held, max_tokens=monitor_tokens)
    training = []
    for q, a, _ in LEARNING:
        p = backend.encode(renderer.render("Answer with just the name.", q))
        target = backend.encode(renderer.p.training_answer_prefix + a) + [backend.stop_id]
        if not p or len(p) + len(target) > max_seq_len:
            raise ValueError("synthetic training example exceeds context bound")
        training.append((p + target, len(p)))
    blocked = [q for q, _ in gate.GENERAL_QA + MONITOR_QA] + [h["q"] for h in held]
    questions = replay.public_questions(GENERIC_PROMPTS, blocked)
    report = {"experiment": "paired-replay-synthetic-1", "quality_claim": False,
              "identity": replay.reference_identity(backend, renderer),
              "config": {"steps": steps, "lr": lr, "seed": seed, "max_seq_len": max_seq_len,
                         "replay_max_tokens": replay_max_tokens, "monitor_tokens": monitor_tokens,
                         "seed_scope": "replay sampling; callers control adapter initialization"},
              "initial_adapter_files": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                        for path in initial.iterdir() if path.is_file()},
              "pass_marks": {"previously_correct_monitor_losses_max": 0, "held_out_learning_gain_min": 1},
              "monitor_before": baseline, "learning_before": pre, "arms": {}}
    try:
        for mode in ("prompt", "continuation"):
            backend.load_adapter(initial)
            if mode == "prompt":
                contexts = replay.prompt_examples(backend, [renderer.render("Answer with just the name.", q) for q in questions], max_seq_len)
                stats = {"mode": mode, "examples": len(contexts)}
            else:
                contexts, stats = replay.continuation_examples(backend, renderer, questions, root / "replay-cache.json",
                                                              max_tokens=replay_max_tokens, max_seq_len=max_seq_len)
            rng = random.Random(seed)
            backend.train_begin(steps, lr)
            losses = []
            for i in range(steps):
                rb = rng.sample(contexts, min(4, len(contexts)))
                losses.append(backend.train_step(training, rb, i))
            monitor = measure(backend, renderer, monitor_tokens)
            learning = gate.score_recall(backend, renderer, held, max_tokens=monitor_tokens)
            lost = sum(b and not a for b, a in zip(baseline["flags"], monitor["flags"]))
            gain = learning["hits"] - pre["hits"]
            report["arms"][mode] = {"replay": stats, "monitor_after": monitor, "learning_after": learning,
                                    "previously_correct_monitor_losses": lost, "learning_gain": gain,
                                    "exploratory_pass": lost == 0 and gain >= 1, "last_loss": losses[-1] if losses else None}
        return report
    finally:
        backend.load_adapter(initial)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=12)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-seq-len", type=int, default=640)
    parser.add_argument("--replay-max-tokens", type=int, default=128)
    parser.add_argument("--gen-batch", type=int, default=1)
    parser.add_argument("--tok-budget", type=int, default=256)
    parser.add_argument("--mps-mem-gb", type=float, default=8.0)
    parser.add_argument("--budget-seconds", type=float, default=300.0)
    args = parser.parse_args()
    if (not args.model_dir.expanduser().is_dir() or args.steps < 1 or args.gen_batch < 1
            or args.tok_budget < 1 or args.mps_mem_gb <= 0 or args.budget_seconds <= 0):
        parser.error("cached local model directory and positive step count are required")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="premonition-replay-experiment-") as tmp:
        root = Path(tmp)
        for key, leaf in {"SLEEPMLX_HOME": "sleepmlx", "SLEEPMLX_DIARY_DIR": "diary", "SLEEPMLX_USERDATA": "userdata",
                          "LEARNER_OPS": "ops", "SLEEPMODE_HOME": "sleepmode", "SLEEPMODE_OPS": "mode-ops",
                          "SLEEPMODE_OUT": "mode-out", "HF_HOME": "hf", "HF_MODULES_CACHE": "hf-modules"}.items():
            os.environ[key] = str(root / leaf)
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["SLEEPMLX_MPS_MEM_GB"] = str(args.mps_mem_gb)
        from .backend import Clock, Guards
        from .profile import Renderer, load_profile
        from .worker import choose_backend, make_backend
        prof = load_profile(args.profile, env={"SLEEPMLX_MODEL_DIR": str(args.model_dir.expanduser().resolve())})
        random.seed(args.seed)
        if choose_backend(prof) == "torch":
            import torch
            torch.manual_seed(args.seed)
        else:
            import mlx.core as mx
            mx.random.seed(args.seed)
        backend = None
        stop_sampling = threading.Event()
        peaks = {"sampled_mps_allocated_gb": 0.0, "sampled_mps_driver_gb": 0.0, "sampled_process_rss_gb": 0.0,
                 "sampling_interval_s": 0.1, "measurement": "sampled maxima, not an allocator high-water mark"}
        def sample():
            import psutil
            process = psutil.Process()
            while not stop_sampling.is_set():
                peaks["sampled_process_rss_gb"] = max(peaks["sampled_process_rss_gb"], process.memory_info().rss / 1e9)
                if backend is not None and getattr(backend, "device", None) == "mps":
                    peaks["sampled_mps_allocated_gb"] = max(peaks["sampled_mps_allocated_gb"], backend.torch.mps.current_allocated_memory() / 1e9)
                    peaks["sampled_mps_driver_gb"] = max(peaks["sampled_mps_driver_gb"], backend.torch.mps.driver_allocated_memory() / 1e9)
                stop_sampling.wait(0.1)
        sampling = threading.Thread(target=sample, daemon=True)
        sampling.start()
        try:
            backend, tok = make_backend(prof, env={"SLEEPMLX_GEN_BATCH": str(args.gen_batch), "SLEEPMLX_TOK_BUDGET": str(args.tok_budget)})
            clock = Clock(args.budget_seconds, Guards(poll_s=2, hot_polls=2), reserve_s=0)
            original_generate, original_step = backend.generate, backend.train_step
            def generate(*values, **options):
                clock.check()
                return original_generate(*values, **options)
            def train_step(*values, **options):
                clock.check()
                return original_step(*values, **options)
            backend.generate, backend.train_step = generate, train_step
            report = paired_experiment(backend, Renderer(prof, tok), tmp, steps=args.steps, seed=args.seed,
                                       max_seq_len=args.max_seq_len, replay_max_tokens=args.replay_max_tokens)
            report["runtime"] = dict(peaks, elapsed_s=time.monotonic() - started, gen_batch=args.gen_batch,
                                     tok_budget=args.tok_budget, mps_mem_gb=args.mps_mem_gb, initialization_seed=args.seed)
            from .paths import write_json
            write_json(args.output.expanduser().resolve(), report)
            print(json.dumps({"output": str(args.output), "quality_claim": False, "runtime": report["runtime"],
                              "arms": {key: {field: value[field] for field in ("previously_correct_monitor_losses", "learning_gain", "exploratory_pass")}
                                       for key, value in report["arms"].items()}}, indent=2))
        finally:
            stop_sampling.set()
            sampling.join(timeout=2)
            if backend is not None:
                backend.close()


if __name__ == "__main__":
    main()
