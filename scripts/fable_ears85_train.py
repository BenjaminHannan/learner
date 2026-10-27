#!/usr/bin/env python3
"""Exp 85 -- ModernBERT swap PREP for the ears rung-2 recipe (design doc 85).

    python fable_ears85_train.py --ensure                    # snapshot for the GPU box
    python fable_ears85_train.py --build-pool pool85.jsonl --snapshot <dir>
    python fable_ears85_train.py --seed 4701 --pool pool85.jsonl --snapshot <dir> \\
        --cal <cal.json> --out runs/m-4701
    python fable_ears85_train.py --dry-run --snapshot <dir>  # E2: params + GPU estimate
    python fable_ears85_train.py --len-audit --pool <pool.jsonl> --snapshot <dir>
    python fable_ears85_train.py --smoke --snapshot <dir> --cal <cal.json> \\
        --out <smoke dir>                                    # E1: CPU smoke bundle

What is reused UNCHANGED (imports only, nothing edited): 47's data pipeline
(`fable_ears47_data`: panels, golds, `encode_row`, pool generators), frame head +
loss (`fable_ears47_model.FrameEars/loss_fn`), the CAL golden-section temperature
fit and the checkpoint/meta format of `fable_ears47_train.py`, and the ModernBERT
loader of `fable_modernbert58_loader.load` (exp 61: bit-exact vs eager, 40/40 tokens).
The ONLY swap is the encoder (SciBERT -> ModernBERT-base) and its tokenizer
(WordPiece -> byte-BPE). Recipe fixed: MAX_LEN 96, batch 32, bf16 on CUDA / fp32 on
CPU, AdamW lr 3e-5 cosine, 2 epochs, seeds 4701-4703.

Why `--build-pool`: the exp-47 pool file stores SciBERT wordpiece ids, which are
meaningless to another vocabulary. The wave therefore regenerates the pool with the
SAME generator functions and RNG (`POOL_SEED`) but encodes with the ModernBERT
tokenizer (mirrors `fable_ears47_data.make_pool` line-for-line except the tokenizer).
Rows carry `"enc": "fable-modernbert85/1"` so the trainer uses stored ids; `text` is
kept for audit and decode display.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_data as D                     # noqa: E402  (read-only reuse)
import fable_ears47_model as M                    # noqa: E402  (read-only reuse)
import fable_modernbert58_loader as MB            # noqa: E402  (read-only reuse)

MAX_LEN = D.MAX_LEN                               # 96, same as the 47 wave
HEADS = ("act", "rel", "subj", "obj", "dir")
MODEL_ID = "answerdotai/ModernBERT-base"
ENC_MARK = "fable-modernbert85/1"
SMOKE_MAX = 32
SMOKE_N = 64
SMOKE_STEPS = 20
SMOKE_BATCH = 8


def ensure_snapshot() -> str:
    """Download (or reuse the cache of) the ModernBERT snapshot; return its directory.

    This is the exact step the GPU machine runs once (needs network there)."""
    from huggingface_hub import snapshot_download
    p = snapshot_download(MODEL_ID,
                          allow_patterns=["*.json", "model.safetensors"])
    print(f"model {MODEL_ID}  snapshot {p}")
    return p


def load_encoder(snapshot: str):
    """ModernBERT encoder via the verified exp-58 loader + the `.d` attribute the
    frame head reads (set additively here; the loader itself is untouched)."""
    t0 = time.time()
    enc, tok, info = MB.load(snapshot)
    enc.d = int(enc.emb.weight.shape[1])
    assert hasattr(enc, "layers") and len(enc.layers) > 0
    info["load_s"] = time.time() - t0
    return enc, tok, info


def build_model(snapshot: str, freeze_layers: int = 0):
    enc, tok, info = load_encoder(snapshot)
    model = M.FrameEars(enc, D.N_REL, freeze_layers=freeze_layers)
    return model, tok, info


# ---------------------------------------------------------------- pool handling
def encode_text_rows(rows: list[dict], tok) -> tuple[list[dict], int]:
    """text+gold47 rows -> ModernBERT-encoded rows (same `encode_row` as the wave)."""
    out, drop = [], 0
    for r in rows:
        e = D.encode_row(r, tok)
        if e is None:
            drop += 1
            continue
        e.pop("chspans", None)
        e["text"] = D.row_text(r)
        e["enc"] = ENC_MARK
        out.append(e)
    return out, drop


def load_pool(path: str, tok) -> list[dict]:
    """Encoded pool file -> trainer rows. Rows already carrying our ENC_MARK are used
    as-is; text+gold47 rows are encoded fresh; bare SciBERT-id rows are REFUSED
    (their ids belong to another vocabulary and would train silently wrong)."""
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    out, need_enc, refused = [], [], 0
    for r in rows:
        if r.get("enc") == ENC_MARK and "ids" in r:
            out.append(r)
        elif "gold47" in r:
            need_enc.append(r)
        else:
            refused += 1
    if need_enc:
        enc, drop = encode_text_rows(need_enc, tok)
        out.extend(enc)
        refused += drop
    if not out:
        raise SystemExit(
            f"pool {path}: 0 usable rows ({refused} refused). "
            "The exp-47 pool stores SciBERT ids; rebuild with --build-pool first.")
    print(f"pool {path}: kept={len(out)} refused-or-dropped={refused}")
    return out


def build_pool(out_path: str, tok) -> None:
    """Regenerate the training pool with ModernBERT tokenization (mirrors
    `fable_ears47_data.make_pool`: same generators, same POOL_SEED+7 stream)."""
    rng = random.Random(D.POOL_SEED + 7)
    kept = drop = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        for row in D.synth_pool_rows(tok, rng):
            e = D.encode_row(row, tok)
            if e is None:
                drop += 1
                continue
            e.pop("chspans", None)
            e["text"] = D.row_text(row)
            e["enc"] = ENC_MARK
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            kept += 1
        for row in D.webred_pool_rows():
            e = D.encode_row(row, tok)
            if e is None:
                drop += 1
                continue
            e.pop("chspans", None)
            e["text"] = D.row_text(row)
            e["enc"] = ENC_MARK
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            kept += 1
    print(f"pool kept={kept} dropped={drop} -> {out_path}")


# ------------------------------------------------------------- trainer (47 copy)
def to_pack(rows: list[dict], width: int = MAX_LEN) -> dict:
    n = len(rows)
    ids = torch.zeros(n, width, dtype=torch.long)
    mask = torch.zeros(n, width, dtype=torch.bool)
    for i, r in enumerate(rows):
        L = min(len(r["ids"]), width)
        ids[i, :L] = torch.tensor(r["ids"][:L])
        mask[i, :L] = True
    return {"ids": ids, "mask": mask,
            "act": torch.tensor([r["act"] for r in rows]),
            "rel": torch.tensor([r["rel"] for r in rows]),
            "subj": torch.tensor([r["subj"] for r in rows]),
            "obj": torch.tensor([r["obj"] for r in rows]),
            "dir": torch.tensor([r["dir"] for r in rows]),
            "flags": torch.tensor([r["flags"] for r in rows], dtype=torch.float)}


def batch(pack: dict, idx: torch.Tensor, device=None) -> dict:
    out = {k: v[idx] for k, v in pack.items()}
    if device is not None:
        out = {k: v.to(device) for k, v in out.items()}
    return out


def _pad(z: torch.Tensor, width: int) -> torch.Tensor:
    if z.shape[-1] == width:
        return z
    pad = z.new_full((z.shape[0], width - z.shape[-1]), torch.finfo(z.dtype).min)
    return torch.cat([z, pad], -1)


@torch.no_grad()
def fit_temperatures(model, pack, infer_batch: int = 64) -> torch.Tensor:
    """Verbatim CAL fit from fable_ears47_train.py (B.3/B.5): one scalar per scored
    head, golden-section on log-temperature. Unchanged because the head output dict
    it reads is unchanged. `infer_batch` only sizes the forward chunks (default 64,
    identical to 47); the smoke run passes a smaller value for Mac RAM headroom."""
    dev = next(model.parameters()).device
    logits = {h: [] for h in HEADS}
    tgts = {h: [] for h in HEADS}
    model.eval()
    n = pack["ids"].shape[0]
    for s in range(0, n, infer_batch):
        b = batch(pack, torch.arange(s, min(s + infer_batch, n)), dev)
        o = model(b["ids"], b["mask"])
        logits["act"].append(o["act"]); tgts["act"].append(b["act"])
        logits["rel"].append(o["rel"]); tgts["rel"].append(b["rel"])
        logits["dir"].append(o["direction"]); tgts["dir"].append(b["dir"])
        ptr = o["ptr"]
        logits["subj"].append(_pad(torch.cat([ptr[:, 0], ptr[:, 1]], 0), MAX_LEN))
        tgts["subj"].append(torch.cat([b["subj"][:, 0], b["subj"][:, 1]], 0))
        logits["obj"].append(_pad(torch.cat([ptr[:, 2], ptr[:, 3]], 0), MAX_LEN))
        tgts["obj"].append(torch.cat([b["obj"][:, 0], b["obj"][:, 1]], 0))
    temps = torch.ones(M.N_TEMPS)
    for i, h in enumerate(HEADS):
        L = torch.cat(logits[h], 0).float()
        Y = torch.cat(tgts[h], 0)

        def nll(logt, L=L, Y=Y):
            return F.cross_entropy(L / math.exp(logt), Y).item()

        lo, hi = -1.5, 1.5
        gr = (math.sqrt(5) - 1) / 2
        c, d_ = hi - gr * (hi - lo), lo + gr * (hi - lo)
        fc, fd = nll(c), nll(d_)
        for _ in range(30):
            if fc < fd:
                hi, d_, fd = d_, c, fc
                c = hi - gr * (hi - lo)
                fc = nll(c)
            else:
                lo, c, fc = c, d_, fd
                d_ = lo + gr * (hi - lo)
                fd = nll(d_)
        temps[i] = math.exp((lo + hi) / 2)
    return temps


def train_steps(model, pack, rows, seed, epochs, batch_size, lr, steps_cap, device,
                use_amp, log_every=200):
    opt = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),
                            lr=lr, weight_decay=0.01)
    total = epochs * math.ceil(len(rows) / batch_size)
    if steps_cap:
        total = min(total, steps_cap)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(total, 1))
    log = []
    step = 0
    t_start = time.time()
    tokens_at_200 = None
    done = False
    model.train()
    while not done:
        for s in range(0, len(rows), batch_size):
            if step >= total:
                done = True
                break
            idx = torch.arange(s, min(s + batch_size, len(rows)))
            b = batch(pack, idx, device)
            with torch.autocast(device_type=device.type, dtype=torch.bfloat16,
                                enabled=use_amp):
                o = model(b["ids"], b["mask"])
                loss = M.loss_fn(o, b)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                (p for p in model.parameters() if p.requires_grad), 1.0)
            opt.step()
            sched.step()
            step += 1
            if step == 200:
                elapsed = time.time() - t_start
                tokens_at_200 = int(b["mask"].sum()) * (200 / 1.0) / elapsed
                proj = elapsed / 200 * total
                print(f"[{seed}] step200 tokens/s={tokens_at_200:.0f} "
                      f"sec/step={elapsed / 200:.3f} projected_total={proj / 60:.1f}min",
                      flush=True)
            if step % log_every == 0 or step == total:
                print(f"[{seed}] step {step}/{total} loss {float(loss.detach()):.4f} "
                      f"{(time.time() - t_start) / step:.3f}s/step", flush=True)
                log.append({"step": step, "loss": float(loss.detach())})
    return step, total, log, tokens_at_200, (time.time() - t_start)


def save_checkpoint(model, out: Path, seed, temps, info, freeze_layers):
    torch.save({"state": model.state_dict(), "seed": seed,
                "temps": temps, "encoder_params": info["params"],
                "freeze_layers": freeze_layers}, out / "ear.pt")


# --------------------------------------------------------------- E2 estimation
def dry_run(snapshot: str) -> None:
    model, tok, info = build_model(snapshot)
    n_total = M.n_params(model)
    n_train = M.n_params_trainable(model)
    n_enc = info["params"]
    B, T = 32, MAX_LEN
    d = model.enc.d
    n_layers = len(model.enc.layers)
    n_global = sum(1 for g in model.enc.is_global) if hasattr(model.enc, "is_global") \
        else (n_layers + 2) // 3
    static_gb = n_total * 12 / 1e9          # bf16 w (2B) + bf16 grad (2B) + Adam m+v (8B)
    hid_gb = B * T * d * n_layers * 20 / 1e9  # ~10 resident tensors per layer, bf16
    attn_gb = B * T * T * n_global * 2 / 1e9  # global-layer scores, bf16
    est = static_gb + hid_gb + attn_gb
    print(f"encoder_params {n_enc:,}  head_params {n_total - n_enc:,}  "
          f"total {n_total:,}  trainable {n_train:,}")
    print(f"GPU estimate @ batch {B} / MAX_LEN {T} / bf16 (full fine-tune, AdamW):")
    print(f"  weights+grads+2 fp32 states : {static_gb:.2f} GB  (= 12 B/param)")
    print(f"  activations (hidden)        : {hid_gb:.2f} GB  (= B*T*d*layers*20 B)")
    print(f"  activations (global attn)   : {attn_gb:.2f} GB")
    print(f"  ESTIMATED total             : {est:.2f} GB  (16 GB card: "
          f"{'FITS' if est < 14 else 'TIGHT/OVER'}; measured on GPU at step 200)")


# ------------------------------------------------------------------ E3 audit
def len_audit(pool_path: str, tok) -> None:
    over, n, examples = 0, 0, []
    with open(pool_path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            r = json.loads(line)
            n += 1
            ids, _ = tok.encode(r.get("text", ""), 4096)
            if len(ids) > MAX_LEN:
                over += 1
                if len(examples) < 50:
                    examples.append({"line": i + 1, "len": len(ids),
                                     "text": r.get("text", "")[:160]})
    print(f"len_audit n={n} exceeding MAX_LEN {MAX_LEN}: {over} "
          f"({over / max(n, 1):.3%}) under ModernBERT tokenisation")
    for e in examples:
        print(f"  line {e['line']} len={e['len']} {e['text']!r}")
    if over > 50:
        print(f"  ... and {over - 50} more (all counted above)")


# ------------------------------------------------------------------ E1 smoke
def smoke(snapshot: str, cal_path: str, out: str, seed: int = 4701) -> None:
    import fable_ears47_score as S                 # noqa: E402  (read-only reuse)
    import resource

    def rss(tag):
        print(f"smoke rss {tag}: "
              f"{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6:.0f} MB",
              flush=True)

    outp = Path(out)
    outp.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, tok, info = build_model(snapshot)
    print(f"smoke encoder_params {info['params']:,}  device {device}")
    # 64 pool-like sentences that fit the tiny width, same generator as the pool.
    cand = []
    for r in D.synth_panel("cal"):
        e = D.encode_row(r, tok)
        if e is not None and len(e["ids"]) <= SMOKE_MAX:
            e.pop("chspans", None)
            e["text"] = D.row_text(r)
            cand.append(e)
        if len(cand) >= SMOKE_N:
            break
    assert len(cand) >= SMOKE_N, f"only {len(cand)} short sentences"
    order = list(range(len(cand)))
    random.Random(seed).shuffle(order)
    rows = [cand[i] for i in order]
    width = max(len(r["ids"]) for r in rows)
    pack = to_pack(rows, width)
    torch.manual_seed(seed)

    @torch.no_grad()
    def full_loss() -> float:
        model.eval()
        tot, cnt = 0.0, 0
        for s in range(0, len(rows), SMOKE_BATCH):
            b = batch(pack, torch.arange(s, min(s + SMOKE_BATCH, len(rows))), device)
            o = model(b["ids"], b["mask"])
            tot += float(M.loss_fn(o, b)) * (s + SMOKE_BATCH <= len(rows) and
                                             SMOKE_BATCH or len(rows) - s)
            cnt += s + SMOKE_BATCH <= len(rows) and SMOKE_BATCH or len(rows) - s
        model.train()
        return tot / max(cnt, 1)

    pre_loss = full_loss()
    # epochs overshoots on purpose: steps_cap stops the run at exactly SMOKE_STEPS.
    step, total, log, _, train_s = train_steps(
        model, pack, rows, seed, 10, SMOKE_BATCH, 3e-5, SMOKE_STEPS, device,
        device.type == "cuda", log_every=1)
    assert step == SMOKE_STEPS, f"smoke ran {step} steps, want {SMOKE_STEPS}"
    post_loss = full_loss()
    print(f"smoke full-set eval loss before={pre_loss:.4f} after={post_loss:.4f}",
          flush=True)
    rss("post-train")
    cal_rows = [D.encode_row(r, tok)
                for r in json.loads(Path(cal_path).read_text(encoding="utf-8"))]
    rss("post-cal-encode")
    l1, l20 = log[0]["loss"], log[-1]["loss"]
    print(f"smoke loss step1={l1:.4f} step20={l20:.4f} "
          f"decreases={l20 < l1} width={width}", flush=True)
    cal_pack = to_pack([e for e in cal_rows if e is not None])
    rss("pre-tempfit")
    temps = fit_temperatures(model, cal_pack, infer_batch=16)
    rss("post-tempfit")
    model.temps.copy_(temps)
    save_checkpoint(model, outp, seed, temps, info, 0)
    rss("post-save")
    meta = {"seed": seed, "epochs": 1, "batch": SMOKE_BATCH, "lr": 3e-5,
            "steps": step, "params": M.n_params(model),
            "params_trainable": M.n_params_trainable(model),
            "pool": len(rows), "device": str(device),
            "loss_step1": l1, "loss_step20": l20,
            "full_loss_before": pre_loss, "full_loss_after": post_loss,
            "temps": [float(x) for x in temps], "freeze_layers": 0,
            "smoke_max": SMOKE_MAX, "loss_log": log}
    (outp / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    # reload into a FRESH model: checkpoint must be self-sufficient.
    enc2, _, _ = load_encoder(snapshot)
    m2 = M.FrameEars(enc2, D.N_REL).to(device)
    ck = torch.load(outp / "ear.pt", map_location="cpu", weights_only=False)
    m2.load_state_dict(ck["state"])
    same_head = torch.equal(m2.act.weight.cpu(), model.act.weight.cpu())
    same_temps = torch.equal(m2.temps.cpu(), model.temps.cpu())
    print(f"reload ckpt keys={sorted(ck.keys())} head_identical={same_head} "
          f"temps_identical={same_temps}", flush=True)
    rss("post-reload")
    # unchanged scorer path on the sealed cal panel (chance-level accepted).
    m2.eval()
    raw = json.loads(Path(cal_path).read_text(encoding="utf-8"))
    encs = S.encode_panel(raw, tok)
    P = S.probs_for_model(m2, encs, device, batch=16)
    parses = [S.decode(raw[i], encs[i], P[i], {tok.unk}) for i in range(len(raw))]
    golds = [S.gold_frame_of(e) for e in encs]
    unscorable = sum(1 for e in encs if e is None)
    tau0 = S.tau0_from_cal(golds, [parses], ensemble=False)
    tau_exec = 1.0 - (1.0 - tau0) / 2.0
    rep = S.score_panel(raw, encs, [parses], tau_exec, golds, False, tau_exec)
    print(f"cal_score n={rep['n']} unscorable={unscorable} "
          f"correct={rep['correct']} executed={rep['executed']} "
          f"echoed={rep['echoed']} rephrased={rep['rephrased']} "
          f"silent_wrong_write={rep['silent_wrong_write']} "
          f"tau_exec={tau_exec:.4f}", flush=True)
    print(json.dumps({k: rep[k] for k in ("n", "correct", "executed", "echoed",
                                          "rephrased", "silent_wrong_write")}),
          flush=True)
    (outp / "cal_smoke_score.json").write_text(
        json.dumps({"n": rep["n"], "unscorable": unscorable,
                    "correct": rep["correct"], "executed": rep["executed"],
                    "echoed": rep["echoed"], "rephrased": rep["rephrased"],
                    "silent_wrong_write": rep["silent_wrong_write"],
                    "tau_exec": tau_exec, "verdicts": rep["verdicts"],
            "loss_step1": l1, "loss_step20": l20,
            "full_loss_before": pre_loss, "full_loss_after": post_loss,
                    "reload_head_identical": same_head,
                    "reload_temps_identical": same_temps}, indent=1),
        encoding="utf-8")


# ------------------------------------------------------------------ wave path
def wave(a) -> None:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
    t0 = time.time()
    model, tok, info = build_model(a.snapshot, a.freeze_layers)
    rows = load_pool(a.pool, tok)
    order = list(range(len(rows)))
    random.Random(a.seed).shuffle(order)
    rows = [rows[i] for i in order]
    pack = to_pack(rows)
    cal_rows = []
    for r in json.loads(Path(a.cal).read_text(encoding="utf-8")):
        e = D.encode_row(r, tok)
        if e is not None:
            cal_rows.append(e)
    cal_pack = to_pack(cal_rows)
    data_s = time.time() - t0
    torch.manual_seed(a.seed)
    model = model.to(device)
    step, total, log, tokens_at_200, train_s = train_steps(
        model, pack, rows, a.seed, a.epochs, a.batch, a.lr, a.steps_cap,
        device, device.type == "cuda")
    model.eval()
    with torch.no_grad():
        sub = {k: v[:2048].to(device) for k, v in pack.items()}
        o = model(sub["ids"], sub["mask"])
        cor = int((o["act"].argmax(-1) == sub["act"]).sum())
        tot = sub["ids"].shape[0]
    temps = fit_temperatures(model, cal_pack)
    model.temps.copy_(temps)
    save_checkpoint(model, out, a.seed, temps, info, a.freeze_layers)
    meta = {"seed": a.seed, "epochs": a.epochs, "batch": a.batch, "lr": a.lr,
            "steps": step, "params": M.n_params(model),
            "params_trainable": M.n_params_trainable(model),
            "pool": len(rows), "device": str(device),
            "sec_per_step": train_s / max(step, 1), "train_sec": train_s,
            "data_sec": data_s, "dev_act_acc": cor / max(tot, 1),
            "tokens_per_sec_200": tokens_at_200,
            "projected_min": (tokens_at_200 or 0) and
            (train_s / max(step, 1) * total / 60),
            "temps": [float(x) for x in temps],
            "freeze_layers": a.freeze_layers, "loss_log": log}
    (out / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in meta.items() if k != "loss_log"}, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=False, default=4701)
    ap.add_argument("--pool", default=None)
    ap.add_argument("--snapshot", default=None)
    ap.add_argument("--cal", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--freeze-layers", type=int, default=0)
    ap.add_argument("--steps-cap", type=int, default=0)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ensure", action="store_true")
    ap.add_argument("--build-pool", default=None)
    ap.add_argument("--len-audit", action="store_true")
    a = ap.parse_args()
    if a.ensure:
        ensure_snapshot()
        return
    if a.dry_run:
        assert a.snapshot, "--dry-run needs --snapshot"
        dry_run(a.snapshot)
        return
    if a.build_pool:
        assert a.snapshot, "--build-pool needs --snapshot"
        _, tok, _ = load_encoder(a.snapshot)
        build_pool(a.build_pool, tok)
        return
    if a.len_audit:
        assert a.pool and a.snapshot, "--len-audit needs --pool and --snapshot"
        _, tok, _ = load_encoder(a.snapshot)
        len_audit(a.pool, tok)
        return
    if a.smoke:
        assert a.snapshot and a.cal and a.out, "--smoke needs --snapshot --cal --out"
        smoke(a.snapshot, a.cal, a.out, a.seed)
        return
    assert a.pool and a.snapshot and a.cal and a.out, \
        "wave needs --seed --pool --snapshot --cal --out"
    wave(a)


if __name__ == "__main__":
    main()
