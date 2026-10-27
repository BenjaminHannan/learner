"""Build task 2, part B -- the RULE-BASED REFERENCE PARSER.

English sentence -> the typed part of a thought (act, subject, relation path, object, old
value, path length).  It is the ground-truth checker for the generator: if the generator
says a sentence means X and this parser, reading only the characters, also says X, then the
label is right for a reason that does not depend on the generator being correct.

INDEPENDENCE, stated precisely and honestly.
  * This module imports NOTHING from the generator or the frame table.  It never sees a
    frame id, a construction tag, a placeholder, or the world a sentence came from.  Its
    only inputs are the sentence and (optionally) a symbol table -- the same supplied symbol
    table the running system has (design section 4.3).
  * It is NOT independent in the stronger sense of having been written by someone who had
    never seen the grammar.  The frames and these rules were written in the same session by
    the same builder against a shared, documented inventory of English constructions.  So
    "generator label == parser label" proves the two agree; it does not prove the grammar
    covers English.  That is what the L3 set (sentences Ben types himself) is for, and it is
    deliberately empty until he writes it.

WHAT IT CANNOT RECOVER.  `unknown_reason` and `unknown_step` are properties of the NOTEBOOK,
not of the sentence.  The parser never guesses them; the notebook simulator produces them and
they are checked separately against a direct dictionary walk.

THE CONSTRUCTION INVENTORY it handles (the documented contract with the grammar):
  possessive chain      NAME's (REL's)* REL         "Mira's friend's gift"
  of chain              the REL of|for OWNER        "the gift of the friend of Mira"
                        the REL belonging to OWNER
  relative clause       the REL that NAME has|got|keeps|received
  trailing relation     ... as|for a|his|her|their REL   "got a drum as a gift"
  topic reference       about|as for|speaking of NAME, ... the REL ...
  wh question           who|what|which|whose ...
  auxiliary question    do you know / do you remember / can|could you tell me / any idea /
                        any chance you know / tell me / remind me / look up / i wonder /
                        i forget / i cannot remember / i want to know / what about / how about
  correction marker     actually / no, / sorry / oops / correction / scratch that /
                        forget that / ignore that / i meant / i was wrong / that was wrong /
                        i made a mistake / let me fix / let me change / please change /
                        update / change it / change X to Y / make X Y / set X to Y / instead
  negated old value     is not (a) OLD ... / is no longer (a) OLD ... / does not have OLD
  unclear triggers      pronoun possessive before a relation, two owner-chains each with an
                        object, a relation phrase with no owner at all, gibberish tokens
"""
from __future__ import annotations

import re

FORMAT = 'fable-talker24-parser/1'

# ------------------------------------------------- the published closed-world vocabulary
# Exactly M0's (scripts/fable_notebook_m0.py); repeated here so the parser stands alone.
RELATIONS = ('friend', 'gift', 'prize', 'charm')
LINK_RELATION = 'friend'
VALUES = ('drum', 'kite', 'lamp', 'rope', 'coin', 'flute', 'brush', 'candle',
          'mirror', 'ladder', 'kettle', 'basket', 'ribbon', 'feather', 'pebble', 'whistle')
RELATION_SET, VALUE_SET = frozenset(RELATIONS), frozenset(VALUES)

