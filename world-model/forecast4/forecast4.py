# STEP 6 (from step 5): frozen shared trunk, imagination-only layers: forecasting with the FROZEN exact ridge readout (marks pinned in STATUS.md before running)
import argparse, dataclasses, json, os, time, numpy as np, torch, torch.nn as nn, wm_fit as W, sizes
from imagine_head6 import damped_imagine, add_head
ap=argparse.ArgumentParser(); ap.add_argument("--device",default="mps"); ap.add_argument("--size",default="P7toy")
ap.add_argument("--init",default="run_recon_ridge/model.pt"); ap.add_argument("--steps",type=int,default=3000)
ap.add_argument("--lr",type=float,default=1e-5); ap.add_argument("--img-lr",type=float,default=1e-3); ap.add_argument("--max-minutes",type=float,default=40); ap.add_argument("--out",default="run_forecast4"); a=ap.parse_args()
os.makedirs(a.out,exist_ok=True); dev=a.device; SCALE=0.20385979115962982; W.rms_level=lambda t: t/SCALE  # step-2 try-2 constant
torch.manual_seed(42); m=W.WorldModel(sizes.make_cfg(a.size)).to(dev); del m.head
class Dec(nn.Module):
    def __init__(s,n):
        super().__init__(); s.bn=nn.BatchNorm1d(n,affine=False,eps=1e-3); s.lin=nn.Linear(n,768); s.mlp=nn.Sequential(nn.Linear(n,256),nn.GELU(),nn.Linear(256,768))
    def forward(s,z): z=s.bn(z.flatten(1)); return (s.lin(z)+s.mlp(z)).reshape(-1,16,16,3)
dec=Dec(m.R*m.D).to(dev); add_head(m.cell)  # step 6: imagination-only output layer (zeros)
if a.init:
    ck=torch.load(a.init,map_location=dev); m.load_state_dict(ck["m"],strict=False); "dec" in ck and dec.load_state_dict(ck["dec"])
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
xi1,ai1,w1,_,t1=W.windows(tr,1); m.eval()
def enc_act(act):  # step 4: context-blind imagination. The ONLY context is the action token (no frame-t photo at any rollout step)
    B=act.shape[0]; at=m.action_emb(act); at=(at/at.pow(2).mean(-1,keepdim=True).sqrt().clamp_min(1e-6))[:,None]
    C=1; z=torch.zeros(B,C,device=dev)
    ctx=W.Context(tokens=at,mask=torch.ones(B,C,dtype=torch.bool,device=dev),support=torch.ones(B,C,device=dev),
        source=torch.full((B,C),int(W.Source.SIGHT),dtype=torch.long,device=dev),age_s=z,epoch=torch.zeros(B,dtype=torch.long,device=dev),q_hash=torch.zeros(B,dtype=torch.long,device=dev))
    return m.cell.encode_context(ctx)
def imagine(st,x0,acts):  # x0 unused (kept for call compatibility); rows fed back
    out=[]
    for j in range(acts.shape[1]):
        o=damped_imagine(m.cell,st,enc_act(acts[:,j]),m.action_emb(acts[:,j])); st=dataclasses.replace(st,rows=o.next_rows); out.append(o)
    return out
def feats(rows): return rows.flatten(1).cpu().double().numpy()
def fit_readout():  # exact PCA-ridge readout on REAL train-world boards of the CURRENT weights
  global Wp,bp,lam,ROWSD,M0,SD
  mt=m.training; m.eval()
  with torch.no_grad():  # frozen ridge readout: fit on REAL boards of train worlds (frame the board just read)
      rr=np.random.default_rng(11); ji=np.r_[rr.choice(np.flatnonzero(w1<140),3500,replace=False),rr.choice(np.flatnonzero(w1>=140),500,replace=False)]  # lambda picked on UNSEEN train worlds
      Z=np.concatenate([feats(real_board(tr,xi1[ji[b:b+128]],t1[ji[b:b+128]])[0].rows[:,0]) for b in range(0,4000,128)])
      Y=tr["frames"][xi1[ji]].astype(np.float64).reshape(4000,-1); mu,sd=Z[:3500].mean(0),Z[:3500].std(0); sd=np.maximum(sd,1e-3+0.1*np.median(sd)); A=(Z[:3500]-mu)/sd; ym=Y[:3500].mean(0); best=None
      # step 4: NOISE-ROBUST ridge. lambda is not tuned for val accuracy; it is fixed so the readout equals a ridge fit on boards
      # jittered by NOISE x per-coordinate std (closed form: standardized ridge with lambda = n*NOISE^2). Val SSE is still reported.
      n=3500; lam=n*NOISE**2; al=np.linalg.solve(A@A.T+lam*np.eye(n),Y[:3500]-ym); Wnp=(A.T@al)/sd[:,None]
      e=(((Z[3500:]-mu)@Wnp+ym-Y[3500:])**2).sum(); best=(e,lam,Wnp)
      print("robust ridge lam",lam,"val SSE",e,"valbase",((Y[3500:]-ym)**2).sum(),flush=True)
      Wp=torch.tensor(Wnp,dtype=torch.float32,device=dev); bp=torch.tensor(ym-mu@Wnp,dtype=torch.float32,device=dev)
      ROWSD=float(Z[:3500].std()); SD=torch.tensor(sd,dtype=torch.float32,device=dev).view(1,1,m.R,m.D); M0=refmean(); m.train(mt)
