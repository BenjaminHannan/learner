"""Audio input path for Premonition: numpy CPU reference (no torch).

frontend: Whisper-style log-mel features. adapter: the audio side of the
shared Workspace contract (PR #22 / PR #23). synth: test signals.
Design: design/next-parts/audio-input.md. These modules show the plumbing
works; they say nothing about whether reasoning over audio works.
"""
from .frontend import SAMPLE_RATE, N_FFT, HOP_LENGTH, N_MELS, log_mel, mel_filterbank, n_frames
from .adapter import (ModalityAdapterSpec, SEGMENTS, adapt, audio_segment, batch, check_output,
                      init_weights, sinusoid, to_core_layout)

__all__ = ["SAMPLE_RATE", "N_FFT", "HOP_LENGTH", "N_MELS", "log_mel", "mel_filterbank", "n_frames",
           "ModalityAdapterSpec", "SEGMENTS", "adapt", "audio_segment", "batch", "check_output",
           "init_weights", "sinusoid", "to_core_layout"]