# ------------------------------------------------------------------- the published lexicon
# Section 2.1's name rule needs a word list: "a capitalised word the word list has never
# seen" is a name.  This is that list -- every non-name word the published grammar can emit.
# It is a SUPPLIED artefact, published as LEXICON.json beside the data.  A test asserts that
# the generator never emits a lower-case word outside it.
LEXICON = frozenset("""
a about add after again alright also am an and animal another any anyway are as at
back bake be became bed been before belonging big bike bird birds blue bones book bored
born both boiling but by bake
can cannot capital cats century change charm choose chose clean cleaned close cold colour
correction could countries country
day deep did dinner discovered do does dog dogs down
earth eight engine ended evening ever
famous fast fastest favourite fine first fix fly for forget found fun funny
game garden get give gave go going good got green
had happen happened happy has have having hey hi hello helped here him his hmm home how
hungry
i if ignore in instead into invented is it italy its
japan just
keep keeps kenya kept king know
large largest last later let light like listen little live long longest look love lunch
made make many me mean means meant mistake moon more morning mountain my
new news night nine no north not note now
oceans ocean of oh ok old on one oops or other outside over
painted park people peru picture pizza place plane play played please point press printing
prize put
rain raining read remember remind right river room root
sad said salty say says school sea see set seven shape she shop should sky sleep small
smallest sorry sounds south spain speaking speed spell square stars stay summer sun sunny
tall tallest telephone tell thank thanks that the their them then there these they thing
think this those three time times to today told tomorrow took turned
um up update us very
walk walked walks want war was watched water we weather well went were what whats when
where which while who whos whose why will with word world would write wrote
year yes you your yours
""".split())
# Words the grammar uses that are also ordinary sentence openers; kept out of the name rule.
LEXICON = LEXICON | RELATION_SET | VALUE_SET | frozenset((
    'actually', 'scratch', 'corrected', 'longer', 'mine', 'bit', 'while', 'her', 'their',
    'him', 'wonder', 'chance', 'idea', 'ok', 'okay', 'oops', 'listen', 'anyway', 'hmm',
    'um', 'so', 'right', 'well', 'hey', 'oh', 'by', 'the', 'and', 'or', 'nor',
    # every remaining word the frame table can emit; a test asserts this list is complete
    'america', 'body', 'bread', 'bulb', 'doing', 'fact', 'far', 'france', 'given',
    'happens', 'nice', 'out', 'person', 'pick', 'picked', 'received', 's', 'someone',
    'talk', 'telling', 'tired', 'way', 'won', 'work', 'wrong'))

VOWELS = frozenset('aeiouy')

PRONOUN_POSSESSIVES = frozenset(('his', 'her', 'their', 'its', 'my', 'our', 'your'))
HAVE_VERBS = frozenset(('has', 'got', 'keeps', 'received', 'owns', 'had', 'have', 'kept'))
DETERMINERS = frozenset(('the', 'a', 'an'))
TRAILING_DETS = frozenset(('a', 'an', 'the', 'his', 'her', 'their', 'its'))

# discourse lead-ins the parser strips before it decides anything.  A superset of the
# grammar's openers by shape: up to four words ending in a comma.
OPENER_WORDS = frozenset(('ok', 'okay', 'so', 'by', 'the', 'way', 'hey', 'right', 'well',
                          'anyway', 'oh', 'listen', 'um', 'alright', 'hmm', 'and'))
# trailing tags.  "got it?" would otherwise turn a statement into a question.
CLOSER_RE = re.compile(
    r",\s*(ok|okay|alright|right|please|thanks|thank you|got it|if you can|"
    r"please remember that|write that down|remember that|can you)\s*[.?!]*\s*$")

CORRECTION_MARKERS = (
    'actually', 'no', 'sorry', 'oops', 'correction', 'a correction', 'small correction',
    'scratch that', 'forget that', 'ignore that', 'i meant', 'i meant to say',
    'what i meant was', 'i was wrong', 'that was wrong', 'i made a mistake',
    'let me fix that', 'let me change that', 'please change that', 'update', 'an update',
    'change it')
# corrections that are not a lead-in but a whole imperative shape
CORRECTION_SHAPES = (re.compile(r'^(please\s+)?change\s+'), re.compile(r'^make\s+'),
                     re.compile(r'^set\s+'))
CORRECTION_TAIL = re.compile(r'\b(instead|i corrected that|no longer)\b')

WH_WORDS = frozenset(('who', 'what', 'which', 'whose', 'whos', 'whats',
                      'how', 'when', 'why', 'where'))
ASK_LEADS = ('do you know', 'do you remember', 'can you tell me', 'could you tell me',
             'can you look up', 'tell me', 'remind me', 'look up', 'i wonder', 'i forget',
             'i cannot remember', 'i want to know', 'any idea', 'any chance you know',
             'what about', 'how about', 'do you have')

# Section 4.4 case 3 ("a question about the world") vs ordinary small talk.  Both are
# sentences with no person and no relation in them, so the notebook cannot answer either;
# the only difference is whether the user is asking ABOUT THE ASSISTANT (chat) or about
# something outside the room (an unanswerable question).  There is no structural cue for
# that, so this is an openly hand-written heuristic: a question that opens by addressing
# the assistant is chat, anything else is an unanswerable question.  Declared as a
# heuristic in the report; it is the one place the parser encodes taste rather than syntax.
CHAT_QUESTION_LEADS = ('how are you', 'how is it going', 'how was your', 'what are you',
                       'what do you', 'what is your', "what's your", 'do you like',
                       'do you sleep', 'are you', 'can you see', 'do you want')
