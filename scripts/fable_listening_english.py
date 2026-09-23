# fable_listening_english.py
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request


DEFAULT_BASE_URL = os.environ.get(
    "FABLE_LLM_BASE_URL",
    "http://127.0.0.1:18081",
)
DEFAULT_MODEL = os.environ.get(
    "FABLE_LLM_MODEL",
    "local-model",
)

ACTS = [
    "person",
    "alias",
    "teach",
    "correct",
    "ask",
    "forget",
    "quote",
    "yes",
    "no",
    "pick",
    "undo",
    "smalltalk",
    "unsure",
]

WRITE_ACTS = {
    "person",
    "alias",
    "teach",
    "correct",
    "forget",
}

PARSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["items", "unsure", "unsure_reason"],
    "properties": {
        "items": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "act",
                    "subject",
                    "relation_path",
                    "relation_surface",
                    "value",
                    "value_kind",
                    "alias",
                    "canonical",
                    "choice",
                    "text",
                    "confidence",
                ],
                "properties": {
                    "act": {
                        "type": "string",
                        "enum": ACTS,
                    },
                    "subject": {
                        "type": ["string", "null"],
                    },
                    "relation_path": {
                        "type": "array",
                        "maxItems": 8,
                        "items": {"type": "string"},
                    },
                    "relation_surface": {
                        "type": "array",
                        "maxItems": 8,
                        "items": {"type": "string"},
                    },
                    "value": {
                        "type": ["string", "null"],
                    },
                    "value_kind": {
                        "type": "string",
                        "enum": [
                            "literal",
                            "person",
                            "none",
                        ],
                    },
                    "alias": {
                        "type": ["string", "null"],
                    },
                    "canonical": {
                        "type": ["string", "null"],
                    },
                    "choice": {
                        "type": ["string", "null"],
                    },
                    "text": {
                        "type": ["string", "null"],
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                },
            },
        },
        "unsure": {
            "type": "boolean",
        },
        "unsure_reason": {
            "type": "string",
        },
    },
}


SYSTEM_PROMPT = r"""
You are Fable's English ears. Convert the user's utterance into typed intents;
never answer it and never invent a name or value. Final output must match the
provided JSON schema.

A subject/value denoting a person must copy the exact surface name from the
utterance, except first person maps to Ben and second person maps to self.
Third-person pronouns may resolve only when their explicit antecedent occurs in
the same utterance; otherwise use unsure.

relation_surface must copy words from the utterance. relation_path contains
canonical keys. Normalize:
live/reside/moved-to->city; from/comes-from->origin; born->birthplace;
mom/mother->mother; dad/father->father; work-at/work-for->employer;
trained-on/training-data->training_data; made/created->creator;
favorite-colour/color->favorite_color.
Unknown relations become lowercase_snake_case of relation_surface.

Statements teach. Use correct only for explicit correction language such as
actually, I meant, correction, sorry, or "not X but Y". Questions ask.
Reported speech, hypotheticals, and unsupported negated facts use quote and copy
the complete utterance. Chit-chat uses smalltalk. Natural yes/no/pick is legal
only when pending_state exists. Multiple asserted facts become multiple items.
If uncertain, set unsure=true and emit no actionable item.

Semantic examples:
1 Mira lives in Lisbon. => teach(Mira,city=Lisbon; surface="lives in")
2 Actually Mira lives in Paris. => correct(Mira,city=Paris)
3 Mira's mother is Ana. => teach(Mira,mother->Ana)
4 Where does Mira's mother live? => ask(Mira,mother,city)
5 If Mira lived in Paris, she'd smile. => quote(full utterance)
6 Mira said she lives in Paris. => quote(full utterance)
7 Hi, how are you? => smalltalk
8 I live in Hanover. => teach(Ben,city=Hanover)
9 What were you trained on? => ask(self,training_data)
10 Mary Jane lives in New York. => teach(Mary Jane,city=New York)
11 [pending yes/no] Yep, that's right. => yes
12 [pending E0002,E0007] The second one. => pick(E0007)
""".strip()


RELATION_MAP = {
    "city": "city",
    "is in": "city",
    "'s in": "city",
    "\u2019s in": "city",
    "town": "city",
    "live": "city",
    "lives": "city",
    "live in": "city",
    "lives in": "city",
    "reside": "city",
    "resides": "city",
    "reside in": "city",
    "resides in": "city",
    "move to": "city",
    "moved to": "city",

    "from": "origin",
    "is from": "origin",
    "come from": "origin",
    "comes from": "origin",
    "origin": "origin",
    "hometown": "origin",

    "born": "birthplace",
    "born in": "birthplace",
    "birthplace": "birthplace",

    "mother": "mother",
    "mom": "mother",
    "mum": "mother",

    "father": "father",
    "dad": "father",

    "work": "employer",
    "works": "employer",
    "work at": "employer",
    "works at": "employer",
    "work for": "employer",
    "works for": "employer",
    "employer": "employer",

    "trained on": "training_data",
    "training data": "training_data",
    "training_data": "training_data",

    "made": "creator",
    "made you": "creator",
    "created": "creator",
    "created by": "creator",
    "creator": "creator",

    "favorite color": "favorite_color",
    "favourite color": "favorite_color",
    "favorite colour": "favorite_color",
    "favourite colour": "favorite_color",

    "age": "age",
    "aged": "age",
    "old": "age",
    "years old": "age",
    "year old": "age",
    "friend": "friend",
    "best friend": "friend",
    "brother": "sibling",
    "sister": "sibling",
    "sibling": "sibling",
}

KNOWN_RELATIONS = set(RELATION_MAP.values())

REPORTED_SPEECH_MARKERS = (
    " said ",
    " says ",
    " told me ",
    " i heard ",
    " according to ",
    " claims ",
)


class ParseRejected(ValueError):
    """Model output failed a deterministic safety check."""


