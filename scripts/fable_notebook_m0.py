"""M0 -- Notebook demo v0: a persistent notebook read by the FROZEN lookup operator.

EVALUATION ONLY. Nothing is trained here. No optimizer, no gradient, no checkpoint is
written. Every operator checkpoint is opened read-only and its sha256 is recorded.
Additive: nothing registered is edited; every artefact goes to
``<worktree>/artifacts/fable-notebook-m0-20260920``.

WHAT THIS IS (design/v3/21-teachable-assistant-roadmap-fable-review.md, section 2, row M0)

  Ben types an English sentence.  A RULE-BASED reader turns it into a canonical fact row
  ``[WORLD, entity, relation, object]``.  The row is appended to an append-only DIARY on
  disk and, through the CURRENT VIEW (the latest row per ``(subject, relation)``), becomes
  one line of the "story" that the frozen 79,316-parameter lookup operator reads.  A
  question is turned into the canonical form ``[QUESTION, entity, op..., ANSWER]`` and run
  through the operator's OWN fixed external loop (``astra_canonical_operator.execute``),
  which reads the hop sequence off the question.  A rule-based printer turns the answer
  token back into English.

  SUPPLIED (hand-written code, not learned): the loop, the reader, the printer, the
  correction rule, the symbol table.  LEARNED: only the lookup reader -- "given these rows
  and this (person, relation), produce the object".

  NOT SHOWN by anything in this file: learning of language, "I don't know", names beyond
  the operator's 16 entity tokens, more than 64 facts, or learned control.  An untaught
  question produces a confident wrong answer; the ``eval`` subcommand records that as the
  baseline failure rather than hiding it.

THE STORE

  ``diary.jsonl``   append-only, one JSON object per line, never rewritten:
                    ``{n, time, kind, raw, subject, relation, object, row, source}``.
                    ``kind`` is ``fact`` (a taught or corrected fact) or ``name`` (a person
                    named for the first time by a question, which costs a symbol but states
                    no fact).
  ``symbols.json``  the symbol table: name -> one of the 16 entity tokens 52..67, assigned
                    in order of first appearance.  It is a CACHE: the authoritative table
                    is re-derived from the diary on every load and the file is checked
                    against it.
  ``meta.json``     format version and the sha256 of the published vocabulary.
  ``VOCABULARY.json``  the fixed published vocabulary (relations, values, token layout).

  The current view is DERIVED from the diary on every load: walk the fact entries in order,
  ``view[(subject_token, relation_token)] = entry``.  A correction is an ordinary append; it
  replaces exactly one current-view row and keeps that row's position in the story, so the
  diary is a complete, replayable history and reloading reproduces the state exactly.

STORY PACKING, AND THE DECLARED SMALL-NOTEBOOK CHOICE

  A current-view row is packed as ``[WORLD, entity, relation, object, NEWLINE]`` -- exactly
  the generator's fact-row shape (``premonition.toy_ladder.visit``) with zero trailing
  filler tokens, which is the low end of the generator's own ``randint(0, 2)`` filler draw.
  The story is the current view and nothing else: no filler rows, no gap block, and NO
  PADDING TO A FIXED STORY SIZE.  ``premonition_memnn.pack`` sizes the memory tensor from
  the rows it is given, so a one-row notebook is presented as a one-row story.  Filler
  facts are never invented.  The named M0 risk -- notebooks of 1..15 rows were never
  trained on (the grow-blind curriculum's floor is ``blind_lines = 16`` fact rows) -- is
  therefore measured, not papered over.  An EMPTY notebook is presented as a single
  all-padding row, which ``pack`` marks ineligible and the model's zero NULL key/value
  makes safe; it is the only way to ask the operator a question with no story at all.

CLI
  teach "<sentence>"     append a fact (or a correction) to the notebook
  ask "<question>"       answer a question from the notebook, with the exact lookup trace
  chat                   interactive REPL: teach, correct, ask, :view, :diary, :help
  wipe                   archive the diary and start an empty notebook
  eval                   run the registered M0 marks, per operator seed, no averaging
  vocab                  print / publish the fixed vocabulary file
  answer-batch           internal: answer a question file in a fresh process (reload check)
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
HERE = Path(__file__).resolve().parent
if HERE != (BASE/'scripts'):
    for entry in (str(BASE), str(BASE/'scripts')):
        while entry in sys.path:
            sys.path.remove(entry)
        sys.path.insert(0, entry)

import argparse
import datetime
import hashlib
import json
import os
import random
import re
import subprocess
import tempfile

import astra_canonical_operator as A                                   # noqa: E402

torch, data = A.torch, A.data
torch.set_num_threads(1)

WORLD, QUESTION, ANSWER, LINK = A.WORLD, A.QUESTION, A.ANSWER, A.LINK
ENTITY_MIN, ENTITY_MAX = A.ENTITY_MIN, A.ENTITY_MAX
NEWLINE = 7                          # premonition.toy_ladder.NEWLINE
ATTRIBUTE_RELATIONS = (8, 9, 10)
VALUE_MIN, VALUE_COUNT = 12, 16      # toy_ladder.spec.value(v) = 12 + v, v in 0..15
FORMAT_VERSION = 'fable-notebook-m0/1'

# ------------------------------------------------------------------ fixed vocabulary
# Relations 8/9/10 and the 16 value tokens carry no meaning inside the operator; these
# words are labels chosen once and published so every session speaks the same tiny English.
RELATION_WORDS = (('friend', LINK), ('gift', 8), ('prize', 9), ('charm', 10))
RELATION_TOKEN = dict(RELATION_WORDS)
TOKEN_RELATION = {t: w for w, t in RELATION_WORDS}
ATTRIBUTE_WORDS = tuple(w for w, t in RELATION_WORDS if t in ATTRIBUTE_RELATIONS)
# All 16 begin with a consonant, so the printer's article is always "a" and the grammar
# needs no "an" rule.
VALUE_WORDS = ('drum', 'kite', 'lamp', 'rope', 'coin', 'flute', 'brush', 'candle',
               'mirror', 'ladder', 'kettle', 'basket', 'ribbon', 'feather', 'pebble',
               'whistle')
VALUE_TOKEN = {w: VALUE_MIN + i for i, w in enumerate(VALUE_WORDS)}
TOKEN_VALUE = {t: w for w, t in VALUE_TOKEN.items()}
# Suggested people.  The symbol table accepts any capitalised name; these are the sixteen
# the scripted eval sessions use.
DEFAULT_NAMES = ('Mira', 'Oren', 'Tal', 'Ada', 'Bram', 'Cleo', 'Dov', 'Esme',
                 'Finn', 'Gia', 'Hal', 'Ivo', 'Juno', 'Kai', 'Lena', 'Nils')
MAX_NAMES = ENTITY_MAX - ENTITY_MIN          # 16 entity tokens, hard limit of the operator
MAX_HOPS = 10                                # declared cap on the fixed loop's chain length

OUT = HERE.parent/'artifacts/fable-notebook-m0-20260920'
DEFAULT_NOTEBOOK = OUT/'notebook'
NAMESPACE = 'fable-notebook-m0-v1'           # fresh RNG namespace, not any existing panel's
EVAL_SEEDS = (0, 1, 2)
EVAL_SESSIONS = 64
EVAL_SIZES = (1, 2, 4, 8, 16, 32, 64)
QUESTIONS_PER_CELL = 8
PROBE_COUNT = 16
RELOAD_SESSIONS = 8

MARK_ONE_HOP = MARK_TWO_HOP = MARK_NEW_ANSWER = .95
MARK_OLD_ANSWER = .02

CHECKPOINT_ROOTS = (HERE.parent/'artifacts/fable-operator-grow-blind-20260920',
                    BASE/'artifacts/fable-operator-grow-blind-20260920')
EXPECTED_PARAMETERS = 79316


def vocabulary():
    """The fixed published vocabulary.  Source of truth; the JSON file is a publication."""
    return dict(
        format=FORMAT_VERSION,
        structural=dict(WORLD=WORLD, QUESTION=QUESTION, ANSWER=ANSWER, NEWLINE=NEWLINE),
        entity_tokens=[ENTITY_MIN, ENTITY_MAX],
        max_names=MAX_NAMES,
        max_hops=MAX_HOPS,
        relations={w: t for w, t in RELATION_WORDS},
        values={w: VALUE_TOKEN[w] for w in VALUE_WORDS},
        suggested_names=list(DEFAULT_NAMES),
        fact_row='[WORLD, entity, relation, object, NEWLINE]',
        question='[QUESTION, entity, op..., ANSWER]',
        sentence_shapes=list(SHAPES),
    )


def vocabulary_sha():
    return sha_bytes(json.dumps(vocabulary(), sort_keys=True, separators=(',', ':')).encode())


def sha_bytes(blob):
    return hashlib.sha256(blob).hexdigest()


def sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write_atomic(path, text):
    """Same-directory temp file, fsync, rename.  A reader never sees a half-written file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f'.{path.name}.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


