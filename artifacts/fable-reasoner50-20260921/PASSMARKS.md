# Experiment 50 — registered pass marks (written and sealed BEFORE any registered run)

Date written: 2026-09-21.  Registered sleep seeds: **4131, 4132, 4133**.  The scale/parity
stage is deterministic (sampling seeded by cell tag `reg`), registered as ONE run.
Development used throwaway seed **9999** and sampling tag `dev` only; dev results are not
registered claims.  Every mark is scored as an integer count, never averaged across seeds.

## What is being tested

`scripts/fable_reasoner50.py` implements the Reasoner Protocol
(`answer(question, notebook) -> record`) on the REAL notebook contract: E-IDs with
ambiguous aliases, an open relation set, source-tagged facts, ear frames
`{name, relations, entity_id?}`.  Skills are per-relation lookup views built lazily from
the notebook's current view (answering sources only, `Notebook.current` semantics); base
relations route identity (given by hand); learned words use the Exp-44 3-stage router over
[keep + 8 core skills] installed by the Exp-46 recipe; the hop loop, the five statuses and
the 0.9 threshold are hard-coded; unknown relations abstain with `MISSING_FACT`.

## Definitions

- **Grid cell**: one notebook of `n ∈ {60, 600, 6000}` entities and
  `r ∈ {8, 80, 500}` total relations = `r−3` entity-valued functional relations
  (`rel_0…`) + literal `city` + multi-valued `friend` + multi-valued `hobby`.
  ~15% of main-relation facts missing; duplicate names (AMBIGUOUS) every 50 entities;
  aliases every 25; a fifth of entities have a literal `city`; a tenth have two values each
  of `friend`/`hobby`; 20 proposed/web-quarantine-only subject–relation pairs (source
  filter); ~40 corrections that supersede; 10 retractions.  Built as a contract
  `events.jsonl` with a valid hash chain, loaded through the contract's own loader.
- **Parity frame**: an ear frame; the reasoner and `Notebook.ask` must return records equal
  in `status` AND `fields` (answer, trail, subject, relation, hop, value, choices, ids,
  source, multi…).  300 frames per cell, category mix (registered integers):
  100 ok-entity, 25 ok-literal, 40 missing, 25 broken-chain, 20 ambiguous, 20 unknown-name,
  20 multi, 20 source-filter, 15 entity_id, 15 junk.
- **Unknown-relation frame**: `relations = [never_taught_rel_k]` (never declared, no facts
  of any source, not a word), entity given.  Correct answer: `MISSING_FACT`, identical to
  the contract, no invented entity.
- **Training notebook**: a genuine contract notebook per seed, 60 entities, the 8 core
  relations taught with ~15% missing, written through the public API.
- **Episode**: `(start entity, word, answer entity)` where answer is the word's defined
  chain walked over the notebook view; 20 per word, drawn only from people for whom the
  chain resolves.
- **Install gate** (the Exp-46 recipe, imported read-only): robust loss
  `−log((0.9)p + 0.1/N)`; phi hardened to argmax ±30 after every fold fit and the refit;
  4-fold CV split by person over checkpoints {0, 50, 100, 200, 400, 800}; a checkpoint is
  eligible only at OOF exact match ≥ 0.80; the eligible checkpoint with lowest OOF NLL is
  refit on all episodes; install requires refit-vs-OOF agreement ≥ 0.90, base probe answers
  (through the protocol) unchanged, and an identical weights-only reload.  Nothing
  installs if no checkpoint is eligible; an ungated word is never left loaded.
- **60-start audit**: every entity of the training notebook asks the word frame through
  `answer()`; compared with the word's DEFINED chain over the view.  A disagreement is a
  wrong install: answered OK where the walk is missing, abstained where it resolves, or
  answered the wrong entity.
- **Base probe**: 100 resolvable 1–3 hop core-relation frames on the training notebook,
  answered through the protocol before any install and after each install / all installs.

## Registered marks

**S1 parity** — across the 9 cells: reasoner and contract agree on **2700/2700** frames
(300 per cell), AND every cell's 300 frames contain **≥ 1 frame of each of the five
statuses** OK / MISSING_FACT / BROKEN_CHAIN / AMBIGUOUS / UNKNOWN_ENTITY.  Any single
disagreement = registered FAIL (a bug, not a result).

**S2 abstention** — **90/90** unknown-relation frames (10 per cell) return `MISSING_FACT`
identical to the contract; **0** OK, 0 invented entities.

**D1 installs** — **9/9** (3 seeds × 3 words) words pass the gate above.  Every seed,
every word.

**D2 audit** — **0 disagreements of 540** (9 installs × 60 starts) against the true walk.
Every seed.

**D3 wiring** — the Exp-44 dense path and the protocol `answer()` disagree on **0/540**
audit frames (entity-id vs display-name is normalised before comparison).

## Recorded, not gated

- Time per question (reasoner and contract, post-index-build), one-time index build
  seconds, reasoner cache bytes (tracemalloc), notebook write/load seconds and file size,
  process peak RSS.
- CV tables, chosen checkpoints, routed chains, refit agreement, distinct people,
  base probe accuracy, per-seed wall-clock.
- Reuse: 120 frames per seed with one slept word inside a 2–3 token chain, accuracy.

## Given by hand (not learned) — stated again in RESULTS.md

1. The hop loop, statuses and record fields (mirrors the contract).
2. ANSWER_THRESHOLD 0.9 and "otherwise abstain with MISSING_FACT".
3. View construction, sharing the contract's `ANSWERING_SOURCES`, `active`, sort order.
4. Identity routing for base relation tokens (open vocabulary; Exp 44's learned identity
   inherited as a given — no base router training).
5. Word shape: 3 stages over [keep + 8 core skills] = 27 numbers; the three words and
   their defined chains; episodes only from people for whom the chain resolves.
6. Gate constants (4 folds, checkpoints, 0.80, 0.90), ε=0.10, harden ±30 (Exp 45/46).
7. The grid, missing rate, alias/ambiguity/source-filter/correction cadences, category mix.
8. Seeds 4131/4132/4133; dev seed 9999; MAX_HOPS = 8 from the contract.

## Failure protocol

A registered FAIL is written into RESULTS.md first.  Only then may ONE clearly described
change be made as "v2", with its own sealed marks, run on 4131/4132/4133 plus fresh seeds
4141/4142/4143.  No further tuning.  Disagreements in S1/S3 are bugs: fix the bug, never
re-sample the questions.
