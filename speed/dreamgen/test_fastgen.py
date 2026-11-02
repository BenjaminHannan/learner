"""CPU test: tiny random Qwen3_5Moe (+ Qwen3_5 dense, + LoRA via peft with adapter off) -> fastgen greedy outputs == original Lang.generate / generate_p.
  python speed/dreamgen/test_fastgen.py"""
import sys
from pathlib import Path
import torch
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / "backbone" / "sleep" / "brain", ROOT / "backbone" / "sleep", ROOT / "backbone", Path(__file__).resolve().parent):
    sys.path.insert(0, str(p))
import fastgen  # noqa: E402
import sleep1  # noqa: E402
import sleepb  # noqa: E402
from transformers import Qwen3_5MoeForCausalLM, Qwen3_5MoeTextConfig, Qwen3_5ForCausalLM, Qwen3_5TextConfig  # noqa: E402


class Tok:  # byte-ish tokenizer; vocab 512
    pad_token_id, eos_token_id = 0, 1
    def __call__(self, t, add_special_tokens=False): return {"input_ids": [2 + (ord(c) % 250) for c in t]}
    def decode(self, ids, skip_special_tokens=True): return " ".join(str(i) for i in ids if not (skip_special_tokens and i in (0, 1)))


def tiny(kind, eos):
    torch.manual_seed(0)
    common = dict(vocab_size=512, hidden_size=64, num_attention_heads=4, num_key_value_heads=2, head_dim=16, linear_num_key_heads=2, linear_num_value_heads=4,
                  linear_key_head_dim=16, linear_value_head_dim=16, linear_conv_kernel_dim=4, max_position_embeddings=2048, eos_token_id=eos, pad_token_id=0,
                  tie_word_embeddings=False, layer_types=["linear_attention"] * 3 + ["full_attention"], num_hidden_layers=4)
    if kind == "moe":
        cfg = Qwen3_5MoeTextConfig(moe_intermediate_size=32, shared_expert_intermediate_size=32, num_experts=8, num_experts_per_tok=2, **common)
        cfg._experts_implementation = "eager"  # CPU grouped_mm is minutes slow
        return Qwen3_5MoeForCausalLM(cfg).eval()
    return Qwen3_5ForCausalLM(Qwen3_5TextConfig(intermediate_size=128, **common)).eval()


class Cnt:  # counts row-steps the model actually computes
    def __init__(s, m): s.m, s.rows, s.config = m, 0, m.config
    def generate(s, **kw):
        n0 = kw["input_ids"].shape[1]
        out = s.m.generate(**kw)
        o = out.sequences if hasattr(out, "sequences") else out
        s.rows += kw["input_ids"].shape[0] * (o.shape[1] - n0)
        return out


def prompts(n, seed=0):
    g = torch.Generator().manual_seed(seed)
    return ["".join(chr(97 + int(x)) for x in torch.randint(0, 26, (int(torch.randint(5, 60, (1,), generator=g)),), generator=g)) for _ in range(n)] + ["dup prompt"] * 3


def pick_eos(m, L, ps):  # the most common greedy token after the first one: rows then stop at different steps
    o = sleep1.Lang.generate(L, m, ps, max_new=20, bs=8)
    from collections import Counter
    c = Counter(int(t) for s in o for t in s.split()[1:])
    return c.most_common(1)[0][0]


def main():
    ok = True
    for kind in ("moe", "dense"):
        m = tiny(kind, eos=1)
        L = sleep1.Lang(Tok(), True, torch.device("cpu"))
        ps = prompts(5)
        L.eos = pick_eos(m, L, ps)
        m.generation_config.eos_token_id = L.eos
        for lora in (False, True):
            mm = m
            if lora:
                from peft import LoraConfig, get_peft_model
                mm = get_peft_model(m, LoraConfig(r=4, target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "in_proj_qkv", "out_proj"]))
                for n, p in mm.named_parameters():
                    if "lora_B" in n: torch.nn.init.normal_(p, std=0.05)
                mm.eval()
            ctx = mm.disable_adapter if lora else (lambda: __import__("contextlib").nullcontext())
            for adapter_off in ((True, False) if lora else (False,)):
                with (ctx() if adapter_off else __import__("contextlib").nullcontext()):
                    for max_new, bs, eos in ((14, 8, None), (14, 3, [L.eos, 7]), (3, 8, None)):
                        fastgen.uninstall(); fastgen.CFG.update(compact=True, seg=4, dedupe=True, pad_multiple=1)
                        a = sleep1.Lang.generate(L, Cnt(mm), ps, max_new=max_new, bs=bs, eos=eos)
                        pa = sleepb.generate_p(L, mm, ps, max_new, bs)
                        fastgen.install(sleepb, seg=4, pad_multiple=8)  # also exercise shape rounding
                        c1, c2 = Cnt(mm), Cnt(mm)
                        b = sleep1.Lang.generate(L, c1, ps, max_new=max_new, bs=bs, eos=eos)
                        pb = sleepb.generate_p(L, mm, ps, max_new, bs)
                        same = a == b and pa[0] == pb[0] and all(abs(x - y) < 1e-5 for x, y in zip(pa[1], pb[1]))
                        ok &= same
                        nrows = sum(len(x.split()) for x in a)
                        print(f"{kind} lora={lora} off={adapter_off} max_new={max_new} bs={bs} eos={eos}: identical={same}  distinct-lengths={len({len(x.split()) for x in a})}")
                        if not same:
                            for i, (x, y) in enumerate(zip(a, b)):
                                if x != y: print("  ", i, x, "|", y); break
        # row-step saving (HF computes the longest row for every row)
        fastgen.uninstall()
        c0 = Cnt(m); base = sleep1.Lang.generate(L, c0, ps, max_new=24, bs=8)
        fastgen.install(sleepb, seg=4, pad_multiple=1); c1 = Cnt(m); fast = sleep1.Lang.generate(L, c1, ps, max_new=24, bs=8)
        print(f"{kind}: row-steps original {c0.rows} -> compact {c1.rows} ({1 - c1.rows / c0.rows:.0%} fewer); same={base == fast}")
        ok &= base == fast
        # sampling: with seg >= max_new the code path is one HF generate call -> bit-identical under one seed; top_k=1-like check via seed
        fastgen.uninstall(); torch.manual_seed(5); s0 = sleep1.Lang.generate(L, m, ps[:8], max_new=12, bs=8, sample=True)
        fastgen.install(sleepb, seg=64); torch.manual_seed(5); s1 = sleep1.Lang.generate(L, m, ps[:8], max_new=12, bs=8, sample=True)
        print(f"{kind}: sampling, one segment, same seed: identical={s0 == s1}"); ok &= s0 == s1
        fastgen.uninstall()
    print("ALL OK" if ok else "FAILED")
    sys.exit(0 if ok else 1)


main()