# ============================================================ rule-based reader / printer

SHAPES = (
    "<Name>'s friend is <Name>.",
    "<Name>'s <gift|prize|charm> is a <value>.",
    "Actually, <Name>'s friend is <Name>.",
    "Actually, <Name>'s <gift|prize|charm> is a <value>.",
    "Who is <Name>'s friend?          (and <Name>'s friend's friend?, up to 10 steps)",
    "What is <Name>'s <gift|prize|charm>?   (and <Name>'s friend's ... <gift|prize|charm>?)",
)

NAME_RE = r"[A-Z][A-Za-z'\-]{0,15}"
_ATTR = '|'.join(ATTRIBUTE_WORDS)
_VAL = '|'.join(VALUE_WORDS)
RE_LINK_FACT = re.compile(rf"^(?P<actually>Actually,?\s+)?(?P<subject>{NAME_RE})'s\s+friend"
                          rf"\s+is\s+(?P<object>{NAME_RE})\.$")
RE_ATTR_FACT = re.compile(rf"^(?P<actually>Actually,?\s+)?(?P<subject>{NAME_RE})'s\s+"
                          rf"(?P<relation>{_ATTR})\s+is\s+a\s+(?P<object>{_VAL})\.$")
RE_WHO = re.compile(rf"^Who\s+is\s+(?P<subject>{NAME_RE})'s\s+(?P<chain>(?:friend's\s+)*)"
                    rf"friend\?$")
RE_WHAT = re.compile(rf"^What\s+is\s+(?P<subject>{NAME_RE})'s\s+(?P<chain>(?:friend's\s+)*)"
                     rf"(?P<relation>{_ATTR})\?$")


class ParseError(ValueError):
    """Raised with a plain message listing the accepted shapes.  The reader never guesses."""

    def __init__(self, text, reason):
        lines = [f'I could not read that: {reason}', '', 'I understand exactly these shapes:']
        lines += [f'  {shape}' for shape in SHAPES]
        lines += ['', f'  names       any capitalised word, at most {MAX_NAMES} different ones',
                  f'  values      {", ".join(VALUE_WORDS)}']
        super().__init__('\n'.join(lines))
        self.text, self.reason = text, reason


class Fact:
    """A canonical fact, in words.  ``correction`` is the speaker's flag, not a store rule."""

    kind = 'fact'

    def __init__(self, subject, relation, obj, correction=False):
        self.subject, self.relation, self.obj, self.correction = subject, relation, obj, correction

    def __eq__(self, other):
        return (isinstance(other, Fact) and (self.subject, self.relation, self.obj,
                self.correction) == (other.subject, other.relation, other.obj, other.correction))

    def __repr__(self):
        return f'Fact({self.subject!r}, {self.relation!r}, {self.obj!r}, {self.correction})'


class Question:
    """``subject`` plus a list of relation words; the last one decides Who/What."""

    kind = 'question'

    def __init__(self, subject, ops):
        self.subject, self.ops = subject, list(ops)

    def __eq__(self, other):
        return (isinstance(other, Question)
                and (self.subject, self.ops) == (other.subject, other.ops))

    def __repr__(self):
        return f'Question({self.subject!r}, {self.ops!r})'


def normalise(text):
    return re.sub(r'\s+', ' ', text.replace('’', "'").replace('‛', "'")).strip()


def parse(text):
    """English -> Fact or Question.  Raises ParseError; never guesses at a near miss."""
    s = normalise(text)
    if not s:
        raise ParseError(text, 'the line is empty')
    m = RE_LINK_FACT.match(s)
    if m:
        if m['subject'] == m['object']:
            raise ParseError(text, 'a person cannot be their own friend')
        return Fact(m['subject'], 'friend', m['object'], bool(m['actually']))
    m = RE_ATTR_FACT.match(s)
    if m:
        return Fact(m['subject'], m['relation'], m['object'], bool(m['actually']))
    for regex, tail in ((RE_WHO, 'friend'), (RE_WHAT, None)):
        m = regex.match(s)
        if not m:
            continue
        hops = len(re.findall(r"friend's", m['chain']))
        ops = ['friend']*hops + [tail if tail else m['relation']]
        if len(ops) > MAX_HOPS:
            raise ParseError(text, f'that is {len(ops)} steps; the loop is capped at {MAX_HOPS}')
        return Question(m['subject'], ops)
    if s.endswith('?'):
        raise ParseError(text, 'that is not a question shape I know')
    if s.endswith('.'):
        raise ParseError(text, 'that is not a sentence shape I know')
    raise ParseError(text, 'a statement must end in "." and a question in "?"')


def render_fact(fact):
    head = 'Actually, ' if fact.correction else ''
    if fact.relation == 'friend':
        return f"{head}{fact.subject}'s friend is {fact.obj}."
    return f"{head}{fact.subject}'s {fact.relation} is a {fact.obj}."


def render_question(question):
    chain = ''.join("friend's " for _ in question.ops[:-1])
    last = question.ops[-1]
    word = 'Who' if last == 'friend' else 'What'
    return f"{word} is {question.subject}'s {chain}{last}?"


def possessive_chain(question):
    return f"{question.subject}'s " + ''.join("friend's " for _ in question.ops[:-1]) + question.ops[-1]


def render_answer(question, phrase):
    return f'{possessive_chain(question)} is {phrase}.'


def token_phrase(token, names_by_token):
    """Answer token -> English.  Honest about tokens that are not answer words."""
    if token in TOKEN_VALUE:
        return f'a {TOKEN_VALUE[token]}'
    if ENTITY_MIN <= token < ENTITY_MAX:
        name = names_by_token.get(token)
        return name if name else f'a person I have no name for (entity token {token})'
    if token in TOKEN_RELATION:
        return f'the word "{TOKEN_RELATION[token]}" (token {token}), which is not an answer'
    return f'token {token}, which is not an answer word'


# ============================================================================== the store

