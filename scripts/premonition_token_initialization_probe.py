"""Disjoint training-only diagnostic of width-scaled linear initialization.

The .02 linear-weight scale used by the initial recipe is small at width 48.
Rescale the SAME initial normal draws to std=1/sqrt(3*fan_in), the variance of
PyTorch's default uniform Linear initialization. Everything else, including the
ordered training feedback, matches the earlier diagnostic. No holdout evaluation.
"""
import json
import math
import random
import time

import premonition_token_evidence as E


def rescale(model):
    with E.torch.no_grad():
        for module in model.modules():
            if isinstance(module,E.T.nn.Linear):
                module.weight.mul_(1/(math.sqrt(3*module.in_features)*.02))


if __name__=="__main__":
    E.torch.set_num_threads(1)
    E.torch.manual_seed(774111)
    m=E.T.TokenMemoryReasoner()
    rescale(m)
    optimizer=E.T.optimizer_for(m)
    rng=random.Random(774112)
    start=time.monotonic()
    for step in range(1000):
        x,y=E.training_batch(rng)
        row=E.training_step(m,optimizer,x,y,step)
        if (step+1)%100==0 or step==0:
            print(json.dumps({"step":step+1,"seconds":time.monotonic()-start,**row}),flush=True)
