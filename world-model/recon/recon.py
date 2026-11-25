# STEP 2: can the board hold the CURRENT frame? (marks pinned in STATUS.md before running)
import argparse, json, os, time, numpy as np, torch, torch.nn as nn, wm_fit as W, sizes
ap=argparse.ArgumentParser(); ap.add_argument("--device",default="mps"); ap.add_argument("--size",default="P7toy")
ap.add_argument("--steps",type=int,default=3000); ap.add_argument("--max-minutes",type=float,default=20); ap.add_argument("--out",default="run_recon")
ap.add_argument("--bypass",action="store_true"); ap.add_argument("--fixed-scale",action="store_true"); ap.add_argument("--ridge",action="store_true"); a=ap.parse_args(); os.makedirs(a.out,exist_ok=True); dev=a.device
torch.manual_seed(42); m=W.WorldModel(sizes.make_cfg(a.size)).to(dev); del m.head
class Dec(nn.Module):
    def __init__(s,n):
        super().__init__(); s.bn=nn.BatchNorm1d(n,affine=False,eps=1e-3); s.lin=nn.Linear(n,768); s.mlp=nn.Sequential(nn.Linear(n,256),nn.GELU(),nn.Linear(256,768))
    def forward(s,z): z=s.bn(z.flatten(1)); return (s.lin(z)+s.mlp(z)).reshape(-1,16,16,3)
n=(16 if a.bypass else m.R)*m.D; dec=Dec(n).to(dev)
def board(xp,xt):
    if a.bypass:  # decode straight from reader tokens (no trunk)
        B=xt.shape[0]; p=xt.reshape(B,4,4,4,4,3).permute(0,1,3,2,4,5).reshape(B,16,48); return W.rms_level(m.reader(p)+m.pos[None])
    st=m.read(m.cell.init_state(xt.shape[0],1,device=dev,dtype=torch.float32),m.encode(xp)); return m.read(st,m.encode(xt)).rows[:,0]
def chg(xp,xt): return ((xt-xp).abs().mean(-1,keepdim=True)>0.02).float()
tr=W.load_split("data/train.npz"); he=W.load_split("data/heldout.npz")
if a.fixed_scale:  # try 2: ONE fixed train-set RMS scale (computed once at init) instead of per-token unit RMS
    with torch.no_grad():
        f=torch.from_numpy(tr["frames"][:2048].astype(np.float32)).to(dev); B=f.shape[0]
        p=f.reshape(B,4,4,4,4,3).permute(0,1,3,2,4,5).reshape(B,16,48); SCALE=float((m.reader(p)+m.pos[None]).pow(2).mean().sqrt())
    print("fixed scale",SCALE); W.rms_level=lambda t: t/SCALE
def wins(d): xi=W.windows(d,1)[0]; return xi  # frame t-1 = xi, frame t = xi+1
xtr,xhe=wins(tr),wins(he); F=lambda d,i: torch.from_numpy(d["frames"][i].astype(np.float32)).to(dev)
params=list(dec.parameters())+([*m.reader.parameters(),m.pos] if a.bypass else list(m.parameters()))
opt=torch.optim.Adam(params,lr=3e-4); rng=np.random.default_rng(42); t0=time.time(); done=0
for s in range(a.steps):
    j=rng.integers(0,len(xtr),64); xp,xt=F(tr,xtr[j]),F(tr,xtr[j]+1); y=dec(board(xp,xt)); c=chg(xp,xt)
    loss=((y-xt)**2).mean()+(((y-xt)**2)*c).sum()/(c.sum()*3+1e-6)
    opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(params,1.0); opt.step(); done=s+1
    if s<5 or (s+1)%250==0: print(f"step {s} loss {loss.item():.5f} t {time.time()-t0:.0f}s",flush=True)
    if time.time()-t0>a.max_minutes*60: print("cap hit at",done); break
dec.bn.reset_running_stats(); dec.bn.momentum=None; rc=np.random.default_rng(7)
with torch.no_grad():
    for _ in range(50): j=rc.integers(0,len(xtr),64); dec(board(F(tr,xtr[j]),F(tr,xtr[j]+1)))
