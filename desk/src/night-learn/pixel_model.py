"""Experimental native-action head for the HANDS pixel encoder.

This is a building block, not a deployed controller or a training entrypoint.
It does not write weights. Position labels are normalized screen coordinates.
"""
import hashlib
import importlib.util
import re
from pathlib import Path

import torch
from torch import nn
import torch.nn.functional as F

# Use the same encoder and recurrent memory as the existing HANDS policy.
_POLICY = Path(__file__).resolve().parents[2] / 'tools' / 'hands-toy' / 'policy.py'
_spec = importlib.util.spec_from_file_location('hands_toy_policy', _POLICY)
_policy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_policy)

KINDS = ('click', 'drag', 'key', 'scroll')
KEY_COUNT = 256
INTENT_SIZE = 64


def intent_vector(text):
    """Deterministic signed token hash of the supplied intent text."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError('intent text required')
    vector = torch.zeros(INTENT_SIZE)
    tokens = re.findall(r'\w+', text.casefold())[:256]
    for token in tokens:
        digest = hashlib.sha256(token.encode('utf-8')).digest()
        vector[int.from_bytes(digest[:4], 'big') % INTENT_SIZE] += 1 if digest[4] & 1 else -1
    return F.normalize(vector, dim=0) if tokens else vector


class NativeActionPolicy(nn.Module):
    def __init__(self, toy_state=None):
        super().__init__()
        toy = _policy.PixelPolicy()
        if toy_state is not None:
            toy.load_state_dict(toy_state, strict=True)
        self.encoder = toy.encoder
        self.overview = toy.overview
        self.detail = toy.detail
        self.memory = toy.memory
        self.kind = nn.Linear(512, len(KINDS))
        self.position = nn.Linear(512, 4)  # start x/y and end x/y
        self.key = nn.Linear(512, KEY_COUNT)
        self.scroll = nn.Linear(512, 2)

    def forward(self, image, crop, intent, own, hidden=None):
        overview = self.overview(F.adaptive_avg_pool2d(self.encoder(image), (6, 10)))
        detail = self.detail(F.adaptive_avg_pool2d(self.encoder(crop), (3, 3)))
        state = self.memory(torch.cat((overview, detail, intent, own), dim=1), hidden)
        return {'kind': self.kind(state), 'position': self.position(state).sigmoid(),
                'key': self.key(state), 'scroll': self.scroll(state)}, state


def action_loss(prediction, labels, weights):
    """Per-example loss; corrections can carry weight 3 after verification."""
    kinds = labels['kind']
    if torch.any((weights <= 0) | ~torch.isfinite(weights)):
        raise ValueError('invalid example weights')
    loss = F.cross_entropy(prediction['kind'], kinds, reduction='none')
    position = F.smooth_l1_loss(prediction['position'], labels['position'], reduction='none')
    click = (kinds == KINDS.index('click')).float()
    drag = (kinds == KINDS.index('drag')).float()
    key = (kinds == KINDS.index('key')).float()
    scroll = (kinds == KINDS.index('scroll')).float()
    loss = loss + (click + drag) * position[:, :2].mean(dim=1) + drag * position[:, 2:].mean(dim=1)
    loss = loss + key * F.cross_entropy(prediction['key'], labels['key'], reduction='none')
    loss = loss + scroll * F.smooth_l1_loss(prediction['scroll'], labels['scroll'], reduction='none').mean(dim=1)
    return (loss * weights).sum() / weights.sum()
