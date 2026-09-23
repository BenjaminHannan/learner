"""Visits -> stream text, per-question metadata, QA examples and audit records.

Stream format (one line per non-silent record; visits separated by a blank line):
  [world] <narration or rule>
  [teacher] <teacher sentence>
  [question] <question> [answer] <canonical answer> [feedback] <t.right sentence>
A teacher record whose inner record is a question (t.ask, t.quiz_later) is
written as a question line with the teacher's wrapper around the question.

Line numbers in metadata are 0-based indices into the visit's text lines
(shards convert them to indices into the shard file). The visible window of a
question is the run of text lines just before it that fits in `window_chars`.
"""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from functools import lru_cache
import importlib
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence, Union

from learnlab.leaks import LeakReport, QAExample, _contains, leak_report, words
from learnlab.splits import SplitRegistry, audit_examples

from .render import PatternSource, Renderer, skeleton, village_registry

WINDOW_CHARS = 2048                 # about 512 tokens at ~4 characters per token
CHOICE_QTYPES = frozenset({"Q13"})  # the question names the answer among its options
NOT_TOLD = "not told"
# The class of each bank's answers: leak_report's nulls (one guess among K answers) hold within one class.
ANSWER_CLASSES = {
    "q.where_object": "place", "q.where_person": "place", "q.where_before": "place", "q.where_at_time": "place",
    "q.next_to": "place", "q.compare_count": "place", "q.who_has": "person", "q.yn_at": "yes/no",
    "q.yn_has": "yes/no", "q.yn_in": "yes/no", "q.count_at": "count", "q.count_held": "count",
    "q.direction": "direction", "q.in_container": "contents", "q.what_if": "what if", "q.why_at": "why",
    "q.plan_get": "plan",
}


@dataclass
class RenderedVisit:
    id: str
    split: str
    lines: list[str]
    questions: list[dict[str, Any]]
    provenance: dict[str, tuple[str, ...]]
    units: list[str]                 # one per filled pattern, for the audit
    line_templates: list[list[str]]  # template ids used on each text line

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    def audit_record(self) -> dict[str, Any]:
        """What `splits.audit_examples` checks: split, provenance, and each pattern instance on its own line."""
        return {"id": self.id, "split": self.split, "provenance": self.provenance, "text": "\n".join(self.units)}


@lru_cache(maxsize=None)
def default_source() -> PatternSource:
    return PatternSource.load()


def default_registry(source: PatternSource) -> SplitRegistry:
    """The pattern families plus the world's rule families."""
    from .scheduler import world_families
    return village_registry(source, world_families())


def render_visit(
    visit: Mapping[str, Any],
    source: Optional[PatternSource] = None,
    registry: Optional[SplitRegistry] = None,
    *,
    window_chars: int = WINDOW_CHARS,
) -> RenderedVisit:
    """Render one world visit; the world's provenance is re-checked and recorded through the same view."""
    source = source or default_source()
    registry = registry if registry is not None else default_registry(source)
    split = visit["split"]
    view = registry.view(split)
    for axis, items in (visit.get("provenance") or {}).items():
        for item in ((items,) if isinstance(items, str) else items):
            view.use(axis, item)
    renderer = Renderer(source, visit, view)
    lines: list[str] = []
    units: list[str] = []
    line_templates: list[list[str]] = []
    text_of: dict[int, int] = {}
    asked: list[tuple[Mapping[str, Any], int, Any]] = []
    for record in visit["records"]:
        out = renderer.line(record)
        if out is None:
            continue
        index = len(lines)
        lines.append(out.text)
        units.extend(out.units)
        line_templates.append(out.templates)
        text_of.setdefault(record["line"], index)
        inner = record.get("inner")
        if isinstance(inner, Mapping) and "line" in inner:
            text_of.setdefault(inner["line"], index)
        if out.question is not None:
            asked.append((inner if record["kind"] == "teacher" else record, index, out))

    ends = [0]
    for line in lines:
        ends.append(ends[-1] + len(line) + 1)
    questions = []
    for question, index, out in asked:
        start = bisect_left(ends, ends[index] - window_chars, 0, index)
        evidence = list(question.get("evidence") or ())
        evidence_text = [text_of.get(line) for line in evidence]
        visible = all(t is not None and start <= t < index for t in evidence_text) and not question.get("long_range")
        long_range = any(t is not None and t < start for t in evidence_text) or bool(question.get("long_range"))
        shown = sorted({t for t in evidence_text if t is not None})
        questions.append({
            "id": question["id"], "visit": visit["id"], "split": split, "qtype": question["qtype"],
            "base_qtype": question.get("base_qtype", question["qtype"]), "bank": question["bank"],
            "depth": question.get("depth"), "visible": visible, "long_range": long_range,
            "evidence": evidence, "evidence_text_lines": evidence_text, "text_line": index, "context_start": start,
            "question": out.question, "answer": question["answer"], "twin": question.get("twin"),
            "template": next(t for t in out.templates if source.bank[t] == question["bank"]), "templates": list(out.templates),
            "evidence_templates": list(dict.fromkeys(t for i in shown for t in line_templates[i])),
            "style": out.style, "families": list(question.get("families") or ()),
            "rule_applications": question.get("rule_applications", 0), "knowable": question.get("knowable", True),
            "action": ((question.get("slots") or {}).get("action") or {}).get("bank"),
        })
    return RenderedVisit(str(visit["id"]), split, lines, questions, view.provenance(), units, line_templates)


