"""NEW order-preserving D256 core input boundary. Old core/seals unchanged.
Fixed numeric position/role codes, no text/parser/labels or task rules. Same
representation for loop, unshared plain and embedding control. Mechanics only.
"""
from __future__ import annotations
from pathlib import Path
import torch
from torch import nn
from sol_spatial_attention_core import AttentionReasoner, load_bundle
from sol_spatial_poc_plain import PlainAttentionReasoner

CONTRACT='sol-ordered-notebook-v2'
QUERY_CAP=49
NOTEBOOK_CAP=512
MAX_POSITION=4095


def _register(module, scale=1.0):
    if scale!=1.0:raise ValueError('v2 fixes position/role scale at1; new seal for changes')
    module.register_buffer('position_frequencies',10000.0**(-torch.arange(0,256,2,dtype=torch.float32)/256))
    roles=torch.zeros(2,256,dtype=torch.float32);roles[0,-2]=1;roles[1,-1]=1
    module.register_buffer('boundary_roles',roles)
    module.order_contract=CONTRACT
    module.position_scale=scale


def _prefix_count(mask,b,n,device,name):
    if mask is None:return n
    if mask.dtype!=torch.bool or mask.shape!=(b,n) or mask.device!=device:raise ValueError(name+' mask dtype/shape/device')
    counts=mask.sum(1)
    if not bool((counts==counts[0]).all()):raise ValueError('ragged batch: physical perrow slicing or group same lengths before core')
    count=int(counts[0])
    want=torch.arange(n,device=device)[None]<count
    if not bool((mask==want).all()):raise ValueError('only prefix padding admitted; arbitrary masked facts must be physically removed with original positions')
    return count


def _positions(pos,b,n,device,name):
    if pos is None:return torch.arange(n,device=device,dtype=torch.long)[None].expand(b,-1).clone()
    if pos.dtype!=torch.long or pos.shape!=(b,n) or pos.device!=device:raise ValueError(name+' absolute positions dtype/shape/device')
    if n and (int(pos.min())<0 or int(pos.max())>MAX_POSITION):raise ValueError('absolute position cap4095')
    if n>1 and not bool((pos[:,1:]>pos[:,:-1]).all()):raise ValueError('original absolute indices must be strictly increasing')
    return pos.clone()


def position_codes(module, positions, role):
    """Public same-information embedding-control entrypoint, no learned solver."""
    if role not in (0,1) or positions.dtype!=torch.long or positions.ndim!=2:raise ValueError('role0 query/1 notebook and [B,N] integer indices required')
    if positions.numel() and (int(positions.min())<0 or int(positions.max())>MAX_POSITION):raise ValueError('absolute position cap4095')
    angles=positions.float()[...,None]*module.position_frequencies
    code=torch.stack((angles.sin(),angles.cos()),-1).flatten(-2)
    return module.position_scale*(code+module.boundary_roles[role])


def ordered_begin(module,latent,notebook=None,*,query_mask=None,notebook_mask=None,query_positions=None,notebook_positions=None):
    if latent.ndim!=4 or latent.shape[1]!=1 or latent.shape[-1]!=256:raise ValueError('human ordered core [B,1,N,256] query required')
    b,_,n,d=latent.shape
    if n>QUERY_CAP:raise ValueError('query physical cap49 includesEOS')
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


class OrderedAttentionReasoner(AttentionReasoner):
    def __init__(self,source,experts=8,active=2):
        if isinstance(source,AttentionReasoner):
            # Reconstruct skeleton then strict-copy exact qualified/closed source.
            from sol_spatial_attention_core import N
            super().__init__(N.Net('loop'),experts=source.experts_count,active=source.active_count)
            self.load_state_dict(source.state_dict(),strict=True)
        else:super().__init__(source,experts=experts,active=active)
        _register(self)
    def begin_latent(self,latent,notebook=None,**metadata):return ordered_begin(self,latent,notebook,**metadata)
    def constructor(self):return {'family':'ordered-loop-D256-v2','experts':self.experts_count,'active':self.active_count,'order_contract':CONTRACT,'query_cap':QUERY_CAP,'notebook_cap':NOTEBOOK_CAP,'max_absolute_position':MAX_POSITION,'scale':1.0}


class OrderedPlainAttentionReasoner(PlainAttentionReasoner):
    def __init__(self,source):
        if not isinstance(source,AttentionReasoner):source=AttentionReasoner(source)
        super().__init__(source,rounds=4,sparse=True);_register(self)
    def begin_latent(self,latent,notebook=None,**metadata):return ordered_begin(self,latent,notebook,**metadata)
    def constructor(self):return {'family':'ordered-plain-D256-v2','experts':self.experts_count,'active':self.active_count,'rounds':4,'order_contract':CONTRACT,'query_cap':QUERY_CAP,'notebook_cap':NOTEBOOK_CAP,'max_absolute_position':MAX_POSITION,'scale':1.0}


def make_ordered_source(source,variant='loop'):
    if variant=='loop':return OrderedAttentionReasoner(source)
    if variant=='sparse_unrolled4':return OrderedPlainAttentionReasoner(source)
    raise ValueError('v2 only loop or sparse_unrolled4')


def ordered_bundle_payload(model,metadata):
    if not isinstance(model,(OrderedAttentionReasoner,OrderedPlainAttentionReasoner)):raise TypeError('ordered model required')
    return {'constructor':model.constructor(),'state_dict':{k:v.detach().cpu().clone() for k,v in model.state_dict().items()},'metadata':dict(metadata)}


def load_ordered_bundle(bundle,device='cpu'):
    raw=torch.load(bundle if hasattr(bundle,'read') else Path(bundle),map_location='cpu',weights_only=True);c=raw['constructor']
    from sol_spatial_attention_core import N
    source=AttentionReasoner(N.Net('loop'),experts=c['experts'],active=c['active'])
    if c['family']=='ordered-loop-D256-v2':model=OrderedAttentionReasoner(source)
    elif c['family']=='ordered-plain-D256-v2':model=OrderedPlainAttentionReasoner(source)
    else:raise ValueError('unknown ordered constructor')
    if model.constructor()!=c:raise ValueError('exact ordered constructor/caps/scale required')
    model.load_state_dict(raw['state_dict'],strict=True)
    return model.to(device),raw['metadata']
