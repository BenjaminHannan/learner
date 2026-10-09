"""Thinker, pointer heads and arms for the small talker check.

Pure PyTorch, no pretrained weights. Self-test: python models.py --selftest

Batch convention (all tensors on one device):
  states   float [B,T,768]  reader token states
  lens     long  [B]        valid tokens per row (>= 1)
  word_tok long  [B,W,2]    first/last token index per passage word, -1 padding
  n_words  long  [B]        valid words per row (<= W)

Arms:
  b0          Thinker(use_layers=True)  + PointerHead
  b0_nothinker Thinker(use_layers=False) + PointerHead
  p0          LinearProbe (no thinker, no question vector)
"""
import math
import sys

import torch
import torch.nn as nn
import torch.nn.functional as F

STATE_DIM = 768
NEG = -1e4
ARM_KINDS = ('b0', 'b0_nothinker', 'p0')


def _valid_tokens(lens, T):
    """Bool [B,T]: True for real tokens (t < lens[b])."""
    ar = torch.arange(T, device=lens.device)
    return ar[None, :] < lens[:, None]


def _word_means(note, lens, word_tok):
    """Mean of note over each word's token span. note [B,T,d] -> [B,W,d].

    Padding words (first == -1) and tokens at or beyond lens are excluded,
    so padding words come out as exact zero vectors.
    """
    B, T, _ = note.shape
    ar = torch.arange(T, device=note.device)
    first = word_tok[..., 0]                                   # [B,W]
    last = word_tok[..., 1]                                    # [B,W]
    m = (ar[None, None, :] >= first[..., None]) & (ar[None, None, :] <= last[..., None])
    m = m & (first >= 0)[..., None]
    m = m & _valid_tokens(lens, T)[:, None, :]
    m = m.to(note.dtype)
    cnt = m.sum(-1, keepdim=True).clamp(min=1.0)
    return torch.bmm(m / cnt, note)                            # [B,W,d]


def _mask_words(start, end, n_words):
    """Set start/end logits of word positions i >= n_words to NEG."""
    W = start.shape[1]
    ar = torch.arange(W, device=start.device)
    real = ar[None, :] < n_words[:, None]
    return start.masked_fill(~real, NEG), end.masked_fill(~real, NEG)


class Thinker(nn.Module):
    """Projection + learned positions + LayerNorm, then a looped pre-LN core.

    The same `layers` weights are applied `loops` times (shared, not unrolled).
    forward returns notes: notes[0] = projection output, notes[k] = state after
    loop k. With use_layers=False only notes[0] is returned.
    """

    def __init__(self, d=256, loops=3, layers=2, heads=4, ff=1024, dropout=0.1,
                 use_layers=True, t_max=64):
        super().__init__()
        assert d % heads == 0
        self.d = d
        self.loops = loops
        self.use_layers = use_layers
        self.t_max = t_max
        self.proj = nn.Linear(STATE_DIM, d)
        self.pos = nn.Embedding(t_max, d)
        self.norm_in = nn.LayerNorm(d)
        if use_layers:
            self.core = nn.ModuleList(
                [_PreLNLayer(d, heads, ff, dropout) for _ in range(layers)])

    def forward(self, states, lens):
        B, T, _ = states.shape
        assert T <= self.t_max, f'T={T} exceeds t_max={self.t_max}'
        pos = torch.arange(T, device=states.device)
        x = self.norm_in(self.proj(states) + self.pos(pos)[None])
        notes = [x]
        if self.use_layers:
            key_ok = _valid_tokens(lens, T).clone()
            key_ok[:, 0] = True          # guard: a row with lens==0 would be all-masked
            for _ in range(self.loops):
                for layer in self.core:  # shared weights, applied again each loop
                    x = layer(x, key_ok)
                notes.append(x)
        return notes


class _PreLNLayer(nn.Module):
    def __init__(self, d, heads, ff, dropout):
        super().__init__()
        self.heads = heads
        self.ln1 = nn.LayerNorm(d)
        self.qkv = nn.Linear(d, 3 * d)
        self.out = nn.Linear(d, d)
        self.ln2 = nn.LayerNorm(d)
        self.ff1 = nn.Linear(d, ff)
        self.ff2 = nn.Linear(ff, d)
        self.drop = nn.Dropout(dropout)

    def forward(self, x, key_ok):
        # key_ok: bool [B,T], True = this key may be attended (SDPA convention).
        B, T, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.heads, D // self.heads) \
            .permute(2, 0, 3, 1, 4)                            # each [B,H,T,dh]
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=key_ok[:, None, None, :])
        a = a.transpose(1, 2).reshape(B, T, D)
        x = x + self.drop(self.out(a))
        x = x + self.drop(self.ff2(self.drop(F.gelu(self.ff1(self.ln2(x))))))
        return x


