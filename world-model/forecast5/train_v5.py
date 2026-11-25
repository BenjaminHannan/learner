"""PROBLEM-7 Forecast5 (Rung 1 / Rank 3) Trainer & Evaluator.

Trains strictly on k=1 real transitions from train_dn.npz.
Evaluates open-loop k=1, 3, 5 rollouts via forecast5/scorer.py on dev (legacy 1000..1015).
REFUSES any path containing 'sealed' unless BOTH --eval-only AND --allow-sealed are passed.
Enforces >= 12.0 GiB free disk guard before training and before saving checkpoints.

Arms (exact pinned ablations from ONE script):
  bundle         : K1 (signal_path) + K2 (act_film + bounded imagine) + K3 (RowLNDecoder + residual-matched loss)
  no_signal_path : K2 + K3 only (leave-one-out ablation of K1)
  no_act_film    : K1 + K3 only (leave-one-out ablation of K2 intercom broadcast; action enters via canonical action row only)
  abs_loss_only  : K1 + K2 + RowLNDecoder, drops residual-matched loss l_img_res (trains with l_img_abs only)
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import torch

MIN_FREE_GIB = 12.0
PINNED_SEALED_TEST_SHA256 = "74c421c42c113067e6f065f2343dfefec5372055dbbe54fc34d641f666a85e3f"

ARM_CONFIGS = {
    "bundle": dict(use_signal_path=True, use_act_film=True, use_res_loss=True),
    "no_signal_path": dict(use_signal_path=False, use_act_film=True, use_res_loss=True),
    "no_act_film": dict(use_signal_path=True, use_act_film=False, use_res_loss=True),
    "abs_loss_only": dict(use_signal_path=True, use_act_film=True, use_res_loss=False),
}


def setup_paths(core_dir: str | None) -> None:
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    candidates = []
    if core_dir:
        candidates.append(Path(core_dir))
    candidates.extend([
        here.parent / "wm-harness",
        Path("<m3-project>/PROBLEM-7/wm-harness"),
        Path("~/learner-ops/ds-copies/problem-1/harness-sp/vendor"),
        here.parent / "wm",
    ])
    for c in candidates:
        if c.exists() and str(c) not in sys.path:
            sys.path.append(str(c))


def check_disk(path: str) -> float:
    target = path if os.path.exists(path) else os.path.dirname(os.path.abspath(path))
    while not os.path.exists(target):
        target = os.path.dirname(target)
    free_gib = shutil.disk_usage(target).free / (1024 ** 3)
    print(f"[DISK] {target}: {free_gib:.2f} GiB free (floor {MIN_FREE_GIB:.1f} GiB)", flush=True)
    if free_gib < MIN_FREE_GIB:
        sys.exit(f"ABORT: free disk {free_gib:.2f} GiB < {MIN_FREE_GIB:.1f} GiB floor")
    return free_gib


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
    if is_sealed_path(path):
        if not (eval_only and allow_sealed):
            raise RuntimeError(
                f"REFUSED: {path} (resolved: {os.path.realpath(path)}) is a sealed test split! "
                f"Sealed test may ONLY be read with BOTH --eval-only AND --allow-sealed."
            )


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def changed_weighted_mse(pred: torch.Tensor, target: torch.Tensor, prev: torch.Tensor) -> torch.Tensor:
    c = ((target - prev).abs().mean(-1, keepdim=True) > 0.02).float()
    return (((pred - target) ** 2) * c).sum() / (c.sum() * 3.0 + 1e-6)


def clip_and_check_grad_norm(parameters, max_norm: float = 1.0) -> torch.Tensor:
    """Clip global grad norm and abort loudly before opt.step() if any gradient is non-finite."""
    grad_norm = torch.nn.utils.clip_grad_norm_(parameters, max_norm)
    if not torch.isfinite(grad_norm):
        raise RuntimeError(f"Non-finite grad_norm={float(grad_norm)} before opt.step()")
    return grad_norm


def compute_train_step_loss(model, x_prev, x_t, act, x_next, *, use_res_loss: bool):
    """Strictly k=1 real-transition joint loss (start board detached on imagination branch)."""
    st_t, aux_read = model.real_board(x_prev, x_t)
    with torch.no_grad():
        tgt_rows = model.real_board(x_t, x_next)[0].rows

    x_rec_t = model.dec(st_t.rows[:, 0])
    l_rec = ((x_rec_t - x_t) ** 2).mean() + 0.5 * changed_weighted_mse(x_rec_t, x_t, x_prev)

    # Detach start board AND stop-grad anchor decoder call so l_img_res never fights l_rec
    st_det = dataclasses.replace(st_t, rows=st_t.rows.detach())
    out_img = model.imagine_step(st_det, act, wm_grad=True)
    x_img_abs = model.dec(out_img.next_rows[:, 0])
    x_start_dec_det = x_rec_t.detach()
    x_img_res = x_t + (x_img_abs - x_start_dec_det)

    l_img_res = ((x_img_res - x_next) ** 2).mean()
    l_img_abs = ((x_img_abs - x_next) ** 2).mean()
    copy_mse = ((x_t - x_next) ** 2).mean().clamp_min(1e-8)

    row_var = tgt_rows.var(dim=0, correction=0).mean().clamp_min(1e-3)
    l_row_rel = ((out_img.next_rows - tgt_rows) ** 2).mean() / row_var
    aux_total = aux_read + out_img.aux_loss

    # Matched total imagination pixel weight (1.25) across bundle and abs_loss_only
    if use_res_loss:
        loss = 1.0 * l_rec + 1.0 * l_img_res + 0.25 * l_img_abs + 0.005 * l_row_rel + 0.01 * aux_total
    else:
        loss = 1.0 * l_rec + 1.25 * l_img_abs + 0.005 * l_row_rel + 0.01 * aux_total

    metrics = {
        "loss": float(loss.detach()),
        "l_rec": float(l_rec.detach()),
        "l_img_res": float(l_img_res.detach()),
        "l_img_abs": float(l_img_abs.detach()),
        "img_over_copy": float(l_img_res.detach() / copy_mse),
        "l_row_rel": float(l_row_rel.detach()),
        "aux": float(aux_total.detach()),
    }
    return loss, metrics, st_t.rows.detach()


@torch.no_grad()
def evaluate_model(model, train_split, eval_split, device, batch_size: int = 128, extra_meta: dict | None = None):
    """Run open-loop k=1,3,5 evaluation (real + per-step shuffled actions) and score with scorer.py."""
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
        xi, ai, _, _, ti = scorer.windows(eval_split, k)
        acts_k = scorer.action_values(eval_split["actions"], ai, k)
        s_acts_k = scorer.action_values(sh_acts, ai, k)

        P_list, Pabs_list, Ps_list = [], [], []
        c_abs_list, c_res_list = [], []

        for b in range(0, len(xi), batch_size):
            sl = slice(b, min(b + batch_size, len(xi)))
            i = xi[sl]
            tpos = ti[sl]
            h_idx = np.where(tpos > 0, i - 1, i)
            x_prev = _f(h_idx)
            x0 = _f(i)
            st0, _ = model.real_board(x_prev, x0)

            ak_t = torch.from_numpy(acts_k[sl].astype(np.int64)).to(device)
            sak_t = torch.from_numpy(s_acts_k[sl].astype(np.int64)).to(device)
            out_r = model.rollout(st0, x0, ak_t)
            out_s = model.rollout(st0, x0, sak_t)
            P_list.append(out_r["pred_res"].cpu().double().numpy())
            Pabs_list.append(out_r["pred_abs"].cpu().double().numpy())
            Ps_list.append(out_s["pred_res"].cpu().double().numpy())

            if k == 1:
                x1 = _f(i + 1)
                st1, _ = model.real_board(x0, x1)
                dec0 = model.dec(st0.rows[:, 0])
                dec1 = model.dec(st1.rows[:, 0])
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
    # Non-gating diagnostic: pred_abs E/B at k=1,3,5 (clarifies abs_loss_only vs residual subtraction)
    diag_abs = {}
    for k in (1, 3, 5):
        xi = scorer.windows(eval_split, k)[0]
        yk = hfr[xi + k].astype(np.float64)
        e_abs = float(((preds_abs_by_k[k] - yk) ** 2).sum())
        diag_abs[f"k{k}"] = e_abs / max(res[f"k{k}"]["B"], 1e-12)
    res["diag_pred_abs_E_over_B"] = diag_abs
    return res, preds_by_k


def lr_factor(step: int, total_steps: int, warmup: int = 100, min_ratio: float = 0.1) -> float:
    if step < warmup:
        return float(step + 1) / float(max(warmup, 1))
    prog = float(step - warmup) / float(max(total_steps - warmup, 1))
    prog = min(max(prog, 0.0), 1.0)
    return min_ratio + (1.0 - min_ratio) * 0.5 * (1.0 + math.cos(math.pi * prog))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=sorted(ARM_CONFIGS.keys()), default="bundle")
    ap.add_argument("--size", default="P7toy")
    ap.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    ap.add_argument("--core-dir", default=None)
    ap.add_argument("--train-data", default="data/train_dn.npz")
    ap.add_argument("--eval-data", default="../wm-harness/data/heldout.npz")
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--wd", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-minutes", type=float, default=28.0)
    ap.add_argument("--eval-only", default=None, help="Path to saved model.pt to evaluate without training")
    ap.add_argument("--allow-sealed", action="store_true", help="Explicit opt-in required with --eval-only to touch sealed_test.npz")
    ap.add_argument("--save-forecasts", action="store_true")
    ap.add_argument("--skip-disk-check", action="store_true")
    ap.add_argument("--timing-only", action="store_true", help="Run exact training loop for --steps without saving or scoring (unscored MPS calibration)")
    args = ap.parse_args()

    guard_sealed_path(args.train_data, eval_only=False, allow_sealed=False)
    guard_sealed_path(args.eval_data, eval_only=bool(args.eval_only), allow_sealed=bool(args.allow_sealed))

    setup_paths(args.core_dir)
    import scorer
    import sizes
    from premonition_core_v2.board_swarm import active_param_count
    from model_v5 import WorldModelV5, verify_canonical_board_swarm

    os.makedirs(args.out, exist_ok=True)
    if not args.skip_disk_check:
        check_disk(args.out)

    board_sha = verify_canonical_board_swarm()
    arm_cfg = ARM_CONFIGS[args.arm]

    torch.manual_seed(args.seed)
    dev = torch.device(args.device)
    cfg = sizes.make_cfg(args.size)
    model = WorldModelV5(
        cfg,
        use_signal_path=arm_cfg["use_signal_path"],
        use_act_film=arm_cfg["use_act_film"],
        seed=args.seed,
    ).to(dev)

    c_tot, c_exp, c_act = active_param_count(model.cell)
    n_total = sum(p.numel() for p in model.parameters())
    n_dec = sum(p.numel() for p in model.dec.parameters())
    print(
        f"[INIT] arm={args.arm} size={args.size} dev={args.device} seed={args.seed} "
        f"cell_active={c_act:,} cell_total={c_tot:,} dec={n_dec:,} model_total={n_total:,} "
        f"board_swarm_sha={board_sha[:12]}",
        flush=True,
    )

    tr = scorer.load_split(args.train_data)
    ev = scorer.load_split(args.eval_data)
    xi1, ai1, _, _, t1 = scorer.windows(tr, 1)
    print(
        f"[DATA] train={args.train_data} ({len(xi1)} k1 wins) eval={args.eval_data} "
        f"({len(scorer.windows(ev, 1)[0])} k1 wins)",
        flush=True,
    )

    train_meta = {
        "arm": args.arm,
        "arm_cfg": arm_cfg,
        "size": args.size,
        "seed": args.seed,
        "device": args.device,
        "train_data": os.path.abspath(args.train_data),
        "train_data_sha256": sha256_file(args.train_data),
        "eval_data": os.path.abspath(args.eval_data),
        "eval_data_sha256": sha256_file(args.eval_data),
        "board_swarm_sha256": board_sha,
        "params": {
            "cell_total": int(c_tot),
            "cell_expert": int(c_exp),
            "cell_active": int(c_act),
            "dec_total": int(n_dec),
            "model_total": int(n_total),
        },
    }

    if args.eval_only:
        ck = torch.load(args.eval_only, map_location=dev, weights_only=False)
        ck_arm = ck.get("meta", {}).get("arm")
        if ck_arm != args.arm:
            raise ValueError(f"Checkpoint arm {ck_arm!r} != CLI --arm {args.arm!r}")
        model.load_state_dict(ck["model"], strict=True)
        train_meta["eval_only_ckpt"] = os.path.abspath(args.eval_only)
        train_meta["trained_steps"] = ck.get("steps", None)
        print(f"[EVAL-ONLY] loaded {args.eval_only} (arm={ck_arm})", flush=True)
    else:
        opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.wd)
        sch = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: lr_factor(s, args.steps))
        rng = np.random.default_rng(args.seed)
        t0 = time.time()
        t_steady = None
        warmup_timing = min(5, max(args.steps // 4, 1))
        done = 0
        grad_step0 = {}
        burial_step0 = None
        burial_final = None
        model.train()

        for s in range(args.steps):
            if s == warmup_timing:
                if dev.type == "mps":
                    torch.mps.synchronize()
                t_steady = time.time()
            j = rng.integers(0, len(xi1), size=args.batch)
            i = xi1[j]
            tp = t1[j]
            h = np.where(tp > 0, i - 1, i)
            x_prev = torch.from_numpy(tr["frames"][h].astype(np.float32)).to(dev)
            x_t = torch.from_numpy(tr["frames"][i].astype(np.float32)).to(dev)
            x_next = torch.from_numpy(tr["frames"][i + 1].astype(np.float32)).to(dev)
            act = torch.from_numpy(tr["actions"][ai1[j]].astype(np.int64)).to(dev)

            loss, m, rows_t = compute_train_step_loss(
                model, x_prev, x_t, act, x_next, use_res_loss=arm_cfg["use_res_loss"]
            )
            if not torch.isfinite(loss):
                raise RuntimeError(f"Non-finite loss at step {s}: {m}")

            opt.zero_grad(set_to_none=True)
            loss.backward()
            if s == 0:
                grad_step0["action_emb"] = float(model.action_emb.weight.grad.norm())
                if model.act_film is not None:
                    grad_step0["act_film"] = float(model.act_film.weight.grad.norm())
                burial_step0 = model.board_burial_stats(rows_t)
                print(
                    f"[STEP0] grad={grad_step0} burial={burial_step0['burial_ratio']:.2f} "
                    f"(static={burial_step0['static_rms']:.4f}, spread={burial_step0['spread_rms']:.4f})",
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
                    f"img/copy {m['img_over_copy']:.3f} row_rel {m['l_row_rel']:.4f} "
                    f"w_row {0.005 * m['l_row_rel']:.5f} gnorm {float(grad_norm):.3f} t {el:.1f}s",
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
                f"Refusing to save/score an under-stepped arm."
            )

        if args.timing_only:
            steady_steps = done - warmup_timing
            steady_sec = (time.time() - t_steady) if (t_steady is not None and steady_steps > 0) else train_sec
            ms_per_step = (steady_sec / max(steady_steps, 1)) * 1000.0
            print(
                f"[TIMING] arm={args.arm} steps={done} total={train_sec:.2f}s "
                f"steady({steady_steps}st)={steady_sec:.2f}s ms/step={ms_per_step:.1f} "
                f"proj_2000={ms_per_step*2000/60000:.2f}m proj_2500={ms_per_step*2500/60000:.2f}m "
                f"proj_3000={ms_per_step*3000/60000:.2f}m",
                flush=True,
            )
            return

        # Final board burial stats on 128 train windows
        model.eval()
        with torch.no_grad():
            j_b = np.random.default_rng(7).choice(len(xi1), min(128, len(xi1)), replace=False)
            i_b = xi1[j_b]
            h_b = np.where(t1[j_b] > 0, i_b - 1, i_b)
            rows_b = model.real_board(
                torch.from_numpy(tr["frames"][h_b].astype(np.float32)).to(dev),
                torch.from_numpy(tr["frames"][i_b].astype(np.float32)).to(dev),
            )[0].rows
            burial_final = model.board_burial_stats(rows_b)

        train_meta.update({
            "requested_steps": int(args.steps),
            "trained_steps": done,
            "train_wall_seconds": round(train_sec, 2),
            "grad_step0": grad_step0,
            "burial_step0": burial_step0,
            "burial_final": burial_final,
        })
        if not args.skip_disk_check:
            check_disk(args.out)
        ckpt_path = os.path.join(args.out, "model.pt")
        torch.save({"model": model.state_dict(), "steps": done, "meta": train_meta}, ckpt_path)
        print(f"[SAVED] {ckpt_path} ({done} steps, {train_sec:.1f}s, burial_final={burial_final['burial_ratio']:.2f})", flush=True)

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
        f"ceil_abs={k1['ceiling_abs_E_over_B']:.4f} shuf={k1['shuffle_pooled']:.3f}/{k5['shuffle_pooled']:.3f} "
        f"worlds={res['worlds_k1_shuffle']}/{res['worlds_k5_shuffle']}/{res['worlds_both']} "
        f"pcs={k1['pcs90_pred']}/{k1['pcs90_real']} std_ok={res['std_ok']} "
        f"bo_err={bo['model']['mean_err']:.4f} (fb={bo['model']['false_block_rate']:.4f}, fo={bo['model']['false_open_rate']:.4f}, "
        f"base={bo['strongest_baseline_mean_err']:.4f}, cut={bo['mean_err_reduction_frac']*100:.1f}%) "
        f"legacy={res['verdict']} rung1={res['rung1_verdict']} r3_wrong={res['rank3_proved_wrong']} eval_t={eval_sec:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
