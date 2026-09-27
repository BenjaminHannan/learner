# Exp 257 RESULTS: ear v4 (training data v4.1 + relation table v2)

## Result
**Registered FAIL on M2, M3 and M3b.** M1, M4 and M5 pass.
- The v4.1 ear with the brake and the unchanged 235b gate (tau 9.3) made **4 wrong saves** on the fresh blind panel
  (bar: 1).
- It saved **78 of 112** gold facts exactly (69.6%; bar 85%).
- It held back **24 of 112** as UNSURE (21.4%; bar 12%).
- Questions went well: **39/40** ASK frames exact (97.5%). The GPU median is **148.7 ms**.
- Compared with ear v3 in 235b, the wrong saves fell and recall rose a lot, but not enough to pass.
- Both seals were checked before loading and again after scoring: panel 2/2 OK, my SEAL 37/37 OK.

## Marks (arm A = v4.1 ear + brake + gate, tau 9.3; panel earpanel257, 150 items, run once)
| mark | bar | A | pass? | A_brake | A_raw | B (138i + 228) |
|---|---|---|---|---|---|---|
| M1 no_save saves | ≤ 1 | 1 | PASS | 5 | 5 | 0 |
| M2 wrong saves (4 statement families + no_save) | ≤ 1 | 4 | FAIL | 12 | 20 | 6 |
| M3 exact TEACH recall | ≥ 85% and ≥ B + 30 | 78/112 = 69.6% | FAIL | 98/112 = 87.5% | 98/112 = 87.5% | 15/112 = 13.4% |
| M3b UNSURE share of gold TEACH | ≤ 12% | 24/112 = 21.4% | FAIL | – | – | – |
| M4 exact ASK recall | ≥ 90% | 39/40 = 97.5% | PASS | 39/40 | 39/40 | – |
| M5 GPU median per turn | ≤ 300 ms | 148.7 ms (p90 289, max 437) | PASS | | | |

Other counts for A:
- GUARD_Q blocks: 0 in statement families.
- UNSURE on no_save: 4.
- Stray TEACH frames on questions: 0.

**Mac CPU speed (no bar).** The disk had 5.3 GB free, below the 8 GB floor, so this is a **12-turn dev pilot, not the
panel**: median 2085 ms, p90 4104, max 8825 (1 thread; checkpoint streamed over ssh). CPU and GPU greedy outputs
agreed 12/12.

## Per family (arm A; TEACH hit/gold, wrong, UNSURE; A_brake for comparison)
| family | A | A_brake | B |
|---|---|---|---|
| plain_teach | 23/25, 0 wrong, 2 unsure | 25/25, 0 wrong | 13/25, 2 wrong |
| varied_teach | 30/50, 2 wrong, 13 unsure | 39/50, 6 wrong | 0/50, 4 wrong |
| full_names | 15/22, 1 wrong, 4 unsure | 19/22, 1 wrong | 2/22, 0 wrong |
| corrections | 10/15, 0 wrong, 5 unsure | 15/15, 0 wrong | 0/15, 0 wrong |
| no_save | 1 saved (wrong), 4 unsure | 5 saved | 0 saved |
| questions (ASK) | 24/25 | 24/25 | – |
| chain_questions (ASK) | 15/15 | 15/15 | – |

## Per risk tag (arm A vs A_brake; TEACH hit/gold and wrong, or ASK hit/gold)
| tag | A | A_brake |
|---|---|---|
| R1 pronouns (statements, 18 items) | 27/37, 1 wrong, 9 unsure | 33/37, 4 wrong |
| R1rel pronoun + relative (5) | 7/12, 0 wrong, 4 unsure | 10/12, 1 wrong |
| R2 statement-shaped questions (no_save, 11) | 0 saved, 4 unsure | 4 wrong |
| R2tag / R2so / R2dq (no_save, 6 / 2 / 1) | 0 saved | 2 / 1 / 0 wrong |
| R2f question-word statements (4) | 1/4, 0 wrong, 3 unsure | 4/4, 0 wrong |
| R3 verb decides relation (12) | 12/18, 1 wrong, 5 unsure | 16/18, 2 wrong |
| R4 compound relatives, statements (12) | 16/24, 0 wrong, 5 unsure | 21/24, 0 wrong |
| R4 questions (5) + chain (1) | ASK 4/5 + 1/1 | same |
| R5 everyday relations, statements (17) | 17/19, 1 wrong, 1 unsure | 18/19, 1 wrong |
| R5 questions (5) + chains (4) | ASK 5/5 + 4/4 | same |
| R6 chains with a relative first hop (9) | ASK 9/9 | 9/9 |
| corrections (15) | 10/15, 0 wrong, 5 unsure | 15/15, 0 wrong |
| lower-case (statements 10 / no_save 7 / questions 6) | 9/13, 0 wrong / 0 saved / ASK 6/6 | 12/13 / 4 wrong / 6/6 |
| typo (5) and no-"?" questions (7) | all exact | all exact |

