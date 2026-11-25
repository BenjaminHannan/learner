"""PROBLEM-7 Forecast6 (Rank 6) Trainer & Evaluator.

Trains a dedicated 100%-learned 2D Spatial Conv World Model strictly on k=1 real
transitions from train_dn.npz.
Evaluates open-loop k=1, 3, 5 rollouts via bit-identical forecast6/scorer.py
(sha 6ff1c135c0eeb208...) on dev (legacy 1000..1015).

Hard safety & anti-leakage guards:
  - Verifies forecast6/scorer.py exact SHA-256 at runtime before scoring.
  - REFUSES any path resolving to sealed_test.npz (via path, symlink, OR SHA-256)
    unless BOTH --eval-only AND --allow-sealed are passed.
  - When --allow-sealed is passed, verifies eval_data matches pinned sealed SHA-256.
  - Enforces >= 12.0 GiB free disk before training and before saving checkpoints.
  - Enforces M3 power rule before MPS use: AC Power OR battery >= 35% (via pmset).
  - Fails loudly (non-zero exit, no save/score) if done < args.steps, loss is
    non-finite, or grad_norm is non-finite before opt.step().
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

MIN_FREE_GIB = 12.0
MIN_MPS_BATTERY_PCT = 35
PINNED_SEALED_TEST_SHA256 = "74c421c42c113067e6f065f2343dfefec5372055dbbe54fc34d641f666a85e3f"
PINNED_CANONICAL_BOARD_SWARM_SHA256 = "8ffc3fb860547551f10e10a135bcd088176fe0f7b569125c123e0e797e0b6b1d"
ARCH_TAG = "R6_spatial_conv_unet"
CEILING_DEFINITION = (
    "abs: decode(encode(x_{t+1})) [real next frame reconstructed through same encoder+decoder, "
    "zero actions/dynamics]; res: x_t + (decode(encode(x_{t+1})) - decode(encode(x_t)))"
)
RANK6_AE_CEILING_TRIGGER = 0.20


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_disk(path: str) -> float:
    target = path if os.path.exists(path) else os.path.dirname(os.path.abspath(path))
    while not os.path.exists(target):
        target = os.path.dirname(target)
    free_gib = shutil.disk_usage(target).free / (1024 ** 3)
    print(f"[DISK] {target}: {free_gib:.2f} GiB free (floor {MIN_FREE_GIB:.1f} GiB)", flush=True)
    if free_gib < MIN_FREE_GIB:
        sys.exit(f"ABORT: free disk {free_gib:.2f} GiB < {MIN_FREE_GIB:.1f} GiB floor")
    return free_gib


def parse_pmset_batt(output: str) -> tuple[bool, int | None]:
    """Parse `pmset -g batt` stdout -> (on_ac_power, battery_pct_or_None)."""
    on_ac = "AC Power" in output
    m = re.search(r"(\d+)%", output)
    pct = int(m.group(1)) if m else None
    return on_ac, pct


def check_mps_power(pmset_output: str | None = None) -> tuple[bool, int | None]:
    """Enforce AC Power OR battery >= 35% before any MPS execution."""
    if pmset_output is None:
        proc = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"ABORT: pmset -g batt failed (rc={proc.returncode}): {proc.stderr.strip()}")
        pmset_output = proc.stdout
    on_ac, pct = parse_pmset_batt(pmset_output)
    if on_ac:
        print(f"[POWER] AC Power (battery={pct}%) -> OK for MPS", flush=True)
        return on_ac, pct
    if pct is not None and pct >= MIN_MPS_BATTERY_PCT:
        print(f"[POWER] Battery {pct}% >= {MIN_MPS_BATTERY_PCT}% -> OK for MPS", flush=True)
        return on_ac, pct
    raise RuntimeError(
        f"ABORT: MPS power guard tripped (on_ac={on_ac}, battery={pct}% < {MIN_MPS_BATTERY_PCT}%). "
        f"Connect AC power or charge to >= {MIN_MPS_BATTERY_PCT}% before running MPS."
    )


def is_sealed_path(path: str) -> bool:
    """Detect sealed test split by resolved realpath (following symlinks) OR pinned SHA-256."""
    real = os.path.realpath(path)
    if "sealed" in os.path.basename(real).lower() or "sealed" in real.lower():
        return True
    if "sealed" in os.path.basename(path).lower() or "sealed" in os.path.abspath(path).lower():
        return True
    if os.path.isfile(real) and sha256_file(real) == PINNED_SEALED_TEST_SHA256:
        return True
    return False


def guard_sealed_path(path: str, eval_only: bool, allow_sealed: bool) -> None:
    sealed = is_sealed_path(path)
    if sealed:
        if not (eval_only and allow_sealed):
            raise RuntimeError(
                f"REFUSED: {path} (resolved: {os.path.realpath(path)}) is a sealed test split! "
                f"Sealed test may ONLY be read with BOTH --eval-only AND --allow-sealed."
            )
        if os.path.isfile(os.path.realpath(path)):
            have = sha256_file(os.path.realpath(path))
            if have != PINNED_SEALED_TEST_SHA256:
                raise RuntimeError(
                    f"REFUSED: sealed eval file SHA {have} != pinned {PINNED_SEALED_TEST_SHA256}"
                )
    elif allow_sealed:
        raise RuntimeError(
            f"REFUSED: --allow-sealed was passed, but {path} is NOT the pinned sealed_test.npz!"
        )


def clip_and_check_grad_norm(parameters, max_norm: float = 1.0) -> torch.Tensor:
    """Clip global grad norm and abort loudly before opt.step() if any gradient is non-finite."""
    grad_norm = torch.nn.utils.clip_grad_norm_(parameters, max_norm)
    if not torch.isfinite(grad_norm):
        raise RuntimeError(f"Non-finite grad_norm={float(grad_norm)} before opt.step()")
    return grad_norm


def compute_train_step_loss(
    model,
    x_t: torch.Tensor,
    act: torch.Tensor,
    x_next: torch.Tensor,
    *,
    w_lat: float = 0.05,
):
    """Strictly k=1 real-transition joint loss (start latent detached on dynamics branch).

    Encoder receives ONLY `l_rec` (imagination never corrupts encoding).
    Dynamics receives ONLY `l_img_res + 0.25 * l_img_abs + w_lat * l_lat` (zero l_rec starvation).
    """
    z_t = model.encode(x_t)
    with torch.no_grad():
        z_next_tgt = model.encode(x_next)

    x_rec_t = model.decode(z_t)
    l_rec = ((x_rec_t - x_t) ** 2).mean()

    # Detach start latent AND anchor decode so dynamics never fights encoder/reconstruction
    z_next_pred = model.imagine_step(z_t.detach(), act, wm_grad=True)
    x_img_abs = model.decode(z_next_pred)
    x_img_res = x_t + (x_img_abs - x_rec_t.detach())

    l_img_res = ((x_img_res - x_next) ** 2).mean()
    l_img_abs = ((x_img_abs - x_next) ** 2).mean()
    l_lat = ((z_next_pred - z_next_tgt) ** 2).mean()
    copy_mse = ((x_t - x_next) ** 2).mean().clamp_min(1e-8)

    loss = 1.0 * l_rec + 1.0 * l_img_res + 0.25 * l_img_abs + float(w_lat) * l_lat
    metrics = {
        "loss": float(loss.detach()),
        "l_rec": float(l_rec.detach()),
        "l_img_res": float(l_img_res.detach()),
        "l_img_abs": float(l_img_abs.detach()),
        "l_lat": float(l_lat.detach()),
        "img_over_copy": float(l_img_res.detach() / copy_mse),
    }
    return loss, metrics, z_t.detach()


@torch.no_grad()
def evaluate_model(
    model,
    train_split: dict,
    eval_split: dict,
    device: torch.device,
    batch_size: int = 128,
    extra_meta: dict | None = None,
):
    """Run strictly open-loop k=1,3,5 evaluation (real + per-step shuffled actions).

    For every horizon k in (1, 3, 5), rollout sees ONLY x0 = eval_split["frames"][xi]
    and the k actions — NEVER any intermediate true frames x_{t+1..t+k-1}.
    Ceiling is computed exclusively at k=1 as decode(encode(x_{t+1})) [abs] and
    x_t + (decode(encode(x_{t+1})) - decode(encode(x_t))) [res].
    """
    import scorer

    model.eval()
    hfr = eval_split["frames"]
    sh_acts = scorer.shuffle_actions_per_step(eval_split, seed=43)

    def _f(idx):
        return torch.from_numpy(hfr[idx].astype(np.float32)).to(device)

    preds_by_k = {}
    preds_abs_by_k = {}
    shuf_preds_by_k = {}
    ceil_abs_k1 = None
    ceil_res_k1 = None

    for k in (1, 3, 5):
        xi, ai, _, _, _ = scorer.windows(eval_split, k)
        acts_k = scorer.action_values(eval_split["actions"], ai, k)
        s_acts_k = scorer.action_values(sh_acts, ai, k)

        P_list, Pabs_list, Ps_list = [], [], []
        c_abs_list, c_res_list = [], []

        for b in range(0, len(xi), batch_size):
            sl = slice(b, min(b + batch_size, len(xi)))
            i = xi[sl]
            x0 = _f(i)
            ak_t = torch.from_numpy(acts_k[sl].astype(np.int64)).to(device)
            sak_t = torch.from_numpy(s_acts_k[sl].astype(np.int64)).to(device)

            out_r = model.rollout(x0, ak_t, wm_grad=False)
            out_s = model.rollout(x0, sak_t, wm_grad=False)
            P_list.append(out_r["pred_res"].cpu().double().numpy())
            Pabs_list.append(out_r["pred_abs"].cpu().double().numpy())
            Ps_list.append(out_s["pred_res"].cpu().double().numpy())

            if k == 1:
                x1 = _f(i + 1)
                dec0 = model.decode(out_r["z0"])
                dec1 = model.decode(model.encode(x1))
                c_abs_list.append(dec1.cpu().double().numpy())
                c_res_list.append((x0 + (dec1 - dec0)).cpu().double().numpy())

        preds_by_k[k] = np.concatenate(P_list, axis=0)
        preds_abs_by_k[k] = np.concatenate(Pabs_list, axis=0)
        shuf_preds_by_k[k] = np.concatenate(Ps_list, axis=0)
        if k == 1:
            ceil_abs_k1 = np.concatenate(c_abs_list, axis=0)
            ceil_res_k1 = np.concatenate(c_res_list, axis=0)

    res = scorer.score_predictions(
        train_split,
        eval_split,
        preds_by_k,
        shuf_preds_by_k,
        ceiling_abs_pred_k1=ceil_abs_k1,
        ceiling_res_pred_k1=ceil_res_k1,
        extra_meta=extra_meta,
    )
    diag_abs = {}
    for k in (1, 3, 5):
        xi = scorer.windows(eval_split, k)[0]
        yk = hfr[xi + k].astype(np.float64)
        e_abs = float(((preds_abs_by_k[k] - yk) ** 2).sum())
        diag_abs[f"k{k}"] = e_abs / max(res[f"k{k}"]["B"], 1e-12)
    res["diag_pred_abs_E_over_B"] = diag_abs

    # Rank-6 per-seed verdict reuses scorer.py rung1_verdict verbatim (unchanged bars, incl. ceiling <= 0.70);
    # diag_ae_ceiling_le_0.20 is logged strictly as a non-gating 2D AE sanity diagnostic.
    res["diag_ae_ceiling_le_0.20"] = bool(res["k1"]["ceiling_abs_E_over_B"] <= RANK6_AE_CEILING_TRIGGER)
    res["rank6_verdict"] = res["rung1_verdict"]
    return res, preds_by_k


def lr_factor(step: int, total_steps: int, warmup: int = 100, min_ratio: float = 0.1) -> float:
    w = min(warmup, max(total_steps // 10, 1)) if total_steps < warmup else warmup
    if step < w:
        return float(step + 1) / float(max(w, 1))
    prog = float(step - w) / float(max(total_steps - w, 1))
    prog = min(max(prog, 0.0), 1.0)
    return min_ratio + (1.0 - min_ratio) * 0.5 * (1.0 + math.cos(math.pi * prog))


def main():
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))

    from model_v6 import MODEL_SIZES, SpatialWorldModelV6, verify_pinned_scorer

    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=sorted(MODEL_SIZES.keys()), default="R6conv")
    ap.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    ap.add_argument("--train-data", default="../wm5/data/train_dn.npz")
    ap.add_argument("--eval-data", default="../wm-harness/data/heldout.npz")
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=5000)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--wd", type=float, default=1e-4)
    ap.add_argument("--w-lat", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-minutes", type=float, default=14.0)
    ap.add_argument("--eval-only", default=None, help="Path to saved model.pt to evaluate without training")
    ap.add_argument("--allow-sealed", action="store_true", help="Explicit opt-in required with --eval-only to touch sealed_test.npz")
    ap.add_argument("--save-forecasts", action="store_true")
    ap.add_argument("--skip-disk-check", action="store_true")
    ap.add_argument("--skip-power-check", action="store_true", help="Test-only override; never pass on M3 MPS runs")
    ap.add_argument("--timing-only", action="store_true", help="Run exact training loop for --steps without saving or scoring")
    args = ap.parse_args()

    scorer_sha = verify_pinned_scorer(here / "scorer.py")
    guard_sealed_path(args.train_data, eval_only=False, allow_sealed=False)
    guard_sealed_path(args.eval_data, eval_only=bool(args.eval_only), allow_sealed=bool(args.allow_sealed))

    if args.device == "mps" and not args.skip_power_check:
        check_mps_power()

    import scorer

    os.makedirs(args.out, exist_ok=True)
    if not args.skip_disk_check:
        check_disk(args.out)

    torch.manual_seed(args.seed)
    dev = torch.device(args.device)
    model = SpatialWorldModelV6(size=args.size).to(dev)
    pcounts = model.param_counts()
    print(
        f"[INIT] arch={ARCH_TAG} size={args.size} dev={args.device} seed={args.seed} "
        f"enc={pcounts['encoder']:,} dec={pcounts['decoder']:,} act={pcounts['action_emb']:,} "
        f"dyn={pcounts['dynamics']:,} total={pcounts['model_total']:,} scorer_sha={scorer_sha[:12]}",
        flush=True,
    )

    tr = scorer.load_split(args.train_data)
    ev = scorer.load_split(args.eval_data)
    xi1, ai1, _, _, _ = scorer.windows(tr, 1)
    print(
        f"[DATA] train={args.train_data} ({len(xi1)} k1 wins) eval={args.eval_data} "
        f"({len(scorer.windows(ev, 1)[0])} k1 wins)",
        flush=True,
    )

    train_meta = {
        "arch": ARCH_TAG,
        "size": args.size,
        "model_cfg": model.cfg,
        "seed": args.seed,
        "device": args.device,
        "w_lat": float(args.w_lat),
        "lr": float(args.lr),
        "wd": float(args.wd),
        "batch": int(args.batch),
        "ceiling_definition": CEILING_DEFINITION,
        "scorer_sha256": scorer_sha,
        "train_data": os.path.abspath(args.train_data),
        "train_data_sha256": sha256_file(args.train_data),
        "eval_data": os.path.abspath(args.eval_data),
        "eval_data_sha256": sha256_file(args.eval_data),
        "params": pcounts,
    }

    if args.eval_only:
        ck = torch.load(args.eval_only, map_location=dev, weights_only=False)
        ck_meta = ck.get("meta", {})
        if ck_meta.get("arch") != ARCH_TAG:
            raise ValueError(f"Checkpoint arch {ck_meta.get('arch')!r} != expected {ARCH_TAG!r}")
        if ck_meta.get("size") != args.size:
            raise ValueError(f"Checkpoint size {ck_meta.get('size')!r} != CLI --size {args.size!r}")
        model.load_state_dict(ck["model"], strict=True)
        train_meta["eval_only_ckpt"] = os.path.abspath(args.eval_only)
        train_meta["eval_only_ckpt_sha256"] = sha256_file(args.eval_only)
        train_meta["trained_steps"] = ck.get("steps", None)
        train_meta["ckpt_seed"] = ck_meta.get("seed", None)
        if ck_meta.get("seed") is not None:
            train_meta["seed"] = ck_meta["seed"]
        print(f"[EVAL-ONLY] loaded {args.eval_only} (size={ck_meta.get('size')}, seed={ck_meta.get('seed')})", flush=True)
    else:
        opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.wd)
        sch = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: lr_factor(s, args.steps))
        rng = np.random.default_rng(args.seed)
        t0 = time.time()
        t_steady = None
        warmup_timing = min(10, max(args.steps // 5, 1))
        done = 0
        grad_step0 = {}
        lat_step0 = None
        lat_final = None
        model.train()

        for s in range(args.steps):
            if s == warmup_timing:
                if dev.type == "mps":
                    torch.mps.synchronize()
                t_steady = time.time()

            j = rng.integers(0, len(xi1), size=args.batch)
            i = xi1[j]
            x_t = torch.from_numpy(tr["frames"][i].astype(np.float32)).to(dev)
            x_next = torch.from_numpy(tr["frames"][i + 1].astype(np.float32)).to(dev)
            act = torch.from_numpy(tr["actions"][ai1[j]].astype(np.int64)).to(dev)

            loss, m, z_t = compute_train_step_loss(model, x_t, act, x_next, w_lat=args.w_lat)
            if not torch.isfinite(loss):
                raise RuntimeError(f"Non-finite loss at step {s}: {m}")

            opt.zero_grad(set_to_none=True)
            loss.backward()
            if s == 0:
                grad_step0["action_emb"] = float(model.action_emb.weight.grad.norm())
                grad_step0["encoder"] = float(
                    math.sqrt(sum(float(p.grad.pow(2).sum()) for p in model.encoder.parameters() if p.grad is not None))
                )
                grad_step0["dynamics"] = float(
                    math.sqrt(sum(float(p.grad.pow(2).sum()) for p in model.dynamics.parameters() if p.grad is not None))
                )
                grad_step0["decoder"] = float(
                    math.sqrt(sum(float(p.grad.pow(2).sum()) for p in model.decoder.parameters() if p.grad is not None))
                )
                lat_step0 = model.latent_stats(z_t)
                print(
                    f"[STEP0] grad={ {k: round(v, 5) for k, v in grad_step0.items()} } "
                    f"lat_burial={lat_step0['burial_ratio']:.2f} "
                    f"(static={lat_step0['static_rms']:.4f}, spread={lat_step0['spread_rms']:.4f})",
                    flush=True,
                )

            grad_norm = clip_and_check_grad_norm(model.parameters(), 1.0)
            opt.step()
            sch.step()
            done = s + 1

            if s < 3 or (s + 1) % 250 == 0 or (s + 1) == args.steps:
                el = time.time() - t0
                print(
                    f"step {s:4d} loss {m['loss']:.5f} rec {m['l_rec']:.5f} "
                    f"img_res {m['l_img_res']:.5f} img_abs {m['l_img_abs']:.5f} "
                    f"img/copy {m['img_over_copy']:.3f} lat {m['l_lat']:.5f} "
                    f"gnorm {float(grad_norm):.3f} t {el:.1f}s",
                    flush=True,
                )

            if args.max_minutes > 0.0 and (time.time() - t0) >= args.max_minutes * 60.0 and done < args.steps:
                print(f"[CAP] max-minutes {args.max_minutes} reached at step {done}/{args.steps}", flush=True)
                break

        if dev.type == "mps":
            torch.mps.synchronize()
        train_sec = time.time() - t0

        if done < args.steps:
            raise RuntimeError(
                f"INCOMPLETE RUN: completed {done}/{args.steps} steps before hitting "
                f"max-minutes={args.max_minutes} cap ({train_sec:.1f}s). "
                f"Refusing to save/score an under-stepped run."
            )

        if args.timing_only:
            steady_steps = done - warmup_timing
            steady_sec = (time.time() - t_steady) if (t_steady is not None and steady_steps > 0) else train_sec
            ms_per_step = (steady_sec / max(steady_steps, 1)) * 1000.0
            print(
                f"[TIMING] size={args.size} steps={done} total={train_sec:.2f}s "
                f"steady({steady_steps}st)={steady_sec:.2f}s ms/step={ms_per_step:.1f} "
                f"proj_3000={ms_per_step*3000/60000:.2f}m proj_4000={ms_per_step*4000/60000:.2f}m "
                f"proj_5000={ms_per_step*5000/60000:.2f}m proj_6000={ms_per_step*6000/60000:.2f}m",
                flush=True,
            )
            return

        model.eval()
        with torch.no_grad():
            j_b = np.random.default_rng(7).choice(len(xi1), min(128, len(xi1)), replace=False)
            z_b = model.encode(torch.from_numpy(tr["frames"][xi1[j_b]].astype(np.float32)).to(dev))
            lat_final = model.latent_stats(z_b)

        train_meta.update({
            "requested_steps": int(args.steps),
            "trained_steps": done,
            "train_wall_seconds": round(train_sec, 2),
            "grad_step0": grad_step0,
            "lat_step0": lat_step0,
            "lat_final": lat_final,
        })
        if not args.skip_disk_check:
            check_disk(args.out)
        ckpt_path = os.path.join(args.out, "model.pt")
        torch.save({"model": model.state_dict(), "steps": done, "meta": train_meta}, ckpt_path)
        print(
            f"[SAVED] {ckpt_path} ({done} steps, {train_sec:.1f}s, lat_burial={lat_final['burial_ratio']:.2f})",
            flush=True,
        )

    t_eval = time.time()
    res, preds_by_k = evaluate_model(model, tr, ev, dev, extra_meta=train_meta)
    eval_sec = time.time() - t_eval
    res["eval_wall_seconds"] = round(eval_sec, 2)

    split_tag = "sealed" if is_sealed_path(args.eval_data) else "dev"
    score_path = os.path.join(args.out, f"score_{split_tag}.json")
    with open(score_path, "w") as f:
        json.dump(res, f, indent=2)

    if args.save_forecasts:
        fc_path = os.path.join(args.out, f"forecasts_{split_tag}.npz")
        np.savez(
            fc_path,
            pred_k1=preds_by_k[1].astype(np.float16),
            pred_k3=preds_by_k[3].astype(np.float16),
            pred_k5=preds_by_k[5].astype(np.float16),
        )

    k1, k3, k5 = res["k1"], res["k3"], res["k5"]
    bo = k1["block_open"]
    print(
        f"[SCORE {split_tag}] E/B={k1['E_over_B']:.4f}/{k3['E_over_B']:.4f}/{k5['E_over_B']:.4f} "
        f"(base={k1['strongest_baseline_E_over_B']:.4f}/{k3['strongest_baseline_E_over_B']:.4f}/{k5['strongest_baseline_E_over_B']:.4f}) "
        f"ceil_abs={k1['ceiling_abs_E_over_B']:.4f} ceil_res={k1['ceiling_res_E_over_B']:.4f} "
        f"shuf={k1['shuffle_pooled']:.3f}/{k5['shuffle_pooled']:.3f} "
        f"worlds={res['worlds_k1_shuffle']}/{res['worlds_k5_shuffle']}/{res['worlds_both']} "
        f"pcs={k1['pcs90_pred']}/{k1['pcs90_real']} std_ok={res['std_ok']} "
        f"bo_err={bo['model']['mean_err']:.4f} (fb={bo['model']['false_block_rate']:.4f}, fo={bo['model']['false_open_rate']:.4f}, "
        f"base={bo['strongest_baseline_mean_err']:.4f}, cut={bo['mean_err_reduction_frac']*100:.1f}%) "
        f"legacy={res['verdict']} rung1={res['rung1_verdict']} rank6={res['rank6_verdict']} eval_t={eval_sec:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
