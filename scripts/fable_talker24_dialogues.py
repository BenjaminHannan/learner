"""Build task 2 -- the DIALOGUE GENERATOR and the SEALED WORDING SPLITS.

`design/v3/24-talker-from-scratch-fable-design.md` sections 3.2, 4.1-4.4, 5 and 8, with
Ben's decisions in `design/v3/24b-talker-decisions-ben.md`.  ADDITIVE: this file and its
two companions (`fable_talker24_dialogues_frames.py`, `fable_talker24_parser.py`) are new;
nothing registered is edited.  Nothing here trains, downloads or spends anything.

WHAT THIS PRODUCES
  Practice conversations in which facts are taught, corrected and asked about, mixed with
  small talk, where EVERY turn carries its exact gold thought (act, subject code slot,
  relation path, object slot, flags) by construction -- because we generated it.  The
  notebook is simulated with M0's own rule (latest row per (subject, relation) wins) so the
  right reply, the right unknown-reason and the old value after a correction are all known.

  The output format is specified, before any of this existed, in
  `artifacts/fable-talker24-20260920/INTERFACE-dialogues.md`.  That file is the contract
  with the model/trainer builder; if the two disagree, that file is wrong and gets fixed.

THE THREE PIECES, AND WHY THEY ARE SEPARATE FILES
  `_frames`   the wording grammar and the sealed L1/L2 split -- a data table only.
  `_parser`   the rule-based reference parser.  It imports NOTHING from here or from the
              frame table; it reads characters.  `selftest` measures how often the label
              this file writes and the label that file reads are identical.
  this file   symbols, notebook simulator, world sampler, renderer, reply frames, the Qwen
              paraphrase pipeline (code path only, no model is ever called), the CLI.

CLI
  frames                 frame counts per family and the construction report
  split                  write frame-split.json and LEXICON.json
  generate               stream N dialogues to a JSONL file, deterministically
  seal                   build the L1/L2 test sets, their meta files and SEALED-SPLITS.md
  samples                write SAMPLES.md with 20 worked dialogues
  selftest               generator/parser agreement + notebook-vs-dictionary + throughput
  paraphrase-plan        write the Qwen prompt templates (NO model call, ever)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fable_talker24_dialogues_frames as F                                  # noqa: E402
import fable_talker24_parser as P                                            # noqa: E402

FORMAT = 'fable-talker24-dialogues/1'
NAMESPACE = 'fable-talker24-dialogues-v1'
OUT = HERE.parent/'artifacts/fable-talker24-20260920'

# ------------------------------------------------------------- M0's closed world (mode m0)
# scripts/fable_notebook_m0.py and scripts/astra_canonical_operator.py.  Repeated as plain
# integers so generation needs neither torch nor a checkpoint; a test checks them against
# the real modules.
WORLD_TOKEN, QUESTION_TOKEN, ANSWER_TOKEN, NEWLINE = 3, 4, 5, 7
LINK = 11
ENTITY_MIN, ENTITY_MAX = 52, 68
MAX_NAMES = ENTITY_MAX - ENTITY_MIN                       # 16, the operator's hard limit
VALUE_MIN = 12
RELATION_TOKEN = {'friend': LINK, 'gift': 8, 'prize': 9, 'charm': 10}
RELATIONS = ('friend', 'gift', 'prize', 'charm')
ATTRIBUTE_RELATIONS = ('gift', 'prize', 'charm')
VALUE_WORDS = P.VALUES
VALUE_TOKEN = {w: VALUE_MIN + i for i, w in enumerate(VALUE_WORDS)}
DEFAULT_NAMES = ('Mira', 'Oren', 'Tal', 'Ada', 'Bram', 'Cleo', 'Dov', 'Esme',
                 'Finn', 'Gia', 'Hal', 'Ivo', 'Juno', 'Kai', 'Lena', 'Nils')

# ------------------------------------------------------------- name codes beyond 16 (pool)
# Design section 4.3: after M1 a name is a placeholder plus a frozen code from the
# 4,096-code pool of scripts/fable_newnames21.py (3,072 training / 1,024 reserved).  The
# generator never touches the 48-number code; it records the INDEX into the pool subset,
# drawn exactly as `fable_newnames21.assign_codes` draws it.
POOL_SIZE, RESERVED_SIZE = 4096, 1024
POOL_TRAIN_SIZE = POOL_SIZE - RESERVED_SIZE
POOL_CODE_NAMESPACE = 'fable-talker24/name-codes'

_SYL_ONSET = ('b', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'r', 's', 't', 'v', 'z')
_SYL_NUCLEUS = ('a', 'e', 'i', 'o', 'u')
_SYL_CODA = ('', '', '', 'n', 'l', 'r', 's', 'm')


def build_name_pool(size=256):
    """Invented two-syllable names, deterministic, none colliding with the lexicon.

    Names carry no world knowledge on purpose: the talker must learn that a name is a
    label, never a fact (section B of the design).
    """
    names, seen = [], set()
    rng = random.Random(f'{NAMESPACE}:name-pool')
    while len(names) < size:
        word = (rng.choice(_SYL_ONSET) + rng.choice(_SYL_NUCLEUS) + rng.choice(_SYL_CODA)
                + rng.choice(_SYL_ONSET) + rng.choice(_SYL_NUCLEUS) + rng.choice(_SYL_CODA))
        if word in seen or word in P.LEXICON or len(word) < 4:
            continue
        candidate = word.capitalize()
        if P.looks_like_gibberish(P.Token(word, 0, len(word))):
            continue
        seen.add(word)
        names.append(candidate)
    return tuple(names)


NAME_POOL = build_name_pool()


def draw_pool_indices(key, n_people, which='train'):
    """`n_people` distinct pool-subset rows, drawn exactly like `assign_codes` does.

    `fable_newnames21.assign_codes` is `random.Random(key).sample(range(total), people)`
    per world.  One world here, so one `sample` call with the same key shape.  A test
    compares this against the real function when torch is importable.
    """
    total = POOL_TRAIN_SIZE if which == 'train' else RESERVED_SIZE
    return random.Random(key).sample(range(total), n_people)


# =============================================================== the notebook simulator

class SimNotebook:
    """M0's notebook, in plain Python: an append-only list plus the derived current view.

    The correction rule is M0's exactly -- `view[(subject, relation)] = the latest appended
    row` -- and `answer` is the fixed loop: one lookup per hop, stopping the moment a hop is
    missing.  `fable_notebook_m0` is not imported (it needs torch); a test checks that this
    simulator and a direct dictionary walk over the appended rows always agree.
    """

    def __init__(self, symbol_mode='m0'):
        self.symbol_mode = symbol_mode
        self.appends = []                 # [(subject_symbol, relation_symbol, object_symbol)]
        self.names = {}                   # surface name -> (slot, symbol)
        self.order = []                   # slots in order of first appearance

    # -------------------------------------------------------------------- symbol table
    def name_symbol(self, name, code_index=None):
        """Assign a symbol the first time a name is used, as `Notebook.name_token` does."""
        if name in self.names:
            return self.names[name], False
        slot = len(self.order)
        if self.symbol_mode == 'm0':
            if slot >= MAX_NAMES:
                raise ValueError(f'more than {MAX_NAMES} names in one dialogue')
            symbol = ENTITY_MIN + slot
        else:
            symbol = code_index
        self.names[name] = (slot, symbol)
        self.order.append(name)
        return (slot, symbol), True

    # -------------------------------------------------------------------------- writing
    def append(self, subject_symbol, relation, object_symbol):
        previous = self.view().get((subject_symbol, RELATION_TOKEN[relation]))
        self.appends.append((subject_symbol, RELATION_TOKEN[relation], object_symbol))
        return previous

    def row(self, subject_symbol, relation, object_symbol):
        return [WORLD_TOKEN, subject_symbol, RELATION_TOKEN[relation], object_symbol, NEWLINE]

    # -------------------------------------------------------------------------- reading
    def view(self):
        """Latest appended row per (subject, relation); insertion order preserved."""
        view = {}
        for subject, relation, obj in self.appends:
            view[(subject, relation)] = obj
        return view

    def rows(self):
        return [[WORLD_TOKEN, s, r, o, NEWLINE] for (s, r), o in self.view().items()]

    def answer(self, subject_symbol, path):
        """The fixed loop.  Returns (answer_symbol or None, trace, unknown_step)."""
        view, entity, trace = self.view(), subject_symbol, []
        for step, relation in enumerate(path, 1):
            key = (entity, RELATION_TOKEN[relation])
            if key not in view:
                return None, trace, step
            entity = view[key]
            trace.append(dict(step=step, entity=key[0], relation=key[1], answer=entity))
        return entity, trace, None

    def question_tokens(self, subject_symbol, path):
        return ([QUESTION_TOKEN, subject_symbol]
                + [RELATION_TOKEN[r] for r in path] + [ANSWER_TOKEN])

    def mentioned(self, symbol):
        """Is there any row in the view about this person, as subject or as object?"""
        for (subject, _), obj in self.view().items():
            if subject == symbol or obj == symbol:
                return True
        return False


def dictionary_walk(appends, subject_symbol, path):
    """An independent reading of the same appends: build the view, then walk it.

    Deliberately written a second time, in a different shape, so the test that compares it
    with `SimNotebook.answer` is a real check and not a tautology.
    """
    view = {}
    for subject, relation, obj in appends:
        view[(subject, relation)] = obj
    entity = subject_symbol
    for step, relation in enumerate(path, 1):
        token = RELATION_TOKEN[relation]
        if (entity, token) not in view:
            return None, step
        entity = view[(entity, token)]
    return entity, None


# ========================================================================= the renderer

PLACEHOLDER_RE = re.compile(r'\{[A-Z_0-9]+\}')


def render(template, parts):
    """Fill a template; return (text, {role: (start, end)}).

    `parts[key]` is a list of `(text, role)` segments; `role` is None for plain words and
    'subject' / 'object' / 'old' for the pieces a pointer head must point at.  Spans are
    character offsets into the returned text, which is what INTERFACE-dialogues.md promises.
    """
    segments = []
    for piece in re.split(r'(\{[A-Z_0-9]+\})', template):
        if not piece:
            continue
        if piece.startswith('{') and piece.endswith('}'):
            segments.extend(parts[piece[1:-1]])
        else:
            segments.append((piece, None))
    text, spans, position = [], {}, 0
    for chunk, role in segments:
        if role is not None and role not in spans:
            spans[role] = (position, position + len(chunk))
        text.append(chunk)
        position += len(chunk)
    return ''.join(text), spans


def owner_parts(name, path, style):
    """The {OWNER} / {OWNER_OF} segments for a chain whose LAST relation is path[-1]."""
    middle = list(path[:-1])
    if style == 'poss':
        segs = [(name, 'subject')]
        for relation in middle:
            segs.append((f"'s {relation}", None))
        return segs
    segs = []
    for relation in reversed(middle):
        segs.append((f'the {relation} of ', None))
    segs.append((name, 'subject'))
    return segs


def apply_noise(text, spans, ops):
    """Surface noise.  Only the final character may move, so no slot span is disturbed."""
    for op in ops:
        if op == 'drop_period' and text.endswith('.'):
            text = text[:-1]
        elif op == 'bang' and text.endswith('.'):
            text = text[:-1] + '!'
        elif op == 'ellipsis' and text.endswith('.'):
            text = text + '..'
        elif op == 'capitalise_start' and text and text[0].islower():
            if not any(start == 0 for start, _ in spans.values()):
                text = text[0].upper() + text[1:]
        elif op == 'upper_i':
            text = re.sub(r'(?<![A-Za-z])i(?![A-Za-z\'])', 'I', text)
    return text


def compose(frame, parts, opener, closer, noise_ops):
    """Frame + opener + closer + noise -> (text, spans, closer_used).

    Spans are character offsets into the FINAL text.  `closer_used` is the closer that
    actually survived, which is what the record must name."""
    core, spans = render(frame.template, parts)
    prefix = opener[1] if opener else ''
    text = prefix + core
    spans = {role: (start + len(prefix), end + len(prefix)) for role, (start, end) in spans.items()}
    # A closer replaces the final stop.  It is never attached to a question: ", got it?"
    # after "what is Mira's gift?" would delete the question mark, and the sentence would
    # stop being a question in any reading -- the label would then be a lie.
    if closer and not text.rstrip().endswith('?'):
        if text.endswith(('.', '!')):
            text = text[:-1]
        text = text + closer[1]
    else:
        closer = None
    return apply_noise(text, spans, noise_ops), spans, closer


def pick_noise(rng):
    op = rng.choices(F.NOISE_OPS, weights=F.NOISE_WEIGHTS, k=1)[0]
    return [] if op == 'none' else op.split('+')


# ============================================================================== thoughts

def thought(act, subject=None, path=(), obj=None, old=None, speaker='user',
            unknown_reason=None, unknown_step=None, teachable=True):
    path = list(path)
    return dict(
        act=act,
        subject=subject,
        relation_path=path,
        relation_symbols=[RELATION_TOKEN[r] for r in path],
        object=obj,
        old=old,
        flags=dict(path_len=len(path), speaker=speaker, unknown_reason=unknown_reason,
                   unknown_step=unknown_step, has_old_value=old is not None,
                   teachable=teachable))


def person_slot(name, slot, symbol, span=None):
    out = dict(name=name, slot=slot, symbol=symbol, kind='person')
    out['span'] = list(span) if span else None
    return out


def value_slot(word, span=None):
    return dict(name=word, slot=None, symbol=VALUE_TOKEN[word], kind='value',
                span=list(span) if span else None)


# ========================================================================= reply frames
# Section 4.2: ">= 30 frames per reply act, with copy actions where names and values go."
# `<SUBJ>` `<OBJ>` `<OLD>` are the mouth's three copy actions; a name or a value NEVER
# appears as a word in a reply target, so the mouth has no way to invent one (section 3.4).
# `{RPATH}` is the possessive relation chain after the subject ("friend's gift"); `{R}` the
# last relation alone.

REPLY_ACK_ATTR = [
    "ok. <SUBJ>'s {RPATH} is a <OBJ>.",
    "ok, i wrote that down: <SUBJ>'s {RPATH} is a <OBJ>.",
    "got it. <SUBJ>'s {RPATH} is a <OBJ>.",
    "noted. <SUBJ>'s {RPATH} is a <OBJ>.",
    "i will remember that. <SUBJ>'s {RPATH} is a <OBJ>.",
    "thank you. <SUBJ>'s {RPATH} is a <OBJ>.",
    "ok! <SUBJ>'s {RPATH} is a <OBJ>.",
    "that is new to me. <SUBJ>'s {RPATH} is a <OBJ>.",
    "i have written it down: <SUBJ>'s {RPATH} is a <OBJ>.",
    "in my notebook now: <SUBJ>'s {RPATH} is a <OBJ>.",
    "ok. so <SUBJ>'s {RPATH} is a <OBJ>.",
    "right. <SUBJ>'s {RPATH} is a <OBJ>.",
    "i understand. <SUBJ>'s {RPATH} is a <OBJ>.",
    "done. <SUBJ>'s {RPATH} is a <OBJ>.",
    "added. <SUBJ>'s {RPATH} is a <OBJ>.",
    "a new line for <SUBJ>: the {R} is a <OBJ>.",
    "ok, <SUBJ> then: the {R} is a <OBJ>.",
    "i put it in my notebook: <SUBJ>'s {RPATH} is a <OBJ>.",
]
REPLY_ACK_LINK = [
    "ok. <SUBJ>'s {RPATH} is <OBJ>.",
    "ok, i wrote that down: <SUBJ>'s {RPATH} is <OBJ>.",
    "got it. <SUBJ>'s {RPATH} is <OBJ>.",
    "noted. <SUBJ>'s {RPATH} is <OBJ>.",
    "i will remember that. <SUBJ>'s {RPATH} is <OBJ>.",
    "thank you. <SUBJ>'s {RPATH} is <OBJ>.",
    "ok! <SUBJ>'s {RPATH} is <OBJ>.",
    "that is new to me. <SUBJ>'s {RPATH} is <OBJ>.",
    "i have written it down: <SUBJ>'s {RPATH} is <OBJ>.",
    "in my notebook now: <SUBJ>'s {RPATH} is <OBJ>.",
    "ok. so <SUBJ>'s {RPATH} is <OBJ>.",
    "right. <SUBJ>'s {RPATH} is <OBJ>.",
    "i understand. <SUBJ>'s {RPATH} is <OBJ>.",
    "done. <SUBJ>'s {RPATH} is <OBJ>.",
    "added. <SUBJ>'s {RPATH} is <OBJ>.",
    "a new line for <SUBJ>: the {R} is <OBJ>.",
    "ok, <SUBJ> then: the {R} is <OBJ>.",
    "i put it in my notebook: <SUBJ>'s {RPATH} is <OBJ>.",
]
REPLY_ACKFIX_ATTR = [
    "ok, i changed it. <SUBJ>'s {RPATH} is a <OBJ> now, not a <OLD>.",
    "ok. <SUBJ>'s {RPATH} is a <OBJ> now; it was a <OLD>.",
    "i fixed that. <SUBJ>'s {RPATH} is a <OBJ>, not a <OLD>.",
    "thank you for the correction. <SUBJ>'s {RPATH} is a <OBJ> now.",
    "got it, a <OLD> was wrong. <SUBJ>'s {RPATH} is a <OBJ>.",
    "i crossed out a <OLD>. <SUBJ>'s {RPATH} is a <OBJ>.",
    "changed. <SUBJ>'s {RPATH} is a <OBJ>, not a <OLD>.",
    "ok, the old line said a <OLD>. now <SUBJ>'s {RPATH} is a <OBJ>.",
    "corrected. <SUBJ>'s {RPATH} is a <OBJ>.",
    "i have replaced it. <SUBJ>'s {RPATH} is a <OBJ>.",
    "understood. <SUBJ>'s {RPATH} is a <OBJ> now.",
    "ok. i will not say a <OLD> again. <SUBJ>'s {RPATH} is a <OBJ>.",
    "that line is updated: <SUBJ>'s {RPATH} is a <OBJ>.",
    "done, it was a <OLD> before. <SUBJ>'s {RPATH} is a <OBJ>.",
    "ok! <SUBJ>'s {RPATH} is a <OBJ> now.",
]
REPLY_ACKFIX_LINK = [
    "ok, i changed it. <SUBJ>'s {RPATH} is <OBJ> now, not <OLD>.",
    "ok. <SUBJ>'s {RPATH} is <OBJ> now; it was <OLD>.",
    "i fixed that. <SUBJ>'s {RPATH} is <OBJ>, not <OLD>.",
    "thank you for the correction. <SUBJ>'s {RPATH} is <OBJ> now.",
    "got it, <OLD> was wrong. <SUBJ>'s {RPATH} is <OBJ>.",
    "i crossed out <OLD>. <SUBJ>'s {RPATH} is <OBJ>.",
    "changed. <SUBJ>'s {RPATH} is <OBJ>, not <OLD>.",
    "ok, the old line said <OLD>. now <SUBJ>'s {RPATH} is <OBJ>.",
    "corrected. <SUBJ>'s {RPATH} is <OBJ>.",
    "i have replaced it. <SUBJ>'s {RPATH} is <OBJ>.",
    "understood. <SUBJ>'s {RPATH} is <OBJ> now.",
    "ok. i will not say <OLD> again. <SUBJ>'s {RPATH} is <OBJ>.",
    "that line is updated: <SUBJ>'s {RPATH} is <OBJ>.",
    "done, it was <OLD> before. <SUBJ>'s {RPATH} is <OBJ>.",
    "ok! <SUBJ>'s {RPATH} is <OBJ> now.",
]
REPLY_ANSWER_ATTR = [
    "<SUBJ>'s {RPATH} is a <OBJ>.",
    "it is a <OBJ>.",
    "a <OBJ>.",
    "a <OBJ>, i think.",
    "<SUBJ>'s {RPATH} is a <OBJ>, from my notebook.",
    "my notebook says a <OBJ>.",
    "i wrote down a <OBJ>. <SUBJ>'s {RPATH} is a <OBJ>.",
    "the {R} is a <OBJ>.",
    "that is a <OBJ>.",
    "it is a <OBJ>. that is what you told me.",
    "you told me <SUBJ>'s {RPATH} is a <OBJ>.",
    "a <OBJ> is <SUBJ>'s {RPATH}.",
    "<SUBJ>'s {RPATH}? a <OBJ>.",
    "i looked it up: <SUBJ>'s {RPATH} is a <OBJ>.",
    "i have a <OBJ> for <SUBJ>'s {RPATH}.",
    "the answer is a <OBJ>.",
    "it is a <OBJ> now.",
    "<SUBJ>'s {RPATH} is a <OBJ>, if my notebook is right.",
]
REPLY_ANSWER_LINK = [
    "<SUBJ>'s {RPATH} is <OBJ>.",
    "it is <OBJ>.",
    "<OBJ>.",
    "<OBJ>, i think.",
    "<SUBJ>'s {RPATH} is <OBJ>, from my notebook.",
    "my notebook says <OBJ>.",
    "i wrote down <OBJ>. <SUBJ>'s {RPATH} is <OBJ>.",
    "the {R} is <OBJ>.",
    "that is <OBJ>.",
    "it is <OBJ>. that is what you told me.",
    "you told me <SUBJ>'s {RPATH} is <OBJ>.",
    "<OBJ> is <SUBJ>'s {RPATH}.",
    "<SUBJ>'s {RPATH}? <OBJ>.",
    "i looked it up: <SUBJ>'s {RPATH} is <OBJ>.",
    "i have <OBJ> for <SUBJ>'s {RPATH}.",
    "the answer is <OBJ>.",
    "it is <OBJ> now.",
    "<SUBJ>'s {RPATH} is <OBJ>, if my notebook is right.",
]
# UNKNOWN about a person we have a name for: <SUBJ> may be copied, <OBJ> NEVER can be --
# there is no object symbol in the thought, so the printer has nothing to substitute.
REPLY_UNKNOWN_SUBJ = [
    "i do not know <SUBJ>'s {RPATH} yet. can you tell me?",
    "i do not know <SUBJ>'s {RPATH}. you can teach me.",
    "my notebook has nothing about <SUBJ>'s {RPATH}.",
    "i have not been told <SUBJ>'s {RPATH}.",
    "nothing in my notebook says <SUBJ>'s {RPATH}.",
    "i cannot answer that. i do not have <SUBJ>'s {RPATH}.",
    "sorry, i do not know <SUBJ>'s {RPATH}.",
    "i do not know. please tell me <SUBJ>'s {RPATH}.",
    "i looked and found nothing for <SUBJ>'s {RPATH}.",
    "i have no line for <SUBJ>'s {RPATH}.",
    "that one is not in my notebook.",
    "i do not know that yet. can you tell me about <SUBJ>?",
    "i have nothing written about <SUBJ> there.",
    "i cannot find <SUBJ>'s {RPATH} in my notebook.",
    "i do not know <SUBJ>'s {RPATH} yet.",
    "i would be guessing. i do not know <SUBJ>'s {RPATH}.",
]
REPLY_UNKNOWN_CHAIN = [
    "i lost the chain. i do not know <SUBJ>'s {RPATH}.",
    "i could not follow that all the way. i do not know <SUBJ>'s {RPATH}.",
    "i got part of the way and then my notebook stopped.",
    "one of the steps is missing, so i do not know.",
    "i cannot follow the whole chain for <SUBJ>.",
    "i do not have every step for <SUBJ>'s {RPATH}.",
    "my notebook breaks before the end of that question.",
    "i cannot answer that: a step in the middle is missing.",
    "i do not know. a step for <SUBJ> is missing.",
    "the chain stops before the answer, so i do not know.",
]
REPLY_UNKNOWN_NONE = [
    "i do not know that yet. you can teach me.",
    "i do not know that. i only know what you tell me.",
    "i cannot know that. nobody has told me.",
    "that is outside what i can be taught right now.",
    "i do not know. i have no facts about the world.",
    "sorry, i do not know anything like that.",
    "i only know what is in my notebook, and that is not in it.",
    "i cannot answer that one.",
    "i do not know that yet.",
    "i have no way to know that.",
]
REPLY_CLARIFY = [
    "i am not sure what you mean. can you say it in a short way?",
    "sorry, i did not understand that.",
    "can you say that again in a simple way?",
    "i did not follow that. who do you mean?",
    "i am not sure. can you say one thing at a time?",
    "sorry, that was too much for me. one fact at a time?",
    "i did not understand. can you use a name?",
    "who is that about? i do not know.",
    "i am lost. can you say it another way?",
    "can you tell me the name, please?",
    "i did not get that. can you try again?",
    "that did not make sense to me.",
    "sorry, i cannot read that.",
    "i am not sure what that means.",
    "can you write that more simply?",
    "i need a name to know who you mean.",
    "one thing at a time, please.",
    "i did not understand. can you say who and what?",
    "sorry, can you say that again?",
    "i do not know what you are asking.",
    "that was not clear to me.",
    "please say it in one short sentence.",
    "i cannot tell who that is about.",
    "i do not understand. can you help me?",
    "sorry, i missed that.",
    "can you break that into two sentences?",
    "i am not sure. can you use a full name?",
    "i did not catch that.",
    "i am confused. can you say it again?",
    "sorry, that one is too hard for me.",
]
REPLY_CHAT = [
    "that sounds fun.",
    "that sounds nice.",
    "i am glad to hear that.",
    "hello! how are you today?",
    "hi! it is good to see you.",
    "i am fine, thank you.",
    "i am well, thank you for asking.",
    "that is interesting.",
    "i like that.",
    "tell me more.",
    "what did you do then?",
    "how did that feel?",
    "that sounds like a long day.",
    "i hope you had a good time.",
    "i do not go outside, but that sounds nice.",
    "i do not know much about that, but i like hearing it.",
    "thank you for telling me.",
    "ok!",
    "good night. sleep well.",
    "see you tomorrow.",
    "talk to you later.",
    "i am here if you want to teach me something.",
    "you can tell me a fact if you like.",
    "i like it when you talk to me.",
    "that is kind of you.",
    "i am sorry to hear that.",
    "i hope tomorrow is better.",
    "that made me happy.",
    "what else happened?",
    "i do not have a favourite, but i like hearing yours.",
    "i cannot see, but i can listen.",
    "i do not sleep. i just wait for you.",
]

REPLY_FAMILIES = {
    'reply.ack.attr': REPLY_ACK_ATTR,
    'reply.ack.link': REPLY_ACK_LINK,
    'reply.ackfix.attr': REPLY_ACKFIX_ATTR,
    'reply.ackfix.link': REPLY_ACKFIX_LINK,
    'reply.answer.attr': REPLY_ANSWER_ATTR,
    'reply.answer.link': REPLY_ANSWER_LINK,
    'reply.unknown.subj': REPLY_UNKNOWN_SUBJ,
    'reply.unknown.chain': REPLY_UNKNOWN_CHAIN,
    'reply.unknown.none': REPLY_UNKNOWN_NONE,
    'reply.clarify': REPLY_CLARIFY,
    'reply.chat': REPLY_CHAT,
}
REPLY_ACT_OF = {'reply.ack.attr': 'ACK', 'reply.ack.link': 'ACK',
                'reply.ackfix.attr': 'ACK', 'reply.ackfix.link': 'ACK',
                'reply.answer.attr': 'ANSWER', 'reply.answer.link': 'ANSWER',
                'reply.unknown.subj': 'UNKNOWN', 'reply.unknown.chain': 'UNKNOWN',
                'reply.unknown.none': 'UNKNOWN',
                'reply.clarify': 'CLARIFY', 'reply.chat': 'CHAT'}

COPY_ACTIONS = ('<SUBJ>', '<OBJ>', '<OLD>')
COPY_FIELD = {'<SUBJ>': 'subject', '<OBJ>': 'object', '<OLD>': 'old'}
COPY_RE = re.compile(r'<SUBJ>|<OBJ>|<OLD>')


def render_reply(family, index, reply_thought):
    """Build the mouth target, the printed surface, and the copy alignment between them."""
    template = REPLY_FAMILIES[family][index]
    path = reply_thought['relation_path']
    template = template.replace('{RPATH}', "'s ".join(path) if path else '')
    template = template.replace('{R}', path[-1] if path else '')
    text, surface, copies, cursor = [], [], [], 0
    text_pos = surface_pos = 0
    for match in COPY_RE.finditer(template):
        plain = template[cursor:match.start()]
        text.append(plain)
        surface.append(plain)
        text_pos += len(plain)
        surface_pos += len(plain)
        action = match.group(0)
        field = COPY_FIELD[action]
        slot = reply_thought[field]
        if slot is None:
            raise ValueError(f'{family}[{index}] copies {action} but the thought has no {field}')
        word = slot['name']
        copies.append(dict(action=action, field=field, slot=slot['slot'],
                           symbol=slot['symbol'], word=word,
                           text_span=[text_pos, text_pos + len(action)],
                           surface_span=[surface_pos, surface_pos + len(word)]))
        text.append(action)
        surface.append(word)
        text_pos += len(action)
        surface_pos += len(word)
        cursor = match.end()
    tail = template[cursor:]
    text.append(tail)
    surface.append(tail)
    return ''.join(text), ''.join(surface), copies


def reply_frame_counts():
    counts = {}
    for family, frames in REPLY_FAMILIES.items():
        counts.setdefault(REPLY_ACT_OF[family], 0)
        counts[REPLY_ACT_OF[family]] += len(frames)
    return counts


# ====================================================================== the world sampler

TURN_MIX = (('TELL', .35), ('ASK', .30), ('CORRECT', .08), ('CHAT', .25), ('UNCLEAR', .02))
# Section 4.2's question mix, over ALL questions.
QUESTION_MIX = (('one_hop', .45), ('two_hop', .30), ('three_hop', .05),
                ('untaught_relation', .08), ('unknown_person', .07), ('chain_broke', .05))
# unanswerable ASKs that are outside anything teachable (section 4.4 case 3) are drawn
# separately, as a share of all ASK turns, because they have no relation at all.
NOT_TEACHABLE_SHARE = .06
MIN_PEOPLE, MAX_PEOPLE = 2, 12
MAX_CORRECTIONS = 3
MIN_TURNS, MAX_TURNS = 6, 20


def sample_world(rng, symbol_mode, pool):
    """People, and the facts this dialogue will get round to teaching."""
    n_people = rng.randint(MIN_PEOPLE, MAX_PEOPLE)
    if symbol_mode == 'm0':
        names = rng.sample(list(DEFAULT_NAMES), min(MAX_NAMES, n_people + 3))
        indices = None
    else:
        names = rng.sample(list(NAME_POOL), n_people + 3)
        indices = None
    cast, spare = names[:n_people], names[n_people:]
    facts = []
    for name in cast:
        relations = list(ATTRIBUTE_RELATIONS)
        rng.shuffle(relations)
        for relation in relations[:rng.randint(1, 3)]:
            facts.append((name, relation, rng.choice(VALUE_WORDS)))
        if len(cast) > 1 and rng.random() < .8:
            facts.append((name, 'friend', rng.choice([n for n in cast if n != name])))
    rng.shuffle(facts)
    return dict(cast=cast, spare=spare, facts=facts, pool=pool, indices=indices)


def plan_turns(rng, n_facts):
    """A turn plan honouring section 4.2's mix, with corrections capped at three."""
    acts, weights = zip(*TURN_MIX)
    n_turns = rng.randint(MIN_TURNS, MAX_TURNS)
    plan, taught, corrections = ['TELL'], 0, 0
    while len(plan) < n_turns:
        act = rng.choices(acts, weights=weights, k=1)[0]
        if act == 'TELL' and taught >= n_facts:
            act = 'ASK' if taught else 'CHAT'
        if act == 'CORRECT' and (corrections >= MAX_CORRECTIONS or taught == 0):
            act = 'TELL' if taught < n_facts else 'ASK'
        if act == 'ASK' and taught == 0:
            act = 'TELL'
        plan.append(act)
        taught += int(act == 'TELL')
        corrections += int(act == 'CORRECT')
    return plan


# ===================================================================== the turn builders

def _frame_parts(name, path, obj_word, obj_kind, old_word, pronoun=None, gibberish=None,
                 second=None):
    """The segment lists every core-frame placeholder can need."""
    parts = {
        'OWNER': owner_parts(name, path, 'poss') if name else [],
        'OWNER_OF': owner_parts(name, path, 'of') if name else [],
        'R': [(path[-1], None)] if path else [],
    }
    # `attr` frames say `{V}` (one of the sixteen value words); `link` frames say `{O}`
    # (another person).  The family fixes which, so exactly one of the two is filled and a
    # link frame can never be handed a colour.
    segments = [(obj_word, 'object')] if obj_word else []
    parts['V' if obj_kind in ('value', 'attr') else 'O'] = segments
    if old_word is not None:
        parts['OLD'] = [(old_word, 'old')]
    if pronoun:
        parts['P'] = [(pronoun, None)]
    if gibberish:
        for i, word in enumerate(gibberish):
            parts['G'] = [(word, None)]
    if second:
        parts['O2'], parts['R2'], parts['V2'] = second
    return parts


def _fill_repeated(template, parts, rng, gibberish_words):
    """`{G}` can occur several times; give each occurrence its own nonsense word."""
    out, i = [], 0
    for piece in re.split(r'(\{G\})', template):
        if piece == '{G}':
            out.append(gibberish_words[i % len(gibberish_words)])
            i += 1
        else:
            out.append(piece)
    return ''.join(out)


def build_fact_turn(rng, act, relation_kind, level, name, slot, symbol, path, obj, old):
    """A TELL / CORRECT / ASK turn about a person.  Returns (text, spans, frame)."""
    family = f'{act.lower()}.{relation_kind}'
    frames = F.frames_for(family, level)
    frame = rng.choice(frames)
    obj_word = obj['name'] if obj else None
    parts = _frame_parts(name, path, obj_word, relation_kind,
                         old['name'] if old else None)
    if '{OLD}' in frame.template and old is None:
        frame = rng.choice([f for f in frames if '{OLD}' not in f.template])
    if old is not None and '{OLD}' not in frame.template:
        candidates = [f for f in frames if '{OLD}' in f.template]
        if candidates:
            frame = rng.choice(candidates)
        else:
            old = None
            parts.pop('OLD', None)
    opener, closer, noise = _decor(rng, level)
    text, spans, closer = compose(frame, parts, opener, closer, noise)
    return text, spans, frame, opener, closer, noise, old


def _decor(rng, level):
    openers, closers = F.openers_for(level), F.closers_for(level)
    opener = rng.choice(openers) if openers and rng.random() < .30 else None
    closer = rng.choice(closers) if closers and rng.random() < .18 else None
    return opener, closer, pick_noise(rng)


def _span_of(spans, role):
    return list(spans[role]) if role in spans else None


class Generator:
    """One dialogue at a time; nothing is shared between dialogues except the frame table."""

    def __init__(self, split='L1', symbol_mode='m0', pool='train', namespace=NAMESPACE):
        if split not in ('L1', 'L2'):
            raise ValueError(f'{split}: only L1 and L2 can be generated; L3 is typed by hand')
        if symbol_mode not in ('m0', 'pool'):
            raise ValueError(symbol_mode)
        self.split, self.symbol_mode, self.pool = split, symbol_mode, pool
        self.namespace = namespace

    # ------------------------------------------------------------------------ one dialogue
    def dialogue(self, index):
        key = f'{self.namespace}:{self.split}:{index}'
        rng = random.Random(key)
        world = sample_world(rng, self.symbol_mode, self.pool)
        notebook = SimNotebook(self.symbol_mode)
        codes = None
        if self.symbol_mode == 'pool':
            total = len(world['cast']) + len(world['spare'])
            codes = draw_pool_indices(f'{POOL_CODE_NAMESPACE}:{key}', total, self.pool)
        code_of = {}
        if codes is not None:
            for name, code in zip(world['cast'] + world['spare'], codes):
                code_of[name] = code

        plan = plan_turns(rng, len(world['facts']))
        turns, taught, pending = [], [], list(world['facts'])
        for i, act in enumerate(plan):
            turn = self._turn(rng, i, act, world, notebook, taught, pending, code_of)
            if turn is not None:
                turns.append(turn)
        people = [dict(slot=slot, name=name, symbol=symbol)
                  for name, (slot, symbol) in sorted(notebook.names.items(),
                                                     key=lambda kv: kv[1][0])]
        counts = {}
        for turn in turns:
            counts[turn['user']['thought']['act']] = \
                counts.get(turn['user']['thought']['act'], 0) + 1
        record = dict(
            id=f'{self.split}/{index:06d}', format=FORMAT, split=self.split, index=index,
            seed_key=key, symbol_mode=self.symbol_mode,
            world=dict(people=people, values=dict(VALUE_TOKEN), relations=dict(RELATION_TOKEN),
                       n_people=len(people),
                       code_pool=None if codes is None else dict(
                           pool=self.pool, size=POOL_TRAIN_SIZE if self.pool == 'train'
                           else RESERVED_SIZE, key=f'{POOL_CODE_NAMESPACE}:{key}',
                           indices=[code_of[p['name']] for p in people])),
            turns=turns, counts=counts,
            final_view={f'{s},{r}': o for (s, r), o in notebook.view().items()},
            levels=dict(frames=self.split, openers=self.split, closers=self.split))
        return record

    # ----------------------------------------------------------------------------- a turn
    def _turn(self, rng, i, act, world, notebook, taught, pending, code_of):
        if act == 'TELL':
            return self._tell(rng, i, world, notebook, taught, pending, code_of)
        if act == 'CORRECT':
            return self._correct(rng, i, world, notebook, taught, code_of)
        if act == 'ASK':
            return self._ask(rng, i, world, notebook, taught, code_of)
        if act == 'CHAT':
            return self._chat(rng, i)
        return self._unclear(rng, i, world)

    # ------------------------------------------------------------------------------- TELL
    def _tell(self, rng, i, world, notebook, taught, pending, code_of):
        while pending:
            name, relation, obj_word = pending.pop(0)
            key = None
            try:
                (slot, symbol), fresh = notebook.name_symbol(name, code_of.get(name))
            except ValueError:
                continue
            if (symbol, RELATION_TOKEN[relation]) in notebook.view():
                continue
            key = (name, relation, obj_word)
            break
        else:
            return self._chat(rng, i)
        kind = 'link' if relation == 'friend' else 'attr'
        named = [dict(slot=slot, name=name, symbol=symbol)] if fresh else []
        if kind == 'link':
            try:
                (oslot, osymbol), ofresh = notebook.name_symbol(obj_word, code_of.get(obj_word))
            except ValueError:
                return self._chat(rng, i)
            if ofresh:
                named.append(dict(slot=oslot, name=obj_word, symbol=osymbol))
            obj = person_slot(obj_word, oslot, osymbol)
        else:
            obj = value_slot(obj_word)
        path = [relation]
        text, spans, frame, opener, closer, noise, _ = build_fact_turn(
            rng, 'TELL', kind, self.split, name, slot, symbol, path, obj, None)
        subject = person_slot(name, slot, symbol, _span_of(spans, 'subject'))
        obj = dict(obj, span=_span_of(spans, 'object'))
        user = thought('TELL', subject, path, obj)
        previous = notebook.append(symbol, relation, obj['symbol'])
        taught.append((name, relation, obj_word))
        reply_thought = thought('ACK', dict(subject), path, dict(obj), None, speaker='model')
        family = f'reply.ack.{kind}'
        return self._assemble(i, text, user, frame, opener, closer, noise, family, rng,
                              reply_thought,
                              notebook_record=dict(
                                  op='append', row=notebook.row(symbol, relation, obj['symbol']),
                                  replaced=None, named=named, view_size=len(notebook.view()),
                                  question=None, trace=None, answerable=None,
                                  answer_symbol=None, unknown_reason=None, unknown_step=None))

    # ---------------------------------------------------------------------------- CORRECT
    def _correct(self, rng, i, world, notebook, taught, code_of):
        if not taught:
            return self._chat(rng, i)
        name, relation, old_word = rng.choice(taught)
        (slot, symbol), _ = notebook.name_symbol(name, code_of.get(name))
        kind = 'link' if relation == 'friend' else 'attr'
        current = notebook.view().get((symbol, RELATION_TOKEN[relation]))
        if current is None:
            return self._chat(rng, i)
        named = []
        if kind == 'link':
            options = [n for n in world['cast'] if n != name
                       and notebook.names.get(n, (None, None))[1] != current]
            if not options:
                return self._chat(rng, i)
            new_word = rng.choice(options)
            try:
                (oslot, osymbol), ofresh = notebook.name_symbol(new_word, code_of.get(new_word))
            except ValueError:
                return self._chat(rng, i)
            if ofresh:
                named.append(dict(slot=oslot, name=new_word, symbol=osymbol))
            obj = person_slot(new_word, oslot, osymbol)
            old_name = next((n for n, (_, s) in notebook.names.items() if s == current), None)
            old = person_slot(old_name, *notebook.names[old_name]) if old_name else None
        else:
            new_word = rng.choice([v for v in VALUE_WORDS if VALUE_TOKEN[v] != current])
            obj = value_slot(new_word)
            old_value = next((v for v in VALUE_WORDS if VALUE_TOKEN[v] == current), None)
            old = value_slot(old_value) if old_value else None
        say_old = old is not None and rng.random() < .35
        text, spans, frame, opener, closer, noise, used_old = build_fact_turn(
            rng, 'CORRECT', kind, self.split, name, slot, symbol, [relation], obj,
            old if say_old else None)
        subject = person_slot(name, slot, symbol, _span_of(spans, 'subject'))
        obj = dict(obj, span=_span_of(spans, 'object'))
        spoken_old = dict(used_old, span=_span_of(spans, 'old')) if used_old else None
        user = thought('CORRECT', subject, [relation], obj, spoken_old)
        previous = notebook.append(symbol, relation, obj['symbol'])
        for entry in taught:
            if entry[0] == name and entry[1] == relation:
                taught.remove(entry)
                break
        taught.append((name, relation, new_word))
        reply_thought = thought('ACK', dict(subject), [relation], dict(obj), dict(old),
                                speaker='model')
        family = f'reply.ackfix.{kind}'
        return self._assemble(i, text, user, frame, opener, closer, noise, family, rng,
                              reply_thought,
                              notebook_record=dict(
                                  op='append', row=notebook.row(symbol, relation, obj['symbol']),
                                  replaced=dict(row=[WORLD_TOKEN, symbol,
                                                     RELATION_TOKEN[relation], previous, NEWLINE],
                                                object_symbol=previous,
                                                object_word=old['name'] if old else None),
                                  named=named, view_size=len(notebook.view()), question=None,
                                  trace=None, answerable=None, answer_symbol=None,
                                  unknown_reason=None, unknown_step=None))

    # -------------------------------------------------------------------------------- ASK
    def _ask(self, rng, i, world, notebook, taught, code_of):
        if rng.random() < NOT_TEACHABLE_SHARE:
            return self._ask_none(rng, i)
        kinds, weights = zip(*QUESTION_MIX)
        wanted = rng.choices(kinds, weights=weights, k=1)[0]
        chosen = self._choose_question(rng, wanted, world, notebook, taught, code_of)
        if chosen is None:
            return self._chat(rng, i)
        name, path, category = chosen
        try:
            (slot, symbol), fresh = notebook.name_symbol(name, code_of.get(name))
        except ValueError:
            return self._chat(rng, i)
        named = [dict(slot=slot, name=name, symbol=symbol)] if fresh else []
        kind = 'link' if path[-1] == 'friend' else 'attr'
        text, spans, frame, opener, closer, noise, _ = build_fact_turn(
            rng, 'ASK', kind, self.split, name, slot, symbol, path, None, None)
        subject = person_slot(name, slot, symbol, _span_of(spans, 'subject'))
        user = thought('ASK', subject, path, None)
        answer, trace, broke = notebook.answer(symbol, path)
        if answer is not None:
            obj = (person_slot(_name_for(notebook, answer), *notebook.names[
                _name_for(notebook, answer)]) if kind == 'link'
                else value_slot(_value_for(answer)))
            reply_thought = thought('ANSWER', dict(subject), path, obj, speaker='model')
            family = f'reply.answer.{kind}'
            record = dict(op='lookup', row=None, replaced=None, named=named,
                          view_size=len(notebook.view()),
                          question=notebook.question_tokens(symbol, path), trace=trace,
                          answerable=True, answer_symbol=answer, unknown_reason=None,
                          unknown_step=None)
        else:
            # Which of section 4.4's three "I don't know"s is this?
            #   no_such_person -- the notebook has never heard of the person at all;
            #   chain_broke    -- we got part of the way and then lost the trail, i.e. a
            #                     hop AFTER the first is missing;
            #   no_such_fact   -- the person is known but this very first relation is not.
            reason = ('no_such_person' if not notebook.mentioned(symbol)
                      else ('chain_broke' if broke and broke > 1 else 'no_such_fact'))
            reply_thought = thought('UNKNOWN', dict(subject), path, None, speaker='model',
                                    unknown_reason=reason, unknown_step=broke)
            family = 'reply.unknown.chain' if reason == 'chain_broke' else 'reply.unknown.subj'
            record = dict(op='lookup', row=None, replaced=None, named=named,
                          view_size=len(notebook.view()),
                          question=notebook.question_tokens(symbol, path), trace=trace,
                          answerable=False, answer_symbol=None, unknown_reason=reason,
                          unknown_step=broke)
        turn = self._assemble(i, text, user, frame, opener, closer, noise, family, rng,
                              reply_thought, notebook_record=record)
        turn['user']['question_category'] = category
        return turn

    def _choose_question(self, rng, wanted, world, notebook, taught, code_of):
        """Pick (name, path, realised category); fall back in a fixed, declared order."""
        view = notebook.view()
        known = {name: sym for name, (slot, sym) in notebook.names.items()}
        order = {'three_hop': ['three_hop', 'two_hop', 'one_hop'],
                 'two_hop': ['two_hop', 'one_hop'],
                 'one_hop': ['one_hop'],
                 'untaught_relation': ['untaught_relation', 'unknown_person'],
                 'unknown_person': ['unknown_person', 'untaught_relation'],
                 'chain_broke': ['chain_broke', 'untaught_relation', 'unknown_person']}[wanted]
        for category in order:
            got = self._question_of(rng, category, world, notebook, view, known)
            if got:
                return got[0], got[1], category
        return None

    def _question_of(self, rng, category, world, notebook, view, known):
        if category in ('one_hop', 'two_hop', 'three_hop'):
            hops = {'one_hop': 1, 'two_hop': 2, 'three_hop': 3}[category]
            options = []
            for name, symbol in known.items():
                for path in _paths_from(view, symbol, hops):
                    options.append((name, path))
            return rng.choice(options) if options else None
        if category == 'untaught_relation':
            options = [(name, [r]) for name, symbol in known.items() for r in RELATIONS
                       if (symbol, RELATION_TOKEN[r]) not in view and notebook.mentioned(symbol)]
            return rng.choice(options) if options else None
        if category == 'unknown_person':
            options = [(n, [rng.choice(RELATIONS)]) for n in world['spare']
                       if n not in notebook.names]
            return rng.choice(options) if options else None
        if category == 'chain_broke':
            options = []
            for name, symbol in known.items():
                first = view.get((symbol, LINK))
                if first is None:
                    continue
                for r in RELATIONS:
                    if (first, RELATION_TOKEN[r]) not in view:
                        options.append((name, ['friend', r]))
            return rng.choice(options) if options else None
        return None

    # ------------------------------------------------------------- ASK with no relation
    def _ask_none(self, rng, i):
        frames = F.frames_for('ask.none', self.split)
        frame = rng.choice(frames)
        opener, closer, noise = _decor(rng, self.split)
        text, spans, closer = compose(frame, {}, opener, closer, noise)
        user = thought('ASK', None, [], None, teachable=False)
        reply_thought = thought('UNKNOWN', None, [], None, speaker='model',
                                unknown_reason='not_teachable', teachable=False)
        return self._assemble(i, text, user, frame, opener, closer, noise,
                              'reply.unknown.none', rng, reply_thought,
                              notebook_record=_no_notebook())

    # -------------------------------------------------------------------------- CHAT
    def _chat(self, rng, i):
        frames = F.frames_for('chat.none', self.split)
        frame = rng.choice(frames)
        opener, closer, noise = _decor(rng, self.split)
        text, spans, closer = compose(frame, {}, opener, closer, noise)
        user = thought('CHAT', None, [], None)
        reply_thought = thought('CHAT', None, [], None, speaker='model')
        return self._assemble(i, text, user, frame, opener, closer, noise, 'reply.chat',
                              rng, reply_thought, notebook_record=_no_notebook())

    # ----------------------------------------------------------------------- UNCLEAR
    def _unclear(self, rng, i, world):
        frames = F.frames_for('unclear.none', self.split)
        frame = rng.choice(frames)
        names = list(world['cast']) + list(world['spare'])
        rng.shuffle(names)
        template = frame.template
        if '{G}' in template:
            words = rng.sample(list(F.GIBBERISH), template.count('{G}'))
            template = _fill_repeated(template, {}, rng, words)
        filled = (template
                  .replace('{P}', rng.choice(F.PRONOUNS))
                  .replace('{OWNER}', names[0])
                  .replace('{O2}', names[1] if len(names) > 1 else names[0])
                  .replace('{O}', names[min(2, len(names) - 1)])
                  .replace('{R2}', rng.choice(RELATIONS))
                  .replace('{R}', rng.choice(RELATIONS))
                  .replace('{V2}', rng.choice(VALUE_WORDS))
                  .replace('{V}', rng.choice(VALUE_WORDS)))
        stub = F.Frame(frame.family, frame.index, frame.construction, filled)
        opener, closer, noise = _decor(rng, self.split)
        # Do not capitalise a nonsense word that starts the sentence.  Under the published
        # name rule (section 2.1) "a capitalised word the word list has never seen is a
        # name", so "Gbrtz prize mirror." would be a NAME followed by a fact, and calling
        # that UNCLEAR would be a label no reader could justify.  Lower case keeps the
        # nonsense readable as nonsense.  This is the only place a noise op is suppressed.
        if not opener and filled.split()[:1] and filled.split()[0].strip('.,!?;:') in F.GIBBERISH:
            noise = [op for op in noise if op != 'capitalise_start']
        text, spans, closer = compose(stub, {}, opener, closer, noise)
        user = thought('UNCLEAR', None, [], None)
        reply_thought = thought('CLARIFY', None, [], None, speaker='model',
                                unknown_reason='unclear')
        return self._assemble(i, text, user, frame, opener, closer, noise, 'reply.clarify',
                              rng, reply_thought, notebook_record=_no_notebook())

    # ------------------------------------------------------------------------ assembly
    def _assemble(self, i, text, user_thought, frame, opener, closer, noise, reply_family,
                  rng, reply_thought, notebook_record):
        index = rng.randrange(len(REPLY_FAMILIES[reply_family]))
        reply_text, surface, copies = render_reply(reply_family, index, reply_thought)
        for copy in copies:
            if copy['field'] == 'subject' and reply_thought['subject'] is not None:
                reply_thought = dict(reply_thought)
                reply_thought['subject'] = dict(reply_thought['subject'],
                                                span=list(copy['surface_span']))
        return dict(
            i=i,
            user=dict(text=text, thought=user_thought, frame_id=frame.id,
                      opener_id=opener[0] if opener else None,
                      closer_id=closer[0] if closer else None, noise=list(noise),
                      level=self.split),
            reply=dict(text=reply_text, surface=surface, copy=copies,
                       thought=reply_thought,
                       frame_id=f'{reply_family}.{index:03d}'),
            notebook=notebook_record)


def _no_notebook():
    return dict(op='none', row=None, replaced=None, named=[], view_size=None, question=None,
                trace=None, answerable=None, answer_symbol=None, unknown_reason=None,
                unknown_step=None)


def _paths_from(view, symbol, hops):
    """Every answerable relation path of exactly `hops` steps starting at `symbol`."""
    if hops == 1:
        return [[r] for r in RELATIONS if (symbol, RELATION_TOKEN[r]) in view]
    out = []
    nxt = view.get((symbol, LINK))
    if nxt is None:
        return out
    for tail in _paths_from(view, nxt, hops - 1):
        out.append(['friend'] + tail)
    return out


def _name_for(notebook, symbol):
    for name, (_, sym) in notebook.names.items():
        if sym == symbol:
            return name
    return None


def _value_for(symbol):
    for word, token in VALUE_TOKEN.items():
        if token == symbol:
            return word
    return None


# ======================================================== Qwen paraphrases (NO MODEL CALL)
# Section 4.2: about 1,500 paraphrases written WITH PLACEHOLDERS so the label survives and
# Qwen never sees or invents a name.  This is the code path and its verifier only.  Nothing
# in this file calls a model, opens a socket, or spends anything, and `StubClient` is the
# only client that exists.  Running Qwen needs a night on BensPC and Ben's explicit yes
# (design section 7), so it is deliberately not wired up.

PARAPHRASE_PROMPT = """\
You are helping build practice sentences for a very small language model.

Rewrite the SENTENCE below in {n} different ways that a person might really say. Keep the
meaning exactly the same.

Hard rules:
- Keep every placeholder exactly as written and use each one exactly once: {slots}.
- Never replace a placeholder with a real word, a name, or an example.
- Never add a new placeholder.
- Use simple words a seven-year-old knows. One short sentence each. All lower case.
- Do not explain. Output one rewrite per line and nothing else.

The placeholders mean:
{meanings}

SENTENCE: {template}
"""

# Deliberately example-free.  The prompt never shows a real name, a real value word or a
# real relation word, not even as an illustration: a model that has been shown one example
# word tends to use it, and a single leaked literal would ruin the paraphrase for every
# world it is later filled with.
SLOT_MEANINGS = {
    '{OWNER}': "{OWNER} is a person's name; it is hidden from you on purpose",
    '{OWNER_OF}': "{OWNER_OF} is a person's name; it is hidden from you on purpose",
    '{R}': '{R} is the kind of belonging being talked about',
    '{V}': '{V} is the belonging itself',
    '{O}': '{O} is a second person\'s name; it is hidden from you on purpose',
    '{OLD}': '{OLD} is the wrong answer that is being replaced',
    '{O2}': '{O2} is another person\'s name; it is hidden from you on purpose',
    '{R2}': '{R2} is a second kind of belonging',
    '{V2}': '{V2} is a second belonging',
}

DIRECTION_PROMPT = """\
Answer with one word, YES or NO, and nothing else.

Sentence A: {a}
Sentence B: {b}

Does B say exactly the same fact as A, about the same person, in the same direction?
"""


class StubClient:
    """A stand-in for the Qwen client.  It NEVER calls a model.

    `generate` returns canned, deterministic rewrites so the pipeline, the verifier and the
    tests can run end to end offline.  A real client must expose the same two methods; the
    pipeline does not care which it is given, and the run log records which was used.
    """

    name = 'stub'
    calls = 0

    def __init__(self, rewrites=None, answers=None):
        self.rewrites = rewrites or {}
        self.answers = answers or {}

    def generate(self, prompt, n=8):
        self.calls += 1
        key = prompt.split('SENTENCE: ')[-1].strip()
        return list(self.rewrites.get(key, []))[:n]

    def yes_no(self, prompt):
        self.calls += 1
        return self.answers.get(prompt.strip(), 'YES')


def paraphrase_prompt(frame, n=8):
    slots = sorted(set(PLACEHOLDER_RE.findall(frame.template)))
    meanings = '\n'.join(f'- {SLOT_MEANINGS.get(s, s)}' for s in slots)
    return PARAPHRASE_PROMPT.format(n=n, slots=', '.join(slots), meanings=meanings,
                                    template=frame.template)


def verify_paraphrase(candidate, source_frame, rng=None, trials=6):
    """Accept a paraphrase only if the REFERENCE PARSER maps it back to the same label.

    Checks, in order (the first failure is the reason):
      1. every placeholder of the source appears exactly once, and no new one appears;
      2. no literal name, value word or relation word leaked in where a placeholder belongs;
      3. for `trials` random fillings, the parser recovers the same act, the same subject,
         the same relation path and the same object as the source frame filled the same way;
      4. for a person-to-person relation, the direction is right -- the parser must not swap
         subject and object (section 4.2's explicit direction check).
    A candidate that fails is DROPPED, never repaired.
    """
    rng = rng or random.Random(f'{NAMESPACE}:verify:{candidate}')
    want = sorted(PLACEHOLDER_RE.findall(source_frame.template))
    got = sorted(PLACEHOLDER_RE.findall(candidate))
    if got != want:
        return dict(ok=False, reason='placeholders', want=want, got=got)
    lowered = candidate.lower()
    for word in list(VALUE_WORDS) + list(NAME_POOL[:64]) + list(DEFAULT_NAMES):
        if re.search(rf'\b{re.escape(word.lower())}\b', lowered):
            return dict(ok=False, reason='literal_leak', word=word)
    kind = source_frame.relation_kind
    stub = F.Frame(source_frame.family, 999, 'qwen', candidate)
    for _ in range(trials):
        name = rng.choice(NAME_POOL)
        other = rng.choice([n for n in NAME_POOL if n != name])
        relation = 'friend' if kind == 'link' else rng.choice(ATTRIBUTE_RELATIONS)
        value = rng.choice(VALUE_WORDS)
        old = rng.choice([v for v in VALUE_WORDS if v != value]) if kind == 'attr' \
            else rng.choice([n for n in NAME_POOL if n not in (name, other)])
        obj = value_slot(value) if kind == 'attr' else dict(name=other)
        parts = _frame_parts(name, [relation], obj['name'], kind, old)
        want_text, want_spans = render(source_frame.template, parts)
        got_text, got_spans = render(stub.template, parts)
        a, b = P.parse(want_text), P.parse(got_text)
        if a.act != b.act or a.relation_path != b.relation_path:
            return dict(ok=False, reason='label_mismatch', source=want_text, candidate=got_text,
                        source_act=a.act, candidate_act=b.act,
                        source_path=a.relation_path, candidate_path=b.relation_path)
        for field in ('subject', 'object', 'old'):
            x, y = getattr(a, field), getattr(b, field)
            if (x is None) != (y is None):
                return dict(ok=False, reason=f'{field}_missing', source=want_text,
                            candidate=got_text)
            if x is not None and x['name'] != y['name']:
                return dict(ok=False, reason=f'{field}_mismatch', source=want_text,
                            candidate=got_text, source_word=x['name'], candidate_word=y['name'])
        if kind == 'link' and b.subject is not None and b.object is not None:
            if b.subject['name'] != name or b.object['name'] != other:
                return dict(ok=False, reason='direction', candidate=got_text)
    return dict(ok=True, reason=None)


def paraphrase_round(client, frames, n=8, ask_direction=True):
    """One pass: prompt (through whatever client is given), verify, keep or drop.

    Returns the accepted templates and every rejection with its reason, so that a later
    run can report exactly how many of Qwen's rewrites survived and why the rest did not.
    `client` is a StubClient here; passing a real one is a separate, explicitly-approved
    step that has NOT been taken.
    """
    accepted, rejected = [], []
    for frame in frames:
        for candidate in client.generate(paraphrase_prompt(frame, n), n=n):
            verdict = verify_paraphrase(candidate, frame)
            if verdict['ok'] and ask_direction and frame.relation_kind == 'link':
                answer = client.yes_no(DIRECTION_PROMPT.format(a=frame.template, b=candidate))
                if answer.strip().upper() != 'YES':
                    verdict = dict(ok=False, reason='qwen_direction_check')
            if verdict['ok']:
                accepted.append(dict(source=frame.id, template=candidate))
            else:
                rejected.append(dict(source=frame.id, template=candidate, **verdict))
    return dict(accepted=accepted, rejected=rejected, client=client.name, calls=client.calls)


# ================================================================== L3: outside wordings
# Section 4.2: 100 sentences Ben types BEFORE seeing any model output, plus 200 from Qwen
# under a different prompt.  Neither exists yet, on purpose.  Everything around them does.

L3_BEN = 'l3-ben.txt'
L3_QWEN = 'l3-qwen.jsonl'
L3_EXPECT = {L3_BEN: 100, L3_QWEN: 200}


def normalise_case(text, lexicon=P.LEXICON):
    """Ben types normally; the corpus is lower case except names.  Supplied rule, declared.

    A capitalised word the published word list has never seen is a NAME and keeps its
    capital; every other word is lower-cased.  Exactly section 2.1's rule, run backwards.
    """
    out, cursor = [], 0
    for match in re.finditer(r"[A-Za-z]+(?:'[A-Za-z]+)?", text):
        out.append(text[cursor:match.start()])
        word = match.group(0)
        base = word.split("'")[0]
        out.append(word if (base[:1].isupper() and base.lower() not in lexicon)
                   else word.lower())
        cursor = match.end()
    out.append(text[cursor:])
    return ''.join(out)


def load_l3(folder):
    """Read the sealed outside-wording slot.  Empty is a valid, expected state."""
    folder = Path(folder)
    items, notes = [], {}
    ben = folder/L3_BEN
    if ben.exists():
        lines = [line.strip() for line in ben.read_text().splitlines()
                 if line.strip() and not line.startswith('#')]
        items += [dict(source='ben', index=i, text=normalise_case(line), raw=line)
                  for i, line in enumerate(lines)]
        notes[L3_BEN] = len(lines)
    qwen = folder/L3_QWEN
    if qwen.exists():
        rows = [json.loads(line) for line in qwen.read_text().splitlines() if line.strip()]
        items += [dict(source='qwen', index=i, text=normalise_case(row['text']), raw=row['text'],
                       meta=row) for i, row in enumerate(rows)]
        notes[L3_QWEN] = len(rows)
    return dict(items=items, counts=notes, complete=all(
        notes.get(name, 0) >= want for name, want in L3_EXPECT.items()))


L3_TODO = """\
# TODO -- the L3 "outside wording" set is EMPTY ON PURPOSE

L3 is the only wording level that does not come from our grammar.  Design section 4.2:

| file | who writes it | how many | state |
|---|---|---|---|
| `l3-ben.txt` | **Ben**, by hand, one sentence per line | 100 | **empty -- waiting for Ben** |
| `l3-qwen.jsonl` | Qwen on BensPC, a different prompt ("how might a person casually say this?") | 200 | **empty -- needs a Qwen night and Ben's yes** |

## Rules that make this set worth anything

1. **Ben types his 100 before he ever sees a model output.** If he writes them after seeing
   what the model gets wrong, L3 stops measuring "wordings from outside the grammar" and
   starts measuring "wordings Ben knows are hard". Roughly 20 minutes of his time.
2. **Nothing here is ever trained on.** Not one sentence, not a paraphrase of one.
3. **Both files are hashed the moment they are filled** (`seal` writes the hashes into
   `SEALED-SPLITS.md`), and the hashes go in the run log of every evaluation that uses them.
4. If a failed L3 wording is later added to the grammar (design section 5, S3), that must be
   declared and **a fresh set of sealed L3 sentences is needed** -- the old ones are burnt.

## What Ben should write

Ordinary sentences that teach, ask, correct or chat -- in his own words, not the grammar's.
Names may be anything capitalised. Only the four relations (`friend`, `gift`, `prize`,
`charm`) and the sixteen values (`drum kite lamp rope coin flute brush candle mirror ladder
kettle basket ribbon feather pebble whistle`) exist, because the frozen operator has no
other symbols. A rough mix, not a rule: 35 teaching, 30 asking (some two-step), 10
correcting, 15 small talk, 10 things it cannot possibly know.

## Format

`l3-ben.txt` -- one sentence per line, `#` comments allowed, blank lines ignored. Case is
normalised on load by `fable_talker24_dialogues.normalise_case`, which keeps a capitalised
word as a NAME only when the published lexicon has never seen it.