dec.eval(); mean=torch.from_numpy(np.concatenate([tr["frames"][xtr+1][::7]]).astype(np.float32).mean(0)).to(dev)
S={k:0.0 for k in ["e","mean","e_c","mean_c","copy_c","blank_c","shuf"]}
with torch.no_grad():
    for b in range(0,len(xhe),128):
        i=xhe[b:b+128]; xp,xt=F(he,i),F(he,i+1); c=chg(xp,xt); z=board(xp,xt); y=dec(z)
        yb=dec(board(xp,torch.zeros_like(xt))) ; perm=torch.randperm(len(i),generator=torch.Generator().manual_seed(43)).to(dev); ys=dec(z[perm])
        e=(y-xt)**2; S["e"]+=e.sum().item(); S["mean"]+=((mean-xt)**2).sum().item(); S["e_c"]+=(e*c).sum().item()
        S["mean_c"]+=(((mean-xt)**2)*c).sum().item(); S["copy_c"]+=(((xp-xt)**2)*c).sum().item(); S["blank_c"]+=(((yb-xt)**2)*c).sum().item(); S["shuf"]+=((ys-xt)**2).sum().item()
r=dict(steps=done,bypass=a.bypass,M1_all_vs_mean=S["e"]/S["mean"],M2_changed_vs_mean=S["e_c"]/S["mean_c"],M2_changed_vs_copy=S["e_c"]/S["copy_c"],
       C1_blank_rise=S["blank_c"]/S["e_c"],C2_shuffled_all_vs_mean=S["shuf"]/S["mean"],windows=len(xhe))
r["PASS"]=bool(r["M1_all_vs_mean"]<=0.10 and r["M2_changed_vs_mean"]<=0.25 and r["M2_changed_vs_copy"]<1.0 and r["C1_blank_rise"]>=2 and r["C2_shuffled_all_vs_mean"]>=0.9)
print(json.dumps(r,indent=1)); json.dump(r,open(f"{a.out}/score.json","w"),indent=1)
torch.save({"m":m.state_dict(),"dec":dec.state_dict()},f"{a.out}/model.pt")
if a.ridge:  # exact closed-form readout on the TRAINED board (pinned before running); train worlds only for fitting
    def feats(d,idx,blank=False):
        out=[]
        with torch.no_grad():
            for b in range(0,len(idx),128):
                i=idx[b:b+128]; xp,xt=F(d,i),F(d,i+1); out.append(board(xp,torch.zeros_like(xt) if blank else xt).flatten(1).cpu().double().numpy())
        return np.concatenate(out)
    rr=np.random.default_rng(11); ji=rr.choice(len(xtr),4000,replace=False); fit,val=ji[:3500],ji[3500:]
    Zf,Zv=feats(tr,xtr[fit]),feats(tr,xtr[val]); mu,sd=Zf.mean(0),Zf.std(0)+1e-6; nz=lambda Z:(Z-mu)/sd
    Y=lambda d,i: d["frames"][i+1].astype(np.float64).reshape(len(i),-1); Yf,Yv=Y(tr,xtr[fit]),Y(tr,xtr[val]); ym=Yf.mean(0)
    A=nz(Zf); K=A@A.T; best=None
    for lam in (1e-3,1e-1,1e1,1e3,1e5):
        al=np.linalg.solve(K+lam*np.eye(len(A)),Yf-ym); e=((nz(Zv)@A.T@al+ym-Yv)**2).sum()
        if best is None or e<best[0]: best=(e,lam,al)
    _,lam,al=best; pred=lambda Z: (nz(Z)@A.T@al+ym).reshape(-1,16,16,3)
    Zh=feats(he,xhe); Zb=feats(he,xhe,blank=True); xp=he["frames"][xhe].astype(np.float64); xt=he["frames"][xhe+1].astype(np.float64)
    c=(np.abs(xt-xp).mean(-1,keepdims=True)>0.02).astype(np.float64); mf=Yf.mean(0).reshape(16,16,3)
    yh,yb=pred(Zh),pred(Zb); ys=pred(Zh[np.random.default_rng(43).permutation(len(Zh))])
    e=(yh-xt)**2; em=(mf-xt)**2
    q=dict(lam=lam,M1_all_vs_mean=e.sum()/em.sum(),M2_changed_vs_mean=(e*c).sum()/(em*c).sum(),M2_changed_vs_copy=(e*c).sum()/(((xp-xt)**2)*c).sum(),
           C1_blank_rise=(((yb-xt)**2)*c).sum()/(e*c).sum(),C2_shuffled_all_vs_mean=((ys-xt)**2).sum()/em.sum())
    q={k:float(v) for k,v in q.items()}
    q["PASS"]=bool(q["M1_all_vs_mean"]<=0.10 and q["M2_changed_vs_mean"]<=0.25 and q["M2_changed_vs_copy"]<1.0 and q["C1_blank_rise"]>=2 and q["C2_shuffled_all_vs_mean"]>=0.9)
    print("RIDGE",json.dumps(q)); json.dump(q,open(f"{a.out}/ridge.json","w"),indent=1)
