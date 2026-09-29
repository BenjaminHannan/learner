#!/usr/bin/env python3
"""Driver for the deep sparse-MoE loop test (artifacts/claude-moe-deep-20260929). GPU or CPU, same code.

Nothing in the ruler is edited. Like scripts/claude_relnet_eq_gpu.py, this runs the ruler's own pieces
(claude_fewex_eq_bench's pool, batches and holdout job; claude_patch_eq_ladder.job, the resumable copy of
the harness's adapt_job; claude_fewex_bench's scoring, sleep and gradient check) with changes that are only
about where tensors live and which plug-in config is built:
  * torch.set_default_device(dev); the plug-in's Net(arm) is built on the CPU (so a fresh net's weights come
    from the CPU RNG exactly as on a CPU run) and then moved to the device;
  * cuda is strict fp32: TF32 off for matmul and cudnn, highest matmul precision, no autocast, deterministic
    algorithms requested (warn_only). Stage checkpoints are written as CPU tensors.
It adds: source practice for each config (the ADDENDUM-3 recipe: 12,000 batches of 64 sums/grids, 1e-3
warm-up/cosine, fixed depth on source dev, V1 on the untouched guard, the harness's gradient check), with a
resumable checkpoint; routing-health statistics; and the CPU-vs-GPU smoke with marks fixed in SMOKE_MARKS.

Configs: see claude_moe_deep_net.CFGS; `loopctl` is the baseline loop (claude_fewex_net) from the qualified
loop sources (--loop-source-root/qual-loop-s{S}), re-run here on the same machine as the MoE runs.
Outputs under ART = artifacts/claude-moe-deep-20260929:
  runs/<cfg>-s<S>[-lr<lr>]/source.json, source.pt, resume.pt      (source practice)
  runs/<cfg>-s<S>/qualified.json                                  (which source folder passed V1 and V2)
  eq-runs/<cfg>-<init>-s<S>/adapt.json, partial.json, routes.json, k*.pt, sleep*.pt, holdout.json
  SMOKE-gpu.json, TIMING-gpu.json

  python -B scripts/claude_moe_deep_run.py selftest
  python -B scripts/claude_moe_deep_run.py smoke   --device cuda
  python -B scripts/claude_moe_deep_run.py source  --cfg L8-E64 --seed 0 --device cuda
  python -B scripts/claude_moe_deep_run.py dev     --cfg L8-E64 --seed 0 --init pre --device cuda [--no-stages]
  python -B scripts/claude_moe_deep_run.py dev     --cfg loopctl --seed 0 --init pre --device cuda --loop-source-root DIR
  python -B scripts/claude_moe_deep_run.py holdout --cfg L8-E64 --seed 0 --init pre --device cuda
  python -B scripts/claude_moe_deep_run.py phase   --phase 1 --device cuda --loop-source-root DIR
Every command is idempotent: finished work is skipped, unfinished source practice and ladders resume.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
import random
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_fewex_eq_bench as EQ  # noqa: E402
import claude_moe_deep_net as M  # noqa: E402
import claude_patch_eq_ladder as L  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "claude-moe-deep-20260929"
RUNS, EQR = ART / "runs", ART / "eq-runs"
GUARD_SEED = D.SOURCE_SEED + 300
SOURCE_STEPS, SOURCE_BATCH, SOURCE_CK = 12000, 64, 250
SOURCE_LRS = (1e-3, 5e-4)          # 5e-4 only if 1e-3 fails V1 or V2 (source-only decision, before any maze)
MAIN = M.MAIN
PHASES = {
    # 1: the verdict. MoE sources, practised ladders (stages kept for the holdout), same-machine loop controls.
    1: [("source", MAIN, 0), ("source", MAIN, 1), ("dev", MAIN, 0, "pre"), ("dev", MAIN, 1, "pre"),
        ("dev", "loopctl", 0, "pre"), ("dev", "loopctl", 1, "pre")],
    # 2: scaling, report only, dev only (no stage checkpoints kept). Seed 0 of every config before seed 1.
    2: [(step, c, s) + (("pre",) if step == "dev" else ())
        for s in (0, 1) for c in ("L2-E64", "L4-E64", "L16-E64", "L8-E16", "L8-E32", "L8-E128")
        for step in ("source", "dev")],
    # 3: attribution and practice rows, report only, dev only.
    3: [(step, c, s) + ((init,) if step == "dev" else ())
        for s in (0, 1) for c, init in (("L8-dense-act", "pre"), ("L8-dense-tot", "pre"), ("plain-big", "pre"))
        for step in ("source", "dev")] + [("dev", MAIN, 0, "fresh"), ("dev", MAIN, 1, "fresh")],
}


def utc():
    try:
        return subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Plug:
    """Proxy for a plug-in module: same attributes, but Net(arm) is built on the CPU and moved to the device."""

    def __init__(self, mod, dev):
        object.__setattr__(self, "_mod", mod)
        object.__setattr__(self, "_dev", dev)

    def __getattr__(self, name):
        return getattr(self._mod, name)

    def __setattr__(self, name, value):
        setattr(self._mod, name, value)

    def Net(self, arm):
        with torch.device("cpu"):
            net = self._mod.Net(arm)
        return net.to(self._dev)


def arm_of(cfg):
    return "plain" if cfg != "loopctl" and M.CFGS[cfg]["kind"] == "plain" else "loop"


def setup(dev, cfg, threads=2):
    torch.set_num_threads(threads)
    if dev == "cuda":
        if not torch.cuda.is_available():
            raise SystemExit("NO-CUDA")
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.set_float32_matmul_precision("highest")
        torch.use_deterministic_algorithms(True, warn_only=True)
    torch.set_default_device(dev)
    if cfg == "loopctl":
        mod = importlib.import_module("claude_fewex_net")
    else:
        M.set_cfg(cfg)
        mod = M
    plug = Plug(mod, dev)
    B.N = EQ.B.N = plug
    return plug


def meta(dev):
    return {"device": dev, "torch": torch.__version__,
            "gpu": torch.cuda.get_device_name(0) if dev == "cuda" else None,
            "tf32_matmul": torch.backends.cuda.matmul.allow_tf32, "tf32_cudnn": torch.backends.cudnn.allow_tf32,
            "float32_matmul_precision": torch.get_float32_matmul_precision(),
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
            "threads": torch.get_num_threads(), "driver": "scripts/claude_moe_deep_run.py"}


def cpu_state(net):
    return {k: v.detach().cpu() for k, v in net.state_dict().items()}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ------------------------------------------------------------------ routing health
@torch.no_grad()
def route_stats(net, items):
    """Expert use over 48 rounds on `items`: per layer dead experts, busiest/mean load, load entropy
    (1.0 = perfectly even), and how often a cell's top-1 expert changes from one round to the next."""
    if not hasattr(net, "route_trace") or not net.moes():
        return None
    net.eval()
    t, s, _ = B.N.tensors(items)
    trace = net.route_trace(t, s, B.MAX_ROUNDS)
    layers = []
    for tr in trace:                                   # [rounds, cells, k]
        n = net.moes()[0].n
        counts = torch.bincount(tr.long().reshape(-1), minlength=n).double()
        p = counts / counts.sum()
        ent = float(-(p[p > 0] * p[p > 0].log()).sum() / math.log(n))
        top1 = tr[:, :, 0]
        layers.append({"dead": int((counts == 0).sum()), "experts": n,
                       "max_over_mean": float(counts.max() / counts.mean()), "load_entropy": round(ent, 4),
                       "top1_change_between_rounds": float((top1[1:] != top1[:-1]).double().mean())})
    return {"items": len(items), "rounds": B.MAX_ROUNDS, "layers": layers,
            "dead_total": sum(x["dead"] for x in layers), "experts_total": sum(x["experts"] for x in layers),
            "worst_max_over_mean": max(x["max_over_mean"] for x in layers),
            "min_load_entropy": min(x["load_entropy"] for x in layers)}


