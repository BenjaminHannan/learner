"""plain_tf_steps: PlainTF trained to write the worked steps, then ' # ', then the answer (arithmetic families only).
Scored on the text after the last '#'. Lesion 'calc' (C1'): same weights, but whenever the decoded text ends with
'a op b =' the exact result is forced in as tokens (integer division only when exact).
calc_train (PTC, addendum AG): the calculator (calc_full: the whole integer expression of the step, precedence and brackets) writes the result after every
step 'expr =' at training too, so those characters are left out of the loss (the model still reads them) and the intact model decodes with the calculator on;
the lesion is then 'nocalc' (calculator off). Off (default) is the code before it, bit for bit."""
import re
import torch
from custom_io import capcount
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


def target_text_all(row):
    """B3 steps-for-all (PTS, all_steps=True): '; '.join(steps) + ' # ' + answer for every row that has steps, else the answer. No family gate, no cut.
    The same rule as caps.measure(all_steps=True), so the caps report and the trained target are the same string."""
    return '; '.join(row['steps']) + ' # ' + row['answer'] if row.get('steps') else row['answer']


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


_STEP_START = re.compile(r'[;=#]')
_EXPR_OK = re.compile(r'[\d\s+\-*/x()]+')
_TOK = re.compile(r'\d+|[-+*/x()]')


def _eval_expr(toks):
    """Integer value of a token list: + - * / x, normal precedence, brackets, unary minus; '/' only when exact. Raises on anything else."""
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        pos[0] += 1
        return toks[pos[0] - 1]

    def expr():
        v = term()
        while peek() in ('+', '-'):
            v = v + term() if take() == '+' else v - term()
        return v

    def term():
        v = unary()
        while peek() in ('*', '/', 'x'):
            op = take()
            n = unary()
            if op == '/':
                if n == 0 or v % n:
                    raise ValueError('inexact division')
                v //= n
            else:
                v *= n
        return v

    def unary():
        if peek() == '-':
            take()
            return -unary()
        if peek() == '(':
            take()
            v = expr()
            if peek() != ')':
                raise ValueError('bracket')
            take()
            return v
        t = peek()
        if t is None or not t.isdigit():
            raise ValueError('operand')
        return int(take())

    v = expr()
    if pos[0] != len(toks):
        raise ValueError('trailing')
    return v


def calc_full(text):
    """The calculator of PTC: if text ends with '=' and the whole integer expression since the last step start (start of text, or after ';' '=' '#' and an optional
    space) is evaluable (+ - * / x, precedence, brackets, negative numbers, at least one operator, '/' only when exact), return the string to force in (' ' + result
    when the '=' had a space before it, else the bare result), else None. 'x = 6 * 7 =' -> ' 42' (the variable part is not an expression). Never raises."""
    try:
        if not text.endswith('=') or len(text) > 400:
            return None
        body = text[:-1]
        sp = body.endswith(' ')
        if sp:
            body = body[:-1]
        starts = [m.end() for m in _STEP_START.finditer(body)]
        e = body[starts[-1]:] if starts else body
        if e.startswith(' '):
            e = e[1:]
        if not e or not _EXPR_OK.fullmatch(e):
            return None
        toks = _TOK.findall(e)
        if not any(t in '+-*/x' for t in toks if not t.isdigit()):
            return None
        return (' ' if sp else '') + str(_eval_expr(toks))
    except Exception:
        return None


def calc_mask(text):
    """-> (mask, n_mismatch): mask[i] is True where generate() with the calculator on would force text[i] in. Walks the gold text as generate() walks the decoded
    one: after each character that was written (not forced) ask calc_full(prefix); if it answers f and the gold text continues with f (and does not run on
    into more digits), those len(f) characters are forced (masked) and skipped; if the gold writes something else the step is a mismatch (counted, left in)."""
    mask, bad, i = [False] * len(text), 0, 0
    while i < len(text):
        i += 1                                   # text[i - 1] was written by the model
        if text[i - 1] != '=':
            continue                             # calc_full answers only on a trailing '='
        f = calc_full(text[:i])
        if not f:
            continue
        j = i + len(f)
        if text.startswith(f, i) and not (f[-1].isdigit() and text[j:j + 1].isdigit()):
            mask[i:j] = [True] * len(f)
            i = j                                # a forced string is inserted whole; the character after it is the next one asked about
        else:
            bad += 1
    return mask, bad


def final_answer(text):
    return text.rsplit('#', 1)[1].strip() if '#' in text else text.strip()


