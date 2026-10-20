"""Run card R1, stage 1 (design/steals-2026-10-17/R1-STAGE1-CARD.md): Muon against AdamW on village data. DRAFT.

Arms: A0 = D, full preset, every steal flag off, `train.train_d` with AdamW; A1 = the same with `optimizer="muon"`.
Both at the card's lr. At a seed both arms are bit-identical at init and read the same batches; they run back to back
(the order alternates with the seed) on one box.

Primary readout: held-out village loss (teacher mode, 4 fixed loops, the fixed `eval_visits` validation visits,
fixed distractor seeds, fp32, eval mode) every `eval_every` steps and at the end, through `train_d(eval_extra=...)`.
The training clock excludes evaluation: it is the sum of the log windows' seconds (`MiniTrainer.train` moves each
window's start past an evaluation), so `eval_every` must be a multiple of `log_every`. The loss is interpolated at
T* = the shorter arm's training seconds; d_s = loss(A0, T*) - loss(A1, T*).
Bar: mean(d) - 2 SD(d)/sqrt(3) > 0, d_s > 0 in >= 2 of 3 seeds, mean(d) >= 3% of A0's mean loss at T* (Q42).
G-ACC: A1's final `validate` accuracy more than 3 points below A0's in >= 2 of 3 seeds is a trip.
G-RET (pass-blocking): pooled mean recall@4(A1) < 0.8 x A0's, or A1 more than 0.10 below A0 in >= 2 of 3 seeds, is a
trip; recall@4 missing in any run is a trip.

Every run is bound to the runner, card and package hashes (premonition/ and learnlab/, by content; the commit is
recorded, not binding) and to the data identity (data tag, tokenizer sha256, detector digest). A run directory without
the card's SEAL.sha256.txt runs only with --unsealed and its result is never a card verdict.

    python3 -B scripts/premonition_steals_r1_stage1.py build --root BOX_ROOT              # the village build, once
    python3 -B scripts/premonition_steals_r1_stage1.py run --root BOX_ROOT --data-rel REL --out OUT
    python3 -B scripts/premonition_steals_r1_stage1.py dry --out SCRATCH                    # P3: CPU, tiny village
    python3 -B scripts/premonition_steals_r1_stage1.py verify --out OUT                     # after copy-off
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import time

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from premonition import train as ptrain                                     # noqa: E402

ARMS = {"A0": "adamw", "A1": "muon"}
CARD_SEEDS = (0, 1, 2)
EVAL_LOOPS = 4
EVAL_SEED = 1234                      # distractor seed of held-out batch i: EVAL_SEED + i
MIN_EFFECT = 0.03                     # relative, for the loss readout (Q42)
ACC_POINTS = 0.03                     # G-ACC
RECALL_FLOOR = 0.8                    # G-RET (a)
RECALL_POINTS = 0.10                  # G-RET (b)
CARD = ROOT / "design" / "steals-2026-10-17" / "R1-STAGE1-CARD.md"
SEAL = "SEAL.sha256.txt"
MANIFEST = "MANIFEST.sha256"
# The card's settings (section 2); F is filled in from the re-quote before the seal.
CARD_SETTINGS = {"variant": "D", "size": "full", "device": "cuda", "lr": 1e-3, "flop_budget": None,
                 "warmup_steps": 100, "max_tokens": 55_000, "max_visits": 48, "log_every": 50, "eval_every": 500,
                 "eval_visits": 256, "calibration_batches": 4}
BUILD = {"visits": "large", "seed": 0}
# Stage 1b's F (card section 2): the largest F whose projected cost, at stage 1a's measured step and evaluation times
# and the booked box's $/h, stays within SAFETY x the hard stop; never above F_MAX. Fixed before any GPU run.
# Stage 1a and 1b run as one job on one box under one cap (coordinator ruling 10-20). F_MAX is spec 9.7's ~3-epoch
# limit on this build (7.5e15 / 1.14e12 FLOPs per step x 48.9k tokens ~ 3.0 passes over 106.6M tokens).
PRICE = {"cap_total": 2.80, "hard_stop_1b": 2.50, "safety": 0.8, "f_max": 7.5e15, "f_min": 3.15e15,
         "copy_off_seconds": 900.0, "seeds": 3, "max_muon_step_ratio": 1.25, "time_safety": 0.9}
F_1A = 3.4e14                         # stage 1a: 300 steps x 1.14e12 FLOPs per step (measured on the build, CPU fit)
PACKAGE = "premonition/*.py + learnlab/**/*.py + memorylab/**/*.py"   # the seal's name for the package hash


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_hash() -> str:
    """One hash over the code a run executes: premonition/*.py, learnlab/**/*.py and memorylab/**/*.py (the budget),
    by relative path and content."""
    digest = hashlib.sha256()
    for path in sorted([*(ROOT / "premonition").glob("*.py"), *(ROOT / "learnlab").rglob("*.py"),
                        *(ROOT / "memorylab").rglob("*.py")]):
        digest.update(path.relative_to(ROOT).as_posix().encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def identity() -> dict:
    """The binding hashes; `commit` and the machine are recorded alongside but not compared."""
    return {"runner": sha256(Path(__file__).resolve()), "card": sha256(CARD) if CARD.exists() else None,
            "package": package_hash()}


def provenance() -> dict:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    cuda = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    return {"commit": commit or None, "torch": torch.__version__, "python": platform.python_version(),
            "machine": platform.machine(), "gpu": cuda}


def check_seal(out: Path, ident: dict, unsealed: bool) -> bool:
    """True when `out` holds a seal matching this runner, card and package. Without one, only --unsealed runs."""
    seal = out / SEAL
    if not seal.exists():
        if not unsealed:
            raise SystemExit(f"{seal} is missing; pass --unsealed for a plumbing run (never a card verdict)")
        return False
    if unsealed:
        raise SystemExit(f"{seal} exists: a sealed directory runs only the card, never --unsealed")
    sealed = {line.split(maxsplit=1)[1]: line.split()[0] for line in seal.read_text().splitlines()
              if len(line.split()) >= 2}
    want = {"design/steals-2026-10-17/R1-STAGE1-CARD.md": ident["card"],
            "scripts/premonition_steals_r1_stage1.py": ident["runner"], PACKAGE: ident["package"]}
    for name, digest in want.items():
        if sealed.get(name) != digest:
            raise SystemExit(f"{name} does not match the seal in {seal}; refusing to run")
    return True


def write_json(path: Path, value) -> None:
    """Atomic: a killed run never leaves a half-written file behind."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=1))
    os.replace(tmp, path)