class Notebook:
    """Diary on disk, current view derived from it, symbol table persisted beside it."""

    def __init__(self, path):
        self.path = Path(path)
        self.diary_path = self.path/'diary.jsonl'
        self.symbols_path = self.path/'symbols.json'
        self.meta_path = self.path/'meta.json'
        self.vocab_path = self.path/'VOCABULARY.json'
        self.entries = []
        self.symbols = {}

    # -------------------------------------------------------------- open / load / create
    @classmethod
    def open(cls, path, create=True):
        nb = cls(path)
        if not nb.diary_path.exists():
            if not create:
                raise FileNotFoundError(f'no notebook at {nb.path}')
            nb.create()
        nb.reload()
        return nb

    def create(self):
        self.path.mkdir(parents=True, exist_ok=True)
        if not self.diary_path.exists():
            write_atomic(self.diary_path, '')
        publish_vocabulary(self.vocab_path)
        write_atomic(self.meta_path, json.dumps(dict(
            format=FORMAT_VERSION, created_utc=utcnow(),
            vocabulary_sha256=vocabulary_sha()), indent=1, sort_keys=True) + '\n')
        write_atomic(self.symbols_path, json.dumps(dict(names={}), indent=1, sort_keys=True) + '\n')

    def reload(self):
        """Re-read the diary and rebuild everything derived from it."""
        text = self.diary_path.read_text() if self.diary_path.exists() else ''
        self.entries = [json.loads(line) for line in text.splitlines() if line.strip()]
        for i, entry in enumerate(self.entries):
            if entry['n'] != i:
                raise ValueError(f'diary out of order at line {i}: n={entry["n"]}')
        self.symbols = self.derive_symbols()
        if self.symbols_path.exists():
            cached = json.loads(self.symbols_path.read_text()).get('names', {})
            if cached != self.symbols:
                raise ValueError('symbols.json disagrees with the diary; the diary wins -- '
                                 'delete symbols.json to rebuild it')
        if self.vocab_path.exists():
            if json.loads(self.vocab_path.read_text()) != vocabulary():
                raise ValueError(f'{self.vocab_path} is not this build\'s published vocabulary')
        return self

    def derive_symbols(self):
        """name -> entity token, in order of first appearance anywhere in the diary."""
        names = {}

        def assign(name):
            if name not in names:
                if len(names) >= MAX_NAMES:
                    raise ValueError(f'the notebook already holds {MAX_NAMES} names')
                names[name] = ENTITY_MIN + len(names)

        for entry in self.entries:
            assign(entry['subject'])
            if entry['kind'] == 'fact' and entry['relation'] == 'friend':
                assign(entry['object'])
        return names

    @property
    def names_by_token(self):
        return {t: n for n, t in self.symbols.items()}

    # ------------------------------------------------------------------------- appending
    def _append(self, entry):
        line = json.dumps(entry, sort_keys=True, separators=(',', ':'))
        assert '\n' not in line
        with open(self.diary_path, 'a') as fh:
            fh.write(line + '\n')
            fh.flush()
            os.fsync(fh.fileno())
        self.entries.append(entry)
        self.symbols = self.derive_symbols()
        write_atomic(self.symbols_path,
                     json.dumps(dict(names=self.symbols), indent=1, sort_keys=True) + '\n')
        return entry

    def name_token(self, name, source='ask'):
        """Look a name up, assigning a token (and a diary line) the first time it is used."""
        if name in self.symbols:
            return self.symbols[name]
        if len(self.symbols) >= MAX_NAMES:
            raise ValueError(f'the notebook already holds {MAX_NAMES} names ('
                             f'{", ".join(sorted(self.symbols))}); this operator has no more '
                             f'entity tokens')
        self._append(dict(n=len(self.entries), time=utcnow(), kind='name',
                          raw=name, subject=name, relation=None, object=None,
                          row=None, source=source))
        return self.symbols[name]

    def teach(self, fact, source='teach', raw=None):
        """Append one fact (or correction).  Returns (entry, replaced_entry_or_None)."""
        subject = self.name_token(fact.subject, source=source)
        relation = RELATION_TOKEN[fact.relation]
        if fact.relation == 'friend':
            obj = self.name_token(fact.obj, source=source)
        else:
            obj = VALUE_TOKEN[fact.obj]
        previous = self.view().get((subject, relation))
        entry = dict(n=len(self.entries), time=utcnow(), kind='fact',
                     raw=raw if raw is not None else render_fact(fact),
                     subject=fact.subject, relation=fact.relation, object=fact.obj,
                     row=[WORLD, subject, relation, obj, NEWLINE], source=source)
        self._append(entry)
        return entry, previous

    # ---------------------------------------------------------------- the derived view
    def fact_entries(self, facts=None):
        rows = [e for e in self.entries if e['kind'] == 'fact']
        return rows if facts is None else rows[:facts]

    def view(self, facts=None):
        """Latest fact entry per (subject token, relation token), in first-seen order."""
        view = {}
        for entry in self.fact_entries(facts):
            key = (entry['row'][1], entry['row'][2])
            view[key] = entry              # replaces in place; dicts keep insertion order
        return view

    def rows(self, facts=None):
        return [list(entry['row']) for entry in self.view(facts).values()]

    def truth(self, facts=None):
        """(subject token, relation token) -> object token, straight off the current view."""
        return {k: e['row'][3] for k, e in self.view(facts).items()}

    # ------------------------------------------------------------------------- the wipe
    def wipe(self):
        """Archive the diary (never delete it) and start an empty one."""
        stamp = utcnow().replace(':', '').replace('-', '')
        archive = self.path/'wiped'
        archive.mkdir(parents=True, exist_ok=True)
        moved = []
        for src in (self.diary_path, self.symbols_path):
            if src.exists():
                dst = archive/f'{src.stem}-{stamp}{src.suffix}'
                os.replace(src, dst)
                moved.append(str(dst))
        self.create()
        self.reload()
        return moved


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='microseconds')


def publish_vocabulary(path):
    write_atomic(path, json.dumps(vocabulary(), indent=1, sort_keys=True) + '\n')
    return path


# ======================================================= bridge to the frozen operator

def checkpoint_path(seed):
    for root in CHECKPOINT_ROOTS:
        candidate = root/f'astra_canonical_operator_seed-{seed}/final.pt'
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f'no frozen grow-blind checkpoint for seed {seed}; looked in '
        + ', '.join(str(r) for r in CHECKPOINT_ROOTS))


class Operator:
    """One frozen checkpoint plus the module's own fixed loop.  Read-only, eval-only."""

    def __init__(self, seed, path=None):
        path = Path(path) if path else checkpoint_path(seed)
        if path.name == 'test.pt':
            raise ValueError('test.pt is prohibited')
        self.path, self.seed = path, seed
        self.sha256 = sha_file(path)
        saved = torch.load(path, map_location='cpu', weights_only=False)
        self.architecture = saved['architecture']
        self.model = A.CanonicalOperator(**self.architecture)
        self.model.load_state_dict(saved['state_dict'], strict=True)
        self.model.eval()
        self.parameters = sum(p.numel() for p in self.model.parameters())
        if self.parameters != EXPECTED_PARAMETERS:
            raise ValueError(f'{path}: {self.parameters} parameters, expected '
                             f'{EXPECTED_PARAMETERS}')
        self.updates = saved.get('updates')
        self.saved_seed = saved.get('seed')

    def describe(self):
        return dict(seed=self.seed, path=str(self.path), sha256=self.sha256,
                    parameters=self.parameters, updates=self.updates,
                    saved_seed=self.saved_seed, architecture=self.architecture)


def pack_story(stories, questions, owners):
    """One visit per story; each question sits after every row, so every row is eligible."""
    memories = [(rows if rows else [[0]]) for rows in stories]
    lines = [len(memories[o]) for o in owners]
    return data.pack(memories, [list(q) for q in questions], list(owners), lines)


def question_tokens(subject_token, ops):
    return [QUESTION, subject_token] + [RELATION_TOKEN[op] if isinstance(op, str) else op
                                        for op in ops] + [ANSWER]


@torch.no_grad()
def run_batch(operator, stories, questions, owners):
    """The fixed external loop over a batch.  Returns A.execute's own result dict."""
    return A.execute(operator.model, pack_story(stories, questions, owners))