`l3-qwen.jsonl` -- one JSON object per line: `{"text": "...", "prompt_id": "...",
"model": "...", "seed": 0}`.

The loader is `fable_talker24_dialogues.load_l3(folder)`. It returns
`{"items": [...], "counts": {...}, "complete": false}` today and needs no change when the
files arrive.
"""


# ===================================================================== chat safety screen

# The closed-world content words, and only those.  Ordinary verbs ("has", "got", "gave")
# are deliberately NOT here: they appear in harmless small talk ("i got up late") and in
# the closers the grammar already uses ("..., got it?").  What makes a line look like a
# fact is a RELATION or a VALUE, or a name with nothing to anchor it.
CHAT_FORBIDDEN = frozenset(RELATIONS) | frozenset(VALUE_WORDS) | {
    'friends', 'gifts', 'prizes', 'charms', 'belongs', 'belonging'}


def chat_is_safe(text, extra_names=()):
    """Is this line safe to use as small talk?  Returns (ok, [reasons]).

    Generated chat already satisfies this by construction.  The screen exists for the day
    someone splices chat in from a real corpus (INTERFACE-dialogues.md says to call this
    first).  A chat turn must not look like a fact, because its gold thought says CHAT and
    the notebook must stay untouched; if a spliced line says "ana has a red hat" the label
    is a lie and the router learns that facts are sometimes ignorable.

    Three ways a line fails:
      * it contains a relation word or a value word, in any form we know of;
      * it contains a capitalised token the word list has never seen -- i.e. the supplied
        name rule would read it as a person, and a name in chat with no copy slot is
        exactly the hallucination we designed the copy actions to make impossible;
      * the reference parser does not read it as CHAT.
    """
    reasons = []
    words = re.findall(r"[A-Za-z']+", text)
    hits = sorted({w.lower() for w in words if w.lower() in CHAT_FORBIDDEN})
    if hits:
        reasons.append('fact vocabulary: ' + ', '.join(hits))
    allowed = {str(n).lower() for n in extra_names}
    names = sorted({w for i, w in enumerate(words)
                    if P.is_name_word(w) and w.lower() not in allowed
                    and not (i == 0 and w.lower() in P.LEXICON)})
    if names:
        reasons.append('unregistered name-looking word: ' + ', '.join(names))
    read = P.parse(text)
    if read.act != 'CHAT':
        reasons.append(f'the reference parser reads this as {read.act}, not CHAT')
    return (not reasons), reasons


# ============================================================================ file helpers

def sha_bytes(blob):
    return hashlib.sha256(blob).hexdigest()


def sha_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def write_atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f'.{path.name}.', suffix='.tmp')
    try:
        with os.fdopen(handle, 'w') as out:
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return path


def dumps(record):
    return json.dumps(record, sort_keys=True, separators=(',', ':'))


def stream(out_path, split, n, start=0, symbol_mode='m0', pool='train', progress=None):
    """Write `n` dialogues to a JSONL file.  Returns (turns, seconds, sha256)."""
    generator = Generator(split=split, symbol_mode=symbol_mode, pool=pool)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    started, turns = time.time(), 0
    with open(out_path, 'w') as handle:
        for i in range(start, start + n):
            record = generator.dialogue(i)
            turns += len(record['turns'])
            handle.write(dumps(record) + '\n')
            if progress and (i - start + 1) % progress == 0:
                done = i - start + 1
                rate = done/(time.time() - started)
                print(f'  {done}/{n} dialogues  {rate:,.0f}/s', flush=True)
    return turns, time.time() - started, sha_file(out_path)


# ======================================================= generator / parser agreement

COMPARED_FIELDS = ('act', 'subject', 'relation_path', 'object', 'old', 'path_len', 'teachable')


def label_key(turn_thought, text):
    """The generator's label, reduced to exactly what a parser could see in the text."""
    def slot(item):
        if item is None:
            return None
        span = item.get('span')
        return (item['name'], tuple(span) if span else None)
    return (turn_thought['act'],
            slot(turn_thought['subject']),
            tuple(turn_thought['relation_path']),
            None if turn_thought['object'] is None
            else (turn_thought['object']['name'], turn_thought['object']['kind'],
                  tuple(turn_thought['object']['span'])),
            slot(turn_thought['old']),
            turn_thought['flags']['path_len'],
            turn_thought['flags']['teachable'])


