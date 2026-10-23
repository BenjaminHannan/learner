"""V1 assembly runner: one arm (floor | full), WAKE then SLEEP, resumable, with the abort rules A1-A5 applied mechanically.

  python -m v1.run --arm floor|full --root DATA_ROOT --out OUT --b2 B2_CKPT --skills SKILLS_DIR [--steps N] [--device cuda]

FLOOR = D (d128, AdamW) + creative d256 + one projection each way + sleep + G1(KL 30).
FULL  = FLOOR + Muon on D's 2-D hidden matrices + S2 (decoder_raw_cards).  Defer is OFF in both (default; v1/PARAMS).
Same data, seed and steps for both arms. The sealed splits (village `test`, creative `test.jsonl`) are not opened here.
"""
from __future__ import annotations

import os as _os
if "--deterministic" in __import__("sys").argv:
    _os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
_os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")      # less allocator fragmentation: 'reserved' tracks 'allocated'
import argparse
import collections
import json
import os
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import torch

from learnlab import step1
from premonition import data as pdata
from premonition.config import MiniConfig
from premonition.model import PremonitionMini
from premonition.train import Curriculum, mini_config_dict, mini_train_config, planned_loops, validate, validation_hook
from v1 import baselines, ckpt as vckpt, dtrain, g1 as g1mod, guard as vguard
from v1.joint import Bridge

SEED = 0
# --- fixed training constants (V1_PARAMS.md) ---
MAX_TOKENS = 55_000            # tokens per D batch (premonition.train.train_d default)
MAX_VISITS = 48
LR = 1e-3
WARMUP = 100
CKPT_FRACTION = 0.05
EVAL_FRACTION = 0.05
B2_BATCH = 16                  # skills rows per wake step that train P_dc (creative weights are frozen in wake)
BRIDGE_LR = 1e-3
DEV_EVAL_VISITS = 512

log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


@dataclass
class Arm:
    name: str
    muon: bool
    s2: bool
    defer: bool = False


ARMS = {"floor": Arm("floor", False, False), "full": Arm("full", True, True)}


def build_d(arm: Arm, vocab_size: int) -> PremonitionMini:
    torch.manual_seed(SEED)
    cfg = MiniConfig.preset("D", "full", vocab_size=vocab_size, decoder_raw_cards=arm.s2)
    return PremonitionMini(cfg)


def load_creative(ckpt: str, device: str):
    from creative import sleep
    m, vocab, meta = sleep.load_parent(ckpt, device)
    for p in m.parameters():
        p.requires_grad_(False)          # wake: the creative weights stay at the parent; only P_dc trains (design: JOINT-DESIGN)
    m.eval()
    return m, vocab, meta


class AbortRule(RuntimeError):
    def __init__(self, rule: str, why: str) -> None:
        super().__init__(f"{rule}: {why}")
        self.rule, self.why = rule, why


