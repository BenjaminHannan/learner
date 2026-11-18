# D4: TEACH data profile review and split check

Written 2026-10-08 20:57 ET by a Haiku worker. Track: talker data. TEACH is the B1 training set for the talker (the part that turns the thinker's state into words), and the four English eval sets test the talker. This is separate from the village model and the small card experiments; no village or card result is claimed here.

Method: I did not redo the profile. I recomputed the key numbers from the raw TEACH file (171,940 rows, streamed) and the eval JSON, and rebuilt every split label from the kind rule and the passage guard in `split_proposal.json`. Practised-slice membership was taken from `practised_slice_ids.txt`: I checked it (no passage on the train side, all kinds kept) but did not re-derive the ascending sha256(source_text) selection order (untested). Scripts are in `D4_work/` (`analyze_d4.py`, `analyze_d4b.py`); raw outputs are `D4_work/run.txt`, `D4_work/run_b.txt`, `D4_work/results.json`, `D4_work/per_kind.csv`. Word = regex `[a-z0-9']+` on lowercased text (same as `teach_profile.py`). Answer = `canonical_answer` with surrounding space and one trailing full stop stripped (same as `clean()`). Labels: **shown** = I ran it or read it; **suggested** = reasoning; **untested** = not measured.

## Summary

- **Split checks: 20 of 21 PASS (shown).** The one FAIL is a stricter check I added: 105 passages (130 dev rows, 130 test rows) occur on both the dev and test sides. The proposal's own rules do not cover dev-vs-test overlap, so this is a gap in v1, not a broken rule.
- **v2 fixes that gap** by moving the 130 dev rows whose passage also appears in test into the dropped bucket. The train side, the practised slice and test are unchanged, so `practised_slice_ids.txt` stays valid. Written to `split_proposal_v2.json`.
- **Yes/no mix is 51% in TEACH and in every split, but 10.7% in the four eval sets (shown).** Dev and test therefore measure a different mix from the eval. The proposal's optional thinning would fix this, but it is not applied in v2 (Ben or Astra decides).
- **Answer length is the main mismatch (shown).** 18.4% of TEACH short answers are longer than 8 characters. In the eval sets, 60.6% are. An 8-character cap would drop 15,514 TEACH rows and remove most of the long answers the eval asks for.
- **TEACH short answers are almost all copies of the source text (shown):** 97.0% occur verbatim (case-insensitive) in `source_text`, and 0.45% contain a word absent from the prompt. TEACH rewards copying (suggested: this may favour the copy-style failure seen in PR #37; untested).
- **Eval kinds (shown):** the six eval families that appear in TEACH are all on the train or practised side. Sets FRESH-R3 and GEN-R4 use only these (192 of 384 eval questions). Sets NEW-KINDS-R5 and NEW-KINDS2-R6 use the 12 families absent from TEACH by name (the other 192 questions).

## 1. Stats (shown; `D4_work/results.json`)

### Overall TEACH

| measure | value |
|---|---|
| rows | 171,940 (yes/no 87,807; short_answer 84,133; no other types) |
| yes/no answers | yes 49,442; no 38,365 (yes = 56.3% of yes/no rows) |
| yes/no share | 51.07% |
| empty answers | 0 |
| short-answer words (mean / p50 / p90 / max) | 1.54 / 1 / 2 / 7 |
| short-answer chars (mean / p50 / p90 / max) | 6.76 / 6 / 12 / 32 |
| short answers > 8 chars | 18.44% (15,514 rows, all short) |
| short answer is substring of source_text (case-insensitive / case-sensitive) | 97.01% / 96.07% |
| short answer is substring of paraphrase (case-insensitive / case-sensitive) | 94.42% / 88.98% |
| short answer is substring of question | 1.77% |
| short answer has a word absent from source+paraphrase+question | 0.45% (headline; prompt = all three fields) |
| short answer has a word absent from source+question (passage + question only) | 0.94% (the talker's likely view; `D4_work/run_c.txt`) |
| short answer has a word absent from paraphrase+question | 5.29% |

These match `teach_stats.json` `teach.overall` (0.9701, 0.9607, 0.9442, 0.8898, 0.0177, 0.0045). Yes/no rows have no substring test, since "yes"/"no" are not spans.

### Per split (rebuilt from the v1 rules; all counts match `split_proposal.json`)

| split | rows | yes/no share | kinds | passages | short chars mean | short > 8 chars |
|---|---|---|---|---|---|---|
| train | 125,544 | 51.08% | 46 | 108,464 | 6.76 | 18.1% |
| practised_slice | 2,001 | 51.82% | 46 | 1,725 | 6.55 | 15.8% |
| dev | 25,127 | 50.98% | 8 | 20,766 | 6.65 | 17.8% |
| test | 18,300 | 51.15% | 6 | 15,378 | 7.01 | 22.4% |
| dropped (passage overlap) | 968 | 48.76% | 43 | 705 | 6.12 | 9.1% |

Test has the most long answers (22.4%), but this is a mild imbalance, not a fail.

### Dev and test kinds (shown; from `per_kind.csv`)

| kind | side | rows | yes/no | short chars mean | > 8 chars | source-substring |
|---|---|---|---|---|---|---|
| choice_pick | dev | 3,274 | 0.509 | 6.93 | 22.7% | 98.4% |
| occupation | dev | 3,292 | 0.506 | 6.02 | 20.5% | 91.8% |
| opponent | dev | 3,124 | 0.518 | 8.58 | 31.0% | 97.9% |
| role_in_play | dev | 2,849 | 0.512 | 7.60 | 23.5% | 95.8% |
| found_item | dev | 3,334 | 0.500 | 4.88 | 2.5% | 99.6% |
| forgot | dev | 2,947 | 0.522 | 5.54 | 7.4% | 98.2% |
| object_eaten | dev | 3,156 | 0.528 | 6.04 | 13.1% | 93.8% |
| permission | dev | 3,151 | 0.484 | 7.73 | 22.2% | 98.2% |
| family_relation | test | 3,234 | 0.485 | 7.33 | 18.8% | 99.0% |
| goal_want | test | 2,947 | 0.543 | 5.65 | 10.8% | 97.3% |
| object_read | test | 3,234 | 0.485 | 5.82 | 12.6% | 98.2% |
| object_made | test | 3,234 | 0.485 | 5.31 | 6.7% | 98.9% |
| rule_must | test | 2,529 | 0.550 | 9.48 | 46.7% | 98.4% |
| team_member | test | 3,122 | 0.534 | 9.28 | 47.6% | 98.1% |

Across all 60 kinds, the yes/no share runs from 37.3% (title_role) to 76.1% (caretaker). The 51% overall is an average over kinds. Lowest source-substring rates: part_whole 70.9%, replacement 90.1%, category_member 90.6%, comparative_direction 90.7%. Highest novel-word rates: teacher_of 2.3%, object_eaten 2.1%, part_whole 1.8%.

## 2. Split checks (shown; `D4_work/run.txt`)

| check | result | detail |
|---|---|---|
| dev and test kind lists disjoint | PASS | intersection empty |
| dev/test kinds exist in TEACH | PASS | 8 dev and 6 test kinds, all in the 60 TEACH kinds |
| leave-kinds-out: no dev/test kind on the train side | PASS | train-side kinds = 46, none in dev or test |
| every dev/test row labelled dev/test, no other row is | PASS | |
| rebuilt counts match proposal (train, slice, dev, test, dropped) | PASS (5 of 5) | 125,544 / 2,001 / 25,127 / 18,300 / 968 |
| yes/no share within 0.02 of TEACH 51.07% | PASS (4 of 4) | train 51.08, slice 51.82, dev 50.98, test 51.15 |
| practised-slice ids: unique, 2,001 lines | PASS | |
| practised-slice ids: all are TEACH ids | PASS | 2,001 of 2,001 |
| practised-slice rows all come from kept (train-side) kinds | PASS | 46 kinds, none dev or test |
| practised-slice passages not on the train side | PASS | 0 shared |
| dev and test passages not on the train side | PASS | 0 shared |
| **dev and test share no passage** | **FAIL** | **105 shared passages: 130 dev rows, 130 test rows.** Stricter than the proposal's own rules. Shared passages are multi-kind passages. |

The proposal's `verification_expected_zero` entries are also consistent with the recomputation (0 for each).

Yes/no mix versus eval (shown): the four eval sets pooled are 10.68% yes/no (41 yes/no of 384 questions in the teach_stats count; my recount: 10.68%). TEACH and all splits are about 51%. This is a mismatch, not a split failure, because the proposal targets TEACH's mix. The proposal's optional thinning (`dev_test_eval_mix_alternative`) keeps 2,542 of 22,171 dev+test yes/no rows, giving 10.68% (shown by arithmetic; the sha256 ordering of kept ids was not re-derived, untested).

## 3. Eval-set kinds in TEACH (shown)

- Six eval families are present in TEACH by exact name, all on the train or practised side: comparative_direction, event_ordering, explicit_negation_with_positive_alternative, giver_recipient_roles, two_simple_relations_combined, unambiguous_descriptive_reference. Each has 2,805 to 3,221 TEACH rows. None is on dev or test.
- The 12 new families also use question forms that TEACH never uses (how many, how much, how long, why, when; see section 3b).
- Twelve eval families are absent from TEACH by name: attribute_lookup, cause_reason, counting_quantity, direction_turn, duration_length, instrument_purpose, location_tracking, price_cost, source_origin, speech_quote, time_when, weather_condition.
- Set-level: FRESH-EN-R3 and GEN-HELDOUT-R4 use only the six seen families (96 questions each). NEW-KINDS-R5 and NEW-KINDS2-R6 use only the twelve new families (96 questions each). Consistent with the arithmetic: 6 × 32 = 192 and 12 × 16 = 192.
- Not held out by kind: half of the eval questions (FRESH and GEN) test kinds TEACH already trains on, on different passages.
- No eval `source_text` or `paraphrase` appears verbatim in TEACH (0 of the 192 eval examples). Ten eval questions match a TEACH question string exactly (FRESH 4, GEN 5, R5 1); these are generic wordings.
- Token-overlap hints (suggested only): direction_turn shares the token "direction" with comparative_direction. Not the same kind. The eight SPARES kinds named in `kinds.py` (for example instrument_played, gift_for) are not in TEACH (shown: 0 of 8), so they are unused reserve kinds.

## 3b. Question forms behind the new families (shown; `D4_work/run_c.txt` and a one-off count)

- TEACH question text has zero occurrences of "how many", "how much", "how long", "why " and "when " (anywhere in the question). Wh-word counts are dominated by who, what and which. The most common first words are who 50,961, was 33,215, what 30,367, did 26,751, is 14,504, does 8,087, which 3,037. "where" is not among the top 15 first words.
- Only 73 TEACH rows (0.04%) have a quote mark in the source or question.
- The eval families that are new by name use exactly these missing forms (shown, first two words of questions, top entries): counting_quantity "how many" (13 of 16 items), duration_length "how long" (15 of 16), price_cost "how much" (14 of 16), cause_reason "why did"/"why was" (at least 8 of 16), time_when "when did"/"when does" (14 of 16). speech_quote items need quoted or reported speech.
- So the "new" label is stronger than a name-only match: the question forms behind 5 of the 12 new families are absent from TEACH. This is still a count of forms, not of answers. Whether a talker generalises to them is untested.

## 4. Say-back targets (shown)

Target = `question` (verbatim) + space + answer. Example: "Who was playing the game? Hugo". The verbatim question is a stand-in for a declarative restatement such as "Hugo was playing the game"; the declarative form is untested here, and its lengths would be somewhat longer.

| measure | all rows | short-answer rows |
|---|---|---|
| target chars mean / p50 / p90 / p99 / max | 28.3 / 27 / 37 / 47 / 73 | 30.1 / 28 / 39 / 48 / 73 |
| target words mean / p90 / max | 5.9 / 8 / 14 | 6.1 / 8 / 14 |
| answer chars mean / p50 / p90 / max | 4.6 / 3 / 8 / 32 | 6.8 / 6 / 12 / 32 |
| answer words mean / p90 / max | 1.27 / 2 / 7 | 1.54 / 2 / 7 |
| answers > 8 chars | 15,514 (9.0% of rows) | 15,514 (18.4% of short rows); 0 of yes/no |

- The most frequent over-8-character answers are "a balloon" (437), "a pumpkin" (398), "a lantern" (395), "a goldfish" (389), "a squirrel" (282), "a compass" (227). There are 6,283 distinct such answers. The top entries are mostly article-plus-noun phrases.
- Eval answers for comparison (shown): 60.6% of eval short answers exceed 8 characters (FRESH 63.5%, GEN 78.4%, R5 39.3%, R6 60.5%), with mean 10.4 characters.

Implication for the B2 cap (suggested): a cap of 8 characters keeps 81.6% of TEACH short answers, but only 39% of eval short answers. A talker trained under that cap would rarely see the answer lengths the eval uses. This is a real design question for Ben or Astra, not something to fix in the split.

## 5. v2 proposal (shown; `split_proposal_v2.json`)

- Change: dev rows whose `source_text` also occurs in a test row move to `dropped_dev_test_passage_overlap`. That is 130 rows (IDs in `D4_work/v2_dev_rows_moved_to_dropped_ids.txt`).
- Train side, practised slice and test are unchanged, so `practised_slice_ids.txt` stays valid.
- Result: dev 24,997 rows, yes/no 50.99%, 8 kinds, 20,661 passages. Test unchanged (18,300 rows, 6 kinds).
- Verification (shown, all PASS): 0 dev/test shared passages; 0 dev/test passages on the train side; slice IDs unchanged; all 8 dev and 6 test kinds present.
- Option B (also drop the 130 test rows) was computed for comparison and not chosen, because it would shrink the test set that is the held-out measure.
- The v2 JSON renames the v1-only blocks with a `_v1` suffix (for example `rule_kind_level_v1`) and adds `rule_kind_level_v2` and `rule_dev_test_passage_guard_v2`. The train-side passage guard still uses the v1 dev+test passage set. That is conservative and keeps the train side identical to v1.
- Not applied in v2: the eval-mix thinning, and any change to the 8-character cap question.

## Open questions

1. Yes/no mix: TEACH is 51% yes/no, the eval sets 10.7%. Should dev/test follow the eval mix (the proposal's thinning, which discards about 19,600 yes/no dev+test rows)?
2. Answer length: is the 8-character B2 cap meant for training targets, for talker output, or both? The eval answers exceed it 61% of the time.
3. Copy rate: 97% of TEACH short answers are verbatim source spans. Is a copy-heavy training mix part of the PR #37 failure on unseen kinds? Untested here.
4. Should the eval families seen in TEACH (FRESH-R3, GEN-R4) be reported separately from the unseen-kind sets (R5, R6)? I recommend yes; they test different things.

## Handoff

A fresh agent (or Astra) can use `split_proposal_v2.json` as the dev/test split after reviewing the 130-row move. Before a talker run, decide the answer-length cap (open question 2) and the dev/test yes/no mix (open question 1). Do not train on dev or test, and do not use the eval sets as training data.

## Files

- Report: `/Users/ben-hannan/Desktop/projects/talker-gap-wt/talker_gap/diag/D4-teach-data.md`
- v2 split: `/Users/ben-hannan/Desktop/projects/talker-gap-wt/talker_gap/diag/split_proposal_v2.json`
- Scripts and outputs: `/Users/ben-hannan/Desktop/projects/talker-gap-wt/talker_gap/diag/D4_work/` (`analyze_d4.py`, `analyze_d4b.py`, `run.txt`, `run_b.txt`, `results.json`, `per_kind.csv`, `v2_dev_rows_moved_to_dropped_ids.txt`)
