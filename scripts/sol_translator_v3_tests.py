#!/usr/bin/env python3
"""No-optimization V2 boundary/gradient/checkpoint tests, symbolic probes only."""
import json,tempfile
from pathlib import Path
from types import SimpleNamespace
import torch
import claude_fewex_net as N
from sol_spatial_attention_core import AttentionReasoner
from sol_translator_grounding_v3 import question_notebook_tokens,atomic_save,HumanInputProjection
from sol_translator_runtime_v3 import QuestionNotebookReader
from sol_translator_provenance import sha

class Tokenizer:
    eos_token_id=7
    def encode(self,text,add_special_tokens=False):return [8+ord(c)%8 for c in text]

def run():
    tests=[];tok=Tokenizer();row={'question':'q','context':'abc'}
    q,qm,c,cm=question_notebook_tokens(tok,row,'cpu')
    assert q.shape==(1,2) and c.shape==(1,3) and bool(qm.all()) and bool(cm.all());tests.append('question/context split with constant EOS')
    emb=torch.nn.Embedding(16,32).requires_grad_(False)
    reader=QuestionNotebookReader(emb,tok,HumanInputProjection(32),'cpu')
    out=reader.encode(json.dumps(row));assert out['embeddings'].shape==(1,2,256) and out['notebook']['translated'].shape==(1,3,256);tests.append('runtime exports question query and separate D256 notebook')
    core=AttentionReasoner(N.Net('loop'))
    proj=HumanInputProjection(32);query=proj(emb(q),qm);memo=proj(emb(c),cm).flatten(1,2)
    state=core.begin_latent(query,memo)
    state=core.advance_latent(state);h,halt=core.read_latent(state)
    assert h.shape==(1,2,256);h.square().mean().backward()
    assert any(p.grad is not None and bool(p.grad.abs().sum()) for p in proj.parameters()) and not any(p.grad is not None for p in emb.parameters());tests.append('notebook core gradients; final query only; frozen lexical weights')
    # Serialization of primitive RNG and explicit optimizer/core-only schema;
    # no optimizer update or human text generation is performed.
    import random
    payload={'core':core.state_dict(),'reader':proj.state_dict(),'adapter':{'probe':torch.ones(1)},'optimizer':{'state':{0:{'step':torch.tensor(1),'exp_avg':torch.ones(1),'exp_avg_sq':torch.ones(1)}}},'sample_rng':random.Random(1).getstate(),'torch_rng':torch.get_rng_state(),'cuda_rng':[],'ledger':{'updates':1},'binding':{'driver_sha256':sha(__file__)}}
    with tempfile.TemporaryDirectory(prefix='sol_translator_v2_') as d:
        p=Path(d)/'resume.pt';atomic_save(payload,p);saved=torch.load(p,weights_only=True)
        assert set(saved)==set(payload) and not any(k in saved for k in ('LM','decoder'))
        rng=random.Random();rng.setstate(saved['sample_rng']);assert rng.random()==random.Random(1).random()
    tests.append('atomic primitive resume roundtrip and no LM checkpoint')
    record={'passed':len(tests),'total':len(tests),'tests':tests,'optimizer_steps':0,'actual_PC_LM_training':'UNTESTED','grammar_and_grounding':'UNTESTED'}
    print(json.dumps(record));return record
if __name__=='__main__':run()
