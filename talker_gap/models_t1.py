"""T1 talker (SPEC row T1, Amendment 2): autoregressive char-level pointer-generator decoder.

Everything the model does is learned; this file only defines the network, the vocabulary builder,
the teacher-forced loss and two greedy decoders (incremental with a per-layer self-attention cache,
and a full-recompute reference). Nothing here touches evaluation data.

Shapes (B = batch, N = memory slots, P = prompt chars, T = reader-token slots per row):
  memory      [B, N, 256]   thinker notes; any N (e.g. 3 loops x T tokens stacked)
  mem_mask    [B, N] bool   True = real slot
  mem_tok     [B, N] long   reader-token index of each memory slot (-1 = none)
  prompt_ids  [B, P] long   char ids of the prompt (PAD = 0 for padding)
  prompt_mask [B, P] bool
  tok_off     [B, T, 2] long  (start, end) char span of each reader token inside the prompt, (0, 0) = padding
                              (same layout as prep_states.py tok_off_<split>.npy, cast to long)

Pointer keys for a prompt char c inside reader token t:
  key = note_proj(mean of the memory slots of token t) + char_emb[c] + tok_pos_emb[offset of c inside t]
  value = char_emb[c];  chars inside no token get a zero note and a dedicated "no token" position id.
"""
import argparse
import math
import random
import statistics
import string
import time

import torch
import torch.nn as nn
import torch.nn.functional as F

D, FF, LAYERS, HEADS = 256, 1024, 4, 4
DH = D // HEADS
PAD, BOS, EOS, UNK = 0, 1, 2, 3
SPECIALS = ['<pad>', '<bos>', '<eos>', '<unk>']
POS_CLIP = 16        # within-token offset embedding 0..15 (clipped); index POS_CLIP = char not in any token
NEG = -1e9


def build_vocab(strings):
    """Vocabulary = 4 specials + every printable character seen in `strings` (sorted).
    Any other character is mapped to UNK by encode()."""
    seen = sorted({c for s in strings for c in s if c.isprintable()})
    itos = SPECIALS + seen
    stoi = {c: i for i, c in enumerate(itos)}
    return stoi, itos


def encode_text(text, stoi):
    return [stoi.get(c, UNK) for c in text]


def decode_ids(ids, itos):
    """Characters up to the first EOS; other specials are dropped."""
    out = []
    for i in ids:
        if i == EOS:
            break
        if i >= len(SPECIALS):
            out.append(itos[i])
    return ''.join(out)


def make_teacher(targets, max_target_len):
    """targets: list of char-id lists (no EOS). Returns (tgt_in, tgt_out, tgt_mask).
    tgt_in = [BOS] + target, tgt_out = target + [EOS]. Raises (never truncates) if a target is too long."""
    for i, t in enumerate(targets):
        if len(t) > max_target_len:
            raise ValueError(f'target {i} has {len(t)} chars > max_target_len={max_target_len}; '
                             'filter it out, do not truncate')
    B = len(targets)
    L = max(len(t) for t in targets) + 1
    tin = torch.full((B, L), PAD, dtype=torch.long)
    tout = torch.full((B, L), PAD, dtype=torch.long)
    mask = torch.zeros((B, L), dtype=torch.bool)
    for b, t in enumerate(targets):
        n = len(t)
        tin[b, 0] = BOS
        if n:
            tin[b, 1:n + 1] = torch.tensor(t, dtype=torch.long)
            tout[b, :n] = torch.tensor(t, dtype=torch.long)
        tout[b, n] = EOS
        mask[b, :n + 1] = True
    return tin, tout, mask


class _Attn(nn.Module):
    def __init__(self):
        super().__init__()
        self.q = nn.Linear(D, D)
        self.k = nn.Linear(D, D)
        self.v = nn.Linear(D, D)
        self.o = nn.Linear(D, D)

    @staticmethod
    def split(x):  # [B, S, D] -> [B, H, S, DH]
        B, S, _ = x.shape
        return x.view(B, S, HEADS, DH).transpose(1, 2)

    def forward(self, xq, k, v, add_mask):
        # fused attention (fewer small ops per step; the decode is op-overhead bound on CPU)
        B, Tq, _ = xq.shape
        q = self.q(xq).view(B, Tq, HEADS, DH).transpose(1, 2)    # [B, H, Tq, DH]
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=add_mask)
        return self.o(a.transpose(1, 2).reshape(B, Tq, D))


