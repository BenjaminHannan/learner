"""V1 assembly runner: one arm (floor | full), WAKE then SLEEP, resumable, with the abort rules A1-A5 applied mechanically.

  python -m v1.run --arm floor|full --root DATA_ROOT --out OUT --b2 B2_CKPT --skills SKILLS_DIR [--steps N] [--device cuda]

FLOOR = D (d128, AdamW) + creative d256 + one projection each way + sleep + G1(KL 30).
FULL  = FLOOR + Muon on D's 2-D hidden matrices + S2 (decoder_raw_cards).  Defer is OFF in both (default; v1/PARAMS).
Same data, seed and steps for both arms. The sealed splits (village `test`, creative `test.jsonl`) are not opened here.
"""
from __future__ import annotations

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
from premonition.train import Curriculum, mini_train_config, planned_loops, validation_hook
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
    """A1 and A2 on the wake loss stream; A4 on spend. Pure functions of what is logged (applied mechanically)."""

    def __init__(self, total_steps: int, price_per_hour: float, spend_cap: float, started: float) -> None:
        self.total, self.price, self.cap, self.started = total_steps, price_per_hour, spend_cap, started
        self.losses: list[float] = []
        self.bad = 0
        self.dev_loss0: Optional[float] = None

    def on_step(self, step: int, loss: float) -> None:
        window = self.losses[-200:]
        if len(window) >= 50 and loss > 3.0 * statistics.median(window):          # A1: > 3x the running median
            self.bad += 1
        self.losses.append(loss)
        n = len(self.losses)
        if n >= 300 and self.bad / n > 0.01:                                       # A1: for more than 1% of steps
            raise AbortRule("A1", f"loss above 3x its running median on {self.bad}/{n} steps (> 1%)")
        if self.price and (time.time() - self.started) / 3600.0 * self.price >= self.cap:
            raise AbortRule("A4", f"spend cap ${self.cap:.2f} reached")

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
    ap.add_argument("--price-per-hour", type=float, default=0.0)
    ap.add_argument("--spend-cap", type=float, default=20.0)
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--no-sleep", action="store_true")
    ap.add_argument("--stop-after", type=int, default=None, help="testing only: stop the wake loop after this many steps")
    a = ap.parse_args(argv)
    arm = ARMS[a.arm]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    device = torch.device(a.device)
    data = dtrain.open_data(Path(a.root), Path(a.tokenizer), workers=a.workers, log=lambda s: None)
    d_model = build_d(arm, data.tokenizer.vocab_size)
    b2, b2_vocab, b2_meta = load_creative(a.b2, a.device)
    d_model.to(device)
    b2.to(device)
    bridge = Bridge(d_model.config.d_model, b2.d).to(device).attach(d_model, b2)
    bopt = torch.optim.AdamW(bridge.parameters(), lr=BRIDGE_LR, weight_decay=0.0)
    tc = mini_train_config(lr=LR, warmup_steps=WARMUP, log_every=50, memory_check_every=50)
    trainer = dtrain.StepTrainer(d_model, tc, device, total_steps=a.steps, seed=SEED, optimizer="muon" if arm.muon else "adamw")
    grouping = trainer.optimizer_grouping()
    log("optimizer grouping:", json.dumps({k: (v if k != "groups" else [{kk: vv for kk, vv in g.items() if kk != "names"} for g in v])
                                         for k, v in grouping.items()}))
    (out / "grouping.json").write_text(json.dumps(grouping, indent=1))
    ck_dir = out / "wake-ckpt"
    resumed = vckpt.load(ck_dir)
    if resumed is not None:
        trainer.restore(resumed)
        bridge.load_state_dict(resumed["bridge"])
        bopt.load_state_dict(resumed["bridge_opt"])
        log(f"RESUMED from step {resumed['step']}")
    eval_batches, stops = make_eval_batches(data.dev, DEV_EVAL_VISITS, data.tokenizer)
    hook = validation_hook(eval_batches, tokenizer=data.tokenizer, stop=stops)

    def evaluate(model):
        bridge.frozen_ctx = True
        try:
            res = hook(model)
        finally:
            bridge.frozen_ctx = False
        return {"accuracy": res["accuracy"], "questions": res["questions"], "loops_mean": res["loops_mean"],
                "gold_recall_at_4": res.get("gold_recall_at_4"), "dev_loss": dev_loss(trainer, eval_batches)}

    mon = Monitor(a.steps, a.price_per_hour, a.spend_cap, started)
    evals_path = out / "dev_evals.jsonl"
    if trainer.step == 0:
        e0 = evaluate(d_model)
        mon.dev_loss0 = e0["dev_loss"]
        evals_path.open("a").write(json.dumps({"step": 0, **e0}) + "\n")
        (out / "dev_loss0.json").write_text(json.dumps({"dev_loss0": mon.dev_loss0}))
    else:
        mon.dev_loss0 = json.loads((out / "dev_loss0.json").read_text())["dev_loss0"]
    from custom_io.data import Dataset, collate, load_rows, to_device
    skills_rows = load_rows(os.path.join(a.skills, "train.jsonl"), limit=20_000)
    ckpt_every = max(1, int(CKPT_FRACTION * a.steps))
    eval_every = max(1, int(EVAL_FRACTION * a.steps))
    stream = dtrain.train_stream(data.train, a.max_tokens, SEED, trainer.step, MAX_VISITS)
    stats_log = []

    def b2_step() -> float:
        rows = __import__("random").Random(f"{SEED}-b2-{trainer.step}").sample(skills_rows, B2_BATCH)   # a function of the step: exact resume
        batch = to_device(collate([Dataset(rows, b2_vocab, strict=False)[i] for i in range(len(rows))]), a.device)
        loss, _ = b2.loss(batch)
        loss.backward()                 # gradient reaches P_dc only (creative weights are frozen)
        return float(loss.detach())

    # wake loop: wrapped so the bridge optimizer sees D's gradient on P_cd and the creative gradient on P_dc in the same step
    d_model.train()
    first = trainer.step
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
            loss = float(res["loss"])
            if loss != loss or loss in (float("inf"), float("-inf")):
                raise AbortRule("A1", f"non-finite loss at step {trainer.step}")
            mon.on_step(trainer.step, loss)
            if trainer.step == first + 1 or trainer.step % tc.memory_check_every == 0:
                vguard.check(device, trainer.guard_limit)
            if trainer.step % tc.log_every == 0:
                log(f"step {trainer.step}/{a.steps} {plan.phase} loss {loss:.4f} b2_loss {lb:.4f} bridge {json.dumps(bridge.stats())}")
            if trainer.step % eval_every == 0:
                e = evaluate(d_model)
                evals_path.open("a").write(json.dumps({"step": trainer.step, **e}) + "\n")
                log("DEV", json.dumps(e))
                mon.check_a2(trainer.step, e["dev_loss"])
            if trainer.step % ckpt_every == 0:
                payload = trainer.checkpoint_payload()
                payload.update(bridge=bridge.state_dict(), bridge_opt=bopt.state_dict())
                vckpt.save(ck_dir, trainer.step, payload)
    except AbortRule as ar:
        (out / "ABORT.json").write_text(json.dumps({"rule": ar.rule, "why": ar.why, "step": trainer.step}))
        log("ABORT", ar)
        return 3
    (out / "wake-done.json").write_text(json.dumps({"steps": trainer.step, "bridge": bridge.stats()}))
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
        diary = g1mod.build_diary(parent, replay, n=g1mod.DIARY_SIZE, seed=SEED, device=a.device)
        return g1mod.G1(parent, diary, raw.vocab, device=a.device, seed=SEED)

    bridge.frozen_ctx = True            # D is not training in sleep: the summaries stay as wake left them, P_dc/P_cd are frozen
    raw_dev = creative_sleep.dev_report(raw_ckpt, a.device, attach=bridge.attach_creative)["first_try"]
    stage_dev = {"raw": raw_dev}

    def on_stage(name, info_):
        # A3, applied at the end of the first two G1-active phases (warm-up, N'): KL term > 50% of total loss after the first 25% of the
        # phase AND creative dev first-try up < 1 point over the phase -> stop and judge the last checkpoint.
        f = {"warmup": "warm.pt", "Nprime": "Nprime.pt"}.get(name)
        if f is None:
            return
        cur = creative_sleep.dev_report(str(out / "creative" / f), a.device, attach=bridge.attach_creative)["first_try"]
        prev = stage_dev["raw"] if name == "warmup" else stage_dev["warmup"]
        stage_dev[name] = cur
        share = info_["phases"][name].get("kl_share_mean_after_25pct")
        log(f"A3 check {name}: KL share {share}, creative dev first-try {prev:.4f} -> {cur:.4f}")
        info_.setdefault("a3", {})[name] = {"kl_share": share, "dev_before": prev, "dev_after": cur}
        if share is not None and share > 0.5 and (cur - prev) * 100 < 1.0:
            raise AbortRule("A3", f"{name}: KL share {share:.2f} > 0.50 and creative dev rose {(cur - prev) * 100:.2f} < 1 point")

    try:
        info = creative_sleep.run_creative(str(out / "creative"), raw_ckpt, skills_train, a.skills, device=a.device, seed=SEED,
                                           g1_factory=g1_factory, on_stage=on_stage, attach=bridge.attach_creative)
    except AbortRule as ar:
        (out / "ABORT.json").write_text(json.dumps({"rule": ar.rule, "why": ar.why, "phase": "sleep"}))
        log("ABORT", ar)
        return 3
    (out / "sleep-done.json").write_text(json.dumps(info, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
