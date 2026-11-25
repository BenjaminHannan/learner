import os, sys, numpy as np, torch, wm_fit as W
T=int(os.environ.get('TICKS','2')); LR=float(os.environ.get('LR','3e-4'))
def rd(self,st,enc):
    for _ in range(T): st=self.cell.run_tick(st,enc,noise=False).state
    return st
W.WorldModel.read=rd if os.environ.get('PIN')!='1' else W.WorldModel.read
W.PIN_FRAME=os.environ.get('PIN')=='1'; W.DEC_NORM=os.environ.get('NORM')=='1'
torch.manual_seed(42); tr=W.load_split("data/train.npz")
DEV=os.environ.get('DEV','cpu'); SZ=os.environ.get('SIZE','debug')
if SZ=='debug':
    from premonition_core_v2.board_swarm import BoardSwarmConfig; cfg=BoardSwarmConfig.debug_tiny()
else:
    import sizes; cfg=sizes.make_cfg(SZ)
m=W.WorldModel(cfg).to(DEV)
xi,ai,_,_,_=W.windows(tr,1); F=tr["frames"]; rng=np.random.default_rng(0)
opt=torch.optim.Adam(m.parameters(),lr=LR)
for s in range(int(os.environ.get('STEPS','401'))):
    i=rng.integers(0,len(xi),64); xt=torch.tensor(F[xi[i]],dtype=torch.float32).to(DEV); xn=torch.tensor(F[xi[i]+1],dtype=torch.float32).to(DEV)
    st=m.read(m.cell.init_state(64,1,device=DEV,dtype=torch.float32),m.encode(xt)); st=m.read(st,m.encode(xn))
    d=xn-xt; pr=m.decode(st.rows); l=((pr-d)**2).mean(); opt.zero_grad(); l.backward()
    if s%int(os.environ.get('EV','200'))==0:
        r=st.rows; print(s,"l_real %.6f zero %.6f"%(l.item(),(d**2).mean().item()),"rowstd_over_batch %.4f"%r.std(0).mean().item(),
          "rowabs %.3f"%r.abs().mean().item(),"gW %.2e"%m.head[-1].weight.grad.norm().item(), "enc_g %.2e"%sum(p.grad.norm().item() for n,p in m.named_parameters() if p.grad is not None and "head" not in n and "cell" not in n), flush=True)
    opt.step()