def parser_key(thought_obj):
    def slot(item):
        if item is None:
            return None
        return (item['name'], tuple(item['span']))
    return (thought_obj.act,
            slot(thought_obj.subject),
            tuple(thought_obj.relation_path),
            None if thought_obj.object is None
            else (thought_obj.object['name'], thought_obj.object['kind'],
                  tuple(thought_obj.object['span'])),
            slot(thought_obj.old),
            len(thought_obj.relation_path),
            thought_obj.teachable)


def agreement(split='L1', n=2000, symbol_mode='m0', report=20):
    """Generate `n` dialogues and ask the parser to read every user turn back."""
    generator = Generator(split=split, symbol_mode=symbol_mode)
    total = match = 0
    by_act, disagreements = {}, []
    for i in range(n):
        for turn in generator.dialogue(i)['turns']:
            text = turn['user']['text']
            gold = label_key(turn['user']['thought'], text)
            read = parser_key(P.parse(text))
            act = turn['user']['thought']['act']
            slot = by_act.setdefault(act, dict(n=0, ok=0))
            slot['n'] += 1
            total += 1
            if gold == read:
                slot['ok'] += 1
                match += 1
            elif len(disagreements) < report:
                disagreements.append(dict(dialogue=i, turn=turn['i'], text=text,
                                          frame=turn['user']['frame_id'],
                                          gold=str(gold), parsed=str(read)))
    return dict(n=total, match=match, rate=match/total if total else 0.,
                by_act={a: dict(v, rate=v['ok']/v['n']) for a, v in sorted(by_act.items())},
                disagreements=disagreements)