@torch.no_grad()
def answer_one(operator, rows, subject_token, ops, names_by_token):
    """One question, with the per-step trace and confidence the loop's calls produce."""
    x = pack_story([rows], [question_tokens(subject_token, ops)], [0])
    steps = []

    def observer(inputs, logits):
        probabilities = logits.softmax(-1)[0]
        token = int(logits[0].argmax(-1))
        steps.append(dict(entity=int(inputs.questions[0][1]), operation=int(inputs.questions[0][2]),
                          answer=token, confidence=float(probabilities[token])))

    result = A.execute(operator.model, x, observer=observer)
    for step in steps:
        step['entity_word'] = names_by_token.get(step['entity'], f'entity token {step["entity"]}')
        step['operation_word'] = TOKEN_RELATION.get(step['operation'], str(step['operation']))
        step['answer_word'] = token_phrase(step['answer'], names_by_token)
    return dict(prediction=result['predictions'][0], emitted=result['emitted'][0],
                calls=result['calls'], steps=steps)


def trace_lines(steps):
    out = []
    for i, step in enumerate(steps, 1):
        out.append(f'  lookup {i}: ({step["entity_word"]}, {step["operation_word"]}) '
                   f'-> {step["answer_word"]}   [confidence {step["confidence"]:.3f}]')
    return out


def answer_in_english(notebook, operator, question):
    """Everything a caller needs to print one answer: sentence, trace, confidence."""
    subject = notebook.name_token(question.subject)
    rows = notebook.rows()
    result = answer_one(operator, rows, subject, question.ops, notebook.names_by_token)
    steps = result['steps']
    if result['prediction'] < 0:
        stop = steps[-1]
        sentence = (f'I stopped after {len(steps)} of {len(question.ops)} lookups: step '
                    f'{len(steps)} produced {stop["answer_word"]}, which is not a person, '
                    f'so there was nobody to look up next.')
    else:
        sentence = render_answer(question, token_phrase(result['prediction'],
                                                        notebook.names_by_token))
    supported = supporting_rows(notebook, subject, question.ops)
    return dict(sentence=sentence, trace=trace_lines(steps), result=result,
                rows=len(rows), notebook_supports=supported)


def walk(truth, subject_token, ops):
    """Follow a chain through a current view by the supplied rule. None if a row is missing."""
    entity = subject_token
    for op in ops:
        key = (entity, RELATION_TOKEN[op] if isinstance(op, str) else op)
        if key not in truth:
            return None
        entity = truth[key]
    return entity


def supporting_rows(notebook, subject_token, ops):
    """What the CURRENT VIEW itself implies, by the supplied correction rule -- the
    evaluator's own reading of the store, not the model's answer."""
    truth = notebook.truth()
    entity, path = subject_token, []
    for op in ops:
        key = (entity, RELATION_TOKEN[op] if isinstance(op, str) else op)
        if key not in truth:
            return dict(answerable=False, path=path, missing=key)
        entity = truth[key]
        path.append(entity)
    return dict(answerable=True, path=path, answer=path[-1] if path else None)


# ================================================================================= CLI

def cmd_teach(args):
    notebook = Notebook.open(args.notebook)
    try:
        item = parse(args.sentence)
    except ParseError as exc:
        print(exc)
        return 2
    if item.kind != 'fact':
        print('That is a question, not something to teach. Use `ask` for questions.')
        return 2
    entry, previous = notebook.teach(item, source='teach', raw=normalise(args.sentence))
    if previous is not None:
        print(f'Noted, and it replaces the old line: {previous["raw"]}')
    else:
        print('Noted.')
    print(f'  diary line {entry["n"]}  row {entry["row"]}')
    print(f'  the notebook now holds {len(notebook.view())} facts about '
          f'{len(notebook.symbols)} people')
    return 0


def cmd_ask(args):
    notebook = Notebook.open(args.notebook)
    try:
        item = parse(args.question)
    except ParseError as exc:
        print(exc)
        return 2
    if item.kind != 'question':
        print('That is a statement, not a question. Use `teach` to teach it.')
        return 2
    operator = Operator(args.seed, args.checkpoint)
    out = answer_in_english(notebook, operator, item)
    print(out['sentence'])
    print(f'  (read from {out["rows"]} rows in the notebook, operator seed {operator.seed})')
    for line in out['trace']:
        print(line)
    support = out['notebook_supports']
    if not support['answerable']:
        subject, relation = support['missing']
        who = notebook.names_by_token.get(subject, f'entity token {subject}')
        print(f'  NOTE: the notebook does not contain "{who}\'s '
              f'{TOKEN_RELATION.get(relation, relation)}", so this answer is made up. '
              f'This model has no way to say "I don\'t know" (roadmap M2).')
    return 0


HELP = """\
Type a fact, a correction or a question. Try these six lines in order:
  Mira's friend is Oren.
  Oren's gift is a drum.
  Tal's gift is a kite.
  What is Mira's friend's gift?
  Actually, Mira's friend is Tal.
  What is Mira's friend's gift?
Commands:  :view   the current view (what the operator reads)
           :diary  the append-only history
           :names  the symbol table
           :help   this message
           :quit   leave
"""


def cmd_chat(args):
    notebook = Notebook.open(args.notebook)
    operator = Operator(args.seed, args.checkpoint)
    print(f'Notebook: {notebook.path}')
    print(f'Operator: frozen grow-blind seed {operator.seed}, {operator.parameters} parameters, '
          f'sha256 {operator.sha256[:12]}')
    print(f'It knows {len(notebook.view())} facts about {len(notebook.symbols)} people.\n')
    print(HELP)
    while True:
        try:
            line = input('> ').strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line in (':quit', ':q', ':exit'):
            return 0
        if line == ':help':
            print(HELP)
            continue
        if line == ':view':
            for entry in notebook.view().values():
                fact = Fact(entry['subject'], entry['relation'], entry['object'])
                print(f'  {entry["row"]}   {render_fact(fact)}')
            print(f'  {len(notebook.view())} rows')
            continue
        if line == ':diary':
            for entry in notebook.entries:
                print(f'  {entry["n"]:4d}  {entry["time"]}  {entry["kind"]:5s}  {entry["raw"]}')
            continue
        if line == ':names':
            for name, token in sorted(notebook.symbols.items(), key=lambda kv: kv[1]):
                print(f'  {name:12s} -> entity token {token}')
            continue
        try:
            item = parse(line)
        except ParseError as exc:
            print(exc)
            continue
        if item.kind == 'fact':
            try:
                entry, previous = notebook.teach(item, source='chat', raw=normalise(line))
            except ValueError as exc:
                print(f'  {exc}')
                continue
            if previous is not None:
                print(f'Noted; that replaces "{previous["raw"]}" in the current view.')
            else:
                print('Noted.')
            print(f'  row {entry["row"]}; the notebook now holds {len(notebook.view())} facts.')
            continue
        try:
            out = answer_in_english(notebook, operator, item)
        except ValueError as exc:
            print(f'  {exc}')
            continue
        print(out['sentence'])
        for trace in out['trace']:
            print(trace)
        support = out['notebook_supports']
        if not support['answerable']:
            subject, relation = support['missing']
            who = notebook.names_by_token.get(subject, f'entity token {subject}')
            print(f'  NOTE: nothing in the notebook says what {who}\'s '
                  f'{TOKEN_RELATION.get(relation, relation)} is, so that answer is made up.')


def cmd_wipe(args):
    notebook = Notebook.open(args.notebook)
    facts = len(notebook.view())
    if not args.yes:
        reply = input(f'Archive the diary ({len(notebook.entries)} lines, {facts} facts) and '
                      f'start empty? [y/N] ').strip().lower()
        if reply not in ('y', 'yes'):
            print('Left alone.')
            return 1
    moved = notebook.wipe()
    print('Wiped. The old diary was archived, not deleted:')
    for path in moved:
        print(f'  {path}')
    print(f'  the notebook now holds {len(notebook.view())} facts')
    return 0


