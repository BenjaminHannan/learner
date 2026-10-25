"""CPU wiring tests on a tiny random qwen3_5: python backbone/test_wiring.py  (also: --real PATH checks a real checkpoint)."""
import argparse, sys
from pathlib import Path
import torch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import train as T


def tiny():
    ns = argparse.Namespace(smoke=True, seed=0, model="")
    return T.load_model(ns, torch.device("cpu"), torch.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", default=None)
    a = ap.parse_args()
    lm, tok = tiny()
    torch.nn.init.normal_(lm.model.embed_tokens.weight, std=1.0)  # tied head: makes the random model's outputs token-dependent
    r = T.Runner(lm, loops=1)
    print("default loop block", r.start, "order", T.block_order(8, r.start, 3))
    g = torch.Generator().manual_seed(0)
    seqs = [torch.randint(4, 200, (n,), generator=g).tolist() for n in (11, 17, 6)]
    # 1. loops=1 hidden path == HF forward
    ids, mask = T.right_pad(seqs)
    pos = (mask.cumsum(1) - 1).clamp(min=0)
    with torch.no_grad():
        mine = r.logits(r.hidden(ids, mask, pos))
        ref = lm(input_ids=ids, attention_mask=mask).logits
    err = ((mine - ref) * mask[..., None]).abs().max().item()
    print("1. runner vs HF forward max abs diff (real positions):", err); assert err < 1e-4
    # 2. cached == cache-free greedy, loops 1 and 3, mixed lengths (left padding)
    eos = tok.eos_token_id
    for loops in (1, 3):
        r.loops = loops
        c = T.greedy(r, seqs, torch.device("cpu"), eos, cache=True)
        n = T.greedy(r, seqs, torch.device("cpu"), eos, cache=False)
        s = [T.greedy(r, [q], torch.device("cpu"), eos, cache=False)[0] for q in seqs]
        print(f"2. loops={loops}: cached == uncached: {c == n}; batch == single: {n == s}", c[0][:6])
        print('   distinct generated tokens:', len({t for x in c for t in x}))
        assert c == n and n == s
    # 3. loops change the output
    r.loops = 1; l1 = r.logits(r.hidden(ids, mask, pos)); r.loops = 3; l3 = r.logits(r.hidden(ids, mask, pos))
    d = (l1 - l3).abs().max().item(); print("3. loops 1 vs 3 logit diff", d); assert d > 1e-3
    # 4. LoRA target regex hits every linear projection of every layer, nothing else
    from peft import LoraConfig, get_peft_model
    pm = get_peft_model(lm, LoraConfig(r=4, lora_alpha=8, target_modules=T.LORA_TARGETS))
    names = sorted(n for n, m in pm.named_modules() if hasattr(m, "lora_A") and len(getattr(m, "lora_A", {})))
    print("4. LoRA modules:", len(names), "e.g.", names[0], names[-1])
    others = [n for n, m in lm.named_modules() if isinstance(m, torch.nn.Linear) and "lora" not in n and "base_layer" not in n]
    print("   linear layers left without LoRA:", others)
    # 5. gradients flow through the loop to LoRA params
    r.lm = pm.base_model.model; r.loops = 3; r.checkpoint = True
    loss, n = T.answer_loss_sum(r, [(seqs[0], [5, 6, 1]), (seqs[1], [7, 1])], torch.device("cpu"))
    (loss / n).backward()
    gs = [p.grad is not None and p.grad.abs().sum() > 0 for k, p in pm.named_parameters() if p.requires_grad]
    print("5. grads present on", sum(map(bool, gs)), "of", len(gs), "LoRA tensors (lora_B-only nonzero at init is expected)")
    if a.real:
        from transformers import AutoModelForCausalLM
        m = AutoModelForCausalLM.from_pretrained(a.real, dtype=torch.float32)
        print("6. real model:", type(m).__name__, sum(p.numel() for p in m.parameters()) / 1e6, "M params")
        pm = get_peft_model(m, LoraConfig(r=16, lora_alpha=32, target_modules=T.LORA_TARGETS))
        pm.print_trainable_parameters()
        left = [n for n, mod in m.named_modules() if isinstance(mod, torch.nn.Linear) and "lora" not in n and "base_layer" not in n]
        print("   linear layers left without LoRA:", left)
    print("ALL OK")


if __name__ == "__main__":
    main()