def blank_item(act: str, confidence: float = 1.0, **changes) -> dict:
    item = {
        "act": act,
        "subject": None,
        "relation_path": [],
        "relation_surface": [],
        "value": None,
        "value_kind": "none",
        "alias": None,
        "canonical": None,
        "choice": None,
        "text": None,
        "confidence": confidence,
    }
    item.update(changes)
    return item


def _snake(text: str) -> str:
    text = text.casefold().strip()
    text = re.sub(
        r"[^\w]+",
        "_",
        text,
        flags=re.UNICODE,
    ).strip("_")
    return text


def canonical_relation(surface: str) -> str:
    key = re.sub(
        r"\s+",
        " ",
        surface.casefold().strip(" .?!,:;\"'"),
    )
    return RELATION_MAP.get(
        key,
        _snake(key),
    )


def _contains(text: str, fragment: str) -> bool:
    return (
        isinstance(fragment, str)
        and bool(fragment)
        and fragment.casefold() in text.casefold()
    )


def _has_first_person(text: str) -> bool:
    return bool(
        re.search(
            r"\b(i|i'm|i’m|me|my|mine|myself)\b",
            text,
            re.I,
        )
    )


def _has_second_person(text: str) -> bool:
    return bool(
        re.search(
            r"\b(you|you're|you’re|your|yours|yourself)\b",
            text,
            re.I,
        )
    )


def _has_correction_cue(text: str) -> bool:
    t = text.casefold()

    if any(
        cue in t
        for cue in (
            "actually",
            "i meant",
            "correction",
            "sorry",
            "wait,",
        )
    ):
        return True

    padded = f" {t} "
    if " not " in padded and (
        " but " in padded
        or " now" in t
    ):
        return True

    # "is not Ingrid, it's Freja" (held-out run 1)
    if (
        " not " in padded
        or " no longer " in padded
    ) and re.search(
        r"\b(it's|it\u2019s|it is|i'm|i\u2019m|"
        r"i am|she's|he's|they're)\b",
        t,
    ):
        return True

    # "Noa lives in Eilat, not Haifa"
    if re.search(r",\s*not\s+\S", t):
        return True

    return False


def _pending_ids(pending_state) -> set[str]:
    if pending_state is None:
        return set()

    try:
        raw = json.dumps(
            pending_state,
            ensure_ascii=False,
            default=str,
        )
    except Exception:
        raw = str(pending_state)

    return set(
        re.findall(
            r"\bE\d{4,}\b",
            raw,
        )
    )


def _jsonable(value):
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


def _compact_known_names(known_names) -> list[str]:
    if known_names is None:
        return []

    if isinstance(known_names, dict):
        values = list(known_names.keys())
    elif isinstance(
        known_names,
        (list, tuple, set),
    ):
        values = list(known_names)
    else:
        values = [known_names]

    out = []

    for value in values:
        if isinstance(value, str):
            out.append(value)

        elif isinstance(value, dict):
            for key in (
                "name",
                "alias",
                "display_name",
            ):
                candidate = value.get(key)
                if isinstance(candidate, str):
                    out.append(candidate)

    return out[:200]


def _require_string(item: dict, key: str) -> None:
    value = item[key]

    if not isinstance(value, str) or not value:
        raise ParseRejected(
            f"{item['act']} requires non-empty {key}"
        )


def _require_none(item: dict, *keys: str) -> None:
    for key in keys:
        if item[key] is not None:
            raise ParseRejected(
                f"{item['act']}.{key} must be null"
            )


def _require_empty_relations(item: dict) -> None:
    if (
        item["relation_path"]
        or item["relation_surface"]
    ):
        raise ParseRejected(
            f"{item['act']} must not contain relations"
        )


def _require_relation_count(
    item: dict,
    low: int,
    high: int,
) -> None:
    n = len(item["relation_path"])

    if not low <= n <= high:
        raise ParseRejected(
            f"{item['act']} requires "
            f"{low}..{high} relation hops"
        )


