"""Char vocab (CharVocab) or raw-byte vocab (ByteVocab, V1 `bytes`), dataset, collator, training-order iterator and a word-level view of prompts."""
import json, os, re, sys
import numpy as np
import torch
from custom_io import capcount

# The ONLY place the default data location is written down. Override with --data or $CUSTOM_IO_DATA.
DEFAULT_DATA = os.environ.get(
    'CUSTOM_IO_DATA',
    '/tmp/claude-0/-home-user-learner/efeefd59-f635-5d03-989e-45808869ca31/scratchpad/sk200k')
DEV_SPLITS = ['in_dist', 'answer', 'frame', 'vocab', 'variant', 'family']
MAX_PROMPT, MAX_ANS = 208, 8            # answer slots: MAX_ANS chars + EOS = MAX_ANS + 1 = 9
N_Q = 8


def set_max_ans(n):
    """Set MAX_ANS (answer chars before EOS; default 8). Dataset and collate read it at call time; call it before any data or model is built."""
    global MAX_ANS
    assert int(n) >= 1, n
    MAX_ANS = int(n)
SPECIALS = ['<pad>', '<bos>', '<eos>', '<sep>', '<unk>'] + [f'<q{i}>' for i in range(N_Q)]
PAD, BOS, EOS, SEP, UNK = range(5)
Q0 = 5                                   # Q_i id = Q0 + i, i in 0..7 (answer-slot queries)
N_SPECIAL = len(SPECIALS)
ASCII = set(chr(i) for i in range(32, 127))
KEEP = ('id', 'prompt', 'answer', 'accepted', 'family', 'level', 'stage', 'variant', 'steps')


def load_rows(path, limit=None, keep=KEEP):
    """Read a jsonl file. keep=None keeps every key (meta, slots, ...); default drops them to save RAM."""
    rows = []
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            rows.append(r if keep is None else {k: r[k] for k in keep if k in r})
            if limit and len(rows) >= limit:
                break
    return rows


class CharVocab:
    """ids: PAD=0 BOS=1 EOS=2 SEP=3 UNK=4, Q0..Q7 = 5..12, then the sorted alphabet. Unknown chars -> UNK."""

    is_bytes = False        # units (ids, positions, widths) are characters

    def __init__(self, chars):
        self.chars = ''.join(sorted(set(chars)))
        self.itos = SPECIALS + list(self.chars)
        self.stoi = {c: i + N_SPECIAL for i, c in enumerate(self.chars)}

    def __len__(self):
        return len(self.itos)

    @classmethod
    def build(cls, rows):
        # every printable ASCII char gets its own id, so symbols and capitals that only appear in dev (e.g. # $ & @ O)
        # are distinct new symbols rather than one shared UNK
        return cls(set().union(ASCII, *(set(r['prompt']) | set(r['answer']) for r in rows)))

    def encode(self, s):
        return [self.stoi.get(c, UNK) for c in s]

    # unit measures (one unit = one id): a char here, a byte in ByteVocab. Models and Dataset size everything through these.
    @staticmethod
    def length(s):
        return len(s)

    @staticmethod
    def clip(s, n):
        return s[:n]

    @staticmethod
    def offsets(s):
        """None: char offsets are unit offsets. (ByteVocab: int array [len(s) + 1], the unit offset of each char and of the end.)"""
        return None

    def decode(self, ids):
        """Ids -> string; stops at the first EOS and skips every other special."""
        out = []
        for i in ids:
            i = int(i)
            if i == EOS:
                break
            if i >= N_SPECIAL:
                out.append(self.itos[i])
        return ''.join(out)

    def save(self, path, **meta):
        with open(path, 'w') as f:
            json.dump({'specials': SPECIALS, 'chars': self.chars, **meta}, f)

    @classmethod
    def load(cls, path):
        d = json.load(open(path))
        assert d['specials'] == SPECIALS, 'vocab file was made with different specials'
        return cls(d['chars'])

    @classmethod
    def get(cls, data_dir, path=None, rows=None):
        """Load the vocab at `path` (default data_dir/charvocab.json); else build it from
        data_dir/train.jsonl (or `rows`) and cache it there. A cached default vocab is rebuilt if the
        size of train.jsonl no longer matches the one recorded in the cache."""
        train = os.path.join(data_dir, 'train.jsonl')
        path = path or os.path.join(data_dir, 'charvocab.json')
        size = os.path.getsize(train) if os.path.exists(train) else None
        if os.path.exists(path):
            d = json.load(open(path))
            if size is None or d.get('train_bytes') in (None, size):
                return cls.load(path)
        v = cls.build(rows if rows is not None else load_rows(train))
        try:
            v.save(path, train_bytes=size)
        except OSError as e:
            print(f'warning: could not cache vocab at {path}: {e}', file=sys.stderr)
        return v


