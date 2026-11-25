# STEP 3: forecasting with the FROZEN exact ridge readout (marks pinned in STATUS.md before running)
import argparse, dataclasses, json, os, time, numpy as np, torch, torch.nn as nn, wm_fit as W, sizes
ap=argparse.ArgumentParser(); ap.add_argument("--device",default="mps"); ap.add_argument("--size",default="P7toy")
ap.add_argument("--init",default="run_recon_ridge/model.pt"); ap.add_argument("--steps",type=int,default=1500)
ap.add_argument("--max-minutes",type=float,default=20); ap.add_argument("--out",default="run_forecast"); a=ap.parse_args()
os.makedirs(a.out,exist_ok=True); dev=a.device; SCALE=0.20385979115962982; W.rms_level=lambda t: t/SCALE  # step-2 try-2 constant
torch.manual_seed(42); m=W.WorldModel(sizes.make_cfg(a.size)).to(dev); del m.head
class Dec(nn.Module):
    def __init__(s,n):
        super().__init__(); s.bn=nn.BatchNorm1d(n,affine=False,eps=1e-3); s.lin=nn.Linear(n,768); s.mlp=nn.Sequential(nn.Linear(n,256),nn.GELU(),nn.Linear(256,768))
    def forward(s,z): z=s.bn(z.flatten(1)); return (s.lin(z)+s.mlp(z)).reshape(-1,16,16,3)
dec=Dec(m.R*m.D).to(dev)
if a.init:
    ck=torch.load(a.init,map_location=dev); m.load_state_dict(ck["m"],strict=False); dec.load_state_dict(ck["dec"])
tr=W.load_split("data/train.npz"); he=W.load_split("data/heldout.npz")
F=lambda d,i: torch.from_numpy(d["frames"][i].astype(np.float32)).to(dev)
def real_board(d,i,tpos):  # board after reading history frame then frame t (i = index of frame t)
    h=np.where(tpos>0,i-1,i); st=m.read(m.cell.init_state(len(i),1,device=dev,dtype=torch.float32),m.encode(F(d,h)))
    enc=m.encode(F(d,i)); return m.read(st,enc),enc
def imagine(st,enc,acts):  # acts [B,k] long; context frozen at frame t; rows fed back
    out=[]
    for j in range(acts.shape[1]):
        o=m.cell.imagine(st,enc,m.action_emb(acts[:,j]),wm_grad=True); st=dataclasses.replace(st,rows=o.next_rows); out.append(o)
    return out
xi1,ai1,w1,_,t1=W.windows(tr,1); rng=np.random.default_rng(42); t0=time.time(); done=0
params=list(m.parameters())+list(dec.parameters()); opt=torch.optim.Adam(params,lr=3e-4); m.train(); dec.train()
for s in range(a.steps):
    j=rng.integers(0,len(xi1),64); i=xi1[j]; st,enc=real_board(tr,i,t1[j]); xt=F(tr,i)
    with torch.no_grad(): nxt=real_board(tr,i+1,t1[j]+1)[0].rows             # real board at t+1 = fresh read of (x_t, x_{t+1}), same protocol as the readout
    o=imagine(st,enc,torch.from_numpy(tr["actions"][ai1[j]][:,None]).to(dev))[0]
    c=((F(tr,i)-F(tr,np.where(t1[j]>0,i-1,i))).abs().mean(-1,keepdim=True)>0.02).float(); y=dec(st.rows[:,0])
    l_rec=((y-xt)**2).mean()+(((y-xt)**2)*c).sum()/(c.sum()*3+1e-6); l_row=((o.next_rows-nxt)**2).mean()
    loss=l_rec+l_row+0.01*o.aux_loss; opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(params,1.0); opt.step(); done=s+1
    if s<3 or (s+1)%250==0: print(f"step {s} rec {l_rec.item():.5f} row {l_row.item():.5f} t {time.time()-t0:.0f}s",flush=True)
    if time.time()-t0>a.max_minutes*60: print("cap hit at",done); break
