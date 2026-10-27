#!/usr/bin/env python3
"""Frozen causal English decoder + learned final-state prefix.
Inference consumes FinalLatent only, plus generated history and constant BOS.
Training uses shifted, verified HUMAN targets in one teacher-forced pass.
Inference consumes only final latent, constant BOS and its own output history.
"""
from __future__ import annotations
from pathlib import Path
import hashlib, json
import torch
from torch import nn
from sol_translator_decoder import FinalLatent, validate_final, masked_normalize


class StatePrefix(nn.Module):
    def __init__(self, state_width, lm_width, hidden=32, prefix_tokens=8):
        super().__init__()
        self.state_width, self.prefix_tokens = state_width, prefix_tokens
        self.scale=nn.Parameter(torch.ones(state_width))
        self.bias=nn.Parameter(torch.zeros(state_width))
        self.project = nn.Sequential(nn.Linear(state_width + 3, hidden), nn.GELU(), nn.Linear(hidden, lm_width))

    def forward(self, packet):
        validate_final(packet)
        return self.project_training(packet.latent,packet.latent_mask,packet.answer_mask,packet.token_shape)

    def project_training(self,state,latent_mask,slots,shape):
        """Differentiable joint-grounding phase ONLY, before parent freezing.
        Inference forward() still accepts FinalLatent only. No raw text here.
        """
        rows,cols=shape
        if state.shape[-1]!=self.state_width or state.ndim!=3 or latent_mask.shape!=state.shape or slots.shape!=state.shape[:2]:
            raise ValueError('joint-training latent dimensions invalid')
        h=state.float();mask=latent_mask.float();count=mask.sum(-1,keepdim=True).clamp_min(1)
        mean=(h*mask).sum(-1,keepdim=True)/count
        var=((h-mean).square()*mask).sum(-1,keepdim=True)/count
        normalized=(h-mean)*torch.rsqrt(var+1e-5)*mask
        r=torch.arange(rows,device=state.device).repeat_interleave(cols).float()/max(rows-1,1)
        c=torch.arange(cols,device=state.device).repeat(rows).float()/max(cols-1,1)
        geom=torch.stack((r,c),-1)[None].expand(len(state),-1,-1)
        x=self.project(torch.cat((normalized*self.scale+self.bias,geom,slots[...,None].float()),-1))
        outputs=[]
        for row,mask in zip(x,slots.bool()):
            if not bool(mask.any()):raise ValueError('no answer slots')
            outputs.append(torch.nn.functional.adaptive_avg_pool1d(row[mask].T[None],self.prefix_tokens)[0].T)
        return torch.stack(outputs)

    def parameter_count(self):
        return sum(p.numel() for p in self.parameters())


