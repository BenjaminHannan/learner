#!/usr/bin/env python3
"""Fixed4/causal decoder boundary checks; zero optimizer/English generation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
from types import SimpleNamespace
import torch
from torch import nn
import claude_fewex_net as N
from sol_spatial_attention_core import AttentionReasoner
from scripts.sol_stop_api4 import make_fixed4_executor
from sol_translator_grounding_v6 import HumanInputProjection
from sol_translator_english_v6 import StatePrefix
from sol_translator_proof_v6 import state_for,final_digest
from sol_translator_runtime import component_fingerprint
from scripts.sol_stop_adapter import FinalLatent

class NumericTokenizer:
    eos_token_id=7
    def encode(self,text,add_special_tokens=False):return [int(c) for c in text]

class NumericEmbedding(nn.Module):
    def __init__(self):super().__init__();self.embedding=nn.Embedding(16,32).requires_grad_(False)
    def get_input_embeddings(self):return self.embedding

def run():
    torch.set_num_threads(2);passed=[];lm=NumericEmbedding();tok=NumericTokenizer()
    reader=HumanInputProjection(32).eval().requires_grad_(False)
    core=AttentionReasoner(N.Net('loop')).eval().requires_grad_(False)
    executor=make_fixed4_executor(core);before=component_fingerprint(core)
    row={'id':'numeric-boundary-probe','question':'12','context':'345'}
    finals={}
    for arm in ('loop','no_state','embedding'):
        finals[arm],account=state_for(row,SimpleNamespace(arm=arm,device='cpu'),lm,tok,reader,executor)
        assert type(finals[arm]) is FinalLatent
    assert finals['loop'].latent.shape==(1,3,256);passed.append('real fixed4 exports question query only and canonical FinalLatent')
    assert finals['embedding'].latent.shape==(1,6,256);passed.append('strong decoder-alone embedding control includes all question and context cells')
    assert not bool(finals['no_state'].latent.any());passed.append('no-state truly zero; geometry query-only')
    prefix=StatePrefix(256,32);prefix(finals['loop']).square().mean().backward()
    assert any(p.grad is not None for p in prefix.parameters())
    assert not any(p.grad is not None for m in (lm,reader,core) for p in m.parameters());passed.append('detached final-state decoder gradients cannot reach frozen reader/core/lexical weights')
    assert component_fingerprint(core)==before;passed.append('core unchanged under controls and decoder gradient check')
    try:executor.execute_embeddings(torch.zeros(1,1,256),torch.ones(1,1,dtype=torch.bool),(1,1),policy='learned',cap=48)
    except ValueError:passed.append('fixed4 factory refuses accidental learned48 promotion')
    else:raise AssertionError('wrong stop policy accepted')
    assert final_digest(finals['loop'])!=final_digest(finals['no_state']);passed.append('raw state identity distinguishes actual and no-state control')
    record={'passed':len(passed),'total':7,'tests':passed,'optimizer_steps':0,'human_examples':0,'English_outputs':0,'scope':'numeric mechanics only; frozen-core English quality UNTESTED'}
    print(json.dumps(record));return record
if __name__=='__main__':run()
