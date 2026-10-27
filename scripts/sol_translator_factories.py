#!/usr/bin/env python3
"""D256 joined factories; masked notebook boundary, no unqualified D64 bridge."""
from dataclasses import dataclass
import torch
from sol_translator_runtime import build_joined


def prepare_notebook(state,*,width=256):
    """Consume translated latent + mask ONLY. Padding never becomes a fact.
    B1 chat supported; equal valid lengths supported for batched core calls.
    D64 -> D256 is a semantic coordinate conversion, not harmless padding.
    """
    if type(state) is dict:
        if set(state)!={'translated','mask'}:raise ValueError('notebook payload must be translated + mask only')
        translated,mask=state['translated'],state['mask']
    else:
        translated,mask=getattr(state,'translated',None),getattr(state,'mask',None)
    if not isinstance(translated,torch.Tensor) or translated.ndim!=3 or not translated.is_floating_point():raise ValueError('notebook translated[B,M,D] required')
    if not isinstance(mask,torch.Tensor) or mask.dtype!=torch.bool or mask.shape!=translated.shape[:2] or mask.device!=translated.device:raise ValueError('notebook mask[B,M] bool required')
    if not bool(torch.isfinite(translated).all()):raise ValueError('nonfinite notebook')
    if translated.shape[-1]!=width:
        raise ValueError('UNQUALIFIED D64/D256 semantic bridge: requires separately human-trained, frozen bridge; no random projection or padding substitution')
    lengths=mask.sum(1)
    if not bool((lengths==lengths[0]).all()):raise ValueError('different notebook lengths require per-row core execution; padded facts forbidden')
    return torch.stack([row[valid] for row,valid in zip(translated,mask)]).detach()


@dataclass(frozen=True)
class EnglishFactories:
    agent: object
    state_width: int=256
    semantic_status: str='UNQUALIFIED until real generation + causal controls + independent blind recount'
    @property
    def input_encoder(self):return self.agent.reader
    @property
    def final_state_decoder(self):return self.agent.decoder
    @property
    def frozen_reasoner(self):return self.agent.reasoner
    def notebook_encoder(self,state):return prepare_notebook(state,width=self.state_width)
    def reply(self,human_text,notebook_state=None):
        memory=None if notebook_state is None else self.notebook_encoder(notebook_state)
        return self.agent.reply(human_text,notebook_latents=memory)


def load_d256_factories(config):
    """Requires actual trained/human-qualified checkpoint hashes in config.
    No random initial weights or fallback answer templates returned on missing.
    """
    return EnglishFactories(build_joined(config))
