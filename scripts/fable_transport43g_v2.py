#!/usr/bin/env python3
"""Experiment 43G-v2: one change to the transport control — bounded address scores.

43G v1: 2 of 3 seeds failed to FIT one parity-dependent skill (SWAP or FOLD).  Cause seen in
the saved numbers: the soft choice among the six places had saturated at weight 1.0000 on one
place for every parity, so no gradient was left to split odd from even places.
Change: address score = 10 x cosine(query, key) instead of an unbounded dot product, so a
choice can never saturate completely.  Everything else is 43G v1, imported unchanged.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F

import fable_transport43g as T

SCALE = 10.0


def address(self) -> torch.Tensor:
    inp = torch.cat((self.op_embedding.weight[:, None].expand(-1, 4, -1),
                     T.BITS[None].expand(len(T.OPS), -1, -1)), dim=-1)
    q = self.query(inp).reshape(len(T.OPS), 4, 4, 40)[:, :, T.SLOT_HEAD]
    return (SCALE * (F.normalize(q, dim=-1) * F.normalize(self.keys, dim=-1)).sum(-1)).softmax(-1)


T.Transport.address = address

if __name__ == "__main__":
    T.main()
