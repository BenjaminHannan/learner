# Astra: why does domain mode forget old skills, and what single change should come next? (10-10, 12:30 PM ET)

**Diagnosis only.** Do not edit files, train, run tests, or use a GPU. Read the code and the results, then answer in writing.

## Background

Domain mode lets the model teach itself a new subject from a tool and its help page. Each day it makes practice problems, tries them, and keeps the tool-checked rows. Each night it trains on those rows, with half of every batch replaying old questions answered by its pre-mode self. It undoes a night if it drifts too far, and it stops when its own quiz stops improving.

This is a small card-style experiment: T1SDR 3M parent, CPU, spreadsheets. Keep it separate from anything about the village model.

## Files to read

- Design, marks and addenda A1-A14: `domain/DESIGN-AND-MARKS-2026-10-09.md`. The latest results are in A13 and A14.
- Code:
  - `domain/mode.py`: the night is `train_night`, the gate is in the main loop, and replay comes from `build_diary` and `fresh_replay`.
  - `domain/constants.json`
  - `domain/harm.py`
- Results, each with `log.jsonl` and `analysis/RESULT.md`, under `/mnt/project-files/domain-mode/runs/`:
  - `sheet-s200-v2`: 8 nights.
  - `sheet-s200-v3`: fresh replay; every night was undone.
  - `sheet-s200-v4`: the total-drift cap kept only night 1.
- For comparison, earlier sleep screens where lr-1e-4 nights caused no harm: `creative/results/fastsleep/sleep7d/README.md`. Look for VL, SCL, SCM and the 2x2.

## What we know (shown)

| run | nights kept | sealed near (spreadsheets) | old-skills in_dist drop | families that fired | agreement with pre-mode self |
|---|---|---|---|---|---|
| v2 | 8 | 2.1 -> 69.1 (+67) | 4.19 | cipher_map, fewshot_number_rule, list_stats, passage_qa, rule_apply, seq_next, verify_claim | 100 -> 90.8 |
| v3 (fresh replay) | 0 | no change | 0 | none (nothing kept) | night 1 alone: 96.3 |
| v4 (cap at 3 points total) | 1 | 2.1 -> 26.9 (+25) | 1.47 | rule_apply, seq_next | 97.3 |

- One night at lr 1e-4 already makes rule_apply and seq_next fire. That night had 721 new rows, each seen 16 times, in 361 updates of batch 64, half of each batch replay.
- Fresh replay drifted more than replay from a fixed 4,096-question diary: 3.71 against 2.73 on the same night-1 rows.
- AdamW weight decay is ruled out: shrinking the weights as 2,900 updates would leaves agreement at 99.6.
- The pass bar for keeping old skills is an in_dist drop of 1.5 or less, with no family dropping more than 5 with its 95% interval below 0. Learning needs +30 on sealed near questions.

## Questions

1. What most likely causes the old-skill damage? Label each claim shown, suggested or untested. Candidates we have thought of:
   - Replay targets are the model's own greedy answers, so they push back only after drift.
   - Interference between number-list spreadsheet prompts and number-sequence families.
   - Too many visits per new row.
   - Something in the night code.
   Check the code for bugs that would explain it.
2. Why might the earlier sleep screens show no harm at lr 1e-4 when this does?
3. Propose **one** next change, the same for every subject (no per-domain settings) and done by the model or a fixed rule. Give pass marks fixed in advance for seed 200: DM1 at least +30, and the DM3 harm measure passing. Name the result that would prove the change wrong. Rank up to three alternatives, but recommend one.
4. Write a plain-language summary for Ben, a high-school senior, in five sentences or fewer.