class _SpanHeads(nn.Module):
    """Shared loss() and decode() for PointerHead and LinearProbe."""

    def __init__(self, span_max=12):
        super().__init__()
        self.span_max = span_max

    def loss(self, out, mode_y, start_y, end_y):
        loss = F.cross_entropy(out['mode_logits'], mode_y)
        has = start_y >= 0
        if has.any():
            loss = loss + F.cross_entropy(out['start_logits'][has], start_y[has])
            loss = loss + F.cross_entropy(out['end_logits'][has], end_y[has])
        else:
            loss = loss + (out['start_logits'].sum() + out['end_logits'].sum()) * 0.0
        return loss

    def decode(self, out, n_words):
        mode = out['mode_logits'].argmax(-1)                   # [B]
        s_log, e_log = out['start_logits'], out['end_logits']  # [B,W]
        B, W = s_log.shape
        ar = torch.arange(W, device=s_log.device)
        pair = s_log[:, :, None] + e_log[:, None, :]           # [B,s,e]
        gap = ar[None, :] - ar[:, None]                        # [s,e] = e - s
        ok_span = (gap >= 0) & (gap <= self.span_max - 1)
        real = ar[None, :] < n_words[:, None]                  # [B,W]
        ok = ok_span[None] & real[:, :, None] & real[:, None, :]
        pair = pair.masked_fill(~ok, float('-inf'))
        flat = pair.reshape(B, W * W).argmax(-1)
        s = torch.div(flat, W, rounding_mode='floor')
        e = flat - s * W
        is_span = (mode == 2) & (n_words > 0)
        minus = torch.full_like(s, -1)
        s = torch.where(is_span, s, minus)
        e = torch.where(is_span, e, minus)
        return mode, s, e


class PointerHead(_SpanHeads):
    """Attention-pool the last note, then unary start/end scores per word."""

    def __init__(self, d=256, span_max=12, dropout=0.1):
        super().__init__(span_max)
        self.d = d
        self.query = nn.Parameter(torch.randn(d) / math.sqrt(d))
        self.ln_h = nn.LayerNorm(d)
        self.drop = nn.Dropout(dropout)
        self.mode = nn.Linear(d, 3)
        self.start_h = nn.Linear(d, d)
        self.start_w = nn.Linear(d, d)
        self.end_h = nn.Linear(d, d)
        self.end_w = nn.Linear(d, d)

    def forward(self, notes, lens, word_tok, n_words):
        note = notes[-1]                                       # [B,T,d]
        B, T, d = note.shape
        score = (note @ self.query) / math.sqrt(d)             # [B,T]
        score = score.masked_fill(~_valid_tokens(lens, T), NEG)
        alpha = torch.softmax(score, dim=-1)
        h = self.ln_h(torch.einsum('bt,btd->bd', alpha, note))  # [B,d]
        w = _word_means(note, lens, word_tok)                  # [B,W,d]
        h_d, w_d = self.drop(h), self.drop(w)
        mode_logits = self.mode(h_d)
        sc = math.sqrt(d)
        start = torch.bmm(self.start_w(w_d), self.start_h(h_d)[:, :, None]).squeeze(-1) / sc
        end = torch.bmm(self.end_w(w_d), self.end_h(h_d)[:, :, None]).squeeze(-1) / sc
        start, end = _mask_words(start, end, n_words)
        return {'mode_logits': mode_logits, 'start_logits': start, 'end_logits': end}


class LinearProbe(_SpanHeads):
    """P0: unary heads straight on the frozen reader states.

    One shared Linear(768,d) feeds both the word means and the masked-mean
    pooled mode vector. No thinker, no question vector, no nonlinearity.
    """

    def __init__(self, d=256, span_max=12):
        super().__init__(span_max)
        self.inp = nn.Linear(STATE_DIM, d)
        self.mode = nn.Linear(d, 3)
        self.start = nn.Linear(d, 1)
        self.end = nn.Linear(d, 1)

    def forward(self, states, lens, word_tok, n_words):
        B, T, _ = states.shape
        x = self.inp(states)                                   # [B,T,d]
        valid = _valid_tokens(lens, T).to(x.dtype)
        h = (x * valid[..., None]).sum(1) / valid.sum(1, keepdim=True).clamp(min=1.0)
        w = _word_means(x, lens, word_tok)                     # [B,W,d]
        mode_logits = self.mode(h)
        start = self.start(w).squeeze(-1)
        end = self.end(w).squeeze(-1)
        start, end = _mask_words(start, end, n_words)
        return {'mode_logits': mode_logits, 'start_logits': start, 'end_logits': end}


