"""Shared helpers: numpy only (no scipy). 48 kHz. Everything is deterministic (fixed seeds)."""
import json, subprocess, wave
import numpy as np
SR = 48000

def write_wav(path, x, sr=SR):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1: x = x[:, None]
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as f:
        f.setnchannels(pcm.shape[1]); f.setsampwidth(2); f.setframerate(sr); f.writeframes(pcm.tobytes())

def read_wav(path):
    with wave.open(path, 'rb') as f:
        n, ch, sr = f.getnframes(), f.getnchannels(), f.getframerate()
        x = np.frombuffer(f.readframes(n), dtype='<i2').astype(np.float64) / 32768
    return (x.reshape(-1, ch) if ch > 1 else x), sr

def fft_filter(x, f_lo=None, f_hi=None, order=2):
    """zero-phase smooth band filter in the frequency domain (butterworth-like magnitude); circular, so loops stay seamless"""
    n = len(x); X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR); H = np.ones_like(f)
    if f_hi: H *= 1 / np.sqrt(1 + (f / f_hi) ** (2 * order))
    if f_lo: H *= 1 / np.sqrt(1 + (f_lo / np.maximum(f, 1e-3)) ** (2 * order))
    return np.fft.irfft(X * H, n)

def db(g): return 10 ** (g / 20)

def loudnorm_json(path, pre=''):
    f = (pre + ',' if pre else '') + 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json'
    p = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', f, '-f', 'null', '-'], capture_output=True, text=True, check=True)
    js = json.loads(p.stderr[p.stderr.rindex('{'): p.stderr.rindex('}') + 1])
    return {k: float(js[k]) for k in ('input_i', 'input_tp', 'input_lra', 'input_thresh')}