# ...except when the assistant is being addressed as a lookup service.
FACT_LEAD_EXCEPTIONS = ('do you know', 'do you remember', 'can you tell me',
                        'could you tell me', 'can you look up', 'any chance you know')
WORLD_MARKERS = ('capital of', 'invented', 'discovered', 'how far', 'how tall', 'how deep',
                 'how big', 'how old is the', 'how many', 'when was', 'when did',
                 'what year', 'why is the', 'why is', 'why do birds', 'why does the moon',
                 'largest', 'fastest', 'longest', 'smallest', 'boiling point',
                 'speed of light', 'how do you spell', 'what does that long word',
                 'times eight', 'square root', 'in the news', 'the weather tomorrow',
                 'who won the game', 'what time does the shop', 'how do you bake',
                 'how do you fix', 'how does an engine', 'how does a plane',
                 'what happened in the', 'first person on the moon', 'who wrote that',
                 'who painted that')

TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|[0-9]+|[^\sA-Za-z0-9]")


class Token:
    __slots__ = ('text', 'lower', 'start', 'end')

    def __init__(self, text, start, end):
        self.text, self.start, self.end = text, start, end
        self.lower = text.lower()

    @property
    def stem(self):
        """The word without a trailing possessive `'s`."""
        return self.lower[:-2] if self.lower.endswith("'s") else self.lower

    def __repr__(self):
        return f'Token({self.text!r})'


def tokenize(text):
    return [Token(m.group(0), m.start(), m.end()) for m in TOKEN_RE.finditer(text)]


def is_name_word(word):
    """The supplied name rule: capitalised, and the word list has never seen it."""
    if not word or not word[0].isupper():
        return False
    return word.lower() not in LEXICON


def is_name(tok):
    return is_name_word(tok.text.split("'")[0]) and not tok.lower.endswith("'s")


def is_name_poss(tok):
    return tok.lower.endswith("'s") and is_name_word(tok.text[:-2])


def name_of(tok):
    return tok.text[:-2] if tok.lower.endswith("'s") else tok.text


def name_span(tok):
    end = tok.end - 2 if tok.lower.endswith("'s") else tok.end
    return (tok.start, end)


def is_rel(tok):
    return tok.lower in RELATION_SET


def is_rel_poss(tok):
    return tok.lower.endswith("'s") and tok.stem in RELATION_SET


def is_value(tok):
    return tok.lower in VALUE_SET


def looks_like_gibberish(tok):
    """Shape only -- no dictionary.  No vowel, or five letters with a four-consonant run."""
    word = tok.lower
    if not word.isalpha() or len(word) < 3:
        return False
    if word in LEXICON:
        return False      # the published word list knows it, so it is not nonsense ("hmm")
    if is_name_word(tok.text):
        return False
    if not (set(word) & VOWELS):
        return True
    run = 0
    for ch in word:
        run = 0 if ch in VOWELS else run + 1
        if run >= 4:
            return True
    return False


class Chain:
    """One resolved reference to a person's relation: anchor NAME + relation path."""

    __slots__ = ('anchor', 'path', 'start', 'end', 'closed')

    def __init__(self, anchor, path, start, end, closed):
        self.anchor, self.path = anchor, list(path)
        self.start, self.end, self.closed = start, end, closed

    def __repr__(self):
        return f'Chain({name_of(self.anchor)!r}, {self.path!r})'


