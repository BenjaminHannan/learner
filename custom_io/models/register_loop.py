"""A (steps=True) and A0 (steps=False): Register Loop. Shared CharReader -> 16 slots (9 answer registers + 7 scratch) updated
for n_loops weight-shared rounds of slot self-attention + cross-attention to the reader output + MLP -> linear per-register talker.
Slot j < 9 holds answer char j from the right (EOS after the last char); the talker sees only the final slots. Loss: float32
cross-entropy of every round's registers; round r targets the r-th worked-step value when the row has >= 2 (A), else the answer
(always, in A0). Sizes (vocab 108): plain_tf S 3,244,544 / M 10,775,040.
S = dict(d_model=256, n_heads=4, reader_layers=2, core_blocks=3, n_loops=6, mlp=2.25)   # 3,217,708 params (-0.8%)
M = dict(d_model=384, n_heads=6, reader_layers=2, core_blocks=5, n_loops=6, mlp=2.2)    # 10,785,512 params (+0.1%)"""
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from custom_io.data import EOS, MAX_ANS
from custom_io.models.base import Model
from custom_io.models.reader import CharReader
from custom_io import diag_register as dg


class XBlock(nn.Module):
    """Slot self-attention + cross-attention to the prompt (K/V from kv_of, computed once per forward) + MLP."""

    def __init__(self, d, h, hidden):
        super().__init__()
        self.h = h
        self.ln1, self.ln2, self.ln3, self.lnx = (nn.LayerNorm(d) for _ in range(4))
        self.qkv, self.p1 = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.q, self.kv, self.p2 = nn.Linear(d, d), nn.Linear(d, 2 * d), nn.Linear(d, d)
        self.fc, self.out = nn.Linear(d, hidden), nn.Linear(hidden, d)

    def kv_of(self, X):
        B, T, D = X.shape
        return self.kv(self.lnx(X)).view(B, T, 2, self.h, D // self.h).permute(2, 0, 3, 1, 4)

    def forward(self, H, KV, kmask):
        """KV=None skips the cross-attention (blind rounds)."""
        B, S, D = H.shape
        q, k, v = self.qkv(self.ln1(H)).view(B, S, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        H = H + self.p1(F.scaled_dot_product_attention(q, k, v).transpose(1, 2).reshape(B, S, D))
        if KV is not None:
            q = self.q(self.ln2(H)).view(B, S, self.h, D // self.h).transpose(1, 2)
            a = F.scaled_dot_product_attention(q, KV[0], KV[1], attn_mask=kmask[:, None, None, :])
            H = H + self.p2(a.transpose(1, 2).reshape(B, S, D))
        return H + self.out(F.gelu(self.fc(self.ln3(H))))


class RegisterLoop(Model):
    LESIONS = ['shuffle_state', 'zero_state', 'blind1']

    def __init__(self, vocab, d_model=256, n_heads=4, reader_layers=2, core_blocks=3, n_loops=6, n_reg=9, n_scratch=7, mlp=2.25, steps=True):
        super().__init__(vocab)
        d = d_model
        self.n_loops, self.n_reg, self.use_steps = n_loops, n_reg, steps
        self._tc = {}
        self.reader = CharReader(len(vocab), d, reader_layers)
        self.scr = nn.Embedding(n_scratch, d)
        self.core = nn.ModuleList(XBlock(d, n_heads, int(mlp * d)) for _ in range(core_blocks))
        self.ln_s, self.ln_t = nn.LayerNorm(d), nn.LayerNorm(d)
        self.bias = nn.Parameter(torch.zeros(len(vocab)))
        for m in self.modules():        # the reader's own embeddings are re-initialised too: they are tied to the codes and the talker
            if isinstance(m, (nn.Linear, nn.Embedding)) and not isinstance(m, nn.Conv1d):
                nn.init.normal_(m.weight, std=0.02)
                if getattr(m, 'bias', None) is not None:
                    nn.init.zeros_(m.bias)
        for b in self.core:             # GPT-2 style shrink of the residual-branch outputs
            for lin in (b.p1, b.p2, b.out):
                nn.init.normal_(lin.weight, std=0.02 / math.sqrt(3 * core_blocks * n_loops))

    def codes(self):
        """P [16,d]: register codes tied to the reader's place rows 0..8, then the scratch codes."""
        return torch.cat([self.reader.place.weight[:self.n_reg], self.scr.weight])

    def rounds(self, batch, loops=None, S0=None, start=0, blind=False):
        """Yield S_r [B,16,d] after each round. S0 (default P) with `start` rounds already done lets a caller continue from
        another state; blind=True turns the cross-attention off for global rounds >= 2."""
        X, m = self.reader(batch)
        KV = [b.kv_of(X) for b in self.core]
        P = self.codes()
        S = P.expand(X.shape[0], -1, -1) if S0 is None else S0
        for r in range(start, self.n_loops if loops is None else loops):
            H = S + P
            for b, kv in zip(self.core, KV):
                H = b(H, None if blind and r >= 1 else kv, m)
            S = self.ln_s(H)
            yield S

    def state(self, batch, loops=None, blind=False):
        S = self.codes().expand(batch['prompt_ids'].shape[0], -1, -1)
        for S in self.rounds(batch, loops, blind=blind):
            pass
        return S[:, :self.n_reg]

    def readout(self, R):
        return F.linear(self.ln_t(R), self.reader.tok.weight) + self.bias

    def talk(self, state, batch):
        ids = self.readout(state).argmax(-1).tolist()
        return [self.vocab.decode(r)[::-1] for r in ids]       # decode stops at the first EOS; registers are units-first

    @torch.no_grad()
    def generate(self, batch, lesion=None):
        if lesion == 'blind1':
            return self.talk(self.state(batch, blind=True), batch)
        return super().generate(batch, lesion)

    def row_targets(self, row):
        """[R,n_reg] int16 for one row (fixed per row and model), cached by row id."""
        key = (row.get('id'), row['prompt'], row['answer'])
        t = self._tc.get(key)
        if t is None:
            vals = dg.step_values(row, self.use_steps)
            t = torch.full((self.n_loops, self.n_reg), -100, dtype=torch.int16)
            for r in range(self.n_loops):
                ids = self.vocab.encode(vals[min(r + 1, len(vals)) - 1][:MAX_ANS][::-1]) + [EOS]
                t[r, :len(ids)] = torch.tensor(ids, dtype=torch.int16)
            self._tc[key] = t
        return t

    def targets(self, rows, device=None):
        """[R,B,n_reg] long: reversed target chars (first MAX_ANS chars, as the harness truncates) then EOS, -100 after."""
        tg = torch.stack([self.row_targets(r) for r in rows], 1).long()
        return tg.to(device) if device is not None else tg

    def loss(self, batch):
        tg = self.targets(batch['rows'], batch['prompt_ids'].device)
        L = [F.cross_entropy(self.readout(S[:, :self.n_reg]).float().flatten(0, 1), tg[r].flatten(), ignore_index=-100)
             for r, S in enumerate(self.rounds(batch))]
        return sum(L) / len(L), {'loss_r1': L[0].detach(), 'loss_last': L[-1].detach()}

    @torch.no_grad()
    def extra_evals(self, ctx):
        """Staircase and round-1 register interchange on the CHAIN5 in_dist rows with >= 2 step values (big build if given)."""
        was = self.training
        self.eval()
        rows = dg.chain5_rows(ctx.get('big') or ctx['data'])
        kw = dict(device=ctx['device'], batch_size=ctx['batch_size'], amp=ctx['amp'])
        out = {'n_rows': len(rows), 'staircase': dg.staircase(self, rows, **kw), 'interchange': dg.interchange(self, rows, **kw)}
        self.train(was)
        return out
