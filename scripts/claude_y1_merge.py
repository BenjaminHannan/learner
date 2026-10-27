#!/usr/bin/env python3
"""Rebuild a merged model from a saved bm-398r adapter (Answering-from-memory thread, 2026-09-26). New file.

scripts/claude_bm398r_train.py saves OUT/adapter398r.pt (the LoRA's A and B, fp32) and OUT/merged/. Merged weights are
never pushed and are not kept after a rental (the Mac's upload is ~0.4 MB/s), so a later rental rebuilds merged/ from
the adapter with the trainer's own steps: load the base in the trainer's dtype (bf16 on CUDA, fp32 on CPU),
claude_blurt2.add_lora with the trainer's rank and alpha, copy A and B (every key must match), then
claude_bm397t_train.merge_lora, and save. It prints the merged safetensors' sha256; with --expect it compares them
with the trainer's train398r.json merged_files (report only: the same device type should give the same bytes).

  python -B scripts/claude_y1_merge.py --base BASE --adapter adapter398r.pt --out DIR [--expect train398r.json]
  python -B scripts/claude_y1_merge.py --selftest     (tiny random Llama, CPU)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_bm398r_train as R  # noqa: E402  (sealed: RANK, ALPHA, DROPOUT, _sha)


def rebuild(model, sd: dict) -> int:
    """Add the trainer's LoRA to model, fill it from sd, merge it into the base weights. Returns layers merged."""
    import torch
    import claude_blurt2 as BL
    import claude_bm397t_train as T7
    BL.add_lora(model, r=R.RANK, alpha=R.ALPHA, dropout=R.DROPOUT)
    own = {k for k in model.state_dict() if k.endswith((".A", ".B"))}
    if own != set(sd):
        raise SystemExit(f"y1_merge: adapter keys do not match (missing {len(own - set(sd))}, "
                         f"extra {len(set(sd) - own)})")
    with torch.no_grad():
        for name, mod in model.named_modules():
            if hasattr(mod, "A") and hasattr(mod, "B") and hasattr(mod, "base"):
                mod.A.copy_(sd[name + ".A"].to(mod.A.dtype))
                mod.B.copy_(sd[name + ".B"].to(mod.B.dtype))
    model.eval()
    return T7.merge_lora(model)


def selftest() -> None:
    import tempfile
    import torch
    from transformers import AutoModelForCausalLM, LlamaConfig
    import claude_blurt2 as BL
    import claude_bm397t_train as T7
    torch.manual_seed(0)
    cfg = LlamaConfig(vocab_size=64, hidden_size=32, intermediate_size=64, num_hidden_layers=2, num_attention_heads=4,
                      num_key_value_heads=2, max_position_embeddings=128)
    x = torch.randint(0, 64, (1, 12))
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        AutoModelForCausalLM.from_config(cfg).save_pretrained(d / "base")
        m = AutoModelForCausalLM.from_pretrained(d / "base")
        BL.add_lora(m, r=R.RANK, alpha=R.ALPHA, dropout=0.0)
        for mod in m.modules():
            if hasattr(mod, "B") and hasattr(mod, "base"):
                torch.nn.init.normal_(mod.B, std=0.05)
        m.eval()
        lora_out = m(input_ids=x).logits
        sd = {k: v.detach().cpu() for k, v in m.state_dict().items() if k.endswith(".A") or k.endswith(".B")}
        torch.save(sd, d / "a.pt")
        assert T7.merge_lora(m) == 8
        m.save_pretrained(d / "merged_trainer", safe_serialization=True)
        m2 = AutoModelForCausalLM.from_pretrained(d / "base")
        assert rebuild(m2, torch.load(d / "a.pt", map_location="cpu")) == 8
        assert (m2(input_ids=x).logits - lora_out).abs().max().item() < 1e-4
        m2.save_pretrained(d / "merged_rebuilt", safe_serialization=True)
        a = {p.name: R._sha(p) for p in (d / "merged_trainer").glob("*.safetensors")}
        b = {p.name: R._sha(p) for p in (d / "merged_rebuilt").glob("*.safetensors")}
        assert a and a == b, "rebuilt merge differs from the trainer's"
        bad = dict(sd)
        bad.pop(next(iter(bad)))
        try:
            rebuild(AutoModelForCausalLM.from_pretrained(d / "base"), bad)
            raise AssertionError("missing key not caught")
        except SystemExit as e:
            assert "missing 1" in str(e)
    print("selftest ok")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect", default="")
    a = ap.parse_args()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if dev == "cuda" else torch.float32
    tok = AutoTokenizer.from_pretrained(a.base)
    model = AutoModelForCausalLM.from_pretrained(a.base, dtype=dtype).to(dev)
    n = rebuild(model, torch.load(a.adapter, map_location="cpu"))
    out = Path(a.out)
    model.save_pretrained(out, safe_serialization=True)
    tok.save_pretrained(out)
    res = {"device": dev, "dtype": str(dtype), "merged_layers": n, "adapter_sha256": R._sha(Path(a.adapter)),
           "merged_files": {p.name: R._sha(p) for p in sorted(out.glob("*.safetensors"))}}
    if a.expect:
        want = json.loads(Path(a.expect).read_text(encoding="utf-8"))
        res["adapter_matches_trainer"] = res["adapter_sha256"] == want.get("adapter_sha256")
        res["merged_matches_trainer"] = res["merged_files"] == want.get("merged_files")
    print(json.dumps(res), flush=True)


if __name__ == "__main__":
    main()
