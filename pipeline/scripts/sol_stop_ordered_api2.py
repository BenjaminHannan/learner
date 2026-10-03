"""Native order-aware fixed4 final-state boundary. Engineering, not qualification.

No training/data/English-model imports. Calls native begin/advance/read so the
new parent's positional input encoding is used exactly once. Decoder gets only
canonical detached FinalLatent. No learned-stop or sleep acceptance.
"""
from pathlib import Path
import inspect,sys,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from torch import nn
from scripts.sol_stop_adapter import FinalLatent,StopRun,ExecutionAudit,WorkMeter,module_hash

ROOT=Path(__file__).resolve().parents[1]
ORDER_CONTRACT='sol-ordered-notebook-v2'
SOURCE=ROOT/'scripts/sol_spatial_poc_ordered_v2.py'
SOURCE_SHA='5344e622855c875312f77a88095d287a5709e17dbaca23c90bdd8733b0a38291'


def ordered_attention_math():
    """Use around native TRAIN fixed4 helper too; reasoner only, never LM.
    Explicit shared backend avoids grad/inference SDPA kernel divergence.
    """
    from torch.nn.attention import sdpa_kernel,SDPBackend
    return sdpa_kernel(SDPBackend.MATH)


def _sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare_ordered_notebook(state):
    """Gather valid vectors AND their original indices; never renumber holes.
    Ragged lengths require per-row execution, not unmasked padded facts.
    """
    if type(state) is not dict or set(state) not in ({'translated','mask'},{'translated','mask','positions'}):
        raise ValueError('notebook translated+mask+optional positions only')
    memo,mask=state['translated'],state['mask']
    if (not isinstance(memo,torch.Tensor) or memo.ndim!=3 or memo.shape[-1]!=256 or
            not memo.is_floating_point() or len(memo)==0 or not bool(torch.isfinite(memo).all()) or
            not isinstance(mask,torch.Tensor) or mask.dtype!=torch.bool or mask.shape!=memo.shape[:2] or mask.device!=memo.device):
        raise ValueError('finite Notebook[B,M,256], mask[B,M] bool required')
    lengths=mask.sum(1)
    if not bool((lengths==lengths[0]).all()):raise ValueError('ragged notebook: execute per row')
    pos=state.get('positions')
    if pos is None:pos=torch.arange(memo.shape[1],device=memo.device,dtype=torch.long)[None].expand(len(memo),-1)
    if not isinstance(pos,torch.Tensor) or pos.dtype!=torch.long or pos.shape!=mask.shape or pos.device!=memo.device:
        raise ValueError('original absolute positions[B,M] int64 required')
    selected=torch.stack([row[valid] for row,valid in zip(memo,mask)]).detach().clone()
    positions=torch.stack([row[valid] for row,valid in zip(pos,mask)]).clone()
    if selected.shape[1]>512 or (positions.numel() and (int(positions.min())<0 or int(positions.max())>4095)):
        raise ValueError('ordered notebook caps exceeded')
    if positions.shape[1]>1 and not bool((positions[:,1:]>positions[:,:-1]).all()):raise ValueError('positions must retain original increasing order')
    return {'notebook_latents':selected,'notebook_mask':torch.ones(selected.shape[:2],device=selected.device,dtype=torch.bool),
            'notebook_positions':positions}


