"""Same-size baseline: decoder-only causal char transformer on [BOS] prompt [SEP] answer [EOS].
Loss only on answer chars + EOS. n_loops > 1 re-applies the same block stack (looped / universal transformer).

place=True adds the CharReader's place code (a char's index from the right end of its word token: units digit 0, tens 1,
...; PLACE_NONE for spaces) as one extra embedding table, added to the input at the real prompt chars only. BOS, SEP, the
answer (or step) positions and padding get no place term at all. Nothing else changes: with place=False the model is
exactly the old one (same modules, state_dict keys, seeded init), and with place=True the extra table is created last so
every other weight keeps the init it has without it."""
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from custom_io.data import BOS, EOS, PAD, SEP, MAX_ANS
from custom_io.models.base import Model
from custom_io.models.reader import N_PLACE, batch_places

MAX_LEN = 224       # 1 + 208 + 1 + 9 = 219 is the longest possible sequence


class Block(nn.Module):
    def __init__(self, d, heads):
        super().__init__()
        self.h = heads
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.proj = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.fc, self.out = nn.Linear(d, 4 * d), nn.Linear(4 * d, d)

    def forward(self, x):
        B, T, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        a = F.scaled_dot_product_attention(q, k, v, is_causal=True)      # right-padded batches need no pad mask
        x = x + self.proj(a.transpose(1, 2).reshape(B, T, D))
        return x + self.out(F.gelu(self.fc(self.ln2(x))))


class PlainTF(Model):
    LESIONS = []        # nothing to lesion; 'loops:K' still works because n_loops exists

    def __init__(self, vocab, d_model=256, n_layers=4, n_heads=4, n_loops=1, place=False):
        super().__init__(vocab)
        self.n_loops = n_loops
        self.has_place = False
        self.tok, self.pos = nn.Embedding(len(vocab), d_model), nn.Embedding(MAX_LEN, d_model)
        self.blocks = nn.ModuleList(Block(d_model, n_heads) for _ in range(n_layers))
        self.ln_f = nn.LayerNorm(d_model)
        self.apply(self._init)
        for b in self.blocks:       # GPT-2 style: shrink residual-branch output projections
            for lin in (b.proj, b.out):
                nn.init.normal_(lin.weight, std=0.02 / math.sqrt(2 * n_layers * n_loops))
        if place:
            self._add_place()

    def _add_place(self):
        """Create the place table. Call it after every other module is built and initialised (PlainTFSteps replaces
        self.pos after PlainTF.__init__, so it calls this itself at the end)."""
        self.place = nn.Embedding(N_PLACE, self.tok.embedding_dim)
        self._init(self.place)
        self.has_place = True
        self._place_cache = {}          # prompt -> int8 place row (plain dict, not a parameter or buffer)

    @staticmethod
    def _init(m):
        if isinstance(m, (nn.Linear, nn.Embedding)):
            nn.init.normal_(m.weight, std=0.02)
            if getattr(m, 'bias', None) is not None:
                nn.init.zeros_(m.bias)

    def place_seq(self, batch, width):
        """[B, width] long, aligned with the sequence the model reads: the place id of every real prompt char (sequence
        positions 1..prompt length) and -1 ('no place term') everywhere else. None when the model has no place table."""
        if not self.has_place:
            return None
        pm = batch['prompt_mask']
        pl = torch.full((pm.shape[0], width), -1, dtype=torch.long, device=pm.device)
        pl[:, 1:1 + pm.shape[1]] = batch_places(batch, self._place_cache).masked_fill(~pm, -1)
        return pl

    def hidden_upto(self, seq, n, loops=None, pl=None):
        """hidden() on the first n columns of seq (and of the place tensor, when there is one)."""
        return self.hidden(seq[:, :n], loops) if pl is None else self.hidden(seq[:, :n], loops, pl[:, :n])

    def hidden(self, ids, loops=None, place=None):
        x = self.tok(ids) + self.pos(torch.arange(ids.shape[1], device=ids.device))
        if place is not None:
            x = x + self.place(place.clamp(min=0)) * (place >= 0)[..., None]
        for _ in range(self.n_loops if loops is None else loops):
            for blk in self.blocks:
                x = blk(x)
        return self.ln_f(x)

    def logits(self, h):
        return F.linear(h, self.tok.weight)         # tied input/output embeddings

    def _build(self, batch, with_answer):
        """Right-padded [BOS] prompt [SEP] (answer) rows; returns ids, prompt lengths."""
        p, lens = batch['prompt_ids'], batch['prompt_mask'].sum(1)
        B, T = p.shape
        a = batch['ans_ids'] if with_answer else p.new_zeros(B, MAX_ANS + 1)
        seq = p.new_full((B, T + 2 + MAX_ANS + 1), PAD)
        seq[:, 0], seq[:, 1:1 + T] = BOS, p
        r = torch.arange(B, device=p.device)
        seq[r, 1 + lens] = SEP
        if with_answer:
            seq.scatter_(1, (2 + lens)[:, None] + torch.arange(MAX_ANS + 1, device=p.device), a)
        return seq, lens

    def loss(self, batch):
        seq, lens = self._build(batch, True)
        am = batch['ans_mask']
        # logit at position 1+lens+j predicts answer slot j
        tgt = torch.full_like(seq, -100)
        pos = (1 + lens)[:, None] + torch.arange(MAX_ANS + 1, device=seq.device)
        tgt.scatter_(1, pos, torch.where(am, batch['ans_ids'], torch.full_like(batch['ans_ids'], -100)))
        W = int((2 + lens + am.sum(1)).max())
        lg = self.logits(self.hidden_upto(seq, W, None, self.place_seq(batch, seq.shape[1]))).float()
        return F.cross_entropy(lg.reshape(-1, lg.shape[-1]), tgt[:, :W].reshape(-1), ignore_index=-100)

    @torch.no_grad()
    def generate(self, batch, lesion=None):
        name, arg = self.check_lesion(lesion)
        loops = arg if name == 'loops' else None
        seq, lens = self._build(batch, False)
        B, r = seq.shape[0], torch.arange(seq.shape[0], device=seq.device)
        pl = self.place_seq(batch, seq.shape[1])
        out, done = [], torch.zeros(B, dtype=torch.bool, device=seq.device)
        for t in range(MAX_ANS + 1):
            n = int((2 + lens).max()) + t
            h = self.hidden_upto(seq, n, loops, pl)[r, 1 + lens + t]   # last real position of every row
            nxt = self.logits(h).argmax(-1)
            seq[r, 2 + lens + t] = nxt
            out.append(nxt)
            done |= nxt == EOS
            if done.all():
                break
        out = torch.stack(out, 1).tolist()
        return [self.vocab.decode(o) for o in out]
