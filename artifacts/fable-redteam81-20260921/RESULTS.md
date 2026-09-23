# RESULTS — redteam81 listening-doorway probe (2026-09-22)

Result first: 73 adversarial English turns in 17 sequences through
AgentLoop + FakeEars + Listening M1 + notebook contract: 74/74 cases OK,
0 doorway/contract BUGs, 0 UNCLEAR, 0 crashes. The doorway held every rule
under test; all sharp edges are FakeEars scaffolding limits (safe clarifies),
not doorway bugs. Nothing was fixed (red-team rules).

## Integer summary

turns 73 (+1 harness setup) | OK 74 | BUG 0 (critical 0, high 0, medium 0, low 0) | UNCLEAR 0 | crashes 0

## What was tested

`scripts/fable_redteam81_probe.py` drives the real modules read-only, one
fresh AgentLoop per sequence. Coverage: duplicate first name + question (7);
"actually/no" corrections (5); "forget what I said" (3); statement-as-question
and vice versa (5); double facts (3); pronouns (4); typos (4); case/space/
unicode (8); long/empty/name-only (5); status words as values (4); JSON/
structured lines (3); self-reference (4); 3-hop answer + true 4-hop refuse (6);
"is it true" yes/no (3); user-herself questions (4); contradiction yes/no paths
(4); reported speech/hypotheticals (3). Full log:
`artifacts/fable-redteam81-20260921/fable_redteam81_results.json`.

## Doorway/contract behaviour (held under attack)

Conflict gating (A-03, P-02, L-03, H-03, J-02: "change it to?", no silent 2nd
value); corrections supersede (B-02, B-05, L-04, P-03 incl. confirm-yes path);
ambiguous name asks, never guesses (A-07 "Which one"); UNKNOWN_ENTITY refusals
(F-04, O-04); MISSING_FACT not guesses (E-03, M-06); 3-hop answers, true 4-hop
refuses "1 to 3" (M-04/M-05); self-loop terminates (L-02 "Mira"); case/space
normalised through contract `_norm` (H-03 CONFLICT); status-word values don't
confuse statuses (J-02 conflict, J-04 literal); 6000-char literal saved with no
crash (I-04); empty/whitespace/name-only clarify with 0 writes (I-01..03);
reported speech writes nothing and creates nobody (Q-01, check_no_entity Tom);
"my"-turns create no entity, infer nothing (O-02/O-04, check_no_entity my).

## FakeEars limitations (scaffolding, NOT bugs)

Safe clarifies, 0 writes: pronouns (B-04, F-03), "forget X" (C-02), imperatives
(D-03), yes/no questions (D-04, N-02), JSON (K-01), structured lines (K-02),
uppercase-'S possessive `MIRA'S` (H-02), accented/fullwidth names stored as
separate people (H-05/06, contract `_norm` folds case/space only), typo names
become separate people (G-02, teach-creates by design). Person/alias/forget/
quote acts are unreachable in English (2nd Mira seeded via contract). Two
lossy-but-faithful writes: D-01 `"Mira's city is Lisbon?"` TEACHES with value
`Lisbon?` ("?" kept); E-01 packs a conjunction into one literal, 2nd fact lost
(E-03 MISSING). Sharpest gap: interrogative punctuation is ignored (D-01).

## Marks

| id | mark | bar | outcome |
|----|------|-----|---------|
| R1 | >= 60 turns, each reported | 73 turns, 74/74 in JSON | PASS |
| R2 | expected + observed + verdict; BUG reproducers <= 15 lines | 74/74, 0 BUGs so 0 reproducers | PASS |
| R3 | no fixes, no foreign edits | probe + docs only; `git status` shows no modified tracked files | PASS |
| R4 | report <= 1,200 words | this file + doc 81 | PASS |

## What it means

The listening doorway does what its docstring promises on all 73 adversarial
English turns: clarify-or-write, corrections supersede, ambiguity asks,
questions never write (except D-01's "-as-statement" parse), nothing personal
inferred.

## What it does not mean

One clean probe wave through a template parser; real English ears are
unprobed, and D-01/E-01 show the template layer silently reshapes user intent
before the doorway ever sees it.

## Deviations

First run scored 12 UNCLEAR from my own wrong `must` substrings (e.g. expected
"one-word", product said "another way"; mislabelled 3-hop as 4-hop; forgot
"My city" has no 's). Fixed harness expectations only, added 2 turns (H-03
lowercase-possessive split, M-05 true 4-hop), re-ran once. No product change;
no registered FAIL; no re-runs into passes.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_redteam81_probe.py --out artifacts/fable-redteam81-20260921

Questions for Ben: none.