def notebook_check(split='L1', n=1000, symbol_mode='m0'):
    """Every lookup in every dialogue, re-computed by the independent dictionary walk."""
    generator = Generator(split=split, symbol_mode=symbol_mode)
    checked = mismatched = 0
    examples = []
    for i in range(n):
        record = generator.dialogue(i)
        appends = []
        for turn in record['turns']:
            note = turn['notebook']
            if note['op'] == 'append':
                row = note['row']
                appends.append((row[1], row[2], row[3]))
            elif note['op'] == 'lookup':
                path = turn['user']['thought']['relation_path']
                subject = turn['user']['thought']['subject']['symbol']
                answer, step = dictionary_walk(appends, subject, path)
                checked += 1
                same = (answer == note['answer_symbol']
                        and (answer is not None) == bool(note['answerable'])
                        and step == note['unknown_step'])
                if not same:
                    mismatched += 1
                    if len(examples) < 10:
                        examples.append(dict(dialogue=i, turn=turn['i'],
                                             walk=(answer, step),
                                             record=(note['answer_symbol'],
                                                     note['unknown_step'])))
        # the replay check: the final view must be reproducible from the appends alone
        view = {}
        for subject, relation, obj in appends:
            view[(subject, relation)] = obj
        replay = {f'{s},{r}': o for (s, r), o in view.items()}
        if replay != record['final_view']:
            mismatched += 1
            if len(examples) < 10:
                examples.append(dict(dialogue=i, turn='final_view'))
    return dict(checked=checked, mismatched=mismatched, examples=examples)