class Arm(nn.Module):
    """One experimental arm: b0, b0_nothinker or p0."""

    def __init__(self, kind, d=256):
        super().__init__()
        if kind not in ARM_KINDS:
            raise ValueError(f'unknown kind {kind!r}; expected one of {ARM_KINDS}')
        self.kind = kind
        if kind == 'p0':
            self.thinker = None
            self.head = LinearProbe(d=d)
        else:
            self.thinker = Thinker(d=d, use_layers=(kind == 'b0'))
            self.head = PointerHead(d=d)

    def notes_of(self, states, lens):
        if self.thinker is None:
            raise ValueError('p0 has no thinker, so it has no notes')
        return self.thinker(states, lens)

    def forward(self, states, lens, word_tok, n_words, notes=None):
        if self.thinker is None:
            if notes is not None:
                raise ValueError('p0 takes no notes= argument')
            return self.head(states, lens, word_tok, n_words)
        if notes is None:
            notes = self.thinker(states, lens)
        return self.head(notes, lens, word_tok, n_words)

    def n_params(self):
        return sum(p.numel() for p in self.parameters())


def _selftest():
    import common  # sibling module; its SEED fixes the self-test RNG

    torch.manual_seed(common.SEED)
    B, T, W, D = 4, 20, 6, 256
    lens = torch.tensor([20, 15, 9, 5])
    n_words = torch.tensor([6, 4, 2, 1])
    word_tok = torch.full((B, W, 2), -1, dtype=torch.long)
    for b in range(B):
        pos = 0
        for i in range(int(n_words[b])):
            last = min(pos + (1 + i % 3) - 1, int(lens[b]) - 1)
            word_tok[b, i, 0] = pos
            word_tok[b, i, 1] = last
            pos = last + 1
    states = torch.randn(B, T, STATE_DIM)                      # tokens beyond lens are noise
    mode_y = torch.tensor([2, 0, 2, 1])
    start_y = torch.tensor([1, -1, 0, -1])                     # rows 1 and 3 have no span
    end_y = torch.tensor([2, -1, 0, -1])
    pad = torch.arange(W)[None] >= n_words[:, None]

    print(f'common.SEED={common.SEED} import OK', flush=True)

    for kind in ARM_KINDS:
        arm = Arm(kind, d=D)
        n = arm.n_params()
        print(f'[{kind}] n_params={n:,}', flush=True)
        if kind == 'b0':
            assert 1.6e6 <= n <= 2.2e6, f'b0 n_params {n} far from ~2.06M; check for unrolling'
        arm.train()
        out = arm(states, lens, word_tok, n_words)
        assert out['mode_logits'].shape == (B, 3)
        assert out['start_logits'].shape == (B, W) and out['end_logits'].shape == (B, W)
        print(f'[{kind}] shapes OK', flush=True)

        assert bool((out['start_logits'][pad] <= -1e3).all())
        assert bool((out['end_logits'][pad] <= -1e3).all())
        assert bool((out['start_logits'].argmax(-1) < n_words).all())
        assert bool((out['end_logits'].argmax(-1) < n_words).all())
        print(f'[{kind}] padding words masked and never win start/end argmax', flush=True)

        loss = arm.head.loss(out, mode_y, start_y, end_y)
        assert torch.isfinite(loss), loss
        arm.zero_grad()
        loss.backward()
        params = list(arm.named_parameters())
        missing = [nm for nm, p in params if p.grad is None]
        assert not missing, f'no grad for {missing}'
        print(f'[{kind}] train loss={loss.item():.4f} finite; grad non-None on all {len(params)} params', flush=True)

        arm.eval()
        with torch.no_grad():
            out = arm(states, lens, word_tok, n_words)
            mode, s, e = arm.head.decode(out, n_words)
            assert mode.shape == (B,) and s.shape == (B,) and e.shape == (B,)
            for b in range(B):
                if mode[b] == 2:
                    assert 0 <= s[b] <= e[b] <= s[b] + 11 and e[b] < n_words[b], (b, s[b], e[b])
                else:
                    assert s[b] == -1 and e[b] == -1
            forced = dict(out)
            ml = out['mode_logits'].clone()
            ml[:, 2] = 1e4
            forced['mode_logits'] = ml
            fm, fs, fe = arm.head.decode(forced, n_words)
            assert bool((fm == 2).all())
            assert bool(((fs >= 0) & (fs < n_words)).all()) and bool(((fe >= 0) & (fe < n_words)).all())
            assert bool(((fe >= fs) & (fe - fs <= 11)).all())
            for b in range(B):                                 # brute force over allowed pairs
                best, bs, be = -float('inf'), -1, -1
                for si in range(int(n_words[b])):
                    for ei in range(si, min(si + 12, int(n_words[b]))):
                        sc = float(out['start_logits'][b, si] + out['end_logits'][b, ei])
                        if sc > best:
                            best, bs, be = sc, si, ei
                assert (int(fs[b]), int(fe[b])) == (bs, be), (b, int(fs[b]), int(fe[b]), bs, be)
        print(f'[{kind}] decode shapes OK; forced span path matches brute force and honours s<=e<=s+11, e<n_words', flush=True)

    # Band check on a wide row: start peaked at word 0, end peaked at word 15.
    # Unconstrained best would be (0,15); with e-s<=11 the best is (0,11).
    head = PointerHead(d=D)
    syn = {
        'mode_logits': torch.tensor([[0.0, 0.0, 5.0]]),
        'start_logits': torch.zeros(1, 16),
        'end_logits': torch.zeros(1, 16),
    }
    syn['start_logits'][0, 0] = 10.0
    syn['end_logits'][0, 15] = 12.0
    syn['end_logits'][0, 11] = 9.0
    _, bs, be = head.decode(syn, torch.tensor([16]))
    assert int(bs[0]) == 0 and int(be[0]) == 11, (int(bs[0]), int(be[0]))
    print('band check: start=0 end=11 chosen over unconstrained (0,15) on W=16', flush=True)

    # Random W=16 brute force, including a row with n_words=0 (must give -1,-1).
    g = torch.Generator().manual_seed(common.SEED)
    rnd = {
        'mode_logits': torch.full((4, 3), 0.0),
        'start_logits': torch.randn(4, 16, generator=g),
        'end_logits': torch.randn(4, 16, generator=g),
    }
    rnd['mode_logits'][:, 2] = 1e4
    nw = torch.tensor([16, 9, 3, 0])
    _, rs, re_ = head.decode(rnd, nw)
    for b in range(4):
        n = int(nw[b])
        if n == 0:
            assert int(rs[b]) == -1 and int(re_[b]) == -1
            continue
        best, bs_, be_ = -float('inf'), -1, -1
        for si in range(n):
            for ei in range(si, min(si + 12, n)):
                sc = float(rnd['start_logits'][b, si] + rnd['end_logits'][b, ei])
                if sc > best:
                    best, bs_, be_ = sc, si, ei
        assert (int(rs[b]), int(re_[b])) == (bs_, be_), (b, int(rs[b]), int(re_[b]), bs_, be_)
    print('random W=16 decode matches brute force; n_words=0 gives (-1,-1)', flush=True)

    # Shuffle lesion: b0 with notes from another row must change the output.
    arm = Arm('b0', d=D).eval()
    with torch.no_grad():
        own = arm(states, lens, word_tok, n_words)
        notes = arm.notes_of(states, lens)
        assert len(notes) == 4 and all(nt.shape == (B, T, D) for nt in notes)
        same = arm(states, lens, word_tok, n_words, notes=notes)
        assert torch.allclose(own['start_logits'], same['start_logits'])
        assert torch.allclose(own['mode_logits'], same['mode_logits'])
        rolled = [nt.roll(1, dims=0) for nt in notes]
        swapped = arm(states, lens, word_tok, n_words, notes=rolled)
        diff = max(float((swapped[k] - own[k]).abs().max()) for k in own)
        assert diff > 1e-4, diff
    print(f'shuffle lesion: notes from another row change b0 output (max abs diff {diff:.4f}); notes= with own notes is identical', flush=True)

    nt_arm = Arm('b0_nothinker', d=D).eval()
    with torch.no_grad():
        assert len(nt_arm.notes_of(states, lens)) == 1
    print('b0_nothinker notes = [projection output] only', flush=True)

    p0 = Arm('p0', d=D)
    try:
        p0(states, lens, word_tok, n_words, notes=notes)
        raise AssertionError('p0 accepted notes=')
    except ValueError:
        pass
    print('p0 rejects notes= and has no notes_of (raises ValueError)', flush=True)

    print('models selftest OK', flush=True)


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        _selftest()
    else:
        print('usage: python models.py --selftest')
