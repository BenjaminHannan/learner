"""Fit and score a real-transition world model on recorded Crafter frames."""
import argparse
import dataclasses
import json
import os
import time

import numpy as np
import torch
import torch.nn as nn

from premonition_core_v2.board_swarm import BoardCell, BoardSwarmConfig, active_param_count
from premonition_core_v2.interfaces import Context, Source, rms_level

H = W = 16
N_PATCH = 16
PATCH = 48


class WorldModel(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        D = cfg.dims.d_board
        R = cfg.dims.board_rows
        self.D, self.R = D, R
        self.cell = BoardCell(cfg)
        self.reader = nn.Linear(PATCH, D)
        self.pos = nn.Parameter(torch.empty(N_PATCH, D))
        nn.init.normal_(self.pos, std=0.02)
        self.action_emb = nn.Embedding(17, D)
        pre = [nn.BatchNorm1d(R * D, affine=False, eps=1e-3)] if DEC_NORM else []  # retry 2: standardize board per feature
        self.head = nn.Sequential(*pre, nn.Linear(R * D, 256), nn.GELU(), nn.Linear(256, H * W * 3))
        nn.init.zeros_(self.head[-1].weight)
        nn.init.zeros_(self.head[-1].bias)

    def encode(self, frames):
        B = frames.shape[0]
        p = frames.reshape(B, 4, 4, 4, 4, 3).permute(0, 1, 3, 2, 4, 5).reshape(B, N_PATCH, PATCH)
        tok = rms_level(self.reader(p) + self.pos[None])
        ctx = Context(
            tokens=tok,
            mask=torch.ones(B, N_PATCH, dtype=torch.bool, device=tok.device),
            support=torch.ones(B, N_PATCH, device=tok.device),
            source=torch.full((B, N_PATCH), int(Source.SIGHT), dtype=torch.long, device=tok.device),
            age_s=torch.zeros(B, N_PATCH, device=tok.device),
            epoch=torch.zeros(B, dtype=torch.long, device=tok.device),
            q_hash=torch.zeros(B, dtype=torch.long, device=tok.device),
        )
        enc = self.cell.encode_context(ctx)
        enc.frame_rows = tok  # retry 2: unit-RMS frame tokens, pinned into 16 fast rows by read() when PIN_FRAME
        return enc

    def decode(self, rows):
        return self.head(rows.flatten(1)).reshape(-1, H, W, 3)

    def read(self, state, enc):
        if PIN_FRAME:
            ns = self.cell.ns
            rows = state.rows.clone(); rows[:, :, ns:ns + N_PATCH] = enc.frame_rows[:, None]
            pin = state.row_pin.clone(); pin[:, :, ns:ns + N_PATCH] = True
            state = dataclasses.replace(state, rows=rows, row_pin=pin)
        out = self.cell.run_tick(state, enc, noise=False)
        out = self.cell.run_tick(out.state, enc, noise=False)
        return out.state


ROW_TARGET = "continued"
PIN_FRAME = False
DEC_NORM = False


def forward_batch(model, xt, xn, act):
    enc_t = model.encode(xt)
    enc_n = model.encode(xn)
    state = model.cell.init_state(xt.shape[0], 1, device=xt.device, dtype=torch.float32)
    state_t = model.read(state, enc_t)
    state_n = model.read(state_t, enc_n)
    imagine = model.cell.imagine(state_t, enc_t, model.action_emb(act), wm_grad=True)
    delta = xn - xt
    l_pred = ((model.decode(imagine.next_rows) - delta) ** 2).mean()
    if ROW_TARGET == "fresh":  # retry 1: board after a FRESH read of frame t+1 (no tick-count drift)
        tgt = model.read(model.cell.init_state(xt.shape[0], 1, device=xt.device, dtype=torch.float32), enc_n).rows
    else:
        tgt = state_n.rows
    l_rows = ((imagine.next_rows - tgt.detach()) ** 2).mean()
    l_real = ((model.decode(state_n.rows) - delta) ** 2).mean()
    return l_pred + l_rows + l_real + 0.01 * imagine.aux_loss


def fit(model, split, steps, max_minutes, device, batch=64, lr=3e-4):
    xi, ai, _, _, _ = windows(split, 1)
    frames, actions = split["frames"], split["actions"]
    n = len(xi)
    rng = np.random.default_rng(42)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    start, done = time.time(), 0
    for step in range(steps):
        t0 = time.time()
        idx = rng.integers(0, n, size=batch)
        xt = torch.from_numpy(frames[xi[idx]].astype(np.float32)).to(device)
        xn = torch.from_numpy(frames[xi[idx] + 1].astype(np.float32)).to(device)
        act = torch.from_numpy(actions[ai[idx]].astype(np.int64)).to(device)
        loss = forward_batch(model, xt, xn, act)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        done = step + 1
        if step < 20:
            print(f"step {step} loss {loss.item():.5f} {time.time() - t0:.3f} sec/step", flush=True)
        elif (step + 1) % 100 == 0:
            print(f"step {step} loss {loss.item():.5f} {time.time() - t0:.3f} sec/step", flush=True)
        if time.time() - start >= max_minutes * 60:
            print(f"max-minutes reached after {done} steps")
            break
    return done


def load_split(path):
    with np.load(path) as d:
        return {k: d[k] for k in d.files}


def episode_index(d):
    eid = d["episode_id"]
    n = len(eid)
    cuts = np.flatnonzero(np.r_[True, eid[1:] != eid[:-1]])
    if len(cuts) != len(np.unique(eid)):
        raise ValueError("episodes are not contiguous")
    ends = np.r_[cuts[1:], n]
    lengths = ends - cuts
    action_offsets = np.r_[0, np.cumsum(lengths - 1)[:-1]]
    return cuts, ends, action_offsets


def windows(d, k):
    starts, ends, aoffs = episode_index(d)
    xi, ai, world, episode, t = [], [], [], [], []
    for s, e, ao in zip(starts, ends, aoffs):
        n = (e - s) - k
        if n <= 0:
            continue
        xi.append(np.arange(s, s + n))
        ai.append(np.arange(ao, ao + n))
        world.append(np.full(n, d["world_id"][s], dtype=np.int64))
        episode.append(np.full(n, d["episode_id"][s], dtype=np.int64))
        t.append(np.arange(n, dtype=np.int64))
    cat = np.concatenate
    return cat(xi), cat(ai), cat(world), cat(episode), cat(t)


def moved_mask(frames, xi):
    a = frames[xi].astype(np.float32)
    b = frames[xi + 1].astype(np.float32)
    return ((b - a) ** 2).mean((1, 2, 3)) > 1e-6


def sse(pred, true):
    return (((pred.astype(np.float32) - true.astype(np.float32)) ** 2).sum((1, 2, 3))).astype(np.float64)


@torch.no_grad()
def predict(model, frames, xi, act_values, k, device, batch=64):
    out = np.empty((len(xi), H, W, 3), dtype=np.float32)
    for s in range(0, len(xi), batch):
        sl = slice(s, min(s + batch, len(xi)))
        x = torch.from_numpy(frames[xi[sl]].astype(np.float32)).to(device)
        enc = model.encode(x)
        state = model.cell.init_state(x.shape[0], 1, device=device, dtype=torch.float32)
        state = model.read(state, enc)
        a = torch.from_numpy(act_values[sl].astype(np.int64)).to(device)
        pred = x
        for j in range(k):
            imagine = model.cell.imagine(state, enc, model.action_emb(a[:, j]), wm_grad=True)
            pred = pred + model.decode(imagine.next_rows)
            state = dataclasses.replace(state, rows=imagine.next_rows)
        out[sl] = pred.cpu().numpy()
    return out


@torch.no_grad()
def ceiling_pred(model, frames, xi, device, batch=64):
    out = np.empty((len(xi), H, W, 3), dtype=np.float32)
    for s in range(0, len(xi), batch):
        sl = slice(s, min(s + batch, len(xi)))
        x = torch.from_numpy(frames[xi[sl]].astype(np.float32)).to(device)
        xn = torch.from_numpy(frames[xi[sl] + 1].astype(np.float32)).to(device)
        enc_t = model.encode(x)
        state = model.cell.init_state(x.shape[0], 1, device=device, dtype=torch.float32)
        state_t = model.read(state, enc_t)
        state_n = model.read(state_t, model.encode(xn))
        out[sl] = (x + model.decode(state_n.rows)).cpu().numpy()
    return out


def action_values(actions, ai, k):
    return actions[ai[:, None] + np.arange(k)[None, :]]


def shuffle_actions(d, seed=43):
    a = d["actions"].copy()
    starts, ends, aoffs = episode_index(d)
    aw = np.empty(len(a), dtype=np.int64)
    for s, e, ao in zip(starts, ends, aoffs):
        aw[ao:ao + (e - s - 1)] = d["world_id"][s]
    rng = np.random.default_rng(seed)
    for w in np.unique(aw):
        idx = np.flatnonzero(aw == w)
        a[idx] = a[idx][rng.permutation(len(idx))]
    return a


def blend_a(train, k, mean):
    xi, _, _, _, _ = windows(train, k)
    x = train["frames"][xi].astype(np.float32)
    y = train["frames"][xi + k].astype(np.float32)
    xm = x - mean
    den = np.sum(xm * xm, dtype=np.float64)
    return float(np.sum((y - mean) * xm, dtype=np.float64) / den) if den > 0 else 0.0


def pcs90(x):
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean(0)
    cov = x.T @ x / max(len(x) - 1, 1)
    ev = np.clip(np.linalg.eigvalsh(cov)[::-1], 0.0, None)
    total = ev.sum()
    if total <= 0:
        return 1
    return int(np.searchsorted(np.cumsum(ev) / total, 0.90) + 1)


def fake_split(worlds, n_windows, seed):
    rng = np.random.default_rng(seed)
    frames, actions, eid, wid, tid = [], [], [], [], []
    for j, w in enumerate(worlds):
        length = n_windows + 1
        f = np.cumsum(rng.normal(0, 0.05, size=(length, H, W, 3)), axis=0)
        f = (f - f.min()) / max(f.max() - f.min(), 1e-6)
        frames.append(f)
        actions.append(rng.integers(0, 17, size=n_windows))
        eid.append(np.full(length, j, dtype=np.int64))
        wid.append(np.full(length, w, dtype=np.int64))
        tid.append(np.arange(length, dtype=np.int64))
    return dict(frames=np.concatenate(frames).astype(np.float16),
                actions=np.concatenate(actions).astype(np.int64),
                episode_id=np.concatenate(eid), world_id=np.concatenate(wid),
                t_index=np.concatenate(tid))


def score(model, train, held, device, out_dir):
    mean = train["frames"].astype(np.float32).mean(0, dtype=np.float64).astype(np.float32)
    win = {k: windows(held, k) for k in (1, 3, 5)}
    blend = {k: blend_a(train, k, mean) for k in (1, 3, 5)}
    result = {"params": None, "k": {}, "ceiling": {}, "shuffle": {},
              "action_groups": {}, "pca": {}, "marks": {}, "verdict": None}
    preds, errs, truth = {}, {}, {}
    for k in (1, 3, 5):
        xi, ai = win[k][0], win[k][1]
        x = held["frames"][xi].astype(np.float32)
        y = held["frames"][xi + k].astype(np.float32)
        pred = predict(model, held["frames"], xi, action_values(held["actions"], ai, k), k, device)
        err = sse(pred, y)
        copy_err = sse(x, y)
        blend_err = sse(mean + blend[k] * (x - mean), y)
        moved = moved_mask(held["frames"], xi)
        row = {
            "windows": int(len(xi)), "moved_windows": int(moved.sum()),
            "E": float(err.sum()), "copy_SSE": float(copy_err.sum()),
            "blend_SSE": float(blend_err.sum()), "blend_a": blend[k],
            "B": float(min(copy_err.sum(), blend_err.sum())),
            "E_moved": float(err[moved].sum()),
            "B_moved": float(min(copy_err[moved].sum(), blend_err[moved].sum())),
        }
        row["ratio"] = row["E"] / max(row["B"], 1e-12)
        row["ratio_moved"] = row["E_moved"] / max(row["B_moved"], 1e-12)
        result["k"][str(k)] = row
        preds[k], errs[k], truth[k] = pred, err, y
        print(f"k={k}: E={row['E']:.1f} B={row['B']:.1f} E/B={row['ratio']:.4f} "
              f"moved E/B={row['ratio_moved']:.4f} ({int(moved.sum())}/{len(xi)})")

    xi1 = win[1][0]
    ceil = ceiling_pred(model, held["frames"], xi1, device)
    ceil_err = sse(ceil, truth[1])
    b1 = result["k"]["1"]["B"]
    result["ceiling"] = {"E": float(ceil_err.sum()), "B": float(b1),
                         "ratio": float(ceil_err.sum() / max(b1, 1e-12))}
    print(f"ceiling: E/B={result['ceiling']['ratio']:.4f}")

    sh = shuffle_actions(held)
    for k, thresh in ((1, 1.25), (5, 1.10)):
        xi, ai, world, episode, t = win[k]
        moved = moved_mask(held["frames"], xi)
        sel = np.flatnonzero(moved)
        pred_sh = predict(model, held["frames"], xi[sel],
                          action_values(sh, ai[sel], k), k, device)
        err_sh = sse(pred_sh, truth[k][sel])
        true_err = errs[k][sel]
        ratios = {}
        for w in np.unique(world):
            mask = world[sel] == w
            ratios[str(int(w))] = float(err_sh[mask].sum() / max(true_err[mask].sum(), 1e-12))
        passed = sum(r >= thresh for r in ratios.values())
        pooled = float(err_sh.sum() / max(true_err.sum(), 1e-12))
        result["shuffle"][f"k{k}"] = {"threshold": thresh, "worlds_pass": passed,
                                      "worlds": ratios, "pooled_ratio": pooled}
        print(f"shuffle k={k}: {passed}/{len(ratios)} worlds >= {thresh}, pooled {pooled:.4f}")
        if k == 1:
            k1_pooled = pooled
            k1_worlds_pass = passed
    both = sum(1 for w in result["shuffle"]["k1"]["worlds"]
               if result["shuffle"]["k1"]["worlds"][w] >= 1.25
               and result["shuffle"]["k5"]["worlds"].get(w, 0.0) >= 1.10)
    result["shuffle"]["worlds_both"] = both
    print(f"shuffle worlds with both marks: {both}/{len(result['shuffle']['k1']['worlds'])}")

    a_first = held["actions"][win[1][1]]
    pred_change = (preds[1] - held["frames"][xi1].astype(np.float32)).reshape(len(xi1), -1)
    real_change = (truth[1] - held["frames"][xi1].astype(np.float32)).reshape(len(xi1), -1)
    std_ratios = {}
    for a in range(17):
        idx = np.flatnonzero(a_first == a)
        if len(idx) < 2:
            continue
        sp, sr = float(pred_change[idx].std()), float(real_change[idx].std())
        ratio = sp / sr if sr > 1e-12 else (float("inf") if sp > 1e-12 else 1.0)
        std_ratios[str(a)] = {"n": int(len(idx)), "std_pred": sp, "std_real": sr, "ratio": ratio}
    result["action_groups"] = std_ratios
    pc_pred, pc_real = pcs90(pred_change), pcs90(real_change)
    result["pca"] = {"pred_pcs_for_90": pc_pred, "real_pcs_for_90": pc_real}
    print(f"action std ratios: {[round(v['ratio'], 3) for v in std_ratios.values()]}")
    print(f"PCs for 90%: pred={pc_pred} real={pc_real}")

    ratios_ok = all(0.25 <= v["ratio"] <= 2.0 for v in std_ratios.values())
    r1 = result["k"]["1"]["ratio"]
    r3 = result["k"]["3"]["ratio"]
    r5 = result["k"]["5"]["ratio"]
    marks = {
        "pregate_ceiling_le_0.70": result["ceiling"]["ratio"] <= 0.70,
        "ceiling_gt_0.95": result["ceiling"]["ratio"] > 0.95,
        "a_E1_le_0.80": r1 <= 0.80,
        "a_E3_le_0.90": r3 <= 0.90,
        "a_E5_le_0.95": r5 <= 0.95,
        "b_shuffle_worlds": both >= 12,
        "c_std_ratios": ratios_ok,
        "c_pcs": pc_pred >= 0.5 * pc_real,
        "k1_shuffle_worlds": k1_worlds_pass >= 12,
        "k1_shuffle_pooled_ge_1.05": k1_pooled >= 1.05,
        "proves_wrong": r1 <= 0.80 and k1_pooled < 1.05,
    }
    a_ok = marks["a_E1_le_0.80"] and marks["a_E3_le_0.90"] and marks["a_E5_le_0.95"]
    c_ok = marks["c_std_ratios"] and marks["c_pcs"]
    if marks["ceiling_gt_0.95"]:
        verdict = "WRONG"
    elif a_ok and marks["b_shuffle_worlds"] and c_ok and marks["pregate_ceiling_le_0.70"]:
        verdict = "PASS"
    elif marks["a_E1_le_0.80"] and marks["k1_shuffle_worlds"] and c_ok \
            and (not marks["a_E3_le_0.90"] or not marks["a_E5_le_0.95"]):
        verdict = "PARTIAL"
    else:
        verdict = "WRONG"
    result["marks"] = marks
    result["verdict"] = verdict

    out = {"pred_k1": preds[1].astype(np.float16),
           "pred_k3": preds[3].astype(np.float16),
           "pred_k5": preds[5].astype(np.float16),
           "true_k1": truth[1].astype(np.float16),
           "true_k3": truth[3].astype(np.float16),
           "true_k5": truth[5].astype(np.float16)}
    for k in (1, 3, 5):
        out[f"world_k{k}"] = win[k][2]
        out[f"episode_k{k}"] = win[k][3]
        out[f"t_k{k}"] = win[k][4]
        out[f"action_k{k}"] = held["actions"][win[k][1]]
    np.savez(os.path.join(out_dir, "forecasts.npz"), **out)
    with open(os.path.join(out_dir, "score.json"), "w") as f:
        json.dump(result, f, indent=1)
    print(f"verdict: {verdict}")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default=".")
    ap.add_argument("--device", choices=("mps", "cpu"),
                    default="mps" if torch.backends.mps.is_available() else "cpu")
    ap.add_argument("--steps", type=int, default=1500)
    ap.add_argument("--max-minutes", type=float, default=15.0)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--pin-frame", action="store_true")
    ap.add_argument("--dec-norm", action="store_true")
    ap.add_argument("--size", default="debug")
    ap.add_argument("--row-target", choices=("continued", "fresh"), default="continued")
    args = ap.parse_args()
    globals()["ROW_TARGET"] = args.row_target
    globals()["PIN_FRAME"] = args.pin_frame
    globals()["DEC_NORM"] = args.dec_norm
    torch.manual_seed(42)
    device = torch.device(args.device)
    os.makedirs(args.out, exist_ok=True)
    if args.size == "debug":
        cfg = BoardSwarmConfig.debug_tiny()
    else:
        import sizes
        cfg = sizes.make_cfg(args.size)
    model = WorldModel(cfg).to(device)
    total, expert, active = active_param_count(model.cell)
    n_model = sum(p.numel() for p in model.parameters())
    print(f"params: cell total={total} expert={expert} active={active} (top_k/n_experts), model={n_model}")

    if args.smoke:
        train = fake_split([0, 1, 2, 3], 50, 1)
        held = fake_split([1000, 1001], 40, 2)
        args.steps = 20
    else:
        train = load_split(os.path.join(args.data, "train.npz"))
        held = load_split(os.path.join(args.data, "heldout.npz"))
    print(f"train windows k=1: {len(windows(train, 1)[0])}, heldout k=1: {len(windows(held, 1)[0])}")

    done = fit(model, train, args.steps, args.max_minutes, device)
    if DEC_NORM:  # recalibrate BN stats on the FINAL weights (train windows only, no grad), cumulative average
        bn = model.head[0]; bn.reset_running_stats(); bn.momentum = None; model.train()
        xi_c, ai_c, _, _, _ = windows(train, 1); rc = np.random.default_rng(7)
        with torch.no_grad():
            for _ in range(50):
                j = rc.integers(0, len(xi_c), size=64)
                forward_batch(model, torch.from_numpy(train["frames"][xi_c[j]].astype(np.float32)).to(device),
                              torch.from_numpy(train["frames"][xi_c[j] + 1].astype(np.float32)).to(device),
                              torch.from_numpy(train["actions"][ai_c[j]].astype(np.int64)).to(device))
    torch.save(model.state_dict(), os.path.join(args.out, "wm.pt"))
    model.eval()
    result = score(model, train, held, device, args.out)
    result["params"] = {"cell_total": total, "cell_expert": expert, "cell_active": active,
                        "model_total": n_model, "trained_steps": done, "device": args.device}
    with open(os.path.join(args.out, "score.json"), "w") as f:
        json.dump(result, f, indent=1)


if __name__ == "__main__":
    main()
