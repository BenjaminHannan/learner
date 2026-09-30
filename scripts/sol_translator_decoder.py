#!/usr/bin/env python3
"""Thin, fresh-weight, pointwise state -> symbolic token translator.
No head shortcut, sequence mixing, teacher forcing, text targets or executor.
"""
from __future__ import annotations
import sys
from pathlib import Path
import torch
from torch import nn
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.sol_stop_adapter import FinalLatent


def validate_final(final):
    if type(final) is not FinalLatent:
        raise TypeError('decoder accepts FinalLatent only; StopRun/audit/raw examples forbidden')
    final.__post_init__()
    if final.latent.grad_fn is not None or not bool(final.answer_mask.any(1).all()):
        raise ValueError('detached state and nonempty answer mask required')
    if final.latent_mask.requires_grad or final.answer_mask.requires_grad:
        raise ValueError('metadata must be detached')
    return final


def select_final(final, ids):
    validate_final(final)
    return FinalLatent(final.latent[ids],final.latent_mask[ids],final.answer_mask[ids],final.token_shape)


def masked_normalize(final):
    h=final.latent.float(); mask=final.latent_mask.float()
    count=mask.sum(-1,keepdim=True).clamp_min(1)
    mean=(h*mask).sum(-1,keepdim=True)/count
    var=((h-mean).square()*mask).sum(-1,keepdim=True)/count
    return (h-mean)*torch.rsqrt(var+1e-5)*mask


class ThinDecoder(nn.Module):
    def __init__(self, state_width, hidden=32, vocab=125):
        super().__init__()
        self.state_width, self.vocab = state_width, vocab
        self.scale = nn.Parameter(torch.ones(state_width))
        self.bias = nn.Parameter(torch.zeros(state_width))
        self.project = nn.Linear(state_width + 3, hidden)
        self.output = nn.Linear(hidden, vocab)

    def forward(self, packet):
        validate_final(packet)
        h, (rows, cols), slots = packet.latent, packet.token_shape, packet.answer_mask
        if h.shape[-1] != self.state_width:
            raise ValueError('wrong state width')
        r = torch.arange(rows, device=h.device).repeat_interleave(cols).float() / max(rows - 1, 1)
        c = torch.arange(cols, device=h.device).repeat(rows).float() / max(cols - 1, 1)
        geometry = torch.stack((r, c), -1)[None].expand(len(h), -1, -1)
        x = torch.cat((masked_normalize(packet)*self.scale+self.bias, geometry, slots[..., None].float()), -1)
        # Each output cell depends on ONE state cell, plus fixed geometry/slots.
        return self.output(torch.nn.functional.gelu(self.project(x)))

    def parameter_count(self):
        return sum(p.numel() for p in self.parameters())


def exact_flags(predictions, targets, slots):
    if predictions.shape != targets.shape or slots.shape != targets.shape:
        raise ValueError('scoring shape mismatch')
    return ((predictions == targets) | ~slots.bool()).all(-1)


def numeric_output(predictions, slots):
    """Literal token IDs in fill-slot order; no model-authored answer frames."""
    return [[int(t) for t in p[s.bool()].tolist()] for p, s in zip(predictions, slots)]
