"""Unregistered small CPU trial (sleep research, 2026-09-26): which attention design lets both sums and grids
work on wider pages? Small nets (plain d128x8, loop d256x2), practice sums 1-4 digits + grids 4-5 (358g legend fix),
fresh test puzzles from new seeds (never the sealed test files). Designs:
  base   358a as is: learned row/col offset bias, offsets clipped at 4
  mixed  heads 0-3 see only columns within 1 (rows unrestricted); heads 4-7 as base
  fade   base plus fixed per-head distance penalty on rows and columns, slope 2^-h (h=0..7; head 7 almost global)
"""
import argparse, json, math, random, sys, time
sys.path.insert(0, "/home/user/learner/scripts")
import torch, torch.nn as nn, torch.nn.functional as F
import claude_rsn358g_run as G  # noqa  (installs legend grids + v2 stop)
R, E = G.R, G.E
CLIP = R.CLIP

class Block(nn.Module):
    def __init__(self, d, h, design):
        super().__init__()
        self.h, self.design = h, design
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.out = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.mlp = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Linear(4 * d, d))
        self.br = nn.Parameter(torch.zeros(h, 2 * CLIP + 1)); self.bc = nn.Parameter(torch.zeros(h, 2 * CLIP + 1))
        self.register_buffer("slope", torch.tensor([2.0 ** -i for i in range(h)]), persistent=False)
    def forward(self, x, dr, dc):
        B, T, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        ir, ic = dr.clamp(-CLIP, CLIP) + CLIP, dc.clamp(-CLIP, CLIP) + CLIP
        bias = self.br[:, ir] + self.bc[:, ic]
        if self.design == "mixed":
            far = (dc.abs() > 1)
            m = torch.zeros(self.h, T, T); m[: self.h // 2] = far.float() * -1e9
            bias = bias + m
        elif self.design == "fade":
            bias = bias - self.slope[:, None, None] * (dr.abs() + dc.abs()).float()
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=bias.unsqueeze(0))
        x = x + self.out(a.transpose(1, 2).reshape(B, T, D))
        return x + self.mlp(self.ln2(x))

def raw_offsets(H, W, device):
    r = torch.arange(H, device=device).repeat_interleave(W); c = torch.arange(W, device=device).repeat(H)
    return r[:, None] - r[None, :], c[:, None] - c[None, :]
R.Net.offsets = staticmethod(raw_offsets)
R.ARMS["plain"] = dict(d=128, layers=8, heads=8); R.ARMS["loop"] = dict(d=256, layers=2, heads=8)

def make_net(arm, design):
    net = R.Net(arm); c = R.ARMS[arm]
    net.blocks = nn.ModuleList(Block(c["d"], c["heads"], design) for _ in range(c["layers"]))
    return net

def batch(rng, latin, B):
    env = rng.choice(["sums", "grids"])
    if env == "sums":
        n = rng.choice([1, 2, 3, 4]); return [E.make_sum(rng, n) for _ in range(B)]
    s = rng.choice([4, 5]); return [E.latin_item(rng, *E.augment_latin(rng, *rng.choice(latin[s]))) for _ in range(B)]

@torch.no_grad()
def score(net, items, rounds=(8, 16, 32)):
    net.eval(); t, s, _, env = R.tensors(items, "cpu")
    if net.arm == "plain":
        p = net.plain_forward(t, s, env).argmax(-1).tolist()
        return sum(E.check(it, R.grid_of(x, it)) for it, x in zip(items, p))
    preds, _ = net.loop_rounds(t, s, env, max(rounds))
    return {r: sum(E.check(it, R.grid_of(x, it)) for it, x in zip(items, preds[:, r - 1].tolist())) for r in rounds}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--arm"); ap.add_argument("--design"); ap.add_argument("--seed", type=int)
    ap.add_argument("--steps", type=int, default=4000); ap.add_argument("--batch", type=int, default=64); ap.add_argument("--out")
    a = ap.parse_args()
    torch.manual_seed(a.seed); torch.set_num_threads(1)
    rng = random.Random(500 + a.seed); rr = random.Random(900 + a.seed)
    latin = {s: [E.make_latin_base(rng, s) for _ in range(3000)] for s in (4, 5)}
    net = make_net(a.arm, a.design)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=0.1, betas=(0.9, 0.95))
    sch = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / 200) * 0.5 * (1 + math.cos(math.pi * min(i, a.steps) / a.steps)))
    t0 = time.time()
    for step in range(1, a.steps + 1):
        net.train(); items = batch(rng, latin, a.batch); t, s, y, env = R.tensors(items, "cpu")
        if a.arm == "plain":
            loss, _ = R.ce_and_exact(net.plain_forward(t, s, env), s, y)
        else:
            tot = rr.randint(1, R.TRAIN_ROUNDS); k = rr.randint(1, min(tot, R.GRAD_ROUNDS))
            ls = []
            for lg, q in net.loop_train(t, s, env, tot - k, k):
                c_, ex = R.ce_and_exact(lg, s, y); ls.append(c_ + 0.5 * F.binary_cross_entropy_with_logits(q.float(), ex))
            loss = torch.stack(ls).mean()
        opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0); opt.step(); sch.step()
        if step % 500 == 0: print(step, round(loss.item(), 4), f"{(time.time()-t0)/60:.1f}m", flush=True)
    trng = random.Random(77000)   # fresh test puzzles, same for every run
    tests = {f"sums{n}": [E.make_sum(trng, n) for _ in range(200)] for n in (4, 6, 8, 10, 12)}
    tests.update({f"grids{n}": [E.latin_item(trng, *E.make_latin_base(trng, n)) for _ in range(200)] for n in (5, 6, 7)})
    res = {k: score(net, v) for k, v in tests.items()}
    out = {"arm": a.arm, "design": a.design, "seed": a.seed, "steps": a.steps,
           "weights": sum(p.numel() for p in net.parameters()), "minutes": round((time.time() - t0) / 60, 1), "res": res}
    print(json.dumps(out), flush=True)
    open(a.out, "w").write(json.dumps(out))

if __name__ == "__main__":
    main()