class Monitor:
    """A1 and A2 on the wake loss stream; A4 on spend (persisted across restarts). Pure functions of what is logged.
    A1's 'running median' is taken over the previous 200 steps of the SAME curriculum phase (the loss changes definition between the
    gold, teacher and own phases); the 1% is counted over all steps so far (needs >= 300)."""

    def __init__(self, total_steps: int, price_per_hour: float, spend_cap: float, ledger: Path) -> None:
        self.total, self.price, self.cap, self.ledger = total_steps, price_per_hour, spend_cap, Path(ledger)
        self.by_phase: dict[str, list[float]] = collections.defaultdict(list)
        self.n = 0
        self.bad = 0
        self.dev_loss0: Optional[float] = None
        prior = json.loads(self.ledger.read_text()) if self.ledger.exists() else {}
        self.elapsed_before = float(prior.get("elapsed_s", 0.0))      # wall seconds spent by earlier processes of this arm
        self.t0 = time.time()

    def elapsed(self) -> float:
        return self.elapsed_before + (time.time() - self.t0)

    def save(self) -> None:
        self.ledger.write_text(json.dumps({"elapsed_s": self.elapsed(), "price_per_hour": self.price, "usd": self.usd()}))

    def usd(self) -> float:
        return self.elapsed() / 3600.0 * self.price

    def check_spend(self) -> None:                                                  # A4 (wake steps and sleep stage boundaries)
        if self.price and self.usd() >= self.cap:
            self.save()
            raise AbortRule("A4", f"spend cap ${self.cap:.2f} reached (${self.usd():.2f})")

    def on_step(self, step: int, loss: float, phase: str = "own") -> None:
        window = self.by_phase[phase][-200:]
        if len(window) >= 50 and loss > 3.0 * statistics.median(window):          # A1: > 3x the running median
            self.bad += 1
        self.by_phase[phase].append(loss)
        self.n += 1
        if self.n >= 300 and self.bad / self.n > 0.01:                              # A1: for more than 1% of steps
            raise AbortRule("A1", f"loss above 3x its running median on {self.bad}/{self.n} steps (> 1%)")
        self.check_spend()

    def check_a2(self, step: int, dev_loss: float) -> None:
        if step >= int(0.10 * self.total) and self.dev_loss0 is not None and dev_loss > 0.75 * self.dev_loss0:
            raise AbortRule("A2", f"dev loss {dev_loss:.4f} has not dropped 25% from step 0 ({self.dev_loss0:.4f}) at step {step}")


@torch.no_grad()
def dev_loss(trainer: dtrain.StepTrainer, batches, n: int = 8) -> float:
    """Mean teacher-mode training loss over n fixed dev batches (A2's 'dev loss'); no gradient, no state change."""
    model, vals = trainer.model, []
    was = model.training
    model.eval()
    gen = torch.Generator(device=trainer.device).manual_seed(1234)
    for b in batches[:n]:
        out = model(b.to(trainer.device), mode="teacher", p_own=0.0, generator=gen)
        vals.append(float(out["loss"]))
    model.train(was)
    return sum(vals) / len(vals)


def make_eval_batches(cache, n_visits: int, tokenizer) -> tuple[list, list[int]]:
    chosen = list(range(min(n_visits, len(cache))))
    groups = pdata.length_batches(cache.lengths[chosen].tolist(), MAX_TOKENS, max_visits=MAX_VISITS)
    return [pdata.collate(cache, [chosen[i] for i in g]) for g in groups], sorted(step1.stop_ids(tokenizer)[0])


DIAG_KEYS = ("by_depth", "accuracy_gold_cards", "own_minus_gold_cards", "loops_mean_gold_cards", "halt_rate", "asked_rate",
             "gold_any_at_4", "random_recall_at_4")


def diag_fields(r: dict[str, Any], cards: bool = False) -> dict[str, Any]:
    """The validate() diagnostics that used to be computed and dropped (reporting only; `cards` is the bulky per-card summary)."""
    out = {k: r[k] for k in DIAG_KEYS if k in r}
    if cards and r.get("cards") is not None:
        out["cards"] = r["cards"]
    return out


def write_per_question(rows: list, path: Path) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def make_evaluator(trainer, bridge: Bridge, hook, eval_batches, val_hook=None, bridge_off: bool = False):
    """The periodic eval. Bridge summaries are frozen throughout. The base fields are the old ones plus the full validate()
    diagnostics; the extras (validation split, bridge-off lesion) run under a saved/restored RNG state and restore bridge.enabled, so
    they cannot move the training RNG, the bridge or the weights."""
    def evaluate(model):
        bridge.frozen_ctx = True               # dev data never moves the bridge summaries (dev_loss included)
        try:
            res = hook(model)
            dl = dev_loss(trainer, eval_batches)
            out = {"accuracy": res["accuracy"], "questions": res["questions"], "loops_mean": res["loops_mean"],
                   "gold_recall_at_4": res.get("gold_recall_at_4"), "dev_loss": dl, **diag_fields(res)}
            if bridge_off or val_hook is not None:
                state, was = vckpt.rng_state(), bridge.enabled
                try:
                    if bridge_off:
                        bridge.enabled = False
                        r0 = hook(model)
                        out["bridge_off"] = {"accuracy": r0["accuracy"], "loops_mean": r0["loops_mean"], **diag_fields(r0)}
                    bridge.enabled = True
                    if val_hook is not None:
                        rv = val_hook(model)
                        out.update(val_accuracy=rv["accuracy"], val_questions=rv["questions"], val_loops_mean=rv["loops_mean"],
                                   val_gold_recall_at_4=rv.get("gold_recall_at_4"), **{f"val_{k}": v for k, v in diag_fields(rv).items()})
                finally:
                    bridge.enabled = was
                    vckpt.set_rng_state(state)
        finally:
            bridge.frozen_ctx = False
        return out
    return evaluate