def expert_gradient_check(net, seed):
    """The harness's gradient check covers 2-D matrices; the routed experts are 3-D [E, ...] tensors, so also
    count, per layer, the experts whose slice gets a nonzero gradient on either of the same two batches."""
    if not hasattr(net, "moes") or not net.moes():
        return None
    net.train()
    rng = random.Random(9242700 + seed)
    alive = [torch.zeros(m.n, dtype=torch.bool) for m in net.moes()]
    for batch in ([D.E.make_sum(rng, 4) for _ in range(32)], [D.latin_legend(rng, 5) for _ in range(32)]):
        net.zero_grad(set_to_none=True)
        B.N.train_loss(net, batch, rng).backward()
        for a, m in zip(alive, net.moes()):
            g = m.w1.grad
            if g is not None:
                a |= (g.abs().sum((1, 2)) > 0).cpu()
    net.zero_grad(set_to_none=True)
    per = [int(a.sum()) for a in alive]
    return {"alive_per_layer": per, "experts_per_layer": net.moes()[0].n,
            "alive_total": sum(per), "experts_total": sum(m.n for m in net.moes())}


# ------------------------------------------------------------------ source practice
def source_dir(cfg, seed, lr):
    return RUNS / (f"{cfg}-s{seed}" + ("" if lr == SOURCE_LRS[0] else f"-lr{lr:g}"))