def _validate_shape(
    doc: dict,
    utterance: str,
    pending_state,
) -> None:
    if not isinstance(doc, dict):
        raise ParseRejected(
            "top level must be an object"
        )

    expected_top = {
        "items",
        "unsure",
        "unsure_reason",
    }

    if set(doc) != expected_top:
        raise ParseRejected(
            "wrong top-level JSON fields"
        )

    if (
        not isinstance(doc["items"], list)
        or len(doc["items"]) > 8
    ):
        raise ParseRejected(
            "items must be an array of <= 8"
        )

    if not isinstance(doc["unsure"], bool):
        raise ParseRejected(
            "unsure must be boolean"
        )

    if not isinstance(
        doc["unsure_reason"],
        str,
    ):
        raise ParseRejected(
            "unsure_reason must be string"
        )

    item_fields = {
        "act",
        "subject",
        "relation_path",
        "relation_surface",
        "value",
        "value_kind",
        "alias",
        "canonical",
        "choice",
        "text",
        "confidence",
    }

    meaningful_acts = []

    for item in doc["items"]:
        if (
            not isinstance(item, dict)
            or set(item) != item_fields
        ):
            raise ParseRejected(
                "wrong item JSON fields"
            )

        act = item["act"]
        meaningful_acts.append(act)

        if act not in ACTS:
            raise ParseRejected(
                f"unknown act {act!r}"
            )

        confidence = item["confidence"]

        if (
            not isinstance(
                confidence,
                (int, float),
            )
            or isinstance(confidence, bool)
            or not 0 <= confidence <= 1
        ):
            raise ParseRejected(
                "confidence must be in [0,1]"
            )

        if item["value_kind"] not in {
            "literal",
            "person",
            "none",
        }:
            raise ParseRejected(
                "invalid value_kind"
            )

        if not isinstance(
            item["relation_path"],
            list,
        ):
            raise ParseRejected(
                "relation_path must be array"
            )

        if not isinstance(
            item["relation_surface"],
            list,
        ):
            raise ParseRejected(
                "relation_surface must be array"
            )

        if (
            len(item["relation_path"])
            != len(item["relation_surface"])
        ):
            raise ParseRejected(
                "relation path/surface lengths differ"
            )

        if len(
            item["relation_path"]
        ) > 8:
            raise ParseRejected(
                "too many relation hops"
            )

        if act == "person":
            _require_string(
                item,
                "subject",
            )
            _require_empty_relations(item)
            _require_none(
                item,
                "value",
                "alias",
                "canonical",
                "choice",
            )

        elif act == "alias":
            _require_string(
                item,
                "alias",
            )
            _require_string(
                item,
                "canonical",
            )
            _require_empty_relations(item)
            _require_none(
                item,
                "subject",
                "value",
                "choice",
            )

        elif act in {
            "teach",
            "correct",
        }:
            _require_string(
                item,
                "subject",
            )
            _require_relation_count(
                item,
                1,
                1,
            )
            _require_string(
                item,
                "value",
            )

            if item["value_kind"] not in {
                "literal",
                "person",
            }:
                raise ParseRejected(
                    f"{act} requires a value"
                )

            _require_none(
                item,
                "alias",
                "canonical",
                "choice",
            )

        elif act == "ask":
            _require_string(
                item,
                "subject",
            )
            _require_relation_count(
                item,
                1,
                8,
            )
            _require_none(
                item,
                "value",
                "alias",
                "canonical",
                "choice",
            )

            if item["value_kind"] != "none":
                raise ParseRejected(
                    "ask value_kind must be none"
                )

        elif act == "forget":
            _require_string(
                item,
                "subject",
            )
            _require_relation_count(
                item,
                1,
                1,
            )
            _require_none(
                item,
                "value",
                "alias",
                "canonical",
                "choice",
            )

        elif act == "quote":
            _require_string(
                item,
                "text",
            )

            if item["text"] != utterance:
                raise ParseRejected(
                    "quote.text must exactly copy "
                    "the utterance"
                )

        elif act in {
            "yes",
            "no",
        }:
            if pending_state is None:
                raise ParseRejected(
                    f"{act} is illegal without "
                    "pending state"
                )

        elif act == "pick":
            _require_string(
                item,
                "choice",
            )

            if pending_state is None:
                raise ParseRejected(
                    "pick is illegal without "
                    "pending state"
                )

            choices = _pending_ids(
                pending_state
            )

            if (
                choices
                and item["choice"]
                not in choices
            ):
                raise ParseRejected(
                    "pick ID is not pending"
                )

        for (
            surface,
            relation,
        ) in zip(
            item["relation_surface"],
            item["relation_path"],
        ):
            if (
                not isinstance(surface, str)
                or not isinstance(
                    relation,
                    str,
                )
            ):
                raise ParseRejected(
                    "relations must be strings"
                )

            expected = canonical_relation(
                surface
            )

            if (
                relation != expected
                and _relation_grounded(
                    relation,
                    utterance,
                )
            ):
                # Real Qwen copies sloppy spans
                # ("mother is", "mother's"). For a
                # KNOWN relation the software checks
                # the sentence itself instead.
                continue

            if relation != expected:
                raise ParseRejected(
                    f"relation {relation!r} "
                    f"does not match copied "
                    f"surface {surface!r}; "
                    f"expected {expected!r}"
                )

    control = [
        act
        for act in meaningful_acts
        if act in {
            "yes",
            "no",
            "pick",
            "undo",
        }
    ]

    if control and len(
        [
            x
            for x in meaningful_acts
            if x not in {
                "smalltalk",
                "unsure",
            }
        ]
    ) != 1:
        raise ParseRejected(
            "control responses must stand alone"
        )

    has_quote = (
        "quote" in meaningful_acts
    )
    has_write = any(
        act in WRITE_ACTS
        for act in meaningful_acts
    )

    if has_quote and has_write:
        raise ParseRejected(
            "quote may not coexist with a write"
        )

    if doc["unsure"]:
        actionable = [
            act
            for act in meaningful_acts
            if act not in {
                "unsure",
                "smalltalk",
            }
        ]

        if actionable:
            raise ParseRejected(
                "unsure parse may not contain "
                "an actionable item"
            )


def _validate_copy_constraints(
    doc: dict,
    utterance: str,
) -> None:
    first_person = _has_first_person(
        utterance
    )
    second_person = _has_second_person(
        utterance
    )

    def copied(
        value,
        role: str,
    ) -> None:
        if value is None:
            return

        if role in {
            "subject",
            "person_value",
        }:
            if (
                value == "Ben"
                and first_person
            ):
                return

            if (
                value == "self"
                and second_person
            ):
                return

        if not _contains(
            utterance,
            value,
        ):
            raise ParseRejected(
                "copy constraint rejected "
                f"{role} {value!r}"
            )

    for item in doc["items"]:
        act = item["act"]

        if act in {
            "person",
            "teach",
            "correct",
            "ask",
            "forget",
        }:
            copied(
                item["subject"],
                "subject",
            )

        if act == "alias":
            copied(
                item["alias"],
                "alias",
            )
            copied(
                item["canonical"],
                "canonical",
            )

        if act in {
            "teach",
            "correct",
        }:
            role = (
                "person_value"
                if item["value_kind"]
                == "person"
                else "value"
            )

            copied(
                item["value"],
                role,
            )

        for surface in item[
            "relation_surface"
        ]:
            if _relation_grounded(
                surface,
                utterance,
            ):
                # Rebuilt by software from a KNOWN
                # relation whose wording is present.
                continue

            copied(
                surface,
                "relation_surface",
            )


