"""vid-in (2026-11-05): a clip part goes through the VIDEO projector in the training layout; single pictures and text are unchanged.
Run: ~/learner-ops/nb2-venv/bin/python -m pytest -q desk/tools/test_glim_clip.py"""
import os
import sys
import tempfile
import types

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
mx = pytest.importorskip("mlx.core")
import glim_eyes as E  # noqa: E402
import glim_mlx_server as W  # noqa: E402
from test_glim_eyes import FakeTok, gen_self, save_projector, tiny_nanbeige  # noqa: E402


def clip_part(feats, times):
    n = len(times)
    return {"type": "image_features", "image_features": {"f16": E.f16_b64(feats), "shape": [n * 64, 768], "eye": E.EYE_ID,
                                                         "clip": {"frames": n, "times": times}}}


def setup(video=True):
    import mlx_lm.server as S
    d = tempfile.mkdtemp()
    p, v = os.path.join(d, "img.safetensors"), os.path.join(d, "vid.safetensors")
    save_projector(p, enc=768, d=32, seed=1)
    save_projector(v, enc=768, d=32, seed=2)
    st = W.install_eyes(S, mx, p, log=lambda s: None, video_projector_path=v if video else os.path.join(d, "missing"))
    return S, st, p, v


@pytest.fixture
def restore():
    import mlx_lm.server as S
    saved = (S._image_url, S.ResponseGenerator._tokenize)
    yield
    S._image_url, S.ResponseGenerator._tokenize = saved


def test_clip_uses_video_projector_and_training_layout(restore):
    S, st, p, v = setup()
    assert st["video_projector"] == v
    tok = FakeTok()
    args = types.SimpleNamespace(chat_template_kwargs=None)
    feats = np.random.default_rng(5).standard_normal((3 * 64, 768)).astype(np.float32)
    req = types.SimpleNamespace(request_type="chat", tools=None, messages=[
        {"role": "user", "content": [{"type": "text", "text": "Clip:\n"}, clip_part(feats, [0, 2.6, 5]), {"type": "text", "text": "\nWhat happened?"}]}])
    prompt, _, _, _, vision = S.ResponseGenerator._tokenize(gen_self(), tok, req, args)
    want = (tok.encode("<user>Clip:\nFrame 1 (t=0s):\n") + [0] * 64 + tok.encode("\nFrame 2 (t=3s):\n") + [0] * 64
            + tok.encode("\nFrame 3 (t=5s):\n") + [0] * 64 + tok.encode("\nWhat happened?|<assistant>"))
    assert prompt == want
    assert len(vision.pixel_values) == 3 and st["clips"] == 1
    vp = E.load_projector(v)
    for k in range(3):
        ref = np.array(vp(mx.array(feats[k * 64:(k + 1) * 64]).astype(mx.float16)).astype(mx.float32))
        assert np.allclose(np.array(vision.pixel_values[k].astype(mx.float32)), ref, atol=1e-3), "frame %d: video projector" % k
    m = tiny_nanbeige(d=32)
    st["attach"](m)
    h = m.embed_inputs(mx.array(prompt), pixel_values=vision.pixel_values)
    runs = E.runs_of(prompt, 0)
    assert [n for _, n in runs] == [64, 64, 64]
    for (s0, n), pv in zip(runs, vision.pixel_values):
        assert np.allclose(np.array(h[s0:s0 + n].astype(mx.float32)), np.array(pv.astype(mx.float32)), atol=1e-2)


def test_single_picture_still_uses_image_projector(restore):
    S, st, p, v = setup()
    tok = FakeTok()
    feats = np.random.default_rng(6).standard_normal((64, 768)).astype(np.float32)
    part = {"type": "image_features", "image_features": {"f16": E.f16_b64(feats), "shape": [64, 768], "eye": E.EYE_ID}}
    req = types.SimpleNamespace(request_type="chat", tools=None, messages=[{"role": "user", "content": [part, {"type": "text", "text": "\nHi"}]}])
    prompt, _, _, _, vision = S.ResponseGenerator._tokenize(gen_self(), tok, req, types.SimpleNamespace(chat_template_kwargs=None))
    ref = np.array(E.load_projector(p)(mx.array(feats).astype(mx.float16)).astype(mx.float32))
    assert np.allclose(np.array(vision.pixel_values[0].astype(mx.float32)), ref, atol=1e-3) and st["clips"] == 0


