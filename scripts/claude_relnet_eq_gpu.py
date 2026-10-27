#!/usr/bin/env python3
"""Run the relation-net race (and its loop control) on the GPU, or on the CPU with the same code.

Nothing in the harness is edited. This driver runs the harness's own pieces (claude_fewex_eq_bench's pool, batches and
holdout job; claude_patch_eq_ladder.job, the resumable ladder, which is the harness's adapt_job plus checkpoints;
claude_fewex_bench's scoring and Learner.sleep) with two changes that are only about where tensors live:
  * torch.set_default_device(dev): every tensor the harness builds (torch.tensor, arange, zeros) lands on the device;
  * the plug-in's Net(arm) is built on the CPU (so the initial weights of a --init fresh copy come from the CPU RNG
    exactly as in the CPU runs) and then moved to the device.
cuda mode is strict fp32: TF32 off for matmul and cudnn, highest matmul precision, no autocast, deterministic algorithms
requested (warn_only). Stage checkpoints (k*.pt, sleep*.pt) are written as CPU tensors, so the harness's own
`holdout` and load_model read them anywhere. ADDENDUM-1.md (artifacts/claude-relnet-eq-20260928) governs what it may be
used for; a GPU run is not bit-identical to a CPU run, and a resumed GPU run is not guaranteed bit-identical to an
uninterrupted one (untested).

Arms: relnet (claude_relnet_eq_plugin, sources ART/runs/relnet-s{S}) and loopctl (the baseline loop, claude_fewex_net,
source = the qualified loop source in --loop-source-root/qual-loop-s{S}, the same net the recorded loop-s{S}-pre run used).
Outputs, all under ART = artifacts/claude-relnet-eq-20260928:
  eq-runs/relnet-{pre,fresh}-s{S}/   eq-runs/loopctl-s{S}/     (adapt.json, partial.json, k*.pt, sleep*.pt, holdout.json)
  eq-runs/sleepdraws/{relnet|loopctl}-s{S}-k{64|16384}-d{1|2}.json
  SMOKE-gpu.json (smoke)

  python -B scripts/claude_relnet_eq_gpu.py check
  python -B scripts/claude_relnet_eq_gpu.py smoke  --device cuda [--out SMOKE-gpu.json]
  python -B scripts/claude_relnet_eq_gpu.py dev    --seed S --device cuda|cpu --loop-source-root DIR
  python -B scripts/claude_relnet_eq_gpu.py holdout --seed S --device cuda|cpu
Every command is idempotent: a finished ladder, draw or holdout is skipped; an unfinished ladder resumes from its
32-batch checkpoint. Rerun the same command after any interruption.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_fewex_eq_bench as EQ  # noqa: E402
import claude_patch_eq_ladder as L  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "claude-relnet-eq-20260928"
PLUGINS = {"relnet": "claude_relnet_eq_plugin", "loopctl": "claude_fewex_net"}
OFFSET = {1: 101, 2: 202}            # same sleep-seed offsets as claude_fewex_distill_sleep.py / H13's ADDENDUM-2
GUARD_SEED = D.SOURCE_SEED + 300


def utc():
    return subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True).strip() if os.name != "nt" else \
        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def save_stage_cpu(net, out, name):
    torch.save({k: v.detach().cpu() for k, v in net.state_dict().items()}, out / f"{name}.pt")


def setup(dev, arm, threads=2):
    torch.set_num_threads(threads)
    if dev == "cuda":
        if not torch.cuda.is_available():
            raise SystemExit("NO-CUDA")
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.set_float32_matmul_precision("highest")
        torch.use_deterministic_algorithms(True, warn_only=True)
    torch.set_default_device(dev)
    plug = Plug(importlib.import_module(PLUGINS[arm]), dev)
    B.N = EQ.B.N = plug
    B.save_stage = save_stage_cpu
    return plug


def meta(dev):
    return {"device": dev, "torch": torch.__version__,
            "gpu": torch.cuda.get_device_name(0) if dev == "cuda" else None,
            "tf32_matmul": torch.backends.cuda.matmul.allow_tf32, "tf32_cudnn": torch.backends.cudnn.allow_tf32,
            "float32_matmul_precision": torch.get_float32_matmul_precision(),
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
            "driver": "scripts/claude_relnet_eq_gpu.py"}


def source_dir(arm, seed, loop_root):
    if arm == "relnet":
        return ART / "runs" / f"relnet-s{seed}"
    if loop_root is None:
        raise SystemExit("--loop-source-root is required for the loop control")
    return Path(loop_root) / f"qual-loop-s{seed}"


def run_dir(arm, seed, init):
    return ART / "eq-runs" / (f"relnet-{init}-s{seed}" if arm == "relnet" else f"loopctl-s{seed}")


def verify_sources(loop_root=None):
    """sha256 of the relation-net sources against checkpoints-sha256.txt (committed with ADDENDUM-1)."""
    bad = []
    for line in (ART / "checkpoints-sha256.txt").read_text().split("\n"):
        if not line.strip():
            continue
        sha, rel = line.split()
        f = ART / rel
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != sha:
            bad.append(rel)
    if bad:
        raise SystemExit(f"SOURCE-NETS-MISMATCH {bad}")
    print(f"source nets ok: {len(bad) == 0} (sha256 match checkpoints-sha256.txt)", flush=True)
    if loop_root:
        for s in (0, 1):
            f = Path(loop_root) / f"qual-loop-s{s}" / "source.pt"
            print(f"loop control source seed {s}: {f} sha256 {hashlib.sha256(f.read_bytes()).hexdigest()}", flush=True)


# ------------------------------------------------------------------ ladder, draws, holdout
def do_ladder(arm, seed, init, dev, loop_root):
    out = run_dir(arm, seed, init)
    if (out / "adapt.json").exists():
        print(f"skip: {out} adapt.json exists", flush=True)
        return
    setup(dev, arm)
    L.job("loop", seed, init, source_dir(arm, seed, loop_root), out)
    a = json.loads((out / "adapt.json").read_text())
    a["run_meta"] = meta(dev)
    a["finished_utc"] = utc()
    B.dump(out / "adapt.json", a)


def do_draw(arm, seed, k, d, dev, loop_root):
    out = ART / "eq-runs" / "sleepdraws" / f"{arm}-s{seed}-k{k}-d{d}.json"
    if out.exists():
        print(f"skip: {out} exists", flush=True)
        return
    setup(dev, arm)
    ck = run_dir(arm, seed, "pre")
    start, started = time.monotonic(), utc()
    depth = EQ.identity_source(source_dir(arm, seed, loop_root), "loop", seed)["fixed_depth"]
    _, banned = D.panels()
    pool, _, digest = EQ.make_pool(seed, banned)
    old, replay = D.old_panels(), D.replay_old()
    net = B.load_model(ck / f"k{k}.pt", "loop")
    learner = getattr(B.N, "Learner", B.Learner)(copy.deepcopy(net), 1e-3)
    sleep_seed = seed + k + OFFSET[d]
    seconds = learner.sleep(pool[:k], sleep_seed, replay)
    if learner.steps != B.SLEEP_STEPS:
        raise ValueError("sleep step count")
    res = {"arm": arm, "seed": seed, "k": k, "draw": d, "sleep_seed": sleep_seed, "updates": learner.steps,
           "fixed_depth": depth, "support_sha256": digest, "started_utc": started, "student_ckpt": str(ck / f"k{k}.pt"),
           "old": {n: v["right"] for n, v in EQ.old_scores(learner.net, old, depth).items()},
           "sleep_seconds": seconds, "seconds_total": time.monotonic() - start, "finished_utc": utc(), "run_meta": meta(dev)}
    B.dump(out, res)
    print(json.dumps({"phase": "draw_done", "arm": arm, "seed": seed, "k": k, "draw": d, "old": res["old"],
                      "seconds": round(res["seconds_total"])}), flush=True)


def cmd_dev(a):
    """Per seed, in the order that gets the comparator early: relnet pre + its draws, loop control + its draws, relnet fresh."""
    verify_sources(a.loop_source_root)
    plan = [("relnet", "pre"), ("loopctl", "pre"), ("relnet", "fresh")]
    for arm, init in plan:
        print(json.dumps({"phase": "start", "arm": arm, "init": init, "seed": a.seed, "utc": utc()}), flush=True)
        do_ladder(arm, a.seed, init, a.device, a.loop_source_root)
        if init == "pre":
            for k in (64, 16384):
                for d in (1, 2):
                    do_draw(arm, a.seed, k, d, a.device, a.loop_source_root)
    print(json.dumps({"phase": "dev_done", "seed": a.seed, "utc": utc()}), flush=True)


def cmd_holdout(a):
    """The harness's own holdout_job, once per run. Needs the dev records committed first (Director's rule)."""
    for arm, init in (("relnet", "pre"), ("loopctl", "pre"), ("relnet", "fresh")):
        out = run_dir(arm, a.seed, init)
        if (out / "holdout.json").exists():
            print(f"skip: {out} holdout.json exists", flush=True)
            continue
        setup(a.device, arm)
        EQ.holdout_job("loop", a.seed, init, out)
        print(json.dumps({"phase": "holdout_done", "arm": arm, "init": init, "seed": a.seed, "utc": utc()}), flush=True)


# ------------------------------------------------------------------ smoke: GPU against CPU
SMOKE_MARKS = {"logit_max_abs_diff": 1e-3, "stop_prob_max_abs_diff": 1e-3, "count_diff_before": 1, "count_diff_after": 2,
               "update_rel_diff_all_8_updates": 0.02, "update_rel_diff_per_tensor_8_updates": 0.10,
               "update_rel_diff_all_after_3_sleep_steps": 0.05}


def sync(dev):
    if dev == "cuda":
        torch.cuda.synchronize()


def phase(dev, seed, threads):
    """One device's numbers: forward logits on 16 dev 9x9 mazes, counts, 2 maze batches (8 updates), 3 sleep steps."""
    plug = setup(dev, "relnet", threads)
    src = ART / "runs" / f"relnet-s{seed}"
    depth = EQ.identity_source(src, "loop", seed)["fixed_depth"]
    panels, banned = D.panels()
    dev9, dev11, dev7 = panels["dev"][9], panels["dev"][11], panels["dev"][7]
    net = B.load_model(src / "source.pt", "loop")
    r = {"device": dev, "torch": torch.__version__, "gpu": torch.cuda.get_device_name(0) if dev == "cuda" else None,
         "tf32_matmul": torch.backends.cuda.matmul.allow_tf32, "tf32_cudnn": torch.backends.cudnn.allow_tf32,
         "param_dtypes": sorted({str(p.dtype) for p in net.parameters()}), "param_device": str(next(net.parameters()).device)}
    guard = D.old_panels(GUARD_SEED)
    net.eval()
    with torch.no_grad():
        t, s, _ = plug.tensors(dev9[:16])
        cells, stops = net.forward(t, s)
        r["cells"] = {str(i): cells[i].float().cpu() for i in (0, 7, 47)}
        r["stops"] = torch.stack([x.float().sigmoid() for x in stops], 1).cpu()
    r["counts_before"] = {"sums4": B.score(net, guard["sums4"], depth), "grids5": B.score(net, guard["grids5"], depth),
                          "maze9_first64": B.score(net, dev9[:64], depth)}
    pool = EQ.make_pool(seed, banned)[0]
    learner = getattr(plug, "Learner")(copy.deepcopy(net), 1e-3)
    times = []
    for i, batch in enumerate(EQ.batches(pool, 64, seed)):
        if i == 2:
            break
        sync(dev)
        t0 = time.monotonic()
        learner.maze_batch(batch)
        sync(dev)
        times.append(time.monotonic() - t0)
    r["maze_batch_seconds"] = times
    r["state_after_updates"] = {k: v.detach().cpu().clone() for k, v in learner.net.state_dict().items()}
    r["counts_after"] = {"maze9_first64": B.score(learner.net, dev9[:64], depth)}
    old_steps = B.SLEEP_STEPS
    B.SLEEP_STEPS = 3
    sync(dev)
    t0 = time.monotonic()
    learner.sleep(pool[:64], seed + 64, D.replay_old())
    sync(dev)
    r["sleep_3_steps_seconds"] = time.monotonic() - t0
    B.SLEEP_STEPS = old_steps
    r["state_after_sleep"] = {k: v.detach().cpu().clone() for k, v in learner.net.state_dict().items()}
    r["start_state"] = {k: v.detach().cpu().clone() for k, v in B.load_model(src / "source.pt", "loop").state_dict().items()}
    # timing of the pieces the ladder repeats (only meaningful on the GPU)
    net.eval()
    tm = {}
    for name, items in (("infer_32_7x7", dev7[:24]), ("infer_32_9x9", dev9[:32]), ("infer_32_11x11", dev11[:32])):
        with torch.no_grad():
            tt, ss, _ = plug.tensors(items)
            sync(dev)
            t0 = time.monotonic()
            net.infer_rounds(tt, ss, 48)
            sync(dev)
            tm[name] = time.monotonic() - t0
    r["inference_seconds"] = tm
    return r