def cmd_vocab(args):
    if args.write:
        path = publish_vocabulary(Path(args.write))
        print(f'{path}  sha256 {sha_file(path)}')
    print(json.dumps(vocabulary(), indent=1, sort_keys=True))
    return 0


def cmd_answer_batch(args):
    """Internal. Answer a question file from a notebook ON DISK, in this fresh process."""
    notebook = Notebook.open(args.notebook, create=False)
    operator = Operator(args.seed, args.checkpoint)
    spec = json.loads(Path(args.questions).read_text())
    rows = notebook.rows(spec.get('facts'))
    x = pack_story([rows]*len(spec['questions']), spec['questions'],
                   list(range(len(spec['questions']))))
    with torch.no_grad():
        logits = operator.model(x) if spec.get('logits') else None
        result = A.execute(operator.model, x)
    out = dict(predictions=result['predictions'], emitted=result['emitted'],
               rows=rows, checkpoint_sha256=operator.sha256)
    if logits is not None:
        out['logits_sha256'] = sha_bytes(logits.detach().contiguous().numpy().tobytes())
    Path(args.out).write_text(json.dumps(out, sort_keys=True))
    return 0


# ================================================================================ eval

def session_world(index):
    """One scripted teaching session: sixteen people, a friend each, three attributes each."""
    rng = random.Random(f'{NAMESPACE}:session:{index}')
    names = list(DEFAULT_NAMES)
    rng.shuffle(names)
    friend = {}
    for i, name in enumerate(names):
        friend[name] = rng.choice([n for n in names if n != name])
    attributes = {(name, rel): rng.choice(VALUE_WORDS)
                  for name in names for rel in ATTRIBUTE_WORDS}
    facts = [Fact(name, 'friend', friend[name]) for name in names]
    facts += [Fact(name, rel, attributes[(name, rel)]) for name in names for rel in ATTRIBUTE_WORDS]
    rng.shuffle(facts)
    # Teaching order fix-up, declared: move one LINK fact to position 0 and one attribute of
    # that link's target to position 1, so a two-hop question exists from notebook size 2 on.
    link_ix = next(i for i, f in enumerate(facts) if f.relation == 'friend')
    head = facts.pop(link_ix)
    attr_ix = next(i for i, f in enumerate(facts)
                   if f.subject == head.obj and f.relation != 'friend')
    second = facts.pop(attr_ix)
    facts = [head, second] + facts
    assert len(facts) == 64
    return dict(index=index, names=names, friend=friend, attributes=attributes, facts=facts,
                rng_stream=f'{NAMESPACE}:session:{index}')


def build_session_notebook(index, root):
    """Teach the 64 facts one at a time, then append the two scripted corrections."""
    world = session_world(index)
    path = Path(root)/f'session-{index:02d}'
    if path.exists():
        for child in sorted(path.rglob('*'), reverse=True):
            child.unlink() if child.is_file() else child.rmdir()
        path.rmdir()
    notebook = Notebook.open(path)
    for fact in world['facts']:
        notebook.teach(fact, source='eval')
    assert len(notebook.view()) == 64, len(notebook.view())

    rng = random.Random(f'{NAMESPACE}:correction:{index}')
    names = world['names']
    # probe people: never corrected, so "untouched facts unchanged" has a clean meaning
    corrected_attr_person = rng.choice(names)
    corrected_relation = rng.choice(list(ATTRIBUTE_WORDS))
    corrected_link_person = rng.choice([n for n in names if n != corrected_attr_person])
    old_value = world['attributes'][(corrected_attr_person, corrected_relation)]
    new_value = rng.choice([v for v in VALUE_WORDS if v != old_value])
    old_friend = world['friend'][corrected_link_person]
    new_friend = rng.choice([n for n in names
                             if n not in (corrected_link_person, old_friend)])
    touched = {corrected_attr_person, corrected_link_person}
    probe_keys = [(n, r) for n in names for r in ATTRIBUTE_WORDS + ('friend',)
                  if n not in touched and not (n == old_friend or n == new_friend)]
    rng.shuffle(probe_keys)
    probes = probe_keys[:PROBE_COUNT]
    assert len(probes) == PROBE_COUNT
    corrections = [Fact(corrected_attr_person, corrected_relation, new_value, correction=True),
                   Fact(corrected_link_person, 'friend', new_friend, correction=True)]
    for fact in corrections:
        notebook.teach(fact, source='eval')
    assert len(notebook.view()) == 64, 'a correction must replace, never add'
    return dict(world=world, path=path, notebook=notebook, probes=probes,
                corrected_attr=dict(person=corrected_attr_person, relation=corrected_relation,
                                    old=old_value, new=new_value),
                corrected_link=dict(person=corrected_link_person, old=old_friend,
                                    new=new_friend))


def sample_questions(session, notebook, size, kind):
    """Answerable questions at this notebook size, from the current view at that size."""
    rng = random.Random(f'{NAMESPACE}:questions:{session["world"]["index"]}:{size}:{kind}')
    truth = notebook.truth(size)
    names_by_token = notebook.names_by_token
    items = []
    if kind == 'one_hop':
        for (subject, relation), obj in truth.items():
            items.append(dict(subject=subject, ops=[relation], gold=obj,
                              subject_name=names_by_token[subject],
                              relation=TOKEN_RELATION[relation]))
    else:
        for (subject, relation), middle in truth.items():
            if relation != LINK:
                continue
            for second in ATTRIBUTE_RELATIONS + (LINK,):
                if (middle, second) in truth:
                    items.append(dict(subject=subject, ops=[relation, second],
                                      gold=truth[(middle, second)], middle=middle,
                                      subject_name=names_by_token[subject],
                                      relation=TOKEN_RELATION[second]))
    items.sort(key=lambda d: (d['subject'], tuple(d['ops'])))
    if len(items) > QUESTIONS_PER_CELL:
        items = rng.sample(items, QUESTIONS_PER_CELL)
    return items


def score_questions(operator, stories, questions, owners, golds):
    if not questions:
        return dict(n=0, correct=0, predictions=[])
    result = run_batch(operator, stories, questions, owners)
    correct = sum(int(p == g) for p, g in zip(result['predictions'], golds))
    return dict(n=len(golds), correct=correct, predictions=result['predictions'])