# ================================================================================== CLI

def cmd_frames(args):
    total = 0
    print(f'{"family":16s} {"frames":>7s} {"L1":>5s} {"L2":>4s} {"constr":>7s} '
          f'{"L2-novel":>9s}')
    for family, row in F.construction_report().items():
        total += row['n_frames']
        print(f'{family:16s} {row["n_frames"]:7d} {row["n_l1"]:5d} {row["n_l2"]:4d} '
              f'{row["n_constructions"]:7d} {row["l2_construction_novel"]:9d}  '
              f'{",".join(row["novel_constructions"])}')
    print(f'{"TOTAL":16s} {total:7d}   openers {len(F.OPENERS)} '
          f'(L2 {len(F.SPLIT["openers"]["L2"])})  closers {len(F.CLOSERS)} '
          f'(L2 {len(F.SPLIT["closers"]["L2"])})')
    print('\nreply frames per reply act:')
    for act, n in sorted(reply_frame_counts().items()):
        print(f'  {act:10s} {n}')
    print(f'\nframe table sha256  {F.frame_table_sha256()}')
    return 0


def cmd_split(args):
    out = Path(args.out)
    payload = dict(
        format=F.FORMAT, split_namespace=F.SPLIT_NAMESPACE,
        held_out_share=F.HELD_OUT_SHARE, frame_table_sha256=F.frame_table_sha256(),
        families={family: dict(
            L1=rows['L1'], L2=rows['L2'],
            templates={f.id: f.template for f in F.FRAMES.get(family, [])},
            constructions={f.id: f.construction for f in F.FRAMES.get(family, [])})
            for family, rows in F.SPLIT.items()},
        openers=dict(zip([f'op.{i:02d}' for i in range(len(F.OPENERS))], F.OPENERS)),
        closers=dict(zip([f'cl.{i:02d}' for i in range(len(F.CLOSERS))], F.CLOSERS)),
        construction_report=F.construction_report(),
        reply_frames={family: frames for family, frames in REPLY_FAMILIES.items()},
        noise=dict(ops=list(F.NOISE_OPS), weights=list(F.NOISE_WEIGHTS)))
    write_atomic(out/'dialogues/frame-split.json',
                 json.dumps(payload, indent=1, sort_keys=True) + '\n')
    write_atomic(out/'dialogues/LEXICON.json', json.dumps(dict(
        format=P.FORMAT, note='the published word list the supplied name rule uses: a '
        'capitalised token whose lower-case form is NOT here is a name',
        relations=list(P.RELATIONS), values=list(P.VALUES),
        words=sorted(P.LEXICON)), indent=1, sort_keys=True) + '\n')
    write_atomic(out/'dialogues/L3/TODO-L3.md', L3_TODO)
    for name in (L3_BEN, L3_QWEN):
        path = out/'dialogues/L3'/name
        if not path.exists():
            write_atomic(path, '')
    print(f'wrote {out/"dialogues/frame-split.json"}')
    print(f'wrote {out/"dialogues/LEXICON.json"}')
    print(f'wrote {out/"dialogues/L3/TODO-L3.md"} and two empty L3 slots')
    return 0


