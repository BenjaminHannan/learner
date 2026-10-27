#!/usr/bin/env python3
"""Joined text -> learned reader -> shared frozen reasoner -> English path.
Factory provides ONLY reader and reasoner. Never routes questions to the LM.
No executor, notebook recall, sleep, rule solver, or answer template here.
"""
from __future__ import annotations
import hashlib,importlib,json,sys
from pathlib import Path
import torch
from sol_translator_decoder import FinalLatent,validate_final
from sol_translator_english import FrozenEnglishDecoder,load_local_lm
from sol_translator_provenance import sha
from scripts.sol_stop_adapter import FinalStateAdapter


def read_final(path):
    data=torch.load(path,map_location='cpu',weights_only=True)
    required={'latent','latent_mask','answer_mask','token_shape'}
    if type(data) is not dict or set(data)!=required:
        raise ValueError('state cache must contain FinalLatent fields only')
    return validate_final(FinalLatent(**data))


def write_final(path,final):
    validate_final(final)
    torch.save({name:getattr(final,name) for name in ('latent','latent_mask','answer_mask','token_shape')},path)


def component_fingerprint(module):
    h=hashlib.sha256()
    for name,t in sorted(module.state_dict().items()):
        h.update(f'{name}:{t.dtype}:{tuple(t.shape)}'.encode())
        h.update(t.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
    return h.hexdigest()


def make_control(final,source,permutation=None):
    validate_final(final)
    if source=='no_state':
        return FinalLatent(torch.zeros_like(final.latent),final.latent_mask,final.answer_mask,final.token_shape)
    if source=='shuffled_state':
        if permutation is None or len(permutation)!=len(final.latent) or bool((permutation==torch.arange(len(permutation),device=permutation.device)).any()):
            raise ValueError('shuffled-state needs a genuine derangement')
        return FinalLatent(final.latent[permutation],final.latent_mask[permutation],final.answer_mask,final.token_shape)
    raise ValueError('embedding/untrained/plain controls must come from their actual frozen sources')


def load_english(model_path,provenance_path,adapter_path,device='cpu'):
    lm,tok,provenance=load_local_lm(model_path,provenance_path,device)
    raw=torch.load(adapter_path,map_location='cpu',weights_only=True)
    required={'state_width','hidden','prefix_tokens','adapter_state','human_manifest_sha256','human_registry_sha256','source_state_contract','lm_provenance_sha256','training_origin','parent_sha256','reader_sha256','training_stage'}
    if type(raw) is not dict or set(raw)!=required or raw['training_origin']!='verified-human-origin-verbatim' or raw['source_state_contract']!='sol-stop-FinalLatent-v1':
        raise ValueError('unqualified English adapter checkpoint')
    if raw['lm_provenance_sha256']!=sha(provenance_path):
        raise ValueError('wrong frozen language decoder provenance')
    dec=FrozenEnglishDecoder(lm,raw['state_width'],tok.bos_token_id,tok.eos_token_id,raw['hidden'],raw['prefix_tokens']).to(device)
    dec.adapter.load_state_dict(raw['adapter_state'])
    return dec,tok,provenance


class JoinedTranslator:
    def __init__(self,reader,reasoner,decoder,tokenizer,reader_provenance):
        if reader_provenance.get('training_origin')!='verified-human-origin' or not reader_provenance.get('weights_sha256'):
            raise ValueError('learned text reader lacks verified human-only adaptation provenance')
        if not hasattr(reader,'encode') or not callable(getattr(reasoner,'execute_embeddings',None)):
            raise TypeError('learned reader.encode + shared FinalStateAdapter required')
        self.reader=reader.eval().requires_grad_(False)
        self.reasoner=reasoner.eval()
        self.decoder,self.tokenizer=decoder,tokenizer

    @torch.no_grad()
    def reply(self,text,max_tokens=64,notebook_latents=None):
        if not isinstance(text,str) or not text.strip():
            raise ValueError('nonempty text required')
        # Raw text ends at input translator. Recall, notebook and thinking are
        # owned by the core; no retrieved strings enter output translation.
        encoded=self.reader.encode(text)
        if type(encoded) is not dict or set(encoded)!={'latent','answer_mask'}:
            raise ValueError('reader must return immutable float latent + answer mask only')
        latent=encoded['latent'].flatten(1,2)
        completed=self.reasoner.execute_embeddings(latent,encoded['answer_mask'],(1,latent.shape[1]),notebook_latents=notebook_latents,policy='learned',compact=True,cap=48)

        # Deliberately pass final ONLY. Audit never goes to decoder.
        ids=self.decoder.generate(completed.final.to(next(self.decoder.adapter.parameters()).device),max_tokens)
        return self.tokenizer.decode(ids[0],skip_special_tokens=True)


def factory(spec,config):
    module,function=spec.split(':',1)
    if not module.startswith('scripts.sol_'):
        raise ValueError('explicit Sol-owned runtime factory required')
    return getattr(importlib.import_module(module),function)(config)


class LearnedEnglishReader(torch.nn.Module):
    def __init__(self,lm,tokenizer,projection,device):
        super().__init__();self.embedding=lm.get_input_embeddings();self.tokenizer=tokenizer;self.projection=projection;self.device=device
    def encode(self,text):
        from sol_translator_grounding import input_tokens
        # Explicit bounded QA input. Bare text is a human question with no supplied
        # context; there is no hidden answer, prompt frame or retrieval rule.
        if text.lstrip().startswith('{'):
            row=json.loads(text)
            if set(row)!={'question','context'} or not all(isinstance(v,str) for v in row.values()):
                raise ValueError('input JSON requires human question and context strings')
        else:row={'question':text,'context':''}
        ids,valid=input_tokens(self.tokenizer,[row],self.device)
        latent=self.projection(self.embedding(ids),valid).detach()
        return {'latent':latent,'answer_mask':valid}


def build_joined(config):
    from sol_translator_grounding import HumanInputProjection
    from sol_spatial_attention_core import load_bundle
    from sol_translator_language_proof import shared_float_adapter
    device=config.get('device','cpu')
    decoder,tok,_=load_english(config['lm_path'],config['lm_provenance'],config['adapter_path'],device)
    binding=torch.load(config['adapter_path'],map_location='cpu',weights_only=True)
    if binding['parent_sha256']!=sha(config['parent_path']) or binding['reader_sha256']!=sha(config['reader_path']):raise ValueError('output adapter does not match the frozen parent and reader')
    raw=torch.load(config['reader_path'],map_location='cpu',weights_only=True)
    if raw.get('training_origin')!='verified-human-origin':raise ValueError('reader adaptation origin invalid')
    projection=HumanInputProjection(raw['lm_width']).to(device);projection.load_state_dict(raw['state_dict'])
    reader=LearnedEnglishReader(decoder.lm,tok,projection,device)
    core,meta=load_bundle(config['parent_path'],device);core.eval().requires_grad_(False)
    reasoner=shared_float_adapter(core)
    return JoinedTranslator(reader,reasoner,decoder,tok,{'training_origin':'verified-human-origin','weights_sha256':sha(config['reader_path'])})


def chat(config_path):
    cfg=json.loads(Path(config_path).read_text())
    agent=build_joined(cfg)
    for text in sys.stdin:
        if text.strip():print(agent.reply(text.rstrip('\n')),flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--config',required=True)
    a=p.parse_args();chat(a.config)
