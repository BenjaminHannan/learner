"""Frozen ordered state/control extraction; output-only canonical FinalLatent."""
import copy,torch
from pathlib import Path
from sol_translator_grounding_v6 import HumanInputProjection,question_notebook_tokens
from sol_translator_provenance import sha
from sol_translator_proof_v6 import final_digest
from sol_translator_decoder import FinalLatent,validate_final
from sol_spatial_poc_ordered_v2 import load_ordered_bundle,CONTRACT,position_codes
from scripts.sol_stop_ordered_api2 import make_ordered_fixed4_executor

def read_source(a,lm):
 raw=torch.load(a.reader,map_location='cpu',weights_only=True)
 if raw.get('input_version')!='human-notebook-ordered-v10' or raw.get('order_contract')!=CONTRACT or raw.get('training_origin')!='verified-human-origin':raise ValueError('actual HUMAN ordered reader required')
 if raw['human_manifest_sha256']!=sha(Path(a.corpus)/'pairs.json'):raise ValueError('reader/corpus mismatch')
 reader=HumanInputProjection(raw['lm_width']).to(a.device);reader.load_state_dict(raw['state_dict']);reader.eval().requires_grad_(False)
 core,meta=load_ordered_bundle(a.parent,a.device)
 if meta.get('order_contract')!=CONTRACT or meta.get('human_manifest_sha256')!=raw['human_manifest_sha256']:raise ValueError('ordered parent/reader binding')
 core.eval().requires_grad_(False)
 return reader,core,make_ordered_fixed4_executor(core)

@torch.no_grad()
def state_for(row,a,lm,tok,reader,executor):
 ids,mask,mids,mmask=question_notebook_tokens(tok,row,a.device,max_context=512)
 q=reader(lm.get_input_embeddings()(ids),mask).detach().flatten(1,2);m=reader(lm.get_input_embeddings()(mids),mmask).detach().flatten(1,2)
 account={'id':row['id'],'input_ids':ids.cpu().tolist(),'input_mask':mask.cpu().tolist(),'notebook_ids':mids.cpu().tolist(),'notebook_mask':mmask.cpu().tolist(),'source':a.arm,'order_contract':CONTRACT,'notebook_cap':512,'position_information':'same absolute numeric positions and query/book roles as native core; no reader position duplication'}
 if a.arm=='embedding':
  qp=torch.arange(q.shape[1],device=q.device,dtype=torch.long)[None];mp=torch.arange(m.shape[1],device=m.device,dtype=torch.long)[None]
  h=torch.cat((q+position_codes(executor.core,qp,0),m+position_codes(executor.core,mp,1)),1)
  f=FinalLatent(h,torch.ones_like(h,dtype=torch.bool),torch.ones(h.shape[:2],device=h.device,dtype=torch.bool),(1,h.shape[1]));account['geometry_limit']='all query+context vs real final query only; strong retained-input control'
 elif a.arm=='no_state':f=FinalLatent(torch.zeros_like(q),torch.ones_like(q,dtype=torch.bool),mask,(1,q.shape[1]))
 else:
  result=executor.execute_embeddings(q,mask,(1,q.shape[1]),query_mask=mask,notebook_latents=m,notebook_mask=mmask,policy='fixed',cap=4,compact=True);f=result.final
  account.update(selected_row_rounds=result.audit.selected_row_rounds,executed_row_rounds=result.audit.executed_row_rounds,work=result.audit.work,core_sha256=result.audit.core_sha256)
  if f.latent.shape[1]!=q.shape[1]:raise ValueError('notebook cannot reach output decoder')
 validate_final(f);account['final_sha256']=final_digest(f);return f,account
