#!/usr/bin/env python3
"""Post-FAIL diagnosis only (not the registered run): is the 3.07e-4 gap the
attention backend (sdpa default vs eager) or a real modeling error?"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
sys.path.insert(0, "scripts")
from fable_bert_loader import SENTENCES
from fable_modernbert58_loader import load
import torch
from transformers import AutoModel, AutoTokenizer

SNAP = "/Users/ben-hannan/.cache/huggingface/hub/models--answerdotai--ModernBERT-base/snapshots/8949b909ec900327062f0ebf497f51aef5e6f0c8"
ours, tok, _ = load(SNAP)
ref_tok = AutoTokenizer.from_pretrained(SNAP)
ref_def = AutoModel.from_pretrained(SNAP).eval()
print("default backend:", ref_def.config._attn_implementation)
ref_eager = AutoModel.from_pretrained(SNAP, attn_implementation="eager").eval()
with torch.no_grad():
    w_def, w_eager, w_de = 0.0, 0.0, 0.0
    arg_def = arg_eager = None
    for s in SENTENCES:
        ids, _ = tok.encode(s, 128)
        x = torch.tensor([ids]); m = torch.ones_like(x, dtype=torch.bool)
        h_ours = ours(x, m)
        h_def = ref_def(input_ids=x, attention_mask=m.long()).last_hidden_state
        h_eag = ref_eager(input_ids=x, attention_mask=m.long()).last_hidden_state
        d1 = (h_ours - h_def).abs().max().item()
        d2 = (h_ours - h_eag).abs().max().item()
        d3 = (h_def - h_eag).abs().max().item()
        if d1 > w_def: w_def, arg_def = d1, s[:40]
        if d2 > w_eager: w_eager, arg_eager = d2, s[:40]
        w_de = max(w_de, d3)
print(f"ours-vs-default worst {w_def:.2e} at {arg_def!r}")
print(f"ours-vs-eager   worst {w_eager:.2e} at {arg_eager!r}")
print(f"default-vs-eager worst {w_de:.2e}")
