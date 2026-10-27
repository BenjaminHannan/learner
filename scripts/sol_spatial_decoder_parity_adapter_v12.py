"""Canonical FinalLatent wrapper for the immutable prefix parity helper."""
import torch
from sol_spatial_decoder_parity_v12 import probe_prefix_parity

@torch.no_grad()
def probe_decoder_parity(decoder,packet,target_ids,max_new_tokens=16):
    # This is the exact normal inference adapter path; no raw question/notebook.
    # Caller must supply frozen eval LM. No flags/weights are changed here.
    prefix=decoder.adapter(packet)
    return probe_prefix_parity(decoder.lm,prefix,target_ids,decoder.bos_id,
                               decoder.eos_id,max_tokens=max_new_tokens)
