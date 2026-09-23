#!/usr/bin/env python3
"""rsn-294 runner: copy phase, practice (RL) phase, dev check, panel eval.

  train : python claude_rsn294_run.py train --arm loop|plain --seed 1 --out DIR
          [--size 30m|tiny] [--copy-steps 6000] [--rl-steps 6000] [--device cuda]
          Writes DIR/copy_only.pt, DIR/final.pt, DIR/train_log.jsonl, DIR/train_summary.json
  dev   : python claude_rsn294_run.py dev --ckpt DIR/final.pt --out DIR/dev.json
          Fresh generated episodes (seed 777), per category, incl. the generator's own
          three-step and 30-40-row cases. Development only.
  eval  : python claude_rsn294_run.py eval --ckpt DIR/final.pt --panel PANEL/items.jsonl
          --out DIR/panel_scores.json
          Registered scoring. Writes CATEGORY-LEVEL counts only (never item text).

COPY phase (what 292's code reasoner can already do: one- and two-step lookups, backwards
"who", yes/no, newest correction, missing -> "I don't know"): the network copies the right
action (cross-entropy) and the facts it used (support bits).
PRACTICE phase (RL, a one-decision bandit with a group baseline, GRPO-style): every kind of
question, including counting, comparing and before/after, which it is NEVER shown the answer
to. It only gets a score for its own choice: +1 right, -1 wrong, +0.3 honest "I don't know",
-0.5 "I don't know" when the fact was there, -2 an answer when there is no fact; +0.2 when
the cited facts are exactly right on a right answer. A copy batch keeps running beside it so
old skills are not forgotten.
Loop arm: trained with a random 2-12 passes; registered eval uses 12 passes.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn294_core as C  # noqa: E402

COPY_KINDS = ["value1", "value2", "who", "yesno", "correction", "missing"]
ALL_KINDS = COPY_KINDS + ["count", "compare", "before", "after"]
EVAL_STEPS = 12


class Stream(torch.utils.data.IterableDataset):
    def __init__(self, kinds, batch, seed):
        self.kinds, self.batch, self.seed = kinds, batch, seed

    def __iter__(self):
        wi = torch.utils.data.get_worker_info()
        rng = random.Random(self.seed * 1000 + (wi.id if wi else 0))
        while True:
            eps = [C.gen_episode(rng, rng.choice(self.kinds)) for _ in range(self.batch)]
            enc, infos = C.encode(eps, rng)
            ga = [C.gold_action(e, i) for e, i in zip(eps, infos)]
            sup = torch.zeros(len(eps), C.MAX_ROWS)
            for b, (e, inf) in enumerate(zip(eps, infos)):
                s = set(e["gold"]["support"])
                for j, r in enumerate(inf["rows"]):
                    if r["fid"] in s:
                        sup[b, j] = 1.0
            yield enc, torch.tensor([g if g is not None else -100 for g in ga]), sup, \
                [e["gold"]["answer"] for e in eps], infos


def loader(kinds, batch, seed, workers):
    return iter(torch.utils.data.DataLoader(Stream(kinds, batch, seed), batch_size=None,
                                            num_workers=workers, collate_fn=lambda x: x,
                                            prefetch_factor=4 if workers else None,
                                            persistent_workers=bool(workers)))


def steps_for(arm, rng):
    return rng.randint(2, EVAL_STEPS) if arm == "loop" else None


def copy_loss(model, arm, batch, dev, rng):
    enc, ga, sup, _, _ = batch
    enc, ga, sup = enc.to(dev), ga.to(dev), sup.to(dev)
    logits, sl = model(enc, steps_for(arm, rng)) if arm == "loop" else model(enc)
    la = F.cross_entropy(logits, ga, ignore_index=-100)
    m = sl > -1e8
    ls = F.binary_cross_entropy_with_logits(sl[m], sup[m])
    return la + 0.5 * ls, la.item()


def rl_loss(model, arm, batch, dev, rng, G=8):
    enc, _, sup, golds, infos = batch
    enc, sup = enc.to(dev), sup.to(dev)
    logits, sl = model(enc, steps_for(arm, rng)) if arm == "loop" else model(enc)
    dist = torch.distributions.Categorical(logits=logits)
    acts = dist.sample((G,))                                   # [G, B]
    m = sl > -1e8
    sprob = torch.sigmoid(sl).clamp(1e-4, 1 - 1e-4)
    sbits = torch.bernoulli(sprob.detach().expand(G, *sprob.shape)) * m    # [G, B, R]
    R = torch.zeros(G, len(golds), device=dev)
    for g in range(G):
        for b in range(len(golds)):
            a = int(acts[g, b])
            ans = C.decode(a, infos[b])
            r = C.reward(ans, golds[b])
            if r == 1.0 and torch.equal(sbits[g, b][m[b]], sup[b][m[b]]):
                r += 0.2
            R[g, b] = r
    adv = (R - R.mean(0, keepdim=True)) / (R.std(0, keepdim=True) + 1e-4)
    lp = dist.log_prob(acts)                                   # [G, B]
    slp = (sbits * torch.log(sprob) + (1 - sbits) * torch.log(1 - sprob)) * m
    slp = slp.sum(-1)                                          # [G, B]
    loss = -(adv.detach() * (lp + slp)).mean() - 0.01 * dist.entropy().mean()
    return loss, R.mean().item()


def train(a):
    torch.manual_seed(a.seed)
    rng = random.Random(a.seed)
    dev = torch.device(a.device)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    model = C.build(a.arm, a.size).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.01)
    total = a.copy_steps + a.rl_steps
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / 300) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(s, total) / total))))
    log = open(out / "train_log.jsonl", "w")
    copy_it = loader(COPY_KINDS, a.batch, a.seed, a.workers)
    t0 = time.time()
    amp = dict(device_type="cuda", dtype=torch.bfloat16) if dev.type == "cuda" else None
    ctx = (lambda: torch.autocast(**amp)) if amp else (lambda: torch.autocast("cpu", enabled=False))
    for s in range(a.copy_steps):
        with ctx():
            loss, la = copy_loss(model, a.arm, next(copy_it), dev, rng)
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step()
        if s % 100 == 0 or s == a.copy_steps - 1:
            log.write(json.dumps({"phase": "copy", "step": s, "loss": round(loss.item(), 4),
                                  "action_ce": round(la, 4), "min": round((time.time() - t0) / 60, 2)}) + "\n"); log.flush()
    torch.save({"arm": a.arm, "size": a.size, "state": model.state_dict()}, out / "copy_only.pt")
    rl_it = loader(ALL_KINDS, a.rl_batch, a.seed + 50, a.workers)
    for s in range(a.rl_steps):
        with ctx():
            lr_, rmean = rl_loss(model, a.arm, next(rl_it), dev, rng)
            lc, _ = copy_loss(model, a.arm, next(copy_it), dev, rng)
            loss = lr_ + 0.5 * lc
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step()
        if s % 100 == 0 or s == a.rl_steps - 1:
            log.write(json.dumps({"phase": "rl", "step": s, "reward": round(rmean, 4),
                                  "loss": round(loss.item(), 4), "min": round((time.time() - t0) / 60, 2)}) + "\n"); log.flush()
    torch.save({"arm": a.arm, "size": a.size, "state": model.state_dict()}, out / "final.pt")
    json.dump({"arm": a.arm, "size": a.size, "seed": a.seed, "params": C.n_params(model),
               "copy_steps": a.copy_steps, "rl_steps": a.rl_steps, "batch": a.batch,
               "rl_batch": a.rl_batch, "minutes": round((time.time() - t0) / 60, 1),
               "device": str(dev), "torch": torch.__version__},
              open(out / "train_summary.json", "w"), indent=1)


def load(path, device):
    ck = torch.load(path, map_location=device, weights_only=True)
    m = C.build(ck["arm"], ck["size"]).to(device)
    m.load_state_dict(ck["state"])
    m.eval()
    return m, ck["arm"]


@torch.no_grad()
def answer(model, arm, items, device, steps=EVAL_STEPS, bs=64):
    """-> list of (raw answer, checked answer). checked = fact-check on the way out."""
    rng = random.Random(4242)
    res = []
    for i in range(0, len(items), bs):
        chunk = items[i:i + bs]
        enc, infos = C.encode(chunk, rng)
        enc = enc.to(device)
        logits, sl = model(enc, steps) if arm == "loop" else model(enc)
        acts = logits.argmax(-1).tolist()
        sbits = (sl > 0).tolist()
        for a, sb, inf in zip(acts, sbits, infos):
            raw = C.decode(a, inf)
            chk = raw if C.supported(a, sb, inf) else "UNKNOWN"
            res.append((raw, chk))
    return res


def score(items, answers, cat_key):
    by = defaultdict(Counter)
    for it, (raw, chk) in zip(items, answers):
        c = it[cat_key]
        g = C._key(it["gold"]["answer"])
        for tag, p in (("raw", raw), ("checked", chk)):
            p = C._key(p)
            if p == g:
                by[c][tag + "_right"] += 1
            elif p == "unknown":
                by[c][tag + "_idk"] += 1
            elif g == "unknown":
                by[c][tag + "_answered_without_fact"] += 1
            else:
                by[c][tag + "_wrong"] += 1
        by[c]["n"] += 1
    tot = Counter()
    for c in by.values():
        tot.update(c)
    return {"total": dict(tot), "by_category": {k: dict(v) for k, v in sorted(by.items())}}


def dev(a):
    device = torch.device(a.device)
    model, arm = load(a.ckpt, device)
    rng = random.Random(777)
    items = []
    for k in ALL_KINDS + ["value3"]:
        for _ in range(a.n):
            e = C.gen_episode(rng, k); e["cat"] = k; items.append(e)
    for _ in range(a.n):
        e = C.gen_episode(rng, rng.choice(["value1", "value2"]), n_rows=(30, 40))
        e["cat"] = "big_notebook"; items.append(e)
    out = {}
    for st in ([6, 12, 20] if arm == "loop" else [None]):
        out[f"steps_{st}"] = score(items, answer(model, arm, items, device, st or EVAL_STEPS), "cat")
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({k: v["total"] for k, v in out.items()}))


def evaluate(a):
    device = torch.device(a.device)
    model, arm = load(a.ckpt, device)
    items = [json.loads(l) for l in open(a.panel)]
    res = score(items, answer(model, arm, items, device, EVAL_STEPS), "category")
    res.update({"ckpt": str(a.ckpt), "arm": arm, "eval_steps": EVAL_STEPS if arm == "loop" else None,
                "items": len(items)})
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps(res["total"]))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("train")
    t.add_argument("--arm", choices=["loop", "plain"], required=True)
    t.add_argument("--seed", type=int, default=1)
    t.add_argument("--out", required=True)
    t.add_argument("--size", default="30m")
    t.add_argument("--copy-steps", type=int, default=6000)
    t.add_argument("--rl-steps", type=int, default=6000)
    t.add_argument("--batch", type=int, default=256)
    t.add_argument("--rl-batch", type=int, default=128)
    t.add_argument("--lr", type=float, default=3e-4)
    t.add_argument("--workers", type=int, default=6)
    t.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    d = sp.add_parser("dev")
    d.add_argument("--ckpt", required=True)
    d.add_argument("--out", required=True)
    d.add_argument("--n", type=int, default=100)
    d.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    e = sp.add_parser("eval")
    e.add_argument("--ckpt", required=True)
    e.add_argument("--panel", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = p.parse_args()
    {"train": train, "dev": dev, "eval": evaluate}[a.cmd](a)
