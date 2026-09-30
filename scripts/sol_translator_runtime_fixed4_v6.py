#!/usr/bin/env python3
"""Version-pinned question-only reader/context notebook/final-query English."""
import json
import torch
from torch import nn
from sol_translator_grounding_v6 import HumanInputProjection,question_notebook_tokens
from sol_translator_english_v6 import load_english
from sol_translator_provenance import sha
from sol_spatial_attention_core import load_bundle
from scripts.sol_stop_api4 import make_fixed4_executor
from sol_translator_decoder import FinalLatent
from sol_translator_factories import prepare_notebook


class QuestionNotebookReader(nn.Module):
    def __init__(self,embedding,tokenizer,projection,device):
        super().__init__();self.embedding=embedding;self.tokenizer=tokenizer;self.projection=projection;self.device=device
    @torch.no_grad()
    def encode(self,text):
        row=json.loads(text) if text.lstrip().startswith('{') else {'question':text,'context':''}
        if set(row)!={'question','context'} or not all(isinstance(v,str) for v in row.values()):raise ValueError('human question/context required')
        ids,mask,mids,mmask=question_notebook_tokens(self.tokenizer,row,self.device)
        query=self.projection(self.embedding(ids),mask).detach().flatten(1,2)
        memo=self.projection(self.embedding(mids),mmask).detach().flatten(1,2)
        return {'embeddings':query,'answer_mask':mask,'token_shape':(1,query.shape[1]),'notebook':{'translated':memo,'mask':mmask}}


class NotebookEnglishFactories:
    def __init__(self,reader,reasoner,decoder,tokenizer):
        self.input_encoder=reader;self.frozen_reasoner=reasoner;self.final_state_decoder=decoder;self.tokenizer=tokenizer
        self.semantic_status='UNQUALIFIED: actual output, fixed4 engineering phase; learnedstop/sleep unqualified; controls and independent blind recount required'
    @staticmethod
    def notebook_encoder(state):return prepare_notebook(state,width=256)
    @torch.no_grad()
    def reply(self,human_text,notebook_state=None,max_tokens=64):
        encoded=self.input_encoder.encode(human_text)
        memo=self.notebook_encoder(encoded['notebook'])
        if notebook_state is not None:
            extra=self.notebook_encoder(notebook_state)
            memo=torch.cat((memo,extra),1)
        run=self.frozen_reasoner.execute_embeddings(encoded['embeddings'],encoded['answer_mask'],encoded['token_shape'],notebook_latents=memo,notebook_mask=torch.ones(memo.shape[:2],device=memo.device,dtype=torch.bool),policy='fixed',compact=True,cap=4)
        if type(run.final) is not FinalLatent:raise TypeError('shared FinalLatent required')
        # ONLY final query state goes to language decoder, never audit or notebook.
        tokens=self.final_state_decoder.generate(run.final,max_tokens)[0]
        return self.tokenizer.decode(tokens,skip_special_tokens=True)


def load_d256_notebook_factories(config):
    if config['runtime_factory_sha256']!=sha(__file__):raise ValueError('wrong runtime version')
    if config['stop_factory_sha256']!=sha(__import__('pathlib').Path(__file__).parent/'sol_stop_api4.py'):raise ValueError('wrong fixed4 executor source')
    if config['reader_version']!='human-notebook-v2':raise ValueError('wrong reader architecture')
    for key in ('parent','reader','adapter'):
        if config[key+'_sha256']!=sha(config[key+'_path']):raise ValueError('checkpoint hash mismatch '+key)
    raw=torch.load(config['reader_path'],map_location='cpu',weights_only=True)
    if raw.get('reader_version')!='human-notebook-v2' or raw.get('training_origin')!='verified-human-origin':raise ValueError('not a verified human v2 reader')
    binding=torch.load(config['adapter_path'],map_location='cpu',weights_only=True)
    if binding['parent_sha256']!=config['parent_sha256'] or binding['reader_sha256']!=config['reader_sha256']:raise ValueError('adapter parent/reader binding mismatch')
    device=config.get('device','cpu');dec,tok,_=load_english(config['lm_path'],config['lm_provenance'],config['adapter_path'],device)
    projection=HumanInputProjection(raw['lm_width']).to(device);projection.load_state_dict(raw['state_dict'])
    reader=QuestionNotebookReader(dec.lm.get_input_embeddings(),tok,projection,device).eval().requires_grad_(False)
    core,meta=load_bundle(config['parent_path'],device)
    if meta.get('reader_version')!='human-notebook-v2' or meta.get('human_manifest_sha256')!=raw['human_manifest_sha256']:raise ValueError('parent input qualification differs')
    return NotebookEnglishFactories(reader,make_fixed4_executor(core),dec,tok)