# the qualified loop sources the recorded F_eq baseline used (artifacts/claude-distill-20260928/checkpoints-sha256.txt)
LOOP_SOURCE_SHA = {0: "1f15f8990a1fd768841d0bfa989e8aba809f54951d7eabf375c42bb82f0c12fe",
                   1: "17e7217bedc7559f3ed17ab13e4f2c717e34a12124d618b4acef24097f65abd9"}


def qualified_dir(cfg, seed, loop_root=None):
    if cfg == "loopctl":
        if loop_root is None:
            raise SystemExit("--loop-source-root is required for the loop control")
        d = Path(loop_root) / f"qual-loop-s{seed}"
        if not (d / "source.pt").exists() or sha(d / "source.pt") != LOOP_SOURCE_SHA[seed]:
            raise SystemExit(f"LOOP-SOURCE-MISMATCH: {d / 'source.pt'} is missing or not the recorded net")
        return d
    q = RUNS / f"{cfg}-s{seed}" / "qualified.json"
    if not q.exists():
        raise SystemExit(f"WAITING: {q} missing (run `source` first)")
    rec = json.loads(q.read_text())
    if not rec["qualified"]:
        raise SystemExit(f"SOURCE-NOT-QUALIFIED: {cfg} seed {seed} failed V1/V2 at every source lr")
    return ROOT / rec["folder"]


def train_source(cfg, seed, dev, lr, threads):
    out = source_dir(cfg, seed, lr)
    if (out / "source.json").exists():
        print(f"skip: {out} source.json exists", flush=True)
        return json.loads((out / "source.json").read_text())
    setup(dev, cfg, threads)
    arm = arm_of(cfg)
    out.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(seed)
    rng = random.Random(7000000 + seed)
    with torch.device("cpu"):
        practice = M.Practice(arm, seed, SOURCE_STEPS, lr)
    practice.net.to(dev)                       # parameters move in place; the optimizer keeps them
    ck = out / "resume.pt"
    start, prior, log = 0, 0.0, []
    if ck.exists():
        st = torch.load(ck, map_location=dev, weights_only=False)
        practice.net.load_state_dict(st["net"])
        practice.opt.load_state_dict(st["opt"])
        practice.sched.load_state_dict(st["sched"])
        practice.round_rng.setstate(st["round_rng"])
        rng.setstate(st["source_rng"])
        start, prior, log = st["step"], st["seconds"], st["log"]
    probe = D.old_panels(D.SOURCE_SEED + 100)
    t0, losses, started = time.monotonic(), [], utc()
    for step in range(start + 1, SOURCE_STEPS + 1):
        loss = practice.step(D.source_batch(rng, SOURCE_BATCH))
        if not math.isfinite(loss):
            raise SystemExit(f"NONFINITE-LOSS at step {step}: {loss}")
        losses.append(loss)
        if step % SOURCE_CK == 0 or step == SOURCE_STEPS:
            secs = prior + time.monotonic() - t0
            entry = {"step": step, "loss_mean": sum(losses) / len(losses), "seconds": round(secs, 1)}
            if step % 1000 == 0 and arm == "loop" and cfg != "loopctl":
                rs = route_stats(practice.net, probe["sums4"][:16]) or {}
                rg = route_stats(practice.net, probe["grids5"][:16]) or {}
                entry["route_dead"] = [rs.get("dead_total"), rg.get("dead_total")]
                entry["route_worst_max_over_mean"] = [rs.get("worst_max_over_mean"), rg.get("worst_max_over_mean")]
            log.append(entry)
            torch.save({"net": practice.net.state_dict(), "opt": practice.opt.state_dict(),
                        "sched": practice.sched.state_dict(), "round_rng": practice.round_rng.getstate(),
                        "source_rng": rng.getstate(), "step": step, "seconds": secs, "log": log}, ck.with_suffix(".tmp"))
            ck.with_suffix(".tmp").replace(ck)
            print(json.dumps({"phase": "source", "cfg": cfg, "seed": seed, "lr": lr, **entry}), flush=True)
            losses = []
    net = practice.net
    train_seconds = prior + time.monotonic() - t0
    if arm == "loop":
        source_dev = D.old_panels(D.SOURCE_SEED + 100)
        fixed_counts = {str(d): sum(B.score(net, v, d)["fixed_right"] for v in source_dev.values()) for d in B.DEPTHS}
        fixed_depth = max(B.DEPTHS, key=lambda d: (fixed_counts[str(d)], -d))
        sweep = None
    else:
        fixed_counts, fixed_depth = {}, 1
        sweep = B.source_plain_lr_sweep(net, seed)
    old = {k: B.score(net, v, fixed_depth) for k, v in D.old_panels(GUARD_SEED).items()}
    grad = B.gradient_check(net, seed)
    experts = expert_gradient_check(net, seed)
    torch.save(cpu_state(net), out / "source.pt")
    res = {"arm": arm, "cfg": cfg, "cfg_detail": M.cfg() if cfg != "loopctl" else None,
           "design": "deep sparse-MoE loop (claude_moe_deep_net)", "seed": seed, "source_lr": lr,
           "source_steps": SOURCE_STEPS, "source_batch": SOURCE_BATCH, "source_guard_seed": GUARD_SEED,
           "weights": net.weight_count(), "persistent_coefficients": net.weight_count(),
           "active_per_cell_round": net.active_count() if hasattr(net, "active_count") else net.weight_count(),
           "fixed_depth": fixed_depth, "fixed_source_dev": fixed_counts, "plain_lr_sweep": sweep,
           "gradient_check": grad, "expert_gradient_check": experts, "old": old,
           "v1_pass": all(v["right"] >= 190 for v in old.values()),
           "route_source_guard": {k: route_stats(net, v[:32]) for k, v in D.old_panels(GUARD_SEED).items()},
           "loss_log": log, "train_seconds": train_seconds, "started_utc": started, "finished_utc": utc(),
           "run_meta": meta(dev), "source_pt_sha256": sha(out / "source.pt")}
    B.dump(out / "source.json", res)
    ck.unlink(missing_ok=True)
    print(json.dumps({"phase": "source_done", "cfg": cfg, "seed": seed, "lr": lr,
                      "old": {k: v["right"] for k, v in old.items()}, "v1_pass": res["v1_pass"],
                      "v2": grad["nonzero_all"], "seconds": round(train_seconds)}), flush=True)
    return res


