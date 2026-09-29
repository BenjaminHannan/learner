#!/usr/bin/env python3
"""Translator check (helper trn, 2026-09-29). Marks: artifacts/claude-dir-trn-20260929/PASSMARKS.md.

Frozen practised loop -> round-48 state -> small decoder (state only, never the puzzle tokens) -> answer tokens.
Controls: A input embedding only, B untrained loop state, C shuffled-weights loop state; row P: plain net state.

  python -B scripts/claude_dir_trn_decode.py run --src ARTIFACT_ROOT --out DIR [--steps 3000] [--tasks sums,mazes]
  python -B scripts/claude_dir_trn_decode.py selftest
"""
from __future__ import annotations
import argparse, copy, json, math, random, sys, time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_net as N      # noqa: E402
import claude_fewex_data as D     # noqa: E402
import claude_rsn358a_envs as E   # noqa: E402

TRAIN_SEED, DEV_SUM_SEED = 9302900, 9302901
LOOP_WEIGHTS = 1_645_726
CAP = LOOP_WEIGHTS // 10          # 164,572
ROUNDS = 48
SOURCES = ("L", "A", "B", "C", "P")


# ---------------- data ----------------
def sum_key(it): return (it.meta["a"], it.meta["b"])


def make_sums(n_train, n_dev):
    dev_rng, tr_rng = random.Random(DEV_SUM_SEED), random.Random(TRAIN_SEED + 1)
    dev, seen = [], set()
    while len(dev) < n_dev:
        it = E.make_sum(dev_rng, 4)
        if sum_key(it) not in seen:
            seen.add(sum_key(it)); dev.append(it)
    train, ban = [], set(seen)
    while len(train) < n_train:
        it = E.make_sum(tr_rng, 4)
        if sum_key(it) not in ban:
            ban.add(sum_key(it)); train.append(it)
    assert not ({sum_key(i) for i in train} & {sum_key(i) for i in dev})
    return train, dev


def make_mazes(n_train):
    pan, banned = D.panels()
    dev = pan["dev"][9]
    rng, seen, train = random.Random(TRAIN_SEED + 2), set(), []
    while len(train) < n_train:
        train.append(D.unique_maze(rng, 9, banned, seen))
    assert not ({D.layout_key(i) for i in train} & {D.layout_key(i) for i in dev})
    return train, dev


# ---------------- frozen nets ----------------
def load_net(arm, path):
    net = N.Net(arm)
    d = torch.load(path, map_location="cpu", weights_only=True)
    net.load_state_dict(d["state"] if "state" in d and "tok.weight" not in d else d)
    return net.eval().requires_grad_(False)


def untrained(arm, seed):
    torch.manual_seed(seed)
    return N.Net(arm).eval().requires_grad_(False)


def shuffled(net, seed):
    net = copy.deepcopy(net)
    g = torch.Generator().manual_seed(seed)
    with torch.no_grad():
        for p in net.parameters():
            p.copy_(p.flatten()[torch.randperm(p.numel(), generator=g)].view_as(p))
    return net.eval().requires_grad_(False)


@torch.no_grad()
def encode(net, items, kind, bs=64):
    """kind 'state': final loop round (48) or plain last block output; 'embed': token+slot embedding only.
    Returns (memory [N,T,d] half, slot [N,T], target [N,T], head_ok [N] the net's own output head is exact)."""
    mem, slots, ys, ok = [], [], [], []
    for i in range(0, len(items), bs):
        t, s, y = N.tensors(items[i:i + bs])
        e, (dr, dc) = net.embed(t, s)
        if kind == "embed":
            h = e
        elif net.arm == "loop":
            h = torch.zeros_like(e)
            for _ in range(ROUNDS):
                h = net.step(h, e, dr, dc)
        else:
            h = e
            for b in net.blocks:
                h = b(h, dr, dc)
        B = t.shape[0]
        sb, yb = s.view(B, -1).bool(), y.view(B, -1)
        ok.append(((net.read(h)[0].argmax(-1) == yb) | ~sb).all(1))
        mem.append(h.half()); slots.append(s.view(B, -1)); ys.append(yb)
    return torch.cat(mem), torch.cat(slots), torch.cat(ys), torch.cat(ok)


