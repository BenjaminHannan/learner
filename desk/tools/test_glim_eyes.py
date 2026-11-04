"""Tests for Glim's eyes (track I1): glim_eyes.py and the "Glim can see" path in glim_mlx_server.py.
Tiny shapes and a tiny random Nanbeige only (no real model, no download, no server). MLX needed.
Run: ~/learner-ops/nb2-venv/bin/python -m pytest -q desk/tools/test_glim_eyes.py"""
import base64
import json
import os
import sys
import tempfile
import types

import numpy as np
import pytest

mx = pytest.importorskip("mlx.core")
import mlx.nn as nn  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
import glim_eyes as E  # noqa: E402
import glim_mlx_server as W  # noqa: E402


def tiny_nanbeige(vocab=64, d=32, loops=2):
    from mlx_lm.models import nanbeige as NB
    args = NB.ModelArgs(model_type="nanbeige", hidden_size=d, num_hidden_layers=2, intermediate_size=48, num_attention_heads=4,
                        num_key_value_heads=2, rms_norm_eps=1e-5, vocab_size=vocab, head_dim=8, num_loops=loops,
                        tie_word_embeddings=False, max_position_embeddings=512, rope_theta=10000.0)
    mx.random.seed(0)
    m = NB.Model(args)
    mx.eval(m.parameters())
    return m


def save_projector(path, enc=8, d=32, seed=0):
    rng = np.random.default_rng(seed)
    W_ = {"fc1.weight": rng.standard_normal((d, enc)) * 0.2, "fc1.bias": rng.standard_normal(d) * 0.1,
          "fc2.weight": rng.standard_normal((d, d)) * 0.2, "fc2.bias": rng.standard_normal(d) * 0.1}
    mx.save_safetensors(path, {k: mx.array(v.astype(np.float32)) for k, v in W_.items()})
    return W_


def test_pool_matches_reference_loop():
    lh = np.random.default_rng(1).standard_normal((1, 256, 4)).astype(np.float32)
    got = np.array(E.pool(mx, mx.array(lh)))[0]
    g = lh.reshape(16, 16, 4)
    ref = np.stack([g[2 * i:2 * i + 2, 2 * j:2 * j + 2].mean((0, 1)) for i in range(8) for j in range(8)])
    assert got.shape == (64, 4) and np.allclose(got, ref, atol=1e-5)


def test_preprocess_is_the_training_recipe():
    from PIL import Image
    im = Image.fromarray(np.full((10, 30, 4), 255, np.uint8), "RGBA")
    x = E.preprocess(im)
    assert x.shape == (256, 256, 3) and x.dtype == np.float32 and np.allclose(x, 1.0)
    assert np.allclose(E.preprocess(Image.new("RGB", (5, 5))), -1.0)


def test_tiny_vision_tower_runs_and_loads_torch_layout():
    m = E.build_vision(mx, nn, {"hidden_size": 16, "num_hidden_layers": 1, "num_attention_heads": 2, "intermediate_size": 32})
    mx.eval(m.parameters())
    out = m(mx.zeros((2, 256, 256, 3)))
    assert out.shape == (2, 256, 16)
    assert E.pool(mx, out).shape == (2, 64, 16)


def test_projector_is_exact_gelu_mlp():
    from math import erf
    p = os.path.join(tempfile.mkdtemp(), "p.safetensors")
    Wt = save_projector(p)
    proj = E.load_projector(p, dtype=mx.float32)
    x = np.random.default_rng(2).standard_normal((5, 8)).astype(np.float32)
    h = x @ Wt["fc1.weight"].T + Wt["fc1.bias"]
    h = h * 0.5 * (1 + np.vectorize(erf)(h / np.sqrt(2)))
    ref = h @ Wt["fc2.weight"].T + Wt["fc2.bias"]
    assert np.allclose(np.array(proj(mx.array(x))), ref, atol=1e-4)


def test_f16_round_trip_and_bad_size():
    a = np.random.default_rng(3).standard_normal((64, 768)).astype(np.float32)
    b = E.f16_from_b64(E.f16_b64(a), [64, 768])
    assert np.allclose(a, b, atol=2e-3)
    with pytest.raises(ValueError):
        E.f16_from_b64(E.f16_b64(a), [65, 768])


