#!/usr/bin/env python3
"""rd-378L addendum D: rebuild the rd-378 note writer on a rental from its own LoRA adapter (Trustworthy notes, 09-26).

rd-378L's registered writer is the rd-378 merged model, model.safetensors sha256 WANT below (trained on BensPC by
claude_lis300_train.py --merge). The merged model is 2.1 GB and the Mac uploads ~0.4 MB/s; its adapter (OUT/adapter of
the same run) is ~90 MB. This merges that adapter onto the same base exactly as claude_lis300_train.py did (bf16 on
cuda, gradient checkpointing + input grads enabled, PEFT merge_and_unload, save_pretrained with safetensors, the
base's tokenizer) and hashes the result. A different hash means it is NOT the registered writer: exit 3, never use it.

python claude_rd378L_rebuild.py --base BASE --adapter ADAPTER_DIR --out MERGED_DIR [--want SHA256]
  prints one JSON line {"sha256", "match", "torch", "transformers", "peft", "gpu"}; exit 0 on match, 3 on mismatch.
python claude_rd378L_rebuild.py selftest   (CPU, tiny random model: the merge path runs and is deterministic)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

WANT = "dbcc8db5a5840d839fe049f720bdfeacf094deb78f2652984c28c53f8c388510"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rebuild(base, adapter, out, dev):
    """claude_lis300_train.py's load and --merge path, minus training: same dtype, device and calls."""
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    dtype = torch.bfloat16 if dev == "cuda" else torch.float32
    tok = AutoTokenizer.from_pretrained(base)
    model = AutoModelForCausalLM.from_pretrained(base, dtype=dtype).to(dev)
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    merged = model.merge_and_unload()
    merged.save_pretrained(Path(out), safe_serialization=True)
    tok.save_pretrained(Path(out))
    return sha256(Path(out) / "model.safetensors")


def selftest():
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoTokenizer, LlamaConfig, LlamaForCausalLM, PreTrainedTokenizerFast
    from tokenizers import Tokenizer, models, pre_tokenizers

    ok = {}
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        torch.manual_seed(0)
        cfg = LlamaConfig(vocab_size=64, hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                          num_attention_heads=4, num_key_value_heads=4, max_position_embeddings=64)
        LlamaForCausalLM(cfg).save_pretrained(d / "base", safe_serialization=True)
        raw = Tokenizer(models.WordLevel({f"w{i}": i for i in range(64)}, unk_token="w0"))
        raw.pre_tokenizer = pre_tokenizers.Whitespace()
        PreTrainedTokenizerFast(tokenizer_object=raw, unk_token="w0").save_pretrained(d / "base")
        m = get_peft_model(LlamaForCausalLM.from_pretrained(d / "base"), LoraConfig(
            r=4, lora_alpha=8, target_modules=["q_proj", "v_proj", "down_proj"], task_type="CAUSAL_LM"))
        with torch.no_grad():
            for n, p in m.named_parameters():
                if "lora_B" in n:
                    p.normal_(0, 0.1)
        m.save_pretrained(d / "adapter")
        want = m.merge_and_unload().state_dict()
        h1 = rebuild(d / "base", d / "adapter", d / "m1", "cpu")
        h2 = rebuild(d / "base", d / "adapter", d / "m2", "cpu")
        got = LlamaForCausalLM.from_pretrained(d / "m1").state_dict()
        ok["deterministic"] = h1 == h2
        ok["weights_equal_direct_merge"] = all(torch.equal(want[k], got[k]) for k in want if k in got)
        ok["base_changed"] = not torch.equal(
            LlamaForCausalLM.from_pretrained(d / "base").state_dict()["model.layers.0.self_attn.q_proj.weight"],
            got["model.layers.0.self_attn.q_proj.weight"])
        ok["tokenizer_saved"] = AutoTokenizer.from_pretrained(d / "m1").vocab_size == 64
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("RD378L-REBUILD-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL"))
    return 0 if all(ok.values()) else 1


def main():
    if sys.argv[1:] == ["selftest"]:
        return selftest()
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--want", default=WANT)
    a = ap.parse_args()
    import peft
    import torch
    import transformers

    if not torch.cuda.is_available():
        print(json.dumps({"error": "no cuda: the registered writer was merged in bf16 on cuda"}))
        return 2
    got = rebuild(a.base, a.adapter, a.out, "cuda")
    print(json.dumps({"sha256": got, "match": got == a.want, "torch": torch.__version__,
                      "transformers": transformers.__version__, "peft": peft.__version__,
                      "gpu": torch.cuda.get_device_name(0)}))
    return 0 if got == a.want else 3


if __name__ == "__main__":
    sys.exit(main())