def cmd_generate(args):
    turns, seconds, digest = stream(args.out, args.split, args.n, args.start,
                                    args.symbol_mode, args.pool, args.progress)
    size = Path(args.out).stat().st_size
    print(json.dumps(dict(out=args.out, split=args.split, n=args.n, start=args.start,
                          turns=turns, seconds=round(seconds, 2),
                          dialogues_per_second=round(args.n/seconds, 1),
                          turns_per_second=round(turns/seconds, 1),
                          bytes=size, sha256=digest), indent=1))
    return 0


def _meta(path, split, n, turns, seconds, symbol_mode):
    return dict(format=FORMAT, file=path.name, split=split, dialogues=n, turns=turns,
                symbol_mode=symbol_mode, namespace=NAMESPACE,
                seed_key_shape=f'{NAMESPACE}:{split}:<index>', start_index=0,
                seconds=round(seconds, 2), bytes=path.stat().st_size,
                sha256=sha_file(path), frame_table_sha256=F.frame_table_sha256(),
                parser_format=P.FORMAT,
                sealed_before_any_model='yes -- no talker model exists at the time of writing')


def cmd_seal(args):
    out = Path(args.out)
    cmd_split(args)
    files = {}
    for split in ('L1', 'L2'):
        path = out/f'dialogues/{split}-test.jsonl'
        turns, seconds, digest = stream(path, split, args.n, 0, args.symbol_mode)
        meta = _meta(path, split, args.n, turns, seconds, args.symbol_mode)
        write_atomic(path.with_suffix('.meta.json'),
                     json.dumps(meta, indent=1, sort_keys=True) + '\n')
        files[path.name] = meta
        print(f'  {path.name}: {args.n} dialogues, {turns} turns, sha256 {digest[:16]}')
    agree = agreement('L1', args.check) if args.check else None
    agree2 = agreement('L2', args.check) if args.check else None
    notes = notebook_check('L1', args.check) if args.check else None
    write_atomic(out/'SEALED-SPLITS.md',
                 sealed_markdown(out, files, agree, agree2, notes, args.n))
    print(f'wrote {out/"SEALED-SPLITS.md"}')
    return 0