class _Layer(nn.Module):
    """Pre-LN decoder layer: causal self-attention, cross-attention over the notes, FFN."""
    def __init__(self):
        super().__init__()
        self.ln1 = nn.LayerNorm(D)
        self.ln2 = nn.LayerNorm(D)
        self.ln3 = nn.LayerNorm(D)
        self.sa = _Attn()
        self.ca = _Attn()
        self.ff = nn.Sequential(nn.Linear(D, FF), nn.GELU(), nn.Linear(FF, D))


class T1Talker(nn.Module):
    def __init__(self, vocab_size, max_target_len=128):
        super().__init__()
        self.V = vocab_size
        self.max_target_len = max_target_len
        self.char_emb = nn.Embedding(vocab_size, D, padding_idx=PAD)
        self.pos_emb = nn.Embedding(max_target_len + 1, D)
        self.layers = nn.ModuleList([_Layer() for _ in range(LAYERS)])
        self.ln_f = nn.LayerNorm(D)
        self.mem_ln = nn.LayerNorm(D)
        self.out = nn.Linear(D, vocab_size)
        # pointer / copy branch
        self.note_proj = nn.Linear(D, D)
        self.tok_pos_emb = nn.Embedding(POS_CLIP + 1, D)
        self.ptr_q = nn.Linear(D, D)
        self.gate = nn.Linear(2 * D, 1)
        bias = torch.zeros(vocab_size)
        bias[PAD] = -1e4
        bias[BOS] = -1e4
        self.register_buffer('bias_pb', bias)
        for emb in (self.char_emb, self.pos_emb, self.tok_pos_emb):
            nn.init.normal_(emb.weight, std=0.1)
        if self.char_emb.padding_idx is not None:
            with torch.no_grad():
                self.char_emb.weight[PAD].zero_()

    # ---- prompt geometry -------------------------------------------------------------------
    @staticmethod
    def _char_token_index(tok_off, P):
        """tok_off [B,T,2] -> (prompt_tok [B,P] token index or T if none, prompt_pos [B,P] offset or POS_CLIP)."""
        B, T, _ = tok_off.shape
        start, end = tok_off[..., 0], tok_off[..., 1]
        j = torch.arange(P, device=tok_off.device)
        inside = ((j[None, :, None] >= start[:, None, :]) & (j[None, :, None] < end[:, None, :])
                  & (end > start)[:, None, :])                                   # [B,P,T]
        has = inside.any(-1)
        t_idx = inside.long().argmax(-1)                                         # first matching token
        s = torch.gather(start, 1, t_idx)                                        # [B,P]
        pos = (j[None, :] - s).clamp(0, POS_CLIP - 1)
        prompt_tok = torch.where(has, t_idx, torch.full_like(t_idx, T))
        prompt_pos = torch.where(has, pos, torch.full_like(pos, POS_CLIP))
        return prompt_tok, prompt_pos

    # ---- encoder side (done once per prompt) ----------------------------------------------
    def encode(self, memory, mem_mask, mem_tok, prompt_ids, prompt_mask, tok_off):
        B, N, _ = memory.shape
        T = tok_off.shape[1]
        P = prompt_ids.shape[1]
        valid = mem_mask & (mem_tok >= 0) & (mem_tok < T)
        idx = torch.where(valid, mem_tok, torch.full_like(mem_tok, T))
        sums = memory.new_zeros(B, T + 1, D).scatter_add(
            1, idx[..., None].expand(-1, -1, D), memory * valid[..., None].to(memory.dtype))
        cnt = memory.new_zeros(B, T + 1).scatter_add(1, idx, valid.to(memory.dtype))
        tok_note = sums / cnt.clamp_min(1.0)[..., None]
        keep = (torch.arange(T + 1, device=memory.device) < T).to(memory.dtype)
        tok_note = tok_note * keep[None, :, None]                                # row T = zero note
        prompt_tok, prompt_pos = self._char_token_index(tok_off, P)
        note_c = torch.gather(tok_note, 1, prompt_tok[..., None].expand(-1, -1, D))
        E = self.char_emb(prompt_ids)                                            # values = char embeddings
        K = self.note_proj(note_c) + E + self.tok_pos_emb(prompt_pos)           # pointer keys
        mem_n = self.mem_ln(memory)
        cross = [(layer.ca.split(layer.ca.k(mem_n)), layer.ca.split(layer.ca.v(mem_n)))
                 for layer in self.layers]
        return {
            'B': B,
            'prompt_ids': prompt_ids,
            'prompt_bias': torch.where(prompt_mask, 0.0, NEG).to(memory.dtype),  # [B,P]
            'K': K,
            'E': E,
            'cross': cross,
            'mem_bias': torch.where(mem_mask, 0.0, NEG).to(memory.dtype)[:, None, None, :],
        }

    # ---- output mixture ----------------------------------------------------------------------
    def _mix(self, h, enc):
        """h [B,L,D] (after ln_f). Returns logp [B,L,V], p_gen [B,L], alpha [B,L,P]."""
        B, L, _ = h.shape
        P = enc['K'].shape[1]
        logp_v = F.log_softmax(self.out(h) + self.bias_pb, -1)                   # [B,L,V]
        s = self.ptr_q(h) @ enc['K'].transpose(1, 2) / math.sqrt(D) + enc['prompt_bias'][:, None, :]
        alpha = s.softmax(-1)                                                    # [B,L,P]
        ctx = alpha @ enc['E']                                                   # [B,L,D]
        z = self.gate(torch.cat([h, ctx], -1)).squeeze(-1)                       # [B,L]
        copy = h.new_zeros(B, L, self.V).scatter_add(
            2, enc['prompt_ids'][:, None, :].expand(B, L, P), alpha)              # scatter onto char ids
        logp_c = torch.log(copy + 1e-12) + self.bias_pb
        logp = torch.logaddexp(F.logsigmoid(z)[..., None] + logp_v,
                               F.logsigmoid(-z)[..., None] + logp_c)
        return logp, torch.sigmoid(z), alpha

    def _hidden_full(self, enc, tgt_in):
        B, L = tgt_in.shape
        if L > self.max_target_len + 1:
            raise ValueError('decoder input longer than max_target_len + 1')
        x = self.char_emb(tgt_in) + self.pos_emb.weight[:L][None]
        causal = torch.triu(torch.full((L, L), NEG, dtype=x.dtype, device=x.device), 1)[None, None]
        for layer, (ck, cv) in zip(self.layers, enc['cross']):
            h = layer.ln1(x)
            k = layer.sa.split(layer.sa.k(h))
            v = layer.sa.split(layer.sa.v(h))
            x = x + layer.sa(h, k, v, causal)
            x = x + layer.ca(layer.ln2(x), ck, cv, enc['mem_bias'])
            x = x + layer.ff(layer.ln3(x))
        return self.ln_f(x)

    def forward_logp(self, enc, tgt_in):
        return self._mix(self._hidden_full(enc, tgt_in), enc)

    def nll(self, enc, tgt_in, tgt_out, tgt_mask):
        """Mean NLL over every real target position, EOS included (no truncation)."""
        logp, _, _ = self.forward_logp(enc, tgt_in)
        nll = -logp.gather(2, tgt_out[..., None]).squeeze(-1)
        return nll[tgt_mask].mean()

    # ---- decoding ------------------------------------------------------------------------------
    def _step(self, tok, s, enc, cache):
        """One incremental decoder step. tok [B] long; cache[li] = (K, V) of self-attention so far."""
        x = self.char_emb(tok)[:, None, :] + self.pos_emb.weight[s]
        for li, layer in enumerate(self.layers):
            h = layer.ln1(x)
            k = layer.sa.split(layer.sa.k(h))
            v = layer.sa.split(layer.sa.v(h))
            if cache[li] is not None:
                k = torch.cat([cache[li][0], k], dim=2)
                v = torch.cat([cache[li][1], v], dim=2)
            cache[li] = (k, v)
            x = x + layer.sa(h, k, v, None)
            ck, cv = enc['cross'][li]
            x = x + layer.ca(layer.ln2(x), ck, cv, enc['mem_bias'])
            x = x + layer.ff(layer.ln3(x))
        return self.ln_f(x)

    def _check_len(self, max_len):
        if max_len > self.max_target_len:
            raise ValueError(f'max_len {max_len} > max_target_len {self.max_target_len}')

    @torch.inference_mode()
    def greedy(self, enc, max_len=None, stop_at_eos=True, return_logp=False):
        """Incremental greedy decode (self-attention K/V cached per layer). Batch-aware."""
        max_len = self.max_target_len if max_len is None else max_len
        self._check_len(max_len)
        B = enc['B']
        cache = [None] * LAYERS
        tok = torch.full((B,), BOS, dtype=torch.long, device=enc['K'].device)
        done = torch.zeros(B, dtype=torch.bool, device=enc['K'].device)
        outs, logps = [], []
        for s in range(max_len + 1):
            h = self._step(tok, s, enc, cache)
            logp, _, _ = self._mix(h, enc)
            logp = logp[:, 0]
            nxt = logp.argmax(-1)
            nxt = torch.where(done, torch.full_like(nxt, PAD), nxt)
            outs.append(nxt)
            if return_logp:
                logps.append(logp)
            done = done | (nxt == EOS)
            tok = nxt
            if stop_at_eos and bool(done.all()):
                break
        ids = _cut_rows(torch.stack(outs, 1))
        return (ids, logps) if return_logp else ids

    @torch.inference_mode()
    def greedy_full(self, enc, max_len=None, stop_at_eos=True, return_logp=False):
        """Reference greedy decode that recomputes the whole prefix at every step."""
        max_len = self.max_target_len if max_len is None else max_len
        self._check_len(max_len)
        B = enc['B']
        tok = torch.full((B, 1), BOS, dtype=torch.long, device=enc['K'].device)
        done = torch.zeros(B, dtype=torch.bool, device=enc['K'].device)
        outs, logps = [], []
        for s in range(max_len + 1):
            h = self._hidden_full(enc, tok)[:, -1:]
            logp, _, _ = self._mix(h, enc)
            logp = logp[:, 0]
            nxt = logp.argmax(-1)
            nxt = torch.where(done, torch.full_like(nxt, PAD), nxt)
            outs.append(nxt)
            if return_logp:
                logps.append(logp)
            done = done | (nxt == EOS)
            tok = torch.cat([tok, nxt[:, None]], 1)
            if stop_at_eos and bool(done.all()):
                break
        ids = _cut_rows(torch.stack(outs, 1))
        return (ids, logps) if return_logp else ids


