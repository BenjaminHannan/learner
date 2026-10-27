"""Read-only numeric decoder parity receipt; no loader, optimizer or file writes.
Raw logits are losslessly packed little-endian FP32 C-order/zlib/base64; outputs
are diagnostic data ONLY, never training targets. No acceptance threshold.
"""
from __future__ import annotations
import base64,hashlib,inspect,json,zlib,math
from pathlib import Path
import torch

def _sha_source(obj):
    try:
        p=Path(inspect.getfile(obj));return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    except Exception as e:return {'unavailable':type(e).__name__+': '+str(e)}

def _config(obj):
    try:return json.loads(obj.to_json_string())
    except Exception as e:return {'unavailable':type(e).__name__+': '+str(e)}

@torch.no_grad()
def probe_prefix_parity(lm,prefix,targets,bos,eos,max_tokens=16):
    if prefix.ndim!=3 or prefix.shape[:2]!=(1,8) or prefix.dtype!=torch.float32 or not bool(torch.isfinite(prefix).all()):
        raise ValueError('finite FP32 prefix[1,8,W] required')
    if targets.ndim!=2 or targets.shape[0]!=1 or not 1<=targets.shape[1]<=64 or targets.dtype!=torch.long:
        raise ValueError('human targets[1,T<=64] int64 required')
    if targets.device!=prefix.device or bool((targets<0).any()):raise ValueError('one unpadded HUMAN target row required')
    if type(bos)is not int or type(eos)is not int or type(max_tokens)is not int or not 1<=max_tokens<=16:raise ValueError('BOS/EOS integers and cap1..16 required')
    if lm.training:raise ValueError('caller must supply frozen eval LM; helper does not change training flags')
    if any(p.requires_grad for p in lm.parameters()):raise ValueError('frozen LM required')
    emb=lm.get_input_embeddings()
    if emb.weight.dtype!=torch.float32 or prefix.shape[-1]!=emb.weight.shape[-1]:raise ValueError('exact FP32 lexical width required')
    vocab=emb.weight.shape[0]
    if not 0<=bos<vocab or not 0<=eos<vocab or int(targets.max())>=vocab:raise ValueError('token bounds')
    try:
        import transformers
        tv=transformers.__version__
    except ImportError:tv='unavailable'
    report={'version':'sol-spatial-decoder-parity-v12','torch':torch.__version__,'transformers':tv,'device':str(prefix.device),'dtype':str(prefix.dtype),
      'LM_class':type(lm).__name__,'source':_sha_source(type(lm)),'generate_source':_sha_source(lm.generate),'helper_source':_sha_source(probe_prefix_parity),
      'config':_config(lm.config),'generation_config':_config(lm.generation_config),'human_target_ids':targets.cpu().tolist(),'bos':bos,'eos':eos,
      'max_tokens':max_tokens,'raw_arrays':{},'errors':{},'optimizer_updates':0,'no_acceptance_threshold':True,
      'scope':'same prefix, numeric parity only; no generated ID may become a training target; no semantic verdict'}
    arrays=report['raw_arrays']
    def pack(x):
        x=x.detach().float().cpu().contiguous();data=x.numpy().astype('<f4',copy=False).tobytes();key=hashlib.sha256(data).hexdigest()
        arrays.setdefault(key,{'shape':list(x.shape),'dtype':'little-endian-float32','order':'C','encoding':'zlib-base64','bytes':len(data),'data':base64.b64encode(zlib.compress(data)).decode()})
        return key
    def summary(x,target,keep_raw=True):
        x=x.detach().float().flatten();v,ids=torch.topk(x,min(8,len(x)));tid=int(target)
        return {'raw_array_sha256':pack(x) if keep_raw else None,'finite':bool(torch.isfinite(x).all()),'argmax':int(x.argmax()),'top8_ids':ids.cpu().tolist(),
          'top8_logits':v.cpu().tolist(),'human_target_id':tid,'human_target_logit':float(x[tid]),'human_target_rank_strict':1+int((x>x[tid]).sum()),
          'human_target_probability':float(x.softmax(-1)[tid]),'top1_minus_top2':float(v[0]-v[1])}
    def compare(a,b):
        d=(a.detach().float()-b.detach().float()).abs()
        return {'max_abs':float(d.max()),'mean_abs':float(d.mean()),'exact_equal':bool(torch.equal(a,b)),'argmax_equal':bool(torch.equal(a.argmax(-1),b.argmax(-1)))}
    def mask(n):return torch.ones((1,n),device=prefix.device,dtype=torch.long)
    def fail(name,e):report['errors'][name]={'type':type(e).__name__,'message':str(e)}
    start=torch.tensor([[bos]],device=prefix.device,dtype=torch.long)
    shifted=torch.cat((start,targets[:,:-1]),1)
    full=torch.cat((prefix,emb(shifted)),1);initial=torch.cat((prefix,emb(start)),1)
    full_logits=lm(inputs_embeds=full,attention_mask=mask(full.shape[1]),use_cache=False).logits[:,8:].float()
    first=lm(inputs_embeds=initial,attention_mask=mask(9),use_cache=False).logits[:,-1].float()
    repeat=lm(inputs_embeds=initial,attention_mask=mask(9),use_cache=False).logits[:,-1].float()
    report['prefix_raw_sha256']=pack(prefix)
    report['first_full_teacher_forcing']=summary(full_logits[:,0],targets[0,0])
    report['first_BOS_only_no_cache']=summary(first,targets[0,0]);report['repeat_BOS_only_no_cache']=summary(repeat,targets[0,0])
    report['full_vs_BOS_first']=compare(full_logits[:,0],first);report['repeat_noise']=compare(first,repeat)
    report['teacher_history_cache_vs_full']=[]
    try:
        cached=lm(inputs_embeds=initial,attention_mask=mask(9),use_cache=True)
        cache=cached.past_key_values
        if cache is None:raise RuntimeError('LM returned no past_key_values')
        for j in range(targets.shape[1]):
            if j:
                cached=lm(inputs_embeds=emb(targets[:,j-1:j]),attention_mask=mask(9+j),past_key_values=cache,use_cache=True)
                cache=cached.past_key_values
            logits=cached.logits[:,-1].float()
            report['teacher_history_cache_vs_full'].append({'target_index':j,**compare(full_logits[:,j],logits),'cached':summary(logits,targets[0,j],j==0),'full':summary(full_logits[:,j],targets[0,j],j==0)})
    except Exception as e:fail('teacher_history_incremental_cache',e)
    for requested_cache in (True,False):
        name='generate_requested_cache_'+str(requested_cache).lower()
        try:
            result=lm.generate(inputs_embeds=initial,attention_mask=mask(9),max_new_tokens=max_tokens,do_sample=False,use_cache=requested_cache,
                bos_token_id=bos,eos_token_id=eos,pad_token_id=eos,return_dict_in_generate=True,output_logits=True,output_scores=True)
            item={'sequence_ids':result.sequences.cpu().tolist(),'requested_use_cache':requested_cache,'effective_cache_not_instrumented':True,
                  'first_raw':summary(result.logits[0],targets[0,0]),'first_processed':summary(result.scores[0],targets[0,0]),
                  'first_raw_vs_BOS':compare(result.logits[0],first),'first_processed_vs_raw':compare(result.scores[0],result.logits[0])}
            report[name]=item
        except Exception as e:fail(name,e)
    generated=start;manual=[]
    try:
        for j in range(max_tokens):
            inp=torch.cat((prefix,emb(generated)),1)
            logits=lm(inputs_embeds=inp,attention_mask=mask(inp.shape[1]),use_cache=False).logits[:,-1].float()
            token=logits.argmax(-1,keepdim=True);manual.append(int(token[0,0]));generated=torch.cat((generated,token),1)
            if int(token[0,0])==eos:break
        report['manual_uncached_greedy_ids']=manual
        def trim(ids):return ids[:ids.index(eos)] if eos in ids else ids
        for name in ('generate_requested_cache_true','generate_requested_cache_false'):
            if name in report:report[name]['eos_trimmed_ids_equal_manual']=trim(report[name]['sequence_ids'][0])==trim(manual)
    except Exception as e:fail('manual_no_cache_greedy',e)
    report['logit_infinity_note']='Processed generation scores may include -Infinity masks; packed raw arrays preserve exact bytes. No silent acceptance bar.'
    def json_safe(value):
        if isinstance(value,float) and not math.isfinite(value):return str(value)
        if isinstance(value,dict):return {k:json_safe(v) for k,v in value.items()}
        if isinstance(value,list):return [json_safe(v) for v in value]
        return value
    return json_safe(report)
