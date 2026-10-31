"""G2: English-only ordered_begin with a 64-token query guard (incl. EOS).

Source-exact copy of sol_spatial_poc_ordered_v2.ordered_begin (lines 55-79).
The ONLY computational difference is the physical query guard (49 -> 64); it
reuses the same AttentionReasoner.begin_latent, position_codes, mask/position
validators and bookkeeping imported from the unchanged module. The module's
global QUERY_CAP (49), the class, core.constructor() (query_cap 49) and every
parameter/buffer stay unchanged. bind_english_cap64() binds the copy to one core
instance, so the unchanged fixed4_training reaches it through core.begin_latent.
"""
import types

import torch
import sol_spatial_poc_ordered_v2 as _ordered
from sol_spatial_poc_ordered_v2 import (AttentionReasoner, CONTRACT, NOTEBOOK_CAP,
    OrderedAttentionReasoner, _positions, _prefix_count, position_codes)

ENGLISH_QUERY_CAP = 64
SOURCE_FUNCTION = 'ordered_begin'


def english_ordered_begin(module,latent,notebook=None,*,query_mask=None,notebook_mask=None,query_positions=None,notebook_positions=None):
    if latent.ndim!=4 or latent.shape[1]!=1 or latent.shape[-1]!=256:raise ValueError('human ordered core [B,1,N,256] query required')
    b,_,n,d=latent.shape
    if n>ENGLISH_QUERY_CAP:raise ValueError('English query physical cap64 includesEOS')
    qn=_prefix_count(query_mask,b,n,latent.device,'query')
    if qn<1:raise ValueError('nonempty query required')
    qpos=_positions(query_positions,b,n,latent.device,'query')[:,:qn]
    query=latent[:,:,:qn]
    if notebook is None:
        if notebook_mask is not None or notebook_positions is not None:raise ValueError('notebook metadata without notebook')
        mn=0;mpos=torch.empty(b,0,device=latent.device,dtype=torch.long);memo=None
    else:
        if notebook.ndim!=3 or notebook.shape[0]!=b or notebook.shape[-1]!=d or notebook.device!=latent.device or notebook.dtype!=latent.dtype:raise ValueError('notebook [B,M,256] same dtype/device required')
        m=notebook.shape[1]
        if m>NOTEBOOK_CAP:raise ValueError('notebook physical cap512, future chunks need fresh protocol')
        mn=_prefix_count(notebook_mask,b,m,latent.device,'notebook')
        mpos=_positions(notebook_positions,b,m,latent.device,'notebook')[:,:mn];memo=notebook[:,:mn]
    state=AttentionReasoner.begin_latent(module,query,memo)
    codes=position_codes(module,qpos,0)
    if mn:codes=torch.cat((codes,position_codes(module,mpos,1)),1)
    # Inputs and positions remain unchanged; gradients still reach thin reader.
    state['e']=state['e']+codes.to(state['e'].dtype)
    state.update(order_contract=CONTRACT,query_absolute_positions=qpos,notebook_absolute_positions=mpos,
                 input_valid=torch.ones(b,qn+mn,device=latent.device,dtype=torch.bool))
    return state


def _english_begin_latent(self,latent,notebook=None,**metadata):return english_ordered_begin(self,latent,notebook,**metadata)


def structural_snapshot(core):
    return {'constructor': core.constructor(),
            'parameters': [(n, tuple(p.shape), str(p.dtype)) for n, p in core.named_parameters()],
            'buffers': [(n, tuple(b.shape), str(b.dtype)) for n, b in core.named_buffers()],
            'state_dict_keys': list(core.state_dict().keys())}


def bind_english_cap64(core):
    """Bind the English guard to this ONE core instance; no params/buffers/globals change."""
    if not isinstance(core, OrderedAttentionReasoner):
        raise TypeError('exact ordered native core required')
    if 'begin_latent' in vars(core):
        raise ValueError('core already carries an instance begin_latent binding')
    if type(core).begin_latent is not OrderedAttentionReasoner.begin_latent:
        raise ValueError('core class overrides ordered begin_latent; English binding not admitted')
    if _ordered.QUERY_CAP != 49 or core.constructor().get('query_cap') != 49:
        raise ValueError('numeric QUERY_CAP 49 and constructor query_cap 49 must stay unchanged')
    before = structural_snapshot(core)
    core.begin_latent = types.MethodType(_english_begin_latent, core)
    after = structural_snapshot(core)
    if before != after or _ordered.QUERY_CAP != 49:
        raise RuntimeError('English binding changed parameters, buffers, constructor or global cap')
    return {'english_query_cap_with_EOS': ENGLISH_QUERY_CAP, 'global_QUERY_CAP': _ordered.QUERY_CAP,
            'constructor_query_cap': core.constructor()['query_cap'], 'parameters_added': 0,
            'buffers_added': 0, 'instance_binding': True}


def is_bound(core):
    bound = vars(core).get('begin_latent')
    return isinstance(bound, types.MethodType) and bound.__func__ is _english_begin_latent and bound.__self__ is core


def require_bound(core):
    if not is_bound(core):
        raise RuntimeError('English cap64 begin_latent binding required on this core')