def test_splice_rows_full_partial_and_cached_images():
    h = mx.zeros((12, 2))
    A = mx.full((4, 2), 1.0)
    B = mx.full((4, 2), 2.0)
    B = mx.concatenate([mx.full((2, 2), 2.0), mx.full((2, 2), 3.0)])
    ids = [5, 9, 9, 9, 9, 6, 9, 9, 9, 9, 7, 8]
    out = np.array(E.splice_rows(mx, h, ids, 9, [A, B]))
    assert (out[1:5] == 1).all() and (out[6:8] == 2).all() and (out[8:10] == 3).all() and (out[[0, 5, 10, 11]] == 0).all()
    # the prompt cache took image A and the first half of B: the rest starts with B's last 2 rows
    out2 = np.array(E.splice_rows(mx, mx.zeros((4, 2)), [9, 9, 7, 8], 9, [A, B]))
    assert (out2[0:2] == 3).all() and (out2[2:] == 0).all()
    assert E.runs_of([1, 9, 9, 2, 9], 9) == [(1, 2), (4, 1)]


def test_make_seeing_embeddings_path_equals_ids_path_on_tiny_nanbeige():
    from mlx_lm.models.cache import make_prompt_cache
    m = tiny_nanbeige()
    ids = mx.array([[3, 7, 1, 12, 40, 2]])
    ref = m(ids)
    W.make_seeing(m)
    assert np.allclose(np.array(m(ids)), np.array(ref), atol=1e-5), "without embeddings: stock call"
    emb = m.model.embed_tokens(ids)
    got = m(ids, input_embeddings=emb)
    assert np.allclose(np.array(got), np.array(ref), atol=1e-5)
    # with a KV cache, in two chunks (as the server's prefill does)
    c = make_prompt_cache(m)
    m(ids[:, :4], cache=c, input_embeddings=emb[:, :4])
    last = m(ids[:, 4:], cache=c, input_embeddings=emb[:, 4:])
    assert np.allclose(np.array(last), np.array(ref[:, 4:]), atol=1e-4)
    from mlx_lm.utils import does_model_support_input_embeddings
    assert does_model_support_input_embeddings(m)
    assert W.make_seeing(m) is m   # idempotent


class FakeTok:
    """Char-level tokenizer with a ChatML-like template; id 0 = <unk> (the placeholder)."""
    unk_token_id = 0
    has_thinking = False
    response_initial_state = None

    def apply_chat_template(self, messages, add_generation_prompt=True, tokenize=False, tools=None, **kw):
        s = "".join("<%s>%s|" % (m["role"], m["content"]) for m in messages) + ("<assistant>" if add_generation_prompt else "")
        return s if not tokenize else self.encode(s)

    def encode(self, s, add_special_tokens=False):
        return [1 + (ord(ch) % 60) for ch in s]


def gen_self():
    return types.SimpleNamespace(model_provider=types.SimpleNamespace(cli_args=types.SimpleNamespace(chat_template_args={})))