def cmd_eval(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    prereg = out/'PREREG-MARKS.md'
    if not prereg.exists():
        raise SystemExit(f'{prereg} must be written BEFORE eval runs. Run `prereg` first.')
    sessions_root = out/'eval-notebooks'
    sessions_root.mkdir(parents=True, exist_ok=True)
    publish_vocabulary(out/'VOCABULARY.json')

    print(f'building {args.sessions} scripted teaching sessions ...', flush=True)
    sessions = [build_session_notebook(i, sessions_root) for i in range(args.sessions)]
    operators = [Operator(seed, None) for seed in args.seeds]
    for op in operators:
        print(f'  operator seed {op.seed}: {op.parameters} parameters, sha256 {op.sha256}',
              flush=True)

    results = dict(
        namespace=NAMESPACE, sessions=args.sessions, sizes=list(EVAL_SIZES),
        questions_per_cell=QUESTIONS_PER_CELL, probes=PROBE_COUNT,
        reload_sessions=RELOAD_SESSIONS, marks=dict(
            one_hop=MARK_ONE_HOP, two_hop=MARK_TWO_HOP, new_answer=MARK_NEW_ANSWER,
            old_answer=MARK_OLD_ANSWER),
        vocabulary_sha256=vocabulary_sha(), generated_utc=utcnow(),
        operators=[op.describe() for op in operators], seeds={})

    # ------------------------------------------------------- growth: sizes 1, 2, 4 ... 64
    cells = {}
    for size in EVAL_SIZES:
        for kind in ('one_hop', 'two_hop'):
            stories, questions, owners, golds = [], [], [], []
            for owner, session in enumerate(sessions):
                nb = session['notebook']
                stories.append(nb.rows(size))
                for item in sample_questions(session, nb, size, kind):
                    questions.append(question_tokens(item['subject'], item['ops']))
                    owners.append(owner)
                    golds.append(item['gold'])
            if questions:                        # the evaluator's own check of every gold
                packed = pack_story(stories, questions, owners)
                assert [p[-1]['target'] for p in A.truth_paths(packed)] == golds, \
                    f'gold not derivable from the current view at size {size} ({kind})'
            cells[(size, kind)] = (stories, questions, owners, golds)

    # ------------------------------------------------------------- corrections + probes
    probe_stories_before, probe_q, probe_owner = [], [], []
    probe_stories_after = []
    corr_q, corr_owner, corr_new, corr_old, corr_tag = [], [], [], [], []
    for owner, session in enumerate(sessions):
        nb = session['notebook']
        before, after = nb.rows(64), nb.rows(66)
        probe_stories_before.append(before)
        probe_stories_after.append(after)
        truth_before = nb.truth(64)
        for name, relation in session['probes']:
            subject = nb.symbols[name]
            token = RELATION_TOKEN[relation]
            probe_q.append(question_tokens(subject, [token]))
            probe_owner.append(owner)
            assert (subject, token) in truth_before
        ca, cl = session['corrected_attr'], session['corrected_link']
        truth_after = nb.truth(66)
        person, linked = nb.symbols[ca['person']], nb.symbols[cl['person']]
        asked = [(person, [RELATION_TOKEN[ca['relation']]], 'attribute one-hop'),
                 (linked, [LINK], 'link one-hop')]
        asked += [(linked, [LINK, RELATION_TOKEN[r]], 'two-hop through the corrected link')
                  for r in ATTRIBUTE_WORDS]
        for subject, ops, tag in asked:
            new = walk(truth_after, subject, ops)
            old = walk(truth_before, subject, ops)
            assert new is not None and old is not None
            corr_q.append(question_tokens(subject, ops))
            corr_owner.append(owner)
            corr_new.append(new)
            corr_old.append(old)
            corr_tag.append(tag)

    # ------------------------------------------------- untaught and wipe (descriptive)
    untaught_q, untaught_owner, untaught_tag = [], [], []
    for owner, session in enumerate(sessions):
        nb = session['notebook']
        truth16 = nb.truth(16)
        names_by_token = nb.names_by_token
        present = {s for s, _ in truth16}
        rng = random.Random(f'{NAMESPACE}:untaught:{session["world"]["index"]}')
        gaps = [(s, r) for s in sorted(present) for r in ATTRIBUTE_RELATIONS + (LINK,)
                if (s, r) not in truth16]
        for subject, relation in rng.sample(gaps, min(4, len(gaps))):
            untaught_q.append(question_tokens(subject, [relation]))
            untaught_owner.append(owner)
            untaught_tag.append('known person, relation never taught')
        strangers = [t for t in names_by_token if t not in present]
        for subject in rng.sample(strangers, min(4, len(strangers))):
            for relation in (LINK, ATTRIBUTE_RELATIONS[0]):
                untaught_q.append(question_tokens(subject, [relation]))
                untaught_owner.append(owner)
                untaught_tag.append('person never mentioned in the notebook')

    wipe_q = ([question_tokens(ENTITY_MIN, [LINK])]
              + [question_tokens(ENTITY_MIN, [r]) for r in ATTRIBUTE_RELATIONS]
              + [question_tokens(ENTITY_MIN + 1, [LINK, ATTRIBUTE_RELATIONS[0]])]
              + [question_tokens(ENTITY_MIN + 2, [r]) for r in ATTRIBUTE_RELATIONS])

    # ----------------------------------------------------------------- score every seed
    for operator in operators:
        print(f'scoring operator seed {operator.seed} ...', flush=True)
        seed_result = dict(checkpoint=operator.describe(), sizes={}, correction={},
                           probes={}, reload={}, untaught={}, wipe={})
        for size in EVAL_SIZES:
            entry = {}
            for kind in ('one_hop', 'two_hop'):
                stories, questions, owners, golds = cells[(size, kind)]
                entry[kind] = score_questions(operator, stories, questions, owners, golds)
                entry[kind].pop('predictions')
            seed_result['sizes'][str(size)] = entry

        before = run_batch(operator, probe_stories_before, probe_q, probe_owner)['predictions']
        after = run_batch(operator, probe_stories_after, probe_q, probe_owner)['predictions']
        seed_result['probes'] = dict(n=len(before),
                                     unchanged=sum(int(a == b) for a, b in zip(before, after)))

        corr = run_batch(operator, probe_stories_after, corr_q, corr_owner)['predictions']
        by_tag, total = {}, dict(n=0, new=0, old=0, other=0, n_old_defined=0)
        for tag, pred, new, old in zip(corr_tag, corr, corr_new, corr_old):
            slot = by_tag.setdefault(tag, dict(n=0, new=0, old=0, other=0, n_old_defined=0))
            for target in (slot, total):
                target['n'] += 1
                if pred == new:
                    target['new'] += 1
                elif old != new and pred == old:
                    target['old'] += 1
                else:
                    target['other'] += 1
                target['n_old_defined'] += int(old != new)
        seed_result['correction'] = dict(total=total, by_question=by_tag)

        # kill-and-reload: a FRESH PROCESS re-instantiates the notebook from disk
        reload_checks = []
        for session in sessions[:RELOAD_SESSIONS]:
            nb = session['notebook']
            questions = [question_tokens(nb.symbols[name], [RELATION_TOKEN[rel]])
                         for name, rel in session['probes']]
            spec = dict(questions=questions, facts=None, logits=True)
            qfile = out/'reload'/f'seed-{operator.seed}-s{session["world"]["index"]:02d}.json'
            rfile = qfile.with_suffix('.result.json')
            qfile.parent.mkdir(parents=True, exist_ok=True)
            write_atomic(qfile, json.dumps(spec))
            x = pack_story([nb.rows()]*len(questions), questions, list(range(len(questions))))
            with torch.no_grad():
                here_logits = operator.model(x)
            here = dict(predictions=A.execute(operator.model, x)['predictions'],
                        logits_sha256=sha_bytes(here_logits.detach().contiguous()
                                                .numpy().tobytes()))
            subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), 'answer-batch',
                            '--notebook', str(nb.path), '--seed', str(operator.seed),
                            '--questions', str(qfile), '--out', str(rfile)],
                           check=True, env=dict(os.environ, OMP_NUM_THREADS='1',
                                                VECLIB_MAXIMUM_THREADS='1'))
            there = json.loads(rfile.read_text())
            reload_checks.append(dict(
                session=session['world']['index'],
                rows_identical=there['rows'] == nb.rows(),
                predictions_identical=there['predictions'] == here['predictions'],
                logits_identical=there['logits_sha256'] == here['logits_sha256']))
        seed_result['reload'] = dict(
            sessions=len(reload_checks),
            all_identical=sum(int(c['rows_identical'] and c['predictions_identical']
                                  and c['logits_identical']) for c in reload_checks),
            checks=reload_checks)

        # descriptive: untaught questions
        untaught_stories = [session['notebook'].rows(16) for session in sessions]
        packed = pack_story(untaught_stories, untaught_q, untaught_owner)
        with torch.no_grad():
            logits = operator.model(packed)
        probabilities = logits.softmax(-1)
        confidence = probabilities.max(-1).values.tolist()
        predictions = logits.argmax(-1).tolist()
        buckets = {}
        for tag, pred, conf in zip(untaught_tag, predictions, confidence):
            slot = buckets.setdefault(tag, dict(n=0, confident=0, confidence_sum=0.,
                                                value_token=0, entity_token=0, other_token=0))
            slot['n'] += 1
            slot['confident'] += int(conf >= .9)
            slot['confidence_sum'] += conf
            slot['value_token' if pred in TOKEN_VALUE else
                 ('entity_token' if ENTITY_MIN <= pred < ENTITY_MAX else 'other_token')] += 1
        for slot in buckets.values():
            slot['mean_confidence'] = slot.pop('confidence_sum')/slot['n']
        seed_result['untaught'] = dict(by_tag=buckets, n=len(untaught_q),
                                       note='none of these are answerable from the notebook; '
                                            'there is no UNKNOWN answer in this operator')

        # descriptive: the wipe test
        empty = Notebook.open(out/'wipe-probe-notebook')
        empty.wipe()
        packed = pack_story([empty.rows()]*len(wipe_q), wipe_q, list(range(len(wipe_q))))
        with torch.no_grad():
            logits = operator.model(packed)
        probabilities = logits.softmax(-1)
        seed_result['wipe'] = dict(
            rows=len(empty.rows()), n=len(wipe_q),
            predictions=logits.argmax(-1).tolist(),
            confidence=[round(float(c), 4) for c in probabilities.max(-1).values.tolist()],
            note='an empty notebook is presented as one all-padding row; the operator still '
                 'emits a token, which is the honest baseline failure')

        results['seeds'][str(operator.seed)] = seed_result

    verdicts = {seed: verdict_for(r) for seed, r in results['seeds'].items()}
    results['verdicts'] = verdicts
    write_atomic(out/'results.json', json.dumps(results, indent=1, sort_keys=True) + '\n')
    write_atomic(out/'RESULTS.md', results_markdown(results))
    print(f'\nwrote {out/"results.json"} and {out/"RESULTS.md"}')
    print(report_text(results))
    return 0