def cmd_source(cfg, seed, dev, threads):
    """Pre-registered: train at 1e-3; only if that source fails V1 or V2, train once more at 5e-4. No maze is seen."""
    qpath = RUNS / f"{cfg}-s{seed}" / "qualified.json"
    if qpath.exists():
        print(f"skip: {qpath} exists", flush=True)
        return
    tried = []
    for lr in SOURCE_LRS:
        res = train_source(cfg, seed, dev, lr, threads)
        ok = bool(res["v1_pass"] and res["gradient_check"]["nonzero_all"])
        tried.append({"lr": lr, "folder": str(source_dir(cfg, seed, lr).relative_to(ROOT)), "v1_v2_pass": ok})
        if ok:
            break
    good = [t for t in tried if t["v1_v2_pass"]]
    rec = {"cfg": cfg, "seed": seed, "tried": tried, "qualified": bool(good),
           "folder": good[0]["folder"] if good else None, "utc": utc()}
    qpath.parent.mkdir(parents=True, exist_ok=True)
    B.dump(qpath, rec)
    print(json.dumps({"phase": "qualified", **rec}), flush=True)


# ------------------------------------------------------------------ ladder and holdout
def run_dir(cfg, seed, init):
    return EQR / f"{cfg}-{init}-s{seed}"


