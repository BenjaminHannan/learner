"""Plumbing tests for the streaming stereo game-sound path (premonition/audio/stream.py).

They show causality, chunk-size independence, shapes and that stereo features
carry left/right. They say nothing about whether a trained ear or the reasoner
can hear anything.
"""
import numpy as np
import pytest

from premonition.audio import synth
from premonition.audio.adapter import ModalityAdapterSpec, SEGMENTS, init_weights
from premonition.audio.frontend import N_MELS, log_mel
from premonition.audio.stream import (AudioWindow, CausalConvEar, CausalConvEarSpec, StreamingStereoMel,
                                      hearing_latency_bound, ild_pan_estimate, init_ear_weights)

SR = 16000


def _scene(seed=0):
    return synth.stereo_scene([
        {"kind": "steps", "start": 0.1, "length": 0.8, "azimuth": -60, "seed": seed},
        {"kind": "hiss", "start": 0.6, "length": 0.7, "azimuth": 150, "seed": seed + 1},
    ], seconds=1.5)


def _stream(fe, x, sizes):
    out, i = [], 0
    for n in sizes:
        out.append(fe.push(x[i:i + n])); i += n
    out.append(fe.push(x[i:]))
    return np.concatenate(out)


# ---------------------------------------------------------------- front end

def test_frame_count_and_width():
    fe = StreamingStereoMel()
    f = fe.push(np.zeros((SR, 2)))
    assert f.shape == (1 + (SR - 400) // 160, 3 * N_MELS) and f.dtype == np.float32


def test_chunking_does_not_change_frames():
    x = _scene()
    full = StreamingStereoMel().push(x)
    rng = np.random.default_rng(1)
    sizes = rng.integers(1, 900, size=60)
    assert np.array_equal(_stream(StreamingStereoMel(), x, sizes), full)


def test_frontend_is_causal():
    x = _scene()
    y = x.copy()
    cut = 12000
    y[cut:] = np.random.default_rng(5).standard_normal(y[cut:].shape)   # loud, different future
    fx, fy = StreamingStereoMel().push(x), StreamingStereoMel().push(y)
    done = (cut - 400) // 160 + 1          # frames whose window ends before the cut
    assert np.array_equal(fx[:done], fy[:done])
    assert not np.array_equal(fx[done:], fy[done:])


def test_whisper_frontend_is_not_causal():
    """Documents why a separate front end exists: whisper_norm uses the clip maximum."""
    x = np.zeros(SR) + 1e-4 * np.random.default_rng(0).standard_normal(SR)
    y = x.copy(); y[-1600:] += 0.9 * np.random.default_rng(1).standard_normal(1600)
    assert not np.allclose(log_mel(x)[:10], log_mel(y)[:10])


def test_mono_input_gives_zero_ild():
    f = StreamingStereoMel().push(synth.tone(1000, 0.3))
    assert np.allclose(f[:, 2 * N_MELS:], 0) and np.allclose(f[:, :N_MELS], f[:, N_MELS:2 * N_MELS])


@pytest.mark.parametrize("az,sign", [(60, 1), (90, 1), (-45, -1), (-90, -1), (120, 1), (-150, -1)])
def test_ild_baseline_reads_left_right(az, sign):
    x = synth.stereo_scene([{"kind": "groan", "start": 0.0, "length": 0.5, "azimuth": az}], 0.5)
    pan = ild_pan_estimate(StreamingStereoMel().push(x))
    assert np.sign(np.median(pan)) == sign


def test_amplitude_panning_is_front_back_blind():
    """Same features for a source 30 deg ahead-left and 150 deg behind-left (shown for this panner)."""
    a = synth.stereo_scene([{"kind": "hiss", "start": 0, "length": 0.4, "azimuth": 30}], 0.4)
    b = synth.stereo_scene([{"kind": "hiss", "start": 0, "length": 0.4, "azimuth": 150}], 0.4)
    assert np.allclose(StreamingStereoMel().push(a), StreamingStereoMel().push(b))


def test_rejects_bad_input():
    fe = StreamingStereoMel()
    with pytest.raises(ValueError):
        fe.push(np.zeros((10, 3)))
    with pytest.raises(TypeError):
        fe.push(np.zeros((10, 2), np.int16))
    with pytest.raises(ValueError):
        fe.push(np.full((10, 2), np.nan))


# ---------------------------------------------------------------- learned ear

def test_ear_receptive_field_and_size():
    s = CausalConvEarSpec()
    assert s.receptive_field_frames == 63 and abs(s.receptive_field_seconds - 0.63) < 1e-9
    assert s.parameter_count() == 3 * 240 * 128 + 128 + 4 * (3 * 128 * 128 + 128)


def test_ear_streaming_equals_full_pass():
    s = CausalConvEarSpec()
    w = init_ear_weights(s, seed=3)
    feats = StreamingStereoMel().push(_scene())
    full = CausalConvEar(s, w).push(feats)
    ear = CausalConvEar(s, w)
    rng = np.random.default_rng(2)
    parts, i = [], 0
    while i < len(feats):
        n = int(rng.integers(1, 9)); parts.append(ear.push(feats[i:i + n])); i += n
    assert np.allclose(np.concatenate(parts), full, atol=1e-5)


def test_ear_is_causal_and_sees_its_receptive_field():
    s = CausalConvEarSpec()
    w = init_ear_weights(s, seed=4)
    feats = StreamingStereoMel().push(_scene())
    changed = feats.copy(); t0 = 80
    changed[t0] += 3.0
    a, b = CausalConvEar(s, w).push(feats), CausalConvEar(s, w).push(changed)
    diff = np.abs(a - b).max(axis=1)
    assert np.all(diff[:t0] == 0)                                   # past untouched
    assert diff[t0] > 0 and diff[t0 + s.receptive_field_frames - 1] > 0


# ---------------------------------------------------------------- workspace window

def _window(n_slots=40):
    ear_spec = CausalConvEarSpec()
    spec = ModalityAdapterSpec(modality="audio", d_in=ear_spec.width, frame_period=0.01, downsample=5)
    return spec, AudioWindow(spec, init_weights(spec, seed=1), n_slots=n_slots)


def test_window_slots_are_one_tick_and_times_are_relative():
    spec, win = _window()
    assert abs(spec.slot_seconds - 0.05) < 1e-12
    win.push(np.ones((23, 128), np.float32))
    assert win.slots_done == 4                                   # 23 frames -> 4 full slots, 3 pending
    ws = win.workspace(now=0.23, pad_to=8)
    v = ws["valid"]
    assert v.tolist() == [True] * 4 + [False] * 4
    t = ws["coords"][v, 2]
    assert np.allclose(t, np.array([0.025, 0.075, 0.125, 0.175]) - 0.23) and np.all(t <= 0)
    assert np.all(ws["segment"] == [SEGMENTS["notebook"], SEGMENTS["audio"]])
    assert np.all(ws["tokens"][~v] == 0) and np.all(ws["coords"][~v] == 0)
    cv = ws["coord_valid"]                                       # Workspace v1: row/col absent
    assert cv.shape == (8, 3) and not cv[:, :2].any() and np.array_equal(cv[:, 2], v)


def test_window_keeps_only_last_slots_and_never_revises():
    spec, win = _window(n_slots=10)
    rng = np.random.default_rng(0)
    frames = rng.standard_normal((200, 128)).astype(np.float32)
    win.push(frames[:100]); first = win.workspace(now=1.0)["tokens"][-1].copy()
    win.push(frames[100:105])
    ws = win.workspace(now=1.05)
    assert ws["valid"].sum() == 10 and win.slots_done == 21
    assert np.array_equal(ws["tokens"][-2], first)
    with pytest.raises(ValueError):
        win.workspace(now=1.05, pad_to=5)


def test_window_chunking_matches_one_push():
    spec, a = _window()
    _, b = _window()
    frames = np.random.default_rng(1).standard_normal((97, 128)).astype(np.float32)
    a.push(frames)
    for i in range(0, 97, 7):
        b.push(frames[i:i + 7])
    assert np.array_equal(a.workspace(1.0)["tokens"], b.workspace(1.0)["tokens"])


def test_end_to_end_chunked_stream_shapes():
    ear_spec = CausalConvEarSpec()
    ear = CausalConvEar(ear_spec, init_ear_weights(ear_spec))
    fe = StreamingStereoMel()
    spec, win = _window()
    x = _scene()
    for i in range(0, len(x), 800):                                   # 50 ms chunks
        win.push(ear.push(fe.push(x[i:i + 800])))
    ws = win.workspace(now=len(x) / SR)
    assert ws["tokens"].shape == (40, 256) and ws["valid"].sum() == min(40, win.slots_done)


def test_latency_bound():
    b = hearing_latency_bound()
    assert abs(b["first_frame"] - 0.01) < 1e-12 and abs(b["total"] - 0.05) < 1e-12