def _validate_nonwrite_guards(
    doc: dict,
    utterance: str,
) -> None:
    writes = [
        item
        for item in doc["items"]
        if item["act"] in WRITE_ACTS
    ]

    if not writes:
        return

    lower = utterance.casefold()
    padded = f" {lower} "

    if "?" in utterance:
        raise ParseRejected(
            "question may not write"
        )

    if re.match(
        r"^\s*(if\b|suppose\b|imagine\b)",
        lower,
    ):
        raise ParseRejected(
            "hypothetical may not write"
        )

    if any(
        marker in padded
        for marker
        in REPORTED_SPEECH_MARKERS
    ):
        raise ParseRejected(
            "reported speech may not write"
        )

    negation = bool(
        re.search(
            r"\b("
            r"not|never|no longer|"
            r"isn't|isn’t|"
            r"doesn't|doesn’t|"
            r"wasn't|wasn’t"
            r")\b",
            lower,
        )
    )

    if (
        negation
        and not all(
            item["act"] == "correct"
            for item in writes
        )
    ):
        raise ParseRejected(
            "unsupported negation "
            "may not write"
        )

    has_correct = any(
        item["act"] == "correct"
        for item in writes
    )

    if (
        has_correct
        and not _has_correction_cue(
            utterance
        )
    ):
        raise ParseRejected(
            "correct requires explicit "
            "correction language"
        )

    has_teach = any(
        item["act"] == "teach"
        for item in writes
    )

    if (
        has_teach
        and _has_correction_cue(
            utterance
        )
    ):
        raise ParseRejected(
            "correction language may not "
            "be downgraded to teach"
        )


def validate_model_output(
    doc: dict,
    utterance: str,
    pending_state=None,
) -> None:
    _validate_shape(
        doc,
        utterance,
        pending_state,
    )

    _validate_copy_constraints(
        doc,
        utterance,
    )

    _validate_nonwrite_guards(
        doc,
        utterance,
    )


def _atom(value: str) -> str:
    """
    Single-token values preserve M1 syntax.

    Multi-word/special values use JSON string syntax.
    M1 therefore needs a small quoted-atom parser.
    """
    if (
        re.fullmatch(
            r"[^\s=]+",
            value,
        )
        and '"' not in value
        and "\\" not in value
    ):
        return value

    return json.dumps(
        value,
        ensure_ascii=False,
    )


def render_item(
    item: dict,
    utterance: str,
) -> str | None:
    act = item["act"]

    if act == "person":
        return (
            f"person "
            f"{_atom(item['subject'])}"
        )

    if act == "alias":
        return (
            f"alias "
            f"{_atom(item['alias'])} = "
            f"{_atom(item['canonical'])}"
        )

    if act in {
        "teach",
        "correct",
    }:
        operator = (
            "->"
            if item["value_kind"]
            == "person"
            else "="
        )

        return (
            f"{act} "
            f"{_atom(item['subject'])} "
            f"{item['relation_path'][0]} "
            f"{operator} "
            f"{_atom(item['value'])}"
        )

    if act == "ask":
        path = " ".join(
            item["relation_path"]
        )

        return (
            f"ask "
            f"{_atom(item['subject'])} "
            f"{path}"
        )

    if act == "forget":
        return (
            f"forget "
            f"{_atom(item['subject'])} "
            f"{item['relation_path'][0]}"
        )

    if act == "quote":
        return (
            f"quote {utterance}"
        )

    if act in {
        "yes",
        "no",
    }:
        return act

    if act == "pick":
        return (
            f"pick {item['choice']}"
        )

    if act == "undo":
        return "undo last"

    if act in {
        "smalltalk",
        "unsure",
    }:
        return None

    raise ParseRejected(
        f"cannot render {act!r}"
    )


def render_lines(
    doc: dict,
    utterance: str,
) -> list[str]:
    result = []

    for item in doc["items"]:
        line = render_item(
            item,
            utterance,
        )

        if line is not None:
            result.append(line)

    return result


def confirm_before_write_policy(
    doc: dict,
) -> bool:
    """
    Hook for the English adapter's extra
    echo-back confirmation.

    Existing Listening conflict/ambiguity
    confirmation still remains authoritative.
    """
    writes = [
        item
        for item in doc["items"]
        if item["act"] in WRITE_ACTS
    ]

    if not writes:
        return False

    # A bundle is easier to mis-hear.
    if len(writes) > 1:
        return True

    # Nicknames: which name is the new one is
    # easy to get backwards (round 2, item 143),
    # so they are always echoed first.
    if any(
        item["act"] == "alias"
        for item in writes
    ):
        return True

    if min(
        float(item["confidence"])
        for item in writes
    ) < 0.98:
        return True

    # Unknown relation normalization is
    # semantically riskier.
    for item in writes:
        if any(
            relation
            not in KNOWN_RELATIONS
            for relation
            in item["relation_path"]
        ):
            return True

    return False


def _decode_model_content(
    response_obj: dict,
) -> dict:
    try:
        content = (
            response_obj[
                "choices"
            ][0][
                "message"
            ][
                "content"
            ]
        )
    except (
        KeyError,
        IndexError,
        TypeError,
    ) as exc:
        raise ParseRejected(
            "server response had no "
            "choices[0].message.content"
        ) from exc

    if isinstance(content, dict):
        return content

    if not isinstance(content, str):
        raise ParseRejected(
            "model content was not text"
        )

    text = content.strip()

    # Should not occur with JSON-schema
    # decoding, but harmless defensive code.
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    try:
        return json.loads(
            text.strip()
        )
    except json.JSONDecodeError as exc:
        raise ParseRejected(
            f"invalid model JSON: {exc}"
        ) from exc


def _request_doc(
    utterance: str,
    pending_state,
    known_names,
    base_url: str,
    model: str,
) -> dict:
    context = {
        "utterance": utterance,
        "pending_state": _jsonable(
            pending_state
        ),
        "known_names": (
            _compact_known_names(
                known_names
            )
        ),
    }

    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 900,
        # Qwen "thinks" by default and can spend
        # the whole budget before any JSON.
        "chat_template_kwargs": {
            "enable_thinking": False,
        },
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps(
                    context,
                    ensure_ascii=False,
                ),
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": (
                    "fable_listening_parse"
                ),
                "strict": True,
                "schema": PARSE_SCHEMA,
            },
        },
    }

    url = (
        base_url.rstrip("/")
        + "/v1/chat/completions"
    )

    request = urllib.request.Request(
        url,
        data=json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            "Content-Type":
                "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=120,
        ) as response:
            response_obj = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

    except urllib.error.HTTPError as exc:
        body = exc.read().decode(
            "utf-8",
            "replace",
        )

        raise RuntimeError(
            f"llama.cpp HTTP "
            f"{exc.code}: "
            f"{body[:1000]}"
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            "cannot reach llama.cpp at "
            f"{base_url}: {exc.reason}"
        ) from exc

    return _decode_model_content(
        response_obj
    )


