"""Shared by test_moe.py and the gold file: fixed rows, an EmbeddingGemma stub and a fingerprint (params, keys, tensor hashes, loss, aux, answers)."""
import hashlib
import torch
from custom_io.data import Dataset, collate
from custom_io.models.ledger import Ledger

SMALL = dict(d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0)
G3M = dict(d=256, n_heads=4, reader_layers=2, blocks=2, n_loops=12, mlp=4.8, copy=True, eg_embed=True)
_R = [('What is 12 + 30 ?', '42', 'arith_bare', ['12 + 30 = 42']), ('Echo: sune', 'sune', 'copy_word', []),
      ('Tom has 5 apples and gets 7 more . How many ?', '12', 'story_addsub', ['5 + 7 = 12']),
      ('What is 9 * 8 ?', '72', 'arith_bare', ['9 * 8 = 72']), ('Echo: marlo', 'marlo', 'copy_word', []),
      ('Ann has 20 pens and gives away 6 . How many are left ?', '14', 'story_addsub', ['20 - 6 = 14']),
      ('Is 7 + 5 = 13 true ?', 'no', 'verify_claim', ['7 + 5 = 12']), ('What is 100 - 37 ?', '63', 'arith_bare', ['100 - 37 = 63'])]


class StubEG:
    """Deterministic stand-in for models/eg.FrozenEG (same pattern as test_ledger_eg)."""
    def encode(self, prompts, T, device, chars=True):
        H, pooled = torch.zeros(len(prompts), T, 768), torch.zeros(len(prompts), 768)
        for b, p in enumerate(prompts):
            g = torch.Generator().manual_seed(int(hashlib.sha1(p.encode()).hexdigest()[:8], 16))
            n = min(len(p), T)
            H[b, :n] = torch.randn(n, 768, generator=g) * 40
            pooled[b] = torch.randn(768, generator=g)
        return (H.to(device) if chars else None), pooled.to(device)


def vocab():
    from custom_io.g8a import configs as C
    return C.vocab()


def batch(n=8, tag='c'):
    """tag: row-id prefix; progparse caches targets by id, so rows built before and after caps.apply need different tags ('u' = today's caps)."""
    rows = [dict(id=f'{tag}{i}', prompt=p, answer=a, accepted=[a], family=f, level=1, stage=1, variant='v', steps=st) for i, (p, a, f, st) in enumerate(_R[:n])]
    ds = Dataset(rows, vocab())
    return collate([ds[j] for j in range(len(rows))])


def make(cfg, seed=0, **kw):
    torch.manual_seed(seed)
    m = Ledger(vocab(), **{**cfg, **kw})
    if hasattr(m, '_eg'):
        m._eg = [StubEG()]
    return m


def tensor_hashes(m):
    return {k: hashlib.sha256(t.detach().contiguous().numpy().tobytes()).hexdigest() for k, t in m.state_dict().items()}


def fingerprint(m, b):
    sd = m.state_dict()
    loss, aux = m.loss(b)
    return dict(n_params=m.n_params(), keys=sorted(sd), hashes=tensor_hashes(m), loss=loss.item(), aux={k: float(v) for k, v in sorted(aux.items())},
                answers=m.generate(b))
