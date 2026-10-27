"""Fast CPU contracts for the A3-teacher-delay-v2 launcher (design/v3/12-teacher-delay-contract.md).

Covers: the frozen plan schema and seed registration, the FLOP-share curriculum clock against the
historical curriculum at B_ref, model/init/stream parity between the two arms and against the
historical trainer, passive telemetry, the completion predicate, the refusals, and that the saved
checkpoint still loads through the existing pair-suite loader.

No GPU, no network, no test split, no real training wave: every fixture is at most a handful of
optimizer updates on the CPU.

    PY -B tests/test_premonition_teacher_delay.py
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_teacher_delay as TD  # noqa: E402

CHECKS = 0


def check(label, cond):
    global CHECKS
    assert bool(cond), label
    CHECKS += 1
    print("PASS " + label, flush=True)


def refuses(label, call):
    try:
        call()
    except SystemExit:
        check(label, True)
        return
    check(label, False)


def main() -> int:
    started = time.perf_counter()
    TD.ensure_bootstrap()
    import torch
    torch.set_num_threads(2)
    from premonition.train import Curriculum, MiniTrainer, mini_train_config
    import premonition_first_card_probe as P

    tmp = tempfile.TemporaryDirectory(prefix="teacher-delay-test-")
    work = Path(tmp.name)

    # ------------------------------------------------------------------ 1. plan schema and seeds
    plan_dir = work / "plan"
    check("plan returns 0 and launches nothing", TD.main(["plan", "--out", str(plan_dir)]) == 0)
    plan = json.loads((plan_dir / "plan.json").read_text())
    check("plan.json top-level schema is exactly the registered fields",
          sorted(plan) == sorted(["experiment_id", "B", "B_ref", "gold_until", "ramp_width",
                                  "p_own_max", "max_updates", "max_seconds", "flop_tolerance",
                                  "pairs"]))
    check("plan header carries the frozen literals",
          plan["experiment_id"] == "A3-teacher-delay-v2"
          and plan["B"] == 34062815112683.242 and plan["B_ref"] == 68125630225366.484
          and plan["B"] == plan["B_ref"] / 2 and plan["gold_until"] == 0.2
          and plan["ramp_width"] == 0.1668 and plan["p_own_max"] == 0.75
          and plan["max_updates"] == 20000 and plan["max_seconds"] == 1200
          and plan["flop_tolerance"] == 0.05)
    check("plan registers 48 pairs", len(plan["pairs"]) == 48
          and [p["pair_id"] for p in plan["pairs"]] == list(range(48)))
    jobs = [job for pair in plan["pairs"] for job in pair["jobs"].values()]
    ids = [job["job_id"] for job in jobs]
    check("96 unique job ids, one control and one delayed per pair",
          len(ids) == 96 and len(set(ids)) == 96
          and all(sorted(pair["jobs"]) == ["control", "delayed"] for pair in plan["pairs"])
          and ids[:2] == ["p000-control", "p000-delayed"] and ids[-1] == "p047-delayed")

    seeds = [pair[k] for pair in plan["pairs"] for k in ("init_seed", "data_seed", "eval_seed")]
    check("144 distinct seeds, all in [10_000, 2**31-1], none colliding with historical 0..39",
          len(seeds) == 144 and len(set(seeds)) == 144
          and all(isinstance(s, int) and 10_000 <= s <= 2 ** 31 - 1 for s in seeds)
          and not set(seeds) & set(range(40)))

    def independent_seed(i, purpose):
        text = "v3|TrackA|A3-teacher-delay-v2|replication={}|{}".format(i, purpose)
        return 10_000 + int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2 ** 31 - 1 - 10_000 + 1)

    check("seeds are the SHA-256 of the registered seed string (recomputed independently)",
          all(pair[f"{p}_seed"] == independent_seed(pair["pair_id"], p)
              for pair in plan["pairs"] for p in ("init", "data", "eval")))
    check("the plan is deterministic", TD.make_plan(48) == plan)

    control = [pair["jobs"]["control"] for pair in plan["pairs"]]
    delayed = [pair["jobs"]["delayed"] for pair in plan["pairs"]]
    check("ramp_until == teacher_until + 0.1668 for both arms (and equals the contract literals)",
          all(job["ramp_until"] == TD.ramp_end(job["teacher_until"])
              and abs(job["ramp_until"] - (job["teacher_until"] + 0.1668)) <= 1e-12
              for job in jobs)
          and all(c["teacher_until"] == 0.3666 and c["ramp_until"] == 0.5334 for c in control)
          and all(d["teacher_until"] == 0.6 and d["ramp_until"] == 0.7668 for d in delayed))
    def only_teacher_differs(c, d):
        if sorted(c) != ["job_id", "ramp_until", "teacher_until"] or sorted(c) != sorted(d):
            return False
        if c["teacher_until"] == d["teacher_until"]:
            return False
        width_c = c["ramp_until"] - c["teacher_until"]
        width_d = d["ramp_until"] - d["teacher_until"]
        return abs(width_c - width_d) < 1e-12 and abs(width_c - 0.1668) < 1e-12

    check("teacher_until is the only independent difference between the arms",
          all(only_teacher_differs(c, d) for c, d in zip(control, delayed)))
    check("both arms of a pair share the initialization, data and evaluation seeds",
          all(set(pair) == {"pair_id", "init_seed", "data_seed", "eval_seed", "jobs"}
              for pair in plan["pairs"]))
    small = TD.make_plan(2)
    check("--pairs scales the roster without changing the frozen header",
          len(small["pairs"]) == 2
          and all(small[k] == plan[k] for k in plan if k != "pairs")
          and small["pairs"] == plan["pairs"][:2])
    check("plan does not create jobs/", not (plan_dir / "jobs").exists()
          and sorted(p.name for p in plan_dir.iterdir()) == ["plan.json", "plan_sources.json"])
    refuses("plan refuses an existing output directory",
            lambda: TD.main(["plan", "--out", str(plan_dir)]))

    # ------------------------------------------------------------------ 2. the curriculum clock
    B_ref, B = plan["B_ref"], plan["B"]
    hist = Curriculum(gold_until=0.10, teacher_until=0.1833, ramp_until=0.2667, p_own_max=0.75)
    ctrl = Curriculum(gold_until=0.20, teacher_until=0.3666, ramp_until=0.5334, p_own_max=0.75)
    late = Curriculum(gold_until=0.20, teacher_until=0.6, ramp_until=TD.ramp_end(0.6), p_own_max=0.75)
    check("doubling the historical fractions is exact in binary floats",
          0.1833 * 2 == 0.3666 and 0.2667 * 2 == 0.5334 and 0.10 * 2 == 0.20
          and (0.5334 - 0.3666) == 2 * (0.2667 - 0.1833) == 0.1668)

    flops, steps, mismatch, seen = 0.0, 0, 0, set()
    while flops / B <= 0.5334 and steps < 20000:
        a, b = hist.plan(flops / B_ref), ctrl.plan(flops / B)
        mismatch += (a.phase != b.phase) or (a.p_own != b.p_own)
        seen.add(a.phase)
        flops += (B / 4000.0) * (1.0 + (steps * 37 % 11) / 10.0)   # deterministic synthetic costs
        steps += 1
    check(f"historical clock at B_ref and v2 control at B_ref/2 agree on phase and p_own for all "
          f"{steps} synthetic updates through the control ramp",
          mismatch == 0 and steps > 1000 and seen == {"gold", "teacher", "own"})

    boundaries = []
    for share in (0.10, 0.1833, 0.2667):
        spent = share * B_ref
        for value in (spent * (1 - 1e-9), spent, spent * (1 + 1e-9)):
            a, b = hist.plan(value / B_ref), ctrl.plan(value / B)
            boundaries.append((a.phase == b.phase, a.p_own == b.p_own, a.phase))
    check("below / at / above every absolute boundary the two clocks give the same phase and p_own",
          all(same_phase and same_own for same_phase, same_own, _ in boundaries)
          and [row[2] for row in boundaries] == ["gold", "teacher", "teacher",
                                                 "teacher", "own", "own",
                                                 "own", "own", "own"])
    check("control phases: gold below .2B, teacher on [.2B, .3666B), own from .3666B, p_own=.75 at .5334B",
          ctrl.plan(0.1999).phase == "gold" and ctrl.plan(0.2).phase == "teacher"
          and ctrl.plan(0.36659).phase == "teacher" and ctrl.plan(0.3666).phase == "own"
          and ctrl.plan(0.3666).p_own == 0.0 and ctrl.plan(0.5334).p_own == 0.75
          and ctrl.plan(0.99).p_own == 0.75
          and abs(ctrl.plan(0.45).p_own - 0.75 * (0.45 - 0.3666) / 0.1668) < 1e-15)
    check("delayed arm: teacher until .6B, ramp to .7668B, max-own share .2332 vs control .4666",
          late.plan(0.5999).phase == "teacher" and late.plan(0.6).phase == "own"
          and late.plan(0.6).p_own == 0.0 and late.plan(late.ramp_until).p_own == 0.75
          and abs((1.0 - late.ramp_until) - 0.2332) < 1e-12
          and abs((1.0 - ctrl.ramp_until) - 0.4666) < 1e-12
          and abs((late.teacher_until - late.gold_until) / (ctrl.teacher_until - ctrl.gold_until)
                  - 2.40096) < 1e-4)
    check("both arms keep the gold phase and the ramp width identical",
          late.gold_until == ctrl.gold_until == 0.2
          and abs((late.ramp_until - late.teacher_until) - (ctrl.ramp_until - ctrl.teacher_until)) < 1e-12
          and late.p_own_max == ctrl.p_own_max == 0.75)

    # ------------------------------------------------------------------ 3. model / stream parity
    pair0 = plan["pairs"][0]
    init_seed, data_seed = pair0["init_seed"], pair0["data_seed"]
    model = TD.make_model(init_seed)
    base = TD.R.build("bypass-k1", init_seed, 0.2)
    check("the launcher's model has exactly 79,748 parameters",
          model.num_parameters() == 79748 == TD.PARAMETERS)
    check("state-dict keys are identical to R.build('bypass-k1', seed)",
          list(model.state_dict()) == list(base.state_dict()))
    check("initial tensors are bit-identical to the historical builder at the same seed",
          all(torch.equal(v, base.state_dict()[k]) for k, v in model.state_dict().items())
          and type(model).__name__ == type(base).__name__)
    check("a different init seed gives a different initial state",
          TD.state_sha256(model) != TD.state_sha256(TD.make_model(init_seed + 1)))

    control_init = TD.state_sha256(TD.make_model(init_seed))
    delayed_init = TD.state_sha256(TD.make_model(init_seed))
    stream_a, stream_b = TD.make_stream(data_seed), TD.make_stream(data_seed)
    first_a = [next(stream_a) for _ in range(2)]
    first_b = [next(stream_b) for _ in range(2)]
    other = [next(TD.make_stream(pair0["eval_seed"])) for _ in range(2)]
    check("both arms of a pair share init_state_sha256 and the first training batches",
          control_init == delayed_init == TD.state_sha256(base)
          and TD.batch_tokens_sha256(first_a) == TD.batch_tokens_sha256(first_b)
          and all(torch.equal(x.tokens, y.tokens) for x, y in zip(first_a, first_b)))
    check("a different data seed gives a different training stream",
          TD.batch_tokens_sha256(other) != TD.batch_tokens_sha256(first_a))

    def updates(teacher_until, ramp_until, *, historical=False, n=3):
        """n real CPU updates with the frozen recipe; returns (mean logged loss, weight digest)."""
        m = TD.make_model(init_seed)
        stream = TD.make_stream(data_seed)
        head = [next(stream) for _ in range(2)]
        if historical:                      # the unwrapped frozen trainer, same seed and stream
            curriculum = Curriculum(gold_until=0.2, teacher_until=teacher_until,
                                    ramp_until=ramp_until, p_own_max=0.75)
            trainer = MiniTrainer(m, mini_train_config(lr=1e-3, warmup_steps=100, log_every=50,
                                                       eval_every=0),
                                  "cpu", flop_budget=1.0, tolerance=0.05, seed=init_seed,
                                  curriculum=curriculum)
        else:
            trainer, _ = TD.make_trainer(m, init_seed, teacher_until, ramp_until, "cpu", 1.0)
        trainer.calibrate(head)
        trainer.flop_budget = B
        curve = []
        report = trainer.train(itertools.chain(head, stream), max_steps=n, max_seconds=120,
                               on_log=curve.append)
        return curve, report, P.fingerprint(m), trainer

    c_curve, c_report, c_state, c_trainer = updates(0.3666, 0.5334)
    d_curve, d_report, d_state, _ = updates(0.6, TD.ramp_end(0.6))
    h_curve, h_report, h_state, _ = updates(0.3666, 0.5334, historical=True)
    check("a 3-update CPU fixture is bit-identical between the control and delayed arms "
          "(they share the gold phase)",
          c_state == d_state and c_curve[-1]["loss"] == d_curve[-1]["loss"]
          and c_report["flops"] == d_report["flops"]
          and all(c_curve[-1][k] == d_curve[-1][k] for k in ("lm", "ask", "ans", "halt", "phase")))
    check("the same fixture is bit-identical to the direct historical-trainer fixture "
          "(passive telemetry consumes no RNG and adds no forward pass)",
          c_state == h_state and c_curve[-1]["loss"] == h_curve[-1]["loss"]
          and c_report["flops"] == h_report["flops"]
          and c_curve[-1]["phase"] == h_curve[-1]["phase"] == "gold")
    check("the telemetry recorded the first gold update passively",
          c_trainer.crossings["first_gold_update"]["update"] == 1
          and c_trainer.crossings["first_gold_update"]["flops_before"] == 0.0
          and "first_own_update" not in c_trainer.crossings)

    # ------------------------------------------------------------------ 4. completion predicate
    check("a max_steps stop is incomplete",
          TD.completion_status({"stop": "max_steps", "budget_ok": True}) == "incomplete")
    check("a max_seconds stop is incomplete",
          TD.completion_status({"stop": "max_seconds", "budget_ok": True}) == "incomplete")
    check("a stream-ended stop is incomplete",
          TD.completion_status({"stop": "stream ended", "budget_ok": True}) == "incomplete")
    check("a FLOP-budget stop with budget_ok False is incomplete",
          TD.completion_status({"stop": "flop budget", "budget_ok": False}) == "incomplete")
    check("a FLOP-budget stop with budget_ok True is complete",
          TD.completion_status({"stop": "flop budget", "budget_ok": True}) == "complete"
          and TD.completion_status({"stop": "flop budget (the next batch would pass the tolerance)",
                                    "budget_ok": True}) == "complete")

    # ------------------------------------------------------------------ 5. a real (incomplete) job
    job_dir = work / "run" / "jobs" / "p000-control"
    result = TD.train_job(out_dir=job_dir, job_id_="p000-control", pair_id=0, arm_name="control",
                          init_seed=init_seed, data_seed=data_seed, eval_seed=pair0["eval_seed"],
                          teacher_until=0.3666, ramp_until=0.5334, flop_budget=B, max_updates=3,
                          max_seconds=120, device="cpu")
    saved = json.loads((job_dir / "result.json").read_text())
    required = {"job_id", "pair_id", "arm", "status", "report", "curriculum", "phases", "curve",
                "parameters", "init_state_sha256", "first_batches_sha256", "seconds_train",
                "seconds_total", "device", "gpu_name", "torch_version", "source_sha256",
                "checkpoint_sha256"}
    check("result.json carries every required top-level key",
          required <= set(saved) and saved == json.loads(json.dumps(result, default=str)))
    check("an update-ceiling stop is recorded incomplete even though a checkpoint exists",
          saved["status"] == "incomplete" and saved["report"]["stop"] == "max_steps"
          and (job_dir / "model.pt").is_file()
          and json.loads((job_dir / "manifest.json").read_text())["status"] == "incomplete")
    check("the report keeps the budget accounting",
          {"stop", "budget_ok", "flops", "flop_budget", "steps"} <= set(saved["report"])
          and saved["report"]["flop_budget"] == B == saved["flop_budget"]
          and saved["report"]["steps"] == 3 and saved["parameters"] == 79748)
    check("the resolved curriculum and the arm identifiers are recorded",
          saved["curriculum"]["gold_until"] == 0.2 and saved["curriculum"]["teacher_until"] == 0.3666
          and saved["curriculum"]["ramp_until"] == 0.5334
          and saved["curriculum"]["p_own_max"] == 0.75 and saved["curriculum"]["early_ans"] == 0.2
          and saved["arm"] == "control" and saved["job_id"] == "p000-control"
          and saved["init_seed"] == init_seed and saved["data_seed"] == data_seed)
    check("phase accounting records the actual boundaries and per-phase FLOPs",
          set(saved["phases"]) >= {"first_teacher_update", "first_own_update",
                                   "first_p_own_max_update", "flops_in_phase"}
          and saved["phases"]["first_gold_update"]["update"] == 1
          and saved["phases"]["first_teacher_update"] is None
          and saved["phases"]["flops_in_phase"]["gold"] > 0)
    check("every 50-update log entry carries the full record",
          saved["curve"] and saved["log_every"] == 50
          and all({"step", "flops", "phase", "p_own", "gold_recall_at_4", "ans", "lm", "ask",
                   "halt", "loss"} <= set(entry) for entry in saved["curve"]))
    check("the digests and source closure are recorded",
          saved["init_state_sha256"] == control_init
          and saved["first_batches_sha256"] == TD.batch_tokens_sha256(first_a)
          and saved["checkpoint_sha256"] == TD.L.sha256(job_dir / "model.pt")
          and len(saved["source_sha256"]) >= 5
          and any(k.endswith("FROZEN.SHA256SUMS") for k in saved["source_sha256"]))

    loaded, blob = P.load_from("model", job_dir)
    check("the saved model.pt loads through the existing pair-suite loader unchanged",
          list(loaded.state_dict()) == list(base.state_dict())
          and all(torch.equal(v, blob["state_dict"][k]) for k, v in loaded.state_dict().items())
          and P.fingerprint(loaded) != saved["init_state_sha256"])
    check("the loaded checkpoint is the trained model in eval mode with the gpu_port blob fields",
          not loaded.training and loaded.num_parameters() == 79748
          and blob["arm"] == "bypass-k1" and blob["seed"] == init_seed
          and {"state_dict", "config", "arm", "identity", "seed", "model_class", "writer_class",
               "key_pool", "relation_shortcut", "ordered_evidence", "no_step_emb", "width",
               "lr_cooldown"} <= set(blob)
          and {"experiment_id", "job_id", "pair_id", "arm_name", "init_seed", "data_seed"} <= set(blob)
          and blob["experiment_id"] == "A3-teacher-delay-v2" and blob["arm_name"] == "control"
          and blob["key_pool"] is False and blob["relation_shortcut"] is False)

    refuses("train_job refuses an existing job directory",
            lambda: TD.train_job(out_dir=job_dir, job_id_="p000-control", pair_id=0,
                                 arm_name="control", init_seed=init_seed, data_seed=data_seed,
                                 teacher_until=0.3666, ramp_until=0.5334, max_updates=1))
    check("the refused repeat left the finished job untouched",
          json.loads((job_dir / "result.json").read_text()) == saved)

    def broken_stream(_seed):
        raise RuntimeError("synthetic stream failure")

    failed_dir = work / "failed" / "jobs" / "p001-delayed"
    original_stream, raised = TD.make_stream, False
    TD.make_stream = broken_stream
    try:
        TD.train_job(out_dir=failed_dir, job_id_="p001-delayed", pair_id=1, arm_name="delayed",
                     init_seed=init_seed, data_seed=data_seed, teacher_until=0.6,
                     ramp_until=TD.ramp_end(0.6), max_updates=1)
    except RuntimeError:
        raised = True
    finally:
        TD.make_stream = original_stream
    failed = json.loads((failed_dir / "result.json").read_text())
    check("a job that raises is recorded as failed and stays in the roster",
          raised and failed["status"] == "failed" and failed["job_id"] == "p001-delayed"
          and failed["arm"] == "delayed" and "synthetic stream failure" in failed["error"]
          and json.loads((failed_dir / "manifest.json").read_text())["status"] == "failed"
          and not (failed_dir / "model.pt").exists())

    # ------------------------------------------------------------------ 6. refusals
    refuses("run refuses an unknown job id",
            lambda: TD.main(["run", "--plan", str(plan_dir / "plan.json"), "--job", "p099-control",
                             "--out-root", str(work / "run2"), "--device", "cpu"]))
    refuses("run refuses an existing job output directory",
            lambda: TD.main(["run", "--plan", str(plan_dir / "plan.json"), "--job", "p000-control",
                             "--out-root", str(work / "run"), "--device", "cpu"]))
    check("run created nothing for the refused job ids",
          sorted(p.name for p in (work / "run" / "jobs").iterdir()) == ["p000-control"]
          and not (work / "run2").exists())

    edited = json.loads((plan_dir / "plan.json").read_text())
    edited["B"] = B / 10
    refuses("an edited budget is refused as a recipe override", lambda: TD.validate_plan(edited))
    edited = json.loads((plan_dir / "plan.json").read_text())
    edited["pairs"][0]["jobs"]["delayed"]["teacher_until"] = 0.45
    refuses("an edited arm schedule is refused", lambda: TD.validate_plan(edited))
    edited = json.loads((plan_dir / "plan.json").read_text())
    edited["experiment_id"] = "A3-teacher-delay-v1"
    refuses("a foreign experiment id is refused", lambda: TD.validate_plan(edited))
    for flag, value in (("--teacher-until", "0.5"), ("--ramp-until", "0.9"), ("--gold-until", "0.0"),
                        ("--flop-budget", "1e12"), ("--arm", "bypass-k4"), ("--steps", "10"),
                        ("--lr", "0.01"), ("--key-pool", None), ("--relation-shortcut", None)):
        argv = ["run", "--plan", str(plan_dir / "plan.json"), "--job", "p001-delayed",
                "--out-root", str(work / "run3"), "--device", "cpu", flag]
        if value is not None:
            argv.append(value)
        refuses(f"run rejects the recipe override {flag}", lambda a=argv: TD.main(a))
    check("no recipe override created an output directory", not (work / "run3").exists())

    # ------------------------------------------------------------------ 7. rehearsal
    refuses("rehearse refuses to write inside a plan's jobs/ directory",
            lambda: TD.main(["rehearse", "--out", str(work / "run" / "jobs" / "rehearsal"),
                             "--device", "cpu", "--updates", "1",
                             "--concurrency-note", "test"]))
    rehearsal_dir = work / "rehearsal"
    check("rehearse returns 0", TD.main(["rehearse", "--out", str(rehearsal_dir), "--device", "cpu",
                                         "--updates", "1", "--concurrency-note",
                                         "1 job, shared CPU, smoke only"]) == 0)
    rehearsal = json.loads((rehearsal_dir / "rehearsal.json").read_text())
    roster = {TD.derive_seed(i, p) for i in range(48) for p in ("init", "data", "eval")}
    check("the rehearsal stream is disjoint from the 48 learning pairs",
          rehearsal["data_seed"] not in roster and rehearsal["init_seed"] not in roster
          and rehearsal["data_seed"] == TD.derive_seed(0, "rehearsal"))
    check("the rehearsal reports counted FLOP/s for both schedules plus calibration and save times",
          set(rehearsal["measurements"]) == {"control_schedule", "own_forced"}
          and all(m["counted_flops_per_second"] > 0 and m["seconds_calibrate"] > 0
                  and m["seconds_checkpoint_save"] > 0 and m["flops"] > 0
                  for m in rehearsal["measurements"].values())
          and rehearsal["measurements"]["control_schedule"]["phases_seen"] == {"gold": 1}
          and rehearsal["measurements"]["own_forced"]["phases_seen"] == {"own": 1}
          and rehearsal["concurrency_note"] == "1 job, shared CPU, smoke only")
    check("the own-forced rehearsal is the expensive end of the schedule",
          rehearsal["measurements"]["own_forced"]["flops"]
          > rehearsal["measurements"]["control_schedule"]["flops"]
          and rehearsal["nominal_per_job_floor_counted_flops_per_second"] == B / 1200)
    refuses("rehearse refuses an existing output directory",
            lambda: TD.main(["rehearse", "--out", str(rehearsal_dir), "--device", "cpu",
                             "--updates", "1", "--concurrency-note", "test"]))

    tmp.cleanup()
    print(f"ALL {CHECKS} CHECKS PASSED in {time.perf_counter() - started:.1f} s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
