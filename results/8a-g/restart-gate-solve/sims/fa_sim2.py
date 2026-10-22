# Calibrated form: one-time calibration with K resumes from one checkpoint -> m=K(K-1)/2 pairwise means N_ij.
# Gate for a run: D = mean_t|R-C| (one fresh pair involving the logged run) <= L, L = c * max_ij N_ij  (or c*mean).
# Under H0, D is exchangeable with any N_ij. Report false-alarm P(D > L).
import numpy as np
rng=np.random.default_rng(1); T=50; N=200000
def traj(M,rho,lam):
    e=np.empty((N,M,T)); x=rng.standard_normal((N,M))
    for t in range(T):
        if t: x=rho*x+np.sqrt(1-rho**2)*rng.standard_normal((N,M))
        e[:,:,t]=x*np.exp(lam*t)
    return e
for K in (2,3,4,6):
  for rho,lam in ((1.0,0),(0.95,0.05),(0.8,0.05)):
    e=traj(K+2,rho,lam); C=e[:,0]; R=e[:,1]; cal=e[:,2:]
    D=np.mean(np.abs(R-C),1)
    P=np.array([np.mean(np.abs(cal[:,i]-cal[:,j]),1) for i in range(K) for j in range(i+1,K)])
    mx=P.max(0); mn=P.mean(0)
    out=" ".join(f"P(D>{c}max)={np.mean(D>c*mx):.4f}" for c in (1.0,1.5,2.0))
    out+=" "+" ".join(f"P(D>{c}mean)={np.mean(D>c*mn):.4f}" for c in (2.0,3.0))
    print(f"K={K} m={len(P)} rho={rho}: {out}")