def component_ran(arm: Arm, trainer, bridge: Bridge, d_model, b2, guard_logs: dict) -> dict[str, Any]:
    """Gate S item 3: every component whose flag is on proves its code executed."""
    rep: dict[str, Any] = {"arm": arm.name}
    cfgd = d_model.config
    rep["S2"] = {"flag": bool(cfgd.decoder_raw_cards), "raw_card_rows": cfgd.cards if cfgd.decoder_raw_cards else 0}
    g = trainer.optimizer_grouping()
    rep["muon_groups"] = {"flag": arm.muon, "optimizer": g["optimizer"],
                          "muon_tensors": sum(x["n_tensors"] for x in g["groups"] if x["muon"]),
                          "adamw_tensors": sum(x["n_tensors"] for x in g["groups"] if not x["muon"])}
    rep["bridge"] = bridge.stats()
    rep["g1"] = guard_logs
    return rep


def load_plans(root, name: str) -> dict:
    """question id -> plan world for the dev / validation split dir (`step1.load_oracle`; {} without an oracle index).
    Only non-sealed dirs: `name` must be dev or validation."""
    if name not in ("dev", "validation"):
        raise ValueError(f"plans are loaded for dev/validation only, not {name!r}")
    return step1.load_oracle(Path(root) / name)[1]


