#!/usr/bin/env python3
"""Experiment 139e -- THE ONE CHANGE vs loop139c: relation-gated unknown-tail clarify.

Single diagnosis-driven follow-up to the registered FAIL of 139d. 139d's
clarify ("Rome honestly" -> Did you mean "Rome"? ..., 0 writes) worked on
chat but its trigger was too broad: bench values "Gaelic football",
"American football", "Wa language" end in a lowercase word, the guard
clarified mid-chain and G1 got 20 new wrong.

THE ONE CHANGE (this file, closed list fixed here before any panel read):
the SAME 139d trigger and reply, but ONLY when the teach/correct action's
relation is in LISTED_RELATIONS below -- person-valued and place-valued
relations derived from the relation table loop139c's probe uses (boss,
city, coach, pet, school, teacher, town) plus 139d's listed shapes
(mother, city, boss, coach, pet, school, teacher, town), extended to the
closed person/place set named in the 139e brief:

  person-valued: mother, father, sister, brother, sibling, spouse,
    husband, wife, boss, friend, teacher, coach, pet, dog
  place-valued: city, town, hometown (+ home_town spelling), country,
    birthplace (+ place_of_birth spelling), school

NOT listed (byte-identical to loop139c, whatever the value shape): sport,
language (official_language, languages_spoken_written_or_signed), genre,
occupation, food, drink, color, instrument, and every other relation
(including all declarative bench73 template keys such as capital,
continent, country_of_citizenship, manufacturer, notable_work, religion,
author, founder/founded, director, performer, educated_at, headquarters,
head_of_state/government, place_of_death, position_played, creator,
developer, employer, officeholder, apprentice/mentor/rival/scout/warden/
herald/keeper/envoy/inventor/composer/discoverer/author_of, and the chat
relations motto, song, band, film, book, hero, lunch, drink, food, color).

Relation keys are normalised exactly as FakeEars._relation does
(scripts/fable_agent_loop.py: FakeEars._relation -- lowercase,
whitespace runs joined with "_"), so "home town" and "hometown" style
surfaces map to the listed keys. An action with a missing/empty relation
never triggers (safe default: byte-identical to loop139c).

After 139c's strip (which runs first, read-only), if the value's FIRST
word starts with A-Z and its trailing RUN of words is all all-lowercase
letters ([a-z]+), none a name connector (closed list copied verbatim from
139d), AND the relation is listed, the turn does not write and replies
exactly:

  Did you mean "<value without the last lowercase words>"? Please say it
  again without the extra words.
"""

from __future__ import annotations

import fable_fix139c_tail as T139c  # noqa: E402 (139c strip runs first, read-only)
import fable_fix139d_tail as T139d  # noqa: E402 (trigger + reply + connectors, read-only)

# THE CLOSED LISTED-RELATION SET -- fixed before any panel read, in the doc.
# Normalised keys (lowercase, spaces -> "_", as FakeEars._relation makes).
LISTED_RELATIONS = frozenset({
    # person-valued
    "mother", "father", "sister", "brother", "sibling", "spouse",
    "husband", "wife", "boss", "friend", "teacher", "coach",
    "pet", "dog",
    # place-valued
    "city", "town", "hometown", "home_town", "country",
    "birthplace", "place_of_birth", "school",
})


def normalize_relation(relation) -> str:
    """Normalise a relation surface exactly like FakeEars._relation."""
    return "_".join(str(relation or "").strip().lower().split())


def check_value(value: str, relation) -> str | None:
    """Clarify message for a post-139c value on a listed relation only."""
    if normalize_relation(relation) not in LISTED_RELATIONS:
        return None
    split = T139d.unknown_tail_split(value)
    if split is None:
        return None
    return T139d.clarify_text(split[0])


def guard_action(action: dict) -> dict:
    """teach/correct with unknown tail on a LISTED relation -> clarify."""
    if not isinstance(action, dict):
        return action
    if action.get("act") not in ("teach", "correct"):
        return action
    cleaned_action = T139c.sanitize_action(action)
    msg = check_value(cleaned_action.get("value", ""),
                      cleaned_action.get("relation", ""))
    if msg is not None:
        return {"act": "clarify", "text": msg}
    return cleaned_action


def guard_actions(actions: list[dict]) -> list[dict]:
    return [guard_action(a) for a in list(actions)]


class RelationGatedTailMixin:
    """Stackable mixin: relation-gated unknown-tail clarify on teach paths."""

    @staticmethod
    def listed_relation(relation) -> bool:
        return normalize_relation(relation) in LISTED_RELATIONS

    @classmethod
    def guard_action(cls, action: dict) -> dict:
        return guard_action(action)

    @classmethod
    def guard_actions(cls, actions: list[dict]) -> list[dict]:
        return guard_actions(actions)