UNDO_PATTERN = re.compile(
    r"^\s*((can|could|would)\s+you\s+|please\s+|ok\s+|just\s+|"
    r"oops[,!.]?\s+|wait[,!.]?\s+|sorry[,!.]?\s+)*"
    r"undo"
    r"(\s+(that|the|my|it|this|last|save|saved|"
    r"one|change|fact|thing|entry|please))*"
    r"\s*[.!?]?\s*$",
    re.IGNORECASE,
)

YES_PATTERN = re.compile(
    r"^\s*(yes|yep|yeah|yup|y|correct|right|"
    r"sure|ok|okay|do it|save it|please do)"
    r"(\s+(please|thanks|that's right|"
    r"that\u2019s right))?\s*[.!]?\s*$",
    re.IGNORECASE,
)

NO_PATTERN = re.compile(
    r"^\s*(no|nope|nah|n|don't|don\u2019t|"
    r"cancel|never mind|nevermind)"
    r"(\s+(thanks|please|don't save it|"
    r"don\u2019t save it))?\s*[.!]?\s*$",
    re.IGNORECASE,
)

PERSON_LINE_PATTERN = re.compile(
    r"^\s*person\s*:\s*(\S.{0,78}?)\s*$",
    re.IGNORECASE,
)

ALIAS_SUBJECT_FIRST = re.compile(
    r"\b(short for|another name for|"
    r"a nickname for|nickname for)\b",
    re.IGNORECASE,
)

ALIAS_VALUE_FIRST = re.compile(
    r"\b(also known as|aka|goes by|"
    r"answers to|is called|nicknamed|"
    r"call (him|her|them))\b",
    re.IGNORECASE,
)

PERSON_RELATIONS = {
    "mother",
    "father",
    "creator",
    "friend",
    "sibling",
}


def _relation_grounded(
    relation: str,
    utterance: str,
) -> bool:
    """
    True when a KNOWN relation has one of its
    listed English wordings inside the sentence.
    Deterministic; does not trust the model.
    """
    if relation not in KNOWN_RELATIONS:
        return False

    if relation == "age" and re.search(
        r"\b(is|am|was|turned|turns|"
        r"'s|'m|\u2019s|\u2019m)\s*\d{1,3}\b",
        utterance.casefold(),
    ):
        return True

    text = " " + re.sub(
        r"\s+",
        " ",
        utterance.casefold(),
    ) + " "

    for surface, key in RELATION_MAP.items():
        if key != relation:
            continue

        left = (
            ""
            if surface[:1] in "'\u2019"
            else r"(?<![\w])"
        )

        if re.search(
            left
            + re.escape(surface)
            + r"(?![\w])",
            text,
        ):
            return True

    return False


def _must_not_write(utterance: str) -> bool:
    """
    Same tests as _validate_nonwrite_guards:
    hypothetical, reported speech, or a bare
    negation with no correction wording.
    """
    lower = utterance.casefold()
    padded = f" {lower} "

    if re.match(
        r"^\s*(if\b|suppose\b|imagine\b)",
        lower,
    ):
        return True

    if any(
        marker in padded
        for marker in REPORTED_SPEECH_MARKERS
    ):
        return True

    negation = re.search(
        r"\b(not|never|no longer|isn't|isn\u2019t|"
        r"doesn't|doesn\u2019t|wasn't|wasn\u2019t)\b",
        lower,
    )

    return bool(
        negation
        and not _has_correction_cue(utterance)
    )


