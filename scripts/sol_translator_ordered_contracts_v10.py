#!/usr/bin/env python3
"""Numeric-only full512 joint graph and native final-only boundary checks."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import json
import torch
from torch import nn
from sol_spatial_attention_core import load_bundle
from sol_spatial_poc_ordered_v2 import make_ordered_source
from sol_translator_ground_ordered_v10 import row_graph
from sol_translator_grounding_v6 import HumanInputProjection
from sol_translator_english_v6 import FrozenEnglishDecoder
from sol_translator_runtime import component_fingerprint
from sol_translator_provenance import sha
OWN=ROOT/'artifacts/sol-translator-20260929'
class NumericLM(nn.Module):
 def __init__(self):
  super().__init__();self.embedding=nn.Embedding(16,2048);self.head=nn.Linear(2048,16);self.requires_grad_(False)
 def get_input_embeddings(self):return self.embedding
 def forward(self,inputs_embeds,attention_mask,use_cache=False):
  h=inputs_embeds+inputs_embeds.cumsum(1)/torch.arange(1,inputs_embeds.shape[1]+1)[None,:,None]
  return type('Result',(),{'logits':self.head(h)})()
def run():
 torch.set_num_threads(2);records=[]
 for seed in (0,1):
  torch.manual_seed(4100+seed);src,meta=load_bundle(OWN/f'frozen-parent-s{seed}/parent-s{seed}.pt','cpu');core=make_ordered_source(src).train().requires_grad_(True)
  lm=NumericLM();reader=HumanInputProjection(2048);reader.load_state_dict(torch.load(OWN/f'frozen-parent-s{seed}/input-s{seed}.pt',weights_only=True,map_location='cpu')['state_dict'])
  decoder=FrozenEnglishDecoder(lm,256,1,2);prefixfile=OWN/f'prefix-v7-s{seed}-d0-loop/English.pt';raw=torch.load(prefixfile,map_location='cpu',weights_only=True);decoder.adapter.load_state_dict(raw['adapter_state'])
  assert raw['parent_sha256']==sha(OWN/f'frozen-parent-s{seed}/parent-s{seed}.pt')
  before=component_fingerprint(lm);ids=torch.randint(16,(1,49));book=torch.randint(16,(1,512));labels=torch.randint(16,(1,8));valid=torch.ones_like(ids,dtype=torch.bool);mvalid=torch.ones_like(book,dtype=torch.bool)
  loss,account=row_graph(lm,core,reader,decoder,ids,valid,book,mvalid,labels);loss.backward()
  norms={k:sum(float(p.grad.abs().sum()) for p in m.parameters() if p.grad is not None) for k,m in [('core',core),('reader',reader),('prefix',decoder.adapter)]}
  assert all(x>0 for x in norms.values());assert all(p.grad is None for p in lm.parameters());assert component_fingerprint(lm)==before
  assert account['round']==4 and not account['stop_used'] and len(account['predictions'][0])==8
  records.append({'seed':seed,'numeric_query_positions':49,'numeric_notebook_positions':512,'numeric_label_tokens':8,'gradient_L1':norms,'LM_frozen':True,'final_round':4,'prefix_actual_sha256':sha(prefixfile),'loss_numeric':float(loss.detach()),'checks':5})
 result={'passed':10,'total':10,'records':records,'optimizer_steps':0,'human_examples':0,'DEV_reads':0,'inference_English_outputs':0,'caveat':'Numeric surrogate frozenLM proves graph/shape/lineage only; actualFP32GPUmemory/fullmodel semantics must queuedrun','driver_sha256':sha(ROOT/'scripts/sol_translator_ground_ordered_v10.py')}
 out=OWN/'ORDERED-GROUND-V10-CONTRACTS-r3.json'
 if out.exists():raise ValueError('preserve record')
 out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':run()
