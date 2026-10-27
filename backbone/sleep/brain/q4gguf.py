"""--q4-gguf: the frozen base = the dequantized official GGUF (the exact weights llama.cpp runs), for LFM3 (standalone: nothing imports this unless asked).

    iter_gguf(path)            # yields (hf_name, ggml type name, float32 tensor in the HF shape), one tensor at a time (the file is memory-mapped)
    dequant_dict(path, dtype)  # {hf_name: tensor} of every mapped tensor (bf16: ~3.5 GB for LFM3-1.7B)
    apply_gguf(lm, path, dtype=None)   # overwrites the mapped weights of lm in place (dequantized, cast to the weight's dtype); stats dict
    python q4gguf.py --verify --hf DIR_OR_REPO --gguf FILE [--out stats.json]   # real-model check: per-tensor rel Frobenius error vs the HF weights, then 2 greedy answers without / with the GGUF

Mapping (llama.cpp's lfm2/lfm3 names -> Lfm3ForCausalLM, checked against the real QAD Q4_0 file by --verify): no Q/K row permutation (lfm3 is NEOX-style rope, gguf keeps HF order), no transposes (gguf's
[in, out] shape is numpy (out, in) = torch's Linear layout); the short-conv weight is gguf [7, 2048] = numpy (2048, 7), HF Conv1d (2048, 1, 7) -> unsqueeze(1). token_embd is tied to the head (no output.weight);
rope_freqs.weight has no HF parameter (the rotary inverse frequencies are a buffer computed from the config) and is ignored, listed in stats["ignored"].
Dense storage only (LFM3 is small); there is no packed Q4_0 form.
"""
import argparse
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

# (gguf name regex, HF name template); {n} = layer index
NAME_MAP = [
    (r"token_embd\.weight", "model.embed_tokens.weight"),
    (r"output_norm\.weight", "model.embedding_norm.weight"),  # LFM2/3's HF "embedding_norm" is the final norm (verified: ~0 rel error)
    (r"output\.weight", "lm_head.weight"),  # absent in the tied official files; mapped in case an untied file comes
    (r"blk\.(\d+)\.attn_norm\.weight", "model.layers.{n}.operator_norm.weight"),
    (r"blk\.(\d+)\.ffn_norm\.weight", "model.layers.{n}.ffn_norm.weight"),
    (r"blk\.(\d+)\.post_attention_norm\.weight", "model.layers.{n}.post_operator_norm.weight"),
    (r"blk\.(\d+)\.post_ffw_norm\.weight", "model.layers.{n}.post_ffn_norm.weight"),
    (r"blk\.(\d+)\.attn_q\.weight", "model.layers.{n}.self_attn.q_proj.weight"),
    (r"blk\.(\d+)\.attn_k\.weight", "model.layers.{n}.self_attn.k_proj.weight"),
    (r"blk\.(\d+)\.attn_v\.weight", "model.layers.{n}.self_attn.v_proj.weight"),
    (r"blk\.(\d+)\.attn_output\.weight", "model.layers.{n}.self_attn.o_proj.weight"),
    (r"blk\.(\d+)\.attn_gate\.weight", "model.layers.{n}.self_attn.gate_proj.weight"),
    (r"blk\.(\d+)\.attn_q_norm\.weight", "model.layers.{n}.self_attn.q_norm.weight"),
    (r"blk\.(\d+)\.attn_k_norm\.weight", "model.layers.{n}.self_attn.k_norm.weight"),
    (r"blk\.(\d+)\.shortconv\.in_proj\.weight", "model.layers.{n}.conv.in_proj.weight"),
    (r"blk\.(\d+)\.shortconv\.out_proj\.weight", "model.layers.{n}.conv.out_proj.weight"),
    (r"blk\.(\d+)\.shortconv\.conv\.weight", "model.layers.{n}.conv.conv.weight"),
    (r"blk\.(\d+)\.ffn_gate\.weight", "model.layers.{n}.feed_forward.w1.weight"),
    (r"blk\.(\d+)\.ffn_up\.weight", "model.layers.{n}.feed_forward.w3.weight"),
    (r"blk\.(\d+)\.ffn_down\.weight", "model.layers.{n}.feed_forward.w2.weight"),
]
IGNORE = {"rope_freqs.weight"}
_RX = [(re.compile(g + "$"), h) for g, h in NAME_MAP]


def gguf_to_hf(name):
    """HF parameter name of a GGUF tensor name, or None when unmapped."""
    for rx, h in _RX:
        m = rx.match(name)
        if m:
            return h.format(n=m.group(1)) if m.groups() else h
    return None


