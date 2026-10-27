"""v1 D256 immutable-float executor. New checkpoint qualification required.

Original halt+full125 stability remains a comparator. Learned-only policy has
no stability/minimum-round rule. Output decoder receives final query state only.
Notebook entries must be unpadded: source attention has no padding-mask API.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from torch import nn
from scripts.sol_stop_adapter import FinalLatent, ExecutionAudit, StopRun, WorkMeter, module_hash

VERSION = 'sol_stop.human-grounded.d256.v4'


class MaskedLatentStopController(nn.Module):
    def __init__(self, width=256, hidden=32):
        super().__init__()
        self.register_buffer('mean', torch.zeros(width))
        self.register_buffer('scale', torch.ones(width))
        self.mlp = nn.Sequential(nn.Linear(width,hidden), nn.GELU(), nn.Linear(hidden,1))

    @staticmethod
    def features(board, mask):
        return (board.float()*mask[...,None]).sum(1)/mask.sum(1,keepdim=True).clamp_min(1)

    def forward(self, board, mask):
        return self.mlp((self.features(board,mask)-self.mean)/self.scale).squeeze(-1)


class GroundedD256FinalStateAdapter(nn.Module):
    def __init__(self, core, controller=None):
        super().__init__()
        self.core, self.controller = core.eval().requires_grad_(False), controller
        if controller is not None:
            controller.eval().requires_grad_(False)
        self.core_state_sha256 = module_hash(core)

    def train(self, mode=True):
        super().train(False)
        return self

    @torch.no_grad()
    def execute_embeddings(self, embeddings, answer_mask, token_shape, *, notebook_latents=None,
                           notebook_mask=None, policy='learned', threshold=.5, cap=4, compact=True,
                           trace=None):
        if (embeddings.ndim!=3 or embeddings.shape[-1]!=256 or not embeddings.is_floating_point()
                or answer_mask.shape!=embeddings.shape[:2] or answer_mask.dtype!=torch.bool
                or embeddings.device!=answer_mask.device or not bool(torch.isfinite(embeddings).all())
                or not bool(answer_mask.any(1).all()) or len(token_shape)!=2
                or token_shape[0]*token_shape[1]!=embeddings.shape[1]
                or type(cap)!=int or not 1<=cap<=48 or not 0<=threshold<=1
                or policy not in ('learned','guarded','original_guarded','fixed')
                or type(compact)!=bool):
            raise ValueError('invalid D256 float input / policy / mask')
        if policy in ('learned','guarded') and self.controller is None:
            raise ValueError('exact checkpoint-bound D256 controller required')
        if policy=='original_guarded' and threshold!=.5:
            raise ValueError('inherited comparator threshold is exactly .5')
        if self.core.__class__.__name__ == 'PlainAttentionReasoner':
            return self._plain(embeddings,answer_mask,token_shape,notebook_latents,notebook_mask,policy,cap,compact,trace)
        e=embeddings.detach().clone(); b,n,_=e.shape
        dr,dc=self.core.offsets(*token_shape,e.device)
        if notebook_latents is not None:
            memo=notebook_latents
            if (memo.ndim!=3 or memo.shape[0]!=b or memo.shape[-1]!=256
                    or memo.device!=e.device or memo.dtype!=e.dtype or not bool(torch.isfinite(memo).all())):
                raise ValueError('finite same-device/dtype Notebook[B,M,256] required')
            if notebook_mask is None or notebook_mask.shape!=memo.shape[:2] or notebook_mask.dtype!=torch.bool:
                raise ValueError('explicit notebook mask required')
            if not bool(notebook_mask.all()):
                raise ValueError('unpadded notebook required; do not pretend source attention masks padding')
            if memo.shape[1]:
                e=torch.cat((e,memo.detach().clone()),1)
                total=e.shape[1]
                rr=torch.full((total,total),4,device=e.device,dtype=torch.long); cc=rr.clone()
                rr[:n,:n],cc[:n,:n]=dr,dc; dr,dc=rr,cc
        elif notebook_mask is not None:
            raise ValueError('notebook mask without notebook')
        board=torch.zeros_like(e); active=torch.arange(b,device=e.device)
        chosen=e.new_zeros(b,n,256); rounds=torch.zeros(b,device=e.device,dtype=torch.long)
        stopped=torch.zeros(b,device=e.device,dtype=torch.bool); done=torch.zeros_like(stopped)
        mask=answer_mask.clone(); previous=previous2=None; sizes=[]
        meter=WorkMeter(self)
        plain=getattr(self.core,'arm',None)=='plain'
        if plain and policy!='fixed':
            meter.close(); raise ValueError('plain control has fixed unshared depth')
        try:
            for r in range(1,(1 if plain else cap)+1):
                meter.phase='transition'; sizes.append(len(active))
                if plain:
                    board=e
                    for block in self.core.blocks:board=block(board,dr,dc)
                else:board=self.core.step(board,e,dr,dc)
                query=board[:,:n]
                meter.phase='source_reference_read'
                lg,q=self.core.read(query); pred=lg.argmax(-1)
                fire=torch.zeros(len(active),dtype=torch.bool,device=e.device)
                if policy!='fixed' and not plain:
                    if policy!='original_guarded':
                        meter.phase='controller'; q=self.controller(query,mask)
                    if not bool(torch.isfinite(q).all()):raise ValueError('nonfinite halt')
                    fire=q.sigmoid()>threshold
                    if policy in ('guarded','original_guarded'):
                        guard_mask=mask if policy=='guarded' else torch.ones_like(mask)
                        fire &= (~(((pred!=previous)|(previous!=previous2))&guard_mask).any(1)
                                 if previous2 is not None else torch.zeros_like(fire))
                if trace is not None:
                    # Collection callback receives detached states only; never influences stop.
                    trace(r,active.clone(),query.detach().clone(),mask.clone(),pred.detach().clone())
                choose=(fire|(r==cap)|plain)&~done[active]
                ids=active[choose]; chosen[ids]=query[choose]; rounds[ids]=r; stopped[ids]=fire[choose] & (r < cap)
                done[ids]=True
                if compact:
                    keep=~choose
                    previous2=previous[keep] if previous is not None else None
                    previous=pred[keep]
                    active,e,board,mask=active[keep],e[keep],board[keep],mask[keep]
                    if not len(active):break
                else:previous2,previous=previous,pred
            if not bool(done.all()):raise AssertionError('unselected final row')
            if compact and sum(sizes)!=int(rounds.sum()):raise AssertionError('uncharged executed rows')
            meter.phase='final_reference_read'; pred=self.core.read(chosen)[0].argmax(-1)
            final=FinalLatent(chosen.detach(),torch.ones_like(chosen,dtype=torch.bool),answer_mask.clone(),tuple(token_shape))
            return StopRun(final,ExecutionAudit(pred,rounds,stopped,tuple(sizes),int(rounds.sum()),sum(sizes),
                           meter.report(),policy,compact,self.core_state_sha256))
        finally:meter.close()

    def infer(self, embeddings, answer_mask, token_shape, **kwargs):
        return self.execute_embeddings(embeddings,answer_mask,token_shape,**kwargs).final

    @torch.no_grad()
    def _plain(self, embeddings, mask, shape, memo, memo_mask, policy, cap, compact, trace):
        if policy!='fixed' or cap!=4 or self.core.rounds!=4:
            raise ValueError('plain is one fixed four-segment forward pass; cannot learn-stop or recur')
        if memo is not None:
            if (memo.ndim!=3 or memo.shape[0]!=len(embeddings) or memo.shape[-1]!=256
                    or memo_mask is None or memo_mask.dtype!=torch.bool or memo_mask.shape!=memo.shape[:2]
                    or memo.device!=embeddings.device or memo.dtype!=embeddings.dtype
                    or not bool(memo_mask.all()) or not bool(torch.isfinite(memo).all())):
                raise ValueError('finite fully valid plain notebook required')
        elif memo_mask is not None:raise ValueError('notebook mask without memory')
        sizes=[]; handles=[]; meter=WorkMeter(self)
        for norm in self.core.state_norms:
            handles.append(norm.register_forward_pre_hook(lambda module,inputs:sizes.append(len(inputs[0]))))
        try:
            meter.phase='plain_distinct_segments'
            latent=embeddings.detach().clone().reshape(len(embeddings),*shape,256)
            h,_=self.core.forward_latent(latent,None if memo is None else memo.detach().clone())
            if sizes!=[len(embeddings)]*4:raise AssertionError('plain did not execute all four distinct segments once')
            if h.shape!=embeddings.shape:raise AssertionError('plain exported notebook or wrong query shape')
            meter.phase='final_reference_read'
            pred=self.core.head(self.core.ln_out(h)).argmax(-1)
            if trace is not None:trace(4,torch.arange(len(h),device=h.device),h.detach().clone(),mask.clone(),pred.clone())
            final=FinalLatent(h.detach(),torch.ones_like(h,dtype=torch.bool),mask.clone(),tuple(shape))
            rounds=torch.full((len(h),),4,device=h.device,dtype=torch.long)
            return StopRun(final,ExecutionAudit(pred,rounds,torch.zeros(len(h),device=h.device,dtype=torch.bool),
                tuple(sizes),int(rounds.sum()),sum(sizes),meter.report(),'fixed',compact,self.core_state_sha256))
        finally:
            meter.close()
            for handle in handles:handle.remove()
