"""Talker 24 -- the ONE place that knows what the data on disk looks like.

Two other builders own the producers:

  * ``scripts/fable_talker24_data.py`` (build task 1) writes the token shards and the
    tokenizer export.  Its contract is
    ``artifacts/fable-talker24-20260920/INTERFACE-data.md`` -- read on 2026-09-20 and
    implemented here exactly.  THAT FILE IS NOT EDITED BY THIS BUILDER.
  * build task 2 writes the dialogue records with gold thought labels.  Its contract,
    ``INTERFACE-dialogues.md`` (format ``fable-talker24-dialogues/1``), appeared while
    this module was being written and is now implemented for real in the
    "dialogues v1" section below.  The first draft's guessed schema is kept as
    ``parse_legacy_record`` so nothing that was already written against it breaks.
    THAT FILE IS NOT EDITED BY THIS BUILDER EITHER.

THE MISSING BRIDGE.  Task 1 ships *tokens* (corpora) and a tokenizer; task 2 ships *text*
plus exact labels and explicitly does no tokenisation.  Nobody owns turning a dialogue
record into token ids, so this module does it: a pure-Python byte-level BPE encoder driven
by ``shards/tokenizer_vocab.json`` + ``shards/tokenizer_merges.txt``, plus the published
name rule from ``LEXICON.json``.  Every assumption that bridge makes is in ``ASSUMPTIONS``.

Numpy + stdlib only.  No ``tokenizers``, no ``datasets``, no ``pyarrow``: the training
path on the Windows GPU box must not need them (design section 2.1 / D8).

Everything also works with NO DATA AT ALL: ``synthetic_shard`` and
``synthetic_dialogues`` build the same objects in memory, which is what the unit tests and
the Mac CPU dry run of S0 use.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import random
import sys

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# fable_talker24_model puts the project's read-only wheel cache on sys.path when torch is
# not an ordinary import (the Mac); on the GPU box it is a no-op.  numpy rides along.
from fable_talker24_model import (PAD, BOS, EOS, UNK, ENT, SUBJ, OBJ, OLD, TURN, DOC,
                                  ENT_NONE, ENT_POOL, ENT_RESERVED_MIN, VALUE_CODE_MIN,
                                  VALUE_CODE_COUNT,
                                  VOCAB_SIZE, HEARD_ACTS, REPLY_ACTS, RELATION_SLOTS,
                                  RELATION_CHOICES, RELATION_NONE, FLAG_NAMES)

import numpy as np                                                     # noqa: E402

ARTIFACTS = Path(__file__).resolve().parent.parent/'artifacts/fable-talker24-20260920'

# ------------------------------------------------------------------------- assumptions

ASSUMPTIONS = [
    ('shards', 'CONTRACT',
     'INTERFACE-data.md section 1: <split>/<split>-NNNNN.{tokens.u16,ents.u16,sents.u32,'
     'docs.u32} + .json sidecar, raw little-endian, CSR sentence/document indices.'),
    ('specials', 'CONTRACT',
     'INTERFACE-data.md section 2: pad0 bos1 eos2 unk3 ENT4 SUBJ5 OBJ6 OLD7 TURN8 DOC9, '
     'extras 10-15, learned pieces 16..8191, copy actions INSIDE the 8,192 vocabulary. '
     'The mouth therefore has an exactly 8,192-wide tied head and no bolted-on logits.'),
    ('ent-codes', 'CONTRACT',
     'INTERFACE-data.md section 3: entity code ids 0..4095, 3072..4095 reserved and never '
     'drawn, 65535 = "no code". The 48 numbers themselves belong to the model side.'),
    ('sentence-length', 'CONTRACT',
     'INTERFACE-data.md section 5: no sentence in a shard exceeds 48 pieces; the trainer '
     'adds <bos>/<eos> and padding itself.'),
    ('value-codes', 'MODEL-SIDE EXTENSION',
     'The data pipeline codes names only. The object pointer must be able to copy a VALUE '
     '("a drum") as exactly as it copies a name, so code ids 4096..4351 are reserved here '
     'for values. Nothing in INTERFACE-data.md changes; 65535 still means "no code" and '
     'every id still fits in uint16. If build task 2 supplies value spans under another '
     'name, only VALUE_CODE_MIN and DialogueRecord.copy_codes move.'),
    ('bos-eos-framing', 'TRAINER CHOICE',
     'A training sentence is <bos> tokens... <eos>, padded with 0. The mouth is fed the '
     'sequence starting at <bos> and predicts the next token, so the loss covers the real '
     'tokens and the single <eos>.'),
    ('dialogues', 'CONTRACT',
     'INTERFACE-dialogues.md, format "fable-talker24-dialogues/1": JSON Lines, one '
     'dialogue per line, sort_keys, separators (",",":"). Record = id/format/split/index/'
     'seed_key/symbol_mode/world{people[{slot,name,symbol}],values,relations,n_people,'
     'code_pool}/turns[{i,user{text,thought,...},reply{text,surface,copy[],thought},'
     'notebook{...}}]/final_view/counts/levels. Thought = act (STRING), subject|object|old '
     '(objects with slot/name/symbol/span or null), relation_path (relation WORDS), '
     'flags{path_len,speaker,unknown_reason,unknown_step,has_old_value,teachable}. '
     'Implemented in parse_v1_record; missing keys are still filled and counted.'),
    ('dialogue-tokenisation', 'TRAINER CHOICE -- NOBODY ELSE OWNS IT',
     'INTERFACE-dialogues.md section 9 ships TEXT and says tokenisation is the data '
     'builder\'s job; INTERFACE-data.md tokenises corpora only. So this module encodes '
     'dialogue text itself with BytePairEncoder (pure-Python byte-level BPE over '
     'shards/tokenizer_vocab.json + tokenizer_merges.txt) and the published name rule '
     '(capitalised AND lower-cased form absent from LEXICON.json). If build task 1 later '
     'ships encoded dialogues, only load_dialogues changes.'),
    ('name-substitution', 'TRAINER CHOICE',
     'In user text a NAME is replaced by the single token <ENT> and its code goes in both '
     'ents[] and copy_codes[]. A VALUE word (drum, kite) keeps its real pieces -- the ears '
     'must read it -- and its code is tagged onto the FIRST piece of the span in '
     'copy_codes[] only. That is why ents[] and copy_codes[] are two arrays.'),
    ('symbol-to-code', 'TRAINER CHOICE',
     'm0 mode: person code = symbol - 52 (entity tokens 52..67 of fable_notebook_m0), '
     'value code = 4096 + (symbol - 12) (VALUE_WORDS order). pool mode: person code = '
     'world.code_pool.indices[slot], already a 0..4095 pool row. Out-of-range symbols are '
     'folded into range and counted as "symbol_out_of_range".'),
    ('dialogue-act-names', 'CONTRACT + one deliberate move',
     'Acts arrive as the strings TELL/ASK/CORRECT/CHAT/UNCLEAR and ACK/ANSWER/UNKNOWN/'
     'CLARIFY/CHAT, matched by NAME. CHAT is index 3 in BOTH alphabets (see '
     'fable_talker24_model: the design listed CHAT last for replies; it is moved so the '
     '"gist cut to 32 unless CHAT" rule is one index, not two).'),
    ('relations', 'CONTRACT',
     'relation_path arrives as 0-3 relation WORDS; they become ids 1=friend 2=gift '
     '3=prize 4=charm with 0 = "none" (RELATION_NONE), 5..15 spare. Unknown relation '
     'words are given the next free id in first-seen order and counted.'),
    ('flags', 'TRAINER CHOICE',
     'The 8 flag numbers are path_len bit0/bit1, speaker_is_model, and a three-way '
     'one-hot of unknown_reason (no_such_person / no_such_fact / chain_broke), '
     'has_old_value, and spare7 = "not teachable" (flags.teachable false, which also '
     'covers unknown_reason == not_teachable). unknown_reason == "unclear" sets no bit: '
     'the UNCLEAR/CLARIFY act already says it. unknown_step is NOT in the thought.'),
    ('lexicon', 'GUESS',
     'LEXICON.json is read as a JSON list of words, or a dict under "words"/"lexicon"/'
     '"lexicon_words", or a dict whose keys are the words. If it is missing, the name '
     'rule falls back to "capitalised and matches a name in world.people".'),
]


def describe_assumptions():
    lines = ['format assumptions of fable_talker24_loader.py', '']
    for key, kind, text in ASSUMPTIONS:
        lines.append(f'[{kind}] {key}: {text}')
    return '\n'.join(lines)


M0_RELATIONS = {'none': 0, 'friend': 1, 'gift': 2, 'prize': 3, 'charm': 4}
M0_RELATION_NAMES = {v: k for k, v in M0_RELATIONS.items()}


# ----------------------------------------------------------------------- the tokenizer

@dataclass
class TokenizerExport:
    """Only what the training path needs: sizes, special ids, and id -> piece."""
    vocab_size: int = VOCAB_SIZE
    specials: dict = field(default_factory=lambda: {
        '<pad>': PAD, '<bos>': BOS, '<eos>': EOS, '<unk>': UNK, '<ENT>': ENT,
        '<SUBJ>': SUBJ, '<OBJ>': OBJ, '<OLD>': OLD, '<TURN>': TURN, '<DOC>': DOC})
    pieces: list = field(default_factory=list)
    lowercase: bool = True
    sha256: dict = field(default_factory=dict)

    @classmethod
    def load(cls, shards_dir):
        shards_dir = Path(shards_dir)
        meta_path = shards_dir/'tokenizer_meta.json'
        vocab_path = shards_dir/'tokenizer_vocab.json'
        if not meta_path.exists():
            return cls(pieces=[f'<{i}>' for i in range(VOCAB_SIZE)])
        meta = json.loads(meta_path.read_text())
        pieces = [f'<{i}>' for i in range(meta['vocab_size'])]
        if vocab_path.exists():
            for piece, i in json.loads(vocab_path.read_text()).items():
                if 0 <= int(i) < len(pieces):
                    pieces[int(i)] = piece
        return cls(vocab_size=meta['vocab_size'], specials=meta['specials'],
                   pieces=pieces, lowercase=meta.get('lowercase', True),
                   sha256=meta.get('sha256', {}))

    def name_bearing_pieces(self):
        """The copy wall's data-side half: the vocabulary must contain NO name.

        Names were replaced by ``<ENT>`` before the BPE was trained, so no piece is a
        name.  Anything that turns up here would be a hole in the wall and the test in
        tests/test_fable_talker24_model.py fails loudly.
        """
        return [p for i, p in enumerate(self.pieces)
                if i not in self.specials.values() and p.startswith('<') and p.endswith('>')
                and p not in ('<', '>')]

    def decode(self, ids):
        """Rough, readable decode for eyeballing.  The real byte-level decode lives in the
        pipeline's own ``shards/decode_numpy.py``; nothing in training needs it."""
        out = []
        for i in ids:
            i = int(i)
            if i in (PAD, BOS, EOS, UNK, DOC):
                continue
            out.append(self.pieces[i] if i < len(self.pieces) else f'<{i}>')
        return ''.join(out).replace('Ġ', ' ')