def hf_to_gguf(name):
    """Inverse of gguf_to_hf (the synthetic-file test writer); None when no GGUF tensor maps to `name`."""
    for g, h in NAME_MAP:
        if "{n}" in h:
            m = re.match(re.escape(h).replace(r"\{n\}", r"(\d+)") + "$", name)
            if m:
                return re.sub(r"\(\\d\+\)", m.group(1), g).replace("\\.", ".").replace("$", "")
        elif h == name:
            return g.replace("\\.", ".")
    return None


def iter_gguf(path):
    """(hf_name or None, ggml type name, gguf name, float32 torch tensor in the HF layout) per GGUF tensor; the tensor is None for an IGNOREd one."""
    import gguf
    from gguf.quants import dequantize
    for t in gguf.GGUFReader(str(path)).tensors:
        hf = gguf_to_hf(t.name)
        if hf is None:
            yield None, t.tensor_type.name, t.name, None
            continue
        a = np.asarray(dequantize(t.data, t.tensor_type) if t.tensor_type not in (gguf.GGMLQuantizationType.F32, gguf.GGMLQuantizationType.F16) else t.data, dtype=np.float32)
        x = torch.from_numpy(np.array(a, dtype=np.float32))
        if t.name.endswith("shortconv.conv.weight"):
            x = x.unsqueeze(1)
        yield hf, t.tensor_type.name, t.name, x


def dequant_dict(path, dtype=torch.bfloat16):
    out = {}
    for hf, _, name, x in iter_gguf(path):
        if hf is None:
            assert name in IGNORE, f"unmapped GGUF tensor {name}"
            continue
        out[hf] = x.to(dtype)
    return out


def _spread(v):
    v = sorted(v)
    return {"min": v[0], "median": statistics.median(v), "max": v[-1]}


@torch.no_grad()
def apply_gguf(lm, path, dtype=None, per_tensor=False):
    """Overwrite, in place, every weight of lm that the GGUF holds with its dequantized values (cast to the weight's own dtype, or `dtype`). Raises ValueError, before any weight changes (names and shapes are checked first over the file's tensor table), when a GGUF tensor is unmapped (not in IGNORE), maps to no parameter, has the wrong shape, or a parameter of lm is not in the GGUF.
    Returns {file, tensors, params, by_type: {ggml type: {tensors, params, rel_fro: {min, median, max}}}, rel_fro: {...all}, ignored: [...]}; rel_fro = ||dequant - old weight|| / ||old weight||."""
    import gguf
    params = dict(lm.named_parameters())
    rd = gguf.GGUFReader(str(path))
    bad, ign, seen = [], [], set()
    for t in rd.tensors:
        hf = gguf_to_hf(t.name)
        if hf is None:
            (ign if t.name in IGNORE else bad).append(t.name if t.name in IGNORE else f"{t.name} (unmapped)")
            continue
        if hf == "lm_head.weight" and hf not in params:
            hf = "model.embed_tokens.weight"
        if hf not in params:
            bad.append(f"{t.name} -> {hf} (no such parameter)")
            continue
        shp = tuple(int(s) for s in t.shape[::-1])
        want = tuple(params[hf].shape)
        if t.name.endswith("shortconv.conv.weight"):
            shp = (shp[0], 1, shp[1])
        if shp != want:
            bad.append(f"{t.name} -> {hf}: gguf shape {shp} != parameter shape {want}")
        seen.add(hf)
    missing = [n for n in params if n not in seen and not (n == "lm_head.weight")]
    if bad or missing:
        raise ValueError("GGUF does not match the model: " + "; ".join(bad[:20]) + (f"; {len(bad) - 20} more" if len(bad) > 20 else "")
                         + (f"; parameters not in the GGUF: {missing[:20]}" if missing else ""))
    by, allr, per, n_t, n_p = defaultdict(lambda: {"tensors": 0, "params": 0, "r": []}), [], {}, 0, 0
    for hf, ty, name, x in iter_gguf(path):
        if hf is None:
            continue
        if hf == "lm_head.weight" and hf not in params:
            hf = "model.embed_tokens.weight"
        w = params[hf]
        new = x.to(dtype or w.dtype)
        r = float((new.float() - w.float()).norm() / w.float().norm().clamp_min(1e-30))
        w.data.copy_(new)
        d = by[ty]
        d["tensors"] += 1
        d["params"] += w.numel()
        d["r"].append(r)
        allr.append(r)
        n_t += 1
        n_p += w.numel()
        if per_tensor:
            per[hf] = {"type": ty, "rel_fro": r}
    return {"file": str(path), "tensors": n_t, "params": n_p, "rel_fro": _spread(allr), "ignored": ign,
            "by_type": {ty: {"tensors": d["tensors"], "params": d["params"], "rel_fro": _spread(d["r"])} for ty, d in sorted(by.items())},
            **({"per_tensor": per} if per_tensor else {})}


