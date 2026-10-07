"""Speed only, no change to what is computed: fill the reader's per-prompt place-id cache with numpy instead of the reader's own per-row torch calls.
The values are the same as custom_io.models.reader.place_ids (integer bookkeeping, zero FLOPs either way); under the eval's FLOP counter each tiny torch
call costs Python dispatch time, and those calls were about two thirds of a fine-tune update's wall time."""
import numpy as np
from custom_io.data import word_spans
from custom_io.models.reader import PLACE_NONE


def place_row(p):
    v = np.full(len(p), PLACE_NONE, np.int8)
    for a, e in word_spans(p):
        v[a:e] = np.minimum(np.arange(e - a - 1, -1, -1), PLACE_NONE - 1)
    return v


def prefill(m, rows):
    cache = m.reader._cache
    for r in rows:
        p = r['prompt']
        if p not in cache:
            cache[p] = place_row(p)