def test_bad_clips_are_refused_and_missing_video_projector_falls_back(restore):
    S, st, p, v = setup()
    tok = FakeTok()
    args = types.SimpleNamespace(chat_template_kwargs=None)
    feats = np.zeros((2 * 64, 768), np.float32)
    for bad in (clip_part(feats, [0]), clip_part(np.zeros((9 * 64, 768), np.float32), list(range(9)))):
        bad["image_features"]["shape"] = [len(bad["image_features"]["clip"]["times"]) * 64, 768]
        with pytest.raises(ValueError):
            S.ResponseGenerator._tokenize(gen_self(), tok, types.SimpleNamespace(request_type="chat", tools=None,
                                          messages=[{"role": "user", "content": [bad]}]), args)
    wrong = clip_part(feats, [0, 1]); wrong["image_features"]["shape"] = [3 * 64, 768]
    with pytest.raises(ValueError):
        S.ResponseGenerator._tokenize(gen_self(), tok, types.SimpleNamespace(request_type="chat", tools=None,
                                      messages=[{"role": "user", "content": [wrong]}]), args)
    S2, st2, p2, _ = setup(video=False)
    assert st2["video_projector"] is None
    f = np.random.default_rng(7).standard_normal((2 * 64, 768)).astype(np.float32)
    req = types.SimpleNamespace(request_type="chat", tools=None, messages=[{"role": "user", "content": [clip_part(f, [0, 2])]}])
    prompt, _, _, _, vision = S2.ResponseGenerator._tokenize(gen_self(), tok, req, args)
    assert prompt.count(0) == 64 and len(vision.pixel_values) == 1
    ref = np.array(E.load_projector(p2)(mx.array(f[64:]).astype(mx.float16)).astype(mx.float32))
    assert np.allclose(np.array(vision.pixel_values[0].astype(mx.float32)), ref, atol=1e-3), "fallback: last frame, image projector"


def test_default_video_projector_prefers_sense_sleep_copy():
    d = tempfile.mkdtemp()
    sf = os.path.join(d, "settings.json")
    assert W.default_video_projector(sf) == W.SHIPPED_VIDEO_PROJECTOR
    os.makedirs(os.path.join(d, "sense-sleep"))
    open(os.path.join(d, "sense-sleep", "video_projector.safetensors"), "wb").write(b"x")
    assert W.default_video_projector(sf) == os.path.join(d, "sense-sleep", "video_projector.safetensors")


def test_seeing_ask_after_tool_calls_parses_arguments(restore):
    """Regression (M3 in-app test, 2026-11-05): a clip ask in a thread with earlier tool calls failed with
    'Can only get item pairs from a mapping' because tool-call arguments reached the chat template as JSON strings."""
    S, st, p, v = setup()

    class MapTok(FakeTok):
        def apply_chat_template(self, messages, add_generation_prompt=True, tokenize=False, tools=None, **kw):
            for m in messages:
                for tc in m.get("tool_calls") or []:
                    assert isinstance(tc["function"]["arguments"], dict), "arguments must be a mapping"
            return FakeTok.apply_chat_template(self, messages, add_generation_prompt, tokenize, tools, **kw)

    feats = np.random.default_rng(7).standard_normal((3 * 64, 768)).astype(np.float32)
    req = types.SimpleNamespace(request_type="chat", tools=None, messages=[
        {"role": "user", "content": "look something up"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "search", "arguments": "{\"q\": \"x\"}"}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "result"},
        {"role": "user", "content": [clip_part(feats, [0, 2.5, 5]), {"type": "text", "text": "\nWhat happened?"}]}])
    prompt, _, _, _, vision = S.ResponseGenerator._tokenize(gen_self(), MapTok(), req, types.SimpleNamespace(chat_template_kwargs=None))
    assert len(vision.pixel_values) == 3 and req.messages[1]["tool_calls"][0]["function"]["arguments"] == {"q": "x"}
