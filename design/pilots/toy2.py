import numpy as np
from toy_consolidation import run
for cond, ratio, steps in [('new_only',0,50),('new_only',0,100),('replay_exact',0.25,300),('self_distill',0.1,300),('self_distill',0.25,300)]:
    rs=[run(s,cond,ratio,steps) for s in range(3)]
    m=lambda k: np.mean([x[k] for x in rs])
    print(f"{cond:13s} old_frac={ratio:.2f} steps={steps} new_after={m('new'):.3f} old_after={m('old'):.3f} worst_old_during={m('min_old'):.3f}")