# --------------------------------------------------------------------------- the shards

@dataclass
class Shard:
    stem: str
    meta: dict
    tokens: np.ndarray
    ents: np.ndarray
    sents: np.ndarray
    docs: np.ndarray

    def sentence(self, i):
        a, b = int(self.sents[i]), int(self.sents[i + 1])
        return np.asarray(self.tokens[a:b]), np.asarray(self.ents[a:b])

    @property
    def n_sentences(self):
        return len(self.sents) - 1


def load_shard(stem):
    """INTERFACE-data.md section 1, verbatim."""
    stem = Path(stem)
    meta = json.loads(stem.with_suffix('.json').read_text())
    if meta.get('byte_order', 'little') != 'little':
        raise ValueError(f'{stem}: byte order {meta["byte_order"]!r} is not supported')
    tokens = np.memmap(f'{stem}.tokens.u16', dtype='<u2', mode='r')
    ents = np.memmap(f'{stem}.ents.u16', dtype='<u2', mode='r')
    sents = np.fromfile(f'{stem}.sents.u32', dtype='<u4')
    docs = np.fromfile(f'{stem}.docs.u32', dtype='<u4')
    shard = Shard(str(stem), meta, tokens, ents, sents, docs)
    check_shard(shard)
    return shard


def check_shard(shard):
    """The invariants INTERFACE-data.md promises.  Cheap; run on every open."""
    s, d, n = shard.sents, shard.docs, len(shard.tokens)
    assert len(shard.ents) == n, 'ents must be 1:1 with tokens'
    assert s[0] == 0 and s[-1] == n, 'sentence CSR must span the shard'
    assert bool((np.diff(s) > 0).all()), 'no empty sentences'
    assert d[0] == 0 and int(d[-1]) == len(s) - 1, 'document CSR must span the sentences'
    assert bool((np.diff(d) > 0).all()), 'no empty documents'
    return True


