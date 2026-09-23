# 73 — Fable-Edit-200 English-input arm with pluggable ears (Muse)

## Goal

An English-input twin of the exp-65 structured arm: the same notebook,
QualifierAwareReasoner and scoring, but every fact and every query arrives as
an English string through a swappable Ears object. The real ears (exp 47,
training elsewhere) drops in later with no new code: the pluggable unit is
the per-sentence mapper; query composition is shared arm code.

## Architecture

```
sentence_en -> Ears.hear_teach -> (subject, relation, object) | None
question_en -> compose_question(q, parsed triples) -> (name, [rels]) | None
triples -> notebook (correction iff (subj,rel) repeats w/ new object)
(name, [rels]) -> QualifierAwareReasoner -> scored exactly like exp 65
None anywhere -> MISSING/abstain, never a write, never a guess
```

`--ears template` = regex mapper (registered arm). `--ears ears47:<ear.pt>`
= FrameEars over borrowed SciBERT, CPU inference: loads `ear.pt`
(state/temps/encoder params as saved by `fable_ears47_train.py`), runs the
forward used by the smoke test, and reuses the same composer over neurally
parsed triples. Full neural decode is implemented but UNVALIDATED — no
checkpoint exists under `artifacts/fable-ears47-20260921/runs/`, so the
registered bar is import + forward on 3 sentences, or a clear skip.

## Every taught-sentence pattern (STATEMENT_PATTERNS, tried in order)

`The author/capital/chairperson/chief executive officer of S is O`;
`The company that produced S is O`; `The headquarters of S is located in the
city of O`; `The name of the current head of state in S is O`;
`The name of the current head of the S government is O`;
`The official language of S is O`; `The type of music that S plays is O`;
`The univeristy [sic] where S was educated is O`; `S died in the city of O`;
`S is a citizen of / affiliated with the religion of / associated with the
sport of / famous for / located in the continent of / married to O`;
`S is the apprentice/author/composer/discoverer/envoy/founder/herald/
inventor/keeper/mentor/rival/scout/warden of O.` (terminal period required);
`S plays the position of / speaks the language of O`;
`S was born in the city of / composed by. / created by / created in the
country of / developed by / discovered by. / founded by.? / founded in the
city of / invented by. / performed by / written by. / worked in the city
of O`; generic `The S is O` (officeholder) LAST. Lazy groups resolve the
Japan/Japanese and Boeing/William-Boeing overlaps; 575/575 triples exact in
dev (gold-free at run time).

## Question composer (shared, both ears)

1. `never-taught relation N of Name` -> 1-hop frame with that key.
2. `never-taught relation of the <noun> of Name` -> `[<noun>_of,
   never_taught_rel]` (undeclared second hop -> structural MISSING).
3. `Who is the <noun> of <Name>?` / `Who <verb> by <Name>?` (bare-name guard
   rejects mquake lookalikes like "the company that developed…") -> triple
   lookup: subject-hit, else object-hit (reverse query), else novel-name
   abstain frame.
4. Else MQuAKE two-hop: the single taught entity named in the question is the
   chain start; hops walk the taught chain (post-edit objects); both hop
   relations must be cue-mentioned in the question (recall-biased cue list in
   REL_MENTION_CUES, e.g. "holds citizenship"->country_of_citizenship,
   "originated"->country_of_origin, "current leader"->{head_of_state,
   head_of_government}), else MISSING.

## Evidence

Registered: template table identical to structured reference (100/50/25/25,
0 wrong, 0.5 s); 5/5 garbled abstain (2 MISSING_FACT, 3 UNKNOWN_ENTITY), 0
wrong; selftest PASS; ears47 smoke SKIP (documented, no checkpoint). Seal
`SEAL.sha256.txt` over PASSMARKS.md predates all registered runs; ledger
P73.1–P73.4 predicted first, 4/4 TRUE.

## What it means / does not mean

English sentences install the same facts as triples and every file question
resolves correctly — but templates are file-specific and two-hop order comes
from chain structure with a mention gate, not from understanding question
paraphrases. General English listening stays with exp 47.

## ears47 run command (once a checkpoint exists)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_bench73_english_arm.py --run --ears ears47:artifacts/fable-ears47-20260921/runs/<seed>/ear.pt
```
