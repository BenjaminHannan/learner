# Exp 235b: write gate on the unchanged 235 v3 ear. Result: registered FAIL (M2, M3, M3b, M4)

**Result.** The gate did what a gate can do: it cut wrong saves from 20 to 5 and no_save saves from 6 to 0. But it
also threw away a third of the correct saves (recall fell from 73.6 % to 49.1 %), it still let through 5 wrong saves
(the bar is 1), and ASK recall was 80 % (the bar is 90 %). Passes: M1 (0 no_save saves) and M5 (GPU median 134 ms).
Fails: M2, M3, M3b and M4. Every one of the 5 wrong saves that got through had **no valid competing reading in the
top 4 beams** (margin = infinity). A margin gate cannot catch an error the model is sure about.

Checkpoint sha256 2852a5c0…8f8 (unchanged; hash-checked at load). τ = 11.8 (sealed; fallback rule, see
Deviations). Panel: artifacts/claude-earpanel235b-20260922/panel.jsonl (sha a15a6b3a…), opened once after the seal
and ledger, run once, scored once with the sealed scorer. Seal re-checked after scoring: 21/21 files OK.

## Marks (panel: 150 items, 110 gold TEACH frames in the statement families, 40 gold ASK frames)

| mark | bar | A (ear+brake+gate) | A_brake (= 235 arm) | A_raw | B (138i+228) | A verdict |
|---|---|---|---|---|---|---|
| M1 no_save saves | ≤ 1 | 0 | 6 | 7 | 0 | PASS |
| M2 wrong saves (4 statement fams + no_save) | ≤ 1 | 5 | 20 | 27 | 1 | FAIL |
| M3 exact TEACH recall | ≥ 85 % and ≥ B+30 | 54/110 = 49.1 % | 81/110 = 73.6 % | 87/110 = 79.1 % | 16/110 = 14.5 % | FAIL (the +30 part passes: +34.6) |
| M3b UNSURE / gold TEACH | ≤ 12 % | 36/110 = 32.7 % | – | – | – | FAIL |
| M4 exact ASK recall | ≥ 90 % | 32/40 = 80.0 % | 32/40 | 35/40 = 87.5 % | – | FAIL |
| M5 GPU median ms (greedy+brake+beams+gate) | ≤ 300 | 134.3 (p90 267.0, max 530.5; 77/150 turns beamed) | | | | PASS |
| Mac CPU speed (no bar) | – | 12-turn pilot only: median 2315 ms, p90 4721, max 5082 (1 thread) | | | | reported |

Other A counts: stray TEACH frames on question turns 0; GUARD_Q blocks on statement families 0; on no_save,
1 UNSURE and 5 guard blocks (these were 6 wrong saves in A_brake).

## Per family, arm A (hit/gold, wrong saves, UNSURE)

| family | TEACH hit/gold | wrong | UNSURE | ASK hit/gold |
|---|---|---|---|---|
| plain_teach | 16/26 | 0 | 7 | – |
| varied_teach | 17/46 | 1 | 20 | – |
| full_names | 11/22 | 3 | 4 | – |
| corrections | 10/16 | 1 | 5 | – |
| questions | – | 0 saved | – | 21/25 |
| chain_questions | – | 0 saved | – | 11/15 |
| no_save | 0 saved | 0 | 1 (+5 guard) | – |

## Per risk tag (TEACH hit/gold, wrong, UNSURE)

| tag | A_raw | A_brake | A | B |
|---|---|---|---|---|
| R1 pronouns, statement items (12 items) | 24/28, 3 wrong | 24/28, 2 wrong | 15/28, 1 wrong, 10 UNSURE | 0/28, 0 |
| R2 question-shaped statements (4 items) | 3/4, 0 | 3/4, 0 | 2/4, 0, 1 UNSURE | 0/4, 0 |
| R2 no_save questions-as-statements (12 items) | 7 wrong saves | 6 wrong saves | 0 saved (1 UNSURE, 5 guard) | 0 |
| R3 verb decides the relation (10 items) | 3/10, 7 wrong | 3/10, 7 wrong | 2/10, 2 wrong, 6 UNSURE | 0/10, 0 |

## Where the misses are (categories only; no items quoted)

- **5 wrong saves in A.** 2 are R3 cases where "teaching at" a place was saved as a *school* relation instead of
  employer/workplace. 1 is a compound family relation shortened to a plain sibling relation. 1 is an R1 pronoun
  fact attached to the wrong person. 1 is an invented extra frame in a correction turn. All 5 had margin = infinity:
  every other top-4 beam was the same reading or failed the brake.