def list_shards(root, split):
    root = Path(root)/split
    if not root.is_dir():
        return []
    return sorted(str(p)[:-len('.json')] for p in root.glob(f'{split}-*.json'))


def synthetic_shard(n_sentences=256, seed=0, vocab_size=VOCAB_SIZE, max_len=16,
                    ent_rate=0.35):
    """The same object, from nothing.  Used by the tests and the Mac CPU dry run."""
    rng = np.random.default_rng(seed)
    tokens, ents, sents = [], [], [0]
    for _ in range(n_sentences):
        length = int(rng.integers(4, max_len + 1))
        ids = rng.integers(16, vocab_size, size=length).astype(np.uint16)
        codes = np.full(length, ENT_NONE, dtype=np.uint16)
        if rng.random() < ent_rate:
            pos = int(rng.integers(0, length))
            ids[pos] = ENT
            codes[pos] = int(rng.integers(0, ENT_RESERVED_MIN))
        tokens.append(ids)
        ents.append(codes)
        sents.append(sents[-1] + length)
    tokens = np.concatenate(tokens)
    ents = np.concatenate(ents)
    sents = np.asarray(sents, dtype=np.uint32)
    step = max(1, n_sentences//8)
    docs = np.asarray(list(range(0, n_sentences, step)) + [n_sentences], dtype=np.uint32)
    docs = np.unique(docs)
    meta = dict(split='synthetic', index=0, byte_order='little', n_tokens=int(len(tokens)),
                n_sentences=int(n_sentences), n_documents=int(len(docs) - 1),
                source_counts={'synthetic': int(len(tokens))}, schema_version=1,
                synthetic=True, seed=seed)
    shard = Shard('synthetic', meta, tokens, ents, sents, docs)
    check_shard(shard)
    return shard


# ------------------------------------------------------- deterministic sentence batches

class SentenceStream:
    """Length-bucketed sentences in an order that is a pure function of (seed, position).

    Section 2.6: ``the data order is a pure function of (seed, step)``.  The order here is
    one fixed permutation per (seed, shard, max_len) -- so a resumed run at position k sees
    exactly what the uninterrupted run saw at position k, which is what makes the kill test
    bit-identical rather than merely close.
    """

    def __init__(self, shards, seed=0, max_len=48, min_len=1):
        self.shards, self.seed, self.max_len, self.min_len = shards, seed, max_len, min_len
        self.index = []                          # (shard, sentence) pairs
        for si, shard in enumerate(shards):
            lengths = np.diff(shard.sents)
            keep = np.nonzero((lengths >= min_len) & (lengths <= max_len))[0]
            self.index.append((si, keep))
        self.order = self._order()
        self.position = 0

    def _order(self):
        parts = []
        for si, keep in self.index:
            rng = np.random.default_rng([self.seed, si, self.max_len])
            perm = rng.permutation(len(keep))
            parts.append(np.stack((np.full(len(keep), si), keep[perm]), axis=1))
        if not parts:
            return np.zeros((0, 2), dtype=np.int64)
        allparts = np.concatenate(parts).astype(np.int64)
        rng = np.random.default_rng([self.seed, 9999, self.max_len])
        return allparts[rng.permutation(len(allparts))]

    def __len__(self):
        return len(self.order)

    def state(self):
        return dict(position=int(self.position), seed=int(self.seed),
                    max_len=int(self.max_len), min_len=int(self.min_len))

    def load_state(self, state):
        if state.get('max_len') != self.max_len or state.get('seed') != self.seed:
            self.max_len = int(state['max_len'])
            self.seed = int(state['seed'])
            self.min_len = int(state.get('min_len', 1))
            self.__init__(self.shards, self.seed, self.max_len, self.min_len)
        self.position = int(state['position'])

    def set_max_len(self, max_len):
        """The length curriculum (12 -> 24 -> 48).  Changing it restarts the stream's
        order, which is fine because the new order is again a pure function of the seed --
        and the checkpoint records both, so a resume reproduces it."""
        if max_len == self.max_len:
            return
        self.max_len = max_len
        self.order = self._order()
        self.position = 0

    def take(self, n):
        if len(self.order) == 0:
            raise RuntimeError('no sentences in this stream')
        out = []
        for _ in range(n):
            si, sent = self.order[self.position % len(self.order)]
            self.position += 1
            tokens, ents = self.shards[int(si)].sentence(int(sent))
            out.append((tokens, ents))
        return out


def pad_batch(pairs, max_len, add_bos_eos=True, device=None):
    """<bos> tokens <eos>, padded with 0.  Returns the tensors the model expects."""
    import torch
    rows, codes = [], []
    for tokens, ents in pairs:
        ids = [BOS] + [int(t) for t in tokens][:max_len] + [EOS] if add_bos_eos \
            else [int(t) for t in tokens][:max_len]
        cod = [ENT_NONE] + [int(c) for c in ents][:max_len] + [ENT_NONE] if add_bos_eos \
            else [int(c) for c in ents][:max_len]
        rows.append(ids)
        codes.append(cod)
    width = max(len(r) for r in rows)
    token_t = torch.full((len(rows), width), PAD, dtype=torch.long)
    code_t = torch.full((len(rows), width), ENT_NONE, dtype=torch.long)
    for i, (r, c) in enumerate(zip(rows, codes)):
        token_t[i, :len(r)] = torch.tensor(r, dtype=torch.long)
        code_t[i, :len(c)] = torch.tensor(c, dtype=torch.long)
    if device is not None:
        token_t, code_t = token_t.to(device), code_t.to(device)
    return token_t, code_t


# ------------------------------------------------------------------- dialogues (task 2)

def _act_index(value, alphabet):
    if isinstance(value, int):
        return value
    value = str(value).upper()
    return alphabet.index(value) if value in alphabet else alphabet.index('CHAT')


@dataclass
class Turn:
    tokens: list
    ents: list
    copy_codes: list
    act: int
    subject_code: int
    relation_path: list
    object_code: int
    flags: list
    reply_tokens: list
    reply_act: int
    reply_subject_code: int
    reply_object_code: int
    reply_relation_path: list
    reply_flags: list
    level: str = 'L1'
    speaker: str = 'you'


@dataclass
class DialogueSet:
    turns: list
    filled: dict
    source: str

    def __len__(self):
        return len(self.turns)


def _get(record, key, default, filled):
    if key in record and record[key] is not None:
        return record[key]
    filled[key] = filled.get(key, 0) + 1
    return default


def parse_dialogue_record(record, filled):
    """One record -> Turn objects.  Missing keys are filled and counted, never crash."""
    out = []
    for turn in record.get('turns', []):
        thought = _get(turn, 'thought', {}, filled)
        reply = _get(turn, 'reply_thought', {}, filled)
        tokens = [int(t) for t in _get(turn, 'tokens', [], filled)]
        ents = [int(c) for c in _get(turn, 'ents', [ENT_NONE]*len(tokens), filled)]
        copies = [int(c) for c in _get(turn, 'copy_codes', ents, filled)]
        path = list(_get(thought, 'relation_path', [RELATION_NONE]*RELATION_SLOTS, filled))
        rpath = list(_get(reply, 'relation_path', path, filled))
        out.append(Turn(
            tokens=tokens, ents=ents, copy_codes=copies,
            act=_act_index(_get(thought, 'act', 'CHAT', filled), HEARD_ACTS),
            subject_code=int(_get(thought, 'subject_code', ENT_NONE, filled)),
            relation_path=(path + [RELATION_NONE]*RELATION_SLOTS)[:RELATION_SLOTS],
            object_code=int(_get(thought, 'object_code', ENT_NONE, filled)),
            flags=list(_get(thought, 'flags', [0.0]*len(FLAG_NAMES), filled)),
            reply_tokens=[int(t) for t in _get(turn, 'reply_tokens', [], filled)],
            reply_act=_act_index(_get(reply, 'act', 'CHAT', filled), REPLY_ACTS),
            reply_subject_code=int(_get(reply, 'subject_code', ENT_NONE, filled)),
            reply_object_code=int(_get(reply, 'object_code', ENT_NONE, filled)),
            reply_relation_path=(rpath + [RELATION_NONE]*RELATION_SLOTS)[:RELATION_SLOTS],
            reply_flags=list(_get(reply, 'flags', [0.0]*len(FLAG_NAMES), filled)),
            level=str(turn.get('level', record.get('level', 'L1'))),
            speaker=str(turn.get('speaker', 'you'))))
    return out


parse_legacy_record = parse_dialogue_record          # the first draft's guessed schema


# =================================================== dialogues, format .../1 (the real one)
#
# INTERFACE-dialogues.md, read 2026-09-20.  Text in, tokens out.  Everything that knows
# about that file lives between here and `load_dialogues`.

DIALOGUE_FORMAT = 'fable-talker24-dialogues/1'
M0_PERSON_SYMBOL_MIN = 52                  # entity tokens 52..67, fable_notebook_m0
M0_VALUE_SYMBOL_MIN = 12                   # value words 12..27, VALUE_WORDS order
USER_ACTS = HEARD_ACTS
UNKNOWN_REASON_FLAG = {'no_such_person': 'unknown_no_person',
                       'no_such_fact': 'unknown_no_fact',
                       'chain_broke': 'unknown_chain_broke',
                       'not_teachable': 'spare7'}
COPY_TOKEN = {'<SUBJ>': SUBJ, '<OBJ>': OBJ, '<OLD>': OLD,
              'subject': SUBJ, 'object': OBJ, 'old': OLD}


def _bytes_to_unicode():
    """GPT-2's byte<->printable-character table; the ByteLevel BPE of INTERFACE-data.md
    section 4 is defined in terms of it."""
    printable = (list(range(ord('!'), ord('~') + 1))
                 + list(range(ord('\xa1'), ord('\xac') + 1))
                 + list(range(ord('\xae'), ord('\xff') + 1)))
    table, extra = list(printable), 0
    for b in range(256):
        if b not in printable:
            printable.append(b)
            table.append(256 + extra)
            extra += 1
    return {b: chr(c) for b, c in zip(printable, table)}


BYTE_TO_CHAR = _bytes_to_unicode()
CHAR_TO_BYTE = {c: b for b, c in BYTE_TO_CHAR.items()}

# GPT-2's pre-tokenizer pattern, with \p{L}/\p{N} spelled the way the stdlib `re` can.
import re                                                              # noqa: E402
PRETOKEN = re.compile(r"'s|'t|'re|'ve|'m|'ll|'d| ?[^\W\d_]+| ?\d+| ?[^\s\w]+|\s+(?!\S)|\s+")


class BytePairEncoder:
    """Byte-level BPE, stdlib only, from the export INTERFACE-data.md section 4 promises.

    The GPU box must be able to encode without the ``tokenizers`` wheel; that is exactly
    why the merge table is exported, and this is the consumer of it.
    """

    def __init__(self, vocab, merges, lowercase=True):
        self.vocab = dict(vocab)
        self.pieces = [None]*(max(self.vocab.values()) + 1)
        for piece, i in self.vocab.items():
            self.pieces[int(i)] = piece
        self.ranks = {tuple(pair): rank for rank, pair in enumerate(merges)}
        self.lowercase = lowercase
        self._cache = {}

    # ------------------------------------------------------------------ loading
    @classmethod
    def load(cls, shards_dir):
        shards_dir = Path(shards_dir)
        vocab_path = shards_dir/'tokenizer_vocab.json'
        merges_path = shards_dir/'tokenizer_merges.txt'
        if not vocab_path.exists() or not merges_path.exists():
            return None
        vocab = json.loads(vocab_path.read_text())
        merges = []
        for line in merges_path.read_text().splitlines():
            if not line or line.startswith('#'):
                continue
            parts = line.split(' ')
            if len(parts) == 2:
                merges.append((parts[0], parts[1]))
        meta_path = shards_dir/'tokenizer_meta.json'
        lower = True
        if meta_path.exists():
            lower = json.loads(meta_path.read_text()).get('lowercase', True)
        return cls(vocab, merges, lowercase=lower)

    # ------------------------------------------------------------------ encoding
    def _bpe(self, token):
        if token in self._cache:
            return self._cache[token]
        word = list(token)
        while len(word) > 1:
            best, where = None, -1
            for i in range(len(word) - 1):
                rank = self.ranks.get((word[i], word[i + 1]))
                if rank is not None and (best is None or rank < best):
                    best, where = rank, i
            if where < 0:
                break
            word[where:where + 2] = [word[where] + word[where + 1]]
        self._cache[token] = word
        return word

    def encode(self, text):
        """Text -> ids.  Unknown pieces fall back to <unk>, counted by the caller."""
        ids = []
        if self.lowercase:
            text = text.lower()
        for chunk in PRETOKEN.findall(text):
            mapped = ''.join(BYTE_TO_CHAR[b] for b in chunk.encode('utf-8'))
            for piece in self._bpe(mapped):
                ids.append(self.vocab.get(piece, UNK))
        return ids

    def encode_marked(self, text, marks):
        """Encode ``text`` where some character spans are special.

        ``marks`` is a list of ``(start, end, kind, token_id, code)``:

        * ``kind='replace'`` -- the span becomes the SINGLE token ``token_id`` (a name
          becoming ``<ENT>``, or a literal ``<SUBJ>`` marker becoming the copy action) and
          ``code`` lands in both the ents array and the copy array;
        * ``kind='tag'``    -- the span is encoded normally (a value word: the ears must
          read the actual letters) and ``code`` is attached to its FIRST piece in the copy
          array only.

        Returns ``(ids, ents, copies)``, three equal-length lists.
        """
        marks = sorted(marks, key=lambda m: m[0])
        ids, ents, copies, cursor = [], [], [], 0
        for start, end, kind, token_id, code in marks:
            if start < cursor:                      # overlapping labels: keep the first
                continue
            for i in self.encode(text[cursor:start]):
                ids.append(i); ents.append(ENT_NONE); copies.append(ENT_NONE)
            if kind == 'replace':
                ids.append(int(token_id))
                ents.append(int(code) if token_id == ENT else ENT_NONE)
                copies.append(int(code))
            else:
                piece_ids = self.encode(text[start:end]) or [UNK]
                for k, i in enumerate(piece_ids):
                    ids.append(i); ents.append(ENT_NONE)
                    copies.append(int(code) if k == 0 else ENT_NONE)
            cursor = end
        for i in self.encode(text[cursor:]):
            ids.append(i); ents.append(ENT_NONE); copies.append(ENT_NONE)
        return ids, ents, copies

    # ------------------------------------------------------------------ decoding
    def decode(self, ids, ents=None, names=None, copy=None):
        """ids -> text.  Byte-exact inverse of ``encode`` for non-special ids.

        ``ents`` is the per-position code array and ``names`` maps a code to a string, so
        ``<ENT>`` can print the person it stands for; ``copy`` maps '<SUBJ>'/'<OBJ>'/
        '<OLD>' to strings.  Anything unresolved is printed as its marker, never silently
        dropped -- an unresolved copy action must be VISIBLE (INTERFACE-data.md section 4).
        """
        out, buffer = [], []
        ents = list(ents) if ents is not None else None

        def flush():
            if buffer:
                raw = bytes(CHAR_TO_BYTE.get(c, ord('?')) for c in ''.join(buffer))
                out.append(raw.decode('utf-8', errors='replace'))
                buffer.clear()

        for position, i in enumerate(ids):
            i = int(i)
            if i in (PAD, BOS, EOS, DOC):
                continue
            if i == TURN:
                flush(); out.append('\n'); continue
            if i in (SUBJ, OBJ, OLD):
                flush()
                marker = {SUBJ: '<SUBJ>', OBJ: '<OBJ>', OLD: '<OLD>'}[i]
                out.append((copy or {}).get(marker, marker))
                continue
            if i == ENT:
                flush()
                code = ents[position] if ents is not None and position < len(ents) else None
                if names is not None and code is not None and int(code) in names:
                    out.append(str(names[int(code)]))
                elif code is not None and int(code) != ENT_NONE:
                    out.append(f'<ent:{int(code)}>')
                else:
                    out.append('<ENT>')
                continue
            piece = self.pieces[i] if i < len(self.pieces) else None
            buffer.append(piece if piece is not None else '<unk>')
        flush()
        return ''.join(out)


def load_lexicon(path):
    """The published word list the name rule uses (INTERFACE-dialogues.md section 2.2)."""
    path = Path(path)
    if not path.exists():
        return None
    blob = json.loads(path.read_text())
    if isinstance(blob, list):
        words = blob
    elif isinstance(blob, dict):
        for key in ('words', 'lexicon', 'lexicon_words', 'vocabulary'):
            if isinstance(blob.get(key), list):
                words = blob[key]
                break
        else:
            words = list(blob.keys())
    else:
        words = []
    return frozenset(str(w).lower() for w in words)


NAME_CANDIDATE = re.compile(r"[A-Z][A-Za-z'’-]*")


def find_names(text, lexicon, known=()):
    """The published rule, verbatim: capitalised AND lower-cased form not in LEXICON.

    ``known`` (the dialogue's own ``world.people`` names) is the fallback when no lexicon
    was shipped, and is also used to keep a possessive whole: ``Mira's`` -> ``<ENT>`` + ``'s``.
    """
    known = {str(k) for k in known}
    spans = []
    for match in NAME_CANDIDATE.finditer(text):
        word = match.group(0)
        end = match.end()
        for suffix in ("'s", '’s'):            # possessive: the 's is ordinary BPE
            if word.endswith(suffix) and len(word) > len(suffix):
                word, end = word[:-len(suffix)], end - len(suffix)
                break
        if word == 'I':
            continue
        is_name = (word in known) if lexicon is None else (word.lower() not in lexicon)
        if is_name:
            spans.append((match.start(), end, word))
    return spans


def _person_code(symbol, slot, world, counters):
    pool = (world or {}).get('code_pool')
    if pool and isinstance(pool.get('indices'), list) and slot is not None \
            and 0 <= slot < len(pool['indices']):
        code = int(pool['indices'][slot])
        # INTERFACE-dialogues.md section 7: `indices[slot]` is a row of
        # ``fable_newnames21.pool_subset(pool, which)`` -- an index INTO THE SUBSET, not an
        # absolute 0..4095 code.  The reserved subset's rows therefore count 0..1023 and
        # would land in the TRAINED half unless they are moved.  The model side's rule is
        # the only thing that matters downstream: 0..3071 trained, 3072..4095 never.
        if str(pool.get('pool', 'train')) == 'reserved':
            code = ENT_RESERVED_MIN + (code % (ENT_POOL - ENT_RESERVED_MIN))
        else:
            code %= ENT_RESERVED_MIN
    else:
        code = int(symbol) - M0_PERSON_SYMBOL_MIN
    if not 0 <= code < ENT_POOL:
        counters['symbol_out_of_range'] = counters.get('symbol_out_of_range', 0) + 1
        code %= ENT_POOL
    return code


def _unnamed_person_code(word, world, counters):
    """A capitalised word the name rule accepts that is NOT in ``world.people``.

    The generator emits these on purpose: an UNCLEAR turn ("both Hal's prize and Ada's
    prize are a whistle") names people the notebook never records, so they cost no symbol
    (INTERFACE-dialogues.md section 3).  They still need SOME code, and two things are
    mandatory:

    * it must be in the TRAINED half (0..3071).  The old code drew from
      ``ENT_RESERVED_MIN + ...``, which put held-out codes into training batches and would
      have voided the reserved-code evaluation.
    * it must be a pure function of the word.  ``hash()`` is salted per process in
      Python 3, so the old code gave a different batch on every run -- which silently
      breaks "the data order is a pure function of (seed, position)" (section 2.6) and any
      resume that has to be bit-identical.
    """
    counters['name_not_in_world'] = counters.get('name_not_in_world', 0) + 1
    digest = hashlib.blake2b(str(word).encode('utf-8'), digest_size=8).digest()
    code = int.from_bytes(digest, 'big') % ENT_RESERVED_MIN
    used = set()
    for person in (world or {}).get('people', []) or []:
        used.add(_person_code(person.get('symbol', 0), person.get('slot'), world, {}))
    for _ in range(len(used) + 1):           # first free code, deterministically
        if code not in used:
            return code
        code = (code + 1) % ENT_RESERVED_MIN
    return code


def _value_code(symbol, counters):
    code = VALUE_CODE_MIN + (int(symbol) - M0_VALUE_SYMBOL_MIN)
    if not VALUE_CODE_MIN <= code < VALUE_CODE_MIN + VALUE_CODE_COUNT:
        counters['symbol_out_of_range'] = counters.get('symbol_out_of_range', 0) + 1
        code = VALUE_CODE_MIN + (int(symbol) % VALUE_CODE_COUNT)
    return code


def _slot_code(node, world, counters):
    """A thought's subject/object/old node -> one code id, or ENT_NONE."""
    if not node:
        return ENT_NONE
    if node.get('kind') == 'value' or node.get('slot') is None:
        if node.get('kind') == 'person':
            return _person_code(node.get('symbol', 0), None, world, counters)
        return _value_code(node.get('symbol', M0_VALUE_SYMBOL_MIN), counters)
    return _person_code(node.get('symbol', 0), node.get('slot'), world, counters)


class RelationIds:
    """Relation WORDS -> the 0..15 slot choice.  M0's four are fixed; anything else gets
    the next free id in first-seen order so an L2/L3 wording cannot crash a run."""

    def __init__(self):
        self.ids = dict(M0_RELATIONS)
        self.unknown = 0

    def __call__(self, word):
        key = str(word).lower()
        if key not in self.ids:
            if len(self.ids) >= RELATION_CHOICES:
                self.unknown += 1
                return RELATION_NONE
            self.ids[key] = max(self.ids.values()) + 1
            self.unknown += 1
        return self.ids[key]


def flags_vector(flags, counters=None):
    """INTERFACE-dialogues.md section 6 flags -> the 8 numbers of the thought."""
    out = [0.0]*len(FLAG_NAMES)
    if not isinstance(flags, dict):
        return out
    path_len = int(flags.get('path_len') or 0)
    out[FLAG_NAMES.index('path_len_bit0')] = float(path_len & 1)
    out[FLAG_NAMES.index('path_len_bit1')] = float((path_len >> 1) & 1)
    out[FLAG_NAMES.index('speaker_is_model')] = float(flags.get('speaker') == 'model')
    reason = flags.get('unknown_reason')
    if reason in UNKNOWN_REASON_FLAG:
        out[FLAG_NAMES.index(UNKNOWN_REASON_FLAG[reason])] = 1.0
    elif reason not in (None, 'unclear') and counters is not None:
        counters['unknown_reason_unrecognised'] = \
            counters.get('unknown_reason_unrecognised', 0) + 1
    out[FLAG_NAMES.index('has_old_value')] = float(bool(flags.get('has_old_value')))
    if flags.get('teachable') is False:
        out[FLAG_NAMES.index('spare7')] = 1.0
    return out


def thought_labels(thought, world, relations, counters):
    """One ``thought`` record -> (act name, subject code, path, object code, old, flags)."""
    thought = thought or {}
    path = [relations(w) for w in (thought.get('relation_path') or [])][:RELATION_SLOTS]
    path = path + [RELATION_NONE]*(RELATION_SLOTS - len(path))
    return dict(act=str(thought.get('act', 'CHAT')).upper(),
                subject_code=_slot_code(thought.get('subject'), world, counters),
                object_code=_slot_code(thought.get('object'), world, counters),
                old_code=_slot_code(thought.get('old'), world, counters),
                relation_path=path,
                flags=flags_vector(thought.get('flags'), counters))


def encode_user_text(text, thought, world, encoder, lexicon, counters):
    """User turn -> (tokens, ents, copy_codes).

    Names become the single token ``<ENT>`` carrying their code; a value word keeps its
    letters and gets its code tagged onto its first piece (see ASSUMPTIONS).
    """
    people = {p['name']: p for p in (world or {}).get('people', []) if 'name' in p}
    marks = []
    for start, end, word in find_names(text, lexicon, people):
        person = people.get(word)
        if person is None:
            code = _unnamed_person_code(word, world, counters)
        else:
            code = _person_code(person.get('symbol', 0), person.get('slot'), world,
                                counters)
        marks.append((start, end, 'replace', ENT, code))
    for field_name in ('object', 'old'):
        node = (thought or {}).get(field_name)
        if node and node.get('span') and node.get('kind') == 'value':
            a, b = int(node['span'][0]), int(node['span'][1])
            marks.append((a, b, 'tag', None, _value_code(node.get('symbol', 12), counters)))
    ids, ents, copies = encoder.encode_marked(text, marks)
    subject = (thought or {}).get('subject')
    if subject and subject.get('span') is not None:
        wanted = _slot_code(subject, world, counters)
        if wanted not in copies:
            counters['subject_code_not_in_text'] = \
                counters.get('subject_code_not_in_text', 0) + 1
    return ids, ents, copies


def encode_reply_text(reply, encoder, counters):
    """Reply turn -> tokens.  ``reply.text`` already contains the literal copy markers, so
    the only work is turning each ``copy[k].text_span`` into the one action token.  No
    name and no value ever enters this token list -- that IS the wall of section 3.4."""
    text = reply.get('text', '')
    marks = []
    for item in reply.get('copy', []) or []:
        span = item.get('text_span')
        action = COPY_TOKEN.get(item.get('action')) or COPY_TOKEN.get(item.get('field'))
        if span is None or action is None:
            counters['copy_without_span'] = counters.get('copy_without_span', 0) + 1
            continue
        marks.append((int(span[0]), int(span[1]), 'replace', action, ENT_NONE))
    ids, _, _ = encoder.encode_marked(text, marks)
    if not marks:
        for marker, token in (('<SUBJ>', SUBJ), ('<OBJ>', OBJ), ('<OLD>', OLD)):
            if marker in text:                    # a copy list that forgot an entry
                counters['marker_without_copy_entry'] = \
                    counters.get('marker_without_copy_entry', 0) + 1
    return ids


def parse_v1_record(record, encoder, lexicon, counters, relations=None):
    """One ``fable-talker24-dialogues/1`` line -> Turn objects the trainer already eats."""
    relations = relations or RelationIds()
    world = record.get('world') or {}
    level = (record.get('levels') or {}).get('frames', record.get('split', 'L1'))
    out = []
    for turn in record.get('turns', []):
        user = _get(turn, 'user', {}, counters)
        reply = _get(turn, 'reply', {}, counters)
        heard = thought_labels(user.get('thought'), world, relations, counters)
        spoken = thought_labels(reply.get('thought'), world, relations, counters)
        tokens, ents, copies = encode_user_text(user.get('text', ''), user.get('thought'),
                                                world, encoder, lexicon, counters)
        out.append(Turn(
            tokens=tokens, ents=ents, copy_codes=copies,
            act=_act_index(heard['act'], USER_ACTS),
            subject_code=heard['subject_code'], relation_path=heard['relation_path'],
            object_code=heard['object_code'], flags=heard['flags'],
            reply_tokens=encode_reply_text(reply, encoder, counters),
            reply_act=_act_index(spoken['act'], REPLY_ACTS),
            reply_subject_code=spoken['subject_code'],
            reply_object_code=spoken['object_code'],
            reply_relation_path=spoken['relation_path'],
            reply_flags=spoken['flags'],
            level=str(level), speaker='you'))
    return out


DIALOGUE_FILES = ('{split}.jsonl', '{split}-test.jsonl', 'dialogues-{split}.jsonl')

# The sealed evaluation sets are L1/L2 indices 0..999 (SEALED-SPLITS.md).  Dialogue i is a
# pure function of (namespace, split, i) -- INTERFACE-dialogues.md section 9 -- so
# GENERATING TRAINING DATA FROM INDEX 0 WOULD REPRODUCE THE TEST SET EXACTLY.  Training
# therefore starts past the sealed block, with a wide margin so the sealed sets can grow.
SEALED_INDEX_END = 1000
TRAIN_INDEX_START = 100000


def find_dialogue_file(root, split):
    folder = Path(root)/'dialogues'
    for pattern in DIALOGUE_FILES:
        path = folder/pattern.format(split=split)
        if path.exists():
            return path
    return None


def load_dialogues(root, split='train', limit=None, shards_dir=None):
    """Read whichever dialogue file exists, in whichever of the two formats it is.

    Returns None -- never raises -- when there is no file, so a run can fall back to
    ``synthetic_dialogues`` and SAY SO in its report.
    """
    path = find_dialogue_file(root, split)
    if path is None:
        return None
    encoder = BytePairEncoder.load(Path(shards_dir or Path(root)/'shards'))
    lexicon = load_lexicon(Path(root)/'dialogues'/'LEXICON.json')
    counters, turns = {}, []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if str(record.get('format', '')).startswith('fable-talker24-dialogues/'):
                if encoder is None:
                    counters['no_tokenizer_export'] = 1
                    return DialogueSet([], counters, f'{path} (NO TOKENIZER EXPORT)')
                turns.extend(parse_v1_record(record, encoder, lexicon, counters))
            else:
                counters['legacy_record'] = counters.get('legacy_record', 0) + 1
                turns.extend(parse_legacy_record(record, counters))
            if limit and len(turns) >= limit:
                break
    return DialogueSet(turns[:limit] if limit else turns, counters, str(path))


def generate_dialogues(root, split='L1', n=512, start=TRAIN_INDEX_START,
                       symbol_mode='m0', pool='train', shards_dir=None, limit=None):
    """TRAINING DATA, STRAIGHT FROM THE GENERATOR -- no 18 GB file on disk.

    INTERFACE-dialogues.md section 1: "Training data is not shipped as a file. It is
    streamed on demand."  A record is ~18 kB, so the 1,000,000 dialogues section 4.1 asks
    for would be ~18 GB of JSON; the generator makes one in ~0.5 ms, which is far cheaper
    than reading it back.  Dialogue i depends only on (namespace, split, i), so this is
    reproducible from (split, start, n) alone and a resume re-draws the same records.

    Returns ``None`` when ``scripts/fable_talker24_dialogues.py`` cannot be imported, so
    the caller can fall back and SAY SO.
    """
    if start < SEALED_INDEX_END:
        raise ValueError(f'start={start} overlaps the sealed evaluation block '
                         f'0..{SEALED_INDEX_END - 1}; those dialogues ARE the test set')
    try:
        import fable_talker24_dialogues as G
    except Exception as exc:                                  # pragma: no cover
        return None, f'generator unavailable ({type(exc).__name__}: {exc})'
    encoder = BytePairEncoder.load(Path(shards_dir or Path(root)/'shards'))
    if encoder is None:
        return None, 'no tokenizer export beside the shards'
    lexicon = load_lexicon(Path(root)/'dialogues'/'LEXICON.json')
    generator = G.Generator(split=split, symbol_mode=symbol_mode, pool=pool)
    counters, turns, relations = {}, [], RelationIds()
    made = 0
    for index in range(start, start + n):
        record = generator.dialogue(index)
        if not isinstance(record, dict):                      # pragma: no cover
            record = json.loads(json.dumps(record, default=lambda o: o.__dict__))
        turns.extend(parse_v1_record(record, encoder, lexicon, counters, relations))
        made += 1
        if limit and len(turns) >= limit:
            break
    source = (f'generated {split}[{start}:{start + made}] symbol_mode={symbol_mode} '
              f'pool={pool} via fable_talker24_dialogues (REAL generator output)')
    return DialogueSet(turns[:limit] if limit else turns, counters, source), source


def synthetic_dialogues(n=64, seed=0, vocab_size=VOCAB_SIZE, max_len=16):
    """Fact turns with gold thought labels, built by construction (design section 4.2).

    Deliberately crude English -- this is a SHAPE stand-in so the trainer and the
    intervention harness can be exercised with no dependency on build task 2.  It is never
    a substitute for the real generator and every report that used it says so.
    """
    rng = random.Random(seed)
    turns = []
    for _ in range(n):
        act = rng.choice([0, 1, 2, 3])                       # TELL ASK CORRECT CHAT
        subject = rng.randrange(0, 256)
        value = VALUE_CODE_MIN + rng.randrange(0, 16)
        relation = rng.randrange(1, 5)
        hops = 1 if act != 1 else rng.choice([1, 1, 2])
        path = [relation] + ([rng.randrange(1, 5)] if hops == 2 else [])
        path = (path + [RELATION_NONE]*RELATION_SLOTS)[:RELATION_SLOTS]
        body = [int(rng.randrange(16, min(vocab_size, 400))) for _ in range(3)]
        tokens = [ENT] + body + ([OBJ] if act in (0, 2) else [])
        ents = [subject] + [ENT_NONE]*len(body) + ([value] if act in (0, 2) else [])
        copies = list(ents)
        if act in (0, 2):
            copies[-1] = value
        reply_act = {0: 0, 1: 1, 2: 0, 3: 3}[act]
        reply_tokens = ([SUBJ] + body[:2] + [OBJ, EOS]) if act != 3 else (body + [EOS])
        turns.append(Turn(
            tokens=tokens[:max_len], ents=ents[:max_len], copy_codes=copies[:max_len],
            act=act, subject_code=subject, relation_path=path,
            object_code=value if act in (0, 2) else ENT_NONE,
            flags=[float(hops == 2)] + [0.0]*(len(FLAG_NAMES) - 1),
            reply_tokens=reply_tokens, reply_act=reply_act,
            reply_subject_code=subject,
            reply_object_code=value if act != 3 else ENT_NONE,
            reply_relation_path=path, reply_flags=[0.0]*len(FLAG_NAMES),
            level='L1', speaker='you'))
    return DialogueSet(turns, {'synthetic': n}, 'synthetic')


def dialogue_batch(turns, device=None, reply=False):
    """Turns -> the tensors the slot / thinker stages consume."""
    import torch
    rows = [(t.reply_tokens if reply else t.tokens) for t in turns]
    codes = [([ENT_NONE]*len(t.reply_tokens) if reply else t.copy_codes) for t in turns]
    width = max(max((len(r) for r in rows), default=1), 1) + 2
    token_t = torch.full((len(turns), width), PAD, dtype=torch.long)
    code_t = torch.full((len(turns), width), ENT_NONE, dtype=torch.long)
    for i, (r, c) in enumerate(zip(rows, codes)):
        ids = [BOS] + list(r) + [EOS]
        cod = [ENT_NONE] + list(c) + [ENT_NONE]
        token_t[i, :len(ids)] = torch.tensor(ids[:width], dtype=torch.long)
        code_t[i, :len(cod)] = torch.tensor(cod[:width], dtype=torch.long)
    labels = dict(
        act=torch.tensor([t.reply_act if reply else t.act for t in turns]),
        subject_code=torch.tensor([t.reply_subject_code if reply else t.subject_code
                                   for t in turns]),
        object_code=torch.tensor([t.reply_object_code if reply else t.object_code
                                  for t in turns]),
        relation_path=torch.tensor([t.reply_relation_path if reply else t.relation_path
                                    for t in turns]),
        flags=torch.tensor([t.reply_flags if reply else t.flags for t in turns],
                           dtype=torch.float32))
    if device is not None:
        token_t, code_t = token_t.to(device), code_t.to(device)
        labels = {k: v.to(device) for k, v in labels.items()}
    return token_t, code_t, labels


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


if __name__ == '__main__':
    print(describe_assumptions())
    shard = synthetic_shard(64, seed=1)
    print('\nsynthetic shard:', shard.meta['n_tokens'], 'tokens',
          shard.n_sentences, 'sentences')
    stream = SentenceStream([shard], seed=3, max_len=12)
    print('stream of', len(stream), 'sentences; first three lengths:',
          [len(t) for t, _ in stream.take(3)])
    print('synthetic dialogues:', len(synthetic_dialogues(8)))