NOISE=0.2
RF=np.random.default_rng(7).choice(np.flatnonzero(w1<140),64,replace=False)  # fixed reference set of REAL train-world boards
def refmean():  # step 4 fix: the board has a large shared offset (real-board spread ~0.02 vs RMS 1.36). Any weight update moves the
    with torch.no_grad(): return real_board(tr,xi1[RF],t1[RF])[0].rows[:,0].mean(0,keepdim=True)  # offset, which wrecked the readout.
fit_readout(); m.cell.imagine_scale=SD[0,0].detach().clone()  # step 6: real-board spread (train boards)
RT0=lambda R: (R.flatten(1)@Wp+bp).reshape(-1,16,16,3)   # the frozen exact readout
MC=None
RT=lambda R: RT0(R if MC is None else R-MC+M0)  # readout re-centred by the CURRENT real-board offset (real train boards only)
ga=None; TRW=np.flatnonzero(w1<140); rng=np.random.default_rng(42); t0=time.time(); done=0; params=list(m.parameters()); IMG=[m.action_emb.weight,m.cell.action_in.weight,m.cell.action_in.bias,m.cell.action_pos,*m.cell.imagine_out.parameters()]; ids={id(p) for p in IMG}
for p in params: p.requires_grad_(id(p) in ids)   # step 6: shared trunk + reader FROZEN
params=IMG; opt=torch.optim.Adam(IMG,lr=a.img_lr); sch=torch.optim.lr_scheduler.LambdaLR(opt,lambda q: min(1.0,(q+1)/100)); m.train()
for s in range(a.steps):
    MC=refmean(); j=TRW[rng.integers(0,len(TRW),64)]; i=xi1[j]; st,_=real_board(tr,i,t1[j]); xt,xn=F(tr,i),F(tr,i+1)
    with torch.no_grad(): nxt=real_board(tr,i+1,t1[j]+1)[0].rows
    act=torch.from_numpy(tr["actions"][ai1[j]]).to(dev); st_n=dataclasses.replace(st,rows=st.rows.detach()+NOISE*st.rows.detach().std(0,keepdim=True)*torch.randn_like(st.rows)); o=imagine(st_n,xt,act[:,None])[0]  # Neon bughunt: start board detached
    l_img=((RT(o.next_rows[:,0])-xn)**2).mean(); l_rec=((RT(st.rows[:,0])-xt)**2).mean(); l_row=(((o.next_rows-nxt)/SD)**2).mean()
    w_img=min(1.0,max(0.0,(s-100)/150)); loss=w_img*l_img+10*l_rec+0.1*l_row+0.01*o.aux_loss; opt.zero_grad(); loss.backward()
    if s==0: ga=float(m.action_emb.weight.grad.norm()); print("action_emb grad norm at step 0",ga,flush=True)
    torch.nn.utils.clip_grad_norm_(params,1.0); opt.step(); sch.step(); done=s+1
    if s<3 or (s+1)%250==0: print(f"step {s} img/copy {(l_img/((RT(st.rows[:,0])-xn)**2).mean()).item():.3f} img {l_img.item():.5f} rec {l_rec.item():.5f} row {l_row.item():.5f} head {m.cell.imagine_out[2].weight.abs().mean().item():.5f} t {time.time()-t0:.0f}s",flush=True)
    if time.time()-t0>a.max_minutes*60: print("cap hit at",done); break
