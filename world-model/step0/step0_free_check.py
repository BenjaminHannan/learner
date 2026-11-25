# Step 0 free check (no training). Pixel gate + copy/blend baselines on 16x16 pooled Crafter frames.
import json, numpy as np, crafter
def pool(o): return o.reshape(16,4,16,4,3).mean((1,3)).astype(np.float64)/255.0
def mse(a,b): return float(((a-b)**2).mean())
NOOP, MOVES = 0, [1,2,3,4]
def run(seed, acts):
    e = crafter.Env(seed=seed); o = e.reset(); fr=[pool(o)]
    for a in acts:
        o,_,d,_ = e.step(a); fr.append(pool(o))
        if d: break
    return fr
rng = np.random.default_rng(7); gate=[]
for i in range(24):
    seed = 5000+i; L = int(rng.integers(5,60)); pre = list(rng.integers(0,17,L))
    mv = int(rng.choice(MOVES))
    fm = run(seed, pre+[mv])[-1]; fn1 = run(seed, pre+[NOOP])[-1]; fn2 = run(seed, pre+[NOOP])[-1]
    gate.append((mse(fm,fn1), mse(fn1,fn2)))
passes = sum(m > n+1e-4 for m,n in gate)
# random-policy episodes: 20 seeds x 250 steps
eps=[]
for s in range(20):
    r=np.random.default_rng(100+s); eps.append(np.stack(run(s, list(r.integers(0,17,250)))))
moved = np.mean([ (((ep[1:]-ep[:-1])**2).mean((1,2,3))>1e-6).mean() for ep in eps])
tr, te = eps[:10], eps[10:]; mean = np.concatenate(tr).mean(0)
out={"gate_pass_count":passes,"gate_of":24,"gate_pass":passes>=8,
     "gate_move_mse_median":float(np.median([g[0] for g in gate])),"gate_noop_noop_max":float(max(g[1] for g in gate)),
     "share_moved_steps":float(moved),"n_steps":int(sum(len(e)-1 for e in eps))}
for k in (1,3,5):
    def pairs(E): return np.concatenate([e[:-k] for e in E]), np.concatenate([e[k:] for e in E])
    x,y = pairs(tr); d=(x-mean); a = float(((y-mean)*d).sum()/(d*d).sum())
    x,y = pairs(te); copy = float(((y-x)**2).sum()); blend=float(((y-(mean+a*(x-mean)))**2).sum())
    out[f"k{k}"]={"copy_SSE":copy,"blend_SSE":blend,"blend_a":a,"B":min(copy,blend),"blend_over_copy":blend/copy,"windows":len(x)}
print(json.dumps(out,indent=1)); json.dump(out,open("step0.json","w"),indent=1)
