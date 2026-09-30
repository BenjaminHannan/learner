#!/usr/bin/env python3
"""Read-only TRAIN coverage and closed-prefix conditioning diagnosis.
No optimizer, DEV generation, oracle crop, or generated adaptation text.
"""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import argparse,json
import torch
from transformers import AutoTokenizer
from sol_translator_grounding_v6 import human_rows,human_loss,guard_queue
from sol_translator_provenance import sha

class ShiftProbe(torch.nn.Module):
 def __init__(self):
  super().__init__();self.embedding=torch.nn.Embedding(16,16);self.embedding.weight.data.copy_(torch.eye(16));self.embedding.requires_grad_(False)
 def get_input_embeddings(self):return self.embedding
 def forward(self,inputs_embeds,attention_mask,use_cache=False):
  self.last_inputs=inputs_embeds.detach().clone();self.last_attention=attention_mask.detach().clone()
  # Numeric logits allow gradient to prefix; labels never supplied to this LM.
  return type('Result',(),{'logits':inputs_embeds+inputs_embeds.mean(1,keepdim=True)})()

def shift_contract():
 lm=ShiftProbe();prefix=torch.ones(2,8,16,requires_grad=True);labels=torch.tensor([[3,4,5],[6,7,-100]])
 loss,preds=human_loss(lm,prefix,labels,1,2,False,True);loss.backward()
 shifted=lm.last_inputs[:,8:].argmax(-1)
 assert shifted.tolist()==[[1,3,4],[1,6,7]],'incorrect shifted HUMAN target'
 assert lm.last_attention.tolist()==[[1]*11,[1]*10+[0]],'prefix/target padding mask wrong'
 assert preds.shape==labels.shape and prefix.grad.abs().sum()>0
 return {'passed':3,'total':3,'checks':['constant BOS + preceding HUMAN tokens only','8 prefix positions visible; target padding masked','loss aligned to3targets and gradients reachprefix'],'optimizer_steps':0,'English_examples':0,'synthetic_labels':'numeric mechanics only'}

def coverage(a):
 guard_queue();out=Path(a.out).resolve()
 if not out.is_relative_to(ROOT/'artifacts/sol-translator-20260929') or out.exists():raise ValueError('new owned report only')
 rows,_=human_rows(a.corpus);rows=[x for x in rows if x['split']=='train']
 from sol_translator_cache_policy_v6 import verify_manifest
 verify_manifest(Path(a.model),json.loads((ROOT/'artifacts/sol-translator-20260929/CACHED-LFM-ORIGINAL-PROVENANCE.json').read_text()))
 tok=AutoTokenizer.from_pretrained(a.model,local_files_only=True,use_fast=True)
 report=[]
 for row in rows:
  full=tok(row['context'],add_special_tokens=False,return_offsets_mapping=True)
  offsets=full['offset_mapping'];char_end=offsets[min(256,len(offsets))-1][1] if offsets else 0
  supplied=row['context'][:char_end]
  # Read-only diagnostic against reference; never changes supplied context.
  record={'id':row['id'],'split':'TRAIN-only','context_tokens':len(full['input_ids']),'supplied_tokens':min(256,len(offsets)),'supplied_char_end':char_end,'supplied_ids':full['input_ids'][:256],'answer_present_in_fixed_prefix':row['answer_text'] in supplied,'full_target_sentence_present_in_fixed_prefix':row['target_text'] in supplied,'source_path':row['source_path'],'source_sha256':row['source_sha256'],'source_span':row['source_span'],'labels_used_to_select_or_crop_input':False}
  report.append(record)
 result={'rows':len(report),'answer_present':sum(r['answer_present_in_fixed_prefix'] for r in report),'full_evidence_sentence_present':sum(r['full_target_sentence_present_in_fixed_prefix'] for r in report),'context_truncated':sum(r['context_tokens']>256 for r in report),'rows_raw':report,'DEV_examples':0,'optimizer_steps':0,'human_pairs_sha256':sha(Path(a.corpus)/'pairs.json'),'driver_sha256':sha(__file__),'shift_contract':shift_contract(),'precision':'tokenizer-only; no LM loaded/CUDA/training','interpretation':'coverage only; presence cannot prove model uses evidence; no inference oraclecrop permitted'}
 out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows_raw'}))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--shift-only',action='store_true');p.add_argument('--model');p.add_argument('--corpus',default=str(ROOT/'artifacts/sol-translator-20260929/corpus'));p.add_argument('--out');a=p.parse_args()
 if a.shift_only:print(json.dumps(shift_contract()))
 else:coverage(a)
