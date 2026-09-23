# 164 — About-stage: "What do you know about X?" (Muse, 2026-09-22)

## Problem

After Ben teaches "Tom's boss is Ann.", asking "What do you know about Tom?"
falls through to the fallback clarify — on loop138 a long decline, on
loop138c "I didn't understand that" (director probe 04:12). The notebook
holds the fact; the ears have no frame for showing it. Users will ask this
constantly: it is the cheapest possible demo that teaching worked.

## The one change

A read-only ears stage, checked FIRST in `hear()`, before the loop150 chain
and therefore before the fallback (`fable_loop90_agent.py:291-292`). It
claims only five full-turn shapes (case-insensitive, optional trailing
`.?`/`!`): "What do you know?", "What do you know about X?", "Tell me about
X", "What have I told you about X?", "Anything about X?". Everything else —
including every teach — delegates byte-identical to loop150.

For X it reads the notebook contract only (`nb.resolve`, `nb.active`,
`nb.facts`, `nb.entities` — the same triple `notebook_triples` uses):
subject-side active taught facts in fact-id order, then value-side ones,
each rendered "Tom's boss is Ann.", max 8 sentences then "and N more.".
Unknown X reuses the base's existing unknown-entity sentence ("I don't know
anyone called X."); ambiguous X, known-but-empty X, and any error delegate
to base. Bare "What do you know?" reports live counts ("I have N facts
about M people…"). The stage returns clarify actions, so about-turns never
write, never touch the web, never infer.

## Boundaries (deliberate)

X must be a plain name span: no possessives ("Tom's boss" stays the
router's job), no compounds ("Tom and Ann" stays the fallback's), no
pronouns (a sealed list; "Tell me about yourself" keeps the exact base
reply), no punctuation. These are not limitations to fix later without a
new experiment: each exclusion is what keeps the 600 bench items, all
marks123 suites, and all 180 session turns byte-identical.

## Why it is safe

Reads are restricted to active taught facts — retracted and superseded rows
are invisible by construction (`nb.active`), proposed/inferred/quarantined
rows are filtered by source, and display strings come from the notebook's
own entity table, so nothing is invented. The unknown and summary sentences
are fixed templates with counts/names filled in, the same way the contract
renders every other status.

## What it does not do

No multi-hop reasoning ("about Tom's boss" delegates), no aggregation
("who do you know?" is out of scope), no pronoun resolution, no teaching
through questions, no web. Zero-fact known names keep the base reply rather
than inventing a new sentence.

## Questions for Ben

None. The conservative defaults (delegate on ambiguity, taught-only,
8-fact cap) stand unless you say otherwise.
