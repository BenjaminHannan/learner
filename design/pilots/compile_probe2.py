"""Probe: does practising a taught procedure (deliberate, step-by-step execution
checked by right/wrong feedback) compile into a one-step habit faster than
learning the habit from reward alone?  Scratch only; list world copied from
memorylab/tasks.py primitives."""
import copy, random, time, sys
import torch, torch.nn as nn, torch.nn.functional as F

torch.manual_seed(0); random.seed(0)
torch.set_num_threads(8)
DEV = "cpu"
L, S = 5, 8                 # max list length, symbol count
PAD = S                     # output/input class for "empty slot"
PRIMS = ["reverse", "drop_first", "rotate_left", "swap_pairs"]

def prim(name, v):
    if name == "reverse": return v[::-1]
    if name == "drop_first": return v[1:]
    if name == "rotate_left": return v[1:] + v[:1] if len(v) > 1 else v
    r = list(v)
    for i in range(0, len(r) - 1, 2): r[i], r[i+1] = r[i+1], r[i]
    return r

def run(prog, v):
    for p in prog: v = prim(p, v)
    return v

OLD = [("reverse","swap_pairs"), ("rotate_left","rotate_left"), ("drop_first","reverse"),
       ("swap_pairs","rotate_left","reverse"), ("rotate_left","drop_first","swap_pairs"),
       ("reverse","rotate_left","rotate_left")]
NEW = [("swap_pairs","reverse","rotate_left"), ("rotate_left","swap_pairs","drop_first"),
       ("reverse","drop_first","rotate_left"), ("swap_pairs","rotate_left","swap_pairs")]
OPS = [(p,) for p in PRIMS] + OLD + NEW      # op id -> program
N_PRIM, N_OLD = len(PRIMS), len(OLD)
OLD_IDS = list(range(N_PRIM, N_PRIM + N_OLD)); NEW_IDS = list(range(N_PRIM + N_OLD, len(OPS)))

def rand_list(): return [random.randrange(S) for _ in range(random.randint(1, L))]
def pad(v): return v + [PAD] * (L - len(v))

def batch(op_ids, lists=None):
    lists = lists or [rand_list() for _ in op_ids]
    x = torch.tensor([pad(v) for v in lists]); o = torch.tensor(op_ids)
    y = torch.tensor([pad(run(OPS[i], v)) for i, v in zip(op_ids, lists)])
    return o, x, y, lists

class Net(nn.Module):
    def __init__(s, d=96):
        super().__init__()
        s.op = nn.Embedding(len(OPS), d); s.sym = nn.Embedding(S + 1, d); s.pos = nn.Parameter(torch.randn(L + 1, d) * .02)
        s.enc = nn.TransformerEncoder(nn.TransformerEncoderLayer(d, 4, 4 * d, 0.0, batch_first=True, norm_first=True), 3)
        s.out = nn.Linear(d, S + 1)
    def forward(s, o, x):
        h = torch.cat([s.op(o)[:, None], s.sym(x)], 1) + s.pos
        return s.out(s.enc(h)[:, 1:])             # (B, L, S+1)

def acc(net, ids, n=1024):
    with torch.no_grad():
        o, x, y, _ = batch([random.choice(ids) for _ in range(n)])
        return (net(o, x).argmax(-1) == y).all(-1).float().mean().item()

def deliberate(net, ids, x):
    """Execute each taught program one primitive per forward pass (the slow path)."""
    steps = torch.tensor([[PRIMS.index(p) for p in OPS[i]] for i in ids])  # (B, 3)
    with torch.no_grad():
        for k in range(steps.shape[1]):
            x = net(steps[:, k], x).argmax(-1)
    return x

def deliberate_acc(net, n=1024):
    ids = [random.choice(NEW_IDS) for _ in range(n)]
    o, x, y, _ = batch(ids)
    return (deliberate(net, ids, x) == y).all(-1).float().mean().item()

t0 = time.time()
net = Net(); opt = torch.optim.Adam(net.parameters(), 1e-3)
for step in range(2500):                         # Stage A: primitives + old named skills
    o, x, y, _ = batch([random.randrange(N_PRIM + N_OLD) for _ in range(256)])
    loss = F.cross_entropy(net(o, x).reshape(-1, S + 1), y.reshape(-1))
    opt.zero_grad(); loss.backward(); opt.step()
print(f"stageA {time.time()-t0:.0f}s prim={acc(net, range(N_PRIM)):.3f} old={acc(net, OLD_IDS):.3f} "
      f"new_habit={acc(net, NEW_IDS):.3f} new_deliberate={deliberate_acc(net):.3f}", flush=True)
base = copy.deepcopy(net.state_dict())

def practice(arm, updates=600, bs=64, replay=True):
    m = Net(); m.load_state_dict(base); op = torch.optim.Adam(m.parameters(), 1e-3)
    curve = []; used = 0
    for u in range(updates + 1):
        if u % 100 == 0: curve.append((u * bs, round(acc(m, NEW_IDS, 512), 3)))
        if u == updates: break
        ids = [random.choice(NEW_IDS) for _ in range(bs)]
        o, x, y, _ = batch(ids)
        if arm.startswith("compile"):
            tgt = deliberate(m, ids, x)
            ok = (tgt == y).all(-1) if arm == "compile_checked" else torch.ones(bs, dtype=torch.bool)  # right/wrong feedback
            used += int(ok.sum())
            loss = F.cross_entropy(m(o, x)[ok].reshape(-1, S + 1), tgt[ok].reshape(-1)) if ok.any() else 0 * m.pos.sum()
        else:                                     # reward only: sample answer, get per-slot right/wrong
            logits = m(o, x); dist = torch.distributions.Categorical(logits=logits); a = dist.sample()
            r = (a == y).float() if arm == "rl_slot" else (a == y).all(-1, keepdim=True).float().expand_as(a)
            loss = -((r - r.mean(0, keepdim=True)) * dist.log_prob(a)).mean() - 0.01 * dist.entropy().mean()
        if replay:                                # interleave old experiences (primitives + old skills)
            o2, x2, y2, _ = batch([random.randrange(N_PRIM + N_OLD) for _ in range(bs)])
            loss = loss + F.cross_entropy(m(o2, x2).reshape(-1, S + 1), y2.reshape(-1))
        op.zero_grad(); loss.backward(); op.step()
    return curve, acc(m, range(N_PRIM)), acc(m, OLD_IDS)

for seed in range(3):
  random.seed(100+seed); torch.manual_seed(100+seed)
  for arm, rep in [("compile_checked", True), ("compile_trust", True), ("compile_checked", False), ("rl_slot", True), ("rl_exact", True)]:
    t = time.time(); curve, p, o_ = practice(arm, replay=rep)
    print(f"seed{seed} {arm:16s} replay={rep!s:5s} {time.time()-t:4.0f}s prim={p:.3f} old={o_:.3f} curve(practice_problems, habit_acc)={curve}", flush=True)