# ----------------------------------------------------------------------------- readout
@torch.no_grad()
def held_out_loss(model, batches) -> dict:
    """Mean teacher-mode losses over the fixed validation batches: fixed loops and distractor seeds, fp32, eval mode.
    Runs inside `train_d`'s validation hook (under `read_only`, which also restores the RNG)."""
    was = model.training
    model.eval()
    device = next(model.parameters()).device
    started = time.perf_counter()
    rows = []
    for i, batch in enumerate(batches):
        generator = torch.Generator(device=device).manual_seed(EVAL_SEED + i)
        out = model(batch.to(device), mode="teacher", loops=EVAL_LOOPS, generator=generator)
        rows.append((batch.tokens.shape[0], {k: float(out[k]) for k in ("loss", "lm", "ask", "ans", "halt")}))
    model.train(was)
    visits = sum(n for n, _ in rows)                 # batches differ in size: weight each by its visits
    return {"held_out": {k: sum(n * r[k] for n, r in rows) / visits for k in rows[0][1]} if rows else None,
            "held_out_seconds": time.perf_counter() - started}


def train_clock(history: list) -> dict[int, float]:
    """Training seconds at each logged step, evaluation excluded: the sum of window seconds (window tokens over the
    window's tokens/s; `MiniTrainer.train` moves a window's start past any evaluation inside it)."""
    clock, total, tokens = {}, 0.0, 0
    for record in history:
        if "eval" in record:
            continue
        window = record["tokens"] - tokens
        total += window / record["tokens_per_s"] if window else 0.0
        tokens = record["tokens"]
        clock[record["step"]] = total
    return clock


def curve_of(report: dict) -> list:
    """[(training seconds, step, held-out loss)] at every evaluation and at the end."""
    clock = train_clock(report["history"])
    points = []
    for record in report["history"]:
        if "eval" in record:
            if record["step"] not in clock:
                raise RuntimeError(f"no log window ends at evaluation step {record['step']}; "
                                   "eval_every must be a multiple of log_every")
            points.append((clock[record["step"]], record["step"], record["eval"]["held_out"]["loss"]))
    final = report["validation"]["held_out"]["loss"]
    end = max(clock.values(), default=0.0)
    steps = max(clock, default=0)              # an aborted report has no "steps"
    if not points or points[-1][1] != steps:
        points.append((end, steps, final))
    return points


def loss_at(curve: list, seconds: float) -> float:
    """Held-out loss linearly interpolated at `seconds` of training (clamped to the curve's ends)."""
    if seconds <= curve[0][0]:
        return curve[0][2]
    for (t0, _, l0), (t1, _, l1) in zip(curve, curve[1:]):
        if t0 <= seconds <= t1:
            return l0 if t1 == t0 else l0 + (l1 - l0) * (seconds - t0) / (t1 - t0)
    return curve[-1][2]