def final_eval(arm: Arm, d_model, bridge: Bridge, data, out: Path, a, steps: int, aborted: Optional[dict] = None) -> dict[str, Any]:
    """Dev numbers for the decision rule (never the sealed splits): D on all 5,000 DEV visits and the 1,000 `validation` visits,
    the creative first-try on creative DEV (latest finished creative stage), the bridge-off lesion of each, W1/W2 pass on dev, and
    the KL-share summary. After an abort it judges the last checkpoint (`aborted` carries the rule)."""
    from creative import rules_real
    from v1 import creative_sleep
    from v1.creative_baselines import creative_baselines
    res: dict[str, Any] = {"arm": arm.name, "steps": steps, "aborted": aborted}
    bridge.frozen_ctx = True
    for name, cache in (("dev", data.dev), ("validation", data.validation)):
        batches, stops = make_eval_batches(cache, getattr(a, "final_visits", None) or len(cache), data.tokenizer)
        plans = load_plans(a.root, name) if getattr(a, "plan_scoring", False) else None
        rows_on, rows_off = ([] if getattr(a, "per_question", False) else None for _ in range(2))
        bridge.enabled = True
        r = validate(d_model, batches, tokenizer=data.tokenizer, stop=stops, plans=plans, per_question=rows_on)
        res[f"d_{name}"] = {"accuracy": r["accuracy_exact"], "questions": r["questions"], "gold_recall_at_4": r.get("gold_recall_at_4"),
                            "loops_mean": r["loops_mean"], **diag_fields(r, cards=True)}  # "accuracy" stays exact match: the frozen decision rule reads it
        if plans is not None:
            res[f"d_{name}"].update({k: r[k] for k in ("q12_questions", "q12_exact", "q12_plan_checked", "q12_accuracy_exact",
                                                       "q12_accuracy_plan_checked")}, accuracy_plan_checked=r["accuracy"],
                                    plan_worlds=len(plans))
        bridge.enabled = False
        r0 = validate(d_model, batches, tokenizer=data.tokenizer, stop=stops, plans=plans, per_question=rows_off)
        bridge.enabled = True
        res[f"d_{name}"]["bridge_off_accuracy"] = r0["accuracy_exact"]
        res[f"d_{name}"]["bridge_off"] = {"accuracy": r0["accuracy_exact"], "loops_mean": r0["loops_mean"], **diag_fields(r0, cards=True)}
        if plans is not None:
            res[f"d_{name}"]["bridge_off_accuracy_plan_checked"] = r0["accuracy"]
        if rows_on is not None:
            write_per_question(rows_on, out / f"per_question_{name}_bridge_on.jsonl")
            write_per_question(rows_off, out / f"per_question_{name}_bridge_off.jsonl")
    base = baselines.baselines(data.train, data.dev)
    res["baseline_dev"] = base
    res["W1_dev_threshold"] = base["best"] + 0.10
    res["W1_dev_pass"] = res["d_dev"]["accuracy"] >= res["W1_dev_threshold"]
    for name in ("W2.pt", "W1.pt", "Nprime.pt", "warm.pt"):
        mp = out / "creative" / name
        if mp.exists():
            c = creative_sleep.dev_report(str(mp), a.device, attach=bridge.attach_creative)
            bridge.enabled = False
            c0 = creative_sleep.dev_report(str(mp), a.device, attach=bridge.attach_creative)
            bridge.enabled = True
            res["creative_dev"] = {**c, "bridge_off_first_try": c0["first_try"], "model": name}
            res["W2_dev_pass"] = c["first_try"] >= 0.20 and name == "W2.pt"
            break
    if "creative_dev" in res:              # reporting only: no-learning baselines on creative dev; W2_dev_pass above is unchanged
        res["creative_baselines"] = creative_baselines(rules_real.load_split(creative_sleep.DATA, "dev"))
    tj = out / "creative" / "train.json"
    if tj.exists():
        ti = json.loads(tj.read_text())
        res["kl_share"] = {k: v.get("kl_share_mean_after_25pct") for k, v in ti.get("phases", {}).items()}
    return res


def restore_last(trainer, bridge, bopt, ck_dir: Path, load_opt: bool = True) -> Optional[int]:
    got = vckpt.load(ck_dir)
    if got is None:
        return None
    if load_opt:
        trainer.restore(got)
    else:                                  # A1 relaunch with AdamW: weights, counters and RNG only; a fresh optimizer
        trainer.model.load_state_dict(got["model"])
        trainer.load_state_dict(got["trainer"])
        vckpt.set_rng_state(got["rng"])
    bridge.load_state_dict(got["bridge"])
    if load_opt:
        bopt.load_state_dict(got["bridge_opt"])
    return int(got["step"])