def _repair_harmless_fields(
    doc,
    utterance: str = "",
) -> None:
    """
    Found with real Qwen (2026-09-21). Bookkeeping
    the software can decide is taken away from the
    model. Every repair either removes a write or
    leaves the written subject/relation/value
    untouched, so no repair can invent a fact.
    """
    if not isinstance(doc, dict):
        return

    items = doc.get("items")
    if not isinstance(items, list):
        return

    writes = [
        item
        for item in items
        if isinstance(item, dict)
        and item.get("act") in WRITE_ACTS
    ]

    if (
        writes
        and "?" not in utterance
        and _must_not_write(utterance)
    ):
        # Store the raw sentence, not a fact.
        doc["items"] = [
            blank_item(
                "quote",
                text=utterance,
            )
        ]
        doc["unsure"] = False
        return

    for item in items:
        if not isinstance(item, dict):
            continue

        act = item.get("act")
        path = item.get("relation_path")

        if isinstance(path, list):
            # "brother" -> sibling, "dad" -> father
            path = [
                canonical_relation(r)
                if isinstance(r, str)
                and r not in KNOWN_RELATIONS
                and canonical_relation(r)
                in KNOWN_RELATIONS
                else r
                for r in path
            ]
            item["relation_path"] = path

        # Qwen files "Remember X as a person" and
        # "Call X Y" under teach with a made-up
        # relation. Re-file them; names are still
        # copy-checked afterwards.
        value = item.get("value")

        if (
            act == "teach"
            and isinstance(item.get("subject"), str)
            and (
                path == ["person"]
                or (
                    path == []
                    and re.search(
                        r"\b(person|someone|"
                        r"somebody|named|called)\b",
                        utterance.casefold(),
                    )
                )
                or (
                    isinstance(value, str)
                    and value.casefold()
                    in {"person", "a person"}
                )
            )
        ):
            # "X is a person" / "Add X as a person"
            subject = item.get("subject")
            item.update(blank_item(
                "person",
                subject=subject,
            ))
            act = "person"

        elif (
            act == "teach"
            and not isinstance(item.get("alias"), str)
            and isinstance(item.get("subject"), str)
            and isinstance(item.get("value"), str)
            and (
                ALIAS_SUBJECT_FIRST.search(utterance)
                or ALIAS_VALUE_FIRST.search(utterance)
                or path == ["alias"]
            )
            and not (
                isinstance(path, list)
                and len(path) == 1
                and path[0] in KNOWN_RELATIONS
            )
        ):
            # "Tommy is another name for Tom."
            # "Katherine is also known as Kate."
            value_first = bool(
                ALIAS_VALUE_FIRST.search(utterance)
            )
            item.update(blank_item(
                "alias",
                alias=(
                    item["value"]
                    if value_first
                    else item["subject"]
                ),
                canonical=(
                    item["subject"]
                    if value_first
                    else item["value"]
                ),
            ))
            act = "alias"

        elif (
            act == "teach"
            and not (
                isinstance(path, list)
                and len(path) == 1
                and path[0] in KNOWN_RELATIONS
            )
            and isinstance(item.get("alias"), str)
            and isinstance(
                item.get("canonical"),
                str,
            )
        ):
            item.update(blank_item(
                "alias",
                alias=item["alias"],
                canonical=item["canonical"],
            ))
            act = "alias"

        if (
            act == "teach"
            and _has_correction_cue(utterance)
        ):
            # "wait, Mateo is from Quito." The guard
            # forbids teach here; correct is the
            # cautious act (Listening confirms it).
            item["act"] = act = "correct"

        if (
            act in {"ask", "teach", "correct", "forget"}
            and isinstance(item.get("subject"), str)
            and isinstance(path, list)
            and path
        ):
            owner = re.match(
                r"^(.+?)['\u2019]s\s+(\w+)$",
                item["subject"],
            )

            if (
                owner
                and canonical_relation(
                    owner.group(2)
                ) == path[0]
            ):
                # "Yuki's friend" + [friend, ...]
                item["subject"] = owner.group(1)

        if (
            isinstance(path, list)
            and path
            and all(
                isinstance(r, str)
                and _relation_grounded(r, utterance)
                for r in path
            )
        ):
            # Every hop is a KNOWN relation whose
            # wording is in the sentence; the model's
            # own copied spans are not needed.
            item["relation_surface"] = list(path)

        if act == "ask":
            # A question never writes, so stray
            # value fields are simply dropped.
            item["value"] = None
            item["value_kind"] = "none"
            item["alias"] = None
            item["canonical"] = None
            item["choice"] = None

        if act == "quote":
            # A quote keeps the raw sentence only.
            item.update(blank_item(
                "quote",
                text=utterance,
            ))

        if act in {"person", "alias"}:
            item["relation_path"] = []
            item["relation_surface"] = []
            item["value"] = None
            item["value_kind"] = "none"
            item["text"] = None

        if act in {"teach", "correct"}:
            path = item.get("relation_path")

            if (
                isinstance(path, list)
                and len(path) == 1
                and path[0] in KNOWN_RELATIONS
                and isinstance(
                    item.get("value"),
                    str,
                )
            ):
                item["value_kind"] = (
                    "person"
                    if path[0]
                    in PERSON_RELATIONS
                    else "literal"
                )


def parse_english_proposal(
    utterance: str,
    pending_state,
    known_names,
    *,
    base_url: str | None = None,
    model: str | None = None,
) -> dict:
    """
    Parse and validate, but never write memory.
    """
    base_url = (
        base_url
        or DEFAULT_BASE_URL
    )
    model = (
        model
        or DEFAULT_MODEL
    )

    person_line = PERSON_LINE_PATTERN.match(
        utterance
    )

    plain_answer = None

    if pending_state is not None:
        if YES_PATTERN.match(utterance):
            plain_answer = "yes"
        elif NO_PATTERN.match(utterance):
            plain_answer = "no"

    if plain_answer:
        # A bare yes/no to a pending question
        # needs no model (found in real chat:
        # Qwen re-sent the pending fact instead).
        doc = {
            "items": [blank_item(plain_answer)],
            "unsure": False,
            "unsure_reason": "",
        }
    elif person_line:
        # Already a structured line.
        doc = {
            "items": [blank_item(
                "person",
                subject=person_line.group(1),
            )],
            "unsure": False,
            "unsure_reason": "",
        }
    elif UNDO_PATTERN.match(utterance):
        # A plain command; no model needed.
        doc = {
            "items": [blank_item("undo")],
            "unsure": False,
            "unsure_reason": "",
        }
    else:
        doc = _request_doc(
            utterance,
            pending_state,
            known_names,
            base_url,
            model,
        )

    _repair_harmless_fields(
        doc,
        utterance,
    )

    validate_model_output(
        doc,
        utterance,
        pending_state,
    )

    return {
        "doc": doc,
        "lines": render_lines(
            doc,
            utterance,
        ),
        "confirm_before_write":
            confirm_before_write_policy(
                doc
            ),
    }


def parse_english(
    utterance: str,
    pending_state,
    known_names,
    *,
    base_url: str | None = None,
    model: str | None = None,
) -> list[str]:
    """
    Required public interface.

    Returns zero or more validated structured
    lines. It does NOT call Listening and does
    NOT write the notebook.
    """
    proposal = (
        parse_english_proposal(
            utterance,
            pending_state,
            known_names,
            base_url=base_url,
            model=model,
        )
    )

    return proposal["lines"]


def _doc(
    *items,
    unsure=False,
    reason="",
) -> dict:
    return {
        "items": list(items),
        "unsure": unsure,
        "unsure_reason": reason,
    }