def flat(d, keys):
    return torch.cat([d[k].reshape(-1).double() for k in keys])


def compare(c, g):
    keys = [k for k in c["start_state"] if c["start_state"][k].is_floating_point()]
    out = {}
    out["logit_max_abs_diff"] = {r: float((c["cells"][r] - g["cells"][r]).abs().max()) for r in c["cells"]}
    out["stop_prob_max_abs_diff"] = float((c["stops"] - g["stops"]).abs().max())
    out["counts_before"] = {n: {f: [c["counts_before"][n][f], g["counts_before"][n][f]] for f in ("right", "fixed_right")}
                            for n in c["counts_before"]}
    out["counts_after"] = {n: {f: [c["counts_after"][n][f], g["counts_after"][n][f]] for f in ("right", "fixed_right")}
                           for n in c["counts_after"]}

    def rel(stage):
        dc = flat(c[stage], keys) - flat(c["start_state"], keys)
        dg = flat(g[stage], keys) - flat(c["start_state"], keys)
        per = {}
        for k in keys:
            nc = float((c[stage][k].double() - c["start_state"][k].double()).norm())
            if nc > 0:
                per[k] = float((g[stage][k].double() - c[stage][k].double()).norm()) / nc
        return float((dg - dc).norm() / dc.norm()), max(per.values()) if per else 0.0, max(per, key=per.get) if per else None
    a_all, a_per, a_name = rel("state_after_updates")
    s_all, s_per, s_name = rel("state_after_sleep")
    out["update_rel_diff_all_8_updates"], out["update_rel_diff_per_tensor_8_updates"] = a_all, a_per
    out["worst_tensor_8_updates"] = a_name
    out["update_rel_diff_all_after_3_sleep_steps"] = s_all
    m = SMOKE_MARKS
    checks = {
        "flags_strict_fp32": (not g["tf32_matmul"] and not g["tf32_cudnn"] and g["param_dtypes"] == ["torch.float32"]
                              and g["param_device"].startswith("cuda")),
        "logits": max(out["logit_max_abs_diff"].values()) <= m["logit_max_abs_diff"],
        "stop_probs": out["stop_prob_max_abs_diff"] <= m["stop_prob_max_abs_diff"],
        "counts_before": all(abs(v[f][0] - v[f][1]) <= m["count_diff_before"] for v in out["counts_before"].values() for f in v),
        "counts_after": all(abs(v[f][0] - v[f][1]) <= m["count_diff_after"] for v in out["counts_after"].values() for f in v),
        "update_all": a_all <= m["update_rel_diff_all_8_updates"],
        "update_per_tensor": a_per <= m["update_rel_diff_per_tensor_8_updates"],
        "sleep_update_all": s_all <= m["update_rel_diff_all_after_3_sleep_steps"]}
    out["checks"] = checks
    out["PASS"] = all(checks.values())
    return out


