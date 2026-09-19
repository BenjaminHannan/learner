"""Deterministic Declare-Clear-Apply episodes for the persistent learner.

This module owns the evaluator-side synthetic world. Model-facing helpers
encode only controlled-English teaching/query text; expected answers, tiers,
and semantic procedure metadata never enter inference batches.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
import random
import re
from typing import Iterable, Optional, Sequence

import torch


# Fixed controlled-English tokenizer -------------------------------------------------

PAD = "<pad>"
BOS = "<bos>"
EOS = "<eos>"
UNK = "<unk>"
NAME_START = "<name>"
NAME_END = "</name>"

SYMBOLS = tuple("abcdefgh")
NAME_CHAR_TOKENS = tuple(f"@{c}" for c in "abcdefghijklmnopqrstuvwxyz")
PUNCTUATION = ("[", "]", ".", ",", ":", ";", "?")

# Every ordinary word used by the generator is fixed here. Any other lowercase
# alphabetic token is represented compositionally as characters, so a test
# nonce name never requires test-only vocabulary growth.
CONTROL_WORDS = (
    "a", "after", "and", "apply", "as", "at", "belongs", "by", "called",
    "carries", "correction", "define", "does", "drop", "end", "exchange",
    "first", "flip", "followed", "give", "have", "head", "is", "it", "item",
    "left", "list", "means", "me", "move", "neighboring", "next", "of", "pairs",
    "remove", "reverse", "rotate", "show", "swap", "tag", "tell", "that", "the",
    "then", "to", "twin", "unknown", "what", "when", "which", "you",
)

TOKENS = (
    (PAD, BOS, EOS, UNK, NAME_START, NAME_END)
    + PUNCTUATION
    + tuple(dict.fromkeys(CONTROL_WORDS + SYMBOLS))
    + NAME_CHAR_TOKENS
)
VOCAB = {token: index for index, token in enumerate(TOKENS)}
ID_TO_TOKEN = {index: token for token, index in VOCAB.items()}

PAD_ID = VOCAB[PAD]
BOS_ID = VOCAB[BOS]
EOS_ID = VOCAB[EOS]
UNK_ID = VOCAB[UNK]
NAME_START_ID = VOCAB[NAME_START]
NAME_END_ID = VOCAB[NAME_END]

_LEXEME_RE = re.compile(r"[a-z]+|\[|\]|[.,:;?]|\S")


class ControlledEnglishTokenizer:
    """Fixed tokenizer with character-composable lowercase nonce names."""

    def __init__(self) -> None:
        self.vocab = VOCAB
        self.pad_id = PAD_ID
        self.bos_id = BOS_ID
        self.eos_id = EOS_ID
        self.unk_id = UNK_ID

    @property
    def vocab_size(self) -> int:
        return len(self.vocab)

    def pieces(self, text: str) -> tuple[str, ...]:
        if text != text.lower():
            raise ValueError("Controlled English must be lowercase")
        pieces: list[str] = []
        for lexeme in _LEXEME_RE.findall(text):
            if lexeme in self.vocab:
                pieces.append(lexeme)
            elif lexeme.isalpha() and lexeme.islower():
                pieces.append(NAME_START)
                pieces.extend(f"@{char}" for char in lexeme)
                pieces.append(NAME_END)
            else:
                pieces.append(UNK)
        return tuple(pieces)

    def encode(
        self,
        text: str,
        *,
        add_bos: bool = True,
        add_eos: bool = True,
    ) -> list[int]:
        ids = [self.vocab[piece] for piece in self.pieces(text)]
        if add_bos:
            ids.insert(0, self.bos_id)
        if add_eos:
            ids.append(self.eos_id)
        return ids


TOKENIZER = ControlledEnglishTokenizer()


# Model-facing records and deliberately separate evaluator feedback ------------------


@dataclass(frozen=True)
class Teaching:
    """One accepted declaration; program is evaluator-only audit metadata."""

    text: str
    correction: bool = False
    program: Optional[tuple[str, ...]] = field(default=None, repr=False)

    def tokens(self, tokenizer: ControlledEnglishTokenizer = TOKENIZER) -> list[int]:
        return tokenizer.encode(self.text)


@dataclass(frozen=True)
class Query:
    """Scored query with evaluator-only answer and semantic metadata."""

    text: str
    expected: str = field(repr=False)
    tier: int = field(default=1, repr=False)
    purpose: str = field(default="score", repr=False)
    program: Optional[tuple[str, ...]] = field(default=None, repr=False)

    def tokens(self, tokenizer: ControlledEnglishTokenizer = TOKENIZER) -> list[int]:
        """Inference encoding contains query text only."""
        return tokenizer.encode(self.text)


@dataclass(frozen=True)
class Episode:
    split: str
    episode: int
    seed: int
    tier: int
    teachings: tuple[Teaching, ...]
    queries: tuple[Query, ...]


@dataclass(frozen=True)
class TeachingFeedback:
    """Teaching feedback contains acceptance/correction status, never a target."""

    accepted: bool
    correction: bool


@dataclass(frozen=True)
class SelfEvaluation:
    """Practice feedback is exactly one correctness bit."""

    correct: bool


def accepted_teaching(teaching: Teaching) -> TeachingFeedback:
    return TeachingFeedback(accepted=True, correction=teaching.correction)


def self_evaluate(query: Query, response: str) -> SelfEvaluation:
    """Evaluator-only exact match; the returned object cannot reveal the target."""
    return SelfEvaluation(correct=response.strip() == query.expected)


_TAG_TEACHING_RE = re.compile(
    r"^(?:correction : )?the tag of ([a-z]+) is ([a-h]) \.$"
)
_TWIN_TEACHING_RE = re.compile(
    r"^(?:correction : )?the twin of ([a-z]+) is ([a-z]+) \.$"
)


def support_query_for_teaching(teaching: Teaching) -> Optional[Query]:
    """Build an evaluator-side immediate readback query for a factual write.

    The answer is used only as a training target. ``batch_queries`` still
    exposes only query text to the model, so the writer never receives this
    target or evaluator metadata. Procedure definitions need an operand to
    test execution and therefore use their separate reader controls instead.
    """
    tag = _TAG_TEACHING_RE.fullmatch(teaching.text)
    if tag is not None:
        subject, value = tag.groups()
        return Query(
            f"what is the tag of {subject} ?",
            value,
            tier=1,
            purpose="immediate_support",
        )
    twin = _TWIN_TEACHING_RE.fullmatch(teaching.text)
    if twin is not None:
        subject, value = twin.groups()
        return Query(
            f"what is the twin of {subject} ?",
            value,
            tier=2,
            purpose="immediate_support",
        )
    return None


def relation_value_key_probe(teaching: Teaching) -> Optional[Query]:
    """Return the canonical next-hop cue whose key a relation value should share.

    For ``twin(a)=b``, the stored value must be usable to retrieve information
    about ``b`` on the next reasoning step. The probe text is model-facing, but
    its placeholder expected value is never batched or scored.
    """
    twin = _TWIN_TEACHING_RE.fullmatch(teaching.text)
    if twin is None:
        return None
    _, target = twin.groups()
    return Query(
        f"what is the tag of {target} ?",
        "unknown",
        tier=2,
        purpose="relation_value_key_probe",
    )


# Padding/batching. Targets are a separate evaluator/training utility. ----------------


@dataclass(frozen=True)
class TokenBatch:
    token_ids: torch.Tensor
    lengths: torch.Tensor
    attention_mask: torch.Tensor


def pad_sequences(
    sequences: Sequence[Sequence[int]],
    *,
    pad_id: int = PAD_ID,
    max_length: Optional[int] = None,
    device: Optional[torch.device | str] = None,
) -> TokenBatch:
    if not sequences:
        raise ValueError("Cannot batch zero sequences")
    lengths = [len(sequence) for sequence in sequences]
    if any(length <= 0 for length in lengths):
        raise ValueError("Token sequences must be non-empty")
    width = max(lengths) if max_length is None else max_length
    if width <= 0 or any(length > width for length in lengths):
        raise ValueError("max_length is shorter than an input sequence")

    ids = torch.full((len(sequences), width), pad_id, dtype=torch.long, device=device)
    for row, sequence in enumerate(sequences):
        ids[row, : len(sequence)] = torch.tensor(sequence, dtype=torch.long, device=device)
    lens = torch.tensor(lengths, dtype=torch.long, device=device)
    positions = torch.arange(width, device=device).unsqueeze(0)
    mask = positions < lens.unsqueeze(1)
    return TokenBatch(ids, lens, mask)


def batch_teachings(
    teachings: Sequence[Teaching],
    *,
    device: Optional[torch.device | str] = None,
) -> TokenBatch:
    return pad_sequences([teaching.tokens() for teaching in teachings], device=device)


def batch_queries(
    queries: Sequence[Query],
    *,
    device: Optional[torch.device | str] = None,
) -> TokenBatch:
    """Safe inference batch: only Query.text is encoded."""
    return pad_sequences([query.tokens() for query in queries], device=device)


def encode_answer(
    answer: str,
    tokenizer: ControlledEnglishTokenizer = TOKENIZER,
) -> list[int]:
    """Encode an evaluator target as payload followed by EOS, without BOS."""
    return tokenizer.encode(answer, add_bos=False, add_eos=True)


def normalize_text(value: str) -> str:
    """Canonical whitespace/case normalization used for reported answers."""
    return re.sub(r"\s+", " ", value.strip().lower())


def decode_token_ids(
    token_ids: Iterable[int],
    tokenizer: ControlledEnglishTokenizer = TOKENIZER,
) -> str:
    """Deterministically decode generated ids into canonical controlled English."""
    id_to_token = {index: token for token, index in tokenizer.vocab.items()}
    pieces: list[str] = []
    name_chars: list[str] = []
    in_name = False
    for raw_id in token_ids:
        token = id_to_token.get(int(raw_id), UNK)
        if token == EOS:
            break
        if token in (PAD, BOS):
            continue
        if token == NAME_START:
            if in_name and name_chars:
                pieces.append("".join(name_chars))
            in_name = True
            name_chars = []
            continue
        if token == NAME_END:
            if in_name:
                pieces.append("".join(name_chars))
            in_name = False
            name_chars = []
            continue
        if in_name and token.startswith("@") and len(token) == 2:
            name_chars.append(token[1])
            continue
        if in_name:
            if name_chars:
                pieces.append("".join(name_chars))
            in_name = False
            name_chars = []
        pieces.append(token)
    if in_name and name_chars:
        pieces.append("".join(name_chars))
    return normalize_text(" ".join(pieces))


def batch_query_targets(
    queries: Sequence[Query],
    *,
    device: Optional[torch.device | str] = None,
) -> TokenBatch:
    """Explicit target-side utility; never use this as model inference input."""
    return pad_sequences([encode_answer(query.expected) for query in queries], device=device)


# Bounded list procedures with explicit edge semantics --------------------------------


MAX_LIST_LENGTH = 5
PRIMITIVES = ("reverse", "drop_first", "rotate_left", "swap_pairs")


def apply_primitive(name: str, items: Sequence[str | int]) -> tuple[str | int, ...]:
    values = tuple(items)
    if name == "reverse":
        return tuple(reversed(values))
    if name == "drop_first":
        # [] -> []; [x] -> [].
        return values[1:] if values else ()
    if name == "rotate_left":
        # Empty and singleton lists are fixed points.
        return values[1:] + values[:1] if len(values) > 1 else values
    if name == "swap_pairs":
        # Swap (0,1), (2,3), ...; an unpaired final item stays in place.
        result = list(values)
        for index in range(0, len(result) - 1, 2):
            result[index], result[index + 1] = result[index + 1], result[index]
        return tuple(result)
    raise ValueError(f"Unknown primitive: {name}")


def apply_program(
    program: Sequence[str],
    items: Sequence[str | int],
) -> tuple[str | int, ...]:
    result = tuple(items)
    for primitive in program:
        result = apply_primitive(primitive, result)
    return result


def format_list(items: Sequence[str]) -> str:
    return "[ " + " ".join(items) + " ]"


def semantic_signature(program: Sequence[str]) -> tuple[tuple[int, ...], ...]:
    """Function identity on every list length 0..5."""
    return tuple(
        tuple(int(value) for value in apply_program(program, tuple(range(length))))
        for length in range(MAX_LIST_LENGTH + 1)
    )


# Include depth four because a depth-three learned procedure followed by one
# familiar primitive is a scored query-time composition.
_PROGRAMS_2_TO_4 = tuple(
    tuple(program)
    for depth in range(2, 5)
    for program in product(PRIMITIVES, repeat=depth)
)
_ALL_SIGNATURES = sorted({semantic_signature(program) for program in _PROGRAMS_2_TO_4})
_split_rng = random.Random(20_260_917)
_shuffled_signatures = list(_ALL_SIGNATURES)
_split_rng.shuffle(_shuffled_signatures)
_train_cut = int(len(_shuffled_signatures) * 0.70)
_validation_cut = _train_cut + max(1, int(len(_shuffled_signatures) * 0.10))

SEMANTIC_PROCEDURE_CLASSES = {
    "train": frozenset(_shuffled_signatures[:_train_cut]),
    "validation": frozenset(_shuffled_signatures[_train_cut:_validation_cut]),
    "test": frozenset(_shuffled_signatures[_validation_cut:]),
}
_CLASS_OWNER = {
    signature: split
    for split, signatures in SEMANTIC_PROCEDURE_CLASSES.items()
    for signature in signatures
}

_TRIVIAL_SIGNATURES = {semantic_signature(())}
_TRIVIAL_SIGNATURES.update(semantic_signature((primitive,)) for primitive in PRIMITIVES)


def _representative_programs() -> dict[tuple[tuple[int, ...], ...], tuple[str, ...]]:
    representatives: dict[tuple[tuple[int, ...], ...], tuple[str, ...]] = {}
    for depth in (2, 3):
        for candidate in product(PRIMITIVES, repeat=depth):
            program = tuple(candidate)
            signature = semantic_signature(program)
            if signature in _TRIVIAL_SIGNATURES:
                continue
            previous = representatives.get(signature)
            if previous is None or program < previous:
                representatives[signature] = program
    return representatives


_REPRESENTATIVES = _representative_programs()


def _same_split_extensions(
    program: tuple[str, ...],
    split: str,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    extensions: list[tuple[str, tuple[str, ...]]] = []
    for primitive in PRIMITIVES:
        after = program + (primitive,)
        before = (primitive,) + program
        if _CLASS_OWNER.get(semantic_signature(after)) == split:
            extensions.append((f"after:{primitive}", after))
        if _CLASS_OWNER.get(semantic_signature(before)) == split:
            extensions.append((f"before:{primitive}", before))
    return tuple(extensions)


_PROCEDURE_POOLS: dict[str, tuple[tuple[str, ...], ...]] = {}
for _split in ("train", "validation", "test"):
    candidates = tuple(
        program
        for signature, program in sorted(_REPRESENTATIVES.items())
        if _CLASS_OWNER.get(signature) == _split
    )
    composable = tuple(program for program in candidates if _same_split_extensions(program, _split))
    _PROCEDURE_POOLS[_split] = composable or candidates

if any(not pool for pool in _PROCEDURE_POOLS.values()):
    raise RuntimeError("Semantic procedure split produced an empty definition pool")


# Controlled-English surface realization ---------------------------------------------


_PRIMITIVE_TEACH_PHRASES = {
    "reverse": ("reverse it", "flip it"),
    "drop_first": ("drop the first item", "remove the head"),
    "rotate_left": ("rotate it left", "move the first item to the end"),
    "swap_pairs": ("swap adjacent pairs", "exchange neighboring pairs"),
}
_PRIMITIVE_QUERY_PHRASES = {
    "reverse": "reverse",
    "drop_first": "drop first",
    "rotate_left": "rotate left",
    "swap_pairs": "swap pairs",
}


NONCE_NAME_PREFIXES = {"train": "ba", "validation": "ce", "test": "di"}
NONCE_NAME_POOL_SIZE = 256
_NONCE_SUFFIX_WIDTH = 4


def _base26_suffix(index: int, width: int = _NONCE_SUFFIX_WIDTH) -> str:
    if not 0 <= index < 26 ** width:
        raise ValueError("nonce-name index exceeds constructor capacity")
    chars = ["a"] * width
    for position in range(width - 1, -1, -1):
        index, remainder = divmod(index, 26)
        chars[position] = chr(ord("a") + remainder)
    return "".join(chars)


NONCE_NAME_POOLS = {
    split: tuple(
        prefix + _base26_suffix(index)
        for index in range(NONCE_NAME_POOL_SIZE)
    )
    for split, prefix in NONCE_NAME_PREFIXES.items()
}
_NONCE_NAME_OWNER = {
    name: split
    for split, pool in NONCE_NAME_POOLS.items()
    for name in pool
}


def levenshtein_distance(left: str, right: str) -> int:
    """Return ordinary insertion/deletion/substitution Levenshtein distance."""
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            current.append(min(
                current[-1] + 1,
                previous[right_index] + 1,
                previous[right_index - 1] + (left_char != right_char),
            ))
        previous = current
    return previous[-1]


for _left_split, _right_split in (
    ("train", "validation"),
    ("train", "test"),
    ("validation", "test"),
):
    _left_prefix = NONCE_NAME_PREFIXES[_left_split]
    _right_prefix = NONCE_NAME_PREFIXES[_right_split]
    if len(_left_prefix) != len(_right_prefix) or sum(
        left != right for left, right in zip(_left_prefix, _right_prefix)
    ) < 2:
        raise RuntimeError("Nonce-name prefixes must force edit distance >= 2")


def _nonce_name(split: str, rng: random.Random, used: set[str]) -> str:
    pool = NONCE_NAME_POOLS[split]
    while True:
        name = pool[rng.randrange(len(pool))]
        if name not in used:
            used.add(name)
            return name


def _tag_teaching(name: str, tag: str, correction: bool = False) -> Teaching:
    prefix = "correction : " if correction else ""
    return Teaching(f"{prefix}the tag of {name} is {tag} .", correction=correction)


def _twin_teaching(left: str, right: str, correction: bool = False) -> Teaching:
    prefix = "correction : " if correction else ""
    return Teaching(f"{prefix}the twin of {left} is {right} .", correction=correction)


def _tag_query(name: str, expected: str, variant: int, *, purpose: str) -> Query:
    templates = (
        f"what is the tag of {name} ?",
        f"which tag does {name} have ?",
        f"give me the tag of {name} .",
    )
    return Query(templates[variant % len(templates)], expected, tier=1, purpose=purpose)


def _primitive_phrase(primitive: str, variant: int) -> str:
    choices = _PRIMITIVE_TEACH_PHRASES[primitive]
    return choices[variant % len(choices)]


def _definition_text(
    name: str,
    program: tuple[str, ...],
    template: int,
    rng: random.Random,
) -> str:
    phrases = [_primitive_phrase(primitive, rng.randrange(2)) for primitive in program]
    if template == 1:
        return f"to {name} a list : " + " , then ".join(phrases) + " ."
    if template == 2:
        return f"{name} means " + " then ".join(phrases) + " ."
    if template == 3:
        return f"define {name} as " + " followed by ".join(phrases) + " ."
    if template == 4:
        return f"you {name} a list when you " + " and next ".join(phrases) + " ."
    if template == 5:
        return f"{name} is : " + " ; after that ".join(phrases) + " ."
    raise ValueError("Definition template must be 1..5")


def _definition_teaching(
    name: str,
    program: tuple[str, ...],
    split: str,
    rng: random.Random,
) -> Teaching:
    # T5 is held out from meta-training and validation.
    template = 5 if split == "test" else rng.choice((1, 2, 3, 4))
    return Teaching(
        _definition_text(name, program, template, rng),
        correction=False,
        program=program,
    )


def _random_operand(
    rng: random.Random,
    length: Optional[int] = None,
) -> tuple[str, ...]:
    count = rng.randrange(MAX_LIST_LENGTH + 1) if length is None else length
    if not 0 <= count <= MAX_LIST_LENGTH:
        raise ValueError("Operand length must be in [0, 5]")
    return tuple(rng.choice(SYMBOLS) for _ in range(count))


_operand_rng = random.Random(20_260_918)
_shuffled_operands = list(product(SYMBOLS, repeat=MAX_LIST_LENGTH))
_operand_rng.shuffle(_shuffled_operands)
TIER3_OPERAND_POOLS = {
    split: tuple(_shuffled_operands[offset::3])
    for offset, split in enumerate(("train", "validation", "test"))
}
_TIER3_OPERAND_OWNER = {
    operand: split
    for split, pool in TIER3_OPERAND_POOLS.items()
    for operand in pool
}


# Deterministic episodic generator ----------------------------------------------------


SPLIT_BASES = {"train": 0, "validation": 1_000_000, "test": 2_000_000}
EPISODES_PER_SPLIT = 1_000_000


def split_seed(split: str, episode: int) -> int:
    if split not in SPLIT_BASES:
        raise ValueError(f"Unknown split: {split}")
    if not isinstance(episode, int) or not 0 <= episode < EPISODES_PER_SPLIT:
        raise ValueError("episode must be an integer in [0, 1_000_000)")
    return SPLIT_BASES[split] + episode


def _tier1_episode(split: str, episode: int, seed: int, rng: random.Random) -> Episode:
    used: set[str] = set()
    names = [_nonce_name(split, rng, used) for _ in range(7)]
    primary = names[0]
    old_tag = rng.choice(SYMBOLS)
    new_tag = rng.choice(tuple(symbol for symbol in SYMBOLS if symbol != old_tag))
    distractor_tags = {name: rng.choice(SYMBOLS) for name in names[1:]}

    teachings: list[Teaching] = [_tag_teaching(primary, old_tag)]
    teachings.extend(_tag_teaching(name, distractor_tags[name]) for name in names[1:4])
    teachings.append(_tag_teaching(primary, new_tag, correction=True))
    teachings.extend(_tag_teaching(name, distractor_tags[name]) for name in names[4:])

    queries: list[Query] = [
        _tag_query(primary, new_tag, 1, purpose="correction_paraphrase"),
        _tag_query(primary, new_tag, 2, purpose="correction_paraphrase"),
    ]
    queries.extend(
        _tag_query(name, distractor_tags[name], index, purpose="interference")
        for index, name in enumerate(names[1:], start=1)
    )
    unknown_name = _nonce_name(split, rng, used)
    queries.append(_tag_query(unknown_name, "unknown", 0, purpose="unknown_control"))
    return Episode(split, episode, seed, 1, tuple(teachings), tuple(queries))


def _tier2_episode(split: str, episode: int, seed: int, rng: random.Random) -> Episode:
    used: set[str] = set()
    a, b, c, d = (_nonce_name(split, rng, used) for _ in range(4))
    old_tag = rng.choice(SYMBOLS)
    new_tag = rng.choice(tuple(symbol for symbol in SYMBOLS if symbol != old_tag))
    a_tag = rng.choice(SYMBOLS)
    d_tag = rng.choice(SYMBOLS)

    teachings = (
        _twin_teaching(a, b),
        _tag_teaching(b, old_tag),
        _tag_teaching(a, a_tag),
        _twin_teaching(c, d),
        _tag_teaching(d, d_tag),
        _tag_teaching(b, new_tag, correction=True),
    )
    queries = (
        Query(
            f"what is the tag of the twin of {a} ?",
            new_tag,
            tier=2,
            purpose="corrected_two_hop",
        ),
        Query(
            f"which tag does the twin of {a} have ?",
            new_tag,
            tier=2,
            purpose="two_hop_paraphrase",
        ),
        Query(f"what is the tag of {b} ?", new_tag, tier=2, purpose="single_hop_control"),
        Query(f"what is the tag of {a} ?", a_tag, tier=2, purpose="distractor_control"),
    )
    return Episode(split, episode, seed, 2, teachings, queries)


def _procedure_query_text(
    name: str,
    operand: tuple[str, ...],
    extension: Optional[str] = None,
) -> str:
    rendered = format_list(operand)
    if extension is None:
        return f"apply {name} to {rendered} ."
    direction, primitive = extension.split(":", 1)
    primitive_text = _PRIMITIVE_QUERY_PHRASES[primitive]
    if direction == "after":
        return f"apply {name} then {primitive_text} to {rendered} ."
    if direction == "before":
        return f"apply {primitive_text} then {name} to {rendered} ."
    raise ValueError(extension)


def _tier3_episode(split: str, episode: int, seed: int, rng: random.Random) -> Episode:
    used: set[str] = set()
    name = _nonce_name(split, rng, used)
    pool = _PROCEDURE_POOLS[split]
    program = pool[rng.randrange(len(pool))]
    teaching = _definition_teaching(name, program, split, rng)

    extensions = _same_split_extensions(program, split)
    operand_count = 2 if extensions else 1
    operands = rng.sample(TIER3_OPERAND_POOLS[split], k=operand_count)
    operand = operands[0]
    result = apply_program(program, operand)
    queries: list[Query] = [
        Query(
            _procedure_query_text(name, operand),
            format_list(tuple(str(item) for item in result)),
            tier=3,
            purpose="novel_operand",
            program=program,
        )
    ]

    if extensions:
        extension, combined = extensions[rng.randrange(len(extensions))]
        operand = operands[1]
        result = apply_program(combined, operand)
        queries.append(
            Query(
                _procedure_query_text(name, operand, extension),
                format_list(tuple(str(item) for item in result)),
                tier=3,
                purpose="query_time_composition",
                program=combined,
            )
        )
    return Episode(split, episode, seed, 3, (teaching,), tuple(queries))


def generate_episode(split: str, episode: int, tier: Optional[int] = None) -> Episode:
    """Generate one deterministic episode from a split-disjoint RNG range."""
    seed = split_seed(split, episode)
    selected_tier = 1 + episode % 3 if tier is None else tier
    if selected_tier not in (1, 2, 3):
        raise ValueError("tier must be 1, 2, or 3")
    rng = random.Random(seed)
    if selected_tier == 1:
        return _tier1_episode(split, episode, seed, rng)
    if selected_tier == 2:
        return _tier2_episode(split, episode, seed, rng)
    return _tier3_episode(split, episode, seed, rng)


class EpisodeGenerator:
    """Convenience wrapper for one fixed data split."""

    def __init__(self, split: str):
        if split not in SPLIT_BASES:
            raise ValueError(f"Unknown split: {split}")
        self.split = split

    def episode(self, index: int, tier: Optional[int] = None) -> Episode:
        return generate_episode(self.split, index, tier=tier)

    def episodes(
        self,
        start: int,
        count: int,
        *,
        tier: Optional[int] = None,
    ) -> tuple[Episode, ...]:
        if count < 0:
            raise ValueError("count must be non-negative")
        return tuple(self.episode(index, tier=tier) for index in range(start, start + count))


# Leakage/split audit -----------------------------------------------------------------


_SURFACE_WORDS = frozenset(CONTROL_WORDS) | frozenset(SYMBOLS) | {"adjacent"}
_LIST_OPERAND_RE = re.compile(r"\[\s*(.*?)\s*\]")


def _nonce_names_in_text(text: str) -> tuple[str, ...]:
    return tuple(
        word for word in re.findall(r"[a-z]+", text)
        if word not in _SURFACE_WORDS
    )


def _operand_in_query(text: str) -> Optional[tuple[str, ...]]:
    match = _LIST_OPERAND_RE.search(text)
    if match is None:
        return None
    body = match.group(1)
    return tuple(body.split()) if body else ()


def audit_split_separation(episodes: Iterable[Episode]) -> dict[str, object]:
    """Audit semantic classes plus observed nonce names and scored operands."""
    observed: dict[str, set[tuple[tuple[int, ...], ...]]] = {
        "train": set(),
        "validation": set(),
        "test": set(),
    }
    observed_names: dict[str, set[str]] = {split: set() for split in observed}
    observed_operands: dict[str, set[tuple[str, ...]]] = {split: set() for split in observed}
    violations: list[str] = []

    for item in episodes:
        expected_seed = split_seed(item.split, item.episode)
        if item.seed != expected_seed:
            violations.append(
                f"{item.split}:{item.episode} has seed {item.seed}, expected {expected_seed}"
            )
        entries = [
            *((f"teaching[{index}]", teaching.program)
              for index, teaching in enumerate(item.teachings)),
            *((f"query[{index}]", query.program)
              for index, query in enumerate(item.queries)),
        ]
        for source, program in entries:
            if program is None:
                continue
            signature = semantic_signature(program)
            observed[item.split].add(signature)
            owner = _CLASS_OWNER.get(signature)
            if owner != item.split:
                violations.append(
                    f"{item.split}:{item.episode} {source} uses a semantic class "
                    f"reserved for {owner or 'no registered split'}"
                )

        text_entries = [
            *((f"teaching[{index}]", teaching.text)
              for index, teaching in enumerate(item.teachings)),
            *((f"query[{index}]", query.text)
              for index, query in enumerate(item.queries)),
        ]
        for source, text in text_entries:
            for name in _nonce_names_in_text(text):
                observed_names[item.split].add(name)
                owner = _NONCE_NAME_OWNER.get(name)
                if owner != item.split:
                    violations.append(
                        f"{item.split}:{item.episode} {source} uses nonce name {name!r} "
                        f"reserved for {owner or 'no registered split'}"
                    )

        if item.tier == 3:
            for index, query in enumerate(item.queries):
                operand = _operand_in_query(query.text)
                if operand is None:
                    violations.append(
                        f"{item.split}:{item.episode} query[{index}] has no encoded operand"
                    )
                    continue
                observed_operands[item.split].add(operand)
                if not 0 <= len(operand) <= MAX_LIST_LENGTH:
                    violations.append(
                        f"{item.split}:{item.episode} query[{index}] operand exceeds "
                        f"MAX_LIST_LENGTH"
                    )
                if any(symbol not in SYMBOLS for symbol in operand):
                    violations.append(
                        f"{item.split}:{item.episode} query[{index}] operand contains "
                        "an unregistered symbol"
                    )
                if UNK_ID in TOKENIZER.encode(format_list(operand)):
                    violations.append(
                        f"{item.split}:{item.episode} query[{index}] operand is not fully encoded"
                    )
                owner = _TIER3_OPERAND_OWNER.get(operand)
                if owner != item.split:
                    violations.append(
                        f"{item.split}:{item.episode} query[{index}] uses operand {operand!r} "
                        f"reserved for {owner or 'no registered split'}"
                    )

    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        overlap = observed[left] & observed[right]
        if overlap:
            violations.append(f"{left}/{right} observed semantic overlap: {len(overlap)} class(es)")
        name_overlap = observed_names[left] & observed_names[right]
        if name_overlap:
            violations.append(
                f"{left}/{right} observed nonce-name overlap: {len(name_overlap)} name(s)"
            )
        operand_overlap = observed_operands[left] & observed_operands[right]
        if operand_overlap:
            violations.append(
                f"{left}/{right} observed operand overlap: {len(operand_overlap)} operand(s)"
            )
        for left_name in observed_names[left]:
            for right_name in observed_names[right]:
                if levenshtein_distance(left_name, right_name) < 2:
                    violations.append(
                        f"{left}/{right} nonce names {left_name!r}/{right_name!r} have "
                        "Levenshtein distance < 2"
                    )

    if violations:
        raise ValueError("Split audit failed: " + "; ".join(violations))
    return {
        "ok": True,
        "observed_classes": {split: len(classes) for split, classes in observed.items()},
        "observed_names": {split: len(names) for split, names in observed_names.items()},
        "observed_operands": {
            split: len(operands) for split, operands in observed_operands.items()
        },
        "reserved_classes": {
            split: len(classes) for split, classes in SEMANTIC_PROCEDURE_CLASSES.items()
        },
    }


__all__ = [
    "BOS", "BOS_ID", "EOS", "EOS_ID", "PAD", "PAD_ID", "UNK", "UNK_ID",
    "VOCAB", "TOKENIZER", "ControlledEnglishTokenizer", "Teaching", "Query",
    "Episode", "TeachingFeedback", "SelfEvaluation", "TokenBatch",
    "accepted_teaching", "self_evaluate", "pad_sequences", "batch_teachings",
    "batch_queries", "encode_answer", "decode_token_ids", "normalize_text",
    "batch_query_targets", "SYMBOLS",
    "PRIMITIVES", "MAX_LIST_LENGTH", "apply_primitive", "apply_program",
    "format_list", "semantic_signature", "SEMANTIC_PROCEDURE_CLASSES",
    "NONCE_NAME_PREFIXES", "NONCE_NAME_POOLS", "levenshtein_distance",
    "TIER3_OPERAND_POOLS",
    "SPLIT_BASES", "split_seed", "generate_episode", "EpisodeGenerator",
    "audit_split_separation",
]
