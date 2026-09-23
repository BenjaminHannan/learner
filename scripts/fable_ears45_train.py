#!/usr/bin/env python3
"""Rung 1 of design 43 -- train one ear.

    python fable_ears45_train.py --arm tape --seed 4301 --out runs/tape-4301 [--smoke]

The training pool is generated once from the TRAIN frames and the TRAIN name/value pools
with a fixed pool seed, so all arms and all seeds see the same sentences; `--seed` controls
initialisation, batch order, feature dropout and the per-sentence opaque-label shuffle.
Temperatures (B.3) are fitted on the CALIBRATION panel at the end -- never on a test panel.
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
import fable_ears45_data as D                       # noqa: E402
import fable_ears45_model as M                      # noqa: E402

POOL_SEED = 45100
POOL_SIZE = 60000
BUCKETS = (10, 14, 18, 64)


def encode_many(rows, lex, arm, rng):
    hash_names = (arm == "names")
    out = []
    for ex in rows:
        e = D.encode(ex, lex, rng, False, hash_names=hash_names)
        if e is not None:
            out.append(e)
    return out


def to_tensors(encs, device="cpu"):
    """group by length bucket -> list of dicts of padded tensors"""
    groups = {}
    for e in encs:
        b = next(i for i, hi in enumerate(BUCKETS) if e["n"] <= hi)
        groups.setdefault(b, []).append(e)
    packs = []
    for b in sorted(groups):
        g = groups[b]
        t = max(e["n"] for e in g)
        n = len(g)
        ids = torch.zeros(n, t, dtype=torch.long)
        feats = torch.zeros(n, t, M.N_FEATS)
        mask = torch.zeros(n, t)
        for i, e in enumerate(g):
            ids[i, :e["n"]] = torch.tensor(e["ids"])
            feats[i, :e["n"]] = torch.tensor(e["feats"], dtype=torch.float)
            mask[i, :e["n"]] = 1.0
        packs.append({
            "ids": ids, "feats": feats, "mask": mask,
            "pending": torch.zeros(n),
            "act": torch.tensor([e["act"] for e in g]),
            "n_items": torch.tensor([e["n_items"] for e in g]),
            "flags": torch.tensor([e["flags"] for e in g], dtype=torch.float),
            "slot_ptr": torch.tensor([e["slot_ptr"] for e in g]),
            "n_hops": torch.tensor([e["n_hops"] for e in g]),
            "hop_ptr": torch.tensor([e["hop_ptr"] for e in g]),
            "hop_key": torch.tensor([e["hop_key"] for e in g]),
            "hop_type": torch.tensor([e["hop_type"] for e in g]),
            "rows": g,
        })
    return packs


def batch_from(pack, idx, gen: torch.Generator, train=True):
    b = {k: v[idx] for k, v in pack.items() if k != "rows"}
    if train:
        f = b["feats"].clone()
        for col, p in ((0, 0.30), (7, 0.50), (8, 0.30)):
            keep = (torch.rand(f[:, :, col].shape, generator=gen) >= p).float()
            f[:, :, col] = f[:, :, col] * keep
        b["feats"] = f
        ids = b["ids"]
        perm = torch.argsort(torch.rand(ids.shape[0], D.N_OPQ, generator=gen), dim=1)
        opq = (ids >= D.OPQ0) & (ids < D.OPQ0 + D.N_OPQ)
        rel = (ids - D.OPQ0).clamp(0, D.N_OPQ - 1)
        mapped = D.OPQ0 + torch.gather(perm, 1, rel)
        b["ids"] = torch.where(opq, mapped, ids)
    return b


def _pad_logits(z, width=BUCKETS[-1]):
    """pointer logits from different length buckets -> one common width, -inf padding"""
    if z.shape[-1] == width:
        return z
    pad = z.new_full((z.shape[0], width - z.shape[-1]), torch.finfo(z.dtype).min)
    return torch.cat([z, pad], -1)


def fit_temperatures(model, packs, n_hops_run=4):
    """one scalar per head on CAL, by golden-section on log-temperature (B.3)."""
    heads = ["act", "items", "slot", "hop", "stop", "relkey"]
    logits = {h: [] for h in heads}
    tgts = {h: [] for h in heads}
    with torch.no_grad():
        for pack in packs:
            for s in range(0, pack["ids"].shape[0], 256):
                idx = torch.arange(s, min(s + 256, pack["ids"].shape[0]))
                b = batch_from(pack, idx, torch.Generator(), train=False)
                o = model(b["ids"], b["feats"], b["pending"], b["mask"],
                          n_hops_run=n_hops_run)
                nb, t = b["ids"].shape
                logits["act"].append(o["act"])
                tgts["act"].append(b["act"])
                logits["items"].append(o["items"])
                tgts["items"].append(b["n_items"])
                logits["slot"].append(_pad_logits(o["slot"].reshape(-1, t)))
                tgts["slot"].append(b["slot_ptr"].reshape(-1))
                live = (b["n_hops"] > 0)
                if live.any():
                    logits["hop"].append(_pad_logits(
                        torch.cat([o["hop_start"][live, 0], o["hop_end"][live, 0]], 0)))
                    tgts["hop"].append(
                        torch.cat([b["hop_ptr"][live, 0, 0], b["hop_ptr"][live, 0, 1]], 0))
                    logits["relkey"].append(o["relkey"][live, 0])
                    tgts["relkey"].append(b["hop_key"][live, 0])
                st = o["stop"].reshape(-1)
                sy = torch.stack([(b["n_hops"] == j).float() for j in range(n_hops_run)],
                                 1).reshape(-1)
                logits["stop"].append(st)
                tgts["stop"].append(sy)
    temps = torch.ones(6)
    for i, h in enumerate(heads):
        if not logits[h]:
            continue
        L = torch.cat(logits[h], 0)
        Y = torch.cat(tgts[h], 0)

        def nll(logt):
            z = L / math.exp(logt)
            if h == "stop":
                return F.binary_cross_entropy_with_logits(z, Y).item()
            return F.cross_entropy(z, Y).item()

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["tape", "bigru", "names"])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--updates", type=int, default=12000)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    torch.set_num_threads(1)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    updates = 200 if a.smoke else a.updates
    pool_size = 4000 if a.smoke else POOL_SIZE

    t_start = time.time()
    split, pools, lex, gen = D.load_all()
    prng = random.Random(POOL_SEED)
    rows = []
    while len(rows) < pool_size:
        fam = D._pick_family(prng, {f.family for f in split.frames("train")})
        hops = None
        if fam.startswith("ask."):
            r, acc = prng.random(), 0.0
            for h, w in D.ASK_HOPS:
                acc += w
                if r <= acc:
                    hops = h
                    break
            hops = hops or 1
        try:
            ex = gen.sample(prng, "train", "train", "train", False, [fam], False, hops)
        except (KeyError, IndexError):
            continue
        if len(D.tokenise(ex["utterance"])) > D.MAX_TOKENS:
            continue
        rows.append(ex)
    erng = random.Random(a.seed)
    packs = to_tensors(encode_many(rows, lex, a.arm, erng))
    cal = D.make_panel(gen, "cal", 800 if a.smoke else None)
    cal_packs = to_tensors(encode_many(cal, lex, a.arm, random.Random(a.seed + 1)))
    dev = D.make_panel(gen, "dev", 800)
    dev_packs = to_tensors(encode_many(dev, lex, a.arm, random.Random(a.seed + 2)))
    t_data = time.time() - t_start

    torch.manual_seed(a.seed)
    model = M.Ears(lex.size, a.arm)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=0.01)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=updates)
    g = torch.Generator().manual_seed(a.seed + 7)
    sizes = torch.tensor([float(p["ids"].shape[0]) for p in packs])
    probs = sizes / sizes.sum()
    log = []
    t0 = time.time()
    for step in range(updates):
        pi = int(torch.multinomial(probs, 1, generator=g))
        pack = packs[pi]
        idx = torch.randint(0, pack["ids"].shape[0], (a.batch,), generator=g)
        b = batch_from(pack, idx, g, train=True)
        o = model(b["ids"], b["feats"], b["pending"], b["mask"], n_hops_run=4)
        loss = M.loss_fn(o, b, n_hops_run=4)
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        sched.step()
        if step % 200 == 0 or step == updates - 1:
            log.append({"step": step, "loss": float(loss.detach())})
            print(f"[{a.arm} {a.seed}] step {step} loss {float(loss.detach()):.4f} "
                  f"{(time.time()-t0)/max(step,1):.3f}s/upd", flush=True)
    train_s = time.time() - t0

    # dev accuracy, monitoring only
    with torch.no_grad():
        cor = tot = 0
        for pack in dev_packs:
            n = pack["ids"].shape[0]
            bb = batch_from(pack, torch.arange(n), g, train=False)
            o = model(bb["ids"], bb["feats"], bb["pending"], bb["mask"], n_hops_run=4)
            cor += int((o["act"].argmax(-1) == bb["act"]).sum())
            tot += n
    temps = fit_temperatures(model, cal_packs)
    model.temps.copy_(temps)
    torch.save({"state": model.state_dict(), "arm": a.arm, "seed": a.seed,
                "vocab": lex.size, "temps": temps,
                "updates": updates, "batch": a.batch}, out / "ear.pt")
    meta = {"arm": a.arm, "seed": a.seed, "updates": updates, "batch": a.batch,
            "params": M.n_params(model), "pool": len(rows),
            "sec_per_update": train_s / updates, "train_sec": train_s,
            "data_sec": t_data, "dev_act_acc": cor / max(tot, 1),
            "temps": [float(x) for x in temps], "loss_log": log,
            "lexicon_sha": lex.sha(), "split_sha": split.sha()}
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps({k: v for k, v in meta.items() if k != "loss_log"}, indent=1))


if __name__ == "__main__":
    main()