def finite(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


# ----------------------------------------------------------------------------- one run
def run(arm: str, seed: int, *, budget, data_rel: str, tokenizer_path: str, settings: dict, out: Path,
        bound: dict, log) -> dict:
    ckpt = out / "ckpt" / f"{arm}-s{seed}"
    if ckpt.exists():                              # left by a run killed before its JSON; never scored
        shutil.rmtree(ckpt)
    relative = os.path.relpath(ckpt, budget.root)
    if relative.startswith(".."):
        raise SystemExit(f"--out must be inside --root ({budget.root}) so the checkpoint can be saved there")
    keys = ("variant", "size", "device", "lr", "flop_budget", "warmup_steps", "max_tokens", "max_visits",
            "log_every", "eval_every", "eval_visits", "calibration_batches")
    log(f"{arm} s{seed}: {ARMS[arm]} start {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    started = time.perf_counter()
    report = ptrain.train_d(budget, data_rel=data_rel, tokenizer_path=tokenizer_path, seed=seed,
                            optimizer=ARMS[arm], eval_extra=held_out_loss, checkpoint=relative,
                            log=lambda line: log(f"{arm} s{seed} | {line}"), **{k: settings[k] for k in keys})
    wall = time.perf_counter() - started
    bound = {**bound, "data": {**bound["data"], "tag": report["data"]["tag"], "detector": report["detector"]}}
    curve = curve_of(report)
    clock = train_clock(report["history"])
    seconds = max(clock.values(), default=0.0)
    evals = [{"step": r["step"], "held_out": r["eval"]["held_out"], "accuracy": r["eval"].get("accuracy"),
              "gold_recall_at_4": r["eval"].get("gold_recall_at_4"),
              "seconds": r["eval"].get("seconds", 0.0) + r["eval"].get("held_out_seconds", 0.0)}
             for r in report["history"] if "eval" in r]
    windows = [{"step": r["step"], "s_per_step": None} for r in report["history"] if "eval" not in r]
    previous = (0, 0.0)
    for window in windows:
        steps, at = window["step"] - previous[0], clock[window["step"]]
        window["s_per_step"] = (at - previous[1]) / steps if steps else None
        previous = (window["step"], at)
    validation = report["validation"]
    losses = [*(report.get("final") or {}).values(), *(p[2] for p in curve),
              *(v for e in evals for v in e["held_out"].values())]
    result = {
        "arm": arm, "seed": seed, "optimizer": ARMS[arm], "settings": settings, "bound": bound,
        "provenance": provenance(), "status": report["status"], "error": report.get("error"),
        "stop": report.get("stop"), "budget_ok": report.get("budget_ok"), "steps": report.get("steps"),
        "parameters": report["parameters"], "flops": report.get("flops"), "train_seconds": seconds,
        "wall_seconds": wall,
        "final_eval_seconds": validation.get("seconds", 0.0) + validation.get("held_out_seconds", 0.0),
        "s_per_step": seconds / max(clock) if clock and max(clock) else None,
        "final_losses": report.get("final"), "curve": curve, "evals": evals, "windows": windows,
        "validation": {k: validation.get(k) for k in (
            "held_out", "accuracy", "accuracy_gold_cards", "gold_recall_at_4", "random_recall_at_4", "asked_rate",
            "loops_mean", "halt_rate", "questions")},
        "finite": all(finite(v) for v in losses if v is not None),
        "checkpoint": ckpt.relative_to(out).as_posix(),
    }
    log(f"{arm} s{seed}: {result['status']}, {result['steps']} steps, train {seconds:.0f}s (wall {wall:.0f}s), "
        f"held-out loss {curve[-1][2]:.4f}, acc {validation.get('accuracy')}, "
        f"recall@4 {validation.get('gold_recall_at_4')}")
    return result


def card_settings(settings: dict) -> bool:
    """The card's settings, F aside (F comes from `price`, and the runs' shared price file binds it)."""
    strip = lambda d: {k: v for k, v in d.items() if k != "flop_budget"}           # noqa: E731
    return strip(settings) == strip(CARD_SETTINGS) and finite(settings.get("flop_budget"))


# ----------------------------------------------------------------------------- stage 1b's F
def projected_seconds(f: float, arms: list[dict], eval_every: int) -> float:
    """Stage 1b's box seconds at F from stage 1a's runs on the same box (the build and the caches are already paid):
    per run, steps x s/step + evaluations x their seconds + the start-up with the caches built (the faster arm's);
    times the card's seeds; plus the copy-off."""
    startups = [max(arm["wall_seconds"] - arm["train_seconds"] - sum(e["seconds"] for e in arm["evals"])
                    - arm["final_eval_seconds"], 0.0) for arm in arms]
    total = PRICE["copy_off_seconds"]
    for arm in arms:
        steps = f / (arm["flops"] / arm["steps"])
        evals = math.floor(steps / eval_every) + 1
        eval_seconds = statistics.fmean([e["seconds"] for e in arm["evals"]] + [arm["final_eval_seconds"]])
        total += PRICE["seeds"] * (steps * arm["s_per_step"] + evals * eval_seconds + min(startups))
    return total


def timing_settings() -> dict:
    """Stage 1a: the card's settings at F_1a (300 steps' worth), seed 0, unsealed, on the box that then runs 1b."""
    return dict(CARD_SETTINGS, flop_budget=F_1A)


def price(arms: list[dict], *, dph: float, spent_seconds: float, seconds_left: float,
          ident: dict | None = None) -> dict:
    """The card's F rule on stage 1a's two runs (one per arm), at the box's $/h, after `spent_seconds` of box time,
    with `seconds_left` before the job's own run deadline. F is the largest value in [F_min, F_max] (two significant
    figures, rounded down, never below F_min) whose projected stage-1b time fits all three: SAFETY x the 1b stop, the
    total cap less what is spent (both in dollars at `dph`), and time_safety x the seconds left. "go" is False, with
    the reason, when 1a's gate fails or even F_min does not fit."""
    if sorted(a["arm"] for a in arms) != sorted(ARMS) or any(a["status"] != "completed" or not a["finite"]
                                                               for a in arms):
        raise SystemExit("price needs one completed, finite stage-1a run of each arm")
    if any(a["settings"] != timing_settings() or a["seed"] != 0 for a in arms):
        raise SystemExit("price needs stage-1a runs made with `run --timing` (the card's settings at F_1a, seed 0)")
    if ident is not None and any(a["bound"].get("code") != ident for a in arms):
        raise SystemExit("the stage-1a runs were made by other code than this runner, card and package")
    spent = spent_seconds / 3600.0 * dph
    budget = min(PRICE["safety"] * PRICE["hard_stop_1b"], PRICE["cap_total"] - spent)
    allowed = min(budget / dph * 3600.0, PRICE["time_safety"] * seconds_left)
    cost = lambda f: projected_seconds(f, arms, CARD_SETTINGS["eval_every"])         # noqa: E731
    by = {a["arm"]: a for a in arms}
    ratio = by["A1"]["s_per_step"] / by["A0"]["s_per_step"]
    gate = ratio <= PRICE["max_muon_step_ratio"]
    fits = cost(PRICE["f_min"]) <= allowed
    f = None
    if fits and cost(PRICE["f_max"]) <= allowed:
        f = PRICE["f_max"]
    elif fits:
        low, high = PRICE["f_min"], PRICE["f_max"]
        for _ in range(60):
            mid = (low + high) / 2
            low, high = (mid, high) if cost(mid) <= allowed else (low, mid)
        unit = 10.0 ** (math.floor(math.log10(low)) - 1)
        f = max(PRICE["f_min"], math.floor(low / unit) * unit)      # two significant figures, down, not below F_min
    reason = None if gate and fits else ("1a gate: Muon's s/step over 1.25 x AdamW's" if not gate else
                                         f"even F_min does not fit ${budget:.2f} at ${dph}/h within "
                                         f"{seconds_left:.0f} s")
    projected = None if f is None else cost(f) / 3600.0 * dph
    return {"go": gate and fits, "reason": reason, "flop_budget": f, "dph": dph, "rule": PRICE,
            "spent_seconds": spent_seconds, "seconds_left": seconds_left, "spent_dollars": spent,
            "budget_dollars": budget, "allowed_seconds": allowed,
            "projected_hours": None if f is None else cost(f) / 3600.0, "projected_dollars": projected,
            "projected_total_dollars": None if f is None else spent + projected,
            "steps_at_f": None if f is None else {a["arm"]: f / (a["flops"] / a["steps"]) for a in arms},
            "s_per_step": {a["arm"]: a["s_per_step"] for a in arms}, "muon_step_ratio": ratio,
            "gate_1a": {"muon_step_ratio_ok": gate},
            "s_per_flop": {a["arm"]: a["s_per_step"] / (a["flops"] / a["steps"]) for a in arms}}


# ----------------------------------------------------------------------------- scoring
def arm_order(seed: int) -> list[str]:
    names = list(ARMS)
    return names[seed % 2:] + names[:seed % 2]


def check_price(price: dict) -> None:
    """A PRICE.json the sealed rule could have written, saying go: this runner's rule, F within [F_min, F_max], 1a's
    gate met, the projection within SAFETY x the 1b stop, and spent + projected within the total cap."""
    if price.get("rule") != PRICE:
        raise SystemExit("PRICE.json was made under another rule")
    if price.get("go") is not True:
        raise SystemExit(f"PRICE.json says no go: {price.get('reason')}")
    f = price.get("flop_budget")
    if not (finite(f) and PRICE["f_min"] <= f <= PRICE["f_max"]):
        raise SystemExit(f"PRICE.json's F {f} is outside [{PRICE['f_min']:.3g}, {PRICE['f_max']:.3g}]")
    if not price.get("gate_1a", {}).get("muon_step_ratio_ok"):
        raise SystemExit("PRICE.json records a failed stage-1a gate (Muon's s/step over 1.25 x AdamW's)")
    projected = price.get("projected_dollars")
    if not (finite(projected) and projected <= PRICE["safety"] * PRICE["hard_stop_1b"]):
        raise SystemExit("PRICE.json projects past the 1b stop")
    if not (finite(price.get("spent_dollars")) and price["spent_dollars"] + projected <= PRICE["cap_total"]):
        raise SystemExit("PRICE.json's spent + projected is over the total cap")
    if not (finite(price.get("projected_hours")) and finite(price.get("seconds_left"))
            and price["projected_hours"] * 3600.0 <= PRICE["time_safety"] * price["seconds_left"]):
        raise SystemExit("PRICE.json projects past the job's run deadline")


def check_price_source(price_file: dict, timing: Path) -> None:
    """The sealed 1b run's own check that F came from the rule: the 1a runs in `timing` are the ones PRICE.json
    hashed, and `price` on them, with the recorded inputs, gives the same F and go."""
    names = [f"{arm}-s0.json" for arm in ARMS]
    if price_file.get("from") != {n: sha256(timing / n) for n in names}:
        raise SystemExit(f"PRICE.json was not made from the stage-1a runs in {timing}")
    again = price([json.loads((timing / n).read_text()) for n in names], dph=price_file["dph"],
                  spent_seconds=price_file["spent_seconds"], seconds_left=price_file["seconds_left"],
                  ident=identity())
    if (again["go"], again["flop_budget"]) != (price_file.get("go"), price_file.get("flop_budget")):
        raise SystemExit(f"price on {timing} gives go {again['go']}, F {again['flop_budget']}; PRICE.json says "
                         f"go {price_file.get('go')}, F {price_file.get('flop_budget')}")


def score(runs: list[dict], *, sealed: bool, ident: dict | None = None) -> dict:
    """The card's verdict, or NOT SCORED with the reason (the numbers are still computed for plumbing checks).
    DID NOT TRAIN comes first, and says so when the runs are not the card's either."""
    by = {(r["arm"], r["seed"]): r for r in runs}
    seeds = sorted({r["seed"] for r in runs})
    problems = []
    if not sealed:
        problems.append("unsealed run directory")
    if ident is not None and any(r["bound"].get("code") != ident for r in runs):
        problems.append("runs made with other code than this sealed runner, card and package")
    if len({(r.get("provenance") or {}).get("torch") for r in runs}) != 1:
        problems.append("runs made under different torch versions")
    non_finite = sorted(f"{r['arm']}-s{r['seed']}" for r in runs if not r["finite"])
    if non_finite:                                    # first, whatever else is wrong
        verdict = "DID NOT TRAIN"
        if problems or any((arm, seed) not in by for arm in ARMS for seed in seeds) or len(by) != len(runs):
            verdict += " (and not the card's runs: " + "; ".join(problems or ["arms missing or repeated"]) + ")"
        return {"verdict": verdict, "non_finite": non_finite}
    if any((arm, seed) not in by for arm in ARMS for seed in seeds) or len(by) != len(runs):
        return {"verdict": "NOT SCORED: every seed needs exactly one run of each arm (no numbers can be paired)"}
    if tuple(seeds) != CARD_SEEDS:
        problems.append(f"seeds {tuple(seeds)}, the card registers {CARD_SEEDS}")
    if any(not card_settings(r["settings"]) for r in runs) or len({r["settings"]["flop_budget"] for r in runs}) != 1:
        problems.append("settings differ from the card's")
    if len({json.dumps(r["bound"], sort_keys=True) for r in runs}) != 1:
        problems.append("runs are bound to different code or data")
    if any(not r["bound"].get("data", {}).get("price") for r in runs):
        problems.append("no PRICE.json binds F")
    incomplete = [f"{r['arm']}-s{r['seed']}" for r in runs if r["status"] != "completed" or not r["budget_ok"]]
    if incomplete:
        problems.append(f"incomplete runs {incomplete}")
    unpaired = [s for s in seeds if (by[("A0", s)]["steps"], by[("A0", s)]["flops"]) !=
                (by[("A1", s)]["steps"], by[("A1", s)]["flops"])]
    if unpaired:                                       # the arms of a seed must train the same steps and FLOPs
        problems.append(f"unpaired steps or FLOPs at seeds {unpaired}")
    rows, ds, base, acc_hits, rec_hits, rec0, rec1, unreadable = [], [], [], 0, 0, [], [], False
    for seed in seeds:
        a0, a1 = by[("A0", seed)], by[("A1", seed)]
        t_star = min(a0["train_seconds"], a1["train_seconds"])
        l0, l1 = loss_at(a0["curve"], t_star), loss_at(a1["curve"], t_star)
        acc0, acc1 = a0["validation"]["accuracy"], a1["validation"]["accuracy"]
        r0, r1 = a0["validation"]["gold_recall_at_4"], a1["validation"]["gold_recall_at_4"]
        acc_hits += acc1 - acc0 < -ACC_POINTS
        if r0 is None or r1 is None:
            unreadable = True
        else:
            rec0.append(r0)
            rec1.append(r1)
            rec_hits += r1 - r0 < -RECALL_POINTS
        ds.append(l0 - l1)
        base.append(l0)
        rows.append({"seed": seed, "order": arm_order(seed), "t_star": t_star, "loss_A0": l0, "loss_A1": l1,
                     "d": l0 - l1, "equal_step_loss_A0": a0["curve"][-1][2], "equal_step_loss_A1": a1["curve"][-1][2],
                     "steps": [a0["steps"], a1["steps"]], "s_per_step": [a0["s_per_step"], a1["s_per_step"]],
                     "accuracy": [acc0, acc1], "recall_at_4": [r0, r1]})
    n = len(ds)
    mean = statistics.fmean(ds)
    sd = statistics.stdev(ds) if n > 1 else math.inf
    se = sd / math.sqrt(n)
    positive = sum(d > 0 for d in ds)
    effect = mean / statistics.fmean(base)
    bar = mean - 2 * se > 0 and positive >= math.ceil(2 * n / 3) and effect >= MIN_EFFECT
    g_acc_trip = acc_hits >= math.ceil(2 * n / 3)
    pooled = None if unreadable else (statistics.fmean(rec1), statistics.fmean(rec0))
    g_ret_trip = unreadable or pooled[0] < RECALL_FLOOR * pooled[1] or rec_hits >= math.ceil(2 * n / 3)
    if bar and g_ret_trip:
        verdict = "NOT COUNTED (retrieval guard)"
    elif bar and g_acc_trip:
        verdict = "NOT COUNTED (accuracy guard)"
    elif bar:
        verdict = "PASS"
    elif mean + 2 * se < 0:
        verdict = "PROVED WRONG"
    else:
        verdict = "NOT SHOWN"
    out = {"rows": rows, "d": ds, "mean_d": mean, "sd_d": sd, "lower": mean - 2 * se, "upper": mean + 2 * se,
           "seeds_positive": positive, "relative_effect": effect, "bar": bar,
           "G_ACC": {"seeds_below": acc_hits, "trip": g_acc_trip},
           "G_RET": {"pooled_A1_A0": pooled, "seeds_below": rec_hits, "unreadable": unreadable, "trip": g_ret_trip}}
    if problems:
        out.update(verdict=f"NOT SCORED: {'; '.join(problems)}", would_be=verdict)
    else:
        out["verdict"] = verdict
    return out


def note(result: dict) -> str:
    s = result["score"]
    lines = [f"# R1 stage 1 run note ({'SEALED' if result['sealed'] else 'UNSEALED, plumbing only'})", "",
             f"Verdict: **{s['verdict']}**" + (f" (would be {s['would_be']})" if "would_be" in s else ""), ""]
    if "rows" in s:
        lines += ["| seed | order | T* s | loss A0 | loss A1 | d | acc A0 | acc A1 | recall A0 | recall A1 |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        fmt = lambda v: "n/a" if v is None else f"{v:.4f}"                          # noqa: E731
        for r in s["rows"]:
            lines.append(f"| {r['seed']} | {','.join(r['order'])} | {r['t_star']:.1f} | {r['loss_A0']:.4f} | "
                         f"{r['loss_A1']:.4f} | {r['d']:+.4f} | {fmt(r['accuracy'][0])} | {fmt(r['accuracy'][1])} | "
                         f"{fmt(r['recall_at_4'][0])} | {fmt(r['recall_at_4'][1])} |")
        lines += ["", f"mean d {s['mean_d']:+.4f}, 2SE band {s['lower']:+.4f} to {s['upper']:+.4f}, "
                  f"{s['seeds_positive']}/{len(s['d'])} positive, relative {s['relative_effect']:+.2%}; "
                  f"G-ACC trip {s['G_ACC']['trip']}, G-RET trip {s['G_RET']['trip']}"]
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------- copy-off
def write_manifest(out: Path) -> Path:
    """sha256sum-style lines for every file under `out` (the manifest itself aside)."""
    lines = [f"{sha256(p)}  {p.relative_to(out).as_posix()}" for p in sorted(out.rglob("*"))
             if p.is_file() and p.name != MANIFEST and not p.name.endswith(".tmp")]
    (out / MANIFEST).write_text("\n".join(lines) + "\n")
    return out / MANIFEST


def verify(out: Path) -> list[str]:
    """Files missing or changed against the manifest (empty when the copy is whole)."""
    bad = []
    for line in (out / MANIFEST).read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        path = out / name
        if not path.is_file() or sha256(path) != digest:
            bad.append(name)
    return bad


# ----------------------------------------------------------------------------- commands
def run_all(*, budget, data_rel: str, tokenizer_path: str, settings: dict, seeds, out: Path, unsealed: bool,
            log, extra: dict | None = None) -> dict:
    ident = identity()
    sealed = check_seal(out, ident, unsealed)
    for seed in seeds:
        for arm in arm_order(seed):
            path = out / f"{arm}-s{seed}.json"
            data = {**data_identity(budget, data_rel, tokenizer_path), **(extra or {})}
            if path.exists():
                saved = json.loads(path.read_text())
                bound = saved.get("bound", {})
                if saved.get("settings") != settings or bound.get("code") != ident or \
                        {k: bound.get("data", {}).get(k) for k in data} != data:
                    raise SystemExit(f"{path} was made with other settings, code or data; use a new --out")
                log(f"{arm} s{seed}: reusing {path.name}")
                continue
            write_json(path, run(arm, seed, budget=budget, data_rel=data_rel, tokenizer_path=tokenizer_path,
                                 settings=settings, out=out, bound={"code": ident, "data": data}, log=log))
    runs = [json.loads((out / f"{arm}-s{seed}.json").read_text()) for seed in seeds for arm in ARMS]
    result = {"sealed": sealed, "identity": ident, "settings": settings, "score": score(runs, sealed=sealed, ident=ident),
              "runs": [{k: v for k, v in r.items() if k not in ("curve", "evals", "windows")} for r in runs]}
    write_json(out / "RESULT.json", result)                    # the only writer of RESULT.json
    (out / "RUN-NOTE.md").write_text(note(result))
    log(f"verdict: {result['score']['verdict']}")
    return result


def data_identity(budget, data_rel: str, tokenizer_path: str) -> dict:
    return {"data_rel": data_rel, "tokenizer": sha256(Path(budget.root) / tokenizer_path)}


def logger(out: Path):
    handle = (out / "log.txt").open("a")

    def log(line: str) -> None:
        print(line, flush=True)
        handle.write(line + "\n")
        handle.flush()
    return log


def make_budget(root: Path, hard_gb: float):
    from memorylab.storage import Budget
    return Budget(root, hard=int(hard_gb * 1e9), steady=int(hard_gb * 0.8e9))


def cmd_build(args) -> None:
    """The card's village build (step 1, `large`, seed 0) under --root; prints the data_rel to pass to `run`."""
    from learnlab import step1
    budget = make_budget(args.root, args.hard_gb)
    data = step1.build_data(budget, visits=BUILD["visits"], seed=BUILD["seed"], workers=args.workers)
    print(json.dumps({"data_rel": data.rel, "tag": data.tag, "seconds": data.seconds}))


def cmd_run(args) -> None:
    """The card (F from `--price`, sealed directory) or a plumbing run (`--flop-budget`, `--unsealed`)."""
    if sum(x is not None and x is not False for x in (args.price, args.flop_budget, args.timing)) != 1:
        raise SystemExit("pass exactly one of --price (the card's F), --timing (stage 1a) and --flop-budget (plumbing)")
    if args.flop_budget is not None and not args.unsealed:
        raise SystemExit("--flop-budget is for plumbing runs only; add --unsealed")
    settings = dict(CARD_SETTINGS)
    extra = {}
    if args.timing:                                  # stage 1a: unsealed, F_1a, seed 0
        settings = timing_settings()
        args.unsealed, args.seeds = True, [0]
    elif args.price is not None:
        price_file = json.loads(args.price.read_text())
        check_price(price_file)
        if args.timing_from is None:
            raise SystemExit("--price needs --timing-from (stage 1a's directory) to re-check F")
        check_price_source(price_file, args.timing_from)
        settings["flop_budget"] = price_file["flop_budget"]
        extra["price"] = sha256(args.price)
    else:
        settings["flop_budget"] = args.flop_budget
    args.out.mkdir(parents=True, exist_ok=True)
    log = logger(args.out)
    log(f"R1 stage 1 start {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {provenance()} settings {settings}")
    run_all(budget=make_budget(args.root, args.hard_gb), data_rel=args.data_rel, tokenizer_path=args.tokenizer,
            settings=settings, seeds=args.seeds, out=args.out, unsealed=args.unsealed, log=log, extra=extra)
    print(write_manifest(args.out))


def cmd_price(args) -> None:
    """Stage 1b's F from stage 1a's run JSONs (--from), the box's $/h and the box seconds spent so far; writes
    PRICE.json. Exit 0: go; 3: 1a's gate failed; 4: even F_min does not fit (PRICE.json is written either way)."""
    arms = [json.loads((args.source / f"{arm}-s0.json").read_text()) for arm in ARMS]
    result = price(arms, dph=args.dph, spent_seconds=args.spent_seconds, seconds_left=args.seconds_left,
                   ident=identity())
    result["from"] = {f"{arm}-s0.json": sha256(args.source / f"{arm}-s0.json") for arm in ARMS}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.out, result)
    print(json.dumps(result, indent=1))
    if not result["go"]:
        raise SystemExit(3 if not result["gate_1a"]["muon_step_ratio_ok"] else 4)


def cmd_dry(args) -> None:
    """P3: the whole pipeline on a tiny generated village, CPU, tiny preset; never a card verdict."""
    from learnlab import step1
    from learnlab.tokenizer import Tokenizer
    from learnlab.village.names import SYLLABLES
    from learnlab.village.shards import write_shards
    args.out.mkdir(parents=True, exist_ok=True)
    if any(args.out.iterdir()):
        raise SystemExit(f"{args.out} is not empty; the dry run needs a fresh directory")
    for split, count in (("train", 48), ("validation", 16)):
        write_shards(split, count, args.out / "data" / "v", 1, seed=0, visits_per_shard=8, verbose=False)
    texts = [p.read_text(encoding="utf-8") for p, _ in step1.shard_files(args.out / "data" / "v" / "train")]
    Tokenizer.train(texts, vocab_size=1200, syllables=SYLLABLES).save(args.out / "tok.json")
    settings = dict(CARD_SETTINGS, size="tiny", device="cpu", lr=3e-3, flop_budget=args.flop_budget,
                    warmup_steps=2, max_tokens=4000, max_visits=8, log_every=2, eval_every=4, eval_visits=8,
                    calibration_batches=2)
    run_dir = args.out / "run"
    run_dir.mkdir()
    torch.set_num_threads(1)
    result = run_all(budget=make_budget(args.out, 10), data_rel="data/v", tokenizer_path="tok.json",
                     settings=settings, seeds=CARD_SEEDS, out=run_dir, unsealed=True, log=logger(run_dir))
    write_manifest(run_dir)
    bad = verify(run_dir)
    print(json.dumps({"verdict": result["score"]["verdict"], "manifest_ok": not bad}, indent=1))


def cmd_verify(args) -> None:
    bad = verify(args.out)
    print("manifest OK" if not bad else f"MISSING OR CHANGED: {bad}")
    raise SystemExit(1 if bad else 0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--root", type=Path, required=True)
    build.add_argument("--workers", type=int, default=8)
    build.add_argument("--hard-gb", type=float, default=50)
    build.set_defaults(fn=cmd_build)
    go = sub.add_parser("run")
    go.add_argument("--root", type=Path, required=True)
    go.add_argument("--data-rel", required=True)
    go.add_argument("--tokenizer", default="data/tokenizer/premonition-tok-v2.json")
    go.add_argument("--out", type=Path, required=True)
    go.add_argument("--seeds", type=int, nargs="+", default=list(CARD_SEEDS))
    go.add_argument("--price", type=Path, default=None, help="PRICE.json from `price`: the card's F")
    go.add_argument("--flop-budget", type=float, default=None, help="plumbing runs only (--unsealed)")
    go.add_argument("--timing", action="store_true", help="stage 1a: the card's settings at F_1a, seed 0, unsealed")
    go.add_argument("--timing-from", type=Path, default=None, help="with --price: stage 1a's directory")
    go.add_argument("--hard-gb", type=float, default=50)
    go.add_argument("--unsealed", action="store_true")
    go.set_defaults(fn=cmd_run)
    cost = sub.add_parser("price")
    cost.add_argument("--from", dest="source", type=Path, required=True, help="stage 1a's run directory")
    cost.add_argument("--dph", type=float, required=True, help="the booked box's $/h")
    cost.add_argument("--spent-seconds", type=float, required=True,
                      help="box seconds billed so far (the job's elapsed time plus its pre-job allowance)")
    cost.add_argument("--seconds-left", type=float, required=True, help="seconds left before the job's run deadline")
    cost.add_argument("--out", type=Path, required=True)
    cost.set_defaults(fn=cmd_price)
    dry = sub.add_parser("dry")
    dry.add_argument("--out", type=Path, required=True)
    dry.add_argument("--flop-budget", type=float, default=2e11)
    dry.set_defaults(fn=cmd_dry)
    check = sub.add_parser("verify")
    check.add_argument("--out", type=Path, required=True)
    check.set_defaults(fn=cmd_verify)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
