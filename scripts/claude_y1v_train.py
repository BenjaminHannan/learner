#!/usr/bin/env python3
"""y1v training (Answering-from-memory thread, 2026-09-27): y1t's recipe (scripts/claude_bm398r_train.py, unchanged
and imported) on plain LFM2.5-1.2B-Instruct. The only difference is where the LoRA goes.

The recipe puts a rank-16 LoRA on each attention layer's q/k/v/o projections. On MiniCPM5-1B those are named
q_proj/k_proj/v_proj/o_proj in all 24 layers (96 modules). LFM2.5-1.2B has 16 layers: 6 attention layers, whose
projections are self_attn.q_proj/k_proj/v_proj/out_proj, and 10 short-convolution layers with no attention. The
unchanged trainer matches child names only, so on LFM it would find q/k/v but miss the attention output (named
out_proj there). Adding "out_proj" to the names would also catch conv.out_proj in the 10 conv layers. So here the
LoRA goes on q_proj, k_proj, v_proj and out_proj inside each self_attn block (24 modules), and nowhere else, as on
MiniCPM, where the MLP gets none. Every other setting is the trainer's own.

  python -B scripts/claude_y1v_train.py --base BASE --train train.jsonl --dev dev.jsonl --out OUT   (as the trainer)
  python -B scripts/claude_y1v_train.py --selftest   (tiny random LFM2, CPU; prints "selftest ok")
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_blurt2 as BL  # noqa: E402

ATTN_NAMES = ("q_proj", "k_proj", "v_proj", "out_proj")
_ORIG_ADD_LORA = BL.add_lora


def add_lora_attention(model, r=16, alpha=32, dropout=0.05, names=None):
    """Freeze the whole model, then put the trainer's LoRA on q/k/v/out_proj inside every self_attn block only."""
    for prm in model.parameters():
        prm.requires_grad_(False)
    n = 0
    for name, mod in list(model.named_modules()):
        if name.endswith(".self_attn"):
            _ORIG_ADD_LORA(mod, r=r, alpha=alpha, dropout=dropout, names=ATTN_NAMES)
            n += 1
    if n == 0:
        raise SystemExit("y1v: no self_attn block found; this wrapper is for LFM2")
    return model


def selftest() -> None:
    import torch
    from transformers import AutoModelForCausalLM, Lfm2Config
    import claude_bm397t_train as T7
    torch.manual_seed(0)
    cfg = Lfm2Config(vocab_size=64, hidden_size=32, intermediate_size=64, num_hidden_layers=4, num_attention_heads=4,
                     num_key_value_heads=2, max_position_embeddings=128,
                     layer_types=["conv", "full_attention", "conv", "full_attention"])
    m = AutoModelForCausalLM.from_config(cfg)
    x = torch.tensor([list(range(3, 20))])
    with torch.no_grad():
        before = m(input_ids=x).logits
    add_lora_attention(m, r=16, alpha=32, dropout=0.0)
    lora = [n for n, mod in m.named_modules() if hasattr(mod, "A") and hasattr(mod, "B") and hasattr(mod, "base")]
    train = sorted({n for n, p in m.named_parameters() if p.requires_grad})
    assert len(lora) == 8 and all(".self_attn." in n and n.split(".")[-1] in ATTN_NAMES for n in lora), lora
    assert not any(".conv." in n for n in lora), lora
    assert train and all(n.endswith(".A") or n.endswith(".B") for n in train), train
    m.eval()
    with torch.no_grad():
        assert (m(input_ids=x).logits - before).abs().max().item() < 1e-5   # B starts at zero
        for mod in m.modules():
            if hasattr(mod, "B") and hasattr(mod, "base"):
                torch.nn.init.normal_(mod.B, std=0.05)
        lora_out = m(input_ids=x).logits
        assert T7.merge_lora(m) == 8
        assert (m(input_ids=x).logits - lora_out).abs().max().item() < 1e-4
    print("selftest ok (8 LoRA modules on self_attn q/k/v/out_proj, none on conv, merge matches)")


def main() -> int:
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        return 0
    BL.add_lora = add_lora_attention     # the trainer calls BL.add_lora(model, r=..., alpha=..., dropout=...)
    import claude_bm398r_train as TR
    return TR.main()


if __name__ == "__main__":
    sys.exit(main())
