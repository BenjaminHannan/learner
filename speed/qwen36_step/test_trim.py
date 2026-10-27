"""profile_step.trim_checkpoint on a tiny random Qwen3.5-MoE conditional-generation checkpoint saved in many shards (the real file layout: model.language_model.*, model.visual.*, mtp.*,
lm_head): the trimmed dir must load through train.load_model as a text-only ForCausalLM with N layers and carry the original layer 0..N-1 weights. CPU.  python test_trim.py"""
import json
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "backbone" / "sleep" / "brain"), str(HERE.parents[1] / "backbone" / "sleep"), str(HERE.parents[1] / "backbone")]
import profile_step as ps  # noqa: E402
from transformers import Qwen3_5MoeConfig, Qwen3_5MoeForConditionalGeneration  # noqa: E402
from train import load_model  # noqa: E402

tc = dict(vocab_size=512, hidden_size=64, num_hidden_layers=8, num_attention_heads=4, num_key_value_heads=2, head_dim=16, linear_num_key_heads=2, linear_num_value_heads=4,
          linear_key_head_dim=16, linear_value_head_dim=16, linear_conv_kernel_dim=4, moe_intermediate_size=32, shared_expert_intermediate_size=32, num_experts=8, num_experts_per_tok=2,
          max_position_embeddings=2048, eos_token_id=1, pad_token_id=0, tie_word_embeddings=False, layer_types=(["linear_attention"] * 3 + ["full_attention"]) * 2)
vc = dict(depth=2, hidden_size=32, intermediate_size=64, num_heads=2, out_hidden_size=64, num_position_embeddings=16)
with tempfile.TemporaryDirectory() as d:
    full, trim = Path(d) / "full", Path(d) / "trim"
    cfg = Qwen3_5MoeConfig(text_config=tc, vision_config=vc)
    torch.manual_seed(0)
    full_m = Qwen3_5MoeForConditionalGeneration(cfg).to(torch.float32)
    full_m.save_pretrained(full, max_shard_size="100KB")
    idx = json.load(open(full / "model.safetensors.index.json"))
    print("full ckpt: shards", len(set(idx["weight_map"].values())), "keys", len(idx["weight_map"]), "sample", [k for k in idx["weight_map"] if "layers.0." in k][:2])
    path, info = ps.trim_checkpoint(str(full), 4, trim)
    lm, _ = load_model(Namespace(smoke=False, model=path, revision=None, seed=0), torch.device("cpu"), torch.float32)
    ok = type(lm).__name__.endswith("ForCausalLM") and len(lm.model.layers) == 4 and lm.config.num_hidden_layers == 4
    ref = full_m.model.language_model.layers[3].self_attn.q_proj.weight
    got = lm.model.layers[3].self_attn.q_proj.weight
    ok &= bool(torch.equal(ref, got)) and bool(torch.equal(full_m.lm_head.weight, lm.lm_head.weight))
    ok &= bool(torch.equal(full_m.model.language_model.layers[0].mlp.experts.down_proj, lm.model.layers[0].mlp.experts.down_proj))
    print(json.dumps({"class": type(lm).__name__, "layers": len(lm.model.layers), "shards_used": len(info["shards"]), "of": len(set(idx["weight_map"].values())), "weights_equal": ok}))
    sys.exit(0 if ok else 1)
