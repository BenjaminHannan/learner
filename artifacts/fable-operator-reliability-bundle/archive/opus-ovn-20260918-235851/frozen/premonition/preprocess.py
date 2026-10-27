"""Label-free inputs shared by D and the Core contenders (design/06 §9.1, §11).

"Label-free" means no earlier answer or feedback can reach a model's input; the current question's answer
stays a training target. Masking a loss does not remove information from a reader, so labels are removed
from the TEXT, before names are bound to entity ids and before anything is encoded.

Every input is built from the visit's lines through `visible_line`:

- label-free (the default for new evaluation): a question line keeps its text through "[answer]" (its
  `Question.prompt_line`) and loses the answer and feedback spans; other lines are unchanged. Every question
  line of a visit therefore reads "[question] ... [answer]" + newline, both in D's reader stream (where each
  question is answered at its own "[answer]") and in the Core prompts (A, B, C, E), whose final line is the
  current question cut at "[answer]".
- with-labels: lines unchanged. Reported as a diagnostic, never in a verdict.
- gold-evidence: a privileged diagnostic regime (the correct evidence is supplied); its prompts follow the
  label-free line rule. It never enters a verdict. (Its inputs are built by a later milestone.)

Names (`prepare_visit`). Entity ids are bound in first-mention order over the VISIBLE text only, so a name
that occurs only in an earlier answer or feedback never enters the name table or shifts later ids. The
current answer is bound with the mapping of the visible prefix through its own "[answer]": a target name
the prefix never mentioned stays ordinary tokenizer tokens and is FLAGGED (`PreparedQuestion.unbound`),
never imported from a label.

Identity. `spec(regime)` states these rules; `digest(regime)` is the SHA-256 of that canonical JSON. Caches,
checkpoints and reports carry `identity(regime)`; a changed rule must bump VERSION (a golden test pins the
output of a fixed visit to the digest), so a changed preprocessing digest always yields a new cache identity.

Scoring boundaries. `prediction_text` turns an output entity the name table does not hold into "<entK>",
which matches no answer (a wrong prediction, never a crash). `target_text` is strict: a gold target that
cannot be detokenised is a `MalformedTarget`, and a malformed input is a `MalformedInput`; both are errors,
distinguishable from wrong predictions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Iterable, Mapping, Optional, Sequence

from learnlab.step1 import ANSWER_TAG, FEEDBACK_TAG, QUESTION_TAG, parse_question_line
from learnlab.tokenizer import Tokenizer

from .batch import N_ENT, NameTable
from .pointer import Binder, NameDetector, answer_text, pointerize

FORMAT = "premonition.preprocess"
VERSION = 1
LABEL_FREE = "label-free"
WITH_LABELS = "with-labels"
GOLD_EVIDENCE = "gold-evidence"
LEGACY = "legacy-unknown"           # a report or checkpoint that records no regime: never assumed label-free
REGIMES = (LABEL_FREE, WITH_LABELS, GOLD_EVIDENCE)
VERDICT_REGIMES = frozenset({LABEL_FREE})
LOOKUP_CANDIDATES = "before-c-window"          # design/06 §11.5; the legacy rule was "before-a-window"
LEGACY_LOOKUP_CANDIDATES = "before-a-window"


class MalformedInput(ValueError):
    """A model input breaks the preprocessing contract (a label in the input, a cut question line ...)."""


class MalformedTarget(ValueError):
    """A gold target cannot be represented (empty, or an entity id the name table does not hold)."""


def check_regime(regime: str) -> str:
    if regime not in REGIMES:
        raise ValueError(f"unknown input regime {regime!r}; choose from {REGIMES}")
    return regime


def regime_of(labels: Optional[bool], regime: Optional[str]) -> str:
    """The regime of an API that still takes the older `labels` flag (None: not given)."""
    if labels is not None and regime is not None:
        wanted = WITH_LABELS if labels else LABEL_FREE
        if wanted != regime:
            raise ValueError(f"labels={labels} contradicts regime={regime!r}")
    if regime is not None:
        return check_regime(regime)
    return WITH_LABELS if labels else LABEL_FREE


# ----------------------------------------------------------------- identity


def spec(regime: str) -> dict[str, Any]:
    """The rules of one regime, as data (their digest is the preprocessing identity)."""
    check_regime(regime)
    labelled = regime == WITH_LABELS
    return {
        "format": FORMAT, "version": VERSION, "regime": regime,
        "question_lines": "whole line" if labelled else "text through [answer], then newline",
        "removed_spans": [] if labelled else ["answer", "feedback"],
        "other_lines": "unchanged; a non-question line holding [answer] or [feedback] is malformed",
        "names": ("first mention over the whole lines, answers included" if labelled
                  else "first mention over the visible text only"),
        "targets": ("the current answer, bound with the names of its whole question line (legacy v1)" if labelled
                    else "the current answer, bound with the names of the visible prefix through its [answer]; "
                    "an unbound target name stays tokenizer tokens and is flagged"),
        "reader_lm_mask": "no L_lm target on any answer token, nor on [answer] -> newline",
        "core_window": "newest whole visible lines within 736 tokens with the question cut at [answer]",
        "lookup_candidates": LOOKUP_CANDIDATES,
    }


def digest(regime: str) -> str:
    canonical = json.dumps(spec(regime), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def identity(regime: str) -> dict[str, Any]:
    """What caches, checkpoints and reports record about their preprocessing."""
    return {"format": FORMAT, "version": VERSION, "regime": check_regime(regime), "digest": digest(regime)}


def identity_problems(recorded: Optional[Mapping[str, Any]]) -> list[str]:
    """Why a recorded preprocessing identity is not one this code produces (empty: it is)."""
    if not recorded:
        return ["no preprocessing identity recorded (legacy/unknown)"]
    if recorded.get("format") != FORMAT or recorded.get("version") != VERSION:
        return [f"preprocessing {recorded.get('format')} v{recorded.get('version')} is not {FORMAT} v{VERSION}"]
    regime = recorded.get("regime")
    if regime not in REGIMES:
        return [f"unknown preprocessing regime {regime!r}"]
    if recorded.get("digest") != digest(regime):
        return [f"preprocessing digest {str(recorded.get('digest'))[:12]} is not today's {regime} digest "
                f"{digest(regime)[:12]}"]
    return []


# ----------------------------------------------------------------- lines


def visible_line(line: str, regime: str = LABEL_FREE) -> str:
    """The text of one stream line as a model in `regime` may see it (no trailing newline)."""
    if check_regime(regime) == WITH_LABELS:
        return line
    if line.startswith(QUESTION_TAG):
        if ANSWER_TAG not in line:
            raise MalformedInput(f"question line without {ANSWER_TAG}: {line[:80]!r}")
        return line[: line.index(ANSWER_TAG) + len(ANSWER_TAG)]
    if ANSWER_TAG in line or FEEDBACK_TAG in line:
        raise MalformedInput(f"a non-question line carries a label tag: {line[:80]!r}")
    return line


def answer_segment(line: str) -> str:
    """The raw text between "[answer]" and "[feedback]" (or the line's end) of a question line."""
    if not line.startswith(QUESTION_TAG) or ANSWER_TAG not in line:
        raise MalformedInput(f"not a question line: {line[:80]!r}")
    rest = line[line.index(ANSWER_TAG) + len(ANSWER_TAG):]
    return rest.split(FEEDBACK_TAG, 1)[0]


def label_spans(line: str) -> tuple[str, str]:
    """(answer, feedback) of a question line, stripped (what label-free inputs drop)."""
    _, answer, feedback = parse_question_line(line)
    return answer, feedback


# ----------------------------------------------------------------- visits


@dataclass(frozen=True)
class PreparedQuestion:
    line: int                           # the question's line within the visit
    span: tuple[int, int]               # [line start, "[answer]" + 1) in visit token positions
    target: list[int]                   # the answer's ids then <eos> (names as entity ids where bound)
    unbound: tuple[str, ...]            # target names the visible prefix never mentioned (kept as plain tokens)
    bound: tuple[str, ...]              # names bound by the visible prefix through this "[answer]"


@dataclass
class PreparedVisit:
    """One visit's lines as `regime` shows them, encoded (names as entities when a detector is given)."""

    regime: str
    pieces: list[list[int]]             # each visible line's ids, ending with the newline
    starts: list[int]                   # token position of each line; starts[-1] = total tokens
    table: NameTable                    # entity -> spelling, bound from the visible text only
    questions: dict[int, PreparedQuestion] = field(default_factory=dict)   # by line index
    label_only_names: tuple[str, ...] = ()   # names written only in answer/feedback spans (never bound)

    @property
    def tokens(self) -> list[int]:
        return [i for piece in self.pieces for i in piece]


def _strip_trailing_space(ids: list[int], tokenizer: Tokenizer) -> list[int]:
    base = tokenizer.vocab_size
    while ids and ids[-1] < base and not tokenizer.decode(ids[-1:]).strip():
        ids = ids[:-1]
    return ids


def bind_target(segment: str, tokenizer: Tokenizer, detector: Optional[NameDetector], mapping: Mapping[str, int],
                *, cache: Optional[dict[str, list[int]]] = None) -> tuple[list[int], tuple[str, ...]]:
    """(target ids without <eos>, unbound names) of an answer segment under a fixed name mapping.

    A name in `mapping` becomes its entity id; any other name stays the tokenizer's encoding of its
    spelling and is reported, so a target never binds a name its visible input did not.
    """
    base = tokenizer.vocab_size

    def encode(text: str) -> list[int]:
        if cache is None:
            return tokenizer.encode(text)
        found = cache.get(text)
        if found is None:
            if len(cache) >= 200_000:
                cache.clear()
            found = cache[text] = tokenizer.encode(text)
        return found

    if detector is None:
        return _strip_trailing_space(list(encode(segment)), tokenizer), ()
    ids: list[int] = []
    unbound: list[str] = []
    for part, is_name in detector.split(segment):
        if is_name and part in mapping:
            ids.append(base + mapping[part])
        else:
            ids.extend(encode(part))
            if is_name:
                unbound.append(part)
    return _strip_trailing_space(ids, tokenizer), tuple(dict.fromkeys(unbound))


def prepare_visit(lines: Sequence[str], tokenizer: Tokenizer, detector: Optional[NameDetector], *,
                  regime: str = LABEL_FREE, order: Optional[Sequence[int]] = None,
                  cache: Optional[dict[str, list[int]]] = None) -> PreparedVisit:
    """Encode a visit's lines under `regime`, with a target for every question line.

    With a detector, names become entity ids (`order`: the entity of the k-th distinct name; identity by
    default). Without one (D-noptr), lines are plain tokenizer ids and targets never have entities.
    """
    check_regime(regime)
    answer_id = tokenizer.token_to_id(ANSWER_TAG)
    eos = tokenizer.token_to_id("<eos>")
    newline = tokenizer.encode("\n")
    binder = Binder(order)
    pieces: list[list[int]] = []
    starts = [0]
    questions: dict[int, PreparedQuestion] = {}
    for k, line in enumerate(lines):
        text = visible_line(line, regime)
        if detector is None:
            ids = list(tokenizer.encode(text + "\n") if cache is None else _cached(cache, tokenizer, text + "\n"))
        else:
            ids = pointerize(text + "\n", tokenizer, detector, binder=binder, cache=cache)[0]
        if line.startswith(QUESTION_TAG):
            if answer_id not in ids:
                raise MalformedInput(f"line {k}: question line without {ANSWER_TAG}")
            a = ids.index(answer_id)
            if regime != WITH_LABELS and ids[a + 1:] != newline:
                raise MalformedInput(f"line {k}: a label-free question line continues after {ANSWER_TAG}")
            mapping = binder.bound()
            target, unbound = bind_target(answer_segment(line), tokenizer, detector, mapping, cache=cache)
            if not target:
                raise MalformedTarget(f"line {k}: empty answer")
            questions[k] = PreparedQuestion(line=k, span=(starts[-1], starts[-1] + a + 1), target=target + [eos],
                                            unbound=unbound, bound=tuple(mapping))
        pieces.append(ids)
        starts.append(starts[-1] + len(ids))
    label_only: tuple[str, ...] = ()
    if detector is not None and regime != WITH_LABELS:
        shown = set(binder.table.spellings.values())
        label_only = tuple(name for name in detector.names("\n".join(lines)) if name not in shown)
    return PreparedVisit(regime=regime, pieces=pieces, starts=starts, table=binder.table, questions=questions,
                         label_only_names=label_only)


def _cached(cache: dict[str, list[int]], tokenizer: Tokenizer, text: str) -> list[int]:
    found = cache.get(text)
    if found is None:
        if len(cache) >= 200_000:
            cache.clear()
        found = cache[text] = tokenizer.encode(text)
    return found


# ----------------------------------------------------------------- audits and scoring text


def audit_ids(ids: Sequence[int], tokenizer: Tokenizer, regime: str) -> None:
    """A label-free (or gold-evidence) input: no "[feedback]" at all, and every "[answer]" ends its question
    line (a newline follows) except the final one, which ends the input. MalformedInput otherwise."""
    if check_regime(regime) == WITH_LABELS:
        return
    answer_id, feedback_id = tokenizer.token_to_id(ANSWER_TAG), tokenizer.token_to_id(FEEDBACK_TAG)
    newline = tokenizer.encode("\n")
    ids = list(ids)
    if feedback_id in ids:
        raise MalformedInput("a label-free input holds a [feedback] token")
    if not ids or ids[-1] != answer_id:
        raise MalformedInput(f"an input must end with {ANSWER_TAG}")
    for position, token in enumerate(ids[:-1]):
        if token == answer_id and ids[position + 1:position + 1 + len(newline)] != newline:
            raise MalformedInput(f"an earlier {ANSWER_TAG} at position {position} is followed by answer text")


def audit_stream(ids: Sequence[int], tokenizer: Tokenizer, regime: str) -> None:
    """A label-free reader stream (a whole visit): no "[feedback]", and a newline right after every
    "[answer]". MalformedInput otherwise."""
    if check_regime(regime) == WITH_LABELS:
        return
    answer_id, feedback_id = tokenizer.token_to_id(ANSWER_TAG), tokenizer.token_to_id(FEEDBACK_TAG)
    newline = tokenizer.encode("\n")
    ids = [int(i) for i in ids]
    if feedback_id in ids:
        raise MalformedInput("a label-free reader stream holds a [feedback] token")
    for position, token in enumerate(ids):
        if token == answer_id and ids[position + 1:position + 1 + len(newline)] != newline:
            raise MalformedInput(f"{ANSWER_TAG} at position {position} is followed by answer text")


def prediction_text(ids: Iterable[int], table: NameTable, tokenizer: Tokenizer) -> tuple[str, bool]:
    """(answer text, whether it used an entity the table does not hold). An unbound entity is written
    "<entK>", which matches no answer: the prediction is wrong, never an error."""
    base, specials = tokenizer.vocab_size, len(tokenizer.specials)
    used: list[int] = []                                  # the ids `answer_text` reads, in its order
    for index in ids:
        index = int(index)
        if index == -100:
            continue
        if index < specials or index >= base + N_ENT:     # a special ends the answer; so does an impossible id
            break
        used.append(index)
        if index < base and "\n" in tokenizer.decode([index]):
            break
    unbound = any(i >= base and (i - base) not in table.spellings for i in used)
    known = {e: f"<ent{e}>" for e in range(N_ENT)}
    known.update(table.spellings)
    return answer_text(used, NameTable(known), tokenizer), unbound


def target_text(ids: Iterable[int], table: NameTable, tokenizer: Tokenizer) -> str:
    """The gold answer text; MalformedTarget if it is empty or names an entity the table does not hold."""
    try:
        text = answer_text(ids, table, tokenizer)
    except ValueError as error:
        raise MalformedTarget(str(error)) from None
    if not text:
        raise MalformedTarget("an empty target")
    return text


__all__ = [
    "FORMAT", "GOLD_EVIDENCE", "LABEL_FREE", "LEGACY", "LEGACY_LOOKUP_CANDIDATES", "LOOKUP_CANDIDATES",
    "MalformedInput", "MalformedTarget", "PreparedQuestion", "PreparedVisit", "REGIMES", "VERDICT_REGIMES",
    "VERSION", "WITH_LABELS", "answer_segment", "audit_ids", "audit_stream", "bind_target", "check_regime", "digest", "identity",
    "identity_problems", "label_spans", "prediction_text", "prepare_visit", "regime_of", "spec", "target_text",
    "visible_line",
]
