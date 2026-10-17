# False-alarm calibration for the ratio gate under H0 (restore complete => C, R1..RK exchangeable).
# Each trajectory's loss deviation e_i(t), t=1..50, is an AR(1) Gaussian process with lag-1 corr rho,
# times a growth envelope g(t)=exp(lam*t) (chaotic amplification). rho=1 is the worst case (one draw per run).
import numpy as np
rng=np.random.default_rng(0)
T=50; N=200000
def sim(K,rho,lam):
    M=K+1
    e=np.empty((N,M,T)); x=rng.standard_normal((N,M))
    for t in range(T):
        if t: x=rho*x+np.sqrt(1-rho**2)*rng.standard_normal((N,M))
        e[:,:,t]=x*np.exp(lam*t)
    C=e[:,0]; R=e[:,1:]
    D=np.mean(np.abs(R-C[:,None,:]),axis=2).mean(1)          # mean over resumes of mean_t|Ri-C|
    pairs=[(i,j) for i in range(K) for j in range(i+1,K)]
    Nn=np.mean([np.mean(np.abs(R[:,i]-R[:,j]),axis=1) for i,j in pairs],axis=0)
    return D/Nn
for K in (2,3,4):
  for rho,lam in ((1.0,0),(0.95,0.05),(0.8,0.05),(0.5,0)):
    S=sim(K,rho,lam)
    print(f"K={K} rho={rho} lam={lam}: median={np.median(S):.2f} q95={np.quantile(S,.95):.2f} q99={np.quantile(S,.99):.2f} "
          f"P>1.5={np.mean(S>1.5):.3f} P>2={np.mean(S>2):.4f} P>3={np.mean(S>3):.4f}")
