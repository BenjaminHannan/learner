"""Four-segment differentiable training path, final HUMAN loss owned by driver.
Same mean8 sparse balancing auxiliary in ordered loop/plain. No optimization,
text, checker, routing or learned-stop qualification in this helper.
"""
from __future__ import annotations
import torch
from sol_spatial_poc_ordered_v2 import OrderedAttentionReasoner,OrderedPlainAttentionReasoner

def fixed4_training(core,query,notebook=None,**metadata):
    if not isinstance(core,(OrderedAttentionReasoner,OrderedPlainAttentionReasoner)):
        raise TypeError('exact ordered native core required')
    state=core.begin_latent(query,notebook,**metadata);terms=[]
    for r in range(4):
        state=core.advance_latent(state)
        blocks=core.blocks if isinstance(core,OrderedAttentionReasoner) else core.blocks[2*r:2*r+2]
        terms.extend(block.mlp.aux for block in blocks)
    h,q=core.read_latent(state)
    if len(terms)!=8:raise RuntimeError('mean exactly8 physically visited sparse block auxiliary graphs')
    return h,q,torch.stack(terms).mean()
