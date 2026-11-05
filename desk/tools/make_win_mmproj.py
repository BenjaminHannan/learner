r"""Glim's eyes for llama.cpp (Windows, Nov 4): SigLIP2-base-patch16-256 vision tower + Glim's vision projector as ONE mmproj GGUF.

llama.cpp's projector type "d1omni_v" is: SigLIP ViT -> pixel-unshuffle 2x2 (4 neighbouring patches side by side, 4 x 768) -> fc1 ->
exact GELU -> fc2. Glim's eyes are: SigLIP ViT -> 2x2 AVERAGE pool (768) -> fc1 (768 -> 3072) -> exact GELU -> fc2 (3072 -> 3072).
Averaging is linear, so  fc1(avg(a,b,c,d)) = [W1/4 W1/4 W1/4 W1/4] . [a;b;c;d] + b1 : the pooled projector becomes the unshuffle
projector exactly, with fc1's weight tiled 4 times and divided by 4 (the order of the 4 neighbours does not matter: all blocks are equal).
Tiling is turned off (preproc_max_tiles 1) and the app sends 256 x 256 pictures, so every picture is 16 x 16 patches -> 64 tokens,
like training (premonition-projectors scripts/mm.py: RGB, 256 x 256 bicubic, (x/255 - 0.5)/0.5).

usage: python -I make_win_mmproj.py <siglip2 vision dir> <vision_projector.safetensors> <out.gguf>
needs: pip install gguf numpy
"""
import json
import struct
import sys

import numpy as np
import gguf


def read_safetensors(path):
    """name -> float32 array (bf16 / f16 / f32), without torch."""
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        head = json.loads(f.read(n))
        base = 8 + n
        out = {}
        for k, v in head.items():
            if k == "__metadata__":
                continue
            s, e = v["data_offsets"]
            f.seek(base + s)
            raw = f.read(e - s)
            dt = v["dtype"]
            if dt == "BF16":
                a = (np.frombuffer(raw, dtype="<u2").astype(np.uint32) << 16).view(np.float32)
            elif dt == "F16":
                a = np.frombuffer(raw, dtype="<f2").astype(np.float32)
            elif dt == "F32":
                a = np.frombuffer(raw, dtype="<f4").copy()
            else:
                raise ValueError("unsupported dtype %s for %s" % (dt, k))
            out[k] = a.reshape(v["shape"])
    return out


def main(vision_dir, projector_path, out_path):
    cfg = json.load(open(vision_dir + "/config.json"))
    V = read_safetensors(vision_dir + "/model.safetensors")
    P = read_safetensors(projector_path)
    D, F, L, H = cfg["hidden_size"], cfg["intermediate_size"], cfg["num_hidden_layers"], cfg["num_attention_heads"]
    assert P["fc1.weight"].shape == (3072, D) and P["fc2.weight"].shape == (3072, 3072), "unexpected projector shape"

    w = gguf.GGUFWriter(out_path, "clip")
    w.add_string("general.name", "Glim eyes: SigLIP2-base-patch16-256 + Glim vision projector v1")
    w.add_string("general.description", "pooled 2x2 projector folded into a d1omni_v unshuffle projector; 64 tokens per 256x256 picture")
    w.add_uint32("general.file_type", 1)
    w.add_bool("clip.has_vision_encoder", True)
    w.add_bool("clip.has_audio_encoder", False)
    w.add_string("clip.projector_type", "d1omni_v")
    w.add_bool("clip.use_gelu", True)                 # SigLIP's own MLP: gelu_pytorch_tanh
    w.add_uint32("clip.vision.image_size", cfg["image_size"])
    w.add_uint32("clip.vision.patch_size", cfg["patch_size"])
    w.add_uint32("clip.vision.embedding_length", D)
    w.add_uint32("clip.vision.feed_forward_length", F)
    w.add_uint32("clip.vision.block_count", L)
    w.add_uint32("clip.vision.attention.head_count", H)
    w.add_float32("clip.vision.attention.layer_norm_epsilon", cfg["layer_norm_eps"])
    w.add_uint32("clip.vision.projection_dim", 3072)
    w.add_array("clip.vision.image_mean", [float(x) for x in cfg["image_mean"]])
    w.add_array("clip.vision.image_std", [float(x) for x in cfg["image_std"]])
    w.add_uint32("clip.vision.projector.scale_factor", 2)
    w.add_string("clip.vision.image_resize_algo", "bicubic")
    w.add_uint32("clip.vision.preproc_min_tiles", 1)
    w.add_uint32("clip.vision.preproc_max_tiles", 1)
    w.add_uint32("clip.vision.preproc_tile_size", 512)
    w.add_float32("clip.vision.preproc_max_pixels_tolerance", 2.0)

    def t(name, a, f16=True):
        a = np.ascontiguousarray(a, dtype=np.float16 if (f16 and a.ndim >= 2) else np.float32)
        w.add_tensor(name, a)

    pre = "vision_model."
    t("v.patch_embd.weight", V[pre + "embeddings.patch_embedding.weight"])
    t("v.patch_embd.bias", V[pre + "embeddings.patch_embedding.bias"])
    t("v.position_embd.weight", V[pre + "embeddings.position_embedding.weight"], f16=False)
    for i in range(L):
        b = pre + "encoder.layers.%d." % i
        for hf, gg in (("self_attn.q_proj", "attn_q"), ("self_attn.k_proj", "attn_k"), ("self_attn.v_proj", "attn_v"),
                       ("self_attn.out_proj", "attn_out"), ("mlp.fc1", "ffn_up"), ("mlp.fc2", "ffn_down"),
                       ("layer_norm1", "ln1"), ("layer_norm2", "ln2")):
            t("v.blk.%d.%s.weight" % (i, gg), V[b + hf + ".weight"])
            t("v.blk.%d.%s.bias" % (i, gg), V[b + hf + ".bias"])
    t("v.post_ln.weight", V[pre + "post_layernorm.weight"])
    t("v.post_ln.bias", V[pre + "post_layernorm.bias"])
    # the fold: avg-pool 2x2 then fc1  ==  unshuffle 2x2 then [W1/4 x 4]
    t("mm.1.weight", np.concatenate([P["fc1.weight"] / 4.0] * 4, axis=1))
    t("mm.1.bias", P["fc1.bias"])
    t("mm.2.weight", P["fc2.weight"])
    t("mm.2.bias", P["fc2.bias"])

    w.write_header_to_file()
    w.write_kv_data_to_file()
    w.write_tensors_to_file()
    w.close()
    print("wrote", out_path)


if __name__ == "__main__":
    main(*sys.argv[1:4])