def to_qa_examples(
    visit: Union[RenderedVisit, Mapping[str, Any]],
    *,
    source: Optional[PatternSource] = None,
    registry: Optional[SplitRegistry] = None,
    window_chars: int = WINDOW_CHARS,
    include_choice: bool = False,
) -> list[QAExample]:
    """One QAExample per question: the visible window before it, the question text and the canonical answer.

    Choice questions (Q13 names both places) are left out unless `include_choice`,
    since their answer is necessarily in the question.
    """
    rendered = visit if isinstance(visit, RenderedVisit) else render_visit(visit, source, registry, window_chars=window_chars)
    examples = []
    for q in rendered.questions:
        if q["qtype"] in CHOICE_QTYPES and not include_choice:
            continue
        # The base type: "Q10" would name the answer ("not told") outright.
        meta = {"template": q["template"], "style": q["style"] or "", "qtype": q["base_qtype"], "bank": q["bank"],
                "rule_family": "+".join(q["families"]) or "none"}
        if q.get("action"):
            meta["action"] = q["action"]  # what a hypothetical does; the question says it too
        context = "\n".join(rendered.lines[q["context_start"]:q["text_line"]])
        examples.append(QAExample(context, q["question"], str(q["answer"]), meta, group=str(rendered.id)))
    return examples


SPECIAL_ANSWERS = frozenset((NOT_TOLD, "nobody", "nothing", "nothing would happen", "zero"))


def answer_class(example: QAExample) -> str:
    """The class whose answers are one guess among the same options. A hypothetical's options depend on its
    action (someone going: a follower; an opening: it opens or stays shut), so each action is its own class."""
    name = ANSWER_CLASSES.get(example.meta.get("bank", ""), "rule")
    if name == "what if" and example.meta.get("action"):
        return f"what if: {example.meta['action']}"
    return name


def effect_only(example: QAExample) -> QAExample:
    """A hypothetical's answer without the thing the question already names: "the sack would stay shut" after
    "... opened the sack?" becomes "it would stay shut". The thing is given; only the effect is to be found."""
    subject, sep, effect = example.answer.partition(" would ")
    if not sep or not subject or not _contains(words(example.question), words(subject)):
        return example
    return QAExample(example.context, example.question, f"it would {effect}", example.meta, example.group)


