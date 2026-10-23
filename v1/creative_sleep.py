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


def add_dreams(recs: list, counts: dict, pool: list, dream2: int, seed: int, night: int, max_steps: int = 2, strict: bool = False, occam: bool = False):
    """Dream rows (creative/dream2.py): `dream2` extra records appended to a night's W records. dream2 == 0 returns `recs` itself and imports nothing
    (the flag-off path is today's code path exactly). Dreams avoid every warm/pool/dev prompt (and the pool prompts passed here). -> (records, info)."""
    if not dream2:
        return recs, None
    from creative import dream2 as D
    if occam:       # Occam-relabelled (slow find_reference): spread over the cores; fixed shards so the stream does not depend on the core count
        import os
        dreams = D.dream_rows_par(dream2, seed, [r['prompt'] for r in pool], night=night, max_steps=max_steps, strict=strict, shards=32, workers=min(32, os.cpu_count() or 1), occam=True)
    else:
        dreams = D.dream_rows_c2(dream2, seed, [r['prompt'] for r in pool], night=night, max_steps=max_steps, **(dict(strict=True) if strict else {}))
    return list(recs) + dreams, dict(n=len(dreams), seed=seed, night=night, max_steps=max_steps, by_length={L: sum(d['dream']['length'] == L for d in dreams) for L in range(1, max_steps + 1)})


def oracle_records(pool: list) -> tuple[list, int]:
    """Reference-program records for the held-out-kind POOL questions (uses the answer key's kind / params; report-only upper bound). Rows with no reference are skipped. -> (records, skipped)."""
    from creative import fewshot as F
    out, skipped = [], 0
    for r in pool:
        assert r["kind"] in R.HELD_OUT, r["kind"]
        ref = R.reference(r["kind"], tuple(r["params"]))
        if ref is None:
            skipped += 1
            continue
        t, _, qs = ref
        out.append(F._record(r, R.remap(t, qs, F.parse(r["prompt"])["q_slot"]), "OR", 0))
    return out, skipped