def _selftest() -> int:
    """
    Offline tests. No HTTP requests.
    """
    valid_cases = [
        (
            "Mira lives in Lisbon.",
            None,
            _doc(
                blank_item(
                    "teach",
                    subject="Mira",
                    relation_path=[
                        "city"
                    ],
                    relation_surface=[
                        "lives in"
                    ],
                    value="Lisbon",
                    value_kind="literal",
                )
            ),
            [
                "teach Mira city = Lisbon"
            ],
        ),
        (
            "Mary Jane lives in New York.",
            None,
            _doc(
                blank_item(
                    "teach",
                    subject="Mary Jane",
                    relation_path=[
                        "city"
                    ],
                    relation_surface=[
                        "lives in"
                    ],
                    value="New York",
                    value_kind="literal",
                )
            ),
            [
                'teach "Mary Jane" '
                'city = "New York"'
            ],
        ),
        (
            (
                "Where does Mira's "
                "mother live?"
            ),
            None,
            _doc(
                blank_item(
                    "ask",
                    subject="Mira",
                    relation_path=[
                        "mother",
                        "city",
                    ],
                    relation_surface=[
                        "mother",
                        "live",
                    ],
                )
            ),
            [
                "ask Mira mother city"
            ],
        ),
        (
            "What were you trained on?",
            None,
            _doc(
                blank_item(
                    "ask",
                    subject="self",
                    relation_path=[
                        "training_data"
                    ],
                    relation_surface=[
                        "trained on"
                    ],
                )
            ),
            [
                "ask self training_data"
            ],
        ),
        (
            (
                "If Mira lived in Paris, "
                "she'd smile."
            ),
            None,
            _doc(
                blank_item(
                    "quote",
                    text=(
                        "If Mira lived in "
                        "Paris, she'd smile."
                    ),
                )
            ),
            [
                (
                    "quote If Mira lived in "
                    "Paris, she'd smile."
                )
            ],
        ),
        (
            "The second one.",
            {
                "choices": [
                    "E0002",
                    "E0007",
                ]
            },
            _doc(
                blank_item(
                    "pick",
                    choice="E0007",
                )
            ),
            [
                "pick E0007"
            ],
        ),
    ]

    passed = 0

    for (
        utterance,
        pending,
        doc,
        expected,
    ) in valid_cases:
        validate_model_output(
            doc,
            utterance,
            pending,
        )

        got = render_lines(
            doc,
            utterance,
        )

        assert got == expected, (
            utterance,
            got,
            expected,
        )

        passed += 1

    unsafe_cases = [
        (
            "Mira lives in Lisbon.",
            None,
            _doc(
                blank_item(
                    "teach",
                    subject="Ana",
                    relation_path=[
                        "city"
                    ],
                    relation_surface=[
                        "lives in"
                    ],
                    value="Lisbon",
                    value_kind="literal",
                )
            ),
        ),
        (
            (
                "Mira does not live "
                "in Paris."
            ),
            None,
            _doc(
                blank_item(
                    "teach",
                    subject="Mira",
                    relation_path=[
                        "city"
                    ],
                    relation_surface=[
                        "live in"
                    ],
                    value="Paris",
                    value_kind="literal",
                )
            ),
        ),
        (
            (
                "Actually Mira lives "
                "in Paris."
            ),
            None,
            _doc(
                blank_item(
                    "teach",
                    subject="Mira",
                    relation_path=[
                        "city"
                    ],
                    relation_surface=[
                        "lives in"
                    ],
                    value="Paris",
                    value_kind="literal",
                )
            ),
        ),
    ]

    for (
        utterance,
        pending,
        doc,
    ) in unsafe_cases:
        try:
            validate_model_output(
                doc,
                utterance,
                pending,
            )

        except ParseRejected:
            passed += 1

        else:
            raise AssertionError(
                "validator accepted "
                f"unsafe parse: {utterance}"
            )

    bundle = _doc(
        blank_item(
            "teach",
            subject="Mira",
            relation_path=[
                "city"
            ],
            relation_surface=[
                "lives in"
            ],
            value="Lisbon",
            value_kind="literal",
        ),
        blank_item(
            "teach",
            subject="Mira",
            relation_path=[
                "employer"
            ],
            relation_surface=[
                "works at"
            ],
            value="Acme",
            value_kind="literal",
        ),
    )

    assert (
        confirm_before_write_policy(
            bundle
        )
        is True
    )

    passed += 1

    print(
        f"selftest: {passed} checks "
        "passed; no network used"
    )

    return 0


def _listener_pending(listener):
    """
    M1 may use one of these common attribute
    names. If it exposes a dedicated accessor,
    replace this helper with that accessor.
    """
    for name in (
        "pending_state",
        "pending",
        "clarification",
    ):
        if hasattr(listener, name):
            return _jsonable(
                getattr(
                    listener,
                    name,
                )
            )

    return None


def _known_names_from_notebook(
    notebook,
    extras,
) -> list[str]:
    """
    Best-effort read-only extraction. The
    validator never trusts this list enough to
    bypass the copy constraint.
    """
    names = list(
        extras or []
    )

    entities = getattr(
        notebook,
        "entities",
        None,
    )

    if isinstance(
        entities,
        dict,
    ):
        for entity in (
            entities.values()
        ):
            if not isinstance(
                entity,
                dict,
            ):
                continue

            for key in (
                "name",
                "display_name",
            ):
                value = entity.get(
                    key
                )

                if isinstance(
                    value,
                    str,
                ):
                    names.append(
                        value
                    )

            aliases = entity.get(
                "aliases",
                [],
            )

            if isinstance(
                aliases,
                (
                    list,
                    tuple,
                    set,
                ),
            ):
                names.extend(
                    alias
                    for alias
                    in aliases
                    if isinstance(
                        alias,
                        str,
                    )
                )

    return list(
        dict.fromkeys(names)
    )[:500]


def _audit_path(
    folder: str,
) -> str:
    return os.path.join(
        folder,
        "listening_english_audit.jsonl",
    )


