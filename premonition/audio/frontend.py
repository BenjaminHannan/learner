"""Pure-numpy log-mel frontend (CPU reference, no torch).

Constants follow the Whisper recipe. SHOWN (read from openai/whisper
whisper/audio.py on 2026-10-03): SAMPLE_RATE=16000, N_FFT=400 (25 ms),
HOP_LENGTH=160 (10 ms), Hann window, torch.stft (default center=True,
reflect padding), power spectrum ``|X|**2`` with the last frame dropped,
mel filters made by ``librosa.filters.mel(sr=16000, n_fft=400, n_mels=80)``,
then ``log10(clamp(mel, 1e-10))``, floor at ``max - 8``, ``(x + 4) / 4``.

The Slaney mel scale and Slaney area normalisation below are re-implemented
from librosa's source (librosa/filters.py ``mel`` and core/convert.py
``hz_to_mel``; defaults htk=False, norm="slaney", fmin=0, fmax=sr/2).

UNTESTED: bit-for-bit equality with Whisper's stored ``mel_filters.npz`` or
with torch.stft output. We did not download either here. The torch.stft
defaults (center=True, pad_mode="reflect", periodic Hann) are from memory of
the torch docs, not re-checked today. Treat this as "Whisper-style", and run
the parity check in design/next-parts/audio-input.md (experiment A0) before
feeding these features to a real Whisper encoder.
"""
from __future__ import annotations

import numpy as np

SAMPLE_RATE = 16000
N_FFT = 400          # 25 ms window at 16 kHz
HOP_LENGTH = 160     # 10 ms hop at 16 kHz
N_MELS = 80
FRAME_RATE_HZ = SAMPLE_RATE / HOP_LENGTH  # 100 frames per second


def _check_audio(audio: np.ndarray) -> np.ndarray:
    a = np.asarray(audio)
    if a.ndim != 1:
        raise ValueError(f"audio must be 1-D mono samples, got shape {a.shape}")
    if not np.issubdtype(a.dtype, np.floating):
        raise TypeError(f"audio must be floating point in [-1, 1], got {a.dtype}")
    if a.size == 0:
        raise ValueError("audio is empty")
    if not np.all(np.isfinite(a)):
        raise ValueError("audio contains NaN or inf")
    return a.astype(np.float64, copy=False)


def hann_window(n: int = N_FFT) -> np.ndarray:
    """Periodic Hann window (the form torch.hann_window returns by default)."""
    k = np.arange(n, dtype=np.float64)
    return 0.5 - 0.5 * np.cos(2.0 * np.pi * k / n)


def hz_to_mel(f):
    """Slaney mel scale (librosa htk=False)."""
    f = np.asarray(f, dtype=np.float64)
    f_sp = 200.0 / 3
    mels = f / f_sp
    min_log_hz = 1000.0
    min_log_mel = min_log_hz / f_sp
    logstep = np.log(6.4) / 27.0
    return np.where(f >= min_log_hz,
                    min_log_mel + np.log(np.maximum(f, 1e-12) / min_log_hz) / logstep,
                    mels)


def mel_to_hz(m):
    m = np.asarray(m, dtype=np.float64)
    f_sp = 200.0 / 3
    freqs = f_sp * m
    min_log_hz = 1000.0
    min_log_mel = min_log_hz / f_sp
    logstep = np.log(6.4) / 27.0
    return np.where(m >= min_log_mel, min_log_hz * np.exp(logstep * (m - min_log_mel)), freqs)


def mel_filterbank(sr: int = SAMPLE_RATE, n_fft: int = N_FFT, n_mels: int = N_MELS,
                   fmin: float = 0.0, fmax: float | None = None) -> np.ndarray:
    """[n_mels, n_fft//2+1] triangular filters, Slaney scale and Slaney area norm."""
    fmax = sr / 2 if fmax is None else fmax
    fftfreqs = np.linspace(0, sr / 2, n_fft // 2 + 1)
    mel_f = mel_to_hz(np.linspace(hz_to_mel(fmin), hz_to_mel(fmax), n_mels + 2))
    fdiff = np.diff(mel_f)
    ramps = np.subtract.outer(mel_f, fftfreqs)
    weights = np.zeros((n_mels, len(fftfreqs)))
    for i in range(n_mels):
        lower = -ramps[i] / fdiff[i]
        upper = ramps[i + 2] / fdiff[i + 1]
        weights[i] = np.maximum(0, np.minimum(lower, upper))
    weights *= (2.0 / (mel_f[2:n_mels + 2] - mel_f[:n_mels]))[:, None]
    return weights


def mel_center_hz(sr: int = SAMPLE_RATE, n_mels: int = N_MELS) -> np.ndarray:
    """Centre frequency (Hz) of each mel filter, for tests and plots."""
    return mel_to_hz(np.linspace(hz_to_mel(0.0), hz_to_mel(sr / 2), n_mels + 2))[1:-1]


def n_frames(n_samples: int, hop: int = HOP_LENGTH, drop_last: bool = True) -> int:
    """Frame count for center=True STFT: 1 + n//hop, minus one if drop_last."""
    if n_samples <= 0:
        raise ValueError("n_samples must be positive")
    return 1 + n_samples // hop - (1 if drop_last else 0)


def power_spectrogram(audio: np.ndarray, n_fft: int = N_FFT, hop: int = HOP_LENGTH,
                      drop_last: bool = True) -> np.ndarray:
    """[n_frames, n_fft//2+1] power spectrum, centered frames with reflect padding."""
    a = _check_audio(audio)
    pad = n_fft // 2
    if a.size <= pad:
        # numpy reflect padding needs more samples than the pad; edge-pad first.
        a = np.pad(a, (0, pad + 1 - a.size))
    padded = np.pad(a, (pad, pad), mode="reflect")
    count = 1 + (padded.size - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(count)[:, None]
    frames = padded[idx] * hann_window(n_fft)[None, :]
    power = np.abs(np.fft.rfft(frames, axis=-1)) ** 2
    expected = n_frames(len(np.asarray(audio)), hop, drop_last=False)
    power = power[:expected]
    return power[:-1] if drop_last and len(power) > 1 else power


def log_mel(audio: np.ndarray, n_mels: int = N_MELS, whisper_norm: bool = True) -> np.ndarray:
    """[n_frames, n_mels] float32 log-mel features, 100 frames/s.

    Output contract: frame i covers samples centred at i*HOP_LENGTH; values
    are finite. With whisper_norm the dynamic range is clipped to 8 (log10)
    below the clip's own maximum and rescaled by (x+4)/4, so a whole-clip
    statistic is used: features of a frame depend on the loudest frame.
    """
    power = power_spectrogram(audio)
    mel = power @ mel_filterbank(n_mels=n_mels).T
    out = np.log10(np.maximum(mel, 1e-10))
    if whisper_norm:
        out = np.maximum(out, out.max() - 8.0)
        out = (out + 4.0) / 4.0
    return out.astype(np.float32)
