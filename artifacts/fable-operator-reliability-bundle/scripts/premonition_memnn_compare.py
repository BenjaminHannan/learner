"""Exposure-matched historical-reference screen; explicitly NOT equal-spent-FLOP admission.

Plan freezes seeds 0,1,2 before baseline outcomes. Train each answer-only MemNN on
the same frozen stream (seed 1101, 16 visits/update) for the corresponding historical
plain run's actual updates, with its FLOP budget as a ceiling. Re-evaluate both on
the identical existing six-cell development panel. A separate `budget-run` command
supports the full FLOP budget; time-censored jobs never count as compute complete.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import random
import sys
import time

import premonition_memnn as M
from premonition_memnn import torch

ROOT = M.ROOT
EXPERIMENT = "memnn-historical-reference-v1"
SEEDS = (0, 1, 2)
CONTROL = ROOT / "artifacts/claude-keypool-20260919/control"
PANEL = ROOT / "artifacts/claude-pairsuite-20260919/manifest.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    with Path(path).open("x") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def fingerprint(model):
    h = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        h.update(name.encode())
        h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def sources():
    files = [Path(__file__), Path(M.__file__),
             ROOT / "scripts/premonition_ovn_ladder.py",
             ROOT / "scripts/premonition_ovn_retrieval.py",
             ROOT / "scripts/premonition_pair_suite.py",
             ROOT / "scripts/premonition_handoff_diag.py",
             ROOT / "scripts/premonition_first_card_probe.py"]
    frozen = ROOT / "archive/opus-ovn-20260918-235851/frozen"
    files += list(frozen.rglob("*.py"))
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(files)}


def make_plan(out):
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for seed in SEEDS:
        record_path = CONTROL / f"runs/long-s{seed}-12000.json"
        record = json.loads(record_path.read_text())
        ckpt = CONTROL / f"ckpt/long-s{seed}-12000.pt"
        if sha(ckpt) != record["ckpt_sha256"]:
            raise RuntimeError("historical checkpoint does not match its recorded hash")
        rows.append({"seed": seed, "updates": record["train_report"]["steps"],
                     "flop_ceiling": record["train_report"]["flop_budget"],
                     "historical_flops": record["train_report"]["flops"],
                     "control_checkpoint": str(ckpt), "control_sha256": sha(ckpt),
                     "control_record": str(record_path), "control_record_sha256": sha(record_path)})
    plan = {"experiment": EXPERIMENT, "created_unix": time.time(), "jobs": rows,
            "purpose": "fixed-exposure screen at no greater counted compute, historical controls",
            "full_compute_comparison": False, "fresh_paired_reliability_comparison": False,
            "selection": "first three numerical seed IDs, no replacement or outcome-based extension",
            "data_seed": 1101, "visits_per_update": 16, "width": 177, "hops": 3,
            "parameters": 79473, "plain_parameters": 79748, "device": "cpu", "threads": 1,
            "optimizer": {"name": "AdamW", "lr": .001, "betas": [.9,.99], "eps": 1e-8,
                          "weight_decay": .1, "clip": 1., "warmup_updates": 100},
            "loss": "final answer-token CE only; no evidence/role/hop labels or teacher cards",
            "encoding": "full visible lines; published position encoding; independent A,C,B,W; shared H",
            "initialization": "embeddings/output N(0,.1), H identity, padding embeddings zero",
            "inference": "3 soft memory reads; full 68-token output argmax; deterministic EOS suffix",
            "diagnostic_inference": "same learned weights, 3 hard argmax reads; secondary only",
            "max_wave_seconds": 1800, "max_job_training_seconds": 1200,
            "panel_manifest": str(PANEL), "panel_manifest_sha256": sha(PANEL),
            "sources": sources(), "runtime": {"torch": torch.__version__, "python": sys.version,
                                               "platform": platform.platform()},
            "interpretation": "Six-cell answer thresholds only: soft reads are outside the original hard-read G_pair policy; no promotion/certificate.",
            "limitations": ["Historical controls, different training hardware/Torch versions",
                            "Common old development panel, not fresh certification",
                            "Answer-only soft MemNN vs LM/answer/evidence-supervised hard Premonition",
                            "Same update exposure and FLOP ceiling, substantially different actual compute",
                            "Soft reads access all eligible values; no equal discrete-read claim",
                            "Single-token answer classifier with fixed EOS, not a general decoder",
                            "Three fixed seeds do not estimate dependable run reliability"]}
    write_new(out / "plan.json", plan)
    return plan


def load_plan(out):
    plan = json.loads((out / "plan.json").read_text())
    if plan["sources"] != sources() or plan["panel_manifest_sha256"] != sha(PANEL):
        raise RuntimeError("source/panel identity changed since planning")
    return plan


def check_deadline(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError("comparison wall-clock cap reached")


def train_job(plan, job, out, deadline, *, full_budget=False):
    folder = out / (f"budget-seed-{job['seed']}" if full_budget else f"seed-{job['seed']}")
    folder.mkdir(exist_ok=False)
    torch.manual_seed(job["seed"])
    model = M.MemoryNetwork(width=plan["width"], hops=plan["hops"])
    initial = fingerprint(model)
    optimizer = M.optimizer_for(model)
    rng = random.Random(plan["data_seed"])
    started = time.monotonic()
    spent, step, history = 0, 0, []
    stop = "unstarted"
    # A budget job is a separate frozen run, never a continuation chosen by outcome.
    update_cap = 2_000_000 if full_budget else job["updates"]
    while step < update_cap:
        if time.monotonic() >= deadline or time.monotonic() - started >= plan["max_job_training_seconds"]:
            stop = "time_limit"
            break
        inputs, targets = M.training_batch(rng, plan["visits_per_update"])
        cost = M.training_flops(inputs, plan["width"], 68, plan["hops"])
        if spent + cost > job["flop_ceiling"]:
            stop = "flop_ceiling"
            break
        loss = M.training_step(model, optimizer, inputs, targets, step)
        spent += cost
        step += 1
        if step % 1000 == 0 or step == 1:
            row = {"seed": job["seed"], "step": step, "loss": loss,
                   "flops": spent, "seconds": time.monotonic() - started}
            history.append(row)
            print(json.dumps(row), flush=True)
    else:
        stop = "update_cap" if full_budget else "matched_exposure"
    exposure_complete = step == job["updates"] and not full_budget
    budget_complete = stop == "flop_ceiling" and .95 <= spent / job["flop_ceiling"] <= 1
    record = {"seed": job["seed"], "stop": stop, "updates": step,
              "expected_exposure_updates": job["updates"], "exposure_complete": exposure_complete,
              "compute_budget_complete": budget_complete, "counted_flops": spent,
              "flop_ceiling": job["flop_ceiling"], "flop_share": spent / job["flop_ceiling"],
              "training_seconds": time.monotonic()-started, "parameters": model.parameters_count(),
              "initial_fingerprint": initial, "trained_fingerprint": fingerprint(model),
              "curve": history, "training_worlds": step*16, "training_questions": step*64,
              "heldout_two_hop_training_questions": 0}
    torch.save({"state_dict": model.state_dict(), "width": plan["width"], "hops": plan["hops"],
                "seed": job["seed"], "plan_sha256": sha(out / "plan.json")}, folder / "model.pt")
    record["checkpoint_sha256"] = sha(folder / "model.pt")
    write_new(folder / "training.json", record)
    return model.eval(), record, folder


def score_predictions(a, answers_a, b=None, answers_b=None, invariant=False):
    good_a = [x == y for x,y in zip(a, answers_a)]
    if b is None:
        return [int(x) for x in good_a]
    return [int(ok and pred == target and (not invariant or first == pred))
            for ok, first, pred, target in zip(good_a, a, b, answers_b)]


@torch.no_grad()
def score_memnn(model, dataset, deadline, *, hard=False):
    import premonition_handoff_diag as H
    units, all_predictions = [], []
    for chunk in dataset["chunks"]:
        check_deadline(deadline)
        produced, answers = {}, {}
        for side in (("a","b") if dataset["kind"] == "pair" else ("a",)):
            inputs = M.from_batch(H._strip_labels(chunk[side]))
            pred = model(inputs, hard=hard).argmax(-1).tolist()
            produced[side] = [[p, 2] for p in pred]   # toy has exactly one answer token
            answers[side] = [m[f"answer_{side}"] for m in chunk["meta"]]
        units += score_predictions(produced["a"], answers["a"], produced.get("b"),
                                   answers.get("b"), dataset["invariant"])
        all_predictions.append(produced)
    assert len(units) == dataset["n"]
    return {"count": sum(units), "n": len(units), "per_unit": units,
            "prediction_sha256": hashlib.sha256(json.dumps(all_predictions).encode()).hexdigest()}


def load_panels():
    import premonition_pair_suite as PS
    manifest = PS.load_manifest()
    return {name: PS.load_set(name, manifest) for name in PS.CELLS}


def score_all(model, panels, deadline, *, memnn=True):
    import premonition_pair_suite as PS
    from premonition.toy_ladder import LadderSpec
    before = fingerprint(model)
    result, hard_result = {}, {}
    started = time.monotonic()
    for name, data in panels.items():
        check_deadline(deadline)
        cfg = PS.CELLS[name]
        if memnn:
            row = score_memnn(model, data, deadline)
            hard_result[name] = score_memnn(model, data, deadline, hard=True)
        else:
            row = PS.score_cell(model, data, LadderSpec())
        row.update(cutoff=cfg["cutoff"], passed=row["count"] >= cfg["cutoff"])
        result[name] = row
        print(json.dumps({"evaluation": "memnn" if memnn else "plain",
                          "cell": name, "count": row["count"], "n": row["n"]}), flush=True)
    if fingerprint(model) != before:
        raise RuntimeError("evaluation mutated model state")
    integrity = {"weights_unchanged": True, "fingerprint": before}
    if not memnn:
        integrity["native_parity"] = PS.own_fixed_parity(model, next(iter(panels.values())), LadderSpec())
        integrity["world_isolation"] = PS.world_isolation(model, next(iter(panels.values())), LadderSpec())
        if not integrity["native_parity"]["pass"] or not integrity["world_isolation"]["pass"]:
            raise RuntimeError("historical model evaluation integrity failed")
    return {"policy": "three_soft_reads" if memnn else "native_ASK_hard_top1_K4",
            "cells": result, "all_six_answer_thresholds": all(r["passed"] for r in result.values()),
            "fresh_panel": False, "official_G_pair_admission": False,
            "hard_argmax_secondary": hard_result if memnn else None,
            "integrity": integrity, "seconds": time.monotonic()-started}


def report(out, plan, records):
    rows = []
    for job, train, baseline, plain in records:
        for label, result in (("MemNN soft", baseline), ("Plain (saved)", plain)):
            cells = [f"{v['count']}/{v['n']}" for v in result["cells"].values()]
            rows.append(f"| {job['seed']} | {label} | " + " | ".join(cells)
                        + f" | {'yes' if result['all_six_answer_thresholds'] else 'no'} |")
    text = "# Memory-network comparison\n\n"
    text += "Exploratory historical-reference screen. Same training stream/update exposure and approximately 80k parameters; **not equal spent FLOPs**, not a fresh reliability trial. The soft model's answer thresholds are not official hard-retrieval G_pair admission.\n\n"
    text += "| Seed | Model | One hop | Practised two hop | Held-out two hop | Link pair | Endpoint pair | Irrelevant pair | All six |\n|---|---|---|---|---|---|---|---|---|\n"
    text += "\n".join(rows) + "\n\n"
    for job, train, baseline, plain in records:
        text += (f"Seed {job['seed']}: {train['updates']:,} updates; {train['counted_flops']:,} counted training FLOPs "
                 f"({100*train['flop_share']:.3f}% of the historical ceiling); "
                 f"{train['training_seconds']:.1f} training seconds. "
                 f"Exposure complete: {train['exposure_complete']}; full compute budget complete: {train['compute_budget_complete']}.\n\n")
    text += "The primary MemNN uses answer-only training, sentence position encoding and three soft reads. Plain retains its recorded reader/decoder, evidence supervision, teacher curriculum and native ASK/top-1 policy. Both are scored afresh on the same archived development worlds. Baseline hard-argmax results are secondary in each evaluation JSON. No seeds were replaced or selected by baseline outcomes.\n\n"
    text += "A baseline success would demonstrate this task can be solved by the older architecture within a smaller compute allowance. Failure here does not show failure at equal spent FLOPs or after other published training recipes. No causal hard-versus-soft claim, model promotion or general-intelligence conclusion follows from this three-seed screen.\n\n"
    text += "Sources: [End-to-End Memory Networks](https://arxiv.org/abs/1503.08895), [Key-Value Memory Networks](https://aclanthology.org/D16-1147/). Implementation follows the former's layer-wise tying variant; it does not use parsed KB keys/values.\n"
    with (out / "REPORT.md").open("x") as handle:
        handle.write(text)


def run_wave(out):
    plan = load_plan(out)
    M.bootstrap()
    torch.set_num_threads(plan["threads"])
    started = time.monotonic()
    deadline = started + plan["max_wave_seconds"]
    panels = load_panels()
    import premonition_first_card_probe as P
    records = []
    for job in plan["jobs"]:
        check_deadline(deadline)
        model, train, folder = train_job(plan, job, out, deadline)
        baseline = score_all(model, panels, deadline)
        write_new(folder / "baseline-evaluation.json", baseline)
        path = Path(job["control_checkpoint"])
        if sha(path) != job["control_sha256"]:
            raise RuntimeError("control changed since planning")
        plain, _ = P.load_from(path.stem, path.parent)
        control_eval = score_all(plain, panels, deadline, memnn=False)
        write_new(folder / "plain-evaluation.json", control_eval)
        records.append((job, train, baseline, control_eval))
    if plan["sources"] != sources() or sha(PANEL) != plan["panel_manifest_sha256"]:
        raise RuntimeError("source/panel changed during comparison")
    report(out, plan, records)
    write_new(out / "completion.json", {
        "exposure_screen_complete": all(r[1]["exposure_complete"] for r in records),
        "full_compute_comparison_complete": False,
        "seconds": time.monotonic()-started, "jobs": len(records), "paid_compute_cost": 0,
        "baseline_all_six": sum(r[2]["all_six_answer_thresholds"] for r in records),
        "plain_all_six": sum(r[3]["all_six_answer_thresholds"] for r in records),
        "plan_sha256": sha(out / "plan.json")})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run", "budget-run"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, choices=SEEDS)
    args = parser.parse_args()
    if args.command == "plan":
        plan = make_plan(args.out)
        print(json.dumps({"plan": str(args.out / "plan.json"), "seeds": list(SEEDS),
                          "parameters": plan["parameters"], "jobs": len(plan["jobs"])}), flush=True)
    elif args.command == "run":
        run_wave(args.out)
    else:
        if args.seed is None:
            parser.error("budget-run requires --seed")
        plan = load_plan(args.out)
        M.bootstrap()
        torch.set_num_threads(plan["threads"])
        job = next(j for j in plan["jobs"] if j["seed"] == args.seed)
        train_job(plan, job, args.out, time.monotonic()+plan["max_job_training_seconds"], full_budget=True)


if __name__ == "__main__":
    main()
