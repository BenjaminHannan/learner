#!/usr/bin/env python3
"""One copy of MiniCPM5-1B for both the reader (listener) and the mouth (Ben 2026-09-23 19:02: "or maybe
we could have the same model?").

Both are LoRA fine-tunes of the same base, so the base is loaded once and each turn switches the active
adapter: "reader" to read the user's turn, "mouth" to say the reply.

Library:
    sm = SharedBase(base_dir, reader_adapter, mouth_adapter)
    frame, confs, raw, ms = sm.read(turn, prev_reply)
    text, info = sm.say(record, user_turn, tag)
If a run kept only its merged model, recover an exact adapter first (the merged weights differ from
the base by a rank-r product, so an SVD at rank r gives it back up to rounding):
    python claude_own_shared_base.py extract --base BASE --merged MERGED --out ADAPTER_DIR [--rank 32]
Check that sharing changes nothing and measure speed:
    python claude_own_shared_base.py check --base BASE --reader-merged M1 --reader-adapter A1
        --mouth-merged M2 --mouth-adapter A2 --reader-rows ROWS.jsonl --mouth-rows DEV.jsonl [--limit 50]
    prints: identical greedy outputs (reader, mouth), ms per call shared vs separate, resident GB.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch
from safetensors.torch import load_file, save_file

sys.path.insert(0, str(Path(__file__).resolve().parent))

TARGETS = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")


def _load_weights(d):
    d = Path(d)
    out = {}
    for f in sorted(d.glob("*.safetensors")):
        out.update(load_file(str(f)))
    return out


def extract_adapter(base_dir, merged_dir, out_dir, rank=32):
    """Write a PEFT LoRA adapter whose B@A equals merged - base for every target linear layer."""
    base, merged = _load_weights(base_dir), _load_weights(merged_dir)
    tensors, worst = {}, 0.0
    for k, w in base.items():
        if not k.endswith(".weight") or k.split(".")[-2] not in TARGETS:
            continue
        delta = merged[k].float() - w.float()
        U, S, Vh = torch.linalg.svd(delta, full_matrices=False)
        r = min(rank, S.numel())
        B = U[:, :r] * S[:r].sqrt()
        A = S[:r].sqrt()[:, None] * Vh[:r]
        rel = ((B @ A - delta).norm() / (delta.norm() + 1e-12)).item()
        worst = max(worst, rel)
        stem = "base_model.model." + k[: -len(".weight")]
        tensors[stem + ".lora_A.weight"] = A.contiguous().to(torch.float32)
        tensors[stem + ".lora_B.weight"] = B.contiguous().to(torch.float32)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    save_file(tensors, str(out / "adapter_model.safetensors"))
    cfg = {"peft_type": "LORA", "task_type": "CAUSAL_LM", "r": rank, "lora_alpha": rank, "lora_dropout": 0.0,
           "target_modules": list(TARGETS), "bias": "none", "base_model_name_or_path": str(base_dir),
           "fan_in_fan_out": False, "inference_mode": True}
    (out / "adapter_config.json").write_text(json.dumps(cfg, indent=1))
    return {"layers": len(tensors) // 2, "worst_relative_error": worst}


class SharedBase:
    def __init__(self, base_dir, reader_adapter, mouth_adapter, device=None, samples=4):
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from claude_lis300_read import Reader
        from claude_own_m1_speak import Mouth
        self.dev = device or ("cuda" if torch.cuda.is_available() else
                              "mps" if torch.backends.mps.is_available() else "cpu")
        dtype = torch.float32 if self.dev == "cpu" else torch.bfloat16 if self.dev == "cuda" else torch.float16
        tok = AutoTokenizer.from_pretrained(base_dir)
        base = AutoModelForCausalLM.from_pretrained(base_dir, dtype=dtype)
        model = PeftModel.from_pretrained(base, reader_adapter, adapter_name="reader")
        model.load_adapter(mouth_adapter, adapter_name="mouth")
        self.model = model.to(self.dev).eval()
        # reuse the sealed reader/mouth logic unchanged, pointed at the shared model
        self.reader = Reader.__new__(Reader)
        self.reader.dev, self.reader.tok, self.reader.model, self.reader.max_new = self.dev, tok, self.model, 200
        self.mouth = Mouth.__new__(Mouth)
        self.mouth.dev, self.mouth.tok, self.mouth.model = self.dev, tok, self.model
        self.mouth.samples, self.mouth.max_new = samples, 60

    def read(self, turn, prev_reply=""):
        self.model.set_adapter("reader")
        return self.reader.read(turn, prev_reply)

    def say(self, record, user_turn, tag):
        self.model.set_adapter("mouth")
        return self.mouth.say(record, user_turn, tag)


def _rss_gb():
    try:
        import resource
        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return round(r / (1024 ** 3 if sys.platform == "darwin" else 1024 ** 2), 2)
    except Exception:
        return None


def check(a):
    from claude_lis300_read import Reader
    from claude_own_m1_speak import Mouth
    rrows = [json.loads(l) for l in Path(a.reader_rows).read_text().splitlines() if l.strip()][: a.limit]
    mrows = [json.loads(l) for l in Path(a.mouth_rows).read_text().splitlines() if l.strip()][: a.limit]
    sm = SharedBase(a.base, a.reader_adapter, a.mouth_adapter, samples=0)
    torch.manual_seed(0)
    t0 = time.perf_counter()
    sh_r = [sm.read(r["turn"], r.get("prev_reply", ""))[2] for r in rrows]
    t1 = time.perf_counter()
    sh_m = [sm.say(r["record"], r.get("user_turn", ""), r["tag"])[1]["raw"][0] for r in mrows]
    t2 = time.perf_counter()
    shared_gb = _rss_gb()
    del sm
    rd = Reader(a.reader_merged)
    t3 = time.perf_counter()
    se_r = [rd.read(r["turn"], r.get("prev_reply", ""))[2] for r in rrows]
    t4 = time.perf_counter()
    del rd
    mo = Mouth(a.mouth_merged, samples=0)
    t5 = time.perf_counter()
    se_m = [mo.say(r["record"], r.get("user_turn", ""), r["tag"])[1]["raw"][0] for r in mrows]
    t6 = time.perf_counter()
    n_r, n_m = max(1, len(rrows)), max(1, len(mrows))
    print(json.dumps({
        "reader_identical": sum(x == y for x, y in zip(sh_r, se_r)), "reader_rows": len(rrows),
        "mouth_identical": sum(x == y for x, y in zip(sh_m, se_m)), "mouth_rows": len(mrows),
        "ms_read_shared": round((t1 - t0) * 1000 / n_r, 1), "ms_read_separate": round((t4 - t3) * 1000 / n_r, 1),
        "ms_say_shared": round((t2 - t1) * 1000 / n_m, 1), "ms_say_separate": round((t6 - t5) * 1000 / n_m, 1),
        "peak_rss_gb_after_shared": shared_gb, "peak_rss_gb_end": _rss_gb()}))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("--base", required=True)
    e.add_argument("--merged", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--rank", type=int, default=32)
    c = sub.add_parser("check")
    for k in ("base", "reader-merged", "reader-adapter", "mouth-merged", "mouth-adapter", "reader-rows", "mouth-rows"):
        c.add_argument("--" + k, required=True)
    c.add_argument("--limit", type=int, default=50)
    a = ap.parse_args()
    if a.cmd == "extract":
        print(json.dumps(extract_adapter(a.base, a.merged, a.out, a.rank)))
    else:
        check(a)


if __name__ == "__main__":
    main()