def leak_reports(train: Sequence[QAExample], test: Sequence[QAExample], **options: Any) -> dict[str, LeakReport]:
    """`learnlab.leaks.leak_report` per answer class, since its nulls (one guess among K answers) assume one class.

    Pooled, "yes" or "two" beats one-in-K chance just by being a yes/no or count answer. An answer open to
    nearly every question of its bank ("not told", "nobody", "nothing", "nothing would happen", "zero") is
    tested on its own: questions of the same bank answered with it and otherwise, balanced 1:1 within each
    bank and labelled with it or "other", so the detectors test whether wording or context gives it away.
    The class reports then hold the other answers only. "rule_family" is left out of the metadata:
    it is read off the answer's own derivation, and the learner never sees it. A hypothetical's answer is
    tested without the thing its question names (`effect_only`).
    """
    def public(e: QAExample) -> QAExample:
        return QAExample(e.context, e.question, e.answer, {k: v for k, v in e.meta.items() if k != "rule_family"},
                         e.group)

    train, test = ([effect_only(public(e)) if answer_class(e).startswith("what if") else public(e)
                    for e in examples] for examples in (train, test))
    reports = {}
    for name in sorted({answer_class(e) for e in test}):
        mine = [[e for e in examples if answer_class(e) == name and e.answer not in SPECIAL_ANSWERS]
                for examples in (train, test)]
        if mine[0] and mine[1]:
            reports[name] = leak_report(mine[0], mine[1], **options)
    for special in sorted(SPECIAL_ANSWERS):
        sets = [_balanced(examples, special) for examples in (train, test)]
        if sets[0] and sets[1]:
            reports[special] = leak_report(sets[0], sets[1], **options)
    return reports


def _balanced(examples: Sequence[QAExample], special: str) -> list[QAExample]:
    """Per bank, as many questions answered `special` as answered otherwise (relabelled "other"), interleaved."""
    by_bank: dict[str, tuple[list[QAExample], list[QAExample]]] = {}
    for e in examples:
        pair = by_bank.setdefault(e.meta.get("bank", ""), ([], []))
        pair[e.answer != special].append(
            e if e.answer == special else QAExample(e.context, e.question, "other", e.meta, e.group))
    out = []
    for hits, others in by_bank.values():
        size = min(len(hits), len(others))
        out.extend(e for pair in zip(hits[:size], others[:size]) for e in pair)
    return out


def split_vocab(source: PatternSource, names: Iterable[str] = ()) -> dict[str, Any]:
    """Surface forms for `splits.audit_examples`: every pattern (template axis) and the names.

    Teacher patterns are template items with their style's split, so a foreign
    style's wording is caught on the template axis, where an own-split pattern
    that explains a whole unit exempts it; a separate teacher_style text scan
    would flag a one-word wrapper ("Rule: {rule}") inside any question unit.
    Styles are still checked through provenance. A pattern whose skeleton
    (literal words and fields) another split shares cannot be told apart in
    text, so it is left to the provenance check; so is one with no literal words.
    """
    splits: dict[tuple[str, ...], set[str]] = {}
    for pid, text in source.text.items():
        splits.setdefault(skeleton(text), set()).add(source.split[pid])

    def distinct(text: str) -> bool:
        shape = skeleton(text)
        return any(part != "\0" for part in shape) and len(splits[shape]) == 1

    vocab: dict[str, Any] = {"template": {pid: text for pid, text in source.text.items() if distinct(text)}}
    names = list(names)
    if names:
        vocab["name"] = names
    return vocab


def audit(
    visits: Sequence[RenderedVisit], registry: SplitRegistry, source: Optional[PatternSource] = None,
    names: Iterable[str] = (),
) -> dict[str, Any]:
    """`splits.audit_examples` over rendered visits; SplitLeak on any cross-split item."""
    return audit_examples([v.audit_record() for v in visits], registry, text_of=lambda r: r["text"],
                          vocab=split_vocab(source or default_source(), names))


def stream_text(visits: Iterable[RenderedVisit]) -> str:
    """Visits as one stream: each visit's lines, then a blank line."""
    return "".join(v.text + "\n\n" for v in visits)


def load_callable(spec: str) -> Callable[..., Any]:
    """'package.module:function' -> the function."""
    module, _, name = spec.partition(":")
    return getattr(importlib.import_module(module), name)


__all__ = [
    "ANSWER_CLASSES", "CHOICE_QTYPES", "RenderedVisit", "SPECIAL_ANSWERS", "answer_class", "effect_only", "leak_reports", "WINDOW_CHARS", "audit", "default_registry", "default_source", "load_callable", "render_visit",
    "split_vocab", "stream_text", "to_qa_examples",
]
