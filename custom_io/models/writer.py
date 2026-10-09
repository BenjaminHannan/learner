"""O1 byte writer (B3 group 2, design B3-GROUP2-BUILD sec. 2): one small autoregressive decoder that writes a byte string (a tool call such as
`sub 12 5`, or an answer) left to right from the thinker's vectors Z, with copy attention over a context. Input at step i = tok[previous byte] (BOS at 0)
+ position row i + start row[mode] (0 "call?", 1 "answer") + W_fb(feedback), projected to `inner` width. Feedback is CopyNet's selective read
(arXiv 1603.06393): teacher forced = sum_j fb[i,j] Xc[j] with fb from `teacher` (the gold sources of byte i-1); free run = (1 - gate_{i-1}) * the
copy attention of step i-1 applied to Xc. One block: attention over [Z projected; its own steps, causal] (never the context), then an MLP, pre-LN.
Output, fp32 as Ledger.gen_copy: p = gate * softmax(h tok^T + bias) + (1 - gate) * copy, copy = softmax of q_c(h).(k_c(Xc) + ckeys) / sqrt(dk) over
the unmasked context scattered onto cids; nocopy forces gate = 1. `tok` is the reader's table, shared (input rows and tied readout), held in a list: not
registered here, not counted by size(), moved and optimised by its owner."""
import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class ByteWriter(nn.Module):
    def __init__(self, d, tok, cap, dk=64, heads=4, inner=None, mlp=2.0, n_modes=2):
        super().__init__()
        inner = inner or d // 2
        assert inner % heads == 0
        self.d, self.cap, self.dk, self.heads, self.inner, self.n_modes = d, cap, dk, heads, inner, n_modes
        self._tok = [tok]
        self.V = tok.num_embeddings
        self.pos = nn.Embedding(cap, d)
        self.start = nn.Embedding(n_modes, d)
        self.w_fb = nn.Linear(d, d, bias=False)
        self.w_in = nn.Linear(d, inner)
        self.w_z = nn.Linear(d, inner)
        self.ln_z = nn.LayerNorm(inner)
        self.ln1, self.ln2, self.ln_o = nn.LayerNorm(inner), nn.LayerNorm(inner), nn.LayerNorm(inner)
        self.qkv_q, self.qkv_kv, self.proj = nn.Linear(inner, inner), nn.Linear(inner, 2 * inner), nn.Linear(inner, inner)
        hid = int(inner * mlp)
        self.fc1, self.fc2 = nn.Linear(inner, hid), nn.Linear(hid, inner)
        self.w_out = nn.Linear(inner, d)
        self.ln_t = nn.LayerNorm(d)
        self.bias = nn.Parameter(torch.zeros(self.V))
        self.g_cp, self.q_cp, self.k_cp = nn.Linear(d, 1), nn.Linear(d, dk), nn.Linear(d, dk)
        for m in self.modules():
            if isinstance(m, (nn.Linear, nn.Embedding)):
                nn.init.normal_(m.weight, std=0.02)
                if getattr(m, 'bias', None) is not None:
                    nn.init.zeros_(m.bias)

    @property
    def tok(self):
        return self._tok[0]

    def size(self):
        return sum(p.numel() for p in self.parameters())

    def hidden(self, Z, zmask, inp, mode, fbs):
        """[B,L,d] decoder output (pre-LN) for inp [B,L] and the feedback states fbs [B,L,d]."""
        B, L = inp.shape
        assert L <= self.cap
        x = self.tok.weight[inp] + self.pos.weight[:L] + self.start(mode)[:, None] + self.w_fb(fbs)
        x = self.w_in(x)
        z = self.ln_z(self.w_z(Z))
        h = self.ln1(x)
        q = self.qkv_q(h)
        k, v = self.qkv_kv(torch.cat([z, h], 1)).chunk(2, -1)
        sp = lambda t: t.reshape(B, -1, self.heads, self.inner // self.heads).transpose(1, 2)
        causal = torch.ones(L, L, dtype=torch.bool, device=inp.device).tril()
        ok = torch.cat([zmask[:, None, :].expand(B, L, -1), causal.expand(B, -1, -1)], -1)[:, None]
        a = F.scaled_dot_product_attention(sp(q), sp(k), sp(v), attn_mask=ok)
        x = x + self.proj(a.transpose(1, 2).reshape(B, L, self.inner))
        x = x + self.fc2(F.gelu(self.fc1(self.ln2(x))))
        return self.w_out(self.ln_o(x))

    def head(self, R, Xc, cmask, cids, nocopy, ckeys):
        """fp32 pointer-generator -> (p [B,L,V], gate [B,L], attn [B,L,N]). A row with no visible context gets gate 1."""
        with torch.autocast(R.device.type, enabled=False):
            R, Xc = R.float(), Xc.float()
            h = self.ln_t(R)
            p_vocab = (F.linear(h, self.tok.weight.float()) + self.bias.float()).softmax(-1)
            kc = self.k_cp(Xc) if ckeys is None else self.k_cp(Xc) + ckeys.float()
            a = (torch.einsum('bld,bnd->bln', self.q_cp(h), kc) / math.sqrt(self.dk)).masked_fill(~cmask[:, None, :], -1e9).softmax(-1)
            a = a * cmask.any(-1)[:, None, None]
            gate = torch.sigmoid(self.g_cp(h))[..., 0]
            if nocopy:
                gate = torch.ones_like(gate)
            gate = torch.where(cmask.any(-1)[:, None], gate, torch.ones_like(gate))
            copy = torch.zeros_like(p_vocab).scatter_add_(2, cids[:, None, :].expand(-1, R.shape[1], -1), a)
            return gate[..., None] * p_vocab + (1 - gate[..., None]) * copy, gate, a

    def run(self, Z, zmask, Xc, cmask, cids, mode, inp, fb, nocopy, ckeys):
        fbs = torch.bmm(fb.to(Xc.dtype), Xc)
        R = self.hidden(Z, zmask, inp, mode, fbs)
        return self.head(R, Xc, cmask, cids, nocopy, ckeys)

    def forward(self, Z, zmask, Xc, cmask, cids, mode, inp, fb, nocopy=False, ckeys=None, refine=0):
        """Teacher forced. -> (logp [B,L,V] fp32 = log(p + 1e-9), gate [B,L], attn [B,L,N]). refine=k > 0: k no-grad passes first replace fb[:, i] by the
        model's own (1 - gate_{i-1}) * attn_{i-1} (the free-run feedback, on the gold inputs), so the training pass sees what greedy() feeds back; 0 = fb as given."""
        for _ in range(refine):
            with torch.no_grad():
                _, g, a = self.run(Z, zmask, Xc, cmask, cids, mode, inp, fb, nocopy, ckeys)
            fb = torch.cat([torch.zeros_like(fb[:, :1]), ((1 - g[..., None]) * a)[:, :-1]], 1)
        p, gate, a = self.run(Z, zmask, Xc, cmask, cids, mode, inp, fb, nocopy, ckeys)
        return torch.log(p + 1e-9), gate, a

    @staticmethod
    def teacher(targets, cids, cmask, cap, bos, eos, pad=-100):
        """targets: list (len B) of id lists WITHOUT EOS (None = no target) -> dict(inp [B,L], tgt [B,L] (EOS appended, pad after), fb [B,L,N], over [B]).
        len + 1 > cap -> over, an all-pad row, never a cut one. fb[b,i], i >= 1: uniform over the visible j with cids[j] == tgt[i-1] and, for i >= 2,
        cids[j-1] == tgt[i-2] (the gold sources of the previous byte); zero if none or at i = 0."""
        B, N = cids.shape
        ok = [t is not None and len(t) + 1 <= cap for t in targets]
        over = torch.tensor([t is not None and len(t) + 1 > cap for t in targets], dtype=torch.bool)
        L = max([len(t) + 1 for t, o in zip(targets, ok) if o] + [1])
        inp = torch.full((B, L), eos, dtype=torch.long)
        tgt = torch.full((B, L), pad, dtype=torch.long)
        fb = torch.zeros(B, L, N)
        c, m = cids.cpu(), cmask.cpu()
        for b, (t, o) in enumerate(zip(targets, ok)):
            inp[b, 0] = bos
            if not o:
                continue
            n = len(t)
            tgt[b, :n + 1] = torch.tensor(list(t) + [eos])
            if n:
                inp[b, 1:n + 1] = torch.tensor(t)
            for i in range(1, n + 1):
                hit = m[b] & (c[b] == t[i - 1])
                if i >= 2:
                    hit[1:] &= c[b, :-1] == t[i - 2]
                    hit[0] = False
                if hit.any():
                    fb[b, i] = hit.float() / hit.sum()
        dev = cids.device
        return dict(inp=inp.to(dev), tgt=tgt.to(dev), fb=fb.to(dev), over=over.to(dev))

    @staticmethod
    def nll(logp, tgt):
        """[B] mean NLL over the row's target positions (0 for rows with no target)."""
        v = tgt != -100
        lp = logp.gather(-1, tgt.clamp(min=0)[..., None])[..., 0]
        return -(lp * v).sum(1) / v.sum(1).clamp(min=1)

    @staticmethod
    def right(logp, tgt):
        """[B] bool: has a target and the argmax equals it at every target position (= greedy decoding is right)."""
        v = tgt != -100
        return v.any(1) & ((logp.argmax(-1) == tgt) | ~v).all(1)

    @torch.no_grad()
    def greedy(self, Z, zmask, Xc, cmask, cids, mode, max_len=None, nocopy=False, ckeys=None, temperature=0.0, generator=None, bos=1, eos=2):
        """Free run, batched (temperature 0 = argmax, else samples the mixture). -> (list of B id lists without EOS, ended [B] bool: wrote EOS
        within max_len steps, default cap). Feedback for step i is (1 - gate) * attn of step i-1."""
        B, N = cids.shape
        T = min(max_len or self.cap, self.cap)
        inp = torch.full((B, 1), bos, dtype=torch.long, device=cids.device)
        fb = torch.zeros(B, 1, N, device=cids.device)
        done = torch.zeros(B, dtype=torch.bool, device=cids.device)
        out = [[] for _ in range(B)]
        for i in range(T):
            p, gate, a = self.run(Z, zmask, Xc, cmask, cids, mode, inp, fb, nocopy, ckeys)
            p = p[:, -1]
            if temperature > 0:
                nxt = torch.multinomial(p.pow(1 / temperature) + 1e-12, 1, generator=generator)[:, 0]
            else:
                nxt = p.argmax(-1)
            nxt = torch.where(done, torch.full_like(nxt, eos), nxt)
            for b in (~done & (nxt != eos)).nonzero()[:, 0].tolist():
                out[b].append(int(nxt[b]))
            done = done | (nxt == eos)
            if done.all():
                break
            inp = torch.cat([inp, nxt[:, None]], 1)
            fb = torch.cat([fb, ((1 - gate[:, -1:]) * a[:, -1])[:, None]], 1)
        return out, done
