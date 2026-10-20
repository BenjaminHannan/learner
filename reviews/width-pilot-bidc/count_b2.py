"""Parameter counts for Bid C's B2 (custom_io `ledger`, cfg copy=True) at d256/4 heads and d384/6 heads. CPU only, no data.

  PYTHONPATH=. python3 reviews/width-pilot-bidc/count_b2.py            # B2 as the fleet parents are built (N_REG 9)
  PYTHONPATH=. python3 reviews/width-pilot-bidc/count_b2.py --caps     # option A's minimal caps: n_reg 36 (GEN 35 + EOS), max_ans 35, N_PLACE 37

Vocab: 13 specials + the 95 printable ASCII chars = 108 ids (the fleet B2 vocab size). Two non-embedding definitions are printed:
  ne_all    = total minus every nn.Embedding table (the Bid A / Item 0(a) definition);
  ne_reader = total minus the reader's tok / pos / place tables only.
"""
import sys
import torch
from custom_io import data
from custom_io.models import reader, ledger, build

caps = '--caps' in sys.argv
if caps:   # module globals, set before any model is built (what caps.apply does for these fields)
    data.set_max_ans(35)
    ledger.N_REG, ledger.GEN_MAX = 36, 35
    reader.N_PLACE = 37
vocab = data.CharVocab(''.join(chr(c) for c in range(32, 127)))
assert len(vocab) == 108, len(vocab)
rows = {}
for d, h in ((256, 4), (384, 6)):
    torch.manual_seed(0)
    m = build('ledger', vocab, copy=True, d=d, n_heads=h)
    tot = sum(p.numel() for p in m.parameters())
    emb = sum(mod.weight.numel() for mod in m.modules() if isinstance(mod, torch.nn.Embedding))
    rd = sum(p.numel() for n, p in m.named_parameters() if n.split('.')[0] == 'reader' and n.split('.')[1] in ('tok', 'pos', 'place'))
    rows[d] = dict(total=tot, ne_all=tot - emb, ne_reader=tot - rd)
    print(f'd{d}/{h} heads{" (caps)" if caps else ""}: total {tot:,}  ne_all {tot - emb:,}  ne_reader {tot - rd:,}')
for k in ('total', 'ne_all', 'ne_reader'):
    print(f'ratio {k}: {rows[384][k] / rows[256][k]:.4f}')