def _append_audit(
    folder: str,
    raw: str,
    line: str,
    reply: str,
) -> None:
    """
    Compatibility-sidecar for raw English.

    It is append-only and hash chained. Once
    Notebook supports raw_utterance provenance,
    put the raw text in the Notebook event too.
    """
    path = _audit_path(
        folder
    )
    previous_hash = "0" * 64

    try:
        with open(
            path,
            "rb",
        ) as fh:
            last_line = None

            for last_line in fh:
                pass

        if last_line:
            previous = json.loads(
                last_line.decode(
                    "utf-8"
                )
            )

            previous_hash = (
                previous.get(
                    "hash",
                    previous_hash,
                )
            )

    except FileNotFoundError:
        pass

    event = {
        "prev": previous_hash,
        "raw": raw,
        "line": line,
        "reply": reply,
    }

    canonical = json.dumps(
        event,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    event["hash"] = (
        hashlib.sha256(
            canonical.encode(
                "utf-8"
            )
        ).hexdigest()
    )

    os.makedirs(
        folder,
        exist_ok=True,
    )

    with open(
        path,
        "a",
        encoding="utf-8",
    ) as fh:
        fh.write(
            json.dumps(
                event,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        )

        fh.flush()
        os.fsync(
            fh.fileno()
        )


def _confirmation_echo(
    lines: list[str],
) -> str:
    return (
        "I heard: "
        + "; ".join(lines)
        + ". Save that?"
    )


def _apply_lines(
    listener,
    folder: str,
    raw: str,
    lines: list[str],
) -> list[str]:
    replies = []

    for line in lines:
        reply = listener.hear(
            line
        )

        replies.append(
            reply
        )

        _append_audit(
            folder,
            raw,
            line,
            reply,
        )

    return replies


def _chat(args) -> int:
    try:
        from fable_listening_m1 import (
            Listening,
        )
        import fable_notebook_contract as C

    except ImportError as exc:
        print(
            f"import error: {exc}",
            file=sys.stderr,
        )
        return 2

    notebook = C.Notebook(
        args.folder
    )

    listener = Listening(
        notebook
    )

    # The assistant can be taught about itself
    # ("You were trained on ..."), so it needs an
    # entry for itself. Ben likewise for "I/my".
    known_now = {
        name.casefold()
        for name in _compact_known_names(
            _known_names_from_notebook(
                notebook,
                [],
            )
        )
    }

    for own_name in ("self", "Ben"):
        if own_name.casefold() not in known_now:
            listener.hear(f"person {own_name}")

    adapter_pending = None

    print(
        "English Listening REPL. "
        "Ctrl-D or /quit exits."
    )

    while True:
        try:
            utterance = input(
                "you> "
            ).strip()

        except (
            EOFError,
            KeyboardInterrupt,
        ):
            print()
            return 0

        if not utterance:
            continue

        if utterance in {
            "/quit",
            "/exit",
        }:
            return 0

        known_names = (
            _known_names_from_notebook(
                notebook,
                args.known_name,
            )
        )

        # Adapter-owned bundle confirmation.
        if adapter_pending is not None:
            confirm_state = {
                "kind":
                    "confirm_adapter_bundle",
                "choices": [
                    "yes",
                    "no",
                ],
                "proposed_lines":
                    adapter_pending[
                        "lines"
                    ],
            }

            try:
                confirmation = (
                    parse_english_proposal(
                        utterance,
                        confirm_state,
                        known_names,
                        base_url=(
                            args.base_url
                        ),
                        model=args.model,
                    )
                )

            except (
                ParseRejected,
                RuntimeError,
            ) as exc:
                print(
                    "fable> I couldn't "
                    "safely parse that "
                    "confirmation: "
                    f"{exc}"
                )
                continue

            acts = [
                item["act"]
                for item
                in confirmation[
                    "doc"
                ]["items"]
            ]

            if acts == ["yes"]:
                replies = _apply_lines(
                    listener,
                    args.folder,
                    adapter_pending["raw"],
                    adapter_pending["lines"],
                )

                adapter_pending = None

                for reply in replies:
                    print(
                        f"fable> {reply}"
                    )

                continue

            if acts == ["no"]:
                adapter_pending = None
                print(
                    "fable> Cancelled."
                )
                continue

            # Unrelated input cancels the
            # pending clarification and is
            # processed as a fresh utterance.
            adapter_pending = None

        pending_state = (
            _listener_pending(
                listener
            )
        )

        try:
            proposal = (
                parse_english_proposal(
                    utterance,
                    pending_state,
                    known_names,
                    base_url=(
                        args.base_url
                    ),
                    model=args.model,
                )
            )

        except (
            ParseRejected,
            RuntimeError,
        ) as exc:
            print(
                "fable> I didn't trust "
                "that parse, so I saved "
                f"nothing: {exc}"
            )
            continue

        if proposal["doc"]["unsure"]:
            reason = (
                proposal["doc"][
                    "unsure_reason"
                ]
                or
                "I'm not sure what "
                "you meant."
            )

            print(
                f"fable> {reason} "
                "Nothing was saved."
            )
            continue

        lines = proposal[
            "lines"
        ]

        if proposal[
            "confirm_before_write"
        ]:
            adapter_pending = {
                "raw": utterance,
                "lines": lines,
            }

            print(
                "fable> "
                + _confirmation_echo(
                    lines
                )
            )
            continue

        if not lines:
            print(
                "fable> Okay."
            )
            continue

        replies = _apply_lines(
            listener,
            args.folder,
            utterance,
            lines,
        )

        for reply in replies:
            print(
                f"fable> {reply}"
            )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "English front end for "
            "Fable Listening mode"
        )
    )

    mode = (
        parser.add_mutually_exclusive_group(
            required=True
        )
    )

    mode.add_argument(
        "--selftest",
        action="store_true",
        help=(
            "run offline validator "
            "and rendering tests"
        ),
    )

    mode.add_argument(
        "--chat",
        action="store_true",
        help=(
            "run interactive "
            "Listening REPL"
        ),
    )

    parser.add_argument(
        "--folder",
        default="./fable_notebook",
        help="Notebook folder",
    )

    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
    )

    parser.add_argument(
        "--known-name",
        action="append",
        default=[],
    )

    args = parser.parse_args(
        argv
    )

    if args.selftest:
        return _selftest()

    return _chat(
        args
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