def cmd_smoke(a):
    c = phase("cpu", a.seed, a.threads)
    print(json.dumps({"phase": "cpu_done", "maze_batch_seconds": c["maze_batch_seconds"]}), flush=True)
    g = phase(a.device, a.seed, a.threads)
    res = compare(c, g)
    res.update({"seed": a.seed, "marks_fixed_in_advance": SMOKE_MARKS, "utc": utc(),
                "cpu": {k: c[k] for k in ("torch", "maze_batch_seconds", "sleep_3_steps_seconds", "inference_seconds")},
                "gpu": {k: g[k] for k in ("torch", "gpu", "maze_batch_seconds", "sleep_3_steps_seconds", "inference_seconds")}})
    t = g["maze_batch_seconds"][-1]
    i = g["inference_seconds"]
    res["projected_gpu_seconds_per_dev_run"] = round(
        4096 * t + 1024 * g["sleep_3_steps_seconds"] / 3 +
        11 * (i["infer_32_7x7"] * 24 / 32 * 1 + i["infer_32_9x9"] * 300 / 32 + i["infer_32_11x11"] * 300 / 32))
    res["projection_note"] = ("suggested, not a result: TIMING-ESTIMATE.md's formula with the GPU times measured here "
                              "(4096 maze batches, 1024 sleep steps, 11 scoring stages of 24 7x7 + 300 9x9 + 300 11x11)")
    B.dump(a.out, res)
    print(json.dumps({k: res[k] for k in ("PASS", "checks", "update_rel_diff_all_8_updates", "update_rel_diff_per_tensor_8_updates",
                                        "worst_tensor_8_updates", "update_rel_diff_all_after_3_sleep_steps",
                                        "logit_max_abs_diff", "stop_prob_max_abs_diff", "counts_before", "counts_after",
                                        "projected_gpu_seconds_per_dev_run")}, indent=1), flush=True)
    if not res["PASS"]:
        raise SystemExit("SMOKE-FAIL (see " + str(a.out) + "); the CPU plan in ADDENDUM-1.md applies")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("check", "smoke", "dev", "holdout"))
    ap.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    ap.add_argument("--seed", type=int, choices=(0, 1), default=0)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--loop-source-root", type=Path)
    ap.add_argument("--out", type=Path, default=ART / "SMOKE-gpu.json")
    a = ap.parse_args()
    if a.cmd == "check":
        verify_sources(a.loop_source_root)
        print(json.dumps(meta(a.device), indent=1))
    elif a.cmd == "smoke":
        verify_sources()
        cmd_smoke(a)
    elif a.cmd == "dev":
        cmd_dev(a)
    else:
        cmd_holdout(a)