class ByteVocab:
    """V1 `bytes`: the same 13 specials at 0..12, then the 256 byte values at 13..268 (269 ids). encode = UTF-8 bytes (a non-ASCII char is 2-4 ids; no UNK);
    decode = the bytes up to the first EOS, specials skipped, read as UTF-8 with errors='replace'. For ASCII text it is CharVocab's text with different ids.
    Every length in the models is in these units (see length / clip / offsets); `chars` is empty (a checkpoint records vocab='bytes')."""
    is_bytes = True

    def __init__(self):
        self.chars = ''
        self.itos = SPECIALS + [bytes([b]).decode('latin-1') for b in range(256)]
        self.stoi = {chr(b): b + N_SPECIAL for b in range(128)}        # ASCII only (a char above is several ids: use encode)

    def __len__(self):
        return N_SPECIAL + 256

    @classmethod
    def build(cls, rows=None):
        return cls()

    def encode(self, s):
        return [b + N_SPECIAL for b in s.encode('utf-8', errors='replace')]

    def decode(self, ids):
        out = bytearray()
        for i in ids:
            i = int(i)
            if i == EOS:
                break
            if N_SPECIAL <= i < N_SPECIAL + 256:
                out.append(i - N_SPECIAL)
        return out.decode('utf-8', errors='replace')

    @staticmethod
    def length(s):
        return len(s) if s.isascii() else len(s.encode('utf-8', errors='replace'))

    @staticmethod
    def clip(s, n):
        """The longest prefix of s that fits n bytes (never half a character)."""
        return s[:n] if s.isascii() else s.encode('utf-8', errors='replace')[:n].decode('utf-8', errors='ignore')

    @staticmethod
    def offsets(s):
        """None for ASCII (char offset = byte offset); else int64 [len(s) + 1]: the byte offset where each char starts, and the total at the end."""
        if s.isascii():
            return None
        return np.concatenate([[0], np.cumsum([len(c.encode('utf-8', errors='replace')) for c in s])]).astype(np.int64)

    def save(self, path, **meta):
        with open(path, 'w') as f:
            json.dump({'specials': SPECIALS, 'bytes': True, **meta}, f)


def unit_spans(vocab, text, spans):
    """[(start, end)] char offsets of `text` -> unit offsets of `vocab` (identity for CharVocab and for ASCII text)."""
    off = vocab.offsets(text)
    return spans if off is None else [(int(off[a]), int(off[e])) for a, e in spans]


class Dataset(torch.utils.data.Dataset):
    """Item = (prompt ids, answer ids + EOS, raw row). strict=False (dev data) truncates over-long answers
    instead of asserting; the dev 'family' split has answers up to 12 chars that no 8-slot model can emit."""

    def __init__(self, rows, vocab, strict=True):
        self.rows, self.vocab, self.strict = rows, vocab, strict
        ln = vocab.length       # units: chars, or bytes for ByteVocab
        assert max(ln(r['prompt']) for r in rows) <= MAX_PROMPT, 'prompt too long'
        if strict:
            assert max(ln(r['answer']) for r in rows) <= MAX_ANS, 'answer too long'

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows[i]
        a = self.vocab.encode(r['answer'])
        if len(a) > MAX_ANS:
            capcount.hit('answer_over_max')
        return self.vocab.encode(r['prompt']), a[:MAX_ANS] + [EOS], r


def collate(items):
    """-> dict(prompt_ids [B,T], prompt_mask [B,T] bool, ans_ids [B,9], ans_mask [B,9] bool, rows)."""
    B, T = len(items), max(len(p) for p, _, _ in items)
    pi, ai = np.zeros((B, T), np.int64), np.zeros((B, MAX_ANS + 1), np.int64)
    pm, am = np.zeros((B, T), bool), np.zeros((B, MAX_ANS + 1), bool)
    for b, (p, a, _) in enumerate(items):
        pi[b, :len(p)], pm[b, :len(p)] = p, True
        ai[b, :len(a)], am[b, :len(a)] = a, True
    return dict(prompt_ids=torch.from_numpy(pi), prompt_mask=torch.from_numpy(pm),
                ans_ids=torch.from_numpy(ai), ans_mask=torch.from_numpy(am), rows=[r for _, _, r in items])


def to_device(batch, device):
    return {k: (v.to(device, non_blocking=True) if torch.is_tensor(v) else v) for k, v in batch.items()}


def train_batches(ds, batch_size, order='shuffled', seed=0):
    """Endless batch iterator. 'shuffled': a fresh seeded uniform permutation every epoch.
    'curriculum': file order (easy->hard, stage 9 uniform mix last), restarting at the top each epoch."""
    assert order in ('shuffled', 'curriculum')
    rng, n = np.random.RandomState(seed), len(ds)
    while True:
        idx = rng.permutation(n) if order == 'shuffled' else np.arange(n)
        for i in range(0, n - batch_size + 1, batch_size):
            yield collate([ds[j] for j in idx[i:i + batch_size]])


# ---- word-level view -------------------------------------------------------------------------------
# Words are split on spaces; punctuation glued to a word becomes its own token ("hats." -> "hats", ".");
# "h:mm" times, "->" and "..." stay whole, apostrophes stay inside words ("Let's").
_WORD = re.compile(r"\d+:\d+|\w+(?:'\w+)*|\.\.\.|->|[^\w\s]")


def word_spans(prompt):
    """[(start, end)] char offsets of each word/punctuation token."""
    return [m.span() for m in _WORD.finditer(prompt)]


def word_ids(prompts, T):
    """-> (wid [B,T] long: word index of every char, -1 for spaces/padding; n_words [B] long).
    Lets a model pool a char-CNN over each word with scatter/segment ops."""
    wid = torch.full((len(prompts), T), -1, dtype=torch.long)
    n = torch.zeros(len(prompts), dtype=torch.long)
    for b, p in enumerate(prompts):
        spans = word_spans(p)
        n[b] = len(spans)
        for w, (a, e) in enumerate(spans):
            wid[b, a:e] = w
    return wid, n