def cmd_dev(cfg, seed, init, dev, threads, loop_root, stages=True):
    out = run_dir(cfg, seed, init)
    if (out / "adapt.json").exists():
        print(f"skip: {out} adapt.json exists", flush=True)
        return
    src = qualified_dir(cfg, seed, loop_root)
    setup(dev, cfg, threads)
    arm = arm_of(cfg)
    panels, _ = D.panels()
    probe = panels["dev"][9][:32]
    routes_path = out / "routes.json"

    def stage_hook(net, where, name):
        if stages:
            torch.save(cpu_state(net), where / f"{name}.pt")
        rs = route_stats(net, probe) if arm == "loop" else None
        if rs is not None:
            rec = json.loads(routes_path.read_text()) if routes_path.exists() else {}
            rec[name] = rs
            B.dump(routes_path, rec)

    B.save_stage = stage_hook
    started = utc()
    L.job(arm, seed, init, src, out)
    a = json.loads((out / "adapt.json").read_text())
    a.update({"cfg": cfg, "stage_checkpoints_kept": stages, "run_meta": meta(dev), "started_utc": started,
              "finished_utc": utc(), "source_json_sha256": sha(src / "source.json")})
    if init == "pre":
        a["source_pt_sha256"] = sha(src / "source.pt")
    B.dump(out / "adapt.json", a)
    print(json.dumps({"phase": "dev_done", "cfg": cfg, "seed": seed, "init": init,
                      "right9": {k: v["9"]["right"] for k, v in a["rungs"].items()}}), flush=True)


def cmd_holdout(cfg, seed, init, dev, threads):
    out = run_dir(cfg, seed, init)
    if (out / "holdout.json").exists():
        print(f"skip: {out} holdout.json exists", flush=True)
        return
    a = json.loads((out / "adapt.json").read_text())
    if not a.get("stage_checkpoints_kept", True):
        raise SystemExit(f"NO-STAGES: {out} kept no stage checkpoints; it is a dev-only row")
    setup(dev, cfg, threads)
    EQ.holdout_job(arm_of(cfg), seed, init, out)
    h = json.loads((out / "holdout.json").read_text())
    h.update({"cfg": cfg, "run_meta": meta(dev), "finished_utc": utc()})
    B.dump(out / "holdout.json", h)
    print(json.dumps({"phase": "holdout_done", "cfg": cfg, "seed": seed, "init": init}), flush=True)


def cmd_phase(a):
    for item in PHASES[a.phase]:
        step, cfg, seed = item[:3]
        print(json.dumps({"phase": "start", "step": step, "cfg": cfg, "seed": seed,
                          "init": item[3] if len(item) > 3 else None, "utc": utc()}), flush=True)
        if step == "source":
            cmd_source(cfg, seed, a.device, a.threads)
        else:
            try:
                cmd_dev(cfg, seed, item[3], a.device, a.threads, a.loop_source_root, stages=(a.phase == 1))
            except SystemExit as e:        # an unqualified or missing source skips its ladder, never the phase
                if str(e).startswith(("SOURCE-NOT-QUALIFIED", "WAITING", "LOOP-SOURCE-MISMATCH", "--loop-source-root")):
                    print(json.dumps({"phase": "skipped", "cfg": cfg, "seed": seed, "why": str(e)}), flush=True)
                    continue
                raise
    print(json.dumps({"phase": f"phase{a.phase}_done", "utc": utc()}), flush=True)


# ------------------------------------------------------------------ smoke: GPU against CPU, and timing
SMOKE_MARKS = {"logit_max_abs_diff": 1e-3, "stop_prob_max_abs_diff": 1e-3, "route_agreement_min": 0.99,
               "update_rel_diff_all": 0.05, "update_rel_diff_all_after_3_sleep_steps": 0.08}


def sync(dev):
    if dev == "cuda":
        torch.cuda.synchronize()


def smoke_phase(dev, threads):
    """One device's numbers on a fresh main-config net (seeded on the CPU): forward, routing, 3 practice steps,
    2 maze batches (8 updates), 3 sleep steps."""
    plug = setup(dev, MAIN, threads)
    panels, banned = D.panels()
    dev9 = panels["dev"][9]
    torch.manual_seed(4242)
    net = plug.Net("loop")
    start = cpu_state(net)
    r = {"device": dev, "gpu": torch.cuda.get_device_name(0) if dev == "cuda" else None,
         "tf32_matmul": torch.backends.cuda.matmul.allow_tf32, "tf32_cudnn": torch.backends.cudnn.allow_tf32,
         "param_dtypes": sorted({str(p.dtype) for p in net.parameters()}),
         "param_device": str(next(net.parameters()).device), "start_state": start}
    net.eval()
    with torch.no_grad():
        t, s, _ = plug.tensors(dev9[:16])
        cells, stops = net.forward(t, s)
        r["cells"] = {str(i): cells[i].float().cpu() for i in (0, 7, 47)}
        r["stops"] = torch.stack([x.float().sigmoid() for x in stops], 1).cpu()
        r["routes"] = [x.clone() for x in net.route_trace(t, s, 8)]
    rng, round_rng = random.Random(77), random.Random(78)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=.1, betas=(.9, .95))
    for _ in range(3):
        net.train()
        loss = plug.train_loss(net, D.source_batch(rng, 64), round_rng)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.)
        opt.step()
    learner = plug.Learner(net, 1e-3)
    pool = EQ.make_pool(0, banned)[0]
    for i, batch in enumerate(EQ.batches(pool, 64, 0)):
        if i == 2:
            break
        learner.maze_batch(batch)
    r["state_after_updates"] = cpu_state(learner.net)
    old_steps = plug.SLEEP_STEPS
    plug.SLEEP_STEPS = 3
    learner.sleep(pool[:64], 64, D.replay_old())
    plug.SLEEP_STEPS = old_steps
    r["state_after_sleep"] = cpu_state(learner.net)
    return r


