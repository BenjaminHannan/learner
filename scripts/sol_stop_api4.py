"""API4 frozen fixed-four factory. Causal generation only, NOT stop readiness."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from torch import nn
from scripts.sol_stop_adapter import FinalLatent
from scripts.sol_stop_grounded_adapter_v4 import GroundedD256FinalStateAdapter

VERSION='sol_stop.api4.fixed-four.v1'


class FixedFourExecutor(nn.Module):
    def __init__(self,core):
        super().__init__();self.adapter=GroundedD256FinalStateAdapter(core)
        self.accepted_stop_ready=False
        self.stage_proof_status='NOT SHOWN'

    def train(self,mode=True):
        super().train(False);return self

    def execute_embeddings(self,embeddings,answer_mask,token_shape,*,notebook_latents=None,
                           notebook_mask=None,policy='fixed',cap=4,compact=True,threshold=.5):
        if policy!='fixed' or cap!=4:
            raise ValueError('API4 fixed generation is fixed4 only; no inherited cap48/learned qualification')
        return self.adapter.execute_embeddings(embeddings,answer_mask,token_shape,
            notebook_latents=notebook_latents,notebook_mask=notebook_mask,
            policy='fixed',cap=4,compact=compact,threshold=threshold)

    def infer(self,*args,**kwargs)->FinalLatent:
        return self.execute_embeddings(*args,**kwargs).final


def make_fixed4_executor(core)->FixedFourExecutor:
    """Caller loads/hash-binds actual frozen checkpoint. No weights fallback."""
    return FixedFourExecutor(core).eval()