m.eval(); MC=refmean(); print('PRIMARY score readout = the training readout (fit on REAL boards at start, re-centred by the final real-board mean)',flush=True); m.eval(); torch.save({"m":m.state_dict()},f"{a.out}/model.pt")
readout=lambda R: RT(R).cpu().double().numpy()
res0={"action_emb_grad_step0":ga}
with torch.no_grad():
    mean=tr["frames"][xi1].astype(np.float64).mean(0); res={"steps":done,"ridge_lambda":lam,**res0}
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
            P.append(readout(imagine(st,F(he,i),torch.from_numpy(acts[b:b+128]).to(dev))[-1].next_rows[:,0]))
            Ps.append(readout(imagine(st,F(he,i),torch.from_numpy(sh[b:b+128]).to(dev))[-1].next_rows[:,0]))
            if k==1: Pr.append(readout(real_board(he,i+1,ti[b:b+128]+1)[0].rows[:,0]))
        P,Ps=np.concatenate(P),np.concatenate(Ps); x0,yk=hfr[xi],hfr[xi+k]
        E=((P-yk)**2).sum(); cp=((x0-yk)**2).sum(); bs=((mean+bl*(x0-mean)-yk)**2).sum(); B=min(cp,bs)
        mv=((hfr[xi+1]-x0)**2).mean((1,2,3))>1e-6; pe=((P-yk)**2).sum((1,2,3)); pse=((Ps-yk)**2).sum((1,2,3))
        wr=[float(pse[mv&(wi==w)].sum()/max(pe[mv&(wi==w)].sum(),1e-12)) for w in np.unique(wi)]
        r={"E_over_B":E/B,"moved_E_over_B":pe[mv].sum()/min(((x0-yk)**2).sum((1,2,3))[mv].sum(),((mean+bl*(x0-mean)-yk)**2).sum((1,2,3))[mv].sum()),
           "B_is":"copy" if cp<=bs else "blend","shuffle_pooled":float(pse[mv].sum()/pe[mv].sum()),"shuffle_world_ratios":wr,
           "act_baseline_E_over_E":float(E/((act_roll(x0,acts)-yk)**2).sum()),"copy_ness":float(((P-x0)**2).sum()/((yk-x0)**2).sum())}
        if k==1:
            Pr=np.concatenate(Pr); r["ceiling_real_board_E_over_B"]=float(((Pr-yk)**2).sum()/B)
            a0=acts[:,0]; r["pcs90_pred"]=int(W.pcs90((P-x0).reshape(len(P),-1))); r["pcs90_real"]=int(W.pcs90((yk-x0).reshape(len(P),-1))); r["std_ratio_by_first_action"]=[(1.0 if (yk-x0)[a0==q].std()<1e-12 and (P-x0)[a0==q].std()<1e-12 else float((P-x0)[a0==q].std()/((yk-x0)[a0==q].std()+1e-12))) for q in range(17) if (a0==q).sum()>=20]
        res[f"k{k}"]={kk:(float(v) if isinstance(v,(float,np.floating)) else v) for kk,v in r.items()}
        print(k,{kk:v for kk,v in res[f"k{k}"].items() if kk!="shuffle_world_ratios"},flush=True)
k1,k3,k5=res["k1"],res["k3"],res["k5"]; n1=sum(x>=1.25 for x in k1["shuffle_world_ratios"]); n5=sum(x>=1.10 for x in k5["shuffle_world_ratios"]); nboth=sum(x>=1.25 and y>=1.10 for x,y in zip(k1["shuffle_world_ratios"],k5["shuffle_world_ratios"]))
ok1=k1["E_over_B"]<=0.80; okS1=n1>=12; okstd=all(0.25<=x<=2 for x in k1["std_ratio_by_first_action"])
okpc=k1["pcs90_pred"]>=0.5*k1["pcs90_real"]; ceil=k1["ceiling_real_board_E_over_B"]
full=ok1 and k3["E_over_B"]<=0.90 and k5["E_over_B"]<=0.95 and okS1 and nboth>=12 and okstd and okpc and ceil<=0.70
res.update(worlds_k1_shuffle=n1,worlds_k5_shuffle=n5,worlds_both=nboth,pcs_ok=bool(okpc),verdict="FAIL" if ceil>0.95 else ("PASS" if full else ("PARTIAL" if ok1 and okS1 and okstd and okpc and ceil<=0.70 else "FAIL")))
print("VERDICT",res["verdict"],"worlds",n1,n5); json.dump(res,open(f"{a.out}/score.json","w"),indent=1)
