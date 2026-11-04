r"""Glim's eyes (track I1, 2026-11-04): SigLIP2-base-patch16-256 vision tower in MLX -> pooled features -> the vision projector.

Pieces (each tested in test_glim_eyes.py; the encoder against the transformers reference):
  - SiglipVision: the frozen vision tower (12 pre-LN blocks + post-layernorm), MLX, bf16 weights from
    ~/learner-ops/models/siglip2-base-patch16-256-vision/model.safetensors (vision_model.* of google/siglip2-base-patch16-256).
  - preprocess(): exactly the training recipe (premonition-projectors scripts/mm.py): RGB, resize 256x256 BICUBIC, (x/255 - 0.5)/0.5.
  - pool(): 16x16 patch grid -> 2x2 average pool -> 64 x 768 (row-major), the projector's input.
  - Projector / load_projector / splice_rows: the vision projector (fc1 768->3072, exact GELU, fc2 3072->3072) and the splice of its
    64 output rows into a token embedding sequence at placeholder positions.
  - serve(): a small worker for the Desk. One JSON request per stdin line, one JSON reply per stdout line:
        {"id": "...", "path": "/tmp/frame.jpg"}  ->  {"id": "...", "ok": true, "shape": [64, 768], "f16": "<base64 float16 LE>", "ms": 41.2}
    The pooled features are what the Desk stores for sense sleep (FeatureStore) and sends to the model server (image_features part).
    The worker never writes the image anywhere and never deletes the caller's file.

EYE_ID names this exact encoder + pooling. Change it whenever either changes: sense sleep skips features with another id.
"""
import base64
import json
import os
import sys
import time

EYE_ID = "siglip2-base-patch16-256/pool2x2/v1"
DEFAULT_DIR = os.path.expanduser("~/learner-ops/models/siglip2-base-patch16-256-vision")
DEFAULT_PROJECTOR = os.path.expanduser("~/learner-ops/premonition-projectors/weights/vision_projector.safetensors")
N_TOKENS, ENC_DIM, D_MODEL = 64, 768, 3072


def _mx():
    import mlx.core as mx
    import mlx.nn as nn
    return mx, nn