class OrderedFixed4Executor(nn.Module):
    accepted_stop_ready=False
    stage_proof_status='NOT SHOWN'
    policy='fixed4-engineering-unqualified-learned-stop'

    def __init__(self,core):
        super().__init__()
        if _sha(SOURCE)!=SOURCE_SHA or Path(inspect.getfile(type(core))).resolve()!=SOURCE.resolve():
            raise ValueError('exact reviewed ordered source required; new source needs new owner version')
        c=core.constructor()
        if (c.get('family') not in ('ordered-loop-D256-v2','ordered-plain-D256-v2') or
                core.order_contract!=ORDER_CONTRACT or c.get('order_contract')!=ORDER_CONTRACT or
                c.get('query_cap')!=49 or c.get('notebook_cap')!=512 or c.get('max_absolute_position')!=4095 or c.get('scale')!=1.0):
            raise ValueError('unsupported ordered input contract')
        if c['family']=='ordered-plain-D256-v2' and (core.rounds!=4 or len(core.blocks)!=8 or len(core.state_norms)!=4):
            raise ValueError('plain must have exactly four unshared two-block segments')
        if any(p.is_floating_point() and p.dtype!=torch.float32 for p in core.parameters()):raise ValueError('reviewed ordered core requires FP32')
        frequency=10000.0**(-torch.arange(0,256,2,dtype=torch.float32)/256)
        roles=torch.zeros(2,256,dtype=torch.float32);roles[0,-2]=1;roles[1,-1]=1
        if (not torch.equal(core.position_frequencies.detach().cpu(),frequency) or
                not torch.equal(core.boundary_roles.detach().cpu(),roles) or core.position_scale!=1.0):
            raise ValueError('checkpoint position/role buffers differ from fixed source contract')
        self.core=core.eval().requires_grad_(False)
        self.core_state_sha256=module_hash(core)

    def train(self,mode=True):
        super().train(False);return self

    @torch.no_grad()
    def execute_embeddings(self,embeddings,answer_mask,token_shape,*,notebook_latents=None,notebook_mask=None,
                           query_positions=None,notebook_positions=None,query_mask=None,
                           policy='fixed',cap=4,compact=True):
        if (policy!='fixed' or type(cap)!=int or cap!=4 or type(compact)!=bool or
                embeddings.ndim!=3 or embeddings.shape[-1]!=256 or embeddings.dtype!=torch.float32 or
                len(embeddings)==0 or not bool(torch.isfinite(embeddings).all()) or
                tuple(token_shape)!=(1,embeddings.shape[1]) or answer_mask.dtype!=torch.bool or
                answer_mask.shape!=embeddings.shape[:2] or answer_mask.device!=embeddings.device):
            raise ValueError('ordered fixed4 only; valid [B,N,256] query and shape(1,N) required')
        if notebook_latents is not None and not bool(torch.isfinite(notebook_latents).all()):raise ValueError('nonfinite notebook')
        q=embeddings.detach().clone().unsqueeze(1)
        memo=None if notebook_latents is None else notebook_latents.detach().clone()
        meter=WorkMeter(self);sizes=[]
        try:
            with ordered_attention_math():
                meter.phase='ordered_native_begin'
                state=self.core.begin_latent(q,memo,query_mask=query_mask,notebook_mask=notebook_mask,
                    query_positions=query_positions,notebook_positions=notebook_positions)
                if state.get('order_contract')!=ORDER_CONTRACT or state['round']!=0:raise ValueError('native begin contract changed')
                for round_number in range(1,5):
                    meter.phase='ordered_native_transition';sizes.append(len(state['h']))
                    state=self.core.advance_latent(state)
                    if state['round']!=round_number or state.get('order_contract')!=ORDER_CONTRACT:raise ValueError('native advance contract changed')
                meter.phase='final_query_read';latent,_=self.core.read_latent(state)
            n=state['query_n'];mask=answer_mask[:,:n].clone()
            if latent.shape!=(len(q),n,256) or not bool(mask.any(1).all()):raise ValueError('final export must contain query only and valid answer slots')
            final=FinalLatent(latent.detach().clone(),torch.ones_like(latent,dtype=torch.bool),mask,(1,n))
            meter.phase='source_audit_only';prediction=self.core.head(self.core.ln_out(final.latent)).argmax(-1)
            rounds=torch.full((len(q),),4,device=q.device,dtype=torch.long)
            return StopRun(final,ExecutionAudit(prediction,rounds,torch.zeros(len(q),device=q.device,dtype=torch.bool),
                tuple(sizes),int(rounds.sum()),sum(sizes),meter.report(),'fixed',compact,self.core_state_sha256))
        finally:meter.close()

    def infer(self,*args,**kwargs):return self.execute_embeddings(*args,**kwargs).final


def make_ordered_fixed4_executor(core):return OrderedFixed4Executor(core)