# ---------------- decoder ----------------
class Layer(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.n1, self.n2, self.n3 = nn.LayerNorm(d), nn.LayerNorm(d), nn.LayerNorm(d)
        self.sa = nn.MultiheadAttention(d, h, batch_first=True)
        self.ca = nn.MultiheadAttention(d, h, batch_first=True)
        self.mlp = nn.Sequential(nn.Linear(d, 128), nn.GELU(), nn.Linear(128, d))

    def forward(self, q, m):
        x = self.n1(q)
        q = q + self.sa(x, x, x, need_weights=False)[0]
        q = q + self.ca(self.n2(q), m, m, need_weights=False)[0]
        return q + self.mlp(self.n3(q))


class Dec(nn.Module):
    def __init__(self, d_in, T, d=64, layers=2, heads=4):
        super().__init__()
        self.proj = nn.Sequential(nn.Linear(d_in, d), nn.LayerNorm(d))
        self.mpos = nn.Parameter(torch.randn(T, d) * .02)
        self.qpos = nn.Parameter(torch.randn(T, d) * .02)
        self.qslot = nn.Embedding(2, d)
        self.layers = nn.ModuleList(Layer(d, heads) for _ in range(layers))
        self.ln, self.out = nn.LayerNorm(d), nn.Linear(d, E.VOCAB)

    def forward(self, mem, slot):
        m = self.proj(mem.float()) + self.mpos
        q = self.qpos + self.qslot(slot)
        for l in self.layers:
            q = l(q, m)
        return self.out(self.ln(q))

    def weight_count(self):
        return sum(p.numel() for p in self.parameters())


def exact_flags(dec, mem, slot, y, bs=256):
    dec.eval(); out = []
    with torch.no_grad():
        for i in range(0, len(mem), bs):
            sb = slot[i:i + bs].bool()
            out.append(((dec(mem[i:i + bs], slot[i:i + bs]).argmax(-1) == y[i:i + bs]) | ~sb).all(1))
    return torch.cat(out)


def train_dec(train, dev, seed, steps, bs=64, lr=2e-3):
    """train/dev = (mem, slot, y). Returns (dec, dev exact flags, train-pool exact flags on the first 300)."""
    mem, slot, y = train
    torch.manual_seed(seed)
    dec = Dec(mem.shape[-1], mem.shape[1])
    assert dec.weight_count() <= CAP, "decoder over size cap: %d" % dec.weight_count()
    opt = torch.optim.AdamW(dec.parameters(), lr=lr, weight_decay=0.01)
    warm = 100
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / warm) * .5 * (1 + math.cos(math.pi * min(i, steps) / steps)))
    g = torch.Generator().manual_seed(seed)
    for _ in range(steps):
        dec.train()
        idx = torch.randint(0, len(mem), (bs,), generator=g)
        sb = slot[idx].bool()
        loss = F.cross_entropy(dec(mem[idx], slot[idx])[sb], y[idx][sb])
        opt.zero_grad(set_to_none=True); loss.backward(); opt.step(); sched.step()
    return dec, exact_flags(dec, *dev), exact_flags(dec, mem[:300], slot[:300], y[:300])


# ---------------- run ----------------
def task_items(task, n_train):
    return make_sums(n_train, 300) if task == "sums" else make_mazes(n_train)


def net_paths(src, task, arm, s):
    root = Path(src) / "artifacts/claude-fewex-20260927"
    return root / (f"runs/{arm}-s{s}/source.pt" if task == "sums" else f"eq-runs/{arm}-s{s}-pre/k16384.pt")