def save_final(trainer, d_model, bridge, bopt, arm, out: Path, ck_dir: Path) -> None:
    payload = trainer.checkpoint_payload()
    payload.update(bridge=bridge.state_dict(), bridge_opt=bopt.state_dict())
    vckpt.save(ck_dir, trainer.step, payload)
    torch.save({"model": d_model.state_dict(), "config": mini_config_dict(d_model.config), "bridge": bridge.state_dict(),
                "arm": arm.name, "steps": trainer.step}, out / "D-final.pt")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=sorted(ARMS), required=True)
    ap.add_argument("--root", required=True, help="village data root (train/dev/validation; the sealed `test` dir is never read)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--b2", required=True, help="creative parent checkpoint (the one fixed in V1_PARAMS)")
    ap.add_argument("--skills", required=True, help="skills build dir (train.jsonl + dev/) with the hash-checked 200k seed-1 build")
    ap.add_argument("--tokenizer", default=str(Path(__file__).resolve().parent.parent / "data/tokenizer/premonition-tok-v2.json"))
    ap.add_argument("--steps", type=int, default=12_000)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--price-per-hour", type=float, default=0.0, help="box $/h; with --spend-cap it is rule A4 (the arm jobs always pass it)")
    ap.add_argument("--spend-cap", type=float, default=20.0)
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--no-sleep", action="store_true")
    ap.add_argument("--eval-visits", type=int, default=DEV_EVAL_VISITS, help="dev visits per periodic eval (tests use fewer)")
    ap.add_argument("--val-every-eval", action=argparse.BooleanOptionalAction, default=True,
                    help="also score the held-out `validation` split at every periodic eval (reporting only: RNG, bridge and weights restored)")
    ap.add_argument("--val-visits", type=int, default=None, help="validation visits per periodic eval (default all)")
    ap.add_argument("--eval-bridge-off", action=argparse.BooleanOptionalAction, default=True,
                    help="also score the dev subset with the bridge off at every periodic eval (reporting only)")
    ap.add_argument("--per-question", action="store_true", help="final eval also writes per_question_{split}_bridge_{on,off}.jsonl")
    ap.add_argument("--lr-schedule", choices=sorted(dtrain.LR_SCHEDULES), default="constant",
                    help="D's LR after warmup: constant (v1) or wsd = warmup-stable-decay applied to every param group")
    ap.add_argument("--wsd-stable-frac", type=float, default=dtrain.WSD_STABLE_FRAC, help="wsd: fraction of steps held at the base LR")
    ap.add_argument("--wsd-final-frac", type=float, default=0.0, help="wsd: LR at the last step as a fraction of the base LR")
    ap.add_argument("--ckpt-every", type=int, default=None, help="override the 5%%-of-steps checkpoint interval (tests only)")
    ap.add_argument("--eval-every", type=int, default=None, help="override the 5%%-of-steps dev-eval interval (tests only)")
    ap.add_argument("--stop-after", type=int, default=None, help="testing only: stop the wake loop after this many steps")
    ap.add_argument("--sleep-cap", type=int, default=None, help="testing only: cap every sleep stage's updates")
    ap.add_argument("--pool-limit", type=int, default=None, help="testing only")
    ap.add_argument("--dev-limit", type=int, default=None, help="testing only")
    ap.add_argument("--diary", type=int, default=g1mod.DIARY_SIZE, help="testing only: G1 diary size (the arms use 4096)")
    ap.add_argument("--final-visits", type=int, default=None, help="testing only: score only this many dev/validation visits at the end")
    ap.add_argument("--g1-norm", choices=list(g1mod.NORMS), default="none",
                    help="G1 K-FAC G normalisation: none = v1 as frozen (empirical G); example = the L14 NK30 recipe (design/v1/g1-ablate/PREREG.md)")
    ap.add_argument("--no-g1", action="store_true", help="creative sleep without G1 (the g1_off control); off = v1 as frozen")
    ap.add_argument("--sleep-retention", action="store_true", help="after each sleep night score skills5 + creative dev and record them in sleep-done.json; off = v1 as frozen")
    ap.add_argument("--plan-scoring", action="store_true", help="final eval also reports plan-checked accuracy (Q12 plans the oracle accepts count); off = v1 as frozen")
    ap.add_argument("--deterministic", action="store_true", help="torch deterministic algorithms (warn only) + fixed cuBLAS workspace: the resume re-run")
    ap.add_argument("--ack-abort", action="store_true", help="continue after an abort file exists (A1 relaunch / a recorded deviation)")
    ap.add_argument("--relaunch-adamw", action="store_true", help="A1 relaunch for FULL: resume the last good checkpoint with plain AdamW")
    a = ap.parse_args(argv)
    if a.deterministic:
        torch.use_deterministic_algorithms(True, warn_only=True)
    arm = ARMS[a.arm]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    abort_file = out / "ABORT.json"
    if abort_file.exists():
        if not a.ack_abort:
            log("REFUSED: ABORT.json exists (an abort rule fired); rerun with --ack-abort only as a recorded deviation:", abort_file.read_text())
            return 3
        n = len(list(out.glob("ABORT-*.json"))) + 1
        abort_file.rename(out / f"ABORT-{n}.json")
        (out / "deviation.json").write_text(json.dumps({"ack_abort": n, "relaunch_adamw": a.relaunch_adamw, "at": time.strftime("%FT%TZ")}))
    device = torch.device(a.device)
    data = dtrain.open_data(Path(a.root), Path(a.tokenizer), workers=a.workers, log=lambda s: None)
    d_model = build_d(arm, data.tokenizer.vocab_size)
    b2, b2_vocab, b2_meta = load_creative(a.b2, a.device)
    d_model.to(device)
    b2.to(device)
    bridge = Bridge(d_model.config.d_model, b2.d).to(device).attach(d_model, b2)
    bopt = torch.optim.AdamW(bridge.parameters(), lr=BRIDGE_LR, weight_decay=0.0)
    tc = mini_train_config(lr=LR, warmup_steps=WARMUP, log_every=50, memory_check_every=50)
    use_muon = arm.muon and not a.relaunch_adamw
    trainer = dtrain.StepTrainer(d_model, tc, device, total_steps=a.steps, seed=SEED, optimizer="muon" if use_muon else "adamw",
                                 lr_schedule=a.lr_schedule, wsd_stable_frac=a.wsd_stable_frac, wsd_final_frac=a.wsd_final_frac)
    grouping = trainer.optimizer_grouping()
    log("optimizer grouping:", json.dumps({k: (v if k != "groups" else [{kk: vv for kk, vv in g.items() if kk != "names"} for g in v])
                                         for k, v in grouping.items()}))
    (out / "grouping.json").write_text(json.dumps(grouping, indent=1))
    ck_dir = out / "wake-ckpt"
    got = restore_last(trainer, bridge, bopt, ck_dir, load_opt=not a.relaunch_adamw)
    if got is not None:
        log(f"RESUMED from step {got}" + (" with a fresh AdamW (A1 relaunch)" if a.relaunch_adamw else ""))
    eval_batches, stops = make_eval_batches(data.dev, a.eval_visits, data.tokenizer)
    hook = validation_hook(eval_batches, tokenizer=data.tokenizer, stop=stops)

    val_hook = None
    if a.val_every_eval:                       # held-out curve, reporting only (see make_evaluator); fixed visits, same hook
        val_batches, _ = make_eval_batches(data.validation, a.val_visits or len(data.validation), data.tokenizer)
        val_hook = validation_hook(val_batches, tokenizer=data.tokenizer, stop=stops)
    evaluate = make_evaluator(trainer, bridge, hook, eval_batches, val_hook, bridge_off=a.eval_bridge_off)

    mon = Monitor(a.steps, a.price_per_hour, a.spend_cap, out / "spend.json")
    evals_path = out / "dev_evals.jsonl"
    if trainer.step == 0 and not (out / "dev_loss0.json").exists():
        e0 = evaluate(d_model)
        mon.dev_loss0 = e0["dev_loss"]
        evals_path.open("a").write(json.dumps({"step": 0, **e0}) + "\n")
        (out / "dev_loss0.json").write_text(json.dumps({"dev_loss0": mon.dev_loss0}))
    else:
        mon.dev_loss0 = json.loads((out / "dev_loss0.json").read_text())["dev_loss0"]
    from custom_io.data import Dataset, collate, load_rows, to_device
    skills_rows = load_rows(os.path.join(a.skills, "train.jsonl"))          # all 200,000 rows (the file is ordered by stage)
    ckpt_every = a.ckpt_every or max(1, int(CKPT_FRACTION * a.steps))
    eval_every = a.eval_every or max(1, int(EVAL_FRACTION * a.steps))
    stream = dtrain.train_stream(data.train, a.max_tokens, SEED, trainer.step, MAX_VISITS)

    def b2_step() -> float:
        rows = __import__("random").Random(f"{SEED}-b2-{trainer.step}").sample(skills_rows, B2_BATCH)   # a function of the step: exact resume
        batch = to_device(collate([Dataset(rows, b2_vocab, strict=False)[i] for i in range(len(rows))]), a.device)
        loss, _ = b2.loss(batch)
        loss.backward()                 # gradient reaches P_dc only (creative weights are frozen)
        return float(loss.detach())

    def finish_after_abort(ar: AbortRule, phase: str) -> int:
        abort_file.write_text(json.dumps({"rule": ar.rule, "why": ar.why, "step": trainer.step, "phase": phase}))
        log("ABORT", ar)
        mon.save()
        try:                                   # "stop, judge the last checkpoint" (A4: "evaluate the last checkpoint as v1")
            if phase == "wake":
                step_back = restore_last(trainer, bridge, bopt, ck_dir)
                if step_back is None:
                    log("no checkpoint to judge (aborted before the first one)")
                    return 3
                save_final(trainer, d_model, bridge, bopt, arm, out, ck_dir)
            fin = final_eval(arm, d_model, bridge, data, out, a, trainer.step, aborted={"rule": ar.rule, "why": ar.why, "phase": phase})
            (out / "final_dev.json").write_text(json.dumps(fin, indent=1, default=float))
        except Exception as error:             # never let the judging hide the abort itself
            log("judging the last checkpoint failed:", repr(error))
        return 3

    d_model.train()
    first = trainer.step
    t_wake, tok_wake = time.time(), 0
    try:
        while trainer.step < a.steps:
            if a.stop_after is not None and trainer.step - first >= a.stop_after:
                break
            bopt.zero_grad(set_to_none=False)
            batch = next(stream)
            plan = trainer.plan()
            loops = planned_loops(batch, plan.mode, d_model.config)
            res = trainer._train_step(batch, plan, loops, (trainer.step + 1) % tc.log_every == 0)
            lb = b2_step()
            torch.nn.utils.clip_grad_norm_(bridge.parameters(), 1.0)
            bopt.step()
            trainer.tokens += int(batch.lengths.sum())
            tok_wake += int(batch.lengths.sum())
            loss = float(res["loss"])
            if loss != loss or loss in (float("inf"), float("-inf")):
                raise AbortRule("A1", f"non-finite loss at step {trainer.step}")
            mon.on_step(trainer.step, loss, plan.phase)
            with (out / "losses.jsonl").open("a") as lf:
                lf.write(json.dumps({"step": trainer.step, "loss": loss, "b2_loss": lb, "lm": float(res["lm"]), "ans": float(res["ans"]),
                                     "phase": plan.phase}) + "\n")
            if trainer.step == first + 1 or trainer.step % tc.memory_check_every == 0:
                vguard.check(device, trainer.guard_limit)
            if trainer.step % tc.log_every == 0:
                peak = torch.cuda.max_memory_reserved(device) / 2 ** 30 if device.type == "cuda" else 0.0
                log(f"step {trainer.step}/{a.steps} {plan.phase} loss {loss:.4f} b2_loss {lb:.4f} tok/s {tok_wake / max(time.time() - t_wake, 1e-9):,.0f} "
                    f"peak {peak:.2f} GiB usd {mon.usd():.2f} bridge {json.dumps(bridge.stats())}")
            if trainer.step % eval_every == 0:
                e = evaluate(d_model)
                evals_path.open("a").write(json.dumps({"step": trainer.step, **e}) + "\n")
                log("DEV", json.dumps(e))
                mon.check_a2(trainer.step, e["dev_loss"])
            if trainer.step % ckpt_every == 0:
                payload = trainer.checkpoint_payload()
                payload.update(bridge=bridge.state_dict(), bridge_opt=bopt.state_dict())
                vckpt.save(ck_dir, trainer.step, payload)
                mon.save()
    except AbortRule as ar:
        return finish_after_abort(ar, "wake")
    wall = max(time.time() - t_wake, 1e-9)
    if trainer.step >= a.steps:
        save_final(trainer, d_model, bridge, bopt, arm, out, ck_dir)
    mon.save()
    (out / "wake-done.json").write_text(json.dumps({
        "steps": trainer.step, "lr_schedule": a.lr_schedule, "steps_this_process": trainer.step - first, "bridge": bridge.stats(), "tokens_per_s": tok_wake / wall, "wall_s": wall,
        "peak_gpu_reserved_gib": (torch.cuda.max_memory_reserved(device) / 2 ** 30) if device.type == "cuda" else None,
        "guard_limit_gib": trainer.guard_limit / 2 ** 30, "device": str(device),
        "card": torch.cuda.get_device_name(device) if device.type == "cuda" else "cpu"}))
    if a.no_sleep or (a.stop_after is not None):
        return 0
    # ---- SLEEP: the creative module, C2b's W path with G1 ----
    from v1 import creative_sleep
    log("SLEEP starts (G1 on)")
    for p in b2.parameters():
        p.requires_grad_(True)
    b2.train()
    raw_ckpt = a.b2
    skills_train = os.path.join(a.skills, "train.jsonl")

    def g1_factory(raw, replay):
        parent = g1mod.frozen_copy(raw)
        diary = g1mod.build_diary(parent, replay, n=a.diary, seed=SEED, device=a.device)
        return g1mod.G1(parent, diary, raw.vocab, device=a.device, seed=SEED, norm=a.g1_norm)

    bridge.frozen_ctx = True            # D is not training in sleep: the summaries stay as wake left them, P_dc/P_cd are frozen
    stage_dev: dict[str, float] = {}

    def on_stage(name, info_):
        mon.check_spend()                                                           # A4 at every sleep stage boundary
        # A3, applied at the end of the first two G1-active phases (warm-up, N'): mean KL-term share of total loss after the first 25% of
        # the phase > 50% AND creative dev first-try up < 1 point over the phase -> stop and judge the last checkpoint. Re-applied on a restart.
        f = {"warmup": "warm.pt", "Nprime": "Nprime.pt"}.get(name)
        if f is None:
            return
        if "raw" not in stage_dev:
            stage_dev["raw"] = creative_sleep.dev_report(raw_ckpt, a.device, attach=bridge.attach_creative)["first_try"]
        cur = creative_sleep.dev_report(str(out / "creative" / f), a.device, attach=bridge.attach_creative)["first_try"]
        prev = stage_dev["raw"] if name == "warmup" else stage_dev.get("warmup", stage_dev["raw"])
        stage_dev[name] = cur
        share = info_["phases"][name].get("kl_share_mean_after_25pct")
        log(f"A3 check {name}: KL share {share}, creative dev first-try {prev:.4f} -> {cur:.4f}")
        info_.setdefault("a3", {})[name] = {"kl_share": share, "dev_before": prev, "dev_after": cur}
        if share is not None and share > 0.5 and (cur - prev) * 100 < 1.0:
            raise AbortRule("A3", f"{name}: KL share {share:.2f} > 0.50 and creative dev rose {(cur - prev) * 100:.2f} < 1 point")

    retention = None
    if a.sleep_retention:
        from creative import fastsleep as _fs
        _raw, _, _ = creative_sleep.sleep.load_parent(raw_ckpt, a.device)
        bridge.attach_creative(_raw)
        retention = creative_sleep.retention_fn(a.skills, a.device, base5=_fs.skills5(_raw, a.skills, a.device), attach=bridge.attach_creative,
                                                dev_limit=a.dev_limit)
        del _raw
    try:
        info = creative_sleep.run_creative(str(out / "creative"), raw_ckpt, skills_train, a.skills, device=a.device, seed=SEED,
                                           g1_factory=(None if a.no_g1 else g1_factory), retention=retention, on_stage=on_stage, attach=bridge.attach_creative,
                                           updates_cap=a.sleep_cap, pool_limit=a.pool_limit, dev_limit=a.dev_limit,
                                           n1=(4 if a.sleep_cap else 32), n2=(8 if a.sleep_cap else 480))
    except AbortRule as ar:
        return finish_after_abort(ar, "sleep")
    (out / "sleep-done.json").write_text(json.dumps(info, default=float))
    final = final_eval(arm, d_model, bridge, data, out, a, trainer.step)
    (out / "final_dev.json").write_text(json.dumps(final, indent=1, default=float))
    log("FINAL DEV", json.dumps(final, default=float)[:600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
