#!/usr/bin/env python3
"""Experiment 56: miner filter -- qualified rows never enter mined chains.

A pure function over livesleep52's episode input (the conversation turn log).
livesleep52.mine_episodes() turns ask+confirm pairs into training episodes;
its asks were answered through to_v1() projections, so a chain that resolved
through a qualified row (true only 'in 2019', say) would install a word that
fires with no year attached. This filter drops those turns BEFORE mining.

Pure: same (turns, notebook) -> same output; the input list and its dicts are
never mutated. Only 'ask' and 'correct' turns can carry chains, so only those
are examined; every other turn kind passes through untouched.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402
from fable_thought49_schema import SchemaError, ThoughtV2  # noqa: E402


def chain_passes_through_qualified(start_name: str, chain, notebook) -> bool:
    """True if the notebook's answering walk for (start, chain) uses a
    qualified row at any hop. Unresolvable chains return False (the miner
    drops non-OK asks itself; that is not this filter's business)."""
    found = notebook.resolve(start_name)
    if found.status != C.OK:
        return False
    entity_id = found.detail["entity_id"]
    for relation in chain:
        rows = notebook.current(entity_id, relation)
        if not rows:
            return False
        try:
            thought = ThoughtV2.from_v1(notebook.facts[rows[0]["fact_id"]])
        except SchemaError:
            thought = None
        if thought is not None and thought.qualifiers:
            return True
        value = rows[0]["value"]
        if "entity" not in value:
            return False
        entity_id = value["entity"]
    return False


def filter_qualified_turns(turns: list, notebook) -> list:
    """Return a new turn list with qualified-chain 'ask'/'correct' turns removed.

    A turn is removed iff its (start, chain) answering walk passes through a
    qualified row (chain_passes_through_qualified). Turns without a chain
    (smalltalk, confirm, teach, stray) are always kept.
    """
    kept = []
    for turn in turns:
        kind = turn.get("kind")
        if kind in ("ask", "correct") and turn.get("chain"):
            if chain_passes_through_qualified(
                    str(turn.get("start", "")), list(turn["chain"]), notebook):
                continue
        kept.append(turn)
    return kept
