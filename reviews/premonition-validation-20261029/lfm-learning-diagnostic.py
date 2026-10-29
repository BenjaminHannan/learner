"""Isolated, opt-in LFM diagnostic; no model is loaded without --allow-model-load.

Run from the repository root after resource coordination:
  python reviews/premonition-validation-20261029/lfm-learning-diagnostic.py \
    --allow-model-load --model-dir /cached/LFM3 --output /tmp/lfm-diagnostic.json

Only total steps changes relative to the prompt arm of the existing 12-step
fixture. Its cosine schedule is consequently stretched; checkpoints are
diagnostics, not opportunities to choose an endpoint using held-out scores.
The budget is checked between operations; an outer process watchdog should
enforce a strict wall-clock limit if required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


def examples(backend, renderer, rows):
    out = []
    for q, answer in rows:
        prompt = backend.encode(renderer.render("Answer with just the name.", q))
        target = backend.encode(renderer.p.training_answer_prefix + answer) + [backend.stop_id]
        out.append((prompt + target, len(prompt)))
    return out


def teacher_forced(backend, rows, encoded):
    """Observe logits without gradients, optimizer calls, or target adaptation."""
    t = backend.torch
    backend.model.eval()
    results = []
    with t.no_grad():
        for (question, answer), example in zip(rows, encoded):
            ids, attention, batch_index, time_index, target = backend._arrays([example])
            logits = backend._logits(ids, attention, batch_index, time_index)
            log_probs = t.log_softmax(logits, dim=-1)
            chosen = log_probs.gather(1, target[:, None]).squeeze(1)
            first_id = int(logits[0].argmax().item())
            first_lp = float(chosen[0].item())
            results.append({"q": question, "a": answer, "answer_only_nll": float(-chosen[:-1].mean().item()),
                            "answer_plus_stop_nll": float(-chosen.mean().item()),
                            "first_answer_token_probability": math.exp(first_lp),
                            "expected_first_token_id": int(target[0].item()), "greedy_first_token_id": first_id,
                            "greedy_first_token": backend.tok.decode([first_id]),
                            "target_token_ids": target.tolist()})
    return results


def generated(backend, renderer, rows, max_tokens):
    from sleepmlx import gate
    result = []
    for q, answer in rows:
        text = backend.generate([renderer.render("Answer with just the name.", q)], max_tokens,
                                temp=0.0, adapter=True)[0]
        result.append({"q": q, "a": answer, "out": text, "hit": gate.recall_hit(answer, text)})
    return {"n": len(result), "hits": sum(row["hit"] for row in result), "samples": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-model-load", action="store_true")
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", choices=("lfm3_mps", "lfm3_cpu"), default="lfm3_mps")
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--budget-seconds", type=float, default=300)
    parser.add_argument("--mps-mem-gb", type=float, default=8)
    parser.add_argument("--replay-mode", choices=("prompt", "continuation"), default="prompt")
    parser.add_argument("--expected-adapter-sha256")
    parser.add_argument("--expected-replay-cache", type=Path)
    args = parser.parse_args()
    if not args.allow_model_load:
        parser.error("--allow-model-load requires prior resource coordination")
    if args.steps < 1 or args.budget_seconds <= 0 or not args.model_dir.expanduser().is_dir():
        parser.error("positive step/budget values and a cached model directory are required")
    if args.replay_mode == "continuation" and not args.expected_adapter_sha256:
        parser.error("the paired continuation run requires --expected-adapter-sha256")
    output = args.output.expanduser().resolve()
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="premonition-learning-diagnostic-") as tmp:
        root = Path(tmp)
        for key, leaf in {"SLEEPMLX_HOME": "sleepmlx", "SLEEPMLX_DIARY_DIR": "diary", "SLEEPMLX_USERDATA": "userdata",
                          "LEARNER_OPS": "ops", "SLEEPMODE_HOME": "sleepmode", "SLEEPMODE_OPS": "mode-ops",
                          "SLEEPMODE_OUT": "mode-out", "HF_HOME": "hf", "HF_MODULES_CACHE": "hf-modules"}.items():
            os.environ[key] = str(root / leaf)
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["SLEEPMLX_MPS_MEM_GB"] = str(args.mps_mem_gb)
        import torch
        from sleepmlx import gate, replay
        from sleepmlx.backend import Clock, Guards, Stop
        from sleepmlx.paths import write_json
        from sleepmlx.profile import Renderer, load_profile
        from sleepmlx.recipe import GENERIC_PROMPTS
        from sleepmlx.replay_monitor import LEARNING, MONITOR_QA, measure
        from sleepmlx.worker import make_backend
        random.seed(args.seed)
        torch.manual_seed(args.seed)
        profile = load_profile(args.profile, {"SLEEPMLX_MODEL_DIR": str(args.model_dir.expanduser().resolve())})
        backend = None
        report = {"experiment": "lfm-training-versus-transfer-1", "quality_claim": False, "partial": True,
                  "config": {"steps": args.steps, "seed": args.seed, "lr": 2e-4, "replay_mode": args.replay_mode,
                             "gen_batch": 1, "tok_budget": 256, "generation_tokens": 32,
                             "replay_max_tokens": 32,
                             "max_seq_len": 256,
                             "budget_seconds": args.budget_seconds, "mps_mem_gb": args.mps_mem_gb},
                  "fixed_pass_marks": {"held_out_gain_min": 2, "previously_correct_monitor_losses_max": 0,
                                       "training_mean_answer_NLL_relative_drop_diagnostic_min": 0.25,
                                       "first_token_probability_increases_diagnostic_min": 3},
                  "primary_endpoint": args.steps, "checkpoints": []}
        try:
            backend, tok = make_backend(profile, {"SLEEPMLX_GEN_BATCH": "1", "SLEEPMLX_TOK_BUDGET": "256"})
            renderer = Renderer(profile, tok)
            clock = Clock(args.budget_seconds - (time.monotonic() - started), Guards(poll_s=2), reserve_s=0)
            train_rows = [(q, a) for q, a, _ in LEARNING]
            held_rows = [(q, a) for _, a, q in LEARNING]
            train_examples = examples(backend, renderer, train_rows)
            held_examples = examples(backend, renderer, held_rows)
            blocked = [q for q, _ in gate.GENERAL_QA + MONITOR_QA] + [q for q, _ in held_rows]
            public = replay.public_questions(GENERIC_PROMPTS, blocked)
            report["identity"] = replay.reference_identity(backend, renderer)
            initial = root / "initial-adapter"
            backend.save_adapter(initial)
            report["initial_adapter_files"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in initial.iterdir() if p.is_file()}
            if args.expected_adapter_sha256:
                actual = report["initial_adapter_files"].get("adapter_model.safetensors")
                if actual != args.expected_adapter_sha256:
                    raise ValueError("initial adapter tensor SHA differs from paired control: " + str(actual))
                report["paired_initial_adapter_sha256_asserted"] = actual
            original_generate, original_step = backend.generate, backend.train_step
            def generate(*values, **kwargs):
                clock.check()
                return original_generate(*values, **kwargs)
            def step(*values, **kwargs):
                clock.check()
                return original_step(*values, **kwargs)
            backend.generate, backend.train_step = generate, step
            if args.replay_mode == "prompt":
                contexts = replay.prompt_examples(backend, [renderer.render("Answer with just the name.", q) for q in public], 256)
                report["replay"] = {"mode": "prompt", "examples": len(contexts)}
            else:
                contexts, report["replay"] = replay.continuation_examples(
                    backend, renderer, public, root / "replay-cache.json", max_tokens=32, max_seq_len=256,
                    before_generate=lambda _: clock.check())
                if args.expected_replay_cache:
                    fixture = args.expected_replay_cache.read_bytes()
                    if json.loads((root / "replay-cache.json").read_text()) != json.loads(fixture):
                        raise ValueError("regenerated teacher records differ from the frozen continuation fixture")
                    report["regenerated_teacher_fixture_match"] = True
                    report["teacher_fixture_file_sha256"] = hashlib.sha256(fixture).hexdigest()
            def checkpoint(number):
                clock.check()
                entry = {"step": number, "training_teacher_forced": teacher_forced(backend, train_rows, train_examples),
                         "held_out_teacher_forced": teacher_forced(backend, held_rows, held_examples),
                         "training_generation": generated(backend, renderer, train_rows, 32),
                         "held_out_generation": generated(backend, renderer, held_rows, 32),
                         "monitor": measure(backend, renderer, 32), "elapsed_s": time.monotonic() - started}
                report["checkpoints"].append(entry)
                write_json(output, report)
            checkpoint(0)
            rng = random.Random(args.seed)
            backend.train_begin(args.steps, 2e-4)
            report["losses"] = []
            for i in range(args.steps):
                report["losses"].append(backend.train_step(train_examples, rng.sample(contexts, min(4, len(contexts))), i))
                if i + 1 in {12, 32, args.steps}:
                    checkpoint(i + 1)
            before, after = report["checkpoints"][0], report["checkpoints"][-1]
            gain = after["held_out_generation"]["hits"] - before["held_out_generation"]["hits"]
            lost = sum(b and not a for b, a in zip(before["monitor"]["flags"], after["monitor"]["flags"]))
            nll_before = sum(x["answer_only_nll"] for x in before["training_teacher_forced"]) / len(train_rows)
            nll_after = sum(x["answer_only_nll"] for x in after["training_teacher_forced"]) / len(train_rows)
            first_improved = sum(a["first_answer_token_probability"] > b["first_answer_token_probability"]
                                 for b, a in zip(before["training_teacher_forced"], after["training_teacher_forced"]))
            report.update(partial=False, outcome={"held_out_gain": gain, "previously_correct_monitor_losses": lost,
                                                  "learning_retention_pass": gain >= 2 and lost == 0,
                                                  "training_mean_answer_NLL_relative_drop": 1 - nll_after / nll_before,
                                                  "first_token_probability_increases": first_improved})
        except Stop as error:
            report["stop_reason"] = error.reason
        except Exception as error:
            report["error"] = type(error).__name__ + ": " + str(error)
            raise
        finally:
            report["elapsed_s"] = time.monotonic() - started
            write_json(output, report)
            if backend is not None:
                backend.close()


if __name__ == "__main__":
    main()