class FrozenEnglishDecoder(nn.Module):
    def __init__(self, lm, state_width, bos_id, eos_id, hidden=32, prefix_tokens=8):
        super().__init__()
        if type(bos_id) is not int or type(eos_id) is not int:
            raise ValueError('explicit constant BOS/EOS IDs required')
        self.lm=lm.eval().requires_grad_(False)
        width=lm.get_input_embeddings().weight.shape[1]
        self.adapter=StatePrefix(state_width,width,hidden,prefix_tokens)
        self.bos_id,self.eos_id=bos_id,eos_id

    def train(self,mode=True):
        super().train(mode); self.lm.eval()
        return self

    def rollout(self,packet,max_tokens=64):
        if not 1<=max_tokens<=128:
            raise ValueError('token budget outside 1..128')
        prefix=self.adapter(packet)
        emb=self.lm.get_input_embeddings()
        prefix=prefix.to(dtype=emb.weight.dtype)
        generated=torch.full((len(prefix),1),self.bos_id,device=prefix.device,dtype=torch.long)
        logits=[]
        for _ in range(max_tokens):
            # No labels argument, chat template, raw question or reference text.
            inputs=torch.cat((prefix,emb(generated)),dim=1)
            out=self.lm(inputs_embeds=inputs,attention_mask=torch.ones(inputs.shape[:2],device=inputs.device,dtype=torch.long),use_cache=False)
            lg=out.logits[:,-1,:].float()
            logits.append(lg)
            generated=torch.cat((generated,lg.detach().argmax(-1,keepdim=True)),dim=1)
        return generated[:,1:],torch.stack(logits,dim=1)

    @torch.no_grad()
    def generate(self,packet,max_tokens=64):
        self.eval()
        if not 1<=max_tokens<=128:
            raise ValueError('token budget outside 1..128')
        prefix=self.adapter(packet)
        emb=self.lm.get_input_embeddings()
        bos=torch.full((len(prefix),1),self.bos_id,device=prefix.device,dtype=torch.long)
        inputs=torch.cat((prefix.to(emb.weight.dtype),emb(bos)),dim=1)
        ids=self.lm.generate(inputs_embeds=inputs,attention_mask=torch.ones(inputs.shape[:2],device=inputs.device,dtype=torch.long),max_new_tokens=max_tokens,do_sample=False,use_cache=True,bos_token_id=self.bos_id,eos_token_id=self.eos_id,pad_token_id=self.eos_id)
        result=[]
        for row in ids.tolist():
            result.append(row[:row.index(self.eos_id)] if self.eos_id in row else row)
        return result

    def target_loss(self,packet,target_ids):
        # Standard HUMAN-target teacher forcing, training only. Model-authored
        # target text, paraphrases and self-generated training corpora prohibited.
        if target_ids.ndim!=2 or target_ids.shape[0]!=len(packet.latent):
            raise ValueError('target dimensions invalid')
        prefix=self.adapter(packet)
        emb=self.lm.get_input_embeddings()
        bos=torch.full((len(prefix),1),self.bos_id,device=prefix.device,dtype=torch.long)
        shifted=torch.cat((bos,target_ids[:,:-1].masked_fill(target_ids[:,:-1]==-100,self.eos_id)),dim=1)
        inputs=torch.cat((prefix.to(emb.weight.dtype),emb(shifted)),dim=1)
        mask=torch.cat((torch.ones(prefix.shape[:2],device=prefix.device,dtype=torch.long),(target_ids!=-100).long()),dim=1)
        # Target labels stay outside LM forward; history is shifted and HUMAN.
        logits=self.lm(inputs_embeds=inputs,attention_mask=mask,use_cache=False).logits[:,prefix.shape[1]:,:].float()
        return torch.nn.functional.cross_entropy(logits.flatten(0,1),target_ids.flatten(),ignore_index=-100)


def load_local_lm(model_path,provenance_path,device='cpu'):
    """No download/install; frozen pretrained component provenance is disclosed.
This manifest is NOT a claim that its pretraining was exclusively human text.
"""
    from transformers import AutoModelForCausalLM,AutoTokenizer
    p=Path(model_path)
    if not p.is_dir():
        raise FileNotFoundError('local causal decoder weights absent')
    meta=json.loads(Path(provenance_path).read_text())
    required={'model_id','revision','training_origin_disclosure','frozen_component_allowed','files'}
    if set(meta)!=required or meta['frozen_component_allowed'] is not True or not meta['training_origin_disclosure']:
        raise ValueError('explicit frozen-pretrained provenance manifest required')
    files=meta['files']
    disk_weights={f.relative_to(p).as_posix() for f in p.rglob('*') if f.is_file() and f.suffix in ('.safetensors','.bin')}
    if not disk_weights or not disk_weights.issubset(files) or 'config.json' not in files:
        raise ValueError('all model weights and config must be hash-pinned')
    from sol_translator_cache_policy_v6 import verify_manifest
    # All byte digests, cache topology, exact model+revision+filename+target
    # tuple are checked BEFORE loading. No generic hub/shared-blob whitelist.
    verify_manifest(p,provenance_path)
    tok=AutoTokenizer.from_pretrained(p,local_files_only=True,trust_remote_code=False)
    lm=AutoModelForCausalLM.from_pretrained(p,local_files_only=True,trust_remote_code=False,torch_dtype=torch.float32).to(device).eval().requires_grad_(False)
    if any(p.dtype!=torch.float32 for p in lm.parameters() if p.is_floating_point()):raise RuntimeError('full FP32 frozen LM required')
    if lm.get_input_embeddings().weight.dtype!=torch.float32 or lm.get_output_embeddings().weight.dtype!=torch.float32:raise RuntimeError('FP32 lexical/head requirement failed')
    if any(p.requires_grad for p in lm.parameters()):raise RuntimeError('LM must be frozen')
    if tok.bos_token_id is None or tok.eos_token_id is None:
        raise ValueError('constant BOS/EOS unavailable; no invented prompts')
    return lm,tok,meta


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

from sol_translator_provenance import sha
