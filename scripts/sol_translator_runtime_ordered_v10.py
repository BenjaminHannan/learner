#!/usr/bin/env python3
"""Actual order-aware reader/notebook/final-query English factory.
No source fallback; exact trained component hashes, numeric positions in core.
Fixed4 engineering fallback; learned-stop qualification explicitly absent.
"""
import json
from pathlib import Path
import torch
from torch import nn
from sol_translator_grounding_v6 import HumanInputProjection,question_notebook_tokens
from sol_translator_english_ordered_v10 import load_ordered_english
from sol_translator_provenance import sha
from sol_spatial_poc_ordered_v2 import load_ordered_bundle,CONTRACT
from scripts.sol_stop_ordered_api2 import make_ordered_fixed4_executor,prepare_ordered_notebook
from scripts.sol_stop_adapter import FinalLatent

class OrderedQuestionNotebookReader(nn.Module):
 def __init__(self,embedding,tokenizer,projection,device):
  super().__init__();self.embedding=embedding;self.tokenizer=tokenizer;self.projection=projection;self.device=device
 @torch.no_grad()
 def encode(self,text):
  row=json.loads(text) if text.lstrip().startswith('{') else {'question':text,'context':''}
  if set(row)!={'question','context'} or not all(isinstance(x,str) for x in row.values()):raise ValueError('human question/context fields only')
  ids,mask,mids,mmask=question_notebook_tokens(self.tokenizer,row,self.device,max_context=512)
  query=self.projection(self.embedding(ids),mask).detach().flatten(1,2)
  memo=self.projection(self.embedding(mids),mmask).detach().flatten(1,2)
  pos=torch.arange(memo.shape[1],device=memo.device,dtype=torch.long)[None].expand(len(memo),-1)
  return {'embeddings':query,'answer_mask':mask,'token_shape':(1,query.shape[1]),'notebook':{'translated':memo,'mask':mmask,'positions':pos},'input_account':{'query_tokens_before_cap':len(self.tokenizer.encode(row['question'],add_special_tokens=False)),'notebook_tokens_before_cap':len(self.tokenizer.encode(row['context'],add_special_tokens=False)),'query_cap':48,'notebook_cap':512,'selection':'fixed prefix independent of reference labels; all TRAIN contexts<=479'}}

class OrderedNotebookEnglishFactories:
 def __init__(self,reader,reasoner,decoder,tok):
  self.input_encoder=reader;self.frozen_reasoner=reasoner;self.final_state_decoder=decoder;self.tokenizer=tok
  self.semantic_status='ENGINEERING: fixed4 unqualified learned stop; semantic grounding must be measured on allowed human inputs; no overnight gain claim'
 @staticmethod
 def notebook_encoder(state):return prepare_ordered_notebook(state)
 @torch.no_grad()
 def reply(self,human_text,notebook_state=None,max_tokens=64):
  encoded=self.input_encoder.encode(human_text);memo=self.notebook_encoder(encoded['notebook'])
  if notebook_state is not None:
   extra=self.notebook_encoder(notebook_state)
   previous=memo['notebook_positions'];offset=int(previous.max())+1 if previous.numel() else 0
   memo={'notebook_latents':torch.cat((memo['notebook_latents'],extra['notebook_latents']),1),'notebook_mask':torch.cat((memo['notebook_mask'],extra['notebook_mask']),1),'notebook_positions':torch.cat((previous,extra['notebook_positions']+offset),1)}
  run=self.frozen_reasoner.execute_embeddings(encoded['embeddings'],encoded['answer_mask'],encoded['token_shape'],query_mask=encoded['answer_mask'],**memo,policy='fixed',cap=4,compact=True)
  if type(run.final) is not FinalLatent:raise TypeError('canonical detached FinalLatent required')
  # Only final query packet. No prompt, reference text, notebook or audit enters.
  return self.tokenizer.decode(self.final_state_decoder.generate(run.final,max_tokens)[0],skip_special_tokens=True)

def load_d256_notebook_factories(config):
 if config['runtime_factory_sha256']!=sha(__file__):raise ValueError('wrong runtime source')
 if config['stop_factory_sha256']!=sha(Path(__file__).parent/'sol_stop_ordered_api2.py'):raise ValueError('wrong native ordered executor source')
 if config['ordered_core_sha256']!=sha(Path(__file__).parent/'sol_spatial_poc_ordered_v2.py'):raise ValueError('wrong ordered core source')
 if config['order_contract']!=CONTRACT or config['reader_version']!='human-notebook-v2':raise ValueError('wrong input contract')
 for k in ('parent','reader','adapter'):
  if config[k+'_sha256']!=sha(config[k+'_path']):raise ValueError('component checkpoint hash mismatch '+k)
 reader_raw=torch.load(config['reader_path'],map_location='cpu',weights_only=True);prefix_raw=torch.load(config['adapter_path'],map_location='cpu',weights_only=True)
 if reader_raw.get('training_origin')!='verified-human-origin' or reader_raw.get('input_version')!='human-notebook-ordered-v10' or reader_raw.get('order_contract')!=CONTRACT:raise ValueError('wrong actual HUMAN ordered reader')
 if prefix_raw['parent_sha256']!=config['parent_sha256'] or prefix_raw['reader_sha256']!=config['reader_sha256'] or prefix_raw.get('order_contract')!=CONTRACT:raise ValueError('prefix-parent-reader-order binding mismatch')
 device=config.get('device','cpu');dec,tok,_=load_ordered_english(config['lm_path'],config['lm_provenance'],config['adapter_path'],device)
 proj=HumanInputProjection(reader_raw['lm_width']).to(device);proj.load_state_dict(reader_raw['state_dict'])
 reader=OrderedQuestionNotebookReader(dec.lm.get_input_embeddings(),tok,proj,device).eval().requires_grad_(False)
 core,meta=load_ordered_bundle(config['parent_path'],device)
 if meta.get('order_contract')!=CONTRACT or meta.get('human_manifest_sha256')!=reader_raw['human_manifest_sha256'] or meta.get('input_version')!='human-notebook-ordered-v10':raise ValueError('actual ordered parent lineage mismatch')
 return OrderedNotebookEnglishFactories(reader,make_ordered_fixed4_executor(core),dec,tok)