def school_plan(school) -> list:
    """[(night tag, max_steps, n)] per school phase (night tags 9xx keep dream ids distinct from the nightly dreams 1, 2 and from each other)."""
    n, ms, strict = school["n"], school.get("max_steps", 5), bool(school.get("strict"))
    if school.get("curriculum"):
        thirds = [n // 3, n // 3, n - 2 * (n // 3)]
        return [(921 + i, m_, k) for i, (m_, k) in enumerate(zip((2, 3, 5), thirds))]
    return [(900 + 10 * strict + 5 * bool(school.get("occam")), ms, n)]


def run_school(school, base, pool, replay, warm_rows, vocab, device, guard, cap, seed, phase_info):
    """The dream school (see run_creative). -> info dict with '_model' (the trained model), counts by length, seconds and final losses per phase."""
    from creative import dream2 as D
    lr = school.get("lr", 3e-4)
    visits = school.get("visits", 2)
    fl = lambda r: (sum(r["loss"][-50:]) / max(len(r["loss"][-50:]), 1)) if r.get("loss") else None
    info = dict(cfg={k: v for k, v in school.items()}, phases=[])
    if school.get("oracle"):
        recs, skipped = oracle_records(pool)
        ups = cap(school["updates"])
        mv = max(visits, math.ceil(ups * 32 / max(len(recs), 1)))
        cfg = sleep.SleepCfg(updates=ups, batch=64, lr=lr, warmup=20, seed=seed, max_visits=mv)
        t0 = time.time()
        m, r = _sleep_stage(base, recs, replay, warm_rows, vocab, cfg, device, guard)
        info["phases"].append(dict(oracle=True, records=len(recs), skipped=skipped, max_visits=mv, seconds=round(time.time() - t0, 1), final_loss=fl(r), **phase_info(r)))
        info["_model"] = m
        return info
    strict = bool(school.get("strict"))
    plan = school_plan(school)
    avoid = [r["prompt"] for r in pool]
    m = base
    for night, mx, k in plan:
        t0 = time.time()
        st = {}
        dreams = D.dream_rows_par(k, seed, avoid, night=night, max_steps=mx, strict=strict, shards=school.get("shards", 8), workers=school.get("workers", 1), stats=st, cache_dir=school.get("cache"),
                                 occam=bool(school.get("occam")))
        cfg = sleep.SleepCfg(updates=cap(sleep.max_updates(len(dreams), 64, True, visits)), batch=64, lr=lr, warmup=20, seed=seed, max_visits=visits)
        gen_s = time.time() - t0
        if cfg.updates < 1:
            raise ValueError(f"school phase of {len(dreams)} dreams gives 0 updates at {visits} visits; use a larger n")
        m, r = _sleep_stage(m, dreams, replay, warm_rows, vocab, cfg, device, guard)
        info["phases"].append(dict(night=night, max_steps=mx, n=len(dreams), strict=strict, by_length={L: sum(d["dream"]["length"] == L for d in dreams) for L in range(1, mx + 1)},
                                   by_found_length={L: sum(d["dream"].get("found_length", d["dream"]["length"]) == L for d in dreams) for L in range(1, mx + 1)},
                                   draw_stats=st, gen_seconds=round(gen_s, 1), seconds=round(time.time() - t0, 1), final_loss=fl(r), **phase_info(r)))
    info["_model"] = m
    return info


def run_creative(out: str, ckpt: str, skills_train: str, skills_data: str, device: str = "cpu", seed: int = 0,
                 g1_factory: Optional[Callable[[Any, Any], Any]] = None, pool_limit: Optional[int] = None,
                 dev_limit: Optional[int] = None, n1: int = N1, n2: int = N2, T: Optional[float] = None,
                 on_stage: Optional[Callable[[str, dict], None]] = None,
                 attach: Optional[Callable[[Any], None]] = None, updates_cap: Optional[int] = None, dream2: int = 0,
                 dream2_max_steps: int = 2, stop_after: Optional[str] = None, dream2_strict: bool = False, school: Optional[dict] = None, dream2_occam: bool = False) -> dict[str, Any]:
    """dream2: N dream rows (random 1..dream2_max_steps-step programs over B2's executor, creative/dream2.py) added to EACH night's W records; 0 = off = today's behaviour exactly.
    They count in the night's record total, so the existing visit cap (VISITS visits per record, max_visits) applies to them like any other record.
    dream2_strict: nightly dreams also drop every dream equal to a held-out kind's form (dream2.py strict).
    stop_after: "setup" returns right after the setup stage (None = whole pipeline).
    school: None = off = today's behaviour exactly. Else a dream school between setup and night 1 (school.pt from Nprime.pt; night 1 then starts from school.pt): dict(n, max_steps=5, strict=False,
    curriculum=False (3 sequential sleeps, max_steps 2/3/5, n split in thirds), visits=2, lr=3e-4, workers=1, cache=<dir or None>) with skills replay + warm rows as replay_extra, like the warm-up.
    Or dict(oracle=True, updates=U, lr=...): REPORT-ONLY upper bound, school = supervised POOL questions' reference programs (answer key kind/params), U updates (visits raised to fit).
    updates_cap: smoke tests only (caps every stage's update count; never set for an arm). -> info dict (also out/train.json). `g1_factory(parent_model, replay_rows)` returns a G1 object (or None for no guard)."""
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
    if school and not done("school.pt"):
        ts = time.time()
        sinfo = run_school(school, load_parent(P("Nprime.pt"), device)[0], pool, replay, warm_rows, vocab, device, guard, cap, seed, phase_info)
        m_s = sinfo.pop("_model")
        sleep.save_parent(m_s, meta["name"], meta["cfg"], vocab, P("school.pt"), step=(meta["step"] or 0), warmup=True)
        info["school"] = sinfo
        stage("school", time.time() - ts, sinfo)

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
    if stop_after == "setup":                     # the shared part of a multi-arm experiment (creative/multistep.py)
        return info
    Tt = setup["T"]
    seeds = {n: seed + 10 * n for n in (1, 2)}

    for night, base_name in ((1, "school.pt" if school else "Nprime.pt"), (2, "W1.pt")):
        base, _, _ = load_parent(P(base_name), device)
        base.eval()
        ts = time.time()
        if not done(f"rec_W{night}.pt"):
            tries, fit1, fit, drawn = c2_stuck.search(base, pool, vocab, device, seeds[night], Tt, n1, n2)
            Wn, cn = c2_stuck.w_records(pool, tries, seed + night, arm=f"W{night}")
            ninfo = night_info(pool, drawn, Wn, cn, fit1, fit)                # W-only numbers (the search check reads these)
            Wn, dinfo = add_dreams(Wn, cn, pool, dream2, seed, night, dream2_max_steps, dream2_strict, dream2_occam)
            if dinfo:
                info.setdefault("dream2", {})[str(night)] = dinfo
                ninfo["dream2"] = dinfo
                save()
            save_recs(P(f"rec_W{night}.pt"), Wn, counts=cn, info=ninfo)
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
    json.dump(dict(T=Tt, base5=setup["base5"]), open(P("complete.json"), "w"))
    log("CREATIVE DONE", out)
    return info


def dev_report(model_path: str, device: str = "cpu", limit: Optional[int] = None, attach: Optional[Callable[[Any], None]] = None,
               split: str = "dev") -> dict[str, Any]:
    """W2's measure: greedy first try per kind and pooled on creative DEV. split="test" is the sealed 512 (labelled is allowed too) and is passed ONLY by v1/sealed_read.py."""
    if split not in ("dev", "labelled") and os.environ.get("V1_SEALED_READ") != "1":     # labelled = the plain nets' 512 held-out-kind questions (never sealed)
        raise PermissionError("only v1/sealed_read.py may score a split other than dev / labelled")
    m, vocab, _ = sleep.load_parent(model_path, device)
    if attach:
        attach(m)
    m.eval()
    rows = c2_stones._with_nums(R.load_split(DATA, split)[:limit])
    g = c2_pilot.greedy_eval(m, rows, vocab, device)
    kinds = sorted({r["kind"] for r in rows})
    by_kind = {k: sum(g["per_q_right"][i] for i, r in enumerate(rows) if r["kind"] == k) / sum(1 for r in rows if r["kind"] == k) for k in kinds}
    return dict(first_try=g["right"], fits=g["fits"], n=len(rows), by_kind=by_kind, n_by_kind={k: sum(1 for r in rows if r["kind"] == k) for k in kinds})
