# 165 — Missing-apostrophe possessives read as the possessive (Muse)

## The gap (file:line first)

- The base parses possessives in scripts/fable_agent_loop.py:93
  (`_APOS = r"[''s]\b\s*"`) via :102 (`_chain()` splits owner from relation
  on the apostrophe-s). A turn with no apostrophe ("toms boss") never
  splits: teach falls into the "Please say it like ..." clarify (:139),
  questions into the hop-count clarify (:125-127). Verified live on loop162b
  pre-seal: "Toms boss is Lee." replies "I didn't understand that. Could you
  say it another way?" and writes nothing; "Tom's boss is Lee." saves with
  "Saved: Tom's boss is Lee." and "Who is Tom's boss?" answers
  "Tom's boss is Lee." (base stage: fake).

## The one change (behaviour)

`Typo165Mixin` (scripts/fable_fix165_typo.py), stacked outermost as
`Loop165Ears(Typo165Mixin, Loop162bEars)` in
scripts/fable_loop165_agent.py. It claims only two full-turn shapes with no
apostrophe anywhere in the turn: teach `W R is V` and question
`Who/What/Where is|are W R`, where W is one alpha word ending in s/S and R
is one person-relation word (boss/mother/father/sister/brother/friend/
teacher/...). The notebook gates (pure functions of W + notebook state):
(a) `nb.resolve(W-minus-s)` is OK with an entity_id (exactly one known
entity, case-insensitive); (b) `_norm(W)` is not in `nb.aliases` (W itself
unknown, OK and AMBIGUOUS both block); (b2) W is not the final word of a
known multi-word entity (the "The Toms"/"The Beatles" plural block).
Claimed turns are rewritten (`Toms boss is Lee.` → `Tom's boss is Lee.`,
rest byte-preserved) and delegated to the base `hear()` literally, so save
path, screens, correction semantics, and reply text are the base's own.
Everything else — apostrophe turns, unknown/ambiguous stripped names,
W-known, office/table relations, multi-word frames, hearsay-shaped turns —
returns None and takes the loop162b code path literally (byte-identity by
construction for all non-claimed inputs).

## Why this shape

- Rewriting then delegating (rather than re-implementing the save) makes
  the "no extra reply text" ruling structural: replies are base replies.
- Full-turn match plus the person-relation gate keeps the blast radius at
  one unambiguous typo shape; the pre-seal linear shape scan finds zero
  such shapes in any bench/G3/suite input, which is why G1/G2/G3 predict
  zero moves.
- Case-insensitivity comes free: `resolve` normalises, and the rewrite
  preserves the input's capitalisation, so "toms" reuses Tom's entity
  (verified: no duplicate entity, display stays "Tom").
- "Chriss" → "Chris's" falls out of the same rule (ss-stems included);
  "Chris" itself is blocked by gate (b).

## Limits (claims never exceed evidence)

- Correction-shaped repeats ("maxs friend is Ben." after "Max's friend is
  Hal.") take base correction/conflict semantics, not silent overwrite —
  deliberately unprobed here.
- Multi-hop typo chains ("toms boss's mother") contain an apostrophe or
  fail the full-turn shape and stay on the base path.
- The daemon subclass only re-states `idle_seconds` (same pattern as 162b).
- Post-seal case-file fix reported in RESULTS.md (expect now lists the
  setup triple too); agent code untouched since the seal.

## Reproduce

Sealed config + 53-case probe in artifacts/fable-typo165-20260922/;
`scripts/fable_fix165_probe.py`, `scripts/fable_fix165_bench.py` (vs the
base folder's frozen loop162b rows), `scripts/fable_fix165_g3.py`,
`scripts/fable_marks123_all.py --agent scripts/fable_loop165_agent.py
--config …/loop165-config.json --workers 2`,
`scripts/fable_fix165_marksdiff.py` (vs marks162b, volatile keys scrubbed
and listed).
