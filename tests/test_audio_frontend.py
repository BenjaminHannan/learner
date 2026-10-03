"""Plumbing tests for the numpy log-mel frontend. They show the frontend is
wired correctly on synthetic signals; they say nothing about audio reasoning."""
import numpy as np
import pytest

from premonition.audio import frontend as F
from premonition.audio import synth as S


def test_constants_match_whisper_recipe():
    assert (F.SAMPLE_RATE, F.N_FFT, F.HOP_LENGTH, F.N_MELS) == (16000, 400, 160, 80)
    assert F.N_FFT / F.SAMPLE_RATE == 0.025 and F.HOP_LENGTH / F.SAMPLE_RATE == 0.010


def test_filterbank_shape_and_coverage():
    fb = F.mel_filterbank()
    assert fb.shape == (80, 201)
    assert np.all(fb >= 0)
    assert np.all(fb.max(axis=1) > 0)          # no empty filter
    centres = F.mel_center_hz()
    assert np.all(np.diff(centres) > 0) and centres[-1] < 8000


def test_slaney_scale_round_trip_and_knee():
    f = np.array([0.0, 200.0, 999.0, 1000.0, 3000.0, 8000.0])
    assert np.allclose(F.mel_to_hz(F.hz_to_mel(f)), f)
    assert np.isclose(F.hz_to_mel(1000.0), 15.0)  # Slaney: linear part reaches 15 mel at 1 kHz


@pytest.mark.parametrize("seconds", [0.01, 0.5, 1.0, 1.2345, 3.0])
def test_frame_count_arithmetic(seconds):
    x = S.tone(440, seconds)
    m = F.log_mel(x)
    assert m.shape == (F.n_frames(len(x)), 80) == (len(x) // 160, 80)
    assert m.dtype == np.float32 and np.all(np.isfinite(m))


def test_thirty_seconds_gives_3000_frames():
    # Whisper's N_FRAMES for a 30 s chunk is 3000 (whisper/audio.py).
    assert F.n_frames(30 * 16000) == 3000


@pytest.mark.parametrize("freq", [250.0, 500.0, 1000.0, 2000.0, 4000.0, 6000.0])
def test_sine_lands_in_nearest_mel_bin(freq):
    m = F.log_mel(S.tone(freq, 1.0))
    peak = int(np.argmax(m[10:-10].mean(axis=0)))
    expected = int(np.argmin(np.abs(F.mel_center_hz() - freq)))
    assert abs(peak - expected) <= 1


def test_higher_tone_peaks_in_higher_bin():
    lo = np.argmax(F.log_mel(S.tone(300, 1.0)).mean(0))
    hi = np.argmax(F.log_mel(S.tone(3000, 1.0)).mean(0))
    assert hi > lo


def test_chirp_peak_rises_over_time():
    m = F.log_mel(S.chirp(200, 6000, 2.0))
    peaks = m.argmax(axis=1)[5:-5]
    early, late = peaks[: len(peaks) // 4].mean(), peaks[-len(peaks) // 4:].mean()
    assert late > early + 20


def test_deterministic():
    x = S.noise_burst(1.0, 0.3, 0.2, seed=7)
    assert np.array_equal(F.log_mel(x), F.log_mel(x.copy()))
    assert np.array_equal(S.noise_burst(1.0, 0.3, 0.2, seed=7), x)
    assert not np.array_equal(S.noise_burst(1.0, 0.3, 0.2, seed=8), x)


def test_noise_burst_localised_in_time():
    m = F.log_mel(S.noise_burst(1.0, 0.4, 0.2, seed=1), whisper_norm=False)
    energy = m.mean(axis=1)
    inside = energy[45:55].mean()
    outside = np.concatenate([energy[5:30], energy[70:95]]).mean()
    assert inside > outside + 5   # log10 units


def test_silence_vs_tone_separable_by_mean_energy():
    feats = lambda x: F.log_mel(x, whisper_norm=False).mean()
    quiet = [feats(S.silence(0.5)), feats(S.silence(1.0))]
    loud = [feats(S.tone(f, 0.5, amp=0.05)) for f in (200, 1000, 5000)]
    assert max(quiet) < min(loud)


def test_whisper_norm_range():
    m = F.log_mel(S.syllables(4))
    assert m.max() - m.min() <= 2.0 + 1e-6    # 8 log10 units / 4


def test_input_validation():
    with pytest.raises(ValueError):
        F.log_mel(np.zeros((2, 100)))
    with pytest.raises(TypeError):
        F.log_mel(np.zeros(100, dtype=np.int16))
    with pytest.raises(ValueError):
        F.log_mel(np.array([0.0, np.nan] * 200))
