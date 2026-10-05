"""plain_tf_steps: PlainTF trained to write the worked steps, then ' # ', then the answer (arithmetic families only).
Scored on the text after the last '#'. Lesion 'calc' (C1'): same weights, but whenever the decoded text ends with
'a op b =' the exact result is forced in as tokens (integer division only when exact)."""
import re
import torch
import torch.nn as nn
import torch.nn.functional as F
from custom_io.data import BOS, EOS, PAD, SEP, N_SPECIAL
from custom_io.models.plain_tf import PlainTF

# the 11 families whose `steps` are worked equations / arrows (found from the train rows; the 8 pure ones plus
# state_update, percent_rate and verify_claim, whose steps are equations on most rows)
STEP_FAMILIES = frozenset(['arith_bare', 'div_exact', 'story_addsub', 'distance_units', 'chain_ops', 'chain_story2',
                           'story_chain3', 'var_chain', 'state_update', 'percent_rate', 'verify_claim'])
CAP = 64                    # longest steps+answer target (chars) before falling back to the answer alone
MAX_NEW = CAP + 3 + 8 + 1   # ' # ' + 8 answer chars + EOS
MAX_POS = 288
_CALC = re.compile(r'(?:^|[;=#] ?)((?:-?\d+ ?[-+*/x] ?)+-?\d+)( ?)=$')   # whole operand chain, anchored at a step start


def target_text(row):
    """'; '.join(steps) + ' # ' + answer for step families when it fits in CAP chars, else the answer alone."""
    if row.get('family') in STEP_FAMILIES and row.get('steps'):
        t = '; '.join(row['steps']) + ' # ' + row['answer']
        if len(t) <= CAP:
            return t
    return row['answer']


def calc_fill(text):
    """If text ends with an equation 'a op b =' (a step start before it) return the string to force in (' ' + result,
    or the bare result when the '=' had no space before it), else None. Chains of several operators are evaluated
    left to right only when all are + or -. Never raises."""
    try:
        m = _CALC.search(text)
        if not m:
            return None
        nums = re.findall(r'(?:(?<=[-+*/x ])|^)-?\d+', m[1])
        ops = re.findall(r'\d ?([-+*/x]) ?(?=-?\d)', m[1])
        if len(nums) != len(ops) + 1:
            return None
        v = int(nums[0])
        if len(ops) > 1 and set(ops) - {'+', '-'}:
            return None
        for op, n in zip(ops, nums[1:]):
            n = int(n)
            if op == '+': v += n
            elif op == '-': v -= n
            elif op in '*x': v *= n
            else:
                if n == 0 or v % n:
                    return None
                v //= n
        return (' ' if m[2] else '') + str(v)
    except Exception:
        return None


def final_answer(text):
    return text.rsplit('#', 1)[1].strip() if '#' in text else text.strip()


class PlainTFSteps(PlainTF):
    LESIONS = ['calc']

    def __init__(self, vocab, d_model=256, n_layers=4, n_heads=4, n_loops=1, place=False):
        super().__init__(vocab, d_model, n_layers, n_heads, n_loops)
        self.pos = nn.Embedding(MAX_POS, d_model)
        nn.init.normal_(self.pos.weight, std=0.02)
        if place:                   # last, after pos is replaced, so no other weight's init moves (see PlainTF._add_place)
            self._add_place()

    def _targets(self, batch):
        """-> ids [B, A] (target chars + EOS, PAD after), mask [B, A]."""
        enc = [self.vocab.encode(target_text(r))[:CAP + 12] + [EOS] for r in batch['rows']]
        dev = batch['prompt_ids'].device
        ids = torch.full((len(enc), max(map(len, enc))), PAD, dtype=torch.long)
        for i, e in enumerate(enc):
            ids[i, :len(e)] = torch.tensor(e)
        return ids.to(dev), (ids != PAD).to(dev)

    def loss(self, batch):
        p, lens = batch['prompt_ids'], batch['prompt_mask'].sum(1)
        a, am = self._targets(batch)
        B, T, A = p.shape[0], p.shape[1], a.shape[1]
        seq = p.new_full((B, T + 2 + A), PAD)
        seq[:, 0], seq[:, 1:1 + T] = BOS, p
        r = torch.arange(B, device=p.device)
        seq[r, 1 + lens] = SEP
        j = torch.arange(A, device=p.device)
        seq.scatter_(1, (2 + lens)[:, None] + j, a)
        tgt = torch.full_like(seq, -100)
        tgt.scatter_(1, (1 + lens)[:, None] + j, torch.where(am, a, torch.full_like(a, -100)))
        W = int((2 + lens + am.sum(1)).max())
        lg = self.logits(self.hidden_upto(seq, W, None, self.place_seq(batch, seq.shape[1]))).float()
        return F.cross_entropy(lg.reshape(-1, lg.shape[-1]), tgt[:, :W].reshape(-1), ignore_index=-100)

    @torch.no_grad()
    def generate(self, batch, lesion=None):
        name, arg = self.check_lesion(lesion)
        loops, calc = (arg if name == 'loops' else None), name == 'calc'
        p, lens = batch['prompt_ids'], batch['prompt_mask'].sum(1)
        B, T = p.shape
        seq = p.new_full((B, T + 2 + MAX_NEW), PAD)
        seq[:, 0], seq[:, 1:1 + T] = BOS, p
        r = torch.arange(B, device=p.device)
        seq[r, 1 + lens] = SEP
        pl = self.place_seq(batch, seq.shape[1])
        txt, queue, done = [''] * B, [[] for _ in range(B)], [False] * B
        for t in range(MAX_NEW):
            n = int((2 + lens).max()) + t
            h = self.hidden_upto(seq, n, loops, pl)[r, 1 + lens + t]
            nxt = self.logits(h).argmax(-1)
            forced = [(q.pop(0) if q and not d else None) for q, d in zip(queue, done)]
            if any(f is not None for f in forced):
                nxt = torch.tensor([f if f is not None else int(x) for f, x in zip(forced, nxt)], device=p.device)
            seq[r, 2 + lens + t] = nxt
            for i, x in enumerate(nxt.tolist()):
                if done[i]:
                    continue
                if x == EOS:
                    done[i] = True
                elif x >= N_SPECIAL:
                    txt[i] += self.vocab.itos[x]
                    if calc and not queue[i] and forced[i] is None and (f := calc_fill(txt[i])):
                        queue[i] = self.vocab.encode(f)
            if all(done):
                break
        return [final_answer(s) for s in txt]
