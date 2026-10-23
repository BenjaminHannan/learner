"""The creative module's sleep for V1: C2b's W arm exactly (creative/c2b.py `train_parent`, W path only), with G1 optional.

Stages (each writes its file, a re-run skips what exists; a dead box is a restart):
  warm-up (2,048 add/mult rows, 4 visits, lr 3e-4, skills replay) -> N' (stepping-stone sleep) -> pool temperature on DEV ->
  night 1: two-pass search on N' -> W1 records -> sleep -> night 2: search with W1 -> W2 records -> sleep -> W2.pt.
R, H, M arms of C2b are NOT run (they were controls; V1 needs the W path only).
G1 (v1/g1.py) is applied to EVERY weight-changing stage after the raw parent (warm-up, N', both nights); `guard=None` is C2b as tested.
The sealed test split (creative/data/c2/test.jsonl) is never opened here; `dev_report` below reads dev only.
"""
from __future__ import annotations

import json
import math
import os
import time
from typing import Any, Callable, Optional

import torch

from creative import c2_dev, c2_pilot, c2_stones, c2_stuck, fastsleep, sleep, stones
from creative import rules_real as R
from creative.c2b import DATA, LR, N1, N2, VISITS, T_GRID, load_recs, night_info, save_recs
from custom_io.data import load_rows
from v1.joint import clone_model

log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def _sleep_stage(base, recs, replay, extra, vocab, cfg, device, guard):
    m = clone_model(base)
    r = sleep.sleep(m, recs, replay, vocab, cfg, device, replay_extra=extra, guard=guard)
    return m, r


