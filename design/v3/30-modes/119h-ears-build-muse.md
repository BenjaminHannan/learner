# 119h ears build (Muse): varied-shape occupation rows, and nothing else

## Why 119g failed

The 119g relation-conditioned head works: raw exact on reading94b rose to
91/82/100 (from 119f's 24/19/27) at ~2x precision. But occupation exact
stayed 1/94 on every seed. The director's diagnosis: the 5,000 synthetic
occupation rows use exactly two templates, both past tense ("NAME was a/an
NAT JOB." and "NAME (Y1-Y2) was a/an NAT JOB and JOB2."), each labelling
ONLY occupation although the sentence also states a nationality and dates.
The model learned the surface cue "was", not "a job word": on "NAME is a
NAT JOB." or "(born 12 May 1970)" brackets, occupation ranks 6th or lower
and never reaches the K=3 read-outs, and even the forced read-out is exact
on only 2-10/51.

## The one change

`scripts/fable_ears119h_data.py` replaces 119f's `occ_rows` (everything else
is imported: FIRST/LAST/DEMONYMS/PROFESSIONS, the 119b lengthener, the 119g
model/recipe/scorer). Each sentence draws a varied shape; every fact stated
gets one row sharing the same text (1,760 sentences → 5,000 rows):

| shape | target | measured |
|---|---|---|
| is / was (was with death dates; is 70/30 elsewhere) | ~50/50 | 860 / 900 |
| bracket (6 forms: born-DMY, born-year, born-DMY-in-PLACE, DMY span, year en-dash span, year hyphen span) | 60% | 58.9% (1,036) |
| retired / former / professional | 15% | 15.3% (269) |
| nationality demonym | 85% | 85.6% (1,506) |
| job list (2-job / 3-job) | 30% | 29.5% (250 / 270) |
| multi-word first job (film director, rugby player, television presenter, civil engineer, +48 more) | 35% | 34.6% (609) |

Rows per relation: occupation 1,760 (object = FIRST job span only),
country of citizenship 1,506 (demonym span), date of birth 1,036, date of
death 507, place of birth 191. The citizenship-on-demonym choice follows the
pool's own WebRED rows: 1,030 demonym vs 545 country-name objects (361
other). Spans/dir/gold47 match 119f exactly; the text under every span is
asserted. The person for the novelty check comes from the gold subj span
(119f's split on " was " breaks on "is"). Zero sentence overlap and zero
name hits vs the OLD panel; reading94b never opened (path only).

Because the relation head is a softmax trained one-row-per-fact, stated
relations now split the probability instead of one surface cue taking all —
occupation should enter the K=3 read-outs on real shapes.

## The rest (unchanged, sealed)

RelCondEars by import, teacher-forced relation, seeds 11911-11913, batch 32,
2 epochs, AdamW 3e-5, steps asserted == 8838, CAL temps + 47 tau rule, K=3 /
FLOOR=0.10 (119g values, not re-chosen). Pool gates: synth 60,000, occ
5,000, kept in [141377, 141408]. The 119h scorer imports 119g's with the D1
K=1-row wrap built in (score47g keeps the flat form). No step 0 — 119g's
registered numbers are the baseline. Wave: pool → 3 seeds → 47 scoring
(descriptive) → reading94b + reading94 at K=1 and K=3, ≈ 39 min (≤ 40).

## Evidence (pre-seal, Mac CPU, no scores)

Clean-folder import + runtime closure: CLEAN-IMPORT-OK-4, rows sha
9909b6d1, novelty clean. Smoke: deterministic (same sha twice), 5,000 rows,
span asserts on all rows, novelty OK, 50 teacher-forced steps on the new
rows with loss 23.47 → 5.12. PASSMARKS sealed before any registered run;
predictions P119h.1-6 in the ledger.

## Risks

If occupation still ranks below the K=3 cut on real sentences, the fail
will look like 119g's (M1 flat, M2/M3 passing) — the next step would be
teaching the reader (span accuracy), not the picker. If M2 drops, the
multi-fact rows may be stealing probability from other relations.

What it means: the one-change build is staged, sealed, and pipeline-proven;
the wave can launch.
What it does not mean: no score and no occupation claim exist until BensPC
decides.
