"""Count-handoff experiment: train one bridge type (D frozen), score it and its ablations, write JSON.

  python -m bridgelab.real.train --bridge pooled --d-ckpt D-final.pt --c-ckpt W2.pt --village-root ROOT --steps 3000 --device cuda --out bridgelab/real/results

Arms (bridge types):  text (creative trained on typed true c; scores oracle_text, d_text, prior_text)  |  none  |  ema_const  |  pooled  |  xattn.
The count head is trained with CE on the TRUE c (an auxiliary label; recorded in the JSON as "aux_label": "true count c").  D never receives gradient.
The sealed village `test` split and creative/data/c2/test.jsonl are never opened.  See PREREG.md for the pass marks (written before any run).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from creative import sleep
from custom_io.data import Dataset, collate, to_device
from custom_io.evalx import is_hit

from . import data as D
from . import dmsg
from .bridge import D2C, KINDS, Wire, ablate, base_in, to_slot_ledger

HERE = Path(__file__).resolve().parent
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ----------------------------------------------------------------------------- helpers
def make_batch(rows, vocab, device):
    return to_device(collate([Dataset(rows, vocab, strict=False)[i] for i in range(len(rows))]), device)


def file_tag(path: str) -> str:
    if path in ("random", "synthetic"):
        return path
    st = os.stat(path)
    return hashlib.sha256(f"{os.path.abspath(path)}|{st.st_size}|{int(st.st_mtime)}".encode()).hexdigest()[:10]


def load_creative(path: str, device, d_ckpt: str = None):
    model, vocab, meta = sleep.load_parent(path, device)
    to_slot_ledger(model)
    if d_ckpt and d_ckpt not in ("random", "synthetic") and "W2" in os.path.basename(path):    # only the v1 joint creative was trained with it
        payload = torch.load(d_ckpt, map_location="cpu", weights_only=False)
        if "bridge" in payload:                       # v1 W2 needs the v1 bridge's frozen vector (see bridge.base_in)
            from v1.joint import Bridge
            st = payload["bridge"]
            br = Bridge(st["p_dc.weight"].shape[1], st["p_dc.weight"].shape[0])
            br.load_state_dict(st)
            with torch.no_grad():
                model._v1_base = br.to_creative().detach().to(device)
            model.bridge_in = base_in(model)
    return model, vocab, meta


def get_messages(dmodel, items, tokenizer, device, tag: str, split: str, args) -> dict:
    cache_dir = HERE / "ckpt"
    cache_dir.mkdir(exist_ok=True)
    src = getattr(args, "msg_source", "registers")
    ids = hashlib.sha256("|".join(map(str, getattr(items, "qid", items))).encode()).hexdigest()[:16]      # the exact items (the subsample depends on --seed)
    key = hashlib.sha256(f"{tag}|{args.village_root}|{split}|{len(items)}|{ids}{'' if src == 'registers' else '|' + src}".encode()).hexdigest()[:12]
    path = cache_dir / f"dmsg-{key}-{split}.pt"
    if path.exists() and not args.fresh_messages:
        return torch.load(path, weights_only=False)
    log(f"D reading {len(items)} {split} items")
    out = dmsg.extract(dmodel, items, tokenizer, device, max_tokens=args.d_max_tokens, log=None, msg_source=src)
    torch.save(out, path)
    return out


def subsample_items(items: D.VillageItems, n: int, seed: int) -> D.VillageItems:
    if n is None or n <= 0 or n >= len(items):
        return items
    idx = sorted(random.Random(seed).sample(range(len(items)), n))
    return items.take(idx)


def fit_probe(xtr, ytr, xte, yte, ncls=D.CMAX + 1, iters=150, wd=1e-3):
    """Multinomial logistic regression (LBFGS) on standardised features; -> test accuracy.  The 'linear probe on the bridge summary'."""
    xtr, xte = xtr.float().cpu(), xte.float().cpu()
    if float(xtr.abs().sum()) == 0 or xtr.std(0).max() < 1e-8:
        pred = torch.full((len(yte),), int(torch.bincount(ytr).argmax()))
        return float((pred == yte.cpu()).float().mean())
    mu, sd = xtr.mean(0), xtr.std(0).clamp(min=1e-6)
    xtr, xte = (xtr - mu) / sd, (xte - mu) / sd
    W = torch.zeros(xtr.shape[1], ncls, requires_grad=True)
    b = torch.zeros(ncls, requires_grad=True)
    opt = torch.optim.LBFGS([W, b], lr=1.0, max_iter=iters, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = F.cross_entropy(xtr @ W + b, ytr.cpu()) + wd * (W ** 2).sum()
        loss.backward()
        return loss

    opt.step(closure)
    with torch.no_grad():
        return float(((xte @ W + b).argmax(1) == yte.cpu()).float().mean())


# ----------------------------------------------------------------------------- scoring
@torch.no_grad()
def score(ledger, vocab, prompts, device, bs, mode, bridge=None, wire=None, regs=None, slot=None, typed_vals=None):
    """First-try exact answers of the creative model.
    mode 'hidden': prompts' rows with the placeholder; slot [N] long (injected values) and, if bridge, its output on regs [N,R,128] adds vectors.
    mode 'typed' : the placeholder replaced by typed_vals [N] (digits in the text).   -> dict(pred list[str], hit [N] bool)"""
    ledger.eval()
    if bridge is not None:
        bridge.eval()
    preds = []
    N = len(prompts)
    for s in range(0, N, bs):
        ps = prompts[s:s + bs]
        if mode == "typed":
            rows = [dict(p["row"], prompt=p["row"]["prompt"].replace(D.PLACEHOLDER, str(int(v)))) for p, v in zip(ps, typed_vals[s:s + bs].tolist())]
            ledger.slot_value = None
            b = make_batch(rows, vocab, device)
            preds += ledger.generate(b)
        else:
            rows = [p["row"] for p in ps]
            b = make_batch(rows, vocab, device)
            val = slot[s:s + bs].to(device)
            if bridge is not None and regs is not None:
                out = bridge(regs[s:s + bs].to(device))
                wire.set(out, val)
            else:                                   # no bridge vectors at all: only the injected value
                if wire is not None:
                    wire.out = None
                ledger.slot_value, ledger.vcode.vec = val, None
            preds += ledger.generate(b)
    ledger.slot_value = None
    ledger.vcode.vec = None
    hit = torch.tensor([is_hit(p, q["row"]) for p, q in zip(preds, prompts)])
    return dict(pred=preds, hit=hit)


@torch.no_grad()
def count_predictions(bridge, regs, device, bs=256):
    bridge.eval()
    out = []
    for s in range(0, len(regs), bs):
        out.append(bridge(regs[s:s + bs].to(device))["logits"].argmax(-1).cpu())
    return torch.cat(out)


def summarize(hit, c_true, c_pred, prompts):
    n = len(hit)
    kinds = {}
    for h, p in zip(hit.tolist(), prompts):
        kinds.setdefault(p["kind"], []).append(h)
    out = dict(n=n, acc=float(hit.float().mean()), per_kind={k: float(np.mean(v)) for k, v in kinds.items()})
    if c_pred is not None:
        right = c_pred == c_true
        out["count_acc"] = float(right.float().mean())
        out["acc_given_count_right"] = float(hit[right].float().mean()) if right.any() else None
        out["acc_given_count_wrong"] = float(hit[~right].float().mean()) if (~right).any() else None
    return out


# ----------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bridge", required=True, choices=("text",) + KINDS)
    ap.add_argument("--d-ckpt", required=True, help="D-final.pt | random (smoke) | synthetic (smoke: fabricated messages that carry c)")
    ap.add_argument("--train-d-steps", type=int, default=0, help="smoke only: pretrain a random D this many steps on count questions")
    ap.add_argument("--c-ckpt", required=True, help="creative parent checkpoint (train.py/sleep.save_parent format: B2_s200.pt, W2.pt, ...)")
    ap.add_argument("--village-root", required=True, help="v1 layout: ROOT/train, ROOT/dev, ROOT/validation (see data.make_smoke_root for a tiny one)")
    ap.add_argument("--tokenizer", default=str(HERE.parent.parent / "data/tokenizer/premonition-tok-v2.json"))
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--lr-bridge", type=float, default=1e-3)
    ap.add_argument("--lr-creative", type=float, default=3e-4)
    ap.add_argument("--w-ce", type=float, default=1.0)
    ap.add_argument("--freeze-creative", action="store_true")
    ap.add_argument("--inject-train", default="true", choices=("true", "pred"), help="value written into the slot while training the creative loss")
    ap.add_argument("--kinds", default=",".join(D.TAUGHT))
    ap.add_argument("--train-items", type=int, default=0, help="cap on train items (0 = all)")
    ap.add_argument("--eval-items", type=int, default=0, help="cap on dev / validation items (0 = all)")
    ap.add_argument("--eval-batch", type=int, default=128)
    ap.add_argument("--d-max-tokens", type=int, default=60000)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", default=str(HERE / "results"))
    ap.add_argument("--tag", default="")
    ap.add_argument("--save-creative", default="", help="write the trained creative (parent-checkpoint format) here")
    ap.add_argument("--ema-state-from", default="", help="ema_const only: load the v1 bridge state (key 'bridge') of this D-final.pt into the control, as saved")
    ap.add_argument("--msg-source", default="registers", choices=("registers", "decoder"),
                    help="what D hands over: its final-loop register rows (default) | its decoder hidden state at the first answer position ([N,1,128])")
    ap.add_argument("--fresh-messages", action="store_true")
    ap.add_argument("--bf16", action="store_true")
    a = ap.parse_args(argv)

    device = torch.device(a.device)
    torch.manual_seed(a.seed); np.random.seed(a.seed); random.seed(a.seed)
    kinds = tuple(a.kinds.split(","))
    D.warm_references(kinds)
    out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    # ---- village items and D's messages (D frozen; messages are computed once per item, identity entity numbering)
    tokenizer, splits = D.open_village(a.village_root, a.tokenizer, workers=a.workers)
    train_items = subsample_items(splits["train"], a.train_items, a.seed)
    evals = {s: subsample_items(splits[s], a.eval_items, a.seed + 1) for s in ("dev", "validation")}
    synthetic = a.d_ckpt == "synthetic"
    dmodel = None if synthetic else dmsg.load_d(a.d_ckpt, device, tokenizer.vocab_size, seed=a.seed)
    dpath = a.d_ckpt
    if a.d_ckpt == "random" and a.train_d_steps > 0:
        hist = dmsg.train_count_d(dmodel, splits["train"], a.train_d_steps, device, seed=a.seed, log=log)
        dmsg.freeze(dmodel)
        dpath = str(HERE / "ckpt" / f"D_smoke_{a.train_d_steps}.pt")
        (HERE / "ckpt").mkdir(exist_ok=True)
        torch.save({"model": dmodel.state_dict(), "config": dmsg.mini_config_dict(dmodel.config), "steps": a.train_d_steps, "smoke": True}, dpath)
        log("trained smoke D saved to", dpath)
    dtag = file_tag(dpath)
    if synthetic:
        log("SYNTHETIC messages (smoke): registers = A[c] + noise, not read from D")
        msgs = {"train": dmsg.synthetic_messages(train_items, seed=a.seed)}
        for s in evals:
            msgs[s] = dmsg.synthetic_messages(evals[s], seed=a.seed)
    else:
        msgs = {"train": get_messages(dmodel, train_items, tokenizer, device, dtag, "train", a)}
        for s in evals:
            msgs[s] = get_messages(dmodel, evals[s], tokenizer, device, dtag, s, a)
    del dmodel

    # ---- c distribution and the prior baseline (mode of the TRAIN counts)
    prior = {s: D.c_stats(it.c, train_items.c) for s, it in [("train", train_items), ("dev", evals["dev"]), ("validation", evals["validation"])]}
    c_mode = prior["train"]["mode"]
    for s in prior:
        log(f"c[{s}] n={prior[s]['n']} range {prior[s]['min']}..{prior[s]['max']} entropy {prior[s]['entropy_bits']:.2f} bits  prior-baseline {prior[s]['prior_acc']:.3f}")
    d_own = {s: dict(acc=float(msgs[s]["d_correct"].float().mean()), parsed=float((msgs[s]["d_int"] >= 0).float().mean()))
             for s in ("train", "dev", "validation")}
    log("D's own count accuracy:", {s: round(v["acc"], 3) for s, v in d_own.items()})

    # ---- creative + bridge
    ledger, vocab, meta = load_creative(a.c_ckpt, device, a.d_ckpt)
    for p in ledger.parameters():
        p.requires_grad_(not a.freeze_creative)
    bridge = wire = None
    if a.bridge in KINDS:
        bridge = D2C(a.bridge, d_d=msgs["train"]["regs"].shape[2], d_c=ledger.d, n_regs=msgs["train"]["regs"].shape[1], n_core=len(ledger.core)).to(device)
        if a.ema_state_from and a.bridge == "ema_const":
            saved = torch.load(a.ema_state_from, map_location="cpu", weights_only=False)
            bridge.joint.load_state_dict(saved["bridge"])
            bridge.joint.to(device)
            log("ema_const: loaded the saved v1 bridge state from", a.ema_state_from)
        wire = Wire(ledger, bridge).attach()
    groups = []
    if bridge is not None and bridge.trainable():
        groups.append(dict(params=bridge.trainable(), lr=a.lr_bridge, weight_decay=0.01))
    if not a.freeze_creative:
        groups.append(dict(params=[p for p in ledger.parameters() if p.requires_grad], lr=a.lr_creative, weight_decay=0.0))
    opt = torch.optim.AdamW(groups) if groups else None
    n_bridge = sum(p.numel() for p in bridge.trainable()) if bridge is not None else 0
    log(f"bridge={a.bridge} trainable bridge params {n_bridge:,}; creative {'frozen' if a.freeze_creative else 'trained'}; kinds {kinds}")

    # ---- train
    N = len(train_items)
    rng = random.Random(a.seed)
    order, pos = [], 0
    hist = []
    amp = (lambda: torch.autocast(device.type, dtype=torch.bfloat16)) if a.bf16 else (lambda: torch.autocast(device.type, enabled=False))
    t0 = time.time()
    for step in range(1, a.steps + 1):
        if opt is None:
            break
        if pos + a.batch > len(order):
            order, pos = rng.sample(range(N), N), 0
        idx = order[pos:pos + a.batch]; pos += a.batch
        idx_t = torch.tensor(idx)
        c = train_items.c[idx_t]
        items = [D.make_prompt(int(ci), rng, kinds, uid=f"tr{step}:{k}") for k, ci in enumerate(c.tolist())]
        for it in items:
            D.register(it)
        ledger.train()
        loss_ce = torch.zeros(())
        with amp():
            if a.bridge == "text":
                batch = make_batch([it["typed"] for it in items], vocab, device)
                ledger.slot_value = None
                loss_c, aux = ledger.loss(batch)
                loss = loss_c
            else:
                bridge.train()
                regs = msgs["train"]["regs"][idx_t].to(device)
                bridge.observe(regs[:, 0])
                o = bridge(regs)
                loss_ce = F.cross_entropy(o["logits"].float(), c.to(device))
                val = c.to(device) if a.inject_train == "true" else o["logits"].argmax(-1).detach()
                wire.set(o, val)
                batch = make_batch([it["row"] for it in items], vocab, device)
                loss_c, aux = ledger.loss(batch)
                loss = loss_c + a.w_ce * loss_ce
        opt.zero_grad(set_to_none=True)
        loss.backward()
        for g in groups:                    # clipped per group: the creative loss is ~100x the count CE and must not shrink the bridge's gradient
            torch.nn.utils.clip_grad_norm_(g["params"], 1.0)
        opt.step()
        for it in items:
            D.release(it)
        hist.append(dict(step=step, loss=float(loss), creative=float(loss_c), ce=float(loss_ce)))
        if step % max(1, a.steps // 20) == 0 or step == 1:
            r = hist[-max(1, a.steps // 20):]
            log(f"step {step}/{a.steps} loss {np.mean([h['loss'] for h in r]):.3f} creative {np.mean([h['creative'] for h in r]):.3f} ce {np.mean([h['ce'] for h in r]):.3f} ({(time.time() - t0) / step:.2f}s/step)")
    ledger.slot_value = None
    if wire is not None:
        wire.out = None

    # ---- evaluate
    results = {}
    for split in ("dev", "validation"):
        it, m = evals[split], msgs[split]
        prompts = D.eval_prompts(it, kinds, a.seed)
        for p in prompts:
            D.register(p)
        c_true = it.c
        regs = m["regs"]
        arms = {}
        slot_prior = torch.full((len(it),), c_mode, dtype=torch.long)

        def run_hidden(name, regs_in, slot, with_bridge=True):
            r = score(ledger, vocab, prompts, device, a.eval_batch, "hidden", bridge if with_bridge else None, wire, regs_in, slot)
            cp = count_predictions(bridge, regs_in, device) if (with_bridge and bridge is not None) else None
            arms[name] = summarize(r["hit"], c_true, cp, prompts)
            return r, cp

        if a.bridge == "text":
            for name, vals in (("oracle_text", c_true), ("d_text", torch.where(m["d_int"] >= 0, m["d_int"], torch.full_like(m["d_int"], c_mode))),
                               ("prior_text", slot_prior)):
                r = score(ledger, vocab, prompts, device, a.eval_batch, "typed", typed_vals=vals)
                arms[name] = summarize(r["hit"], c_true, vals, prompts)
        else:
            modes = ["real", "off", "shuffle", "mean"] if bridge.per_item else ["real"]
            for mode in modes:
                regs_m = ablate(regs, mode, seed=a.seed, c=c_true)
                cp = count_predictions(bridge, regs_m, device)
                run_hidden(mode, regs_m, cp)
            _, cp_real = None, count_predictions(bridge, regs, device)
            # ceiling of this creative: the TRUE count injected (the bridge vectors of the real message still added)
            run_hidden("oracle_inject", regs, c_true)
            # the creative with the prior mode injected and no bridge vector at all
            r = score(ledger, vocab, prompts, device, a.eval_batch, "hidden", None, wire, None, slot_prior)
            arms["prior_inject"] = summarize(r["hit"], c_true, slot_prior, prompts)
            # typed text on this run's creative, for reference (the canonical text arms come from --bridge text)
            vals_d = torch.where(m["d_int"] >= 0, m["d_int"], torch.full_like(m["d_int"], c_mode))
            for name, vals in (("oracle_text", c_true), ("d_text", vals_d)):
                r = score(ledger, vocab, prompts, device, a.eval_batch, "typed", typed_vals=vals)
                arms[name] = summarize(r["hit"], c_true, vals, prompts)
            if bridge.per_item:
                arms["shuffle"]["same_c_as_original"] = float((c_true[ablate_perm(len(it), a.seed, c_true)] == c_true).float().mean())
        for p in prompts:
            D.release(p)
        results[split] = dict(n=len(it), c=prior[split], d_own=d_own[split], arms=arms)

    # ---- linear probes (train -> dev): what the creative is handed vs what D holds
    probes = {}
    if bridge is not None:
        feats = {}
        for s, mm in (("train", msgs["train"]), ("dev", msgs["dev"])):
            with torch.no_grad():
                bridge.eval()
                o = bridge(mm["regs"].to(device))
            feats[s] = dict(v=None if o["v"] is None else o["v"].cpu(), h=None if o["h"] is None else o["h"].cpu(), reg0=mm["reg0"], regs_flat=mm["regs"].flatten(1))
        for name in ("v", "h", "reg0", "regs_flat"):
            if feats["train"][name] is None:
                continue
            probes[name] = fit_probe(feats["train"][name], train_items.c, feats["dev"][name], evals["dev"].c)
        probes["chance_prior"] = prior["dev"]["prior_acc"]

    summary = dict(bridge=a.bridge, seed=a.seed, steps=a.steps, args=vars(a), aux_label="true count c (count head CE; the only label that crosses besides the answer)",
                   d_ckpt=dpath, c_ckpt=a.c_ckpt, c_ckpt_meta=meta, kinds=kinds, creative_frozen=a.freeze_creative, bridge_params=n_bridge,
                   prior=prior, c_mode=c_mode, results=results, probes=probes, history=hist[:: max(1, len(hist) // 200)],
                   seconds=time.time() - t_start, smoke=bool(a.d_ckpt in ("random", "synthetic") or a.train_d_steps or "smoke" in os.path.basename(dpath)), synthetic=synthetic)
    name = f"{a.bridge}{('-' + a.tag) if a.tag else ''}-s{a.seed}.json"
    json.dump(summary, open(out_dir / name, "w"), indent=1, default=float)
    if a.save_creative:
        sleep.save_parent(ledger, meta["name"], meta["cfg"], vocab, a.save_creative, step=meta["step"] or 0)
        log("creative saved to", a.save_creative)
    for split in results:
        log(split, {k: round(v["acc"], 3) for k, v in results[split]["arms"].items()})
    log("wrote", out_dir / name)
    return summary


def ablate_perm(n, seed, c):
    from .bridge import shuffle_perm
    return shuffle_perm(n, seed, c)


if __name__ == "__main__":
    sys.path.insert(0, str(HERE.parent.parent))
    main()