class PlainTFSteps(PlainTF):
    LESIONS = ['calc']

    def __init__(self, vocab, d_model=256, n_layers=4, n_heads=4, n_loops=1, place=False, all_steps=False, calc_train=False):
        super().__init__(vocab, d_model, n_layers, n_heads, n_loops)
        self.all_steps = bool(all_steps)    # B3 steps-for-all (PTS): a plain bool, no weights and no RNG draw, so the default is unchanged
        self.calc_train = bool(calc_train)  # PTC: same (no weights, no RNG draw)
        if self.calc_train:
            self.LESIONS = ['nocalc']       # instance-level: the intact model has the calculator on, the lesion turns it off ('calc' is the old forcing, PT / PTS only)
        self.pos = nn.Embedding(MAX_POS, d_model)
        nn.init.normal_(self.pos.weight, std=0.02)
        if place:                   # last, after pos is replaced, so no other weight's init moves (see PlainTF._add_place)
            self._add_place()

    def _set_front(self, batch, width):
        """Hook for a front end that adds a per-char term to the prompt input embeddings (g8a plain_tf_steps_g with eg_embed). Called with the batch and the
        sequence width at the start of loss() and generate(); a no-op here."""

    def _targets(self, batch):
        """-> ids [B, A] (target chars + EOS, PAD after), mask [B, A]."""
        if self.all_steps:      # PTS: every row with steps, no family gate, no cut (caps refuse any row longer than plain_target)
            texts = [target_text_all(r) for r in batch['rows']]
            capcount.hit('plain_target_over', sum(len(t) > CAP for t in texts))
            enc = [self.vocab.encode(t) + [EOS] for t in texts]
        else:
            enc = [self.vocab.encode(target_text(r))[:CAP + 12] + [EOS] for r in batch['rows']]
            capcount.hit('plain_target_over', sum(len(target_text(r)) > CAP + 12 for r in batch['rows']))
        dev = batch['prompt_ids'].device
        ids = torch.full((len(enc), max(map(len, enc))), PAD, dtype=torch.long)
        for i, e in enumerate(enc):
            ids[i, :len(e)] = torch.tensor(e)
        return ids.to(dev), (ids != PAD).to(dev)

    def _calc_loss_mask(self, batch, a):
        """[B, A] bool, True on the characters the calculator writes (left out of the loss). The length mask (am) is untouched: it sets the width W."""
        texts = [(target_text_all(r) if self.all_steps else target_text(r)[:CAP + 12]) for r in batch['rows']]
        m = torch.zeros(a.shape, dtype=torch.bool)
        n_bad = n_forced = 0
        for i, t in enumerate(texts):
            cm, bad = calc_mask(t)
            n_bad += bad
            n_forced += sum(cm)
            k = 0
            for c, f in zip(t, cm):
                u = self.vocab.length(c)
                if f:
                    m[i, k:k + u] = True
                k += u
        capcount.hit('calc_mismatch', n_bad)
        capcount.hit('calc_forced', n_forced)
        capcount.hit('calc_rows', len(texts))
        return m.to(a.device)

    def loss(self, batch):
        p, lens = batch['prompt_ids'], batch['prompt_mask'].sum(1)
        a, am = self._targets(batch)
        lm = am & ~self._calc_loss_mask(batch, a) if self.calc_train else am       # loss mask; `am` alone sets the width W below
        B, T, A = p.shape[0], p.shape[1], a.shape[1]
        self._set_front(batch, T + 2 + A)
        seq = p.new_full((B, T + 2 + A), PAD)
        seq[:, 0], seq[:, 1:1 + T] = BOS, p
        r = torch.arange(B, device=p.device)
        seq[r, 1 + lens] = SEP
        j = torch.arange(A, device=p.device)
        seq.scatter_(1, (2 + lens)[:, None] + j, a)
        tgt = torch.full_like(seq, -100)
        tgt.scatter_(1, (1 + lens)[:, None] + j, torch.where(lm, a, torch.full_like(a, -100)))
        W = int((2 + lens + am.sum(1)).max())
        lg = self.logits(self.hidden_upto(seq, W, None, self.place_seq(batch, seq.shape[1]))).float()
        return F.cross_entropy(lg.reshape(-1, lg.shape[-1]), tgt[:, :W].reshape(-1), ignore_index=-100)

    @torch.no_grad()
    def generate(self, batch, lesion=None):
        name, arg = self.check_lesion(lesion)
        loops, calc = (arg if name == 'loops' else None), name == 'calc'
        fill = calc_fill
        if self.calc_train:         # PTC: the calculator is part of the model; only the lesion turns it off
            calc, fill = name != 'nocalc', calc_full
        p, lens = batch['prompt_ids'], batch['prompt_mask'].sum(1)
        B, T = p.shape
        seq = p.new_full((B, T + 2 + MAX_NEW), PAD)
        seq[:, 0], seq[:, 1:1 + T] = BOS, p
        r = torch.arange(B, device=p.device)
        seq[r, 1 + lens] = SEP
        self._set_front(batch, seq.shape[1])
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
                    if calc and not queue[i] and forced[i] is None and (f := fill(txt[i])):
                        queue[i] = self.vocab.encode(f)
            if all(done):
                break
        return [final_answer(s) for s in txt]