def test_server_eyes_tokenize_splice_and_text_only_untouched():
    import mlx_lm.server as S
    saved = (S._image_url, S.ResponseGenerator._tokenize)
    try:
        p = os.path.join(tempfile.mkdtemp(), "proj.safetensors")
        save_projector(p, enc=768, d=32)
        calls = []
        orig = S.ResponseGenerator._tokenize
        S.ResponseGenerator._tokenize = lambda self, tok, req, args: calls.append(1) or ("stock",)
        st = W.install_eyes(S, mx, p, log=lambda s: None)
        tok = FakeTok()
        args = types.SimpleNamespace(chat_template_kwargs=None)
        text_req = types.SimpleNamespace(request_type="chat", tools=None, messages=[{"role": "user", "content": "hi"}])
        assert S.ResponseGenerator._tokenize(gen_self(), tok, text_req, args) == ("stock",) and calls == [1]
        feats = np.random.default_rng(4).standard_normal((64, 768)).astype(np.float32)
        part = {"type": "image_features", "image_features": {"f16": E.f16_b64(feats), "shape": [64, 768], "eye": E.EYE_ID}}
        req = types.SimpleNamespace(request_type="chat", tools=None, messages=[
            {"role": "user", "content": [{"type": "text", "text": "Look: "}, part, {"type": "text", "text": "\nDescribe this image."}]}])
        assert list(S._image_parts(req.messages)) == [part], "feature requests are served one at a time"
        prompt, segs, types_, initial, vision = S.ResponseGenerator._tokenize(gen_self(), tok, req, args)
        pre = tok.encode("<user>Look: ")
        post = tok.encode("\nDescribe this image.|<assistant>")
        assert prompt == pre + [0] * 64 + post
        assert vision.starts == [len(pre)] and vision.cache_key[len(pre)] < 0 and len(vision.pixel_values) == 1
        assert vision.pixel_values[0].shape == (64, 32)
        # the model side: embed_inputs puts the projected rows at the placeholders
        m = tiny_nanbeige(d=32)
        st["attach"](m)
        h = m.embed_inputs(mx.array(prompt), pixel_values=vision.pixel_values)
        assert h.shape == (len(prompt), 32)
        projd = np.array(E.load_projector(p)(mx.array(feats).astype(mx.float16)).astype(mx.float32))
        assert np.allclose(np.array(h[len(pre):len(pre) + 64].astype(mx.float32)), projd, atol=1e-2)
        base = np.array(m.model.embed_tokens(mx.array(prompt)))
        assert np.allclose(np.array(h[:len(pre)]), base[:len(pre)]) and np.allclose(np.array(h[-len(post):]), base[-len(post):])
        # end to end through stock generate_step with input_embeddings
        from mlx_lm.generate import generate_step
        tok1, _ = next(generate_step(mx.array(prompt), m, input_embeddings=h, max_tokens=1))
        assert 0 <= int(tok1) < 64
        with pytest.raises(ValueError):
            bad = dict(part, image_features={"f16": E.f16_b64(feats), "shape": [64, 10]})
            S.ResponseGenerator._tokenize(gen_self(), tok, types.SimpleNamespace(request_type="chat", tools=None,
                                          messages=[{"role": "user", "content": [bad]}]), args)
        S.ResponseGenerator._tokenize = orig
    finally:
        S._image_url, S.ResponseGenerator._tokenize = saved


def test_eyes_setting_defaults_off():
    assert W.eyes_on(None, None) is False
    d = tempfile.mkdtemp()
    p = os.path.join(d, "settings.json")
    json.dump({"glimCanSee": "true"}, open(p, "w"))
    assert W.eyes_on(p, None) is False
    json.dump({"glimCanSee": True}, open(p, "w"))
    assert W.eyes_on(p, None) is True and W.eyes_on(p, "off") is False
    argv = ["x", "--model", "m", "--eyes", "on", "--eyes-projector", "/p", "--port", "1"]
    assert W.pop_flag(argv, "--eyes") == "on" and W.pop_flag(argv, "--eyes-projector") == "/p" and argv == ["x", "--model", "m", "--port", "1"]


def test_serve_worker_lines_and_bad_frame():
    import io
    from PIL import Image
    d = tempfile.mkdtemp()
    good = os.path.join(d, "a.png")
    Image.new("RGB", (40, 30), (10, 20, 30)).save(good)
    inp = io.StringIO(json.dumps({"id": "1", "path": good}) + "\n" + json.dumps({"id": "2", "path": os.path.join(d, "missing.jpg")}) + "\n")
    out = io.StringIO()
    E.serve(inp=inp, out=out, loader=lambda d: "M", encoder=lambda m, ims: np.ones((1, 64, 768), np.float32))
    lines = [json.loads(l) for l in out.getvalue().splitlines()]
    assert lines[0] == {"ready": True, "eye": E.EYE_ID}
    assert lines[1]["ok"] and lines[1]["shape"] == [64, 768] and np.allclose(E.f16_from_b64(lines[1]["f16"], [64, 768]), 1)
    assert lines[2]["ok"] is False and lines[2]["id"] == "2"
    assert os.path.exists(good), "the worker never deletes the caller's file"


def test_default_projector_prefers_the_slept_copy():
    d = tempfile.mkdtemp()
    sf = os.path.join(d, "settings.json")
    assert W.default_projector(sf) == W.PUBLISHED_PROJECTOR and W.default_projector(None) == W.PUBLISHED_PROJECTOR
    os.makedirs(os.path.join(d, "sense-sleep"))
    open(os.path.join(d, "sense-sleep", "vision_projector.safetensors"), "wb").write(b"x")
    assert W.default_projector(sf) == os.path.join(d, "sense-sleep", "vision_projector.safetensors")