def verify(hf, gguf_path, out=None, prompts=("What is the capital of France? Answer in one sentence.", "Give me two tips for studying effectively."), max_new=40):
    """Real-model check on the CPU: HF bf16 weights vs the dequantized GGUF (per-tensor rel Frobenius error, type table), then greedy answers without / with the GGUF (thinking off)."""
    import time
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(hf, trust_remote_code=True)
    lm = AutoModelForCausalLM.from_pretrained(hf, dtype=torch.bfloat16, trust_remote_code=True).eval()

    def answers():
        res = []
        for q in prompts:
            text = tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
            ids = tok(text, add_special_tokens=False, return_tensors="pt")["input_ids"]
            with torch.no_grad():
                o = lm.generate(input_ids=ids, attention_mask=torch.ones_like(ids), max_new_tokens=max_new, do_sample=False, eos_token_id=tok.convert_tokens_to_ids("<|im_end|>"), pad_token_id=tok.pad_token_id)
            res.append(tok.decode(o[0, ids.shape[1]:], skip_special_tokens=True).strip())
        return res
    t0 = time.time()
    before = answers()
    print("[base]", before, f"{time.time() - t0:.0f}s", flush=True)
    stats = apply_gguf(lm, gguf_path, per_tensor=True)
    t0 = time.time()
    after = answers()
    print("[gguf]", after, f"{time.time() - t0:.0f}s", flush=True)
    for ty, d in stats["by_type"].items():
        print(f"{ty:6s} n={d['tensors']:4d} params={d['params']:>13,} rel_fro min/median/max = {d['rel_fro']['min']:.4g} / {d['rel_fro']['median']:.4g} / {d['rel_fro']['max']:.4g}")
    worst = sorted(stats["per_tensor"].items(), key=lambda kv: -kv[1]["rel_fro"])[:5]
    print("worst:", worst)
    res = {"stats": stats, "answers_base": before, "answers_gguf": after, "prompts": list(prompts)}
    if out:
        Path(out).write_text(json.dumps(res, indent=1))
    return res


