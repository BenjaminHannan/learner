"""Plumbing tests for the audio side of the shared Workspace contract
(tokens, segment, coords, valid). They show shapes, masks and coordinates
behave as documented; they say nothing about audio reasoning."""
import math

import numpy as np
import pytest

from premonition.audio import adapter as A
from premonition.audio import frontend as F
from premonition.audio import synth as S


def spec(**kw):
    base = dict(modality="audio", d_in=80, frame_period=0.01, downsample=4)
    base.update(kw)
    return A.ModalityAdapterSpec(**base)


def test_id_tables_match_workspace_v1():
    # Literal copy of PR #23 section 6 (commit 80540de9e), matching vision's PR #26.
    assert A.ROLE_IDS == {"question": 0, "notebook": 1, "example": 2, "tool_result": 3, "register": 4,
                          "action": 5}
    assert A.MODALITY_IDS == {"text": 0, "image": 1, "audio": 2}


def test_example_role_puts_example_index_in_row():
    sp = spec()
    w = A.init_weights(sp, seed=2)
    x = F.log_mel(S.syllables(2))
    out = A.adapt(sp, w, x, role="example", example_index=3)
    v = out["valid"]
    assert np.all(out["coords"][v, 0] == 3) and np.all(out["coord_valid"][v, 0])
    assert not out["coord_valid"][:, 1].any() and np.array_equal(out["coord_valid"][:, 2], v)
    with pytest.raises(ValueError):
        A.adapt(sp, w, x, role="example")
    with pytest.raises(ValueError):
        A.adapt(sp, w, x, role="notebook", example_index=0)


def test_audio_segment_is_role_modality_pair():
    g = A.audio_segment("notebook", 5)
    assert g.dtype == np.int64 and g.shape == (5, 2)
    assert (g == [1, 2]).all()
    with pytest.raises(ValueError):
        A.audio_segment("register", 3)      # registers belong to the core, not an input adapter
    with pytest.raises(ValueError):
        A.audio_segment("question", 3, modality="smell")


@pytest.mark.parametrize("t_in,k", [(1, 4), (3, 4), (4, 4), (5, 4), (100, 4), (101, 8), (7, 1)])
def test_downsample_length_arithmetic(t_in, k):
    sp = spec(downsample=k)
    out = A.adapt(sp, A.init_weights(sp), np.random.default_rng(t_in).standard_normal((t_in, 80)))
    assert out["tokens"].shape == (math.ceil(t_in / k), 256)
    assert sp.out_len(t_in) == math.ceil(t_in / k)


@pytest.mark.parametrize("pool", ["stack", "mean"])
@pytest.mark.parametrize("hidden", [None, 32, 256])
def test_output_is_exactly_the_workspace_fields(pool, hidden):
    sp = spec(pool=pool, hidden=hidden)
    w = A.init_weights(sp, seed=3)
    x = F.log_mel(S.syllables(3))
    out = A.adapt(sp, w, x, role="question")
    n = sp.out_len(len(x))
    assert tuple(out) == ("tokens", "segment", "coords", "coord_valid", "valid")
    assert out["coord_valid"].dtype == bool and out["coord_valid"].shape == (n, 3)
    assert not out["coord_valid"][:, :2].any() and np.array_equal(out["coord_valid"][:, 2], out["valid"])
    assert out["tokens"].dtype == np.float32 and out["tokens"].shape == (n, 256)
    assert out["segment"].dtype == np.int64 and out["segment"].shape == (n, 2)
    assert out["coords"].dtype == np.float32 and out["coords"].shape == (n, 3)
    assert out["valid"].dtype == bool and out["valid"].shape == (n,)
    assert sp.parameter_count() == sum(v.size for v in w.values())


def test_coords_are_time_in_seconds():
    sp = spec(frame_period=0.02, downsample=4)          # Whisper-like 50 Hz frames -> 80 ms slots
    out = A.adapt(sp, A.init_weights(sp), np.random.default_rng(0).standard_normal((10, 80)))
    c = out["coords"]
    assert np.all(c[:, :2] == 0)
    assert np.allclose(c[:, 2], [0.04, 0.12, 0.20])     # slot centres, seconds


def test_padding_valid_and_zero_rows():
    sp = spec()
    w = A.init_weights(sp, seed=1)
    real = F.log_mel(S.tone(500, 0.5))                  # 50 frames
    padded = np.concatenate([real, np.full((30, 80), 99.0, np.float32)])
    valid = np.r_[np.ones(50, bool), np.zeros(30, bool)]
    out = A.adapt(sp, w, padded, valid)
    assert out["valid"].tolist() == [True] * 13 + [False] * 7   # ceil(50/4)=13 of ceil(80/4)=20
    assert np.all(out["tokens"][~out["valid"]] == 0) and np.all(out["coords"][~out["valid"]] == 0)
    alone = A.adapt(sp, w, real)                        # garbage in the padded tail cannot leak
    assert np.allclose(out["tokens"][:13], alone["tokens"], atol=1e-6)