def time_config(dev, cfg, threads, reps=3):
    """Seconds per practice step, maze batch (4 updates), sleep step and 48-round inference of 32 mazes."""
    plug = setup(dev, cfg, threads)
    arm = arm_of(cfg)
    panels, banned = D.panels()
    torch.manual_seed(5)
    with torch.device("cpu"):
        practice = (M if cfg != "loopctl" else plug._mod).Practice(arm, 0, SOURCE_STEPS)
    practice.net.to(dev)
    rng = random.Random(7000000)

    def timed(fn, n):
        fn()
        sync(dev)
        t0 = time.monotonic()
        for _ in range(n):
            fn()
        sync(dev)
        return (time.monotonic() - t0) / n
    out = {"cfg": cfg, "weights": practice.net.weight_count(),
           "practice_step": timed(lambda: practice.step(D.source_batch(rng, SOURCE_BATCH)), 2 * reps)}
    learner = getattr(plug._mod, "Learner", B.Learner)(practice.net, 1e-3)
    pool = EQ.make_pool(0, banned)[0]
    batch = pool[:32]
    out["maze_batch"] = timed(lambda: learner.maze_batch(batch), reps)
    old_steps = (M.SLEEP_STEPS, B.SLEEP_STEPS)
    M.SLEEP_STEPS = B.SLEEP_STEPS = 2
    out["sleep_step"] = timed(lambda: learner.sleep(pool[:64], 1, D.replay_old()), 1) / 2
    M.SLEEP_STEPS, B.SLEEP_STEPS = old_steps
    for size in (7, 9, 11):
        items = panels["dev"][size][:24 if size == 7 else 32]
        out[f"infer_{size}"] = timed(lambda: B.score(learner.net, items, 16), 1)
    score_stage = out["infer_7"] + out["infer_9"] * 300 / 32 + out["infer_11"] * 300 / 32
    old_stage = 400 / 32 * out["infer_7"]                           # 400 small old-kind puzzles, roughly 7x7-sized
    out["projected_source_minutes"] = round((SOURCE_STEPS * out["practice_step"] + 3 * old_stage) / 60, 1)
    out["projected_ladder_minutes"] = round((4096 * out["maze_batch"] + 1024 * out["sleep_step"] +
                                             11 * score_stage + 5 * old_stage) / 60, 1)
    out["note"] = "suggested, not a result: short timing runs, projected linearly"
    return out


def flat(d, keys):
    return torch.cat([d[k].reshape(-1).double() for k in keys])


