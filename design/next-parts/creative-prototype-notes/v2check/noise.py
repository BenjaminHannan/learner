import numpy as np
rng=np.random.default_rng(1)
R=400000
seedsd=5.0
# per-seed pass@8 puzzle noise at level 50%, beta1 factor ~0.8 of the bound, n=256
puz=np.sqrt(0.8*0.25/256)*100
s=np.sqrt(seedsd**2+puz**2)
print('per-seed sd %.2f'%s)
x2=rng.normal(0,s,(R,2)); x3=rng.normal(0,s,(R,3))
r2=np.abs(x2[:,0]-x2[:,1]); r3=x3.max(1)-x3.min(1)
print('P(|diff of 2|>16) %.3f   P(range of 3 >16) %.3f   95th pct: 2 seeds %.1f, 3 seeds %.1f'%((r2>16).mean(),(r3>16).mean(),np.quantile(r2,.95),np.quantile(r3,.95)))
# proved-wrong rule: mean W <= mean R, 3 vs 3 seeds, unpaired (conservative)
for g in (0,3,5,10,15):
    W=rng.normal(g,s,(R,3)).mean(1); Rm=rng.normal(0,s,(R,3)).mean(1)
    print('true gain %2d: P(meanW<=meanR) = %.3f ; P(meanW-meanR in (0,10)) = %.3f'%(g,(W<=Rm).mean(),((W-Rm>0)&(W-Rm<10)).mean()))
# G1: every one of 3 W seeds >= N - 2 on pass@32 when the true coverage is unchanged (N fixed, seed sd 5)
W=rng.normal(0,s,(R,3))
print('G1 false-fail when true coverage unchanged: %.3f'%(1-(W>=-2).all(1).mean()))
