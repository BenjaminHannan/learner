# Free gate G0 (no training): with frame patches pinned into 16 fast rows, does the board hold the frame?
import os, dataclasses, numpy as np, torch, wm_fit as W, sizes
torch.manual_seed(42); SZ=os.environ.get("SIZE","S"); T=int(os.environ.get("TICKS","2")); PIN=os.environ.get("PIN","1")=="1"
cfg=sizes.make_cfg(SZ); m=W.WorldModel(cfg); ns=m.cell.ns; R=m.R
torch.nn.init.orthogonal_(m.reader.weight)
d=W.load_split("data/train.npz"); xi,_,_,_,_=W.windows(d,1)
rng=np.random.default_rng(0); idx=rng.choice(len(xi),512,replace=False); X=torch.tensor(d["frames"][xi[idx]],dtype=torch.float32)
def patches(x):  # [B,16,48] exactly as the reader sees them
    return x.reshape(-1,4,4,4,4,3).permute(0,1,3,2,4,5).reshape(-1,16,48)
def run(x):
    enc=m.encode(x); st=m.cell.init_state(x.shape[0],1,device="cpu",dtype=torch.float32)
    if PIN:
        p=m.reader(patches(x)); p=p/p.pow(2).mean(-1,keepdim=True).sqrt()*st.rows.abs().mean().clamp_min(0.5)
        rows=st.rows.clone(); rows[:,0,ns:ns+16]=p; pin=st.row_pin.clone(); pin[:,0,ns:ns+16]=True
        st=dataclasses.replace(st,rows=rows,row_pin=pin)
    for _ in range(T): st=m.cell.run_tick(st,enc,noise=False).state
    return st.rows[:,0]
m.reader.weight.requires_grad_(True); rows=run(X)
loss=(rows[:,:, :].mean()**2+rows.pow(2).mean()); g=torch.autograd.grad(rows.sum(),m.reader.weight)[0]
Z=rows.detach().numpy(); Y=X.reshape(512,-1).numpy()
def ridge(Zs):
    Zs=Zs.reshape(512,-1); tr,va=slice(0,400),slice(400,512); mu=Zs[tr].mean(0); ym=Y[tr].mean(0)
    A,B=Zs[tr]-mu,Zs[va]-mu; best=-9
    for lam in (1e-4,1e-2,1):
        a=np.linalg.solve(A@A.T+lam*np.eye(400),Y[tr]-ym); pred=B@A.T@a+ym
        best=max(best,1-((Y[va]-pred)**2).sum()/((Y[va]-Y[va].mean(0))**2).sum())
    return float(best)
free=[i for i in range(R) if not (PIN and ns<=i<ns+16)]
snr=float(Z.std(0).mean()/np.sqrt((Z**2).mean(-1)).mean())
print(dict(size=SZ,ticks=T,pin=PIN,R=R,ns=ns,R2_all=ridge(Z),R2_unpinned=ridge(Z[:,free]),snr=snr,reader_grad_rms=float(g.pow(2).mean().sqrt())))
