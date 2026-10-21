"""Gate S checks (smoke tests; no judgment calls). Pass marks are fixed HERE, before the first run of this file:

  overfit : one fixed batch of >= 64 TRAIN questions (D, floor and full configs, bridge on) and 64 creative puzzle records (sleep path):
            total loss <= 5% of its starting value AND, for D, the answer loss <= 0.05, within 400 updates (creative: 150).
  components : every component whose flag is on proves its code ran (S2 rows reach the decoder; Muon group non-empty and its
            weights move; G1 KL term > 0 on > 90% of sleep updates and the lock projection changed the step; sleep phase starts;
            both bridge projections get a nonzero gradient and become nonzero).
  resume  : kill after step K, resume, the losses of steps K+1..N equal the uninterrupted run (max abs diff <= 1e-5 on CPU).
  score   : scoring runs end-to-end on dev (D dev, validation, creative dev), never on the sealed splits.
Usage: python -m v1.gate_s overfit|components|score --root R --b2 CKPT --skills DIR --out OUT [--arm floor|full]
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import time
from pathlib import Path

import torch

from v1 import dtrain, g1 as g1mod, run as vrun
from v1.joint import Bridge

log = vrun.log


def _data(a):
    return dtrain.open_data(Path(a.root), Path(a.tokenizer), workers=a.workers, log=lambda s: None)


def five_steps(device, root=None, tokenizer=None):
    """Preflight hook: 5 real training steps of the FULL-arm D (Muon + S2) with the bridge on."""
    root = root or os.environ["V1_ROOT"]
    tokenizer = tokenizer or os.environ.get("V1_TOKENIZER", "data/tokenizer/premonition-tok-v2.json")
    data = dtrain.open_data(Path(root), Path(tokenizer), workers=2, log=lambda s: None)
    arm = vrun.ARMS["full"]
    d = vrun.build_d(arm, data.tokenizer.vocab_size).to(device)
    tc = vrun.mini_train_config(lr=vrun.LR, warmup_steps=2, log_every=1)
    tr = dtrain.StepTrainer(d, tc, device, total_steps=5, seed=0, optimizer="muon")
    stream = dtrain.train_stream(data.train, 8000, 0, 0, vrun.MAX_VISITS)
    t = time.time()
    r = tr.run(stream, log=lambda s: None)
    if device.type == "cuda":
        torch.cuda.synchronize()
    return {"losses": [l for _, l in r["losses"]], "tokens_per_s": r["tokens_per_s"], "seconds": time.time() - t,
            "peak_gpu_reserved_gib": (r["peak_gpu_reserved_bytes"] or 0) / 2 ** 30}


def overfit_d(a, arm_name: str) -> dict:
    data = _data(a)
    arm = vrun.ARMS[arm_name]
    d = vrun.build_d(arm, data.tokenizer.vocab_size).to(a.device)
    b2, _, _ = vrun.load_creative(a.b2, a.device)
    bridge = Bridge(d.config.d_model, b2.d).to(a.device).attach(d, b2)
    bopt = torch.optim.AdamW(bridge.parameters(), lr=1e-3, weight_decay=0.0)
    tc = vrun.mini_train_config(lr=a.lr, warmup_steps=20, log_every=10_000)
    tr = dtrain.StepTrainer(d, tc, a.device, total_steps=10 ** 9, seed=0, optimizer="muon" if arm.muon else "adamw")
    visits, q = [], 0
    for v in range(len(data.train)):
        visits.append(v)
        q += len(data.train.questions_of(v))
        if q >= 64:
            break
    from premonition import data as pdata
    batch = pdata.collate(data.train, visits).to(a.device)
    from premonition.train import Plan, planned_loops
    plan = Plan("teacher", "teacher", 0.0)
    loops = planned_loops(batch, plan.mode, d.config)
    rows = []
    for i in range(a.steps):
        bopt.zero_grad(set_to_none=False)
        out = tr._train_step(batch, plan, loops, False)
        bopt.step()
        if i % 20 == 0 or i == a.steps - 1:
            rows.append((tr.step, float(out["loss"]), float(out["ans"]), float(out["lm"])))
    l0, l1, ans1 = rows[0][1], rows[-1][1], rows[-1][2]
    return {"arm": arm_name, "questions": q, "visits": len(visits), "curve": rows, "start": l0, "end": l1, "ans_end": ans1,
            "pass": l1 <= 0.05 * l0 and ans1 <= 0.05, "bridge": bridge.stats()}


def overfit_creative(a) -> dict:
    from creative import sleep, stones
    m, vocab, meta = sleep.load_parent(a.b2, a.device)
    ss_rows, _ = stones.make_stone_rows(64, 0)
    recs = stones.solver_records(ss_rows)[:64]
    cfg = sleep.SleepCfg(updates=150, batch=64, lr=1e-3, warmup=10, seed=0, max_visits=10 ** 6)
    r = sleep.sleep(m, recs, [], vocab, cfg, a.device)
    l = r["loss"]
    return {"records": len(recs), "start": l[0], "end": l[-1], "min": min(l), "pass": l[-1] <= 0.05 * l[0]}


def components(a) -> dict:
    data = _data(a)
    out = {}
    for arm_name in ("floor", "full"):
        arm = vrun.ARMS[arm_name]
        d = vrun.build_d(arm, data.tokenizer.vocab_size).to(a.device)
        b2, b2v, _ = vrun.load_creative(a.b2, a.device)
        bridge = Bridge(d.config.d_model, b2.d).to(a.device).attach(d, b2)
        bopt = torch.optim.AdamW(bridge.parameters(), lr=1e-3, weight_decay=0.0)
        tc = vrun.mini_train_config(lr=vrun.LR, warmup_steps=2, log_every=10_000)
        tr = dtrain.StepTrainer(d, tc, a.device, total_steps=100, seed=0, optimizer="muon" if arm.muon else "adamw")
        # S2: what the decoder is given
        seen = []
        h = d.decoder.register_forward_hook(lambda m, args, o: seen.append((tuple(args[1].shape), int(args[2].sum()))))
        stream = dtrain.train_stream(data.train, 6000, 0, 0, vrun.MAX_VISITS)
        before = {n: p.detach().clone() for n, p in d.named_parameters()}
        from custom_io.data import Dataset, collate, load_rows, to_device
        rows = load_rows(os.path.join(a.skills, "train.jsonl"), limit=2000)
        grads = []
        for i in range(4):
            bopt.zero_grad(set_to_none=False)
            batch = next(stream)
            from premonition.train import Plan
            plan = Plan("gold", "gold", 0.0) if i < 2 else Plan("teacher", "teacher", 0.0)     # gold phase never asks; teacher does
            tr._train_step(batch, plan, vrun.planned_loops(batch, plan.mode, d.config), False)
            ds = Dataset(rows[i * 16:(i + 1) * 16], b2v, strict=False)
            lb, _ = b2.loss(to_device(collate([ds[j] for j in range(16)]), a.device))
            lb.backward()
            grads.append(bridge.stats())
            bopt.step()
        h.remove()
        grouping = tr.optimizer_grouping()
        muon_names = [n for g in grouping["groups"] if g["muon"] for n in g["names"]]
        moved = [n for n in muon_names if not torch.equal(before[n], dict(d.named_parameters())[n].detach())]
        out[arm_name] = {
            "S2": {"flag": d.config.decoder_raw_cards, "decoder_memory_shape_and_valid_rows": seen[-1] if seen else None,
                   "raw_card_rows_configured": d.config.cards if d.config.decoder_raw_cards else 0},
            "muon": {"tensors": len(muon_names), "params": sum(g["n_params"] for g in grouping["groups"] if g["muon"]),
                     "moved_after_4_steps": len(moved), "unmoved": [n for n in muon_names if n not in moved], "example_names": muon_names[:5]},
            "bridge_after_4_steps": grads[-1], "bridge_first": grads[0],
            "component_ran": vrun.component_ran(arm, tr, bridge, d, b2, {}),
        }
        last_bridge = bridge
    # G1 + sleep: a real (capped) creative sleep with the guard on, from the parent
    from v1 import creative_sleep
    raw_dev = Path(a.out) / "sleep-smoke"
    last_bridge.frozen_ctx = True
    res_info = creative_sleep.run_creative(str(raw_dev), a.b2, os.path.join(a.skills, "train.jsonl"), a.skills, device=a.device, seed=0,
                                           g1_factory=lambda raw, replay: g1mod.G1(g1mod.frozen_copy(raw), g1mod.build_diary(
                                               g1mod.frozen_copy(raw), replay, n=a.diary, seed=0, device=a.device), raw.vocab, device=a.device),
                                           pool_limit=a.pool, dev_limit=a.devn, n1=4, n2=8, updates_cap=a.cap,
                                           attach=last_bridge.attach_creative)       # the production path: bridge attached, P_dc trained by wake steps
    out["sleep_smoke"] = {"stages": res_info["stages"], "phases": res_info["phases"], "seconds": res_info["seconds"]}
    return out


def resume_compare(dir_a: str, dir_b: str, after: int = 20) -> dict:
    """Run A is uninterrupted; run B was killed after its first stop-after steps and resumed from its last checkpoint. For every step
    present in both, compare the logged losses (the LAST record of a step in B, i.e. the resumed one). Pass: max abs diff <= 1e-5 on CPU
    (on GPU the bar is 1e-3, reported; bf16 autocast and atomics make bit-equality a CPU-only claim)."""
    def last(path):
        d = {}
        for line in open(Path(path) / "losses.jsonl"):
            r = json.loads(line)
            d[r["step"]] = r
        return d
    A, B = last(dir_a), last(dir_b)
    all_B = {}
    for line in open(Path(dir_b) / "losses.jsonl"):
        r = json.loads(line)
        all_B.setdefault(r["step"], []).append(r["loss"])
    after_point = after
    ck = sorted(int(p.name.split("-")[1].split(".")[0]) for p in (Path(dir_b) / "wake-ckpt").glob("step-*.pt"))
    common = sorted(set(A) & set(B))
    diffs = {s: abs(A[s]["loss"] - B[s]["loss"]) for s in common}
    after = [s for s in common if s > after]
    mx = max(diffs[s] for s in after) if after else None
    dup = {st: v for st, v in all_B.items() if len(v) > 1}                      # steps B ran twice: first pass vs the resumed recomputation
    rf = max((abs(v[0] - v[-1]) for v in dup.values()), default=None)
    return {"resumed_vs_first_pass": {"steps": sorted(dup), "max_abs_loss_diff": rf, "pass_cpu_1e-5": rf is not None and rf <= 1e-5,
                                       "pass_gpu_1e-3": rf is not None and rf <= 1e-3},
            "note": "A-vs-B compares two separate runs; on GPU they differ before the kill already (atomics, bf16), so only resumed_vs_first_pass tests resume.",
            "steps_compared": len(common), "resume_point": after_point, "steps_after_resume_point": len(after), "max_abs_loss_diff_after_resume": mx,
            "max_abs_loss_diff_all": max(diffs.values()) if diffs else None, "ckpt_steps_in_B": ck,
            "device_is_cuda": torch.cuda.is_available(), "pass_cpu_1e-5": mx is not None and mx <= 1e-5,
            "pass_gpu_1e-3": mx is not None and mx <= 1e-3}


def sleeptime(a) -> dict:
    """The real creative pipeline (C2b W path + G1, production settings: 32/480 tries, full warm-up and N') on a 1/8-size pool, to time every
    stage and get the first sleep+G1 creative dev number. Costs are scaled linearly in the pool for the projection. DEV only."""
    from v1 import creative_sleep
    base = Path(a.out) / "sleeptime"
    b = Bridge(128, 256).to(a.device)
    from custom_io.models import build
    t0 = time.time()
    info = creative_sleep.run_creative(
        str(base), a.b2, os.path.join(a.skills, "train.jsonl"), a.skills, device=a.device, seed=0,
        g1_factory=lambda raw, replay: g1mod.G1(g1mod.frozen_copy(raw), g1mod.build_diary(g1mod.frozen_copy(raw), replay, n=4096, seed=0, device=a.device),
                                                raw.vocab, device=a.device),
        pool_limit=a.pool, dev_limit=None, attach=b.attach_creative)
    rep = creative_sleep.dev_report(str(base / "W2.pt"), a.device, attach=b.attach_creative)
    raw = creative_sleep.dev_report(a.b2, a.device, attach=b.attach_creative)
    return {"pool_limit": a.pool, "total_seconds": time.time() - t0, "seconds_by_stage": info["seconds"], "stages": info["stages"],
            "night1_records": info.get("night1_records"), "night2_records": info.get("night2_records"), "dev_W2": rep, "dev_raw_parent": raw,
            "phases": info["phases"]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["overfit", "components", "five", "resume_compare", "sleeptime"])
    ap.add_argument("--after", type=int, default=20)
    ap.add_argument("--a", default=None)
    ap.add_argument("--b", default=None)
    ap.add_argument("--root", default=None)
    ap.add_argument("--b2", default=None)
    ap.add_argument("--skills", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tokenizer", default="data/tokenizer/premonition-tok-v2.json")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--diary", type=int, default=256)
    ap.add_argument("--pool", type=int, default=64)
    ap.add_argument("--devn", type=int, default=64)
    ap.add_argument("--cap", type=int, default=40)
    a = ap.parse_args(argv)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    if a.what == "resume_compare":
        res = resume_compare(a.a, a.b, a.after)
    elif a.what == "overfit":
        res = {"floor": overfit_d(a, "floor"), "full": overfit_d(a, "full"), "creative_sleep_path": overfit_creative(a)}
    elif a.what == "sleeptime":
        res = sleeptime(a)
    elif a.what == "components":
        res = components(a)
    else:
        os.environ["V1_ROOT"] = a.root
        res = five_steps(torch.device(a.device), a.root, a.tokenizer)
    (Path(a.out) / f"gate_s_{a.what}.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float)[:4000])


if __name__ == "__main__":
    main()