- **8 ASK misses in A (32/40).** 3 are brake drops, because the question's relation is not in relation table v1
  (the same table gaps also cost several TEACH saves: e.g. roommate-, instrument- and food-type relations). 3 are
  two-hop questions where the model named the first hop with a family word, not the gold canonical relation. The
  sealed loader gives hop 1 no aliases (the director's chain fix puts aliases on the last hop only). 1 is a
  verb-decides-relation question (school vs workplace). 1 is a question read as NONE.
- **36 UNSURE.** The gate at τ = 11.8 is very strict. Most correct saves of varied and pronoun sentences have a valid
  rival reading within 11.8 nats, so they are held back.

## Every move

1. Built the new beam search (batch-4 CUDA-graph beams + an eager CPU path), the gate, and the inference driver
   (claude_smolear235b_beam.py, _infer.py).
2. Built my own dev set (claude_smolear235b_devdata.py): 900 base rows from the 235 dev split plus my own risk families
   (R1 90, R2 70 no-save + R2s 20 statements, R3 60), 1,140 rows. The 235b panel was not opened.
3. Ran the ear + beams on dev on the GPU, then swept τ from 0 to 15 (claude_smolear235b_tau.py). The first sweep showed
   two bugs (below), fixed before the seal. After the fix, no τ reached ≤ 1 % wrong saves on dev (the floor was 1.7 %).
   So a fallback rule, written before the seal, picked the τ with the lowest wrong rate: τ = 11.8. Dev at τ = 11.8:
   338/669 hits, 15 wrong, 301 UNSURE, 44 guard (A_brake: 611/669, 87 wrong).
4. Wrote the strict panel loader with the SCHEMA-MISMATCH check (exit 3, confirmed on a broken fixture) and the chain fix
   built in (claude_smolear235b_panel.py), the scorer (_score.py) and the arm B wrapper (_armb.py). Piloted everything on a
   fixture made from dev and train rows. CPU pilot on 12 dev turns: CPU and GPU greedy text agreed 12/12.
5. Wrote PASSMARKS.md with the predictions, sealed 21 files (SEAL.sha256.txt), and appended ledger lines P235b.1–7.
6. Checked uptime and nvidia-smi, opened the panel, ran A once on the BensPC GPU (the checkpoint was on BensPC; the
   scripts were copied there with scp). Ran B once on the Mac. Scored once. Checked the seal again: all OK.

## Deviations

- **Pre-seal gate fixes** (dev only, before the seal): (1) a duplicate-text bug let a lower beam log-prob overwrite
  the greedy reading's own score; now a duplicate uses the best log-prob. (2) Garbage beams that the brake would drop
  were counting as competitors; now only readings that pass the brake (and NONE) compete.
- **Fallback τ rule.** The brief's rule (the most recall at ≤ 1 % wrong) had no solution on dev. The fallback (lowest
  wrong rate, ties to the smallest τ) was added and sealed before the panel was opened.
- **Beams are skipped** when the brake keeps no TEACH frame, or when the turn ends in "?". Neither case has anything
  for the margin gate to decide. This is sealed and it is part of the timed path.
- **Checkpoint streamed over ssh stdin** for Mac runs (no disk copy); the hash is checked in memory. The GPU run used the
  file on BensPC.
- **Mac CPU timing on the panel was NOT run.** Mac free disk was 7.1 GB, below the 8 GB floor, because of system swap
  growth (my files are under 20 MB). A 1.4 GB fp32 model on CPU would have pushed swap further. The CPU number
  above is the 12-turn dev pilot (same code, same checkpoint), not the panel. Disk had also dipped to about 7.4 GB
  during that pilot.
- The uv command needed `--with tokenizers --with safetensors` in addition to torch/numpy.
- Pilot fixture chain rows came from train.jsonl (dev had only 4 chain rows). This was a pilot only, not scored.
- M2 counts no_save wrong saves, the same as in 235 (as sealed in PASSMARKS).

## Ledger outcome vs predictions

P235b.1 right (0). P235b.2 wrong (5 is above the 1–4 range; the FAIL was the lean). P235b.3 A right (49.1 % in 40–60), A_brake
wrong (73.6 %, below 85–95). P235b.4 right (32.7 %). P235b.5 wrong (80 %). P235b.6 right (134 ms). P235b.7 FAIL, as leaned.

## What it means

- A "confidence margin" gate on this ear trades a lot of good saves for a few bad ones. It removed 15 of 20 wrong saves
  and all 6 no_save saves, but it also held back 27 correct saves.
- The wrong saves that are left are **confident** mistakes: the model does not even consider the right reading in its
  top 4. No threshold can fix that. It needs better training data (R3 verbs, compound relations, pronouns) or a
  different check.
- The question guard works: every statement-shaped question on the no_save list was blocked, and no real statement was
  blocked by it.
- This panel is harder than the 235 panel for the same ear (without the gate, 73.6 % recall and 20 wrong saves here, vs
  94.6 % and 3 wrong there). About a third of the ASK misses come from relation table v1 not listing some everyday
  relations. The other third come from strict first-hop naming in two-hop gold.
- It is fast enough: 134 ms median on the GPU, including the beams.

## What it doesn't mean

- It does not show the ear is useless. Without the gate it still gets 5 times the recall of the 138i rule reader
  (73.6 % vs 14.5 %).
- It does not show that gates never work. It shows that *this* gate (a log-prob margin over the top 4 beams) can't
  see confident errors.
- The CPU speed is from 12 dev turns, not the panel. Treat it as rough.
- One panel of 150 items. Small counts: one or two items move a mark.