def compare(c, g):
    keys = [k for k in c["start_state"] if c["start_state"][k].is_floating_point()]
    out = {"start_state_identical": all(torch.equal(c["start_state"][k], g["start_state"][k]) for k in keys),
           "logit_max_abs_diff": {r: float((c["cells"][r] - g["cells"][r]).abs().max()) for r in c["cells"]},
           "stop_prob_max_abs_diff": float((c["stops"] - g["stops"]).abs().max())}
    same = [float((a.sort(-1).values == b.sort(-1).values).all(-1).double().mean()) for a, b in zip(c["routes"], g["routes"])]
    out["route_agreement_per_layer"] = same
    out["route_agreement_min"] = min(same)

    def rel(stage):
        dc = flat(c[stage], keys) - flat(c["start_state"], keys)
        dg = flat(g[stage], keys) - flat(c["start_state"], keys)
        per = {}
        for k in keys:
            nc = float((c[stage][k].double() - c["start_state"][k].double()).norm())
            if nc > 0:
                per[k] = float((g[stage][k].double() - c[stage][k].double()).norm()) / nc
        worst = max(per, key=per.get) if per else None
        return float((dg - dc).norm() / dc.norm()), (per[worst] if worst else 0.0), worst
    out["update_rel_diff_all"], out["update_rel_diff_worst_tensor"], out["worst_tensor"] = rel("state_after_updates")
    out["update_rel_diff_all_after_3_sleep_steps"] = rel("state_after_sleep")[0]
    m = SMOKE_MARKS
    checks = {
        "flags_strict_fp32": (not g["tf32_matmul"] and not g["tf32_cudnn"] and g["param_dtypes"] == ["torch.float32"]
                              and g["param_device"].startswith("cuda")),
        "same_start": out["start_state_identical"],
        "logits": max(out["logit_max_abs_diff"].values()) <= m["logit_max_abs_diff"],
        "stop_probs": out["stop_prob_max_abs_diff"] <= m["stop_prob_max_abs_diff"],
        "routing": out["route_agreement_min"] >= m["route_agreement_min"],
        "updates": out["update_rel_diff_all"] <= m["update_rel_diff_all"],
        "sleep_updates": out["update_rel_diff_all_after_3_sleep_steps"] <= m["update_rel_diff_all_after_3_sleep_steps"]}
    out["checks"] = checks
    out["PASS"] = all(checks.values())
    return out


def cmd_smoke(a):
    c = smoke_phase("cpu", a.threads)
    print(json.dumps({"phase": "cpu_done"}), flush=True)
    g = smoke_phase(a.device, a.threads)
    res = compare(c, g)
    res.update({"marks_fixed_in_advance": SMOKE_MARKS, "utc": utc(), "run_meta": meta(a.device)})
    B.dump(ART / "SMOKE-gpu.json", res)
    print(json.dumps({k: res[k] for k in ("PASS", "checks", "update_rel_diff_all", "worst_tensor",
                                        "update_rel_diff_worst_tensor", "update_rel_diff_all_after_3_sleep_steps",
                                        "route_agreement_min", "logit_max_abs_diff", "stop_prob_max_abs_diff")},
                     indent=1), flush=True)
    timing = {"utc": utc(), "run_meta": meta(a.device), "configs": {}}
    for cfg in (MAIN, "loopctl", "L16-E64", "L8-E128", "L8-dense-tot", "plain-big", "L2-E64"):
        timing["configs"][cfg] = time_config(a.device, cfg, a.threads)
        print(json.dumps(timing["configs"][cfg]), flush=True)
        B.dump(ART / "TIMING-gpu.json", timing)
    per = timing["configs"]
    main_cost = per[MAIN]["projected_source_minutes"] + per[MAIN]["projected_ladder_minutes"]
    timing["projected_hours"] = {
        "phase1": round((2 * main_cost + 2 * per["loopctl"]["projected_ladder_minutes"]) / 60, 1),
        "note": "suggested; phase 2 and 3 are estimated from these per-config numbers in the job report"}
    B.dump(ART / "TIMING-gpu.json", timing)
    if not res["PASS"]:
        raise SystemExit("SMOKE-FAIL (see SMOKE-gpu.json): PASSMARKS.md section 'Machine' applies")