def _cut_rows(mat):
    rows = []
    for r in mat.tolist():
        seq = []
        for t in r:
            if t == EOS:
                break
            seq.append(t)
        rows.append(seq)
    return rows


def n_params(model):
    return sum(p.numel() for p in model.parameters())


# ============================================================================ self-test
def _fake_examples(n, rng):
    letters = string.ascii_lowercase
    exs = []
    for _ in range(n):
        nw = rng.randint(6, 12)
        words = [''.join(rng.choice(letters) for _ in range(rng.randint(2, 7))) for _ in range(nw)]
        offs, pos = [], 0
        for w in words:
            offs.append((pos, pos + len(w)))
            pos += len(w) + 1
        i = rng.randrange(nw)
        j = min(nw, i + rng.randint(1, 3))
        exs.append(dict(prompt=' '.join(words), offs=offs, target=' '.join(words[i:j])))
    return exs


def _make_batch(exs, stoi, T, n_loops=3):
    """Returns the tensors encode() takes, with random memory (stand-in for thinker notes)."""
    B = len(exs)
    P = max(len(e['prompt']) for e in exs)
    prompt_ids = torch.zeros(B, P, dtype=torch.long)
    prompt_mask = torch.zeros(B, P, dtype=torch.bool)
    tok_off = torch.zeros(B, T, 2, dtype=torch.long)
    mem_mask = torch.zeros(B, n_loops * T, dtype=torch.bool)
    mem_tok = torch.full((B, n_loops * T), -1, dtype=torch.long)
    for b, e in enumerate(exs):
        ids = encode_text(e['prompt'], stoi)
        prompt_ids[b, :len(ids)] = torch.tensor(ids)
        prompt_mask[b, :len(ids)] = True
        for t, (s, en) in enumerate(e['offs']):
            tok_off[b, t, 0], tok_off[b, t, 1] = s, en
        for k in range(n_loops * T):
            t = k % T
            if t < len(e['offs']):
                mem_mask[b, k] = True
                mem_tok[b, k] = t
    memory = torch.randn(B, n_loops * T, D) * 0.5
    return memory, mem_mask, mem_tok, prompt_ids, prompt_mask, tok_off


