"""Shared shallow reader for the custom designs (A register loop, B ledger). Nothing pretrained, no attention.

x = E_char[id] + E_pos[t] + E_place[place]; place = a char's index from the right end of its word_spans token
(units digit 0, tens 1, ...; letters likewise), 15 for spaces/padding, clamped at 14. Then `layers` masked residual
blocks x + Conv1d_k5(GELU(LN x)) and a final LayerNorm. Receptive field: +-2 chars per block (+-4 with 2 blocks), so
every relation between words further apart has to be computed by the reasoner, not here.
Switches (default off = the above exactly): no_place (P1) leaves the place term out of the input (the table stays: the registers' starting vectors and the calculator's
operand cells are its rows); by_bytes (V1) makes positions and places count bytes (a non-ASCII char is several ids, each with its own position; place counts bytes from the
word's right end)."""
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from custom_io.data import MAX_PROMPT, ByteVocab, unit_spans, word_spans

N_PLACE = 16
PLACE_NONE = 15


def place_ids(prompts, T, device=None, by_bytes=False):
    """[B,T] long: index from the right end of each char's word token; PLACE_NONE for spaces and padding. by_bytes: one entry per UTF-8 byte (T counts bytes)."""
    out = torch.full((len(prompts), T), PLACE_NONE, dtype=torch.long)
    for b, p in enumerate(prompts):
        for a, e in (unit_spans(ByteVocab, p, word_spans(p)) if by_bytes else word_spans(p)):
            out[b, a:e] = torch.arange(e - a - 1, -1, -1).clamp(max=PLACE_NONE - 1)
    return out.to(device) if device is not None else out


def batch_places(batch, cache, by_bytes=False):
    """[B, T] long on batch['prompt_ids'].device: place ids for batch['rows'] prompts, PLACE_NONE for spaces and for
    padding out to prompt_ids' width (donor_eval may widen it). `cache` is a plain dict the caller owns: it holds one
    int8 numpy row per distinct prompt, so a shuffled batch costs one small copy per row instead of a regex pass."""
    ids = batch['prompt_ids']
    out = np.full((ids.shape[0], ids.shape[1]), PLACE_NONE, dtype=np.int64)
    for b, r in enumerate(batch['rows']):
        p = r['prompt']
        v = cache.get(p)
        if v is None:
            if len(cache) > 400_000:
                cache.clear()
            v = cache[p] = place_ids([p], ByteVocab.length(p) if by_bytes else len(p), by_bytes=by_bytes)[0].numpy().astype(np.int8)
        out[b, :len(v)] = v
    return torch.from_numpy(out).to(ids.device, non_blocking=True)


class ConvBlock(nn.Module):
    def __init__(self, d, k=5):
        super().__init__()
        self.ln = nn.LayerNorm(d)
        self.conv = nn.Conv1d(d, d, k, padding=k // 2)

    def forward(self, x, mask):
        h = F.gelu(self.ln(x)) * mask[..., None]
        return (x + self.conv(h.transpose(1, 2)).transpose(1, 2)) * mask[..., None]


class CharReader(nn.Module):
    def __init__(self, n_vocab, d, layers=2, k=5, letters=True, no_place=False, by_bytes=False):
        super().__init__()
        self.no_place, self.by_bytes = bool(no_place), bool(by_bytes)
        self.letters = letters      # False (Ledger letters_in=False): the letter table is not added to the input (the talker still uses it as its alphabet)
        self.tok, self.pos, self.place = nn.Embedding(n_vocab, d), nn.Embedding(MAX_PROMPT, d), nn.Embedding(N_PLACE, d)
        self.blocks = nn.ModuleList(ConvBlock(d, k) for _ in range(layers))
        self.ln = nn.LayerNorm(d)
        self._cache = {}

    def places(self, batch):
        """place ids for batch['rows'] prompts, padded to prompt_ids' width (see batch_places); cached per prompt."""
        return batch_places(batch, self._cache, self.by_bytes)

    def forward(self, batch, extra=None):
        """-> X [B,T,d] (zeros at padding), mask [B,T] bool. extra [B,T,d] (Ledger eg_embed) is added to the input embedding, before the conv blocks."""
        ids, mask = batch['prompt_ids'], batch['prompt_mask']
        x = self.pos(torch.arange(ids.shape[1], device=ids.device))
        if self.letters:
            x = self.tok(ids) + x           # same sum order as before: (tok + pos) + place
        if not self.no_place:
            x = x + self.place(self.places(batch))
        if extra is not None:
            x = x + extra
        x = x * mask[..., None]
        for blk in self.blocks:
            x = blk(x, mask)
        return self.ln(x) * mask[..., None], mask