def run_creative(out: str, ckpt: str, skills_train: str, skills_data: str, device: str = "cpu", seed: int = 0,
                 g1_factory: Optional[Callable[[Any, Any], Any]] = None, pool_limit: Optional[int] = None,
                 dev_limit: Optional[int] = None, n1: int = N1, n2: int = N2, T: Optional[float] = None,
                 on_stage: Optional[Callable[[str, dict], None]] = None,
                 attach: Optional[Callable[[Any], None]] = None, updates_cap: Optional[int] = None,
                 retention: Optional[Callable[[str, str], dict]] = None) -> dict[str, Any]:
    """updates_cap: smoke tests only (caps every stage's update count; never set for an arm). -> info dict (also out/train.json). `g1_factory(parent_model, replay_rows)` returns a G1 object (or None for no guard).
    retention(name, ckpt_path) -> dict (default None = off, v1 unchanged): called after each sleep night's W{n}.pt exists (W1, W2), the result is kept in
    info["retention"][name] and train.json (skills retention check, see `retention_fn`)."""
    os.makedirs(out, exist_ok=True)
    P = lambda f: os.path.join(out, f)
    done = lambda f: os.path.exists(P(f))
    path = P("train.json")
    info = json.load(open(path)) if os.path.exists(path) else dict(ckpt=ckpt, seed=seed, stages=[], seconds={}, g1=bool(g1_factory), phases={})
    save = lambda: json.dump(info, open(path, "w"), indent=1, default=float)

    def stage(name, secs, extra=None):
        info["seconds"][name] = round(secs, 1)
        info["stages"].append(name)
        if extra is not None:
            info["phases"][name] = extra
        save()
        log("stage", name, round(secs))
        if on_stage:
            on_stage(name, info)

    if on_stage:                                  # a restart re-applies the stage checks (A3) to stages that are already done
        for done_stage in [x for x in info["stages"] if x in ("warmup", "Nprime")]:
            on_stage(done_stage, info)
    replay = sleep.load_replay(skills_train, None, seed)
    warm_rows = R.warm_records(R.load_split(DATA, "warm"))
    pool = c2_stones._with_nums(R.load_split(DATA, "pool")[:pool_limit])
    _load = sleep.load_parent

    def load_parent(path, dev):                 # every creative model of the joint system carries the bridge hooks
        m_, v_, me_ = _load(path, dev)
        if attach:
            attach(m_)
        return m_, v_, me_
    raw, vocab, meta = load_parent(ckpt, device)
    guard = g1_factory(raw, replay) if g1_factory else None          # parent = the raw pre-V1 creative model (frozen copy inside)

    cap = (lambda u: min(u, updates_cap)) if updates_cap else (lambda u: u)

    def phase_info(r):
        kl = r.get("kl") or []
        if not kl:
            return dict(updates=r["updates"])
        late = kl[len(kl) // 4:] or kl                    # the part of the phase after its first 25% (rule A3's measure)
        share = [k["kl_term"] / max(k["task"] + k["kl_term"], 1e-12) for k in late]
        return dict(updates=r["updates"], guard=r.get("guard"), kl_first=kl[0], kl_last=kl[-1],
                    kl_share_last=kl[-1]["kl_term"] / max(kl[-1]["task"] + kl[-1]["kl_term"], 1e-12),
                    kl_share_mean_after_25pct=sum(share) / len(share),
                    kl_max_term=max(k["kl_term"] for k in kl), kl_nonzero_steps=sum(1 for k in kl if k["kl_term"] > 0))

    ts = time.time()
    if not done("Nprime.pt"):
        cfgw = sleep.SleepCfg(updates=cap(sleep.max_updates(len(warm_rows), 64, True, 4)), batch=64, lr=3e-4, warmup=20, seed=seed, max_visits=4)
        m0, rw = _sleep_stage(raw, warm_rows, replay, None, vocab, cfgw, device, guard)
        sleep.save_parent(m0, meta["name"], meta["cfg"], vocab, P("warm.pt"), step=(meta["step"] or 0), warmup=True)
        stage("warmup", time.time() - ts, phase_info(rw))
        ts = time.time()
        ss_rows, _ = stones.make_stone_rows(2048, seed)
        cfgn = sleep.SleepCfg(updates=cap(sleep.max_updates(2048, 64, True, 4)), batch=64, lr=3e-4, warmup=20, seed=seed, max_visits=4)
        N, rn = _sleep_stage(m0, stones.solver_records(ss_rows), replay, warm_rows, vocab, cfgn, device, guard)
        sleep.save_parent(N, meta["name"], meta["cfg"], vocab, P("Nprime.pt"), step=(meta["step"] or 0), warmup=True)
        stage("Nprime", time.time() - ts, phase_info(rn))
    N, vocab, meta = load_parent(P("Nprime.pt"), device)
    N.eval()

    ts = time.time()
    if not done("setup.json"):
        dev = c2_stones._with_nums(R.load_split(DATA, "dev")[:dev_limit])
        floors = c2_dev.floors_for(dev, P("dev_floors.json"))
        base5 = fastsleep.skills5(N, skills_data, device) if skills_data else None
        res = dict(base5=base5)
        Tsel = T
        if Tsel is None:
            rep = c2_dev.dev_report(N, vocab, dev, floors, device, 32, seed, temps=T_GRID, extend=(), log=log)
            ok = {t: g for t, g in rep["temps"].items() if g["sameness_ok"]} or rep["temps"]
            Tsel = float(max(ok, key=lambda t: ok[t]["reach32"]))
            res["pool_temperature"] = {t: dict(reach32=g["reach32"], sameness_ok=g["sameness_ok"]) for t, g in rep["temps"].items()}
        res["T"] = Tsel
        json.dump(res, open(P("setup.json"), "w"), indent=1)
        stage("setup", time.time() - ts)
    setup = json.load(open(P("setup.json")))
    Tt = setup["T"]
    seeds = {n: seed + 10 * n for n in (1, 2)}

    for night, base_name in ((1, "Nprime.pt"), (2, "W1.pt")):
        base, _, _ = load_parent(P(base_name), device)
        base.eval()
        ts = time.time()
        if not done(f"rec_W{night}.pt"):
            tries, fit1, fit, drawn = c2_stuck.search(base, pool, vocab, device, seeds[night], Tt, n1, n2)
            Wn, cn = c2_stuck.w_records(pool, tries, seed + night, arm=f"W{night}")
            save_recs(P(f"rec_W{night}.pt"), Wn, counts=cn, info=night_info(pool, drawn, Wn, cn, fit1, fit))
            stage(f"night{night}_records", time.time() - ts)
        d = load_recs(P(f"rec_W{night}.pt"))
        recs = d["records"]
        info[f"night{night}_records"] = len(recs)
        if len(recs) < 1:
            info["stop"] = f"night {night}: no W records"
            save()
            return info
        if not done(f"W{night}.pt"):
            ts = time.time()
            updates = cap(VISITS * len(recs) // 32)
            per = 32
            mv = max(VISITS, math.ceil(updates * per / max(len(recs), 1)))
            cfgs = sleep.SleepCfg(updates=updates, batch=64, lr=LR, warmup=20, seed=seed, max_visits=mv)
            m, rs = _sleep_stage(base, recs, replay, warm_rows, vocab, cfgs, device, guard)
            sleep.save_parent(m, meta["name"], meta["cfg"], vocab, P(f"W{night}.pt"), step=(meta["step"] or 0), warmup=True)
            stage(f"W{night}_sleep", time.time() - ts, phase_info(rs))
        if retention is not None and f"W{night}" not in info.get("retention", {}):
            info.setdefault("retention", {})[f"W{night}"] = retention(f"W{night}", P(f"W{night}.pt"))
            save()
            log("retention", f"W{night}", info["retention"][f"W{night}"])
    json.dump(dict(T=Tt, base5=setup["base5"]), open(P("complete.json"), "w"))
    log("CREATIVE DONE", out)
    return info


def dev_report(model_path: str, device: str = "cpu", limit: Optional[int] = None, attach: Optional[Callable[[Any], None]] = None,
               split: str = "dev") -> dict[str, Any]:
    """W2's measure: greedy first try per kind and pooled on creative DEV. split="test" is the sealed 512 and is passed ONLY by v1/sealed_read.py."""
    if split != "dev" and os.environ.get("V1_SEALED_READ") != "1":
        raise PermissionError("only v1/sealed_read.py may score a split other than dev")
    m, vocab, _ = sleep.load_parent(model_path, device)
    if attach:
        attach(m)
    m.eval()
    rows = c2_stones._with_nums(R.load_split(DATA, split)[:limit])
    g = c2_pilot.greedy_eval(m, rows, vocab, device)
    kinds = sorted({r["kind"] for r in rows})
    by_kind = {k: sum(g["per_q_right"][i] for i, r in enumerate(rows) if r["kind"] == k) / sum(1 for r in rows if r["kind"] == k) for k in kinds}
    return dict(first_try=g["right"], fits=g["fits"], n=len(rows), by_kind=by_kind)


def retention_fn(skills_data: str, device: str = "cpu", base5: Optional[float] = None, attach: Optional[Callable[[Any], None]] = None,
                 dev_limit: Optional[int] = None) -> Callable[[str, str], dict]:
    """Skills retention after a sleep night (C2b's harm measure): pooled-5 skills exact (`fastsleep.skills5`) of the checkpoint, harm in points =
    100 x (base5 - skills5) vs `base5` (the RAW parent's score, common to every arm), plus creative dev first-try. DEV only; never the sealed split."""
    def fn(name: str, path: str) -> dict:
        m, _, _ = sleep.load_parent(path, device)
        if attach:
            attach(m)
        s5 = fastsleep.skills5(m, skills_data, device)
        d = dev_report(path, device, limit=dev_limit, attach=attach)
        return dict(skills5=s5, harm_points=None if base5 is None else 100 * (base5 - s5), dev_first_try=d["first_try"], dev_by_kind=d["by_kind"])
    return fn