def _selftest():
    torch.manual_seed(0)
    rng = random.Random(0)
    T = 12
    exs = _fake_examples(8, rng)
    stoi, itos = build_vocab([e['prompt'] for e in exs] + [e['target'] for e in exs])
    max_tgt = 40
    model = T1Talker(len(itos), max_target_len=max_tgt)
    print(f'vocab {len(itos)} (incl. 4 specials); params {n_params(model):,}')

    memory, mem_mask, mem_tok, pids, pmask, toff = _make_batch(exs, stoi, T)
    targets = [encode_text(e['target'], stoi) for e in exs]
    tin, tout, tmask = make_teacher(targets, max_tgt)

    # 1. shapes and normalisation
    enc = model.encode(memory, mem_mask, mem_tok, pids, pmask, toff)
    logp, pgen, alpha = model.forward_logp(enc, tin)
    B, L = tin.shape
    assert logp.shape == (B, L, len(itos)), logp.shape
    assert pgen.shape == (B, L) and alpha.shape == (B, L, pids.shape[1])
    assert torch.allclose(alpha.sum(-1), torch.ones(B, L), atol=1e-5)
    assert torch.allclose(logp.exp().sum(-1), torch.ones(B, L), atol=1e-4)
    print('shapes OK; p(.) sums to 1; alpha sums to 1')

    # 2. loss finite at init, and raises on an over-long target
    loss0 = model.nll(enc, tin, tout, tmask)
    assert torch.isfinite(loss0), loss0
    print(f'initial loss {loss0.item():.4f} finite')
    try:
        make_teacher([[1] * (max_tgt + 1)], max_tgt)
        raise AssertionError('over-long target did not raise')
    except ValueError:
        print('over-long target raises OK')

    # 3. overfit 8 examples (targets copied from prompts), <= 300 steps
    opt = torch.optim.Adam(model.parameters(), lr=3e-3)
    steps_used = 0
    loss = loss0
    for step in range(300):
        enc = model.encode(memory, mem_mask, mem_tok, pids, pmask, toff)
        loss = model.nll(enc, tin, tout, tmask)
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        steps_used = step + 1
        if loss.item() < 0.02:
            break
    assert torch.isfinite(loss), loss
    print(f'overfit: {steps_used} steps, final loss {loss.item():.4f}')

    model.eval()
    with torch.no_grad():
        enc = model.encode(memory, mem_mask, mem_tok, pids, pmask, toff)
        ids = model.greedy(enc, max_len=max_tgt)
        exact = [decode_ids(seq, itos) == e['target'] for seq, e in zip(ids, exs)]
        assert all(exact), f'greedy decode not exact: {exact}'
        print('greedy decode reproduces all 8 targets exactly')

        # p_gen on the copied chars (teacher-forced, target positions only, EOS excluded)
        h = model._hidden_full(enc, tin)
        _, pg, al = model._mix(h, enc)
        sel = tmask.clone()
        sel[tout == EOS] = False
        pg_copied = pg[sel]
        frac_lt = (pg_copied < 0.5).float().mean().item()
        print(f'p_gen on copied chars: mean {pg_copied.mean().item():.3f}, '
              f'fraction < 0.5 = {frac_lt:.3f}')
        assert pg_copied.mean().item() < 0.5, 'p_gen on copied chars not below 0.5'

        # 4. incremental decode equals full-recompute decode (same prompts, padded batch)
        ids_inc, lp_inc = model.greedy(enc, max_len=max_tgt, stop_at_eos=False, return_logp=True)
        ids_full, lp_full = model.greedy_full(enc, max_len=max_tgt, stop_at_eos=False, return_logp=True)
        assert ids_inc == ids_full, 'incremental and full-recompute greedy outputs differ'
        # PAD/BOS are masked to ~-1e4, where float32 resolution is ~1e-3; compare the real columns only
        worst = max((a[:, 2:] - b[:, 2:]).abs().max().item() for a, b in zip(lp_inc, lp_full))
        print(f'incremental == full recompute (float32): same tokens, max |logp diff| {worst:.2e}')
        # float64 copy of the same model: the gap must shrink to rounding of the float64 kind
        md = T1Talker(len(itos), max_target_len=max_tgt).double().eval()
        md.load_state_dict(model.state_dict())
        encd = md.encode(memory.double(), mem_mask, mem_tok, pids, pmask, toff)
        ids_i64, li64 = md.greedy(encd, max_len=max_tgt, stop_at_eos=False, return_logp=True)
        ids_f64, lf64 = md.greedy_full(encd, max_len=max_tgt, stop_at_eos=False, return_logp=True)
        worst64 = max((a[:, 2:] - b[:, 2:]).abs().max().item() for a, b in zip(li64, lf64))
        assert ids_i64 == ids_f64, 'float64: incremental and full greedy outputs differ'
        assert worst64 < 1e-9, f'float64 step log-probs differ by {worst64}'
        print(f'incremental == full recompute (float64): same tokens, max |logp diff| {worst64:.2e}')

    # random-init model, batch of 3 with different lengths, incremental vs full
    torch.manual_seed(1)
    m2 = T1Talker(len(itos), max_target_len=max_tgt).eval()
    sub = exs[:3]
    mem2, mm2, mt2, pi2, pm2, to2 = _make_batch(sub, stoi, T)
    with torch.no_grad():
        e2 = m2.encode(mem2, mm2, mt2, pi2, pm2, to2)
        a, la = m2.greedy(e2, max_len=20, stop_at_eos=False, return_logp=True)
        b, lb = m2.greedy_full(e2, max_len=20, stop_at_eos=False, return_logp=True)
        w2 = max((x[:, 2:] - y[:, 2:]).abs().max().item() for x, y in zip(la, lb))
    assert a == b and w2 < 1e-3, (a == b, w2)
    print(f'random-init batch of 3 (float32): incremental == full, same tokens (max |logp diff| {w2:.2e})')

    # 5. timing: batch 1, ~40-char answer, prompt of 300 chars / 50 tokens, memory 3 x T_MAX(64)
    stoi_t, itos_t = build_vocab([string.printable])
    mt = T1Talker(len(itos_t), max_target_len=64).eval()
    Tm = 64
    prompt = ''.join(rng.choice(string.ascii_lowercase + ' ') for _ in range(300))
    offs, p = [], 0
    while p < len(prompt) and len(offs) < Tm:
        q = min(len(prompt), p + 6)
        offs.append((p, q))
        p = q
    exs_t = [dict(prompt=prompt, offs=offs, target='')]
    mem_t, mm_t, mt_t, pi_t, pm_t, to_t = _make_batch(exs_t, stoi_t, Tm)
    n_threads_default = torch.get_num_threads()
    timing_lines = []
    for nt in (1, n_threads_default):
        torch.set_num_threads(nt)
        enc_t_times, dec_times = [], []
        for r in range(25):
            t0 = time.perf_counter()
            with torch.inference_mode():
                et = mt.encode(mem_t, mm_t, mt_t, pi_t, pm_t, to_t)
            t1 = time.perf_counter()
            out_t = mt.greedy(et, max_len=40, stop_at_eos=False)
            t2 = time.perf_counter()
            if r >= 5:
                enc_t_times.append((t1 - t0) * 1e3)
                dec_times.append((t2 - t1) * 1e3)
        timing_lines.append(f'torch threads={nt}: decode {len(out_t[0])} chars median '
                            f'{statistics.median(dec_times):.1f} ms (min {min(dec_times):.1f}); '
                            f'encode median {statistics.median(enc_t_times):.1f} ms (not in decode)')
    torch.set_num_threads(n_threads_default)
    for line in timing_lines:
        print('timing batch 1, ' + line)
    print(f'params {n_params(mt):,} at V={len(itos_t)} (max_target_len 64)')
    print('SELFTEST PASSED')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        _selftest()
    else:
        m = T1Talker(100, max_target_len=128)
        print(f'T1Talker params at V=100: {n_params(m):,}')


if __name__ == '__main__':
    main()
