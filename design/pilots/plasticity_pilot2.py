"""Pilot: does a tiny transformer lose plasticity on a permuted-vocabulary token stream
within minutes on one GPU, and does weight decay prevent it?  (Modelled on the
Permuted-Shakespeare setup of Farias & Jozefiak, ICLR 2025, but with a synthetic
controlled 'language' so nothing is downloaded.)  Writes no files."""
import math, time, sys, os
import torch, torch.nn as nn, torch.nn.functional as F

torch.manual_seed(0)
dev = "cuda" if torch.cuda.is_available() else "cpu"
V = int(os.environ.get("V", "32")); CTX, BATCH = 128, 32
CORPUS = int(os.environ.get("CORPUS", "32768"))
TASKS = int(os.environ.get("TASKS", "40"))
STEPS = int(os.environ.get("STEPS", "600"))
LR = float(os.environ.get("LR", "1e-3"))

# --- controlled language: random sparse order-2 Markov process (3 successors per context)
g = torch.Generator().manual_seed(1)
succ = torch.randint(0, V, (V, V, 3), generator=g)
probs = torch.tensor([0.6, 0.3, 0.1])
seq = [1, 2]
choice = torch.multinomial(probs, CORPUS, replacement=True, generator=g)
for i in range(CORPUS):
    seq.append(int(succ[seq[-2], seq[-1], choice[i]]))
corpus = torch.tensor(seq, device=dev)

class Block(nn.Module):
    def __init__(s, d=32, h=2, ff=256):
        super().__init__()
        s.ln1, s.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        s.qkv, s.o = nn.Linear(d, 3 * d), nn.Linear(d, d)
        s.fc1, s.fc2 = nn.Linear(d, ff), nn.Linear(ff, d)
        s.h = h
    def forward(s, x):
        B, T, D = x.shape
        q, k, v = s.qkv(s.ln1(x)).view(B, T, 3, s.h, D // s.h).permute(2, 0, 3, 1, 4)
        a = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + s.o(a.transpose(1, 2).reshape(B, T, D))
        hdn = F.relu(s.fc1(s.ln2(x)))
        s.last_act = hdn
        return x + s.fc2(hdn)

class LM(nn.Module):
    def __init__(s, d=32):
        super().__init__()
        s.emb, s.pos = nn.Embedding(V, d), nn.Parameter(torch.randn(CTX, d) * 0.02)
        s.blk, s.lnf, s.out = Block(d), nn.LayerNorm(d), nn.Linear(d, V)
    def forward(s, x):
        return s.out(s.lnf(s.blk(s.emb(x) + s.pos[: x.shape[1]])))

def make_arm(name, wd, replay=0):
    torch.manual_seed(0)
    m = LM().to(dev)
    opt = torch.optim.AdamW(m.parameters(), lr=LR, weight_decay=wd)
    return dict(name=name, m=m, opt=opt, log=[], replay=replay, anchor=[])

arms = [make_arm("adam_noWD+replay", 0.0, 4), make_arm("adamw_wd1.0", 1.0), make_arm("adamw_wd1.0+replay", 1.0, 4)]
anchor_perm = None

def batch(perm):
    idx = torch.randint(0, CORPUS - CTX - 1, (BATCH,), device=dev)
    off = torch.arange(CTX + 1, device=dev)
    chunk = perm[corpus[idx[:, None] + off]]
    return chunk[:, :-1], chunk[:, 1:]

t0 = time.time()
print(f"device={dev} params={sum(p.numel() for p in arms[0]['m'].parameters())} tasks={TASKS} steps/task={STEPS} lr={LR}", flush=True)
for task in range(TASKS):
    perm = torch.randperm(V, device=dev)
    if anchor_perm is None: anchor_perm = perm
    for arm in arms:
        losses = []
        m, opt = arm["m"], arm["opt"]
        torch.manual_seed(1000 + task)
        for step in range(STEPS):
            x, y = batch(perm)
            if arm["replay"] and task > 0:   # replace a few of the 32 sequences with task-1 (anchor) data
                xa, ya = batch(anchor_perm)
                r = arm["replay"]; x = torch.cat([x[r:], xa[:r]]); y = torch.cat([y[r:], ya[:r]])
            per = F.cross_entropy(m(x).reshape(-1, V), y.reshape(-1), reduction="none").view(BATCH, CTX)
            loss = per.mean()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            ncur = BATCH - (arm["replay"] if task > 0 else 0)
            losses.append(per[:ncur].mean().detach())   # log current-task loss only
        L = torch.stack(losses)
        dead = (m.blk.last_act.reshape(-1, 256) > 0).float().amax(0).eq(0).float().mean().item()
        wn = math.sqrt(sum(float(p.detach().pow(2).sum()) for p in m.parameters()))
        arm["log"].append((L.mean().item(), L[-50:].mean().item(), dead, wn))
        if task % 10 == 9:
            with torch.no_grad():
                torch.manual_seed(7); al = sum(F.cross_entropy(m(xa).reshape(-1, V), ya.reshape(-1)).item() for xa, ya in [batch(anchor_perm) for _ in range(8)]) / 8
            arm["anchor"].append(round(al, 3))
    if task % 5 == 4 or task == 0:
        s = " | ".join(f"{a['name']}: auc={a['log'][-1][0]:.3f} end={a['log'][-1][1]:.3f} dead={a['log'][-1][2]:.2f} |w|={a['log'][-1][3]:.0f}" for a in arms)
        print(f"task {task+1:3d} t={time.time()-t0:5.0f}s  {s}", flush=True)
print("entropy floor of the language (nats) ~", round(-(probs * probs.log()).sum().item(), 3))
for a in arms:
    lg = a["log"]
    first = sum(r[0] for r in lg[:5]) / 5
    last = sum(r[0] for r in lg[-5:]) / 5
    print(f"{a['name']}: mean-loss-during-task first5={first:.3f} last5={last:.3f}  end-loss first5={sum(r[1] for r in lg[:5])/5:.3f} last5={sum(r[1] for r in lg[-5:])/5:.3f}")
for a in arms: print(a["name"], "task-1 (anchor) loss every 10 tasks:", a["anchor"])
print(f"total {time.time()-t0:.0f}s")