def _owner_expr(toks, i, depth=0):
    """Parse an expression that denotes a person; return (anchor_tok, path, next_index).

    "Mira" -> (Mira, []).  "Mira's friend" -> (Mira, [friend]).
    "the friend of Mira" -> (Mira, [friend]).  "the gift of Mira's friend" ->
    (Mira, [friend, gift]).  Longest match wins; recursion is capped at three relations.
    """
    n = len(toks)
    if i >= n or depth > 3:
        return None
    j = i
    if toks[j].lower in DETERMINERS:
        j += 1
    if j < n and is_rel(toks[j]):
        rel, k = toks[j].lower, j + 1
        if k < n and toks[k].lower in ('of', 'for'):
            inner = _owner_expr(toks, k + 1, depth + 1)
            if inner:
                return inner[0], inner[1] + [rel], inner[2]
        if k + 1 < n and toks[k].lower == 'belonging' and toks[k + 1].lower == 'to':
            inner = _owner_expr(toks, k + 2, depth + 1)
            if inner:
                return inner[0], inner[1] + [rel], inner[2]
        if (k + 2 < n and toks[k].lower == 'that' and is_name(toks[k + 1])
                and toks[k + 2].lower in HAVE_VERBS):
            return toks[k + 1], [rel], k + 3
    tok = toks[i]
    if is_name_poss(tok):
        path, j = [], i + 1
        while j < n and is_rel_poss(toks[j]) and len(path) < 3:
            path.append(toks[j].stem)
            j += 1
        if j < n and is_rel(toks[j]) and len(path) < 3:
            path.append(toks[j].lower)
            j += 1
        return tok, path, j
    if is_name(tok):
        return tok, [], i + 1
    return None


def scan_chains(toks):
    """Every non-overlapping person reference, left to right, longest match first."""
    chains, i, n = [], 0, len(toks)
    while i < n:
        got = _owner_expr(toks, i)
        if got and (got[1] or is_name(toks[i]) or is_name_poss(toks[i])):
            anchor, path, end = got
            chains.append(Chain(anchor, path, i, end, bool(path)))
            i = max(end, i + 1)
        else:
            i += 1
    return chains


TRAILING_RE = None  # trailing relations are found on tokens, not on the raw string


def trailing_relation_index(toks, after):
    """`as a gift` / `for a prize` / `as his charm` at or after token `after`; token index."""
    for j in range(after, len(toks) - 1):
        if toks[j].lower not in ('as', 'for'):
            continue
        k = j + 1
        if toks[k].lower in TRAILING_DETS:
            k += 1
        if k < len(toks) and is_rel(toks[k]):
            return k
    return None


def trailing_relation(toks, after):
    index = trailing_relation_index(toks, after)
    return None if index is None else toks[index].lower


def strip_discourse(text):
    """Remove one leading discourse marker and one trailing tag.  Returns (body, offset)."""
    body, offset = text, 0
    match = CLOSER_RE.search(body)
    if match:
        body = body[:match.start()]
        if not body.endswith(('.', '?', '!')):
            body += '.'
    lead = re.match(r'^([A-Za-z]+(?:\s+[A-Za-z]+){0,2}),\s+', body)
    if lead and all(w.lower() in OPENER_WORDS for w in lead.group(1).split()):
        offset = lead.end()
        body = body[offset:]
    return body, offset


def _mentions(toks):
    return [t for t in toks if is_name(t) or is_name_poss(t)]


class Thought:
    """The typed part of a thought, as the parser can see it in the text."""

    def __init__(self, act, subject=None, relation_path=(), object=None, old=None,
                 teachable=True, unclear_reason=None):
        self.act = act
        self.subject = subject          # dict(name=, span=) or None
        self.relation_path = list(relation_path)
        self.object = object            # dict(name=, kind=, span=) or None
        self.old = old
        self.teachable = teachable
        self.unclear_reason = unclear_reason

    def key(self):
        """The comparable label: what the generator must agree with, exactly."""
        return (self.act,
                None if self.subject is None else (self.subject['name'],
                                                   tuple(self.subject['span'])),
                tuple(self.relation_path),
                None if self.object is None else (self.object['name'], self.object['kind'],
                                                  tuple(self.object['span'])),
                None if self.old is None else (self.old['name'], tuple(self.old['span'])),
                len(self.relation_path), self.teachable)

    def __repr__(self):
        return (f'Thought({self.act}, subj={self.subject and self.subject["name"]}, '
                f'path={self.relation_path}, obj={self.object and self.object["name"]})')


def _slot(tok, kind=None, span=None, name=None):
    span = span if span is not None else name_span(tok)
    name = name if name is not None else name_of(tok)
    out = dict(name=name, span=[span[0], span[1]])
    if kind:
        out['kind'] = kind
    return out


AND_RE = re.compile(r'\band\b')
PASSIVE_TO_RE = re.compile(r'\b(?:given|gave|passed|handed)\s+to\s+$', re.I)
MAX_PATH = 3


