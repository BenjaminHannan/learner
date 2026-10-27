"""A3-teacher-delay-v2: plan/manifest and single-job launcher for the two frozen v2 schedules.

Implements the launcher row of design/v3/12-teacher-delay-contract.md ("Opus build list"). Nothing
existing is edited: the model, data, curriculum, trainer, optimiser and checkpoint blob format all come
from the hash-checked frozen snapshot through `premonition_ovn_retrieval` / `premonition_gpu_port`.

Both arms are the unchanged legacy `bypass-k1` model (79,748 parameters). The ONLY independent
difference between the arms is `teacher_until`; the ramp end is always `teacher_until + 0.1668`.
No wire, key pool, selectors, ST, early-search loss, frontier target or normalisation change is added,
and this experiment id accepts no curriculum/model overrides from the command line.

    PY -B scripts/premonition_teacher_delay.py plan --out artifacts/<new-dir>
    PY -B scripts/premonition_teacher_delay.py run --plan artifacts/<new-dir>/plan.json \
        --job p000-control --out-root artifacts/<new-dir> --device cuda
    PY -B scripts/premonition_teacher_delay.py rehearse --out artifacts/<new-dir>-rehearsal \
        --device cuda --updates 20 --concurrency-note "4 jobs per GPU"

`plan` never launches anything and never creates `jobs/`. `run` trains exactly one job, uses the plan's
explicit FLOP budget literally, and only reports "complete" for a FLOP-budget stop with `budget_ok`
true -- an update or time stop is "incomplete" even though a checkpoint was written.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import platform
import random
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_ovn_ladder as L  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402
import premonition_gpu_port as G  # noqa: E402

# ----------------------------------------------------------------------------- frozen contract
EXPERIMENT_ID = "A3-teacher-delay-v2"
B_REF = 68125630225366.484                 # median historical plain-control train_report.flop_budget
B = 34062815112683.242                     # = B_REF / 2, frozen numeric literal (never recomputed)
GOLD_UNTIL = 0.2
RAMP_WIDTH = 0.1668
P_OWN_MAX = 0.75
MAX_UPDATES = 20000                        # safety ceiling only; reaching it is INCOMPLETE
MAX_SECONDS = 1200                         # training cap per job; reaching it is INCOMPLETE
FLOP_TOLERANCE = 0.05
TEACHER_UNTIL = {"control": 0.3666, "delayed": 0.6}
ARMS = ("control", "delayed")
PAIRS = 48

MODEL_ARM = "bypass-k1"                    # the unchanged legacy plain/shared model
EARLY_ANS = 0.2
LR = 1e-3
WARMUP = 100
LOG_EVERY = 50
PARAMETERS = 79748
SEED_MIN, SEED_MAX = 10_000, 2 ** 31 - 1
HISTORICAL_SEEDS = frozenset(range(40))    # seeds 0..39 of the historical roster
PURPOSES = ("init", "data", "eval")
STREAM_PREFIX = "teacher-delay-v2"
FORMAT = "premonition-teacher-delay-v2"

_BOOTSTRAPPED = False
_TRAINER_CLASS = None


# ----------------------------------------------------------------------------- schedule helpers
def ramp_end(teacher_until: float) -> float:
    """Ramp end derived from the single independent field `t`: `t + 0.1668`.

    Rounded to 10 decimals so that the delayed arm reports the contract's literal 0.7668 rather than
    0.6 + 0.1668 = 0.7667999999999999 (the control arm's 0.3666 + 0.1668 == 0.5334 is already exact).
    """
    return round(teacher_until + RAMP_WIDTH, 10)


def schedule(arm: str) -> dict:
    if arm not in TEACHER_UNTIL:
        raise SystemExit(f"unknown arm {arm!r}; the registered arms are {ARMS}")
    teacher_until = TEACHER_UNTIL[arm]
    return {"gold_until": GOLD_UNTIL, "teacher_until": teacher_until,
            "ramp_until": ramp_end(teacher_until), "p_own_max": P_OWN_MAX}


def derive_seed(replication: int, purpose: str) -> int:
    """Deterministic seed in [10_000, 2**31 - 1] from the registered seed string."""
    text = f"v3|TrackA|{EXPERIMENT_ID}|replication={replication}|{purpose}"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return SEED_MIN + int(digest, 16) % (SEED_MAX - SEED_MIN + 1)


def job_id(pair_id: int, arm: str) -> str:
    return f"p{pair_id:03d}-{arm}"


def make_plan(pairs: int = PAIRS) -> dict:
    if not 1 <= pairs <= 1000:
        raise SystemExit("--pairs must be between 1 and 1000")
    rows = []
    seen: dict[int, str] = {}
    for i in range(pairs):
        seeds = {}
        for purpose in PURPOSES:
            seed = derive_seed(i, purpose)
            if seed in HISTORICAL_SEEDS:
                raise SystemExit(f"seed {seed} collides with the historical roster (0..39)")
            if seed in seen:
                raise SystemExit(f"seed collision: replication {i}/{purpose} repeats {seen[seed]}")
            seen[seed] = f"replication {i}/{purpose}"
            seeds[purpose] = seed
        jobs = {}
        for arm in ARMS:
            sched = schedule(arm)
            jobs[arm] = {"job_id": job_id(i, arm), "teacher_until": sched["teacher_until"],
                         "ramp_until": sched["ramp_until"]}
        rows.append({"pair_id": i, "init_seed": seeds["init"], "data_seed": seeds["data"],
                     "eval_seed": seeds["eval"], "jobs": jobs})
    return {"experiment_id": EXPERIMENT_ID, "B": B, "B_ref": B_REF, "gold_until": GOLD_UNTIL,
            "ramp_width": RAMP_WIDTH, "p_own_max": P_OWN_MAX, "max_updates": MAX_UPDATES,
            "max_seconds": MAX_SECONDS, "flop_tolerance": FLOP_TOLERANCE, "pairs": rows}


def validate_plan(plan: dict) -> dict:
    """Refuse any recipe override smuggled in through an edited plan under this experiment id."""
    if plan.get("experiment_id") != EXPERIMENT_ID:
        raise SystemExit(f"plan experiment_id {plan.get('experiment_id')!r} is not {EXPERIMENT_ID!r}")
    frozen = (("B", B), ("B_ref", B_REF), ("gold_until", GOLD_UNTIL), ("ramp_width", RAMP_WIDTH),
              ("p_own_max", P_OWN_MAX), ("max_updates", MAX_UPDATES), ("max_seconds", MAX_SECONDS),
              ("flop_tolerance", FLOP_TOLERANCE))
    for key, expected in frozen:
        if key not in plan or plan[key] != expected:
            raise SystemExit(f"plan {key}={plan.get(key)!r} overrides the frozen {expected!r}; "
                             f"no recipe overrides are accepted under {EXPERIMENT_ID}")
    if not isinstance(plan.get("pairs"), list) or not plan["pairs"]:
        raise SystemExit("plan has no pairs")
    for pair in plan["pairs"]:
        if sorted(pair["jobs"]) != sorted(ARMS):
            raise SystemExit(f"pair {pair.get('pair_id')} does not have exactly the arms {ARMS}")
        for arm, job in pair["jobs"].items():
            sched = schedule(arm)
            if job["teacher_until"] != sched["teacher_until"] or job["ramp_until"] != sched["ramp_until"]:
                raise SystemExit(f"{job.get('job_id')}: schedule differs from the frozen {arm} arm")
            if job["job_id"] != job_id(pair["pair_id"], arm):
                raise SystemExit(f"{job.get('job_id')}: job id does not match its pair/arm")
    return plan


def load_plan(path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f"no plan at {path}")
    return validate_plan(json.loads(path.read_text()))


def find_job(plan: dict, wanted: str) -> tuple[dict, str, dict]:
    for pair in plan["pairs"]:
        for arm, job in pair["jobs"].items():
            if job["job_id"] == wanted:
                return pair, arm, job
    raise SystemExit(f"unknown job id {wanted!r}; the plan registers "
                     f"{sum(len(p['jobs']) for p in plan['pairs'])} jobs")


# ----------------------------------------------------------------------------- build helpers
def ensure_bootstrap() -> None:
    global _BOOTSTRAPPED
    if not _BOOTSTRAPPED:
        L.bootstrap()
        _BOOTSTRAPPED = True


def make_model(init_seed: int):
    """The unchanged legacy builder; the parameter count is asserted against the contract."""
    ensure_bootstrap()
    model = R.build(MODEL_ARM, init_seed, EARLY_ANS)
    if model.num_parameters() != PARAMETERS:
        raise SystemExit(f"expected {PARAMETERS} parameters, built {model.num_parameters()}")
    return model


def make_stream(data_seed: int):
    """Independent training-world stream for one pair (both arms share it)."""
    ensure_bootstrap()
    from premonition import toy_ladder
    from premonition.train import label_free
    rng = random.Random(data_seed)
    prefix = f"{STREAM_PREFIX}-{data_seed}"
    return (label_free(toy_ladder.make(L.spec(), L.VISITS, rng, training=True, prefix=prefix)[0])
            for _ in itertools.count())


def trainer_class():
    """`premonition_gpu_port`'s fp32 trainer plus PASSIVE phase telemetry.

    The override only reads counters that already exist before the update (`step`, `flops`, the plan
    the trainer already computed). It runs no extra forward pass, draws nothing from the trainer's
    generator and changes no sample, so losses are bit-identical to the unwrapped trainer.
    """
    global _TRAINER_CLASS
    if _TRAINER_CLASS is not None:
        return _TRAINER_CLASS
    ensure_bootstrap()
    base = G.make_trainer_class(False)

    class TelemetryTrainer(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.crossings: dict[str, dict] = {}

        def _record(self, name: str) -> None:
            if name not in self.crossings:
                self.crossings[name] = {"update": self.step + 1, "flops_before": self.flops,
                                        "flops_share_before": self.flops / self.flop_budget}

        def _train_step(self, batch, plan, loops, track):
            self._record(f"first_{plan.phase}_update")
            if plan.p_own >= self.curriculum.p_own_max:
                self._record("first_p_own_max_update")
            return super()._train_step(batch, plan, loops, track)

    _TRAINER_CLASS = TelemetryTrainer
    return _TRAINER_CLASS


def make_trainer(model, init_seed: int, teacher_until: float, ramp_until: float, device: str,
                 flop_budget: float, *, gold_until: float = GOLD_UNTIL, p_own_max: float = P_OWN_MAX,
                 tolerance: float = FLOP_TOLERANCE):
    ensure_bootstrap()
    from premonition.train import Curriculum, mini_train_config
    curriculum = Curriculum(gold_until=gold_until, teacher_until=teacher_until,
                            ramp_until=ramp_until, p_own_max=p_own_max)
    config = mini_train_config(lr=LR, warmup_steps=WARMUP, log_every=LOG_EVERY, eval_every=0)
    return trainer_class()(model, config, device, flop_budget=flop_budget, tolerance=tolerance,
                           seed=init_seed, curriculum=curriculum), curriculum


def batch_tokens_sha256(batches) -> str:
    """Digest of the token tensors of `batches` (passive: no model call, no RNG)."""
    digest = hashlib.sha256()
    for batch in batches:
        tokens = batch.tokens.detach().cpu().contiguous()
        digest.update(str(tuple(tokens.shape)).encode())
        digest.update(str(tokens.dtype).encode())
        digest.update(tokens.numpy().tobytes())
    return digest.hexdigest()


def save_atomic(blob: dict, path: Path) -> Path:
    """torch.save to a temporary name in the same directory, then rename, so a reader never sees a
    partial file (the same convention as premonition_softread.save_atomic, inlined here because that
    module's `torch` global is only bound by its own lazy class builder)."""
    import os
    import torch
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-{}".format(os.getpid()))
    torch.save(blob, tmp)
    os.replace(tmp, path)
    return path


def state_sha256(model) -> str:
    import premonition_first_card_probe as P
    return P.fingerprint(model)


def completion_status(report: dict) -> str:
    """Completion needs a FLOP-budget stop AND budget_ok. A step/time stop is incomplete."""
    stop = str(report.get("stop", ""))
    return "complete" if stop.startswith("flop budget") and bool(report.get("budget_ok")) else "incomplete"


def source_hashes() -> dict:
    import premonition_first_card_probe as P
    paths = (Path(__file__).resolve(), Path(G.__file__).resolve(), Path(R.__file__).resolve(),
             Path(L.__file__).resolve(), Path(P.__file__).resolve(), L.ARCHIVE / "FROZEN.SHA256SUMS")
    out = {}
    for path in paths:
        key = str(path.relative_to(L.ROOT)) if path.is_relative_to(L.ROOT) else str(path)
        out[key] = L.sha256(path)
    return out


def phase_report(trainer, report: dict) -> dict:
    """Actual boundaries: first update and cumulative FLOPs at each phase and at p_own = p_own_max,
    plus the FLOPs and updates actually spent in each phase. All of it comes from counters the
    trainer already kept."""
    phases = report.get("phases", {})
    return {
        "first_teacher_update": trainer.crossings.get("first_teacher_update"),
        "first_own_update": trainer.crossings.get("first_own_update"),
        "first_p_own_max_update": trainer.crossings.get("first_p_own_max_update"),
        "first_gold_update": trainer.crossings.get("first_gold_update"),
        "flops_in_phase": {name: entry["flops"] for name, entry in phases.items()},
        "updates_in_phase": {name: entry["steps"] for name, entry in phases.items()},
        "first_step_in_phase": {name: entry["first_step"] for name, entry in phases.items()},
        "note": "update is the 1-based index of the update that ran; flops_before is the cumulative "
                "counted FLOPs spent BEFORE it, which is the clock the curriculum uses",
    }


# ----------------------------------------------------------------------------- one job
def train_job(*, out_dir, job_id_: str, pair_id, arm_name: str, init_seed: int, data_seed: int,
              teacher_until: float, ramp_until: float, flop_budget: float = B,
              max_updates: int = MAX_UPDATES, max_seconds: float = MAX_SECONDS, device: str = "cpu",
              gold_until: float = GOLD_UNTIL, p_own_max: float = P_OWN_MAX,
              tolerance: float = FLOP_TOLERANCE, eval_seed=None, extra: dict | None = None) -> dict:
    """Train exactly one registered job into `out_dir` (refused if it already exists).

    A job that raises after its directory was created is recorded as status "failed" (it stays in the
    roster as a failed outcome) and the exception is re-raised.
    """
    out_dir = Path(out_dir)
    created = not out_dir.exists()
    try:
        return _train_job(out_dir=out_dir, job_id_=job_id_, pair_id=pair_id, arm_name=arm_name,
                          init_seed=init_seed, data_seed=data_seed, teacher_until=teacher_until,
                          ramp_until=ramp_until, flop_budget=flop_budget, max_updates=max_updates,
                          max_seconds=max_seconds, device=device, gold_until=gold_until,
                          p_own_max=p_own_max, tolerance=tolerance, eval_seed=eval_seed, extra=extra)
    except BaseException as error:                       # noqa: BLE001 - recorded, then re-raised
        if created and out_dir.is_dir():
            import traceback
            record = {"format": FORMAT, "experiment_id": EXPERIMENT_ID, "job_id": job_id_,
                      "pair_id": pair_id, "arm": arm_name, "status": "failed",
                      "error": f"{type(error).__name__}: {error}",
                      "traceback": traceback.format_exc(), "init_seed": init_seed,
                      "data_seed": data_seed, "flop_budget": flop_budget, "device": device,
                      "report": None, "curve": [], "phases": None}
            (out_dir / "result.json").write_text(json.dumps(record, indent=2, default=str) + "\n")
            (out_dir / "manifest.json").write_text(json.dumps(
                {"format": FORMAT, "experiment_id": EXPERIMENT_ID, "job_id": job_id_,
                 "pair_id": pair_id, "arm": arm_name, "status": "failed",
                 "result": "result.json"}, indent=2) + "\n")
        raise


def _train_job(*, out_dir, job_id_: str, pair_id, arm_name: str, init_seed: int, data_seed: int,
               teacher_until: float, ramp_until: float, flop_budget: float, max_updates: int,
               max_seconds: float, device: str, gold_until: float, p_own_max: float,
               tolerance: float, eval_seed, extra: dict | None) -> dict:
    ensure_bootstrap()
    import torch
    from premonition import answer_path

    out_dir = Path(out_dir)
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists; a job directory is never reused or overwritten")
    if arm_name not in ARMS:
        raise SystemExit(f"unknown arm {arm_name!r}")
    if device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("cuda requested but torch.cuda.is_available() is False")
    if not flop_budget > 0:
        raise SystemExit("the FLOP budget must be positive")

    started = time.perf_counter()
    out_dir.mkdir(parents=True)
    (out_dir / "manifest.json").write_text(json.dumps(
        {"format": FORMAT, "experiment_id": EXPERIMENT_ID, "job_id": job_id_, "pair_id": pair_id,
         "arm": arm_name, "status": "started", "init_seed": init_seed, "data_seed": data_seed,
         "flop_budget": flop_budget}, indent=2) + "\n")

    model = make_model(init_seed)
    init_state = state_sha256(model)
    trainer, curriculum = make_trainer(model, init_seed, teacher_until, ramp_until, device, flop_budget,
                                       gold_until=gold_until, p_own_max=p_own_max, tolerance=tolerance)
    stream = make_stream(data_seed)
    head = [next(stream) for _ in range(2)]
    first_batches = batch_tokens_sha256(head)
    calibration_started = time.perf_counter()
    trainer.calibrate(head)
    calibration_seconds = time.perf_counter() - calibration_started
    trainer.flop_budget = float(flop_budget)     # the explicit literal; never budget_for_steps

    curve: list[dict] = []
    train_started = time.perf_counter()
    report = trainer.train(itertools.chain(head, stream), max_steps=max_updates,
                           max_seconds=max_seconds, on_log=curve.append)
    if device == "cuda":
        torch.cuda.synchronize()
    train_seconds = time.perf_counter() - train_started

    model = model.to("cpu").float()
    if model.num_parameters() != PARAMETERS:
        raise SystemExit(f"parameter count changed during training: {model.num_parameters()}")
    identity = dict(answer_path.identity(answer_path.CARD_BYPASS, model.config),
                    arm=MODEL_ARM, experiment_id=EXPERIMENT_ID, arm_name=arm_name,
                    privilege="L_ask trained on oracle evidence lines (as D)",
                    note="A3-teacher-delay-v2; legacy request path, shared key/value pooling, "
                         "no wire, no added parameters")
    # The blob keeps premonition_gpu_port's exact fields (so premonition_first_card_probe.load_from and
    # the pair suite load it unchanged) and only ADDS this experiment's identifiers.
    blob = {"state_dict": model.state_dict(), "config": _as_dict(model.config), "arm": MODEL_ARM,
            "identity": identity, "seed": init_seed, "no_step_emb": False, "ordered_evidence": False,
            "relation_shortcut": False, "key_pool": False, "width": None,
            "model_class": type(model).__name__,
            "writer_class": type(model.writer).__name__ if model.writer is not None else None,
            "lr_cooldown": 0.0,
            "experiment_id": EXPERIMENT_ID, "job_id": job_id_, "pair_id": pair_id,
            "arm_name": arm_name, "init_seed": init_seed, "data_seed": data_seed}
    save_started = time.perf_counter()
    save_atomic(blob, out_dir / "model.pt")
    save_seconds = time.perf_counter() - save_started

    status = completion_status(report)
    result = {
        "format": FORMAT, "experiment_id": EXPERIMENT_ID, "job_id": job_id_, "pair_id": pair_id,
        "arm": arm_name, "status": status, "report": report,
        "curriculum": {"gold_until": gold_until, "teacher_until": teacher_until,
                       "ramp_until": ramp_until, "ramp_width": RAMP_WIDTH, "p_own_max": p_own_max,
                       "early_ans": EARLY_ANS, "flop_tolerance": tolerance},
        "phases": phase_report(trainer, report),
        "curve": curve,
        "parameters": model.num_parameters(),
        "init_state_sha256": init_state,
        "first_batches_sha256": first_batches,
        "seconds_train": train_seconds, "seconds_total": time.perf_counter() - started,
        "seconds_calibrate": calibration_seconds, "seconds_checkpoint_save": save_seconds,
        "device": device, "gpu_name": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "torch_version": torch.__version__,
        "source_sha256": source_hashes(),
        "checkpoint_sha256": L.sha256(out_dir / "model.pt"),
        "model_arm": MODEL_ARM, "init_seed": init_seed, "data_seed": data_seed, "eval_seed": eval_seed,
        "flop_budget": float(flop_budget), "max_updates": max_updates, "max_seconds": max_seconds,
        "updates_done": trainer.step, "lr": LR, "warmup_steps": WARMUP, "log_every": LOG_EVERY,
        "precision": "fp32", "lr_cooldown": 0.0,
        "checkpoint": str(out_dir / "model.pt"),
        "python": sys.version.split()[0], "platform": platform.platform(),
        "command": " ".join(sys.argv),
        "completion_rule": "complete requires a FLOP-budget stop AND budget_ok; an update or time "
                           "stop is incomplete even though a checkpoint exists",
    }
    if extra:
        result.update(extra)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    (out_dir / "manifest.json").write_text(json.dumps(
        {"format": FORMAT, "experiment_id": EXPERIMENT_ID, "job_id": job_id_, "pair_id": pair_id,
         "arm": arm_name, "status": status, "init_seed": init_seed, "data_seed": data_seed,
         "flop_budget": float(flop_budget), "result": "result.json"}, indent=2) + "\n")
    return result


def _as_dict(config) -> dict:
    from dataclasses import asdict
    return asdict(config)


# ----------------------------------------------------------------------------- sub-commands
def cmd_plan(args) -> int:
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"{out} already exists; choose a new plan directory")
    plan = make_plan(args.pairs)
    out.mkdir(parents=True)
    (out / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    (out / "plan_sources.json").write_text(json.dumps(
        {"format": FORMAT, "experiment_id": EXPERIMENT_ID, "launches": False,
         "seed_string": f"v3|TrackA|{EXPERIMENT_ID}|replication=<i>|<purpose>",
         "source_sha256": source_hashes()}, indent=2) + "\n")
    jobs = [job["job_id"] for pair in plan["pairs"] for job in pair["jobs"].values()]
    print(json.dumps({"plan": str(out / "plan.json"), "pairs": len(plan["pairs"]), "jobs": len(jobs),
                      "first_jobs": jobs[:4], "launched": 0}, indent=2))
    return 0


def cmd_run(args) -> int:
    plan = load_plan(args.plan)
    pair, arm, job = find_job(plan, args.job)
    out_dir = Path(args.out_root) / "jobs" / job["job_id"]
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists; a job directory is never reused or overwritten")
    ensure_bootstrap()
    import torch
    torch.set_num_threads(max(1, args.threads))
    result = train_job(out_dir=out_dir, job_id_=job["job_id"], pair_id=pair["pair_id"], arm_name=arm,
                       init_seed=pair["init_seed"], data_seed=pair["data_seed"],
                       eval_seed=pair["eval_seed"], teacher_until=job["teacher_until"],
                       ramp_until=job["ramp_until"], flop_budget=plan["B"],
                       max_updates=plan["max_updates"], max_seconds=plan["max_seconds"],
                       tolerance=plan["flop_tolerance"], gold_until=plan["gold_until"],
                       p_own_max=plan["p_own_max"], device=args.device,
                       extra={"plan": str(Path(args.plan)), "threads": max(1, args.threads)})
    print(json.dumps({"job_id": result["job_id"], "arm": result["arm"], "status": result["status"],
                      "stop": result["report"]["stop"], "budget_ok": result["report"]["budget_ok"],
                      "updates": result["updates_done"], "flops": result["report"]["flops"],
                      "seconds_train": round(result["seconds_train"], 2),
                      "out": str(out_dir)}, indent=2))
    return 0 if result["status"] == "complete" else 2


def cmd_rehearse(args) -> int:
    out = Path(args.out)
    if "jobs" in out.resolve().parts:
        raise SystemExit("a rehearsal never writes inside a plan's jobs/ directory")
    if out.exists():
        raise SystemExit(f"{out} already exists; choose a new rehearsal directory")
    if args.updates < 1:
        raise SystemExit("--updates must be at least 1")
    ensure_bootstrap()
    import torch
    torch.set_num_threads(max(1, args.threads))

    data_seed = derive_seed(args.index, "rehearsal")
    init_seed = derive_seed(args.index, "rehearsal-init")
    roster = {derive_seed(i, purpose) for i in range(PAIRS) for purpose in PURPOSES}
    if data_seed in roster or init_seed in roster or {data_seed, init_seed} & HISTORICAL_SEEDS:
        raise SystemExit("rehearsal seeds must be disjoint from the learning roster")

    out.mkdir(parents=True)
    started = time.perf_counter()
    measurements = {}
    for name, sched in (("control_schedule", schedule("control")),
                        ("own_forced", {"gold_until": 0.0, "teacher_until": 0.0, "ramp_until": 0.0,
                                        "p_own_max": P_OWN_MAX})):
        model = make_model(init_seed)
        trainer, _ = make_trainer(model, init_seed, sched["teacher_until"], sched["ramp_until"],
                                  args.device, B, gold_until=sched["gold_until"],
                                  p_own_max=sched["p_own_max"])
        stream = make_stream(data_seed)
        head = [next(stream) for _ in range(2)]
        t0 = time.perf_counter()
        trainer.calibrate(head)
        calibrate_seconds = time.perf_counter() - t0
        trainer.flop_budget = B
        curve: list[dict] = []
        t0 = time.perf_counter()
        report = trainer.train(itertools.chain(head, stream), max_steps=args.updates,
                               max_seconds=args.max_seconds, on_log=curve.append)
        if args.device == "cuda":
            torch.cuda.synchronize()
        train_seconds = time.perf_counter() - t0
        model = model.to("cpu").float()
        path = out / f"rehearsal-{name}.pt"
        t0 = time.perf_counter()
        save_atomic({"state_dict": model.state_dict(), "config": _as_dict(model.config),
                     "arm": MODEL_ARM, "rehearsal": name}, path)
        save_seconds = time.perf_counter() - t0
        measurements[name] = {
            "updates": report["steps"], "stop": report["stop"], "flops": report["flops"],
            "seconds_train": train_seconds,
            "counted_flops_per_second": report["flops"] / max(train_seconds, 1e-9),
            "seconds_calibrate": calibrate_seconds, "seconds_checkpoint_save": save_seconds,
            "checkpoint_bytes": path.stat().st_size,
            "phases_seen": {k: v["steps"] for k, v in report["phases"].items()},
            "curriculum": sched,
            "peak_gpu_reserved_bytes": (torch.cuda.max_memory_reserved()
                                        if args.device == "cuda" else None),
        }
    rehearsal = {
        "format": FORMAT + "-rehearsal", "experiment_id": EXPERIMENT_ID,
        "note": "resource rehearsal on a stream disjoint from the 48 learning pairs; no learning job, "
                "no evaluation panel and no stage claim. The control-schedule measurement starts at "
                "zero spent FLOPs, so it measures the gold phase; own_forced measures the expensive "
                "p_own=0.75 end and is the conservative bound.",
        "rehearsal_index": args.index, "data_seed": data_seed, "init_seed": init_seed,
        "disjoint_from_roster": True, "device": args.device, "threads": max(1, args.threads),
        "concurrency_note": args.concurrency_note,
        "B": B, "nominal_per_job_floor_counted_flops_per_second": B / 1200,
        "measurements": measurements,
        "gpu_name": torch.cuda.get_device_name(0) if args.device == "cuda" else None,
        "torch_version": torch.__version__, "python": sys.version.split()[0],
        "platform": platform.platform(), "seconds_total": time.perf_counter() - started,
        "source_sha256": source_hashes(), "command": " ".join(sys.argv),
    }
    (out / "rehearsal.json").write_text(json.dumps(rehearsal, indent=2, default=str) + "\n")
    print(json.dumps({"out": str(out / "rehearsal.json"),
                      "control_schedule_flops_per_s":
                          measurements["control_schedule"]["counted_flops_per_second"],
                      "own_forced_flops_per_s": measurements["own_forced"]["counted_flops_per_second"]},
                     indent=2))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    subs = parser.add_subparsers(dest="command", required=True)

    p = subs.add_parser("plan", help="write the frozen 48-pair plan; launches nothing")
    p.add_argument("--out", required=True, help="new directory for plan.json")
    p.add_argument("--pairs", type=int, default=PAIRS)
    p.set_defaults(func=cmd_plan)

    r = subs.add_parser("run", help="train exactly one registered job")
    r.add_argument("--plan", required=True)
    r.add_argument("--job", required=True)
    r.add_argument("--out-root", required=True)
    r.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    r.add_argument("--threads", type=int, default=1)
    r.set_defaults(func=cmd_run)

    h = subs.add_parser("rehearse", help="disjoint resource rehearsal; never a learning job")
    h.add_argument("--out", required=True)
    h.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    h.add_argument("--updates", type=int, required=True)
    h.add_argument("--concurrency-note", required=True,
                   help="the simultaneous-job configuration this rehearsal represents")
    h.add_argument("--threads", type=int, default=1)
    h.add_argument("--index", type=int, default=0, help="rehearsal replication index")
    h.add_argument("--max-seconds", type=float, default=MAX_SECONDS)
    h.set_defaults(func=cmd_rehearse)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
