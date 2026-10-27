# Exp 257 PASSMARKS: ear v4 (training data v4.1 + relation table v2), sealed before panel 257 is opened

ONE CHANGE vs 235b: the training data, plus the relation-table rows that data needs.
- Same base model (SmolLM2-360M), same recipe and hyperparameters (claude_smolear235_train.py, unchanged, run with the
  235 arguments: epochs 2, the 235 dev split for its dev_eval).
- Same output format, brake (claude_smolear235_model.brake) and gate (claude_smolear235b_beam.gate, k = 4).
- Brake, gate and scorer are imported unchanged. The only thing they see differently is relation table v2, which is
  installed by rebinding the model module's table globals (claude_smolear257_table.install); no code was edited.

**Registered ear = v4.1.** Checkpoint sha256 `55284dec92ea3e6d5d9d99c5afa99ae80a73eafaf644a0c2ca268dcb9fad0bd2`.
It is kept on BensPC (out_v41); records are in train41/.

## The data (scripts/claude_smolear257_data.py; seed 257)
- **v4.1 train** = the v3 train (36,000 rows, unchanged) plus 10,600 new rows in my own templates:
  - C1, the verb decides the relation: 1,300 rows. Teaches, coaches, works or lectures at → employer; studies at, goes
    to, pupil, student or enrolled at → school. Values carry misleading nouns.
  - C2, compound relatives kept whole: 1,500 rows, of which 20% are plain-relative contrast rows.
  - C3, pronouns resolved to the named person: 1,400 rows, including first person + relative + pronoun, and two people
    of different gender.
  - C4, corrections: 900 rows. New value only; no old-value frame.
  - C5, statement-shaped questions with no "?" → NONE, and question-word statements → TEACH: 1,300 rows.
  - C6, table-gap relations: 1,900 rows.
  - C7, two-hop questions with a relative as hop 1 (canonical names): 800 rows.
  - INF, informal asks: 300 rows.
  - C8: 1,200 rows (see below).
- sha256 of the v4.1 train file (data41/train.jsonl): `f5a29f12…5211`.
- **v4.0 and the v4.1 step (disclosed).** The first training set (v4.0, data/, sha `acc081d7…3cde`, checkpoint
  `dc41533b…3e99`) was trained and run on dev. Dev showed three confident-error patterns:
  - "X's my W" (the contraction) was read as a possessive, which reversed the frame. This caused 19 of v4.0's 27 gated
    dev wrong saves at tau 9.3 (C2 13, C6 6).
  - A chatty intro clause became a frame.
  - In "A's W is B and he/she …", the pronoun fact went to A.

  I added one train-only class C8 (1,200 rows) in NEW wordings for these three patterns, generated after all the
  earlier rows. The first 45,400 train rows and all dev rows are byte-identical to v4.0. I then retrained once with the
  same recipe. The dev rows that show these patterns are now near-distribution (the pattern is trained, the exact
  template is not). This is the only data iteration; both runs are reported.
- **Panels.** No TEST-ONLY panel item was read or used. The 235b failures were used at category level only.
- **Panel README.** From the panel-257 README I read the schema and judgement-call sections, as the director allowed.
  One judgement call is followed in the data: girlfriend and boyfriend are `partner` (table v2 aliases).

## Relation table v2 (scripts/claude_smolear257_table.py → relation_table_v2.json, sha `f499f411…6fca`)
- The v1 rows are unchanged except for added aliases, and 52 new relations are appended.
- The new relations cover:
  - step-, half-, -in-law, great-, second cousin, niece and nephew;
  - godparents and godchildren, fiancé, ex-spouse;
  - roommate, classmate, teammate, tutor, landlord, dentist, vet, babysitter and therapist;
  - instrument, favourite food, drink, sport, book, film, animal, season and subject;
  - allergy, car, and new pets.
- The added aliases on existing rows are informal true synonyms: hubby, missus, bro, sis, mam, nan, gran, grandad,
  bestie; and girlfriend, boyfriend, gf and bf → partner.