## Diagnosis of the FAIL (category level; one note, as the rules require)
The 4 wrong saves after the gate are 4 different kinds. All but one had no valid rival reading, so the gate could not
catch them:
1. **"Our …" as the subject (2 of 4).** Two turns used the first-person plural ("our" + a relative or a pet). The ear
   wrote the literal word "Our" as the subject. The sealed scorer counts only singular first-person words as the
   speaker, and the loop would store "Our" as if it were a person. The v4.1 training data has no turn that starts with
   "Our". In both cases the relation and value were right; only the subject was wrong.
2. **A future goal read as a job (1).** "Training to be" a job was saved as the current occupation. This was the one
   case where the gate's margin mattered: the right school fact in the same turn came out UNSURE (as `educated_at`, a v1
   relation separate from `school`).
3. **A hypothetical saved (1).** A "let's say …" turn, which is pretend by Ben's rules, was saved as a fact.

The one missed question used a **plural** relation word ("half-brothers"). The table only has the singular, so the brake
dropped it.

The gate's cost is the bigger problem for M3 and M3b. Without the gate (A_brake), exact recall is 87.5%, which is above
the bar, but there are 12 wrong saves. The gate removes 8 of those 12 and takes 20 correct saves with them (24 UNSURE).
Corrections (5 of 15 UNSURE) and varied wording (13 UNSURE) lost the most.

## Report-only comparisons (no bars)
- **The 235 dev split** (800 rows, training script dev_eval, v1 brake): v3 783/800, v4.0 781/800, v4.1 781/800. Every
  family is identical except teach, which is 339/351 vs v3's 341/351. Plain wording did not regress in any real way.
- **v3 vs v4 on my new dev classes** (tau 9.3, arm A; full table in PASSMARKS.md and dev/devreport.json):
  - All dev: v3 509/1069 with 45 wrong; v4.0 809 with 27 wrong; v4.1 834 with 11 wrong.
  - By class, v3 → v4.1:
    - C1, verb decides the relation: 3 → 43 of 63.
    - C2, compound relatives: 10 → 41 of 51 (0 wrong).
    - C3, pronouns: 25 → 103 of 136.
    - C5, no-"?" questions: 4 wrong → 3.
    - C6, table gaps: 22 → 52 of 76.
    - INF asks: 15 → 20 of 20.
- **v4.1 on the 235b panel** (run once, after the registered run; the sealed 235b scorer with table v2 installed; never
  used for tuning):

  | arm | v4.1 | v3 in 235b |
  |---|---|---|
  | A | 81/110 = 73.6%, 3 wrong, 20 UNSURE (18.2%), 0 no_save saves | 54/110, 5 wrong, 36 unsure |
  | ASK | 37/40 | 32/40 |
  | A_brake | 99/110, 9 wrong | 81/110, 20 wrong |
  | A_raw | 99/110, 11 wrong | 87/110, 27 wrong |

  The same three marks would fail there (M2, M3, M3b). B scored 17/110 here against 16/110 in 235b; the only
  difference is that table v2 is installed for matching.

## Predictions vs outcome (ledger P257.1–7)
| prediction | outcome | right? |
|---|---|---|
| .1 M1 passes | 1 save | right |
| .2 M2 2–4 wrong | 4 | right |
| .3 A 65–80%, A_brake 85–95%, B 10–25% | 69.6%, 87.5%, 13.4% | all right |
| .4 UNSURE 10–20% | 21.4% | range wrong (fail lean right) |
| .5 ASK 85–95% | 97.5% | range wrong (pass lean right) |
| .6 GPU median 120–200 ms | 148.7 ms | right |
| .7 overall PASS ~5% | FAIL | as leaned |

