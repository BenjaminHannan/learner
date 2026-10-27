"""Base-compatible notebook attention + latent export, no answer bypass.

For original source/SleepMoE embed/step/read cores. Composer already implements
encode/initial_state/step/read; its board is directly exportable at width 64.
Source d256 -> common d64 export is a learned projection, never a decoded answer.
This adapter is newly initialized and must be trained/qualified by its owner.
"""
from dataclasses import dataclass
import torch
from torch import nn
from sol_compose_notebook import NotebookState


@dataclass(frozen=True)
class BaseState:
    hidden: torch.Tensor
    embedded: torch.Tensor
    dr: torch.Tensor  # geometry, not batch-specific
    dc: torch.Tensor
    notebook: NotebookState
    rounds: torch.Tensor

    def select(self, ids):
        return BaseState(self.hidden[ids],self.embedded[ids],self.dr,self.dc,
                         self.notebook.select(ids),self.rounds[ids])


class BaseContextAdapter(nn.Module):
    """Explicit dynamic_width excludes any base metadata channels.

    Works with source/SleepMoE tensor signature, not heterogeneous ProgramLibrary
    route metadata. The caller supplies width, never a task-ID lookup. No cached
    geometry, routes or batches in this adapter. The base may own geometry as in
    SleepMoE: caller must restore it from the current grid before each dispatch.
    """
    def __init__(self, core, *, dynamic_width=256, heads=8):
        super().__init__()
        if dynamic_width % heads:
            raise ValueError('dynamic width must divide attention heads')
        self.core, self.dynamic_width = core, dynamic_width
        self.memory_projection = nn.Linear(64,dynamic_width)
        self.attention = nn.MultiheadAttention(dynamic_width,heads,batch_first=True)
        self.memory_gate = nn.Linear(2*dynamic_width,dynamic_width)
        self.export_projection = nn.Linear(dynamic_width,64)
        self.stop = nn.Linear(64,1)

    def encode(self, tokens, slots, notebook):
        if not isinstance(notebook,NotebookState) or len(notebook.values)!=len(tokens):
            raise ValueError('per-example NotebookState required')
        e,(dr,dc)=self.core.embed(tokens,slots)
        if e.shape[-1]<self.dynamic_width:
            raise ValueError('base state narrower than declared dynamic width')
        return BaseState(torch.zeros_like(e),e,dr,dc,notebook,
                         torch.zeros(len(e),dtype=torch.long,device=e.device))

    def step(self, state):
        d=self.dynamic_width; h=state.hidden[...,:d]; prompt=state.embedded[...,:d]
        memory=self.memory_projection(state.notebook.values)
        # Add one valid zero vector so a completely empty notebook is finite.
        memory=torch.cat((memory,memory.new_zeros(len(memory),1,d)),1)
        valid=torch.cat((state.notebook.valid,torch.ones(len(memory),1,dtype=torch.bool,device=h.device)),1)
        read,_=self.attention(h+prompt,memory,memory,key_padding_mask=~valid,need_weights=False)
        gate=self.memory_gate(torch.cat((h,read),-1)).sigmoid()
        mixed=torch.cat((h+gate*read,state.hidden[...,d:]),-1)
        next_h=self.core.step(mixed,state.embedded,state.dr,state.dc)
        return BaseState(next_h,state.embedded,state.dr,state.dc,state.notebook,state.rounds+1)

    def export(self, state):
        return self.export_projection(state.hidden[...,:self.dynamic_width])

    def read(self, state):
        # Core logits are diagnostic only; joined talker takes export(), not them.
        logits,_=self.core.read(state.hidden)
        latent=self.export(state)
        return logits,self.stop(latent.mean(1)).squeeze(-1)

    def joined_output(self, state):
        # This is the complete boundary to an output translator; no notebook.
        return self.export(state)


def export_composer(state):
    if state.board.shape[-1]!=64:
        raise ValueError('common final-state width is 64')
    return state.board
