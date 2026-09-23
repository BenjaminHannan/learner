# 50 — Reasoner on the real notebook contract (Opus, 2026-09-21)

Agent 3 of the parallel build.  Owns `scripts/fable_reasoner50.py`, artifact
`artifacts/fable-reasoner50-20260921/`, this doc.  Additive only; `fable_notebook_contract`,
`fable_reasoner44/45/46` and `fable_agent_loop` are imported read-only.

## The problem

Experiment 44 proved the reasoner on a toy village: a plain dict of
`(person, relation) -> person`, eight closed relations, unique opaque names, facts with no
source tags.  The real NOTEBOOK contract (`fable_notebook_contract.py`) is harder in five
ways at once:

1. **Entities are E-IDs; names are aliases.** Two people may share a name; resolving one
   returns `AMBIGUOUS`, never a guess.  Questions arrive as ear frames
   `{name, relations chain, entity_id?}`.
2. **Relations are an open, growing set** — hundreds (WebRED lists 481+), declared over
   time, most never seen in any training.
3. **Facts carry source tags.** Only `taught | inferred | sleep-derived | web-verified`
   answer (contract's `ANSWERING_SOURCES`); `proposed` and `web-quarantine` never do, and
   corrections/retractions supersede without deleting.
4. **Answers must be the contract's five discrete statuses** — `OK`, `MISSING_FACT`,
   `BROKEN_CHAIN` (a literal where a person was needed), `AMBIGUOUS`, `UNKNOWN_ENTITY` —
   with field-for-field identical details (subject, hop, trail, choices…), because the
   mouth renders them through the contract's templates.
5. **Questions may chain up to `MAX_HOPS = 8`.**

## The design

### Skills = lazy per-relation lookup views

A `RelationView` is built the first time a relation is asked about, from the notebook's
**current view**: facts bucketed by relation (one pass over `nb.facts`), filtered by
`source in ANSWERING_SOURCES and nb.active(fid)`, sorted best-source-first /
newest-first exactly as `Notebook.current` does, then collapsed per subject into one of

- `E` single entity-valued row (functional or unique row → `rows[0]`),
- `L` single literal row (city → "Porto"),
- `M` multi-valued row (non-functional, ≥2 rows → contract answers `OK` with all values),
- absent → `MISSING`.

Nothing is trained: the notebook is the index.  Caches are keyed to `len(nb.events)`, so
any write invalidates and the next answer rebuilds — one line of the contract's append-only
log changes every answer that depends on it.  Memory at the biggest cell
(6 000 × 500) measured by tracemalloc: the bucket index plus every touched view ≈ 72 MB,
against a 2.55-million-fact notebook.

### Router = identity for base relations, learned chains for words

The Exp-44 router was a learned 8×8 token→skill logit table, trained to find the identity
permutation.  On an **open** vocabulary that cannot carry over: relation 481 has no
training row.  We keep the *result* of Exp 44 as a given — **base relation tokens route
identity** (skill `r` = lookup of `r`) — and keep the router exactly where learning still
matters: **learned words**.  A word is the Exp-44 3-stage router over
`[keep + the 8 core skills]` = 27 numbers, installed only by the Exp-46 sleep recipe
(robust loss `−log((1−ε)p+ε/N)`, ε=0.10; harden to argmax ±30 after every fold fit and the
refit; 4-fold CV gate: OOF exact ≥ 0.80, refit agreement ≥ 0.90, base answers unchanged,
weights-only reload identical).  The pipeline reuses `fable_hardgate46`'s patched
`fable_reasoner44.fit_word` directly, so the recipe is literally the registered one.

### Hop loop = the contract's, hard-coded; threshold 0.9; abstain, never guess

`answer(question, notebook)` walks the chain with the contract's own bookkeeping: resolve
(or honour `entity_id`), check for a literal at each hop boundary (`BROKEN_CHAIN`), look up
the view (`MISSING_FACT` with subject/hop/trail), short-circuit multi-valued rows (`OK`,
`multi: true`), finish with `OK` + trail + source.  A probability mass runs alongside
(multiplying the routed stage weight); if it would fall below `ANSWER_THRESHOLD 0.9` the
reasoner abstains with `MISSING_FACT`.  Installed words are hardened, so mass is 1 on the
chosen path — the threshold is a brake, never a decider, in registered runs.

**Unknown relation** (not declared, no facts of any source, not a learned word): the
reasoner returns `MISSING_FACT` with the same fields the contract would give — it abstains
rather than routing to some default skill.  Because "unknown" implies the contract also
finds no rows, abstention and parity never conflict.

### Parity is the correctness oracle

For each of 9 grid cells (60/600/6 000 entities × 8/80/500 relations), 300 frames are
sampled across a fixed category mix (resolvable, literal-OK, missing, broken, ambiguous,
unknown-name, multi, source-filter, entity_id, junk) and both
`FableReasoner50.answer` and the contract's own `Notebook.ask` answer them.  **Any
disagreement on status or any field is a bug, not a result.**  Dev run: 540/540 at 60
frames/cell.

### Sleep on the real notebook

Per seed, a genuine contract notebook is built through the public API (60 entities, the 8
core relations taught, ~15% missing).  20 taught episodes per word come from people for
whom the composite resolves.  Fitting runs the Exp-44 dense path over matrices built from
this notebook's view (Village adapter: entity IDs as names).  Every gate decision goes
through the protocol: base probe frames answered before/after install must be identical;
the saved word is reloaded `weights_only` into a fresh reasoner and must answer identically.
Then the **60-start audit**: every entity asks the word frame through `answer()` and is
compared with the word's *defined* chain over the view — 0 disagreements required (a
mis-routed chain fails here even if self-consistent).  A dense-path vs protocol comparison
on the same 540 frames catches representation drift between the two implementations.

## What is given by hand vs learned

Given: the hop loop and statuses; the 0.9 threshold and abstention; view construction
(sharing the contract's `ANSWERING_SOURCES`/`active`); identity routing for base relations;
word shape (3 stages, keep + 8 skills); the three words and their defined chains; gate
constants; the notebook generator; the parity category mix; seeds.

Learned, and only from final answers: the 27 routing numbers per installed word.

## Deviations / notes for Ben

- **Source tags:** the tasking text said "sleep-derived never answers"; the shipped
  contract has `ANSWERING_SOURCES = (taught, inferred, sleep-derived, web-verified)` —
  sleep-derived *does* answer, ranked last.  Parity is measured against the contract, so
  the reasoner follows the contract.  If Ben wants sleep-derived silenced, that is a
  one-line contract change plus a re-seal, not a reasoner change.
- No base-router training (identity given, see above); no noise controls (not registered);
  `fable_reasoner50.py` answers word-internal failures with the underlying skill's name in
  the `relation` field (the contract has no vocabulary for words).
- Wire point for agent 4: construct `FableReasoner50()` once and pass it as the
  `reasoner=` argument of `AgentLoop`; it implements `answer(question, notebook)` and
  reloads its words from the `.pt` files this experiment writes.