## Every move, in order
1. **Relation table v2** (scripts/claude_smolear257_table.py): 52 new relations, informal aliases on existing rows, and
   girlfriend/boyfriend → partner (the panel README's judgement call). Before the seal, after the fixture pilot, I added
   `workplace` and "place of work" as employer aliases, because the spec names `workplace` as a gold relation and v1
   lacked it.
2. **Data v4.0** (claude_smolear257_data.py): the v3 train plus 9,400 rows for classes C1–C7 and INF, plus 450
   held-out-template dev rows.
3. **Trained v4.0 on the BensPC 5070 Ti** with the unchanged 235 recipe: 12.3 min, checkpoint `dc41533b…`.
4. **Dev inference** for v4.0 and v3 (1,590 turns each). The sealed tau rule gave tau 12.8 with the fallback (the lowest
   rate was 2.1%). Dev showed that the "X's my W" contraction was being reversed, which caused most gated wrong saves.
5. **Data v4.1**: added the train-only class C8 (1,200 rows in new wordings for the contraction, chatty intro clauses,
   and "A's W is B and he/she …"). Earlier rows and the dev set are byte-identical. Retrained once: 12.5 min, checkpoint
   `55284dec…`.
6. **Dev inference for v4.1.** The sealed rule's main condition qualified: tau 9.3 (78.0% recall, 0.95% wrong).
7. **Wrote the 257 loader** (strict; chain_aliases on every hop; exit 3 on schema mismatch, exit 4 on a wrong sha), the
   scorer wrapper, arm B, turns and dev-report scripts. Piloted them on a synthetic fixture: gold predictions 100%, a
   wrong hop 1 fails, bad schemas exit 3.
8. **Mac CPU pilot**: 12 turns.
9. **Registration**: PASSMARKS.md, then SEAL.sha256.txt (37 files), then ledger lines P257.1–7.
10. **Registered run**: checked the panel seal, uptime and the GPU. The strict loader passed. Ran A once on the GPU with
    `--tau 9.3` and B once on the Mac, scored once, then re-checked both seals (all OK). Ledger outcome line appended.
11. **After the run**: v4.1 on the 235b panel (report only).

## Deviations (all disclosed; none after the seal)
- **Two training runs, not one.** v4.0 was trained and checked on dev before v4.1. Only the data changed between them
  (one added train-only class). v4.1 is the registered ear. The dev rows that show the C8 patterns are now
  near-distribution, so dev looks somewhat better than a fully held-out set would.
- **Table v2 changes matching slightly** compared with 235b: the scorer, brake and gate see v2 names and aliases. This
  includes `workplace` → employer and girlfriend/boyfriend → partner.
- **The 235b R3 dev rows (60)** were left out of the tau pick, because v4 trains on those verbs. They are reported as
  R3_indist.
- **Mac CPU timing is a 12-turn dev pilot**, not the panel, because of the disk floor.
- **No driver fixes and no re-runs.** Each registered arm ran once.

## What it means
- Better training data really helped. On the same fixed gate, the new ear got about 70% of facts exactly right, against
  about 49% for the old ear. It made fewer wrong saves (4 vs 5 on a harder, fresh panel; 3 vs 5 on the old panel), and
  it answered almost every question correctly, including all two-step questions that start with a relative.
- The specific problems from 235b mostly went away: "teaches at" vs "studies at", compound relatives like step- and
  -in-law, pronouns, and corrections with extra facts. Two wrong saves carry one of those tags: an R1/R3 item that
  was really a "training to be" problem, and an R5 item that was really an "our" problem.
- The remaining mistakes are new kinds: "our" instead of "my", future plans read as facts, pretend ("let's say")
  statements, and plural relation words. Each is a small, nameable gap, not a general failure to read.
- The gate is now the main thing holding recall down. Without it the ear reaches 87.5%, but it also makes 12 wrong
  saves. With it, wrong saves drop to 4, and 1 in 5 true facts is held back as unsure.

## What it doesn't mean
- It does not mean the ear is safe to wire into the loop. The rule is at most 1 wrong save, and it made 4.
- It does not show that one more round of data would pass. The four new error kinds were found on the test panel, so
  fixing them now would be tuning on the test. A fresh blind panel would be needed.
- The "our" errors are not a scorer bug to excuse. The loop would really store "Our" as a person, so they count.
- The 235b-panel numbers are a report, not a second test. That panel's categories helped choose the v4 data classes.
- The dev numbers (78% recall, 0.95% wrong) are not a promise for new text. Part of dev is now close to the training
  patterns, and the panel's wrong rate was again higher than dev's.

## Files
- **Scripts** (new, additive):
  - scripts/claude_smolear257_table.py, _data.py, _devset.py, _infer.py, _tau.py, _devreport.py
  - scripts/claude_smolear257_panel.py, _score.py, _armb.py, _turns.py, _on235b.py
- **Artifacts:** artifacts/claude-smolear257-20260922/
  - relation_table_v2.json; data/ (v4.0); data41/ (v4.1)
  - train/ (v4.0 records); train41/ (v4.1 records, CKPT.sha256.txt)
  - dev/ (dev sets, preds for v3/v4.0/v4.1, tau.json, tau_v40.json, devreport.json, CPU pilot)
  - run/ (turns, a_preds_gpu.json, b_preds.json, score.json)
  - on235b/ (report only)
  - PASSMARKS.md, SEAL.sha256.txt, RESULTS.md
- **Checkpoints stay on BensPC:** C:\Users\benja\smolear235\out_v41 (v4.1, registered) and out_v4 (v4.0).