m.eval(); torch.save({"m":m.state_dict()},f"{a.out}/model.pt")
def feats(rows): return rows.flatten(1).cpu().double().numpy()
with torch.no_grad():  # frozen ridge readout: fit on REAL boards of train worlds (frame the board just read)
    rr=np.random.default_rng(11); ji=np.r_[rr.choice(np.flatnonzero(w1<140),3500,replace=False),rr.choice(np.flatnonzero(w1>=140),500,replace=False)]  # lambda picked on UNSEEN train worlds
    Z=np.concatenate([feats(real_board(tr,xi1[ji[b:b+128]],t1[ji[b:b+128]])[0].rows[:,0]) for b in range(0,4000,128)])
    Y=tr["frames"][xi1[ji]].astype(np.float64).reshape(4000,-1); mu,sd=Z[:3500].mean(0),Z[:3500].std(0); sd=np.maximum(sd,1e-3+0.1*np.median(sd)); A=(Z[:3500]-mu)/sd; ym=Y[:3500].mean(0); K=A@A.T; best=None
    for lam in (1e-1,1e1,1e2,1e3,1e4,1e5,1e6):
        al=np.linalg.solve(K+lam*np.eye(3500),Y[:3500]-ym); e=((((Z[3500:]-mu)/sd)@A.T@al+ym-Y[3500:])**2).sum()
        print("ridge lam",lam,"val SSE",e,"valbase",((Y[3500:]-ym)**2).sum(),flush=True)
        if best is None or e<best[0]: best=(e,lam,al)
    lam,al=best[1],best[2]; readout=lambda R: ((feats(R)-mu)/sd@A.T@al+ym).reshape(-1,16,16,3)
    mean=tr["frames"][xi1].astype(np.float64).mean(0); res={"steps":done,"ridge_lambda":lam}
    xh1,ah1,wh1,_,th1=W.windows(he,1); hfr=he["frames"].astype(np.float64)
    # extra control (Neon+Astra): stateless per-action linear predictor x_{t+1} ~ M_a [x_t,1], ridge on train, rolled out k steps
    Xa=tr["frames"][xi1].astype(np.float64).reshape(len(xi1),-1); Ya=tr["frames"][xi1+1].astype(np.float64).reshape(len(xi1),-1); aa=tr["actions"][ai1]; Mact={}
    for q in range(17):
        sel=aa==q; Xq=np.c_[Xa[sel],np.ones(sel.sum())]; Mact[q]=np.linalg.solve(Xq.T@Xq+1.0*np.eye(769),Xq.T@Ya[sel])
    def act_roll(x0,acts):
        x=x0.reshape(len(x0),-1)
        for j in range(acts.shape[1]):
            nx=np.empty_like(x)
            for q in range(17):
                sel=acts[:,j]==q
                if sel.any(): nx[sel]=np.c_[x[sel],np.ones(sel.sum())]@Mact[q]
            x=nx
        return x.reshape(-1,16,16,3)
    ce=0.0; cm=0.0   # ceiling: readout on the REAL board after reading t+1
    for k in (1,3,5):
        xk,ak,_,_,_=W.windows(tr,k); xs,ys=tr["frames"][xk].astype(np.float64),tr["frames"][xk+k].astype(np.float64); dd=xs-mean
        bl=float(((ys-mean)*dd).sum()/(dd*dd).sum())
        xi,ai,wi,_,ti=W.windows(he,k); acts=he["actions"][ai[:,None]+np.arange(k)[None]]
        sh=acts.copy(); g=np.random.default_rng(43)
        for w in np.unique(wi): idx=np.flatnonzero(wi==w); sh[idx]=acts[idx[g.permutation(len(idx))]]
        P,Ps,Pr=[],[],[]
        for b in range(0,len(xi),128):
            i=xi[b:b+128]; st,enc=real_board(he,i,ti[b:b+128])
            P.append(readout(imagine(st,enc,torch.from_numpy(acts[b:b+128]).to(dev))[-1].next_rows[:,0]))
            Ps.append(readout(imagine(st,enc,torch.from_numpy(sh[b:b+128]).to(dev))[-1].next_rows[:,0]))
            if k==1: Pr.append(readout(real_board(he,i+1,ti[b:b+128]+1)[0].rows[:,0]))
        P,Ps=np.concatenate(P),np.concatenate(Ps); x0,yk=hfr[xi],hfr[xi+k]
        E=((P-yk)**2).sum(); cp=((x0-yk)**2).sum(); bs=((mean+bl*(x0-mean)-yk)**2).sum(); B=min(cp,bs)
        mv=((hfr[xi+1]-x0)**2).mean((1,2,3))>1e-6; pe=((P-yk)**2).sum((1,2,3)); pse=((Ps-yk)**2).sum((1,2,3))
        wr=[float(pse[mv&(wi==w)].sum()/pe[mv&(wi==w)].sum()) for w in np.unique(wi)]
        r={"E_over_B":E/B,"moved_E_over_B":pe[mv].sum()/min(((x0-yk)**2).sum((1,2,3))[mv].sum(),((mean+bl*(x0-mean)-yk)**2).sum((1,2,3))[mv].sum()),
           "B_is":"copy" if cp<=bs else "blend","shuffle_pooled":float(pse[mv].sum()/pe[mv].sum()),"shuffle_world_ratios":wr,
           "act_baseline_E_over_E":float(E/((act_roll(x0,acts)-yk)**2).sum()),"copy_ness":float(((P-x0)**2).sum()/((yk-x0)**2).sum())}
        if k==1:
            Pr=np.concatenate(Pr); print("DBG P",P.min(),P.max(),"Pr",Pr.min(),Pr.max(),"y",yk.min(),yk.max(),"B",B,"E",E,flush=True); r["ceiling_real_board_E_over_B"]=float(((Pr-yk)**2).sum()/B)
            a0=acts[:,0]; r["std_ratio_by_first_action"]=[float((P-x0)[a0==q].std()/((yk-x0)[a0==q].std()+1e-12)) for q in range(17) if (a0==q).sum()>=20]
        res[f"k{k}"]={kk:(float(v) if isinstance(v,(float,np.floating)) else v) for kk,v in r.items()}
        print(k,{kk:v for kk,v in res[f"k{k}"].items() if kk!="shuffle_world_ratios"},flush=True)
k1,k3,k5=res["k1"],res["k3"],res["k5"]; n1=sum(x>=1.25 for x in k1["shuffle_world_ratios"]); n5=sum(x>=1.10 for x in k5["shuffle_world_ratios"])
ok1=k1["E_over_B"]<=0.80; okS1=n1>=12; okstd=all(0.25<=x<=2 for x in k1["std_ratio_by_first_action"])
full=ok1 and k3["E_over_B"]<=0.90 and k5["E_over_B"]<=0.95 and okS1 and n5>=12 and okstd
res.update(worlds_k1_shuffle=n1,worlds_k5_shuffle=n5,verdict="PASS" if full else ("PARTIAL" if ok1 and okS1 and okstd else "FAIL"))
print("VERDICT",res["verdict"],"worlds",n1,n5); json.dump(res,open(f"{a.out}/score.json","w"),indent=1)