# ------------------------------------------------------------------ selftest (CPU, no training, no maze score)
def cmd_selftest(a):
    torch.set_num_threads(a.threads)
    rep = {"utc": utc(), "torch": torch.__version__, "configs": {}}
    ok = True
    for cfg in M.CFGS:
        rep["configs"][cfg] = {k: v for k, v in M.describe(cfg).items() if k != "cfg"} | {"cfg": M.CFGS[cfg]}
    # 1. batched dispatch equals a naive per-cell computation, values and gradients
    torch.manual_seed(1)
    moe = M.MoE(256, 64, 8, 1, 64, 0.5)
    x = torch.randn(2, 49, 256, requires_grad=True)
    y = moe(x)
    fl = x.reshape(-1, 256)
    tp, ti = moe.router(fl).float().softmax(-1).topk(8, -1)
    gate = tp / tp.sum(-1, keepdim=True)
    ref = torch.stack([moe.shared(fl[n]) + sum(
        gate[n, j] * (F.gelu(fl[n] @ moe.w1[ti[n, j]] + moe.b1[ti[n, j]]) @ moe.w2[ti[n, j]] + moe.b2[ti[n, j]])
        for j in range(8)) for n in range(fl.shape[0])])
    gy = torch.randn_like(y)
    g2 = torch.autograd.grad((ref.view_as(y) * gy).sum(), (x, moe.w1, moe.router.weight), retain_graph=True)
    for path in ("padded", "segments"):          # both dispatch paths, values and gradients
        moe.path = path
        yp = moe(x)
        g1 = torch.autograd.grad((yp * gy).sum(), (x, moe.w1, moe.router.weight))
        rep[f"dispatch_{path}_value_max_abs_diff"] = float((yp.reshape(-1, 256) - ref).abs().max())
        rep[f"dispatch_{path}_grad_max_abs_diff"] = max(float((u - v).abs().max()) for u, v in zip(g1, g2))
        rep[f"batch_independence_{path}_max_abs_diff"] = float((moe(x[:1]) - yp[:1]).abs().max())
        ok &= rep[f"dispatch_{path}_value_max_abs_diff"] < 1e-5 and rep[f"dispatch_{path}_grad_max_abs_diff"] < 1e-4
        ok &= rep[f"batch_independence_{path}_max_abs_diff"] < 1e-6
    moe.path = "auto"
    # 2. the harness contract on the main config and one dense row: 48 cell and stop logits; gradient checks
    panels, _ = D.panels()
    for cfg in (MAIN, "L8-dense-act", "plain-big"):
        setup("cpu", cfg, a.threads)
        arm = arm_of(cfg)
        torch.manual_seed(0)
        net = B.N.Net(arm)
        t, s, _ = B.N.tensors(panels["dev"][9][:2])
        with torch.no_grad():
            cells, stops = net.forward(t, s)
        grad = B.gradient_check(net, 0)
        ex = expert_gradient_check(net, 0)
        rep[f"contract_{cfg}"] = {"cells": len(cells), "stops": len(stops), "cell_shape": list(cells[0].shape),
                                  "gradient_check": grad, "expert_gradient_check": ex}
        ok &= grad["nonzero_all"] and (len(cells), len(stops)) == ((48, 48) if arm == "loop" else (1, 0))
        # expert liveness is reported, not required: a fresh router sends the 12 distinct tokens of a sums
        # batch to only some experts (the dispatch-gradient test above checks every chosen expert's gradient)
    # 3. router losses are collected on gradient passes only, and cleared by the learner
    setup("cpu", MAIN, a.threads)
    net = B.N.Net("loop")
    lrn = M.Learner(net, 1e-3)
    batch = EQ.make_pool(0, D.panels()[1])[0][:4]
    before = [p.detach().clone() for p in net.parameters()]
    lrn.maze_batch(batch)
    rep["learner_steps_per_batch"] = lrn.steps
    rep["learner_router_terms_left"] = sum(len(m.aux) + len(m.z) for m in net.moes())
    rep["learner_changed_params"] = sum(not torch.equal(b, p) for b, p in zip(before, net.parameters()))
    ok &= lrn.steps == 4 and rep["learner_router_terms_left"] == 0
    rep["selftest"] = "ok" if ok else "FAIL"
    B.dump(ART / "selftest.json", rep)
    print(json.dumps({k: v for k, v in rep.items() if k != "configs"}, indent=1, default=str))
    print(json.dumps({c: [v["stored"], v["active_per_cell_round"]] for c, v in rep["configs"].items()}))
    if not ok:
        raise SystemExit("SELFTEST-FAIL")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("selftest", "smoke", "source", "dev", "holdout", "phase"))
    ap.add_argument("--cfg", default=MAIN, choices=sorted(M.CFGS) + ["loopctl"])
    ap.add_argument("--seed", type=int, choices=(0, 1), default=0)
    ap.add_argument("--init", choices=("pre", "fresh"), default="pre")
    ap.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--phase", type=int, choices=(1, 2, 3))
    ap.add_argument("--no-stages", action="store_true")
    ap.add_argument("--loop-source-root", type=Path)
    a = ap.parse_args()
    if a.cmd == "selftest":
        cmd_selftest(a)
    elif a.cmd == "smoke":
        cmd_smoke(a)
    elif a.cmd == "source":
        cmd_source(a.cfg, a.seed, a.device, a.threads)
    elif a.cmd == "dev":
        cmd_dev(a.cfg, a.seed, a.init, a.device, a.threads, a.loop_source_root, stages=not a.no_stages)
    elif a.cmd == "holdout":
        cmd_holdout(a.cfg, a.seed, a.init, a.device, a.threads)
    else:
        cmd_phase(a)