def rate(correct, n):
    return None if not n else correct/n


def verdict_for(seed_result):
    marks = {}
    for size, cell in seed_result['sizes'].items():
        for kind, mark in (('one_hop', MARK_ONE_HOP), ('two_hop', MARK_TWO_HOP)):
            r = rate(cell[kind]['correct'], cell[kind]['n'])
            marks[f'{kind}@{size}'] = ('n/a (no answerable question at this size)' if r is None
                                       else ('PASS' if r >= mark else 'FAIL'))
    total = seed_result['correction']['total']
    marks['correction_new_answer'] = 'PASS' if rate(total['new'], total['n']) >= MARK_NEW_ANSWER \
        else 'FAIL'
    old = rate(total['old'], total['n_old_defined'])
    marks['correction_old_answer'] = ('n/a (no question where the old answer differs)'
                                      if old is None else
                                      'PASS' if old <= MARK_OLD_ANSWER else 'FAIL')
    probes = seed_result['probes']
    marks['untouched_unchanged'] = 'PASS' if probes['unchanged'] == probes['n'] else 'FAIL'
    reload = seed_result['reload']
    marks['kill_and_reload'] = 'PASS' if reload['all_identical'] == reload['sessions'] else 'FAIL'
    marks['ALL'] = 'PASS' if all(v in ('PASS',) or v.startswith('n/a') for v in marks.values()) \
        else 'FAIL'
    return marks


def report_text(results):
    lines = []
    for seed, r in sorted(results['seeds'].items()):
        lines.append(f'\noperator seed {seed}  ({r["checkpoint"]["sha256"][:12]})')
        lines.append('  size |        one-hop |        two-hop')
        for size in results['sizes']:
            cell = r['sizes'][str(size)]
            fields = []
            for kind in ('one_hop', 'two_hop'):
                c = cell[kind]
                fields.append('      -- (n=0)' if not c['n'] else
                              f'{c["correct"]:5d}/{c["n"]:<5d} {100*c["correct"]/c["n"]:5.1f}%')
            lines.append(f'  {size:4d} | {fields[0]} | {fields[1]}')
        total = r['correction']['total']
        lines.append(f'  correction: new {total["new"]}/{total["n"]} '
                     f'({100*total["new"]/total["n"]:.1f}%)  old {total["old"]}'
                     f'/{total["n_old_defined"]} '
                     f'({100*total["old"]/max(1, total["n_old_defined"]):.1f}%)  '
                     f'other {total["other"]}')
        lines.append(f'  untouched probes unchanged: {r["probes"]["unchanged"]}/{r["probes"]["n"]}')
        lines.append(f'  kill-and-reload identical:  {r["reload"]["all_identical"]}'
                     f'/{r["reload"]["sessions"]} sessions')
        marks = results['verdicts'][seed]
        failed = [k for k, v in marks.items() if v == 'FAIL' and k != 'ALL']
        lines.append(f'  VERDICT {marks["ALL"]}' + (f'   failed: {", ".join(failed)}' if failed
                                                    else ''))
    return '\n'.join(lines)


def results_markdown(results):
    L = [f'# M0 -- Notebook demo v0: results', '',
         f'Generated {results["generated_utc"]}. Evaluation only; nothing was trained.',
         f'RNG namespace `{results["namespace"]}`; {results["sessions"]} scripted teaching '
         f'sessions, facts taught one at a time; every seed reported separately, never '
         f'averaged.', '',
         '## Checkpoints (frozen, read-only)', '',
         '| operator seed | parameters | updates | sha256 | path |',
         '|---|---|---|---|---|']
    for op in results['operators']:
        L.append(f'| {op["seed"]} | {op["parameters"]} | {op["updates"]} | `{op["sha256"]}` | '
                 f'`{op["path"]}` |')
    L += ['', '## Growth: accuracy at each notebook size (raw counts)', '']
    for seed, r in sorted(results['seeds'].items()):
        L += [f'### operator seed {seed}', '',
              '| notebook rows | one-hop correct/n | one-hop % | two-hop correct/n | two-hop % |',
              '|---|---|---|---|---|']
        for size in results['sizes']:
            cell = r['sizes'][str(size)]
            fields = []
            for kind in ('one_hop', 'two_hop'):
                c = cell[kind]
                fields += ([f'0/0', 'n/a'] if not c['n'] else
                           [f'{c["correct"]}/{c["n"]}', f'{100*c["correct"]/c["n"]:.2f}%'])
            L.append(f'| {size} | {fields[0]} | {fields[1]} | {fields[2]} | {fields[3]} |')
        total = r['correction']['total']
        L += ['', '**Corrections** (two per session: one attribute, one friend link; asked '
              'after the correction is appended). The old-answer rate is over the questions '
              'whose old answer differs from the new one.', '',
              '| question | n | new answer | old answer | neither |', '|---|---|---|---|---|']
        rows = sorted(r['correction']['by_question'].items()) + [('**all**', total)]
        for tag, slot in rows:
            L.append(f'| {tag} | {slot["n"]} | {slot["new"]}/{slot["n"]} '
                     f'({100*slot["new"]/slot["n"]:.2f}%) | {slot["old"]}'
                     f'/{slot["n_old_defined"]} '
                     f'({100*slot["old"]/max(1, slot["n_old_defined"]):.2f}%) '
                     f'| {slot["other"]} |')
        L += ['', f'**Untouched facts unchanged**: {r["probes"]["unchanged"]}/'
              f'{r["probes"]["n"]} probe answers identical before and after the corrections.',
              '', f'**Kill-and-reload**: {r["reload"]["all_identical"]}/'
              f'{r["reload"]["sessions"]} sessions re-instantiated from disk in a fresh '
              f'process gave byte-identical rows, predictions and answer logits.', '',
              '**Descriptive, no mark -- untaught questions** (notebook of 16 rows; none of '
              'these is answerable from the notebook):', '',
              '| question kind | n | mean confidence | confidence >= 0.9 | answered with a '
              'value token | with an entity token | with neither |', '|---|---|---|---|---|---|---|']
        for tag, slot in sorted(r['untaught']['by_tag'].items()):
            L.append(f'| {tag} | {slot["n"]} | {slot["mean_confidence"]:.3f} | '
                     f'{slot["confident"]} | {slot["value_token"]} | {slot["entity_token"]} | '
                     f'{slot["other_token"]} |')
        wipe = r['wipe']
        L += ['', f'**Descriptive, no mark -- wipe test** (empty notebook, {wipe["n"]} '
              f'questions): predicted tokens {wipe["predictions"]}, confidence '
              f'{wipe["confidence"]}. {wipe["note"]}', '',
              '**Marks**', '', '| mark | verdict |', '|---|---|']
        for key, value in results['verdicts'][seed].items():
            L.append(f'| {key} | {value} |')
        L.append('')
    return '\n'.join(L) + '\n'


