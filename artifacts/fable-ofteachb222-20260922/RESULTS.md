# RESULTS — Exp 222: "IS A R OF" ONLY FOR ONE-OF-MANY PERSON RELATIONS (Muse)

Registered verdict: **PASS** (B1–B5 all hold; seal 5/5 OK post-runs, no
post-seal edits). Additive only: `scripts/fable_fix222_ofteachb.py`,
`scripts/fable_loop222_agent.py`, `artifacts/fable-ofteachb222-20260922/`;
loop215/loop138i imported read-only, never edited.

## The one change

Loop215 rewrote every "X is a/an R of Y." to "Y's R is X.". Loop222 adds
one gate: the indefinite rewrite fires only when R (canonical or alias,
case-insensitive) is a `value_kind=person` + `cardinality=multi` entry of
the relation table (34 names: friend, daughter, son, sister, brother,
cousin, aunt, uncle, child, sibling, colleague, neighbour, rival,
apprentice, grandchild/-son/-daughter/-mother/-father, parent, composer,
author, founder, inventor, designer, discoverer, architect, creator,
developer, performer, director, dog, cat + aliases like kid, grandma,
coworker). Implementation: if `rewrite_teach215` would fire with article
a/an and R outside the set, the turn is handed to
`Loop138iEars.hear` directly, skipping the 215 mixin. "The" teaches and
the question rewrite run the exact 215 path.

## Marks table (integer counts, every case reported)

| mark | bar | result |
|---|---|---|
| B1 C013 | 138i triple + 138i reply | `(Kip Dune, country_of_citizenship, Peru)`, question answered, byte-identical 138i |
| B1 Lima | nothing stored, 138i replies | 0 FACTs, both replies byte-identical 138i (215's `(Peru, city, Lima)` gone) |
| B1 friend/daughter pairs | stored + answered as 215 | 4/4 replies + triples byte-identical 215, incl. "(I also have …)" |
| B1 "The" forms | exactly as 215 | capital/sister save + answer, byte-identical 215 |
| B2 person/multi (20) | byte-identical 215, store (Y,R,X) | 20/20, e.g. `('Otto Marlowe','friend','Wren Hallis')` |
| B2 other nouns (20) | byte-identical 138i | 20/20 (citizen/city/town/country/region/part/kind/member/resident/native/fan/student + mother/father/spouse/wife/husband/boss/teacher/mentor) |
| B2 junk | 0 | 0 (`*_of` 0, city/citizen writes 0) |
| B3 rt136 (145) | 215's set minus C013 | exactly C019–C031 (13); C013 back to OK; rest 0 moves |
| B3 rt143 (124) | J8 K9 O3 | exactly those 3, rows byte-identical to 215 sealed rows |
| B3 sessions152 | 0 moves | 0 moves, 0 new writes |
| B3 bench (600) | only 25 -fwd rows | f00–f24-fwd; other splits 0 moves; all 200 edit200 rows byte-identical to 215 |
| B3 marks123 fast | per-case identical + bench rows | only the 25 fwd rows + bench aggregate shift |
| B4 sleep smoke | same marks as 138i | sleeps 1, installed 1, probes 5/5, wrong 0, broken abstains, taught 50/50, ow 0 — identical to 138i reference run |
| B5 | 0 new wrong writes | 0 outside predicted sets |
| seal | 5/5 OK | 5/5 OK post-runs |

Stale-gold note (evidence, not excuse): the 13 rt136 `WRONG-WRITE`
labels judge true readings (`Bob's apprentice is Mira`) against old junk
golds (`Mira's apprentice_of is Bob`) — the same 13 the 215 report
documents; the 25 bench `-fwd` "correct→wrong" flips are 215's true
subject answers vs junk-echo golds. Every moved row is byte-identical to
215's sealed rows (rt136/rt143/bench-edit200/marks123-bench 200/200).
Hand-verdicts: rt143 J8 abstains on typo'd "Norlanb" instead of repeating
the base's wrong answer (no new wrong); K9 WRONG-ANSWER→OK; O3 OK→OK.

## Deviations

Piloted rt136 + sleepsmoke (both agents) before the seal; bench,
sessions152, rt143, marks123 were dry-run-equivalent via the same harness
only after sealing — no code/case/config change after the seal (seal
re-verified 5/5 OK after all runs). B1/B2 registered runs reuse the
pilot's inline driver (no new files) on the sealed case file.

## What it means

One-of-many person relations ("a friend/daughter of") keep 215's fix and
still save; everything else indefinite ("a citizen/city of", "a mother
of") behaves exactly as 138i, so the two 215 regressions are repaired
with no other movement beyond 215's own set minus C013.

## What it does not mean

It does not fix the stale bench/rt136 golds (they still reward junk
echoes), and it does not learn inverses — untaught directions still
abstain, as on 215.

## Questions for Ben

Same as 215's: should the 25 bench65 `-fwd` golds and the 13 rt136
junk-triple golds be corrected upstream?

Reproduce: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
--no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_suitediff.py --agent scripts/fable_loop222_agent.py
--config artifacts/fable-ofteachb222-20260922/loop222-config.json --base
138i --out <dir> --only <suite>` (one suite at a time).
