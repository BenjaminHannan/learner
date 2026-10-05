"""Shared shallow reader for the custom designs (A register loop, B ledger). Nothing pretrained, no attention.

x = E_char[id] + E_pos[t] + E_place[place]; place = a char's index from the right end of its word_spans token
(units digit 0, tens 1, ...; letters likewise), 15 for spaces/padding, clamped at 14. Then `layers` masked residual
blocks x + Conv1d_k5(GELU(LN x)) and a final LayerNorm. Receptive field: +-2 chars per block (+-4 with 2 blocks), so
every relation between words further apart has to be computed by the reasoner, not here."""
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from custom_io.data import MAX_PROMPT, word_spans

N_PLACE = 16
PLACE_NONE = 15


def place_ids(prompts, T, device=None):
    """[B,T] long: index from the right end of each char's word token; PLACE_NONE for spaces and padding."""
    out = torch.full((len(prompts), T), PLACE_NONE, dtype=torch.long)
    for b, p in enumerate(prompts):
        for a, e in word_spans(p):
            out[b, a:e] = torch.arange(e - a - 1, -1, -1).clamp(max=PLACE_NONE - 1)
    return out.to(device) if device is not None else out


class ConvBlock(nn.Module):
    def __init__(self, d, k=5):
        super().__init__()
        self.ln = nn.LayerNorm(d)
        self.conv = nn.Conv1d(d, d, k, padding=k // 2)

    def forward(self, x, mask):
        h = F.gelu(self.ln(x)) * mask[..., None]
        return (x + self.conv(h.transpose(1, 2)).transpose(1, 2)) * mask[..., None]


class CharReader(nn.Module):
    def __init__(self, n_vocab, d, layers=2, k=5):
        super().__init__()
        self.tok, self.pos, self.place = nn.Embedding(n_vocab, d), nn.Embedding(MAX_PROMPT, d), nn.Embedding(N_PLACE, d)
        self.blocks = nn.ModuleList(ConvBlock(d, k) for _ in range(layers))
        self.ln = nn.LayerNorm(d)
        self._cache = {}

    def places(self, batch):
        """place ids for batch['rows'] prompts, padded to prompt_ids' width (donor_eval may widen it). Cached per prompt
        (int8 numpy rows), so a shuffled batch costs one small copy per row instead of a regex pass."""
        ids = batch['prompt_ids']
        out = np.full((ids.shape[0], ids.shape[1]), PLACE_NONE, dtype=np.int64)
        for b, r in enumerate(batch['rows']):
            p = r['prompt']
            v = self._cache.get(p)
            if v is None:
                if len(self._cache) > 400_000:
                    self._cache.clear()
                v = self._cache[p] = place_ids([p], len(p))[0].numpy().astype(np.int8)
            out[b, :len(v)] = v
        return torch.from_numpy(out).to(ids.device, non_blocking=True)

    def forward(self, batch):
        """-> X [B,T,d] (zeros at padding), mask [B,T] bool."""
        ids, mask = batch['prompt_ids'], batch['prompt_mask']
        x = self.tok(ids) + self.pos(torch.arange(ids.shape[1], device=ids.device)) + self.place(self.places(batch))
        x = x * mask[..., None]
        for blk in self.blocks:
            x = blk(x, mask)
        return self.ln(x) * mask[..., None], mask
