"""Queue-preflight numeric gradient/VRAM probe, never optimizer training.

Caller supplies exact frozen FP32 LM, candidate core, thin reader/decoder and
the sealed driver's loss callable. No corpus, language generation or files read.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import time
import torch


def probe_grounding_memory(lm, core, reader, decoder, human_loss, *, seed,
                           source_sha256, plan_sha256, cap_bytes=16*1024**3):
    if not os.environ.get("JOB") or not os.environ.get("TREE"):
        raise RuntimeError("queued preflight JOB/TREE required")
    if seed not in (0, 1):
        raise ValueError("two-seed protocol requires seed 0 or 1")
    device = lm.get_input_embeddings().weight.device
    if device.type != "cuda":
        raise ValueError("actual CUDA measurement required; no CPU surrogate")
    if any(p.requires_grad for p in lm.parameters()):
        raise ValueError("LM must remain frozen")
    if any(p.dtype != torch.float32 for p in lm.parameters() if p.is_floating_point()):
        raise ValueError("full FP32 frozen LM required, no mixed-precision fallback")
    trainable = [p for m in (core, reader, decoder.adapter) for p in m.parameters() if p.requires_grad]
    if any(p.grad is not None for p in trainable):
        raise ValueError("probe expects fresh modules with no existing gradients")
    trainable_bytes = sum(p.numel()*p.element_size() for p in trainable)
    lm_bytes = sum(p.numel()*p.element_size() for p in lm.parameters())
    free_before, total_bytes = torch.cuda.mem_get_info(device)
    limit = min(cap_bytes, total_bytes)
    torch.cuda.reset_peak_memory_stats(device)
    start = time.monotonic()
    records = []
    try:
        with torch.random.fork_rng(devices=[device.index]):
            torch.manual_seed(2026093020+seed)
            vocab = lm.get_input_embeddings().weight.shape[0]
            losses = []
            # Same retained-graph shape as batch2, 4-round candidate training.
            # Maximum sealed caps, deliberately conservative vs human target55.
            for row in range(2):
                query_ids = torch.randint(vocab, (1,49), device=device)
                notebook_ids = torch.randint(vocab, (1,256), device=device)
                targets = torch.randint(vocab, (1,64), device=device)
                qmask = torch.ones_like(query_ids, dtype=torch.bool)
                mmask = torch.ones_like(notebook_ids, dtype=torch.bool)
                with torch.no_grad():
                    e = lm.get_input_embeddings()(query_ids)
                    memo = lm.get_input_embeddings()(notebook_ids)
                latent = reader(e, qmask)
                notebook = reader(memo, mmask).flatten(1,2)
                state = core.begin_latent(latent, notebook)
                survival = torch.ones(1,device=device)
                expected = torch.zeros_like(survival)
                rounds = []
                for r in range(1,5):
                    state = core.advance_latent(state)
                    h, q = core.read_latent(state)
                    prefix = decoder.adapter.project_training(h,torch.ones_like(h,dtype=torch.bool),qmask,(1,h.shape[1]))
                    per = human_loss(lm,prefix,targets,decoder.bos_id,decoder.eos_id,True)
                    mass = survival if r == 4 else survival*q.sigmoid()
                    expected = expected + mass*(per+.001*r)
                    rounds.append({"round":r,"stop_logits":q.detach().cpu().tolist(),
                                   "selection_mass":mass.detach().cpu().tolist(),
                                   "numeric_CE":per.detach().cpu().tolist()})
                    if r < 4:
                        survival = survival*(1-q.sigmoid())
                losses.append(expected.mean()+core.auxiliary())
                records.append({"row":row,"query_ids":query_ids.cpu().tolist(),
                                "notebook_ids":notebook_ids.cpu().tolist(),
                                "labels":targets.cpu().tolist(),"rounds":rounds,
                                "query_mask":qmask.cpu().tolist(),"notebook_mask":mmask.cpu().tolist(),
                                "label_mask":torch.ones_like(targets,dtype=torch.bool).cpu().tolist()})
            torch.stack(losses).mean().backward()
            torch.cuda.synchronize(device)
            if any(p.grad is not None for p in lm.parameters()):
                raise AssertionError("frozen LM acquired gradient")
            peak_allocated = torch.cuda.max_memory_allocated(device)
            peak_reserved = torch.cuda.max_memory_reserved(device)
            # Two Adam moments plus two additional parameter-sized transient
            # buffers are a conservative inference, NOT measured optimizer work.
            inferred_optimizer_margin = 4*trainable_bytes
            safety_reserve = 512*1024**2
            passed = peak_reserved+inferred_optimizer_margin+safety_reserve <= limit
            record = {"stage":"QUEUED-NUMERIC-FULL-GRAPH-MEMORY","seed":seed,
                      "source_sha256":source_sha256,"plan_sha256":plan_sha256,
                      "probe_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      "job":os.environ["JOB"],"torch":torch.__version__,
                      "GPU":torch.cuda.get_device_name(device),"device_total_bytes":total_bytes,
                      "cap_bytes":limit,"free_before_bytes":free_before,
                      "LM_parameter_bytes":lm_bytes,"trainable_parameter_bytes":trainable_bytes,
                      "LM_embedding_dtype":str(lm.get_input_embeddings().weight.dtype),
                      "LM_head_dtype":str(lm.get_output_embeddings().weight.dtype),
                      "peak_allocated_bytes_measured":peak_allocated,
                      "peak_reserved_bytes_measured":peak_reserved,
                      "optimizer_margin_bytes_inferred_not_measured":inferred_optimizer_margin,
                      "safety_reserve_bytes":safety_reserve,"cap_guard_passed":passed,
                      "wall_seconds_measured":time.monotonic()-start,
                      "input_identity_sha256":hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest(),
                      "raw_numeric_records":records,"optimizer_steps":0,"human_examples":0,
                      "semantic_noise":"INSUFFICIENT; numeric memory compatibility only",
                      "parameter_update_performed":False,"sleep_ready":False}
            return record
    finally:
        for p in trainable:
            p.grad = None
        # Auxiliaries are transient graph caches, not weights. Prevent them
        # retaining this probe's graph or being deepcopied into a live trainer.
        for module in core.modules():
            if module.__class__.__name__ == "UpcycledMLP" and hasattr(module,"aux"):
                del module.aux