# ---- encoder ---------------------------------------------------------------------------------------------
def build_vision(mx, nn, cfg=None):
    cfg = dict({"hidden_size": 768, "num_hidden_layers": 12, "num_attention_heads": 12, "intermediate_size": 3072,
                "patch_size": 16, "image_size": 256, "layer_norm_eps": 1e-6}, **(cfg or {}))
    D, H, P, E = cfg["hidden_size"], cfg["num_attention_heads"], cfg["patch_size"], cfg["layer_norm_eps"]
    G = cfg["image_size"] // P

    class Attn(nn.Module):
        def __init__(self):
            super().__init__()
            self.q_proj, self.k_proj, self.v_proj, self.out_proj = (nn.Linear(D, D) for _ in range(4))

        def __call__(self, x):
            B, L, _ = x.shape
            sh = lambda t: t.reshape(B, L, H, D // H).transpose(0, 2, 1, 3)
            o = mx.fast.scaled_dot_product_attention(sh(self.q_proj(x)), sh(self.k_proj(x)), sh(self.v_proj(x)),
                                                     scale=(D // H) ** -0.5)
            return self.out_proj(o.transpose(0, 2, 1, 3).reshape(B, L, D))

    class MLP(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1, self.fc2 = nn.Linear(D, cfg["intermediate_size"]), nn.Linear(cfg["intermediate_size"], D)

        def __call__(self, x):
            return self.fc2(nn.gelu_approx(self.fc1(x)))   # gelu_pytorch_tanh

    class Layer(nn.Module):
        def __init__(self):
            super().__init__()
            self.layer_norm1, self.layer_norm2 = nn.LayerNorm(D, eps=E), nn.LayerNorm(D, eps=E)
            self.self_attn, self.mlp = Attn(), MLP()

        def __call__(self, x):
            x = x + self.self_attn(self.layer_norm1(x))
            return x + self.mlp(self.layer_norm2(x))

    class Embeddings(nn.Module):
        def __init__(self):
            super().__init__()
            self.patch_embedding = nn.Conv2d(3, D, P, stride=P)   # weight stored (out, kh, kw, in) in MLX
            self.position_embedding = nn.Embedding(G * G, D)

        def __call__(self, px):           # px: (B, 256, 256, 3) NHWC
            x = self.patch_embedding(px).reshape(px.shape[0], G * G, D)
            return x + self.position_embedding.weight[None]

    class Encoder(nn.Module):
        def __init__(self):
            super().__init__()
            self.layers = [Layer() for _ in range(cfg["num_hidden_layers"])]

    class SiglipVision(nn.Module):
        def __init__(self):
            super().__init__()
            self.embeddings, self.encoder, self.post_layernorm = Embeddings(), Encoder(), nn.LayerNorm(D, eps=E)

        def __call__(self, px):
            x = self.embeddings(px)
            for l in self.encoder.layers:
                x = l(x)
            return self.post_layernorm(x)  # last_hidden_state (B, 256, 768)

    return SiglipVision()


def load_vision(model_dir=DEFAULT_DIR, dtype=None):
    """-> MLX SiglipVision with the downloaded weights (head.* is not used: the projector reads last_hidden_state)."""
    mx, nn = _mx()
    dtype = dtype or mx.float16   # measured: f16 compute matches the f32 reference at cos 0.99994 (bf16: 0.9984)
    try:
        cfg = json.load(open(os.path.join(model_dir, "config.json")))
    except OSError:
        cfg = {}
    m = build_vision(mx, nn, {k: cfg[k] for k in ("hidden_size", "num_hidden_layers", "num_attention_heads", "intermediate_size",
                                                   "patch_size", "image_size", "layer_norm_eps") if k in cfg})
    w = mx.load(os.path.join(model_dir, "model.safetensors"))
    out = []
    for k, v in w.items():
        if not k.startswith("vision_model.") or k.startswith("vision_model.head."):
            continue
        k = k[len("vision_model."):]
        if k == "embeddings.patch_embedding.weight":
            v = v.transpose(0, 2, 3, 1)   # torch (out, in, kh, kw) -> MLX (out, kh, kw, in)
        out.append((k, v.astype(dtype)))
    m.load_weights(out, strict=True)
    mx.eval(m.parameters())
    return m


def preprocess(img):
    """PIL image -> float32 numpy (256, 256, 3) in [-1, 1]: RGB, BICUBIC 256x256, mean = std = 0.5 (the training recipe)."""
    import numpy as np
    from PIL import Image
    img = img.convert("RGB").resize((256, 256), Image.BICUBIC)
    return (np.asarray(img, dtype=np.float32) / 255.0 - 0.5) / 0.5


def pool(mx, last_hidden):
    """(B, 256, 768) -> (B, 64, 768): 16x16 grid, 2x2 average pool, row-major (= premonition-projectors pool_siglip)."""
    B, N, D = last_hidden.shape
    return last_hidden.reshape(B, 8, 2, 8, 2, D).mean(axis=(2, 4)).reshape(B, 64, D)


def encode(model, images):
    """List of PIL images -> float32 numpy (B, 64, 768) pooled features."""
    import numpy as np
    mx, _ = _mx()
    px = mx.array(np.stack([preprocess(im) for im in images])).astype(model.post_layernorm.weight.dtype)
    f = pool(mx, model(px).astype(mx.float32))
    mx.eval(f)
    return np.array(f)


# ---- projector + splice ------------------------------------------------------------------------------------
def load_projector(path=DEFAULT_PROJECTOR, dtype=None):
    mx, nn = _mx()

    class Projector(nn.Module):
        def __init__(self, enc_dim, d_model):
            super().__init__()
            self.fc1, self.fc2 = nn.Linear(enc_dim, d_model), nn.Linear(d_model, d_model)

        def __call__(self, x):
            return self.fc2(nn.gelu(self.fc1(x)))   # exact (erf) GELU, as in training

    w = mx.load(path)
    p = Projector(w["fc1.weight"].shape[1], w["fc1.weight"].shape[0])
    p.load_weights([(k, v.astype(dtype or mx.float16)) for k, v in w.items()], strict=True)
    mx.eval(p.parameters())
    return p


def runs_of(ids, token_id):
    """[(start, length)] of the consecutive runs of token_id in a python list of ids."""
    out, i = [], 0
    while i < len(ids):
        if ids[i] == token_id:
            j = i
            while j < len(ids) and ids[j] == token_id:
                j += 1
            out.append((i, j - i))
            i = j
        else:
            i += 1
    return out


def splice_rows(mx, h, ids, token_id, media):
    """h: (L, d) token embeddings of `ids`; media: list of (64, d) arrays, one per placeholder run, in order (the LAST len(media) runs
    when there are more runs than media: earlier images were cut by the prompt cache). A first run shorter than 64 is the tail of an
    image whose head is in the cache: it gets that image's last rows. Returns (L, d)."""
    runs = runs_of(list(ids), token_id)
    if not runs:
        return h
    runs = runs[-len(media):] if len(runs) > len(media) else runs
    media = media[-len(runs):]
    pieces, pos = [], 0
    for (s, n), m in zip(runs, media):
        if s > pos:
            pieces.append(h[pos:s])
        rows = m[-n:] if n <= m.shape[0] else None
        if rows is None:
            raise ValueError("image run longer than its features (%d > %d)" % (n, m.shape[0]))
        pieces.append(rows.astype(h.dtype))
        pos = s + n
    if pos < h.shape[0]:
        pieces.append(h[pos:])
    return mx.concatenate(pieces, axis=0)


def f16_b64(arr):
    import numpy as np
    return base64.b64encode(np.ascontiguousarray(arr, dtype="<f2").tobytes()).decode()


def f16_from_b64(s, shape):
    import numpy as np
    a = np.frombuffer(base64.b64decode(s), dtype="<f2").astype(np.float32)
    if a.size != shape[0] * shape[1]:
        raise ValueError("features size %d does not match shape %s" % (a.size, shape))
    return a.reshape(shape)


# ---- the Desk's worker ----------------------------------------------------------------------------------------
def serve(model_dir=DEFAULT_DIR, inp=sys.stdin, out=sys.stdout, loader=None, encoder=None):
    """Stdin JSON lines -> stdout JSON lines (see the module doc). loader/encoder: test seams."""
    from PIL import Image
    mx, _ = _mx()
    try:
        mx.set_cache_limit(64 << 20)   # gentle: the eyes keep at most 64 MB of freed buffers
    except Exception:  # noqa: BLE001
        pass
    model = (loader or load_vision)(model_dir)
    enc = encoder or encode
    out.write(json.dumps({"ready": True, "eye": EYE_ID}) + "\n")
    out.flush()
    for line in inp:
        line = line.strip()
        if not line:
            continue
        rid = None
        try:
            req = json.loads(line)
            rid = req.get("id")
            if req.get("quit"):
                break
            t0 = time.perf_counter()
            with Image.open(req["path"]) as im:
                f = enc(model, [im])[0]
            rep = {"id": rid, "ok": True, "eye": EYE_ID, "shape": [int(f.shape[0]), int(f.shape[1])], "f16": f16_b64(f),
                   "ms": round((time.perf_counter() - t0) * 1000, 1)}
        except Exception as e:  # noqa: BLE001 - one bad frame never stops the eyes
            rep = {"id": rid, "ok": False, "error": ("%s: %s" % (type(e).__name__, e))[:300]}
        out.write(json.dumps(rep) + "\n")
        out.flush()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Glim's eyes: SigLIP2 frames -> pooled 64x768 features (JSON lines on stdin/stdout).")
    ap.add_argument("cmd", choices=["serve", "encode"])
    ap.add_argument("--model-dir", default=DEFAULT_DIR)
    ap.add_argument("paths", nargs="*")
    a = ap.parse_args()
    if a.cmd == "serve":
        serve(a.model_dir)
    else:
        from PIL import Image
        m = load_vision(a.model_dir)
        for p in a.paths:
            t0 = time.perf_counter()
            with Image.open(p) as im:
                f = encode(m, [im])[0]
            print(json.dumps({"path": p, "shape": list(f.shape), "ms": round((time.perf_counter() - t0) * 1000, 1)}))