def selftest(hf="LiquidAI/LFM3-1.7B"):
    """CPU unit test without the 1 GB file: a tiny random Lfm3ForCausalLM (real config + remote code, hidden 64, one conv / sliding / full layer each) -> a synthetic GGUF (Linears Q4_0, the embedding Q8_0,
    norms / conv F32, written by gguf's GGUFWriter under llama.cpp's names) -> apply_gguf into a second model: every weight equals the dequant, logits differ from the original model and equal a model whose weights
    were copied by hand from the dequant; the name map round-trips; unmapped / missing / mis-shaped tensors raise."""
    import tempfile
    import gguf
    from gguf.quants import dequantize, quantize
    from transformers import AutoConfig, AutoModelForCausalLM
    cfg = AutoConfig.from_pretrained(hf, trust_remote_code=True, hidden_size=64, intermediate_size=128, num_hidden_layers=3, layer_types=["conv", "sliding_attention", "full_attention"],
                                     num_attention_heads=4, num_key_value_heads=2, head_dim=16, vocab_size=300, pad_token_id=1, bos_token_id=2, eos_token_id=3)
    torch.manual_seed(0)
    mk = lambda: AutoModelForCausalLM.from_config(cfg, trust_remote_code=True).float().eval()
    a, b, c = mk(), mk(), mk()  # a: source; b: gets apply_gguf; c: hand copy
    assert not torch.equal(a.model.layers[0].conv.in_proj.weight, b.model.layers[0].conv.in_proj.weight)
    tmp = Path(tempfile.mkdtemp()) / "t.gguf"
    w = gguf.GGUFWriter(str(tmp), "lfm3")
    want, kinds = {}, set()
    for n, p in a.named_parameters():
        g = hf_to_gguf(n)
        assert g is not None and gguf_to_hf(g) == n, (n, g)
        x = p.detach().float().numpy()
        if n.endswith("conv.conv.weight"):
            x = x[:, 0]
        if p.ndim == 2 and n.endswith(("proj.weight", "w1.weight", "w2.weight", "w3.weight")):
            ty, q = gguf.GGMLQuantizationType.Q4_0, quantize(x, gguf.GGMLQuantizationType.Q4_0)
        elif n == "model.embed_tokens.weight":
            ty, q = gguf.GGMLQuantizationType.Q8_0, quantize(x, gguf.GGMLQuantizationType.Q8_0)
        else:
            ty, q = gguf.GGMLQuantizationType.F32, x
        w.add_tensor(g, q, raw_dtype=ty) if ty != gguf.GGMLQuantizationType.F32 else w.add_tensor(g, q)
        d = np.asarray(dequantize(q, ty), dtype=np.float32) if ty != gguf.GGMLQuantizationType.F32 else x
        want[n] = torch.from_numpy(np.ascontiguousarray(d)).reshape(p.shape if not n.endswith("conv.conv.weight") else (p.shape[0], p.shape[2])) if True else None
        if n.endswith("conv.conv.weight"):
            want[n] = want[n].unsqueeze(1)
        kinds.add(ty.name)
    w.add_tensor("rope_freqs.weight", np.ones(8, dtype=np.float32))
    w.write_header_to_file(); w.write_kv_data_to_file(); w.write_tensors_to_file(); w.close()
    ids = torch.randint(0, 300, (2, 12))
    with torch.no_grad():
        lo_a = a(ids).logits
        lo_b0 = b(ids).logits
        st = apply_gguf(b, tmp)
        lo_b = b(ids).logits
        for n, p in c.named_parameters():
            p.copy_(want[n])
        lo_c = c(ids).logits
    assert kinds == {"Q4_0", "Q8_0", "F32"} and st["tensors"] == len(want) and st["ignored"] == ["rope_freqs.weight"], (kinds, st)
    for n, p in b.named_parameters():
        assert torch.equal(p, want[n]), (n, (p - want[n]).abs().max(), p.dtype, want[n].dtype)
    assert torch.equal(lo_b, lo_c) and not torch.equal(lo_b, lo_b0) and not torch.equal(lo_b, lo_a)  # = hand copy; differs from the old weights and from the full-precision source
    import copy
    st2 = apply_gguf(copy.deepcopy(a), tmp)  # onto the source model itself: the stat is then the pure quantization error (random weights: Q4_0 ~ 0.1, F32 exactly 0)
    assert 0 < st2["by_type"]["Q4_0"]["rel_fro"]["max"] < 0.25 and st2["by_type"]["F32"]["rel_fro"]["max"] == 0 and 0 < st2["by_type"]["Q8_0"]["rel_fro"]["max"] < 0.02, st2
    b16 = mk().to(torch.bfloat16)
    apply_gguf(b16, tmp)  # model dtype bf16: the weights are the dequant cast to bf16
    assert all(torch.equal(p, want[n].to(torch.bfloat16)) for n, p in b16.named_parameters())
    # errors: unmapped tensor, missing parameter, wrong shape
    def bad(fn, msg):
        p2 = tmp.with_name("bad.gguf")
        w2 = gguf.GGUFWriter(str(p2), "lfm3")
        fn(w2)
        w2.write_header_to_file(); w2.write_kv_data_to_file(); w2.write_tensors_to_file(); w2.close()
        try:
            apply_gguf(mk(), p2)
        except ValueError as e:
            assert msg in str(e), (msg, str(e)[:300])
            return
        raise AssertionError("no error: " + msg)
    rd = gguf.GGUFReader(str(tmp))
    full = [(t.name, np.array(t.data), t.tensor_type) for t in rd.tensors]
    put = lambda w2, items: [w2.add_tensor(n, x, raw_dtype=ty) if ty not in (gguf.GGMLQuantizationType.F32,) else w2.add_tensor(n, x) for n, x, ty in items]
    bad(lambda w2: put(w2, full + [("blk.0.mystery.weight", np.zeros(4, np.float32), gguf.GGMLQuantizationType.F32)]), "unmapped")
    bad(lambda w2: put(w2, full[1:]), "not in the GGUF")
    bad(lambda w2: put(w2, [(n, x[:-1] if n == "output_norm.weight" else x, ty) for n, x, ty in full]), "shape")
    return {"kinds": sorted(kinds), "tensors": st["tensors"], "by_type_vs_source": st2["by_type"]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="CPU unit test on a tiny model and a synthetic GGUF (needs the LFM3 config from the Hub)")
    ap.add_argument("--hf", help="HF LFM3 repo id or local dir (bf16 safetensors)")
    ap.add_argument("--gguf", help="the GGUF file")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.selftest:
        print(json.dumps(selftest(a.hf or "LiquidAI/LFM3-1.7B"), indent=1))
        raise SystemExit
    if not a.verify or not a.hf or not a.gguf:
        ap.error("--verify --hf and --gguf are required")
    verify(a.hf, a.gguf, a.out)