def test_partial_slot_ignores_padded_frames_in_mean_pool():
    sp = spec(pool="mean", downsample=4)
    w = A.init_weights(sp, seed=2)
    x = np.random.default_rng(0).standard_normal((6, 80)).astype(np.float32)
    garbage = x.copy(); garbage[5] = 1e3
    m = np.array([1, 1, 1, 1, 1, 0], bool)
    assert np.allclose(A.adapt(sp, w, x, m)["tokens"], A.adapt(sp, w, garbage, m)["tokens"])


def test_strict_input_checks():
    sp = spec()
    w = A.init_weights(sp)
    x = np.zeros((8, 80), np.float32)
    with pytest.raises(ValueError):
        A.adapt(sp, w, x, np.array([1, 0, 1, 1, 1, 1, 1, 1], bool))   # hole in valid
    with pytest.raises(ValueError):
        A.adapt(sp, w, x, np.ones(8, np.int64))
    with pytest.raises(ValueError):
        A.adapt(sp, w, x, np.zeros(8, bool))
    with pytest.raises(ValueError):
        A.adapt(sp, w, np.zeros((8, 81), np.float32))
    with pytest.raises(TypeError):
        A.adapt(sp, w, np.zeros((8, 80), np.int32))
    bad = dict(w); bad["w1"] = bad["w1"].astype(np.float64)
    with pytest.raises(TypeError):
        A.adapt(sp, bad, x)
    with pytest.raises(ValueError):
        A.adapt(sp, w, x, role="register")
    with pytest.raises(ValueError):
        A.ModalityAdapterSpec(modality="smell", d_in=8, frame_period=0.01)


def test_time_codes_unique_and_rate_independent():
    t = (np.arange(math.ceil(1500 / 4)) + 0.5) * 0.08   # 30 s of 80 ms slots
    p = A.sinusoid(t, 256, 0.08, 2000.0)
    d = np.sqrt(((p[:, None, :] - p[None, :, :]) ** 2).sum(-1))
    np.fill_diagonal(d, np.inf)
    assert d.min() > 0.5                                # every slot in 30 s has a distinct code
    a = spec(frame_period=0.01, downsample=8)           # 100 Hz frames, 80 ms slots
    b = spec(frame_period=0.02, downsample=4)           # 50 Hz frames, 80 ms slots
    rng = np.random.default_rng(1)
    ca = A.adapt(a, A.init_weights(a), rng.standard_normal((80, 80)))["coords"]
    cb = A.adapt(b, A.init_weights(b), rng.standard_normal((40, 80)))["coords"]
    assert np.allclose(ca, cb)


def test_position_code_changes_tokens_only_when_enabled():
    x = F.log_mel(S.tone(800, 0.4))
    off, on = spec(pos_scale=0.0), spec(pos_scale=1.0)
    w = A.init_weights(off, seed=4)
    a, b = A.adapt(off, w, x), A.adapt(on, w, x)
    pos = A.sinusoid(b["coords"][:, 2].astype(np.float64), 256, on.min_period, on.max_period)
    assert np.allclose(b["tokens"] - a["tokens"], pos, atol=1e-4)


def test_no_tag_added_in_adapter():
    # The core adds Embedding(role) + Embedding(modality) (PR #23); the adapter must not.
    sp = spec()
    w = A.init_weights(sp, seed=5)
    x = F.log_mel(S.chirp(300, 3000, 0.4))
    q, nb = A.adapt(sp, w, x, role="question"), A.adapt(sp, w, x, role="notebook")
    assert np.array_equal(q["tokens"], nb["tokens"])
    assert (q["segment"][:, 0] == 0).all() and (nb["segment"][:, 0] == 1).all()


def test_batch_and_core_layout():
    sp = spec()
    w = A.init_weights(sp, seed=9)
    short, long = F.log_mel(S.tone(400, 0.3)), F.log_mel(S.noise_burst(0.6, 0.2, 0.1, seed=4))
    o1, o2 = A.adapt(sp, w, short), A.adapt(sp, w, long, role="notebook")
    assert np.array_equal(A.adapt(sp, w, short)["tokens"], o1["tokens"])   # deterministic
    b = A.batch([o1, o2])
    n1, n2 = len(o1["valid"]), len(o2["valid"])
    assert b["tokens"].shape == (2, max(n1, n2), 256) and b["segment"].shape == (2, max(n1, n2), 2)
    assert b["valid"][0].sum() == n1 and not b["valid"][0, n1:].any()
    assert np.all(b["tokens"][0, n1:] == 0)
    assert b["coord_valid"].shape == (2, max(n1, n2), 3) and not b["coord_valid"][0, n1:].any()
    kind, latent = A.to_core_layout(o1)
    assert kind == "latent" and latent.shape == (1, 1, n1, 256)
    kind, nb = A.to_core_layout(o2)
    assert kind == "notebook" and nb.shape == (1, n2, 256)


def test_silence_vs_tone_separable_after_adapter():
    # A fixed random adapter keeps a trivial difference visible: mean slot norm.
    sp = spec(layernorm=False)
    w = A.init_weights(sp, seed=11)
    nrm = lambda x: np.linalg.norm(A.adapt(sp, w, F.log_mel(x, whisper_norm=False))["tokens"], axis=1).mean()
    silent = nrm(S.silence(0.5))
    tones = [nrm(S.tone(f, 0.5)) for f in (200, 1000, 4000)]
    assert silent < min(tones) or silent > max(tones)
