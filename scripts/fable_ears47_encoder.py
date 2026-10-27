#!/usr/bin/env python3
"""Rung 2 (design 47) -- our wrapper around the borrowed SciBERT encoder.

    python fable_ears47_encoder.py --ensure            # download snapshot (huggingface_hub)
    python fable_ears47_encoder.py --check <snapshot>  # vs reference, Mac only

Why: allenai/scibert_scivocab_uncased (Apache-2.0, BERT-base) ships `pytorch_model.bin`
only, so `fable_bert_loader.load` (safetensors) cannot read it directly.  This wrapper adds
the `torch.load(weights_only=True)` path and keeps every other line ours.  The arm is void
unless `--check` prints CHECK PASS (max |hidden diff| < 1e-3 on 20 sentences).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_bert_loader as L                      # noqa: E402  (ours, read-only

MODEL_ID = "allenai/scibert_scivocab_uncased"
LICENCE = "Apache-2.0"


def ensure_snapshot() -> str:
    """Download (or reuse the cache of) the SciBERT snapshot; return its directory."""
    from huggingface_hub import snapshot_download
    p = snapshot_download(MODEL_ID,
                          allow_patterns=["*.json", "*.txt", "*.bin", "*.safetensors"])
    return p


def _load_bin_into(model: L.Bert, path: str) -> dict:
    """pytorch_model.bin -> our Bert state dict (HF BertModel naming)."""
    raw = torch.load(path, map_location="cpu", weights_only=True)
    if isinstance(raw, dict) and "state_dict" in raw and isinstance(raw["state_dict"], dict):
        raw = raw["state_dict"]
    state, skipped = {}, []
    for k, v in raw.items():
        r = L.Bert.rename(k)
        if r is None:
            skipped.append(k)
        else:
            state[r] = v.float()
    missing, unexpected = model.load_state_dict(state, strict=False)
    assert not unexpected, unexpected[:8]
    assert not [m for m in missing if not m.startswith("pos")], missing[:8]
    return {"skipped": skipped,
            "params": sum(p.numel() for p in model.parameters())}


def load(snapshot: str) -> tuple[L.Bert, L.WordPiece, dict]:
    """Load SciBERT with OUR loader: safetensors if present, else pytorch_model.bin."""
    with open(os.path.join(snapshot, "config.json")) as fh:
        cfg = json.load(fh)
    model = L.Bert(cfg)
    st_path = os.path.join(snapshot, "model.safetensors")
    bin_path = os.path.join(snapshot, "pytorch_model.bin")
    if os.path.exists(st_path):
        raw = L.read_safetensors(st_path)
        state, skipped = {}, []
        for k, v in raw.items():
            r = L.Bert.rename(k)
            (state.__setitem__(r, v.float()) if r else skipped.append(k))
        missing, unexpected = model.load_state_dict(state, strict=False)
        assert not unexpected, unexpected[:8]
        assert not [m for m in missing if not m.startswith("pos")], missing[:8]
        info = {"skipped": skipped,
                "params": sum(p.numel() for p in model.parameters()),
                "weights": "safetensors"}
    elif os.path.exists(bin_path):
        info = _load_bin_into(model, bin_path)
        info["weights"] = "pytorch_model.bin"
    else:
        raise FileNotFoundError(f"no model.safetensors or pytorch_model.bin in {snapshot}")
    tok = L.WordPiece(os.path.join(snapshot, "vocab.txt"),
                      lowercase=cfg.get("do_lower_case", True))
    return model.eval(), tok, info


def check(snapshot: str) -> None:
    """Reproduce the reference hidden states (Mac only, needs `transformers`)."""
    from transformers import AutoModel, AutoTokenizer
    ours, tok, info = load(snapshot)
    ref_tok = AutoTokenizer.from_pretrained(snapshot)
    ref = AutoModel.from_pretrained(snapshot).eval()
    worst_tok, worst = 0, 0.0
    with torch.no_grad():
        for s in L.SENTENCES:
            ids, _ = tok.encode(s, 128)
            ref_ids = ref_tok(s, truncation=True, max_length=128)["input_ids"]
            worst_tok += ids != ref_ids
            if ids != ref_ids:
                print("token mismatch:", repr(s[:40]), ids[:12], ref_ids[:12])
            x = torch.tensor([ids])
            m = torch.ones_like(x, dtype=torch.bool)
            h_ours = ours(x, m)
            h_ref = ref(input_ids=x, attention_mask=m.long()).last_hidden_state
            worst = max(worst, (h_ours - h_ref).abs().max().item())
        ids, mask, _ = tok.batch(SENTENCES_CHECK, 128)
        hb = ours(ids, mask)
        pad_diff = max(
            (hb[i, : mask[i].sum()]
             - ours(ids[i:i + 1, : mask[i].sum()], mask[i:i + 1, : mask[i].sum()])[0]
             ).abs().max().item()
            for i in range(len(SENTENCES_CHECK)))
    print(f"model {MODEL_ID}  licence {LICENCE}  weights {info['weights']}")
    print(f"params {info['params']:,}  skipped {info['skipped'][:6]}"
          f"{'...' if len(info['skipped']) > 6 else ''}")
    print(f"token mismatches {worst_tok}/{len(L.SENTENCES)}"
          f"  max|hidden diff| {worst:.2e}  pad-vs-single {pad_diff:.2e}")
    ok = worst_tok == 0 and worst < 1e-3 and pad_diff < 1e-4
    print("CHECK", "PASS" if ok else "FAIL")


SENTENCES_CHECK = L.SENTENCES[:4]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ensure", action="store_true")
    ap.add_argument("--check", metavar="SNAPSHOT_DIR")
    a = ap.parse_args()
    if a.ensure:
        print(ensure_snapshot())
    if a.check:
        check(a.check)
