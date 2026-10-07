"""8a arms that need a width-flexible plain transformer.

plain_tf_steps_g (PlainStepsG): plain_tf_steps with a free feed-forward width (`mlp` ratio or an explicit `hidden`), so a plain arm can be
matched to B2's trained size within +-2% at every rung (depth steps alone are too coarse above 3M). With mlp = 4.0 (default) and no `hidden`
it is plain_tf_steps exactly (same modules, same seeded init, same loss and decode).

plain_lm (PlainLM): the plain LLM recipe arm (8A spec section 3). Same network and decode as plain_tf_steps_g. Training differs:
  * a cloze row (family 'cloze', from g8a/cloze.py) is read as raw web text: BOS chunk EOS with the answer put back into the blank, and the
    next-character loss covers every character of the chunk plus EOS (a char-level model's "next-word" loss: no borrowed tokenizer);
  * every other row is a question: BOS prompt SEP target EOS with the loss on the target only, the target being the worked steps then
    ' # ' then the answer exactly as plain_tf_steps writes it (models.plain_tf_steps.target_text).
The loss is the mean over all supervised characters of the batch, as in any language-model run. Nothing is borrowed.
"""
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from custom_io.data import BOS, EOS, PAD, SEP
from custom_io.g8a.cloze import is_cloze, unblank
from custom_io.models import plain_tf_steps as pts
from custom_io.models.plain_tf_steps import PlainTFSteps, target_text


class FlexBlock(nn.Module):
    """plain_tf.Block with a feed-forward hidden width of `hidden` (4 * d in plain_tf)."""

    def __init__(self, d, heads, hidden):
        super().__init__()
        self.h = heads
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.proj = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.fc, self.out = nn.Linear(d, hidden), nn.Linear(hidden, d)

    def forward(self, x):
        B, T, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        a = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + self.proj(a.transpose(1, 2).reshape(B, T, D))
        return x + self.out(F.gelu(self.fc(self.ln2(x))))


class PlainStepsG(PlainTFSteps):
    def __init__(self, vocab, d_model=256, n_layers=4, n_heads=4, n_loops=1, place=False, mlp=4.0, hidden=None):
        super().__init__(vocab, d_model, n_layers, n_heads, n_loops, place)
        h = int(hidden) if hidden is not None else int(mlp * d_model)
        if h != 4 * d_model:      # only then are the blocks rebuilt, so the default really is plain_tf_steps
            self.blocks = nn.ModuleList(FlexBlock(d_model, n_heads, h) for _ in range(n_layers))
            self.blocks.apply(self._init)
            for b in self.blocks:
                for lin in (b.proj, b.out):
                    nn.init.normal_(lin.weight, std=0.02 / math.sqrt(2 * n_layers * n_loops))


class PlainLM(PlainStepsG):
    def _sequences(self, batch):
        """-> seq [B, W] ids (PAD after the end), tgt [B, W] (-100 where not supervised), W. tgt[i, j] is the id the model must emit at position j."""
        seqs, starts = [], []
        for r in batch['rows']:
            if is_cloze(r):
                ids = [BOS] + self.vocab.encode(unblank(r)) + [EOS]
                starts.append(1)            # first supervised token: the char after BOS
            else:
                p = self.vocab.encode(r['prompt'])
                ids = [BOS] + p + [SEP] + self.vocab.encode(target_text(r))[:pts.CAP + 12] + [EOS]
                starts.append(2 + len(p))   # first target char
            seqs.append((ids, starts[-1]))
        W = max(len(s) for s, _ in seqs)
        seq = torch.full((len(seqs), W), PAD, dtype=torch.long)
        tgt = torch.full((len(seqs), W), -100, dtype=torch.long)
        for i, (ids, st) in enumerate(seqs):
            seq[i, :len(ids)] = torch.tensor(ids)
            tgt[i, st - 1:len(ids) - 1] = torch.tensor(ids[st:])        # position j predicts token j + 1
        dev = batch['prompt_ids'].device
        return seq.to(dev), tgt.to(dev), W

    def loss(self, batch):
        seq, tgt, W = self._sequences(batch)
        lg = self.logits(self.hidden(seq)).float()
        return F.cross_entropy(lg.reshape(-1, lg.shape[-1]), tgt.reshape(-1), ignore_index=-100)