def sealed_markdown(out, files, agree, agree2, notes, n):
    report = F.construction_report()
    lines = [
        '# SEALED SPLITS — talker practice dialogues',
        '',
        f'Generated by `scripts/fable_talker24_dialogues.py seal --n {n}` on '
        f'{time.strftime("%Y-%m-%d %H:%M:%S")} local time.',
        '',
        '**Sealed before any model existed.** At the moment these hashes were written there '
        'was no talker model, no tokenizer and no training run of any kind in this project; '
        'build task 3 (model and trainer) is being written in parallel and has never seen '
        'this data. Nothing in these files was chosen by looking at a model output.',
        '',
        '## Files and hashes',
        '',
        '| file | what it is | bytes | sha256 |',
        '|---|---|---|---|',
    ]
    for name, meta in sorted(files.items()):
        lines.append(f'| `dialogues/{name}` | {meta["dialogues"]} dialogues, '
                     f'{meta["turns"]} turns, level {meta["split"]} | {meta["bytes"]:,} | '
                     f'`{meta["sha256"]}` |')
    for extra, what in (('dialogues/frame-split.json', 'the sealed L1/L2 frame split'),
                        ('dialogues/LEXICON.json', 'the published word list'),
                        ('dialogues/L3/TODO-L3.md', 'what still has to be written by hand'),
                        ('dialogues/L3/l3-ben.txt', 'EMPTY — Ben types 100 sentences'),
                        ('dialogues/L3/l3-qwen.jsonl', 'EMPTY — 200 Qwen paraphrases'),
                        ('INTERFACE-dialogues.md', 'the data format')):
        path = out/extra
        if path.exists():
            lines.append(f'| `{extra}` | {what} | {path.stat().st_size:,} | '
                         f'`{sha_file(path)}` |')
    lines += ['',
              f'Frame table sha256 (every core frame, opener and closer, in sealed order): '
              f'`{F.frame_table_sha256()}`', '',
              '## The three wording levels (design §4.2)', '',
              '| level | what is new at test time | state |',
              '|---|---|---|',
              '| **L1** | new people, values and worlds in **seen** frames | built |',
              '| **L2** | **held-out frames** (20 % of core frames, split by frame) plus 2 of '
              '12 openers and 2 of 8 closers never trained | built |',
              '| **L3** | wordings from **outside the grammar** — 100 typed by Ben before he '
              'sees any model output, 200 from Qwen under a different prompt | **empty on '
              'purpose**, see `dialogues/L3/TODO-L3.md` |', '',
              '## Frames per (act × relation kind)', '',
              '| family | frames | L1 | L2 | constructions | L2 frames whose construction '
              'never appears in L1 |',
              '|---|---|---|---|---|---|']
    for family, row in report.items():
        lines.append(f'| `{family}` | {row["n_frames"]} | {row["n_l1"]} | {row["n_l2"]} | '
                     f'{row["n_constructions"]} | {row["l2_construction_novel"]} '
                     f'({", ".join(row["novel_constructions"]) or "none"}) |')
    lines += ['',
              'The last column is the honest measure of how new "new wording" really is. The '
              'design specifies a split **by frame**, which can hand L2 a frame that differs '
              'from a training frame only in its lead-in; that column counts the held-out '
              'frames that are built on a sentence construction the model will never have '
              'seen at all.', '',
              '## Structural disjointness', '',
              'Proved by `tests/test_fable_talker24_dialogues.py`: no frame id is in both '
              'levels, no two frames anywhere share a template string, and no L2 template '
              'equals an L1 template after stripping placeholders, punctuation and case. The '
              'opener and closer splits are disjoint in the same way.', '']
    if agree:
        lines += ['## Generator / parser agreement, measured at sealing time', '',
                  '| set | user turns read back | identical labels | rate |',
                  '|---|---|---|---|',
                  f'| L1 | {agree["n"]:,} | {agree["match"]:,} | {agree["rate"]:.4%} |',
                  f'| L2 | {agree2["n"]:,} | {agree2["match"]:,} | {agree2["rate"]:.4%} |', '',
                  'The reference parser reads characters only; it imports nothing from the '
                  'generator or the frame table. It cannot see `unknown_reason` or '
                  '`unknown_step`, which are properties of the notebook, so those are checked '
                  'separately:', '',
                  f'* notebook lookups re-computed by an independent dictionary walk: '
                  f'**{notes["checked"]:,} checked, {notes["mismatched"]} disagreements**.', '']
    lines += ['## What these hashes do and do not promise', '',
              '* They promise that the evaluation sets were fixed before any model saw them.',
              '* They do **not** promise that the grammar covers English. L1 and L2 are both '
              'our own wordings; only L3, which Ben has not written yet, tests that.',
              '* They do **not** promise the labels match human judgement — only that two '
              'independently written pieces of code agree about them.', '']
    return '\n'.join(lines) + '\n'