PREREG_TEXT = """\
# M0 -- Notebook demo v0: marks, registered BEFORE the run

Written before `eval` was run; `eval` refuses to start unless this file exists.
Evaluation only. No training of anything. Three FROZEN grow-blind operator checkpoints
(seeds 0, 1, 2), each 79,316 parameters, opened read-only with their sha256 recorded.
The fixed external loop is `astra_canonical_operator.execute`, which reads the hop
sequence off the question; there is no learned dispatcher anywhere in this run.

## Design

* {sessions} scripted teaching sessions, RNG namespace `{namespace}` (new: not any existing
  panel's). Each session is a fresh notebook directory on disk. The same {sessions}
  notebooks are read by all three operator seeds, so seeds are paired.
* Each session teaches 64 facts ONE AT A TIME -- 16 people x (one friend link + three
  attributes) -- which is every fact this token vocabulary can hold. Teaching order is a
  seeded shuffle with one declared fix-up: one friend fact is moved to position 0 and one
  attribute of that friend's target to position 1, so that a two-hop question exists from
  notebook size 2 onwards.
* At notebook sizes {sizes} the current view at that size is the story. Up to
  {per_cell} one-hop and {per_cell} two-hop questions per session per size, sampled from the
  questions the current view actually answers. Every gold answer is re-derived by
  `astra_canonical_operator.truth_paths` from the packed story before scoring.
* Two corrections per session are appended after the 64th fact: one attribute value and one
  friend link. Five questions per session are then asked: the corrected attribute (one hop),
  the corrected link (one hop), and the three two-hop questions that run through the
  corrected link.
* {probes} one-hop probe questions per session about people neither correction touches are
  asked before and after the corrections.
* Kill-and-reload: for the first {reload} sessions of each seed, a FRESH PROCESS opens the
  notebook directory from disk and answers the same probe questions.

## Marks (per operator seed, never averaged)

| # | mark | threshold |
|---|---|---|
| 1 | one-hop accuracy at every notebook size | >= 95% |
| 2 | two-hop accuracy at every notebook size where a two-hop question exists | >= 95% |
| 3 | after a correction, the new answer | >= 95% |
| 4 | after a correction, the old answer | <= 2% |
| 5 | untouched facts' answers unchanged by a correction | 100% identical |
| 6 | kill-and-reload: rows, predictions and answer logits byte-identical | 100% |

Declared in advance:

* At notebook size 1 no two-hop question is answerable, so mark 2 is reported as
  `n/a (n=0)` at size 1 and is not scored there.
* Marks 3 and 4 are scored over all five correction questions per session pooled, and are
  also reported per question kind.
* Every "new" and "old" answer is computed by walking the current view AFTER and BEFORE the
  corrections, so a correction that also changes a two-hop answer is scored against the
  value the store actually implies. Where the old and new answers coincide (the two-hop case
  can draw the same value token twice), "old" is not distinguishable from "new", so mark 4's
  denominator is the number of questions whose old answer differs from the new one; that
  denominator is reported.

## Descriptive only, no mark

* Untaught questions at a 16-row notebook, in two kinds (a person the notebook knows but
  with that relation never taught; a person the notebook has never been told about): what
  it answers and how confident it is. EXPECTED: confident wrong answers. This is recorded
  as the baseline failure, not as a result.
* Wipe test: an empty notebook, eight questions -- what it answers with nothing to read.

## Declared handling of the named risk

Notebooks of 1-15 rows were never trained on: the grow-blind curriculum's floor is
`blind_lines = 16` kept fact rows. Nothing is padded and no filler fact is invented. A
current-view row is packed as `[WORLD, entity, relation, object, NEWLINE]` -- the
generator's own fact-row shape with zero trailing filler tokens, the low end of its
`randint(0, 2)` filler draw -- and `premonition_memnn.pack` sizes the memory tensor from
the rows it is given, so a one-row notebook is presented as a one-row story. An EMPTY
notebook is presented as a single all-padding row, which `pack` marks ineligible.

## What a pass would and would not show

Would show: a learned reader can sit behind a persistent, correctable notebook, and its
chained answers are caused by the notebook. Would NOT show: any learning of language,
"I don't know", names beyond 16, more than 64 facts, or learned control. The loop, the
reader, the printer and the correction rule are all supplied code.
"""


def cmd_prereg(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out/'PREREG-MARKS.md'
    if path.exists() and not args.force:
        print(f'{path} already exists (sha256 {sha_file(path)}); not rewriting.')
        return 0
    write_atomic(path, PREREG_TEXT.format(
        sessions=EVAL_SESSIONS, namespace=NAMESPACE, sizes=', '.join(map(str, EVAL_SIZES)),
        per_cell=QUESTIONS_PER_CELL, probes=PROBE_COUNT, reload=RELOAD_SESSIONS))
    print(f'{path}  sha256 {sha_file(path)}')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='command', required=True)

    def with_notebook(parser):
        parser.add_argument('--notebook', default=str(DEFAULT_NOTEBOOK),
                            help=f'notebook directory (default {DEFAULT_NOTEBOOK})')

    def with_operator(parser):
        parser.add_argument('--seed', type=int, default=0, choices=(0, 1, 2),
                            help='frozen grow-blind operator seed (default 0)')
        parser.add_argument('--checkpoint', default=None, help='override the checkpoint path')

    p = sub.add_parser('teach', help='append a fact or a correction')
    p.add_argument('sentence')
    with_notebook(p)
    p.set_defaults(func=cmd_teach)

    p = sub.add_parser('ask', help='answer a question from the notebook')
    p.add_argument('question')
    with_notebook(p)
    with_operator(p)
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser('chat', help='interactive teach / correct / ask')
    with_notebook(p)
    with_operator(p)
    p.set_defaults(func=cmd_chat)

    p = sub.add_parser('wipe', help='archive the diary and start empty')
    with_notebook(p)
    p.add_argument('--yes', action='store_true')
    p.set_defaults(func=cmd_wipe)

    p = sub.add_parser('vocab', help='print (and optionally publish) the fixed vocabulary')
    p.add_argument('--write', default=None)
    p.set_defaults(func=cmd_vocab)

    p = sub.add_parser('prereg', help='write PREREG-MARKS.md (must precede eval)')
    p.add_argument('--out', default=str(OUT))
    p.add_argument('--force', action='store_true')
    p.set_defaults(func=cmd_prereg)

    p = sub.add_parser('eval', help='run the registered M0 marks, per operator seed')
    p.add_argument('--out', default=str(OUT))
    p.add_argument('--sessions', type=int, default=EVAL_SESSIONS)
    p.add_argument('--seeds', type=lambda s: tuple(int(x) for x in s.split(',')),
                   default=EVAL_SEEDS)
    p.set_defaults(func=cmd_eval)

    p = sub.add_parser('answer-batch', help=argparse.SUPPRESS)
    p.add_argument('--notebook', required=True)
    p.add_argument('--questions', required=True)
    p.add_argument('--out', required=True)
    with_operator(p)
    p.set_defaults(func=cmd_answer_batch)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