def run_task(task, nets_for, out, steps, n_train, seeds=(0, 1), dseeds=(0, 1), log=print):
    train, dev = task_items(task, n_train)
    rows = []
    for s in seeds:
        loop, plain = nets_for(task, "loop", s), nets_for(task, "plain", s)
        ctrl = {"A": (loop, "embed"), "B": (untrained("loop", 500 + s), "state"), "C": (shuffled(loop, 600 + s), "state"),
                "L": (loop, "state"), "P": (plain, "state")}
        for src in SOURCES:
            net, kind = ctrl[src]
            tr = encode(net, train, kind)[:3]
            dv = encode(net, dev, kind)
            head = int(dv[3].sum())
            for ds in dseeds:
                t0 = time.time()
                dec, fd, ft = train_dec(tr, dv[:3], ds, steps)
                row = {"task": task, "seed": s, "src": src, "dseed": ds, "dev_exact": int(fd.sum()), "dev_n": len(dev),
                       "train300_exact": int(ft.sum()), "own_head_exact": head, "dec_weights": dec.weight_count(),
                       "steps": steps, "sec": round(time.time() - t0, 1), "dev_flags": [int(x) for x in fd.tolist()]}
                rows.append(row)
                log("trn %s s%d %s d%d dev %d of %d train300 %d of 300 (own head %d) %ss" % (
                    task, s, src, ds, row["dev_exact"], len(dev), row["train300_exact"], head, row["sec"]))
                (Path(out) / f"{task}.json").write_text(json.dumps(rows, indent=1) + "\n")
    return rows


def main_run(a):
    torch.set_num_threads(a.threads)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    def nets_for(task, arm, s):
        p = net_paths(a.src, task, arm, s)
        if not p.exists():
            raise SystemExit("MISSING-NET: %s" % p)
        return load_net(arm, p)
    for task in a.tasks.split(","):
        run_task(task, nets_for, out, a.steps, a.train_n[task])


def selftest():
    torch.set_num_threads(2)
    tr, dv = make_sums(64, 300)
    assert len({sum_key(i) for i in tr + dv}) == 364
    n = Dec(256, 15).weight_count(); m = Dec(256, 81).weight_count()
    assert n <= CAP and m <= CAP, (n, m)
    # positive control: a memory that holds the answer must be decodable (checks the decoder/scorer, not the loop)
    tr, dv = make_sums(2048, 300)
    def onehot(items):
        t, s, y = N.tensors(items)
        B, T = y.shape[0], y.shape[1] * y.shape[2]
        y, s = y.view(B, T), s.view(B, T)
        return F.one_hot(y, E.VOCAB).float(), s, y
    (mt, st, yt), (md, sd, yd) = onehot(tr), onehot(dv)
    dec, fd, _ = train_dec((mt, st, yt), (md, sd, yd), 0, 1500)
    assert int(fd.sum()) >= 290, int(fd.sum())
    # random-init pipeline end to end, tiny
    lp, pl = untrained("loop", 1), untrained("plain", 2)
    rows = run_task("sums", lambda t, a, s: lp if a == "loop" else pl, Path("/tmp"), 20, 128, seeds=(0,), dseeds=(0,), log=lambda *_: None)
    assert [r["src"] for r in rows] == list(SOURCES) and all(r["dec_weights"] <= CAP for r in rows)
    assert not any(p.requires_grad for p in lp.parameters())
    sh = shuffled(lp, 3)
    assert sorted(lp.tok.weight.flatten().tolist()) == sorted(sh.tok.weight.flatten().tolist()) and not torch.equal(lp.tok.weight, sh.tok.weight)
    mz, mdv = make_mazes(8)
    assert len(mdv) == 300 and mz[0].size == 9
    print("trn selftest ok (sums %d, mazes %d decoder weights, cap %d; positive control %d of 300)" % (n, m, CAP, int(fd.sum())))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("run"); r.add_argument("--src", required=True); r.add_argument("--out", required=True)
    r.add_argument("--steps", type=int, default=3000); r.add_argument("--tasks", default="sums,mazes")
    r.add_argument("--threads", type=int, default=4)
    sp.add_parser("selftest")
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    else:
        a.train_n = {"sums": 8192, "mazes": 4096}
        main_run(a)