def cmd_samples(args):
    out = Path(args.out)
    generator = Generator(split=args.split)
    picks = [generator.dialogue(i) for i in range(args.n)]
    lines = ['# SAMPLES — 20 generated practice dialogues', '',
             f'Straight from `scripts/fable_talker24_dialogues.py generate --split '
             f'{args.split}`, indices 0–{args.n - 1}, nothing chosen by hand and nothing '
             'edited. `you:` is the generated user turn, `it:` is what the printer would '
             'say, and `mouth:` is what the decoder is actually trained to produce — note '
             'that no name or value word ever appears there, only the copy actions '
             '`<SUBJ>` `<OBJ>` `<OLD>`.', '']
    for record in picks:
        people = ', '.join(f'{p["name"]}={p["symbol"]}' for p in record['world']['people'])
        lines += [f'## `{record["id"]}`  ({record["world"]["n_people"]} people: {people})', '',
                  '```']
        for turn in record['turns']:
            note, gold = turn['notebook'], turn['user']['thought']
            path = '/'.join(gold['relation_path']) or '-'
            subject = gold['subject']['name'] if gold['subject'] else '-'
            lines.append(f'you:   {turn["user"]["text"]}')
            lines.append(f'       [{gold["act"]:7s} subj={subject:6s} path={path:18s} '
                         f'{_note_line(note)}]')
            lines.append(f'it:    {turn["reply"]["surface"]}')
            lines.append(f'mouth: {turn["reply"]["text"]}')
            lines.append('')
        lines += ['```', '']
    write_atomic(out/'SAMPLES.md', '\n'.join(lines))
    print(f'wrote {out/"SAMPLES.md"}  ({args.n} dialogues)')
    return 0


def _note_line(note):
    if note['op'] == 'append':
        return f'row={note["row"]}' + (' REPLACES' if note['replaced'] else '')
    if note['op'] == 'lookup':
        if note['answerable']:
            return f'lookup->{note["answer_symbol"]} in {len(note["trace"])} step(s)'
        return f'UNKNOWN {note["unknown_reason"]}'
    return 'notebook untouched'


def cmd_selftest(args):
    print(f'frames: {sum(len(v) for v in F.FRAMES.values())} core, '
          f'{sum(len(v) for v in REPLY_FAMILIES.values())} reply')
    for split in ('L1', 'L2'):
        result = agreement(split, args.n)
        print(f'\n{split}: {result["match"]:,}/{result["n"]:,} '
              f'= {result["rate"]:.4%} of user turns read back identically')
        for act, row in result['by_act'].items():
            print(f'    {act:8s} {row["ok"]:6d}/{row["n"]:6d}  {row["rate"]:.4%}')
        for bad in result['disagreements'][:args.show]:
            print(f'    MISMATCH {bad["frame"]}  {bad["text"]!r}')
            print(f'      gold   {bad["gold"]}')
            print(f'      parsed {bad["parsed"]}')
    notes = notebook_check('L1', max(200, args.n//4))
    print(f'\nnotebook vs dictionary walk: {notes["checked"]:,} lookups, '
          f'{notes["mismatched"]} disagreements')
    for bad in notes['examples'][:5]:
        print(f'    {bad}')
    started = time.time()
    generator, turns = Generator('L1'), 0
    for i in range(args.throughput):
        turns += len(generator.dialogue(i)['turns'])
    seconds = time.time() - started
    print(f'\nthroughput (in memory, single process): {args.throughput/seconds:,.0f} '
          f'dialogues/s, {turns/seconds:,.0f} turns/s')
    return 0


def cmd_paraphrase_plan(args):
    out = Path(args.out)
    frames = [F.FRAMES[family][0] for family in F.FACT_FAMILIES]
    payload = dict(
        note='PROMPT TEMPLATES ONLY. No model was called. A Qwen night needs Ben\'s yes '
             '(design section 7) and blocks training on BensPC while it runs.',
        paraphrase_prompt=PARAPHRASE_PROMPT, direction_prompt=DIRECTION_PROMPT,
        slot_meanings=SLOT_MEANINGS, target_paraphrases=1500,
        examples={frame.id: paraphrase_prompt(frame) for frame in frames},
        verifier=dict(
            checks=['placeholders present exactly once and none added',
                    'no literal name, value or relation word leaked into a slot',
                    'the reference parser recovers the same act, subject, relation path, '
                    'object and old value on six random fillings',
                    'person-to-person relations keep their direction',
                    'a yes/no Qwen check that B says exactly the fact A says'],
            on_failure='the paraphrase is dropped, never repaired'),
        client='stub -- StubClient never calls a model')
    write_atomic(out/'QWEN-PARAPHRASE-PLAN.json',
                 json.dumps(payload, indent=1, sort_keys=True) + '\n')
    print(f'wrote {out/"QWEN-PARAPHRASE-PLAN.json"} (no model was called)')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('frames'); p.set_defaults(handler=cmd_frames)
    p = sub.add_parser('split'); p.add_argument('--out', default=str(OUT))
    p.set_defaults(handler=cmd_split)
    p = sub.add_parser('generate')
    p.add_argument('--out', required=True)
    p.add_argument('--split', default='L1', choices=('L1', 'L2'))
    p.add_argument('--n', type=int, default=1000)
    p.add_argument('--start', type=int, default=0)
    p.add_argument('--symbol-mode', dest='symbol_mode', default='m0', choices=('m0', 'pool'))
    p.add_argument('--pool', default='train', choices=('train', 'reserved'))
    p.add_argument('--progress', type=int, default=0)
    p.set_defaults(handler=cmd_generate)
    p = sub.add_parser('seal')
    p.add_argument('--out', default=str(OUT))
    p.add_argument('--n', type=int, default=1000)
    p.add_argument('--check', type=int, default=1000)
    p.add_argument('--symbol-mode', dest='symbol_mode', default='m0', choices=('m0', 'pool'))
    p.set_defaults(handler=cmd_seal)
    p = sub.add_parser('samples')
    p.add_argument('--out', default=str(OUT))
    p.add_argument('--split', default='L1', choices=('L1', 'L2'))
    p.add_argument('--n', type=int, default=20)
    p.set_defaults(handler=cmd_samples)
    p = sub.add_parser('selftest')
    p.add_argument('--n', type=int, default=2000)
    p.add_argument('--show', type=int, default=5)
    p.add_argument('--throughput', type=int, default=2000)
    p.set_defaults(handler=cmd_selftest)
    p = sub.add_parser('paraphrase-plan')
    p.add_argument('--out', default=str(OUT))
    p.set_defaults(handler=cmd_paraphrase_plan)

    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == '__main__':
    raise SystemExit(main())
