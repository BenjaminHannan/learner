#!/usr/bin/env python3
"""Exp 256 -- the learned ear (235 v3 model / 235b gate), loaded once, on the Mac CPU.

Imports 235's model/tokenizer/parse/brake and 235b's greedy_scored/beam_eager/gate
unchanged. read(turn) returns the greedy reading, the brake's kept frames and, when
a tau is set, 235b's gate decision (question guard + margin).
"""
from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235_model as E  # noqa: E402
import claude_smolear235b_beam as B  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


class Ear:
    def __init__(self, ckpt, expect_sha=None, tau=None, k=None, threads=None, device="cpu"):
        ck = Path(ckpt)
        if not ck.is_absolute():
            ck = REPO / ck
        blob = ck.read_bytes()
        self.sha = hashlib.sha256(blob).hexdigest()
        if expect_sha and self.sha != expect_sha:
            raise SystemExit(f"ear checkpoint hash mismatch {self.sha}")
        if threads:
            torch.set_num_threads(int(threads))
        base = E.find_base_dir()
        self.tok = E.Tok(base / "tokenizer.json")
        m = E.SmolLM()
        from safetensors.torch import load as st_load
        m.load_state_dict(st_load(blob), strict=True)
        del blob
        self.m = m.to(device).to(torch.float32).eval()
        self.tau = tau
        self.k = k or B.K
        self.device = device
        B.greedy_scored(self.m, self.tok, "Hello there.")  # warm-up

    def read(self, turn):
        t0 = time.perf_counter()
        raw, lp, _ = B.greedy_scored(self.m, self.tok, turn)
        kept, dropped = E.brake(E.parse_frames(raw), turn)
        out = dict(raw=raw, lp=lp, kept=kept, dropped=dropped, beams=[], gate=None)
        if self.tau is not None:
            teach = any(f["act"] == "TEACH" for f in kept)
            if teach and not B.ends_q(turn):
                out["beams"] = B.beam_eager(self.m, self.tok, turn, k=self.k)
            g = B.gate(turn, raw, lp, out["beams"], self.tau)
            out["gate"] = g
        out["ms"] = (time.perf_counter() - t0) * 1000
        return out
