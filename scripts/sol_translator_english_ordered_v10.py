"""Ordered checkpoint admission; immutable V6 frozen FULL-FP32 LM reused.
No pretrained-table changes, raw question, templates, or synthetic training text.
"""
import torch
from sol_translator_english_v6 import FrozenEnglishDecoder,StatePrefix,load_local_lm
from sol_translator_provenance import sha
from sol_spatial_poc_ordered_v2 import CONTRACT

def validate_ordered_prefix(raw,provenance_path):
 required={'state_width','hidden','prefix_tokens','adapter_state','human_manifest_sha256','human_registry_sha256','source_state_contract','lm_provenance_sha256','training_origin','parent_sha256','reader_sha256','training_stage','input_version','order_contract'}
 if type(raw) is not dict or set(raw)!=required:raise ValueError('exact14 ordered English checkpoint keys required')
 if raw['training_origin']!='verified-human-origin-verbatim' or raw['source_state_contract']!='sol-stop-FinalLatent-v1' or raw['order_contract']!=CONTRACT or raw['input_version']!='human-notebook-ordered-v10':raise ValueError('wrong HUMAN ordered prefix boundary')
 if (raw['state_width'],raw['hidden'],raw['prefix_tokens'])!=(256,32,8):raise ValueError('changed thin-adapter architecture')
 if raw['training_stage'] not in {'ordered-joint-grounding-unqualified','ordered-night-frozen-prefix-rebound-unqualified','ordered-frozen-parent-decoder-proof-unqualified'}:raise ValueError('unknown ordered adapter training/rebinding stage')
 if raw['lm_provenance_sha256']!=sha(provenance_path):raise ValueError('wrong immutable frozen LM provenance')
 return raw

def load_ordered_english(model_path,provenance_path,adapter_path,device='cpu'):
 raw=validate_ordered_prefix(torch.load(adapter_path,map_location='cpu',weights_only=True),provenance_path)
 lm,tok,provenance=load_local_lm(model_path,provenance_path,device)
 dec=FrozenEnglishDecoder(lm,256,tok.bos_token_id,tok.eos_token_id,32,8).to(device);dec.adapter.load_state_dict(raw['adapter_state'])
 return dec,tok,provenance