- `workplace` and "place of work" were added as employer aliases after the fixture pilot. The panel spec lists
  `workplace` as a gold relation name, v1 had no such key, and brief class 1 says "workplace/employer". The v4 data
  never emits it, so this changes matching only.

## tau (dev only; panel 257 not opened)
- **Dev = 1,530 rows** (dev/dev_tau.jsonl):
  - the 235b dev set: 900 rows of the 235 held-out-template split, plus R1 90, R2 70, R2s 20;
  - plus 450 new held-out-template rows: C1 60, C2 60, C3 60, C4 50, C5 70, C6 90, C7 40, INF 20.
  - The 235b R3 rows (60) are excluded from tau as `R3_indist`, because v4 trains on those verbs. They are reported
    separately.
- **Rule:** the sealed 235b rule (claude_smolear235b_tau.main, unchanged): the most recall at a wrong-save rate
  ≤ 1% per non-question row; otherwise the lowest rate, with ties going to the smallest tau.
- **On v4.1 the main rule qualifies (no fallback): tau = 9.3.** At tau 9.3, dev recall is 787/1009 = 78.0%, with
  11 wrong saves in 1,158 rows (0.95%), 176 UNSURE and 31 GUARD_Q.
- For reference, v4.0 on the same rule used the fallback: tau 12.8 (dev/tau_v40.json).

Dev at tau 9.3 (TEACH hit/gold and wrong; A = brake + gate), from dev/devreport.json:

| dev slice | v3 A | v4.0 A | v4.1 A (registered) | v4.1 A_brake |
|---|---|---|---|---|
| all (incl. R3_indist) | 509/1069, 45 wrong | 809/1069, 27 wrong | 834/1069, 11 wrong | 1027/1069, 38 wrong |
| base (235 dev) | 328/434, 3 | 374/434, 2 | 364/434, 2 | 428/434, 6 |
| C1 verb decides | 3/63, 4 | 41/63, 0 | 43/63, 0 | 59/63, 4 |
| C2 compound relatives | 10/51, 1 | 29/51, 13 | 41/51, 0 | 51/51, 0 |
| C3 pronouns | 25/136, 14 | 89/136, 0 | 103/136, 2 | 122/136, 4 |
| C4 corrections | 29/50, 0 | 38/50, 0 | 36/50, 0 | 49/50, 1 |
| C5 no-"?" questions (NONE) and question-word statements | 15/24, 4 | 24/24, 1 | 24/24, 3 | 24/24, 5 |
| C6 table gaps | 22/76, 1 | 47/76, 6 | 52/76, 0 | 71/76, 2 |
| R1 pronouns (235b dev) | 65/155, 7 | 107/155, 5 | 116/155, 4 | 143/155, 9 |
| R2 statement-shaped questions | 5 wrong | 0 | 0 | 7 |
| R3_indist | 7/60, 6 | 54/60, 0 | 47/60, 0 | 60/60, 0 |

ASK hit/gold at tau 9.3:

| dev slice | v3 | v4.0 | v4.1 |
|---|---|---|---|
| all | 352/372 | 366/372 | 366/372 |
| C7 (chains) | 40/40 | 40/40 | 40/40 |
| INF | 15/20 | 20/20 | 20/20 |
| C1 asks | 3/11 | 8/11 | 8/11 |

The 235 dev split (training script dev_eval, 800 rows, v1 brake): v3 783/800, v4.0 781/800, v4.1 781/800. The
families are identical except teach: v3 341/351, v4.x 339/351.

Mac CPU: the disk has 5.3 GB free, below the 8 GB floor, so the full panel is not run on the CPU. **12-turn dev pilot
(v4.1, checkpoint streamed over ssh, 1 thread): median 2085 ms, p90 4104, max 8825; CPU and GPU greedy agree 12/12.**
GPU dev (1,590 turns, no gate timing): median 145 ms.