def strip_correction(body):
    """Remove one leading correction marker.  Returns (body, offset, is_correction)."""
    for marker in sorted(CORRECTION_MARKERS, key=len, reverse=True):
        match = re.match(rf'{re.escape(marker)}\b[,:;]?\s+', body, re.I)
        if match:
            return body[match.end():], match.end(), True
        if body.strip().lower() == marker:
            return body, 0, True
    return body, 0, False


def _covered(chains):
    """Every token index that some person reference has already claimed."""
    taken = set()
    for chain in chains:
        taken.update(range(chain.start, chain.end))
    return taken


def _extend_path(path, toks, chains, anchor_end):
    """Add relation words that no person reference claimed, plus a trailing `as a R`.

    "whose gift is it, for the friend of Mira?"  -> [friend] + free 'gift'  -> [friend, gift]
    "for Mira, the gift is a lamp."              -> []       + free 'gift'  -> [gift]
    "Mira picked a drum as a prize."             -> []       + trailing     -> [prize]
    The outer relation always ends up last, whichever side of the sentence it was written
    on, because a chain is read inside-out and a free relation is always the outer one.
    """
    taken = _covered(chains)
    used = set()
    tail = trailing_relation_index(toks, anchor_end)
    for i, tok in enumerate(toks):
        if i in taken or not (is_rel(tok) or is_rel_poss(tok)):
            continue
        used.add(i)
        if len(path) < MAX_PATH:
            path.append(tok.stem if is_rel_poss(tok) else tok.lower)
    if tail is not None and tail not in used and tail not in taken and len(path) < MAX_PATH:
        path.append(toks[tail].lower)
    return path


def _passive_subject(body, toks, mentions, offset):
    """"Finn was given to Dov as a friend" -- the receiver, not the first name, is the owner."""
    for tok in mentions:
        if PASSIVE_TO_RE.search(body[:tok.start - offset]):
            return tok
    return None


def parse(text):
    """Surface text -> Thought.  Never raises; an unreadable sentence is act UNCLEAR."""
    body, offset = strip_discourse(text)
    body, shift, correction = strip_correction(body)
    offset += shift
    toks = tokenize(body)
    for tok in toks:
        tok.start += offset
        tok.end += offset
    if not toks:
        return Thought('UNCLEAR', unclear_reason='empty')

    lower = body.lower()
    if not correction:
        correction = any(shape.match(lower) for shape in CORRECTION_SHAPES) \
            or bool(CORRECTION_TAIL.search(lower))

    # --- gibberish -------------------------------------------------------------------
    if any(looks_like_gibberish(t) for t in toks):
        return Thought('UNCLEAR', unclear_reason='gibberish')

    # --- pronoun possessive in front of a relation -------------------------------------
    for j, tok in enumerate(toks[:-1]):
        if tok.lower in PRONOUN_POSSESSIVES and (is_rel(toks[j + 1]) or is_rel_poss(toks[j + 1])):
            return Thought('UNCLEAR', unclear_reason='pronoun')

    # --- two facts joined by "and" -----------------------------------------------------
    # No single-fact frame in the published grammar contains a bare "and"; a coordination
    # with a relation word on both sides is two facts, which the notebook cannot write in
    # one go, so the right answer is to ask.
    for match in AND_RE.finditer(lower):
        left, right = lower[:match.start()], lower[match.end():]
        if (any(re.search(rf'\b{r}\b', left) for r in RELATIONS)
                and any(re.search(rf'\b{r}\b', right) for r in RELATIONS)):
            return Thought('UNCLEAR', unclear_reason='two_facts')

    values = [t for t in toks if is_value(t)]
    mentions = _mentions(toks)
    all_chains = scan_chains(toks)
    owner_chains = [c for c in all_chains if c.path]

    # --- two people each with their own relation ---------------------------------------
    if len({(name_of(c.anchor), tuple(c.path)) for c in owner_chains}) >= 2:
        return Thought('UNCLEAR', unclear_reason='two_facts')

    # --- a relation with nobody to own it -----------------------------------------------
    rel_tokens = [t for t in toks if is_rel(t) or is_rel_poss(t)]
    if rel_tokens and not mentions:
        return Thought('UNCLEAR', unclear_reason='no_owner')

    # --- who is the fact about, and what is the relation path --------------------------
    if owner_chains:
        chain = owner_chains[0]
        anchor, path, anchor_end = chain.anchor, list(chain.path), chain.end
    elif mentions:
        anchor = _passive_subject(body, toks, mentions, offset) or mentions[0]
        path, anchor_end = [], 0
        chain = None
    else:
        anchor, chain, path, anchor_end = None, None, [], 0
    if anchor is not None:
        path = _extend_path(path, toks, all_chains if chain else [], anchor_end)

    # --- question or statement ----------------------------------------------------------
    first = toks[0].lower
    question_lead = first in WH_WORDS or any(lower.startswith(lead) for lead in ASK_LEADS)
    ends_q = body.rstrip().endswith('?')

    # --- the object: a value, or the name that is not the owner --------------------------
    obj = old = None
    if values:
        negated = _negated_value(toks, values)
        rest = [t for t in values if t is not negated]
        if negated is not None and rest:
            old, obj = _slot(negated, 'value'), _slot(rest[-1], 'value')
        elif negated is None and len(rest) == 1:
            obj = _slot(rest[0], 'value')
        elif negated is None and len({t.lower for t in rest}) == 1:
            obj = _slot(rest[0], 'value')
        else:
            return Thought('UNCLEAR', unclear_reason='ambiguous_object')
    elif anchor is not None:
        others = [t for t in mentions
                  if not (t.start <= anchor.start and t.end >= anchor.end)
                  and name_of(t) != name_of(anchor)]
        if others:
            negated = _negated_name(toks, others)
            rest = [t for t in others if t is not negated]
            if negated is not None and rest:
                old, obj = _slot(negated, 'person'), _slot(rest[-1], 'person')
            elif negated is None and len({name_of(t) for t in rest}) == 1:
                obj = _slot(rest[0], 'person')
            elif rest:
                return Thought('UNCLEAR', unclear_reason='ambiguous_object')
    if old is not None:
        correction = True          # "X's gift is not a lamp, it is a drum" names an old value

    is_question = question_lead or (ends_q and obj is None)

    if anchor is not None:
        subject = _slot(anchor)
        if not path:
            # a name with nothing said about it: "actually it is Finn now."
            return Thought('UNCLEAR', unclear_reason='no_relation')
        if is_question:
            return Thought('ASK', subject, path, None, None)
        if obj is None:
            return Thought('UNCLEAR', unclear_reason='no_object')
        return Thought('CORRECT' if correction else 'TELL', subject, path, obj, old)

    # --- nobody named and no relation: small talk, or a question nothing can teach ------
    if is_question or ends_q:
        if any(lower.startswith(lead) for lead in FACT_LEAD_EXCEPTIONS):
            return Thought('ASK', None, [], None, None, teachable=False)
        if any(lower.startswith(lead) for lead in CHAT_QUESTION_LEADS):
            return Thought('CHAT', None, [], None, None)
        return Thought('ASK', None, [], None, None, teachable=False)
    if values:
        return Thought('UNCLEAR', unclear_reason='no_owner')
    return Thought('CHAT', None, [], None, None)


NEG_RE = re.compile(r'\b(not|no longer|does not have|is not|isn\'t)\b')


def _negated_value(toks, values):
    """The value token introduced by a negation -- the OLD value a correction names."""
    return _negated(toks, values)


def _negated_name(toks, names):
    return _negated(toks, names)


def _negated(toks, candidates):
    negations = [t for t in toks if t.lower in ('not', 'longer')]
    if not negations:
        return None
    best, best_gap = None, 99
    for neg in negations:
        for cand in candidates:
            gap = sum(1 for t in toks if neg.end <= t.start < cand.start)
            if 0 <= gap <= 2 and cand.start > neg.start and gap < best_gap:
                best, best_gap = cand, gap
    return best


def attach_symbols(thought, symbols, values=None):
    """Fill slot/symbol from a SUPPLIED symbol table: {name: (slot, symbol)}."""
    out = dict(act=thought.act, relation_path=list(thought.relation_path),
               teachable=thought.teachable, unclear_reason=thought.unclear_reason)
    for field in ('subject', 'object', 'old'):
        item = getattr(thought, field)
        if item is None:
            out[field] = None
            continue
        entry = dict(item)
        if entry.get('kind') == 'value':
            entry['slot'] = None
            entry['symbol'] = (values or {}).get(entry['name'])
        else:
            slot, symbol = symbols.get(entry['name'], (None, None))
            entry['slot'], entry['symbol'] = slot, symbol
        out[field] = entry
    return out