## Panel + scoring
- **Panel:** artifacts/claude-earpanel257-20260922/panel.jsonl.
  - Before loading and after scoring: `shasum -a 256 -c artifacts/claude-earpanel257-20260922/SEAL.sha256.txt` from the
    repo root.
  - The loader also checks the panel's sha itself.
- **Loader:** scripts/claude_smolear257_panel.py, strict.
  - Line keys, the 150 lines and the family counts are as in 235b.
  - ASK = exactly {act, subject, relation, chain, relation_aliases, chain_aliases}.
  - chain null ⇔ chain_aliases null; chain_aliases[1] == relation_aliases.
  - Any deviation prints SCHEMA-MISMATCH and exits with code 3 (nothing scored). A sha mismatch exits with code 4.
  - Two-hop gold = `chain`, with chain_aliases on **every** hop.
  - `clear` is ignored (clear:false items count fully).
  - Tags are the R-tags plus lower, typo, noq and correction.
- **Scorer:** scripts/claude_smolear257_score.py = claude_smolear235b_score.score, unchanged, with table v2 installed.
  - The matching is the sealed 235 functions.
  - It refuses predictions that were run with a tau other than the sealed one.
- **Arm B:** scripts/claude_smolear257_armb.py → claude_smolear235_armb.run_items (138i + 228), statement families only,
  run on the Mac.
- **Arm A:** scripts/claude_smolear257_infer.py (= claude_smolear235b_infer with table v2) on the BensPC GPU with
  `--tau 9.3`, run once. Turns come from scripts/claude_smolear257_turns.py.
- Arms reported: A_raw, A_brake, A (registered) and B; per family and per tag.
- **Fixture pilot** (a 150-line synthetic panel in the 257 schema, my own made-up turns):
  - Predictions equal to gold score 114/114 TEACH and 40/40 ASK.
  - A wrong hop 1 on the 15 chains drops ASK to 25/40, which shows hop-1 aliases really count.
  - Two bad-schema fixtures exit with code 3; the wrong panel sha exits with code 4.
  - Arm B ran on 3 fixture items.

## Marks (A = v4.1 ear + brake + gate, tau 9.3); same bars as 235b
| mark | bar |
|---|---|
| M1 | no_save: TEACH frames saved ≤ 1 |
| M2 | wrong saves across plain_teach + varied_teach + full_names + corrections + no_save ≤ 1 |
| M3 | exact TEACH recall on plain_teach + varied_teach + full_names + corrections ≥ 85%, and ≥ B + 30 points |
| M3b | UNSURE TEACH frames on those 4 families ≤ 12% of their gold TEACH frames (GUARD_Q reported separately) |
| M4 | exact ASK recall on questions + chain_questions ≥ 90% |
| M5 | median GPU ms per turn (greedy + brake + beams + gate) ≤ 300 |

The registered verdict is PASS only if all six pass.

After the registered run, report only: v4.1 on the 235b panel (scripts/claude_smolear257_on235b.py → the sealed 235b
scorer, table v2, 235b's own arm-B predictions and tau 9.3), next to v3's A 54/110 (5 wrong), A_brake 81/110 (20 wrong)
and ASK 32/40. It is never used for tuning.

## Predictions (also in the ledger)
Calibration from 235b: the gated dev recall (51%) matched the panel (49%), but the panel's wrong-save rate was about
twice the dev rate.
- P257.1 M1 passes (0–1 no_save saves), ~75%.
- P257.2 M2: 2–4 wrong saves; pass (≤ 1) ~25%.
- P257.3 M3: A recall 65–80%, FAIL ~85%. A_brake 85–95%. B 10–25%.
- P257.4 M3b: UNSURE 10–20% of gold TEACH; pass (≤ 12%) ~35%.
- P257.5 M4: ASK recall 85–95%; pass (≥ 90%) ~55%.
- P257.6 M5 passes (GPU median 120–200 ms), ~97%.
- P257.7 Overall registered PASS ~5%. Data v4.1 should cut the confident errors and raise recall a lot versus 235b, but
  the fixed gate still trades too much recall for safety to reach 85%.
