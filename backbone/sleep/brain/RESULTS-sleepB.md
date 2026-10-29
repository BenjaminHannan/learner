# Sleep-B results (2026-10-24, Qwen/Qwen3.5-2B; preregs `PREREG-sleepB.md` and `PREREG-sleepB-addendum1.md`)

World: Week-1 (`data/week1.json`, seed 1). 982 diary turns over 7 days. 120 base facts: 40 seen on 1 day (C1), 40 on 2 days (C2), 40 on 4 days (C4).
Also 20 facts that change mid-week and 12 routines. Each score comes from one run. Results were read from the Vast instance labels
(`backbone/label_report.py`), because the log and copy services on Vast failed. Boxes: 57467248 ran stage 1 and stage 2;
57479670 ran addendum 1, after 57473371 crashed (likely out of memory) and 57477625 never left "loading". Scores are percent correct. "pool" is forward, reverse,
two-hop, changed and routine questions together. "int" is the integration score: the mean of two-hop, routine and changed-new.

## Weights only (no diary)
| arm | C4 | C2 | C1 | two-hop | changed new / stale | routine | int | pool | ARC-Easy |
|---|---|---|---|---|---|---|---|---|---|
| A0 base | 0 | 0 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | 89.6 |
| AB brain sleep | **67.5** | **52.5** | 0 | 11.1 | 70 / 15 | 66.7 | 49 | 39.8 | 89.6 |
| AF flat sleep, same steps | 45 | 30 | 15 | 0 | 75 / 0 | 58.3 | 44 | 26.1 | 90.6 |
| ab_norem | 85 | 48 | 0 | 4 | 65 | 67 | 45 | 42 | - |
| ab_noshy | 82 | 42 | 0 | 4 | 60 | 75 | 46 | 41 | - |
| ab_flatprio | 82 | 32 | 0 | 15 | 65 | 67 | 49 | 39 | - |
| ab_all (Ben's rule off) | 85 | 55 | 40 | 4 | 65 | 75 | 48 | 53 | - |
| ab_ob (open-book rehearsal) | 80 | 40 | 0 | 11 | 70 | 75 | 52 | 38 | not read |
| ab_klctx (KL on diary prompts) | 75 | 42 | 0 | 22 | 60 | 67 | 50 | 38 | not read |

Stage-2 and addendum numbers are rounded integers from the instance labels. The labels do not carry ARC, so ARC for those arms
needs the result JSONs (`result_<arm>.json`, `arc_easy`).

## With diary search (BM25 top-8 user turns)
| arm | C4 | C2 | C1 | two-hop | changed new | routine | int | pool |
|---|---|---|---|---|---|---|---|---|
| AD base + diary | 100 | 92 | 80 | 7.4 | 100 | 100 | 69 | **84.6** |
| AB | 82 | 80 | 55 | 4 | 75 | 83 | 54 | 65.9 |
| AF | 35 | 35 | 15 | 4 | 40 | 75 | 40 | 32.1 |
| ab_norem | 92 | 85 | 55 | 11 | 75 | 75 | 54 | 71 |
| ab_noshy | 68 | 52 | 10 | 4 | 40 | 92 | 45 | 40 |
| ab_flatprio | 98 | 82 | 72 | 11 | 75 | 100 | 62 | 76 |
| ab_all | 90 | 92 | 75 | 11 | 80 | 92 | 61 | 77 |
| ab_ob | 100 | 98 | 80 | 11 | 95 | 100 | 69 | **85** |
| ab_klctx | 100 | 90 | 78 | 7 | 100 | 100 | 69 | 83 |
| router R (ab_ob adapter) | | | | | | | 62 | 60 |
| router R (ab_klctx adapter) | | | | | | | 60 | 57 |

## Verdicts (marks fixed before the runs)
- P1 FAIL. AB C4 is 67.5, short of 70. C2 is 52.5 and passes its mark of 50. The four stage-2 runs reached 82-85 on C4, so 67.5 may be a low draw. This is a guess from one seed.
- P2 FAIL. Integration is +4.9 over AF, short of +10. Recall on C2+C4 is 60 against AF's 37.5, which passes its part.
- P3 PASS. ARC is 89.6, equal to base.
- P4 FAIL, and its wrong-if fires. AB with the diary scores 65.9, against 84.6 for AD. Two-hop with the diary is 4 against 7.4.
- P5 PASS. Changed-new is 70 and stale is 15.
- Wrong-if on integration (AB <= AF) does not fire: 49 vs 44.
- Q1 FAIL. The better fix arm is ab_ob, which scores 85 with the diary; ab_klctx scores 83. Both are short of 89.6. Both repair note-reading, from 65.9 up to the level of AD.
- Q2 recall part PASS. ab_ob C2+C4 is 60, above the mark of 55. The ARC part has not been read.
- Q3 FAIL. The router scores 60 pooled.
- The addendum wrong-if does not fire. ab_ob scores 85 and ab_klctx 83, both above AB + diary + 5 = 70.9.

## Plain reading
- Brain-like sleep moves recurring facts into the weights better than flat sleep at equal steps. C2 and C4 average 60 against 37.5.
- It keeps one-day facts out, so C1 stays at 0, which is what Ben's rule asks. General knowledge does not move.
- Closed-book rehearsal hurts reading of the diary: 66 vs 85 for the plain model, and 32 for flat sleep (shown). Our guess is that the model learns to answer from memory and skip the context (suggested).
- Both fixes repair this. With the KL leash on diary-format prompts, the diary score is 83 and C4 from memory is 75 (shown, one seed).
- Open-book rehearsal also fixes it. Half the practice questions come with the diary pages. The diary score is back to 85, and 80% of C4 is still known from memory (shown, one seed).
- Removing downscaling hurt note-reading the most: 40 vs 66 with the diary (shown, one seed). Switching Ben's rule off scored best overall, 53 from memory and 77 with the diary. But it also trains on more items, so it gets more steps, and the comparison is not at equal compute.
- Two-hop stays at 0-22 in every arm and mode. The highest, 22, is ab_klctx from memory alone, about 6 of 27 questions. Sleep does not make facts chain.
- The "memory when sure" router scores 60, below diary search alone at 85. A confidence of 0.5 or more on the first token does not mean the answer is right.

## Cost
GPU (Vast A100s): about $2.70 of the $3 cap for stage 1 and addendum 1, and about $1.61 of a $2 cap for addendum 2 (estimated from run times). All boxes are destroyed. Writing the chat week with the Claude API: $1.85.

## Addendum 2: sleep that changes the whole model (prereg `PREREG-sleepB-addendum2.md`, seed 1, AB stage-1 schedule)
Boxes:
- 57521298 (A100 40GB) ran the control.
- 57522280 (A100 80GB) ran ab_ob_full. The first try, 57521297, crashed at startup: a CPU-model self-check is refused by the GPU's Triton kernels.
- ab_ob_merge hit the same crash on 57521298 after the control finished. It is deferred to the next budget.

Scores come from the instance labels.

| arm (seed 1) | C4 | C2 | C1 | recall (C2+C4) | two-hop | changed new | routine | int | pool | + diary pool | ARC-Easy (500) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob control | 80 | 32 | 0 | 56 | 4 | 70 | 67 | 47 | 37 | 82 | 92.4 |
| ab_ob_full (every matrix full-rank, lr 2e-5) | 75 | 40 | 0 | 57.5 | 0 | 40 | 58 | 33 | 33 | 47 | **82.2** |
| (ab_ob seed 0, addendum 1) | 80 | 40 | 0 | 60 | 11 | 70 | 75 | 52 | 38 | 85 | not read |

The full arm's diary scores were C4 85, C2 55, C1 2, two-hop 7, changed 40 and routine 75. The router scored 56 for it and 54 for the control.

Verdicts:
- F1 FAIL: recall is 57.5, against a mark of control + 10 = 66.
- F2 FAIL: diary pooled is 47, against a mark of 77.
- F3 FAIL: ARC is 82.2, against a mark of 87.6.
- F4 PASS: C1 is 0.
- **Wrong-if fires:** ARC 82.2 is below 84.6. The other wrong-if needs the full arm to be no better on both recall and integration. It does not fire, because recall is 57.5 against 56, although integration is 33 against 47.
- Seed spread on recall is |56 - 60| = 4, under 10, so these results count as shown.
- M1-M4 (merge) were not run.

Plain reading:
- Changing every weight at lr 2e-5, with the same steps, the same KL guard and the same morning gate, did not put more facts into memory (57.5 vs 56).
- It cost general knowledge (82.2 vs 92.4 for the control and 89.6 for base), diary reading (47 vs 82) and updates (changed-new 40 vs 70) (shown, one seed).
- The 100-item ARC validation gate did not stop this drift. Whether nights were reverted needs the result JSON, which is not recovered.
- Suggested reasons:
  - The full-rank change has far more room to drift in directions the generic-prompt KL guard never probes.
  - lr 2e-5 over 1,596 steps may be too large a step.
- A smaller step size is untested.

## Checks
- Softmax Cancellation (arXiv 2610.31642) checked 2026-10-24, PR #109: reachable at night start but negligible (2e-7 of the update); numbers unchanged. The KL guard is in `Trainer.step`, and so is the ab_klctx leash, which uses the same code. When the add-on (or the delta) is fresh, cur == ref and the KL gives a spurious gradient of about 6.6e-7. That is swamped by the CE gradient of 0.14-0.66. For future runs, the drop-in fix is `fixed_kl(cur, ref, reduction="sum")/n` from `backbone/think/xent.py`.

## Addendum 3: gentler every-weight step, and targeted plasticity (prereg `PREREG-sleepB-addendum3.md`, seed 1)
Boxes: 57543171 (ab_ob_local) and 57543172 (ab_ob_full_s), both A100 80GB. Each was destroyed when its result reached its label. Spend was about $1.80 of a $2.50 cap.

| arm (seed 1) | C4 | C2 | C1 | recall | two-hop | changed new | routine | int | pool | + diary pool | router | ARC-Easy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob control (add-on) | 80 | 32 | 0 | 56 | 4 | 70 | 67 | 47 | 37 | 82 | 54 | 92.4 |
| ab_ob_full, every weight, lr 2e-5 | 75 | 40 | 0 | 57.5 | 0 | 40 | 58 | 33 | 33 | 47 | 56 | 82.2 |
| **ab_ob_full_s, every weight, lr 5e-6** | 82 | 45 | 0 | **63.5** | 0 | 65 | 67 | 44 | **41** | 81 | **64** | 92.4 |
| **ab_ob_local, tagged top-K (K = LoRA size), lr 2e-5** | 72 | 35 | 0 | 53.5 | 7 | 45 | 67 | 40 | 34 | 82 | 56 | **92.0** |

Verdicts:
- ab_ob_local:
  - L1 PASS: ARC is 92.0, against a mark of 87.6, and diary is 82, against 77.
  - L2 FAIL: recall is 53.5, against a mark of 61.
  - L3 PASS: ARC is 92.0, against ab_ob_full's 82.2 + 5.
  - Neither wrong-if fires.
- ab_ob_full_s:
  - S1 PASS: ARC is 92.4 and diary is 81.
  - S2 PASS: recall is 63.5, against a mark of 61. That is +7.5 over the same-seed control, which clears the 4-point seed-spread rule. But it is only +3.5 over seed-0 ab_ob (60), so the gain is small (suggested).

Plain reading (one seed):
- Changing every weight is safe when the step is small. At lr 5e-6, general knowledge and note-reading match the add-on, and recall is a little higher. At lr 2e-5 they broke.
- Restricting each night's change to the most-tagged 1.2% of weights fully protects general knowledge and note-reading, even at the harmful lr 2e-5 (shown). It stored slightly fewer facts (53.5 vs 56) and fewer updates (changed-new 45 vs 70).
- Untested:
  - Targeted plasticity at the small step.
  - A larger K.
  - Tagging that also counts the update items.
- Per-night tag locations (which layers and module types hold the tagged weights) are in the result JSON, which was not recovered (labels only).

## Addenda 4 and 5: choices made after sealing, before any run (2026-10-24 19:10Z)
- ab_ob_twist: a scene is also dropped if it names an older value of the fact (`twist_dropped_stale`), so a dream never restates a stale fact. The research note `research/sleep-arm-designs-2026-10-24.md` flagged this risk.
- ab_ob_twist: the arm adds 2 extra texts per item, so it changes both "twisted" and "more texts". A T2 pass is labelled suggested until an equal-count plain-paraphrase control is run.
- ab_ob_ther: 2x priority times 0.5 loss weight keeps each salient item's expected push the same. H2 therefore tests spreading the push over more steps, and a null result is likely (suggested, from the same note).
- ab_ob_rot: the quarters are layers [0,6), [6,12), [12,18) and [18,24) of Qwen3.5-2B's 24 layers. A strided split (layer mod 4) is a candidate for the next round.
- ab_ob_b2: the dream generation length also scales (400 x s tokens), so 8 paraphrases and 8 Q&A are not cut off. Update-detection checks and REM sampling lengths are not scaled. Read the gate-revert count before reading B1.
- The new arms record peak GPU memory (`peak_mem_gb`, `peak_mem_train_gb`). The CPU smoke showed that ab_ob and the older arms are bit-identical to before.

## Addendum 2, last arm: fold-in (ab_ob_merge), seed 1
Box 57548525 (A100 PCIE 40GB Japan) ran it in 0.89 h, about $0.34. The run moved here after three tries stalled on Ben's 16 GB PC. The watcher destroyed the box when the result reached its label.

| arm (seed 1) | C4 | C2 | C1 | recall | two-hop | changed new | routine | int | pool | + diary pool | router | ARC-Easy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob control (add-on) | 80 | 32 | 0 | 56 | 4 | 70 | 67 | 47 | 37 | 82 | 54 | 92.4 |
| ab_ob_merge (add-on folded in nightly) | 65 | 38 | 0 | 51.5 | 19 | 55 | 67 | 47 | 37 | **86** | 63 | 92.6 |

With the diary, the fold-in arm scored C4 100, C2 90, C1 80, two-hop 19, changed 95 and routine 100.

Verdicts:
- M1 FAIL: recall is 51.5, against a mark of 66.
- M2 PASS: diary is 86, against a mark of 77.
- M3 PASS: ARC is 92.6, against a mark of 87.6.
- M4 PASS: C1 is 0.

Plain reading (one seed):
- Folding each night's add-on into the model is safe. General knowledge and note-reading held.
- It did not store more facts. Recall was 51.5 against 56, a gap about the size of the seed spread.
- Two-hop from memory was 19 against 4, which is about 5 of 27 questions against 1 (suggested; a small count).
- The diary score of 86 is the best of any slept arm, and above the plain model with the diary (84.6). But it is within 4 points of the control, so it is not called shown.
- On the Mac's 4-bit model, fold-in would write into the quantized weights, so it needs the requantization test (`sleep-q4` constraint).

## Addendum 5: sleep that scales to the chip, at 2x work (ab_ob_b2, seed 1)
Box 57552969 (A100 SXM4 40GB New York) ran it in 1.29 h, about $0.76. The watcher destroyed the box when the result reached its label.

| arm (seed 1) | C4 | C2 | C1 | recall | two-hop | changed new | routine | int | pool | + diary pool | router | ARC-Easy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob control (s = 1) | 80 | 32 | 0 | 56 | 4 | 70 | 67 | 47 | 37 | 82 | 54 | 92.4 |
| **ab_ob_b2 (s = 2)** | 85 | 48 | 0 | **66.5** | 0 | 75 | 67 | 47 | **45** | 83 | 56 | 92.0 |

With the diary, ab_ob_b2 scored C4 100, C2 92, C1 70, two-hop 7, changed 90 and routine 100.

Verdicts:
- B1 PASS: recall is 66.5, against a mark of 61. That is +10.5 over the same-seed control, which clears the 4-point rule.
- B2 PASS: ARC is 92.0 (mark 87.6) and diary is 82.9 (mark 77).
- B3 PASS: integration is 47, against a mark of 43.
- The wrong-if (recall <= 56) does not fire.
- The gate-revert count is in the result JSON, which was not recovered (labels only). Recall rose, so the extra nights were clearly not all reverted.

Plain reading (one seed):
- Twice the night's work (steps, dreams per fact, items, REM chains) stored more recurring facts: 66.5 against 56. That is the best recall from memory so far, above every-weight at the small step (63.5).
- General knowledge, note-reading and updates held.
- So a faster chip, given the same hours, gives a better night, not just a shorter one (shown, one seed).
- Caution: recall rests on 80 facts. An unpaired arm-to-arm gap has a noise of about 7 points, so +10.5 is about 1.5 noise widths. A second seed or a bigger fact set should confirm it.
- Not yet split: whether the gain comes from more steps or from more varied dreams.

## Addendum 4: rotating regions, twisted dreams, guess + dopamine (seed 1); therapy queued on Ben's PC
Boxes: 57555322 (New York) ran ab_ob_twist in 0.82 h. 57555316 (Japan) ran ab_ob_rot, then ab_ob_guess. Two earlier California boxes, 57552967 and 57552968, never got going and were destroyed at 0.36 h.

| arm (seed 1) | C4 | C2 | C1 | recall | two-hop | changed new | routine | int | pool | + diary pool | router | ARC-Easy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob control | 80 | 32 | 0 | 56 | 4 | 70 | 67 | 47 | 37 | 82 | 54 | 92.4 |
| ab_ob_twist (twisted dreams) | 85 | 40 | 0 | 62.5 | 15 | 55 | 67 | 46 | 37 | 84 | 63 | **93.2** |
| ab_ob_rot (a quarter of the layers each night) | 15 | 2 | 0 | **8.5** | 0 | 0 | 8 | 3 | 5 | 85 | 57 | 90.8 |
| ab_ob_guess (guess, then dopamine boost) | 78 | 50 | 0 | **64** | 4 | 70 | 67 | 47 | 41 | 84 | 61 | 92.4 |

With the diary:
- twist: C4 100, C2 92, C1 72, two-hop 22, changed 85, routine 100.
- rot: C4 100, C2 92, C1 82, two-hop 7, changed 95, routine 100.
- guess: C4 100, C2 95, C1 82, two-hop 7, changed 80, routine 100.

Verdicts:
- ab_ob_twist:
  - T1 PASS: ARC is 93.2 and diary is 84.
  - T2 PASS: recall is 62.5, against a mark of 61. That is +6.5 over the control.
  - The wrong-if does not fire.
  - Under the rule written before the run, this stays suggested until an equal-count plain-paraphrase control is run, because the arm adds 2 texts per item. Changed-new fell from 70 to 55, which is 3 of 20 facts.
- ab_ob_rot:
  - R1 PASS: ARC is 90.8 and diary is 85.
  - R2 FAIL: recall is 8.5, against a mark of 52.
  - **The wrong-if fires** (recall < 46): training one quarter of the layers per night, with the trim applied to all layers every night, did not hold the facts.
  - Suggested reasons, to be checked in the result JSON if it can be pulled:
    - The morning gate may have reverted the later nights. Training a new quarter while the trim shrinks the older quarters could drop consolidated recall by more than 10 points, which would leave about one night's learning.
    - Or the trim (x 0.85 each night) may erase a quarter's change before that quarter trains again. Quarter 3 trains only on night 4.
- ab_ob_guess:
  - G1 PASS: ARC is 92.4 and diary is 84.
  - G2 PASS: recall is 64, against a mark of 61. That is +8 over the control.
  - The wrong-if does not fire.
- The result JSONs were not recovered. The watcher stopped box 57555316 before trying `cat`, but asked too soon, while the box was still running, and then destroyed it. The watcher now waits for the stopped state. `label_report.py` now writes each night's gate reverts (`rv=`) into the label.

Plain reading of addenda 4 and 5 (one seed each; noise for an unpaired gap on these 80 facts is about 7 points):
- Four changes raised recall from memory, each with no harm to ARC or diary reading:
  - 2x night work: 66.5.
  - Guess + dopamine: 64.
  - Every weight at a small step: 63.5.
  - Twisted dreams: 62.5.
  - The control scored 56. Each gain is 1 to 1.5 noise widths, so none is shown on its own. Four separate arms all pointing up is suggestive.
- Rotating regions broke memory (8.5).
- Next:
  - Confirm with a bigger fact set and paired per-question scoring.
  - Run the twist control (an equal count of plain paraphrases).
  - Combine the winners: 2x work + guess + twist.

## Addendum 6: Week-2, recorded before any run (2026-10-24 22:00Z)
- `data/week2.json`, sha256 `70db7146ed59d10cbd0d2e8d7a6fc0e245d4b07ec57add0c793db1fdff006e5b`, written by `week.py --seed 2 --scale 2.5 --out data/week2.json --cap 8` (commit 83674e7ce3).
- Facts: 264 in total (C1 64, C2 100, C4 100), 30 changing facts and 20 routines.
- Sessions: 91 (13 a day), with 9.4 mentions per session against 9.6 in Week-1.
- Diary: 2,086 turns, 1,043 of them from the user.
- Test questions: 656 in total.
  - forward: 264, of which 200 are C2+C4, the primary measure;
  - reverse: 264;
  - two-hop: 78;
  - changed: 30;
  - routine: 20.
- Writing: 205 attempts over 91 sessions, with 0 sessions failed and 3 strict-wording warnings. Cost $4.32 at list price.
- Arms ab_ob_win and ab_ob_winp (commit 3991980bb3). A CPU smoke showed the 19 older arms are bit-identical to before. Per-question rows are already in every new arm's result JSON (`scores.<mode>.rows`).

## Addendum 4, last arm: therapy replay (ab_ob_ther, seed 1, on Ben's PC)
This arm ran on the RTX 5070 Ti (bf16, gen-bs 32, tok budget 1024, code b537295cbe) in 2,625 s, not on an A100 like the control. GPU numerics differ a little, so treat it like a different seed. The result JSON and log are on branch `claude/sleepb-ab-ob-ther-pc-results` (commit ba79d6a95212).

| arm (seed 1) | C4 | C2 | C1 | recall | two-hop | changed new / stale | routine | int | pool | + diary pool | router | ARC-Easy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob control (A100) | 80 | 32 | 0 | 56 | 4 | 70 | 67 | 47 | 37 | 82 | 54 | 92.4 |
| ab_ob_ther (PC) | 82.5 | 30 | 0 | 56 | 7 | 55 / 15 | 67 | 43 | 38 | **73** | 56 | 92.0 |

Night by night (arc_val, morning probe recall):
- night 1: no dreams;
- night 2: 0.84, 0.91;
- night 3: 0.86, 0.74;
- night 4: 0.83, 0.48, **reverted** (arc_val below base 0.87 - 0.03);
- night 5: 0.85, 0.77;
- night 6: 0.87, 0.73;
- night 7: 0.85, 0.78.

Weighted (salient) examples per night: 88, 60, 363, 1,245, 969 and 1,476.

Verdicts:
- H1 FAIL: diary pooled is 72.9, against a mark of 77. ARC (92.0) passes.
- H2 FAIL: changed-new is 55, against a mark of 80.
- **The wrong-if fires:** changed-new is 55, below 60.
- Plain reading: more replays at half weight for important or corrected facts did not help updates (55 against 70) and lowered note-reading (73 against 82). The research note predicted no gain, because the expected push is the same. The drop in diary reading is unexplained. It may come from the PC numerics or seed-like noise (suggested).

## Addendum 6: Week-2 control (ab_ob, seed 1)
Box 57572669 (A100 SXM4 UK) ran it in 0.95 h, about $0.64 including a wasted stop wait. The watcher's API stop was accepted, but the box never left "running", so `cat` refused and the result JSON was lost. The watcher now waits for the job's own self-stop, 20 min after DONE.

| arm (Week-2, seed 1) | C4 | C2 | C1 | recall | two-hop | changed new | routine | int | pool | + diary pool | router | ARC-Easy | reverts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob control | 71 | 34 | 0 | 52.5 | 6 | 63 | 55 | 42 | 36 | 84 | 56 | 92.2 | night 4 |

## Addendum 6: 2x work (ab_ob_b2, Ben's PC) and the winners combined (ab_ob_win, Vast), Week-2, seed 1
- ab_ob_win ran on box 57572667 (A100 PCIE Japan) in about 2.1 h for about $0.79. Its result JSON was pulled after the job's own self-stop.
- ab_ob_b2 ran on the RTX 5070 Ti in 5,769 s (code 111b58a372; JSON from branch `claude/sleepb-ab-ob-b2-pc-results`).
- Both JSONs are in `results_wk2/`. Different GPUs give slightly different numerics, so the pair is treated like two seeds.

| arm (Week-2, seed 1) | C4 | C2 | recall | two-hop | changed new | routine | int | pool | + diary pool | ARC-Easy | reverts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob control (Vast, label only) | 71 | 34 | 52.5 | 6 | 63 | 55 | 42 | 36 | 84 | 92.2 | night 4 |
| ab_ob_b2, 2x work (PC) | 81 | 54 | **67.5** | 11.5 | 73.3 | 85 | 56.6 | 47.7 | 85.1 | 93.0 | none |
| ab_ob_win, 2x work + guess + twist (Vast) | 85 | 53 | **69.0** | 7.7 | 60.0 | 85 | 51 | 48 | 84.5 | 92.6 | none |

Paired, `paired.py`, on 200 C2+C4 forward questions:
- ab_ob_win vs ab_ob_b2: +1.5 (win right only: 19; b2 right only: 16; the arms disagree on 17.5% of questions), exact McNemar p = 0.74.

Verdicts so far:
- **W2 FAIL:** combining guess + dopamine and twisted dreams with 2x work adds +1.5, against a mark of +4 (p = 0.74). The guess and twist gains seen on Week-1 (+8 and +6.5, one seed each, 80 facts) do not add on top of 2x work. They may have been noise, or they may overlap with what 2x work already gives (suggested).
- **W1 pending:** b2 is 67.5 against the Vast control's 52.5, which is +15 unpaired. The paired test waits for the control's rerun on the PC, because the Vast control's JSON was lost. With 200 questions and about 17% disagreement between arms, +15 would be far beyond noise (suggested until paired).
- No harm: ARC (93.0 and 92.6) and diary (85.1 and 84.5) both pass.
- W3 (twist vs plain extra texts) waits for ab_ob_winp on the PC.

## Addendum 6: the winners with plain extra texts (ab_ob_winp, Ben's PC), Week-2, seed 1
Ran on the RTX 5070 Ti in 6,286 s (code 111b58a372, gen-bs 32, no reverts). The JSON (`results_wk2/result_ab_ob_winp.json`, sha256 starts 6e61d3bd) came from branch `claude/sleepb-ab-ob-winp-pc-results`.

| arm (Week-2, seed 1) | C4 | C2 | recall | reverse C2+C4 | two-hop | changed new | routine | int | + diary pool | ARC-Easy |
|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob_b2, 2x work | 81 | 54 | 67.5 | 64.5 | 11.5 | 73.3 | 85 | 56.6 | 85.1 | 93.0 |
| ab_ob_win, + guess + twisted scenes | 85 | 53 | 69.0 | 68.0 | 7.7 | 60.0 | 85 | 50.9 | 84.5 | 92.6 |
| ab_ob_winp, + guess + plain paraphrases | 82 | 55 | 68.5 | 66.5 | 6.4 | 73.3 | 85 | 54.9 | 85.8 | 92.2 |

Paired on 200 C2+C4 forward questions:
- winp vs b2: +1.0 (19 vs 17 right-only questions), p = 0.87.
- win vs winp: +0.5 (16 vs 15), p = 1.0.
- Secondary measures, paired: reverse, win vs b2 +3.5 (p = 0.31). Two-hop, win vs b2 −3.8 (p = 0.55). Changed-new, win vs b2 −13.3 (5 vs 1 of 30, p = 0.22). None is significant.

Verdicts:
- **W3 FAIL:** the twist itself adds +0.5 over plain extra texts, against a mark of +4 (p = 1.0). Twisted dreams are no better than ordinary extra paraphrases on Week-2 (shown for this world and seed, since the pair is close to identical).
- No harm: ARC 92.2, diary 85.8, both pass.
- W1 still waits for the control rerun (box 57595799, RTX 3090, started 02:07Z).

What limits memory now (diagnostics of the b2 run; suggested, one seed):
- **Daytime notes miss facts.** The tagger finds 53% of fact mentions. By the end of the week, 71 of 100 C2 facts and 83 of 100 C4 facts were eligible. Recall among eligible facts is already high: C4 81 of 83, C2 54 of 71. So the eligibility ceiling for C2+C4 is about 77%, and b2 reaches 67.5. In the raw samples the tagger often lists a fact about Sam ("Sam takes home 3200", "Sam loves it"), which the validity filter drops, and skips the fact about two named people in the same message ("Krenam's place is in Labozon").
- **Two-step dreams almost never survive.** Of 60 chain dreams a cycle, about 95% fail the format check (the question must name one end, the answer must be the other end, and the shared middle name must stay hidden). Over the week only 20 chain pairs were kept, covering 10 of the 78 two-hop questions. Two-hop questions whose chain was dreamed were 90% right, and the rest were 0% right.
- More work can mostly help the 17 eligible but unlearned C2 facts. Those came up late in the week.

## Addendum 6: the control rerun and the paired W1 test (final)
Two cheap RTX 3090 hosts never started (about $0.09). The rerun then ran on box 57599726 (RTX 5090 Slovakia, $0.489/h) in 1,373 s, about $0.25 including the 2-minute linger. It used the same sleepb.py as the other addendum-6 arms (worktree at b1ce3ed322, before the PR #114 merge). Its JSON is `results_wk2/result_ab_ob.json`.

| arm (Week-2, seed 1) | C4 | C2 | recall | reverse C2+C4 | two-hop | changed new | routine | + diary pool | ARC-Easy | reverts |
|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob control, rerun (5090) | 70 | 36 | **53.0** | 50.5 | 2.6 | 53.3 | 80 | 82 | 93.6 | none |
| ab_ob control, first run (A100, label only) | 71 | 34 | 52.5 | | 6 | 63 | 55 | 84 | 92.2 | night 4 |
| ab_ob_b2, 2x work (PC) | 81 | 54 | **67.5** | 64.5 | 11.5 | 73.3 | 85 | 85.1 | 93.0 | none |

The two control runs agree on recall (53.0 and 52.5).

Paired b2 vs control:

| measure | questions | control | b2 | b2 − control | right only in control / only in b2 | p |
|---|---|---|---|---|---|---|
| recall C2+C4 (primary) | 200 | 53.0 | 67.5 | **+14.5** | 19 / 48 | **0.0005** |
| reverse C2+C4 | 200 | 50.5 | 64.5 | +14.0 | 18 / 46 | 0.0006 |
| changed-new | 30 | 53.3 | 73.3 | +20.0 | 0 / 6 | 0.031 |
| two-hop | 78 | 2.6 | 11.5 | +9.0 | 2 / 9 | 0.065 |
| routine | 20 | 80 | 85 | +5.0 | 2 / 3 | 1.0 |

The winners arms also beat the control by about as much: winp +15.5 (p < 0.001).

Final addendum-6 verdicts:
- **W1 SHOWN:** twice the night's work raises recall from weights by +14.5 points on Week-2 (p = 0.0005), and the gain from addendum 5 replicates on a new world. Reverse questions and updated facts gain by about as much.
- **W2 FAIL** (+1.5, p = 0.74) and **W3 FAIL** (+0.5, p = 1.0): guess + dopamine and twisted dreams add nothing on top of 2x work.
- **No wrong-if fired.** No harm in any arm: ARC 92.2 to 93.6, and diary within 3 points of the control.
- Cost: addendum 6 Vast spend was about $2.10, plus $4.32 of API to write Week-2. b2 and winp ran free on Ben's PC.

## Addendum 7: 4x work, sharper daytime notes, guided two-step dreams (Week-2, seed 1), first three arms
Code 224e79fa28 (PR #114 trainer + arms commit 3ef9356433), tok 2048, linger 120. JSONs are in `results_a7/`. The b2 rerun is the reference.

| arm | GPU | wall | about $ | C4 | C2 | recall | two-hop (dreamed) | changed new | routine | tagger recall | eligible C2 / C4 | + diary pool | ARC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob_b2 rerun (reference) | 5090 | 1,915 s | 0.32 | 81 | 53 | **67.0** | 11.5 (10) | 66.7 | 80 | 0.533 | 72 / 87 | 83.8 | 93.2 |
| ab_ob_b4, 4x work | 5090 | 3,703 s | 0.56 | 86 | 66 | **76.0** | 5.1 (6) | 70.0 | 80 | 0.533 | 72 / 87 | 83.1 | 92.4 |
| ab_ob_tag2, new tagging prompt | 5090 | 1,877 s | 0.36 | 63 | 38 | **50.5** | 5.1 (4) | 23.3 | 15 | 0.251 | 48 / 58 | 81.4 | 93.0 |

Paired tests (exact McNemar):
- **Noise floor:** the b2 rerun vs addendum 6's b2 gives −0.5 (21 vs 20 right-only questions, 20.5% disagreement), p = 1.0. Two-hop gives 0.0 (6 vs 6). The faster trainer and a different GPU reproduce b2, and two identical-settings runs do not produce a false "difference".
- **b4 vs b2:** recall +9.0 (6 vs 24), **p = 0.0014**. Two-hop −6.4 (6 vs 1), p = 0.125.
- **tag2 vs b2:** recall −16.5 (54 vs 21), p = 0.0002. Two-hop −6.4, p = 0.18.

Verdicts:
- **D1 SHOWN:** 4x work beats 2x work by +9.0 points (p = 0.0014), with no harm (ARC 92.4, diary 83.1).
- **The wrong-if fired, and the prediction failed.** I predicted that 4x work would add less than +4, because recall was near the note-taking ceiling. It added +9, so that reading was wrong about how much room was left. The eligibility ceiling itself still holds. With 72 C2 and 87 C4 facts eligible, the most recall can reach is 79.5, and b4 reaches 76. The next gains have to come from catching more facts during the day (suggested).
- **T1 FAIL (the mechanism failed):** the new prompt halved the tagger's mention recall, from 0.533 to 0.251 (precision rose to 0.82). In the raw samples, the small model still answers with "Sam ..." triples, now even for two-name facts ("Sam born in Bodetreth"), and lists fewer facts overall. Naming "Sam" in the instructions seems to make it more salient, not less (suggested). Routines, which are about Sam, collapsed (80 → 15).
- **T2 FAIL, with harm:** recall −16.5 (p = 0.0002). Because T1 failed, this arm does not test whether better notes become memories.
- ab_ob_bridge is still running (RTX 4090, Brazil).

## Addendum 7, last arm: guided two-step dreams (ab_ob_bridge), and the round's verdicts
Box 57604382 (RTX 4090 Brazil, $0.377/h with storage) took 1.95 h, about 3.6x as long as the 5090 runs, for about $0.80. Its result JSON could not be pulled, because Vast's command service answered "not ready" four times after the self-stop, and the watcher then destroyed the box. The numbers below come from its label, so the bridge comparisons are unpaired and at most **suggested**. The watcher now keeps a stopped box when a pull fails.

| arm | C4 | C2 | recall | two-hop | changed new | routine | int | + diary pool | ARC | reverts |
|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob_b2 rerun (reference) | 81 | 53 | 67.0 | 11.5 | 66.7 | 80 | 56 | 83.8 | 93.2 | none |
| ab_ob_bridge (label only) | 83 | 59 | 71.0 | 19 | 70 | 85 | 58 | 83 | 92.2 | none |

- **B1 unknown:** the label does not carry how many two-hop questions had a kept chain dream.
- **B2 FAIL (suggested):** two-hop +7.5 (19 vs 11.5), against a mark of +10. The gain points the right way, but it is unpaired and below the mark.
- **B3 PASS:** recall 71.0 vs 67.0 (no recall cost; +4 unpaired).
- No harm: ARC 92.2, diary 83.

Addendum 7 summary:
- **D1 SHOWN:** 4x work +9.0 over 2x (p = 0.0014). The "wrong if" fired: my prediction of less than +4 was wrong. Recall (76) is now 3.5 points under the eligibility ceiling (79.5).
- **T1/T2 FAIL:** the new tagging prompt halved the tagger's recall, and memory fell by 16.5 (p = 0.0002).
- **B2 FAIL (suggested):** guided two-step dreams gave +7.5 on two-hop (unpaired).
- Noise floor: identical settings on new code and a different GPU reproduce b2 (−0.5, p = 1.0).
- Cost: about $2.70 on Vast. That includes about $0.65 at list price for four boxes whose hosts never started. On a 5090 a 2x-work run took 32 min, about $0.32.

## Addendum 8: re-read the day for names, guided two-step dreams at 4x, and a second seed (Week-2)
Code 8a3da916f3 for the two new arms; the seed-2 runs used 15b3c7a2d2-era code (the same sleepb.py as addendum 7). All runs used RTX 5090 boxes. The reference is addendum 7's ab_ob_b4 (seed 1, `results_a7/`). The JSONs are in `results_a8/`. The prereg header gives ~06:20Z as its time; it was in fact committed at about 05:58Z (commit 9382c0ede6), which is before any addendum-8 code or run.

| arm | seed | wall | C4 | C2 | recall | reverse | two-hop (dreamed) | changed new | routine | tagger recall / precision | eligible C2 / C4 | + diary pool | ARC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob_b4 (reference) | 1 | 3,703 s | 86 | 66 | 76.0 | 73.0 | 5.1 (6) | 70.0 | 80 | 0.533 / 0.691 | 72 / 87 | 83.1 | 92.4 |
| **ab_ob_b4_names** | 1 | 3,856 s | 95 | 81 | **88.0** | 86.5 | 1.3 (3) | **96.7** | 85 | **0.674** / 0.700 | **94 / 94** | 81.6 | 92.6 |
| **ab_ob_b4_bridge** | 1 | 4,599 s | 87 | 67 | 77.0 | | **28.2 (27)** | 70.0 | 90 | 0.533 / 0.691 | 72 / 87 | 82.2 | 93.0 |
| ab_ob_b2 | 2 | 2,189 s | | | 64.0 | | 10.3 | 70.0 | 85 | | | 84.1 | 93.2 |
| ab_ob_b4 | 2 | 3,821 s | 87 | 66 | 76.5 | | 5.1 | 70.0 | 85 | | | 82.6 | 92.6 |

Paired tests (exact McNemar):
- names vs b4:
  - recall **+12.0** (12 vs 36 right-only questions), **p = 0.0007**;
  - reverse +13.5, p = 0.0001;
  - changed-new +26.7 (0 vs 8), p = 0.008;
  - two-hop −3.8, p = 0.38;
  - routine +5, p = 1.0.
- bridge vs b4: two-hop **+23.1** (2 vs 20), **p = 0.0001**; recall +1.0, p = 0.81.
- seed 2, b4 vs b2: **+12.5** (6 vs 31), p < 0.0001.
- b4, seed 2 vs seed 1: +0.5 (11 vs 12), p = 1.0. 4x work gives the same recall on both seeds.

Names pass, summed over the week:
- 277 pairs asked; 175 yes answers, each of which became a new item;
- 0 dropped by the validity checks;
- the candidate vocabulary grew from 223 to 532 names.

Eligible items rose from 276 to 339. 94 of the eligible items do not match a true fact, against 80 for b4. These are extra or partial notes: the precision lower bound held at 0.70.

Verdicts:
- **S1 SHOWN:** 4x work beats 2x on a second seed too: +12.5, p < 0.0001.
- **N1 PASS:**
  - tagger mention recall 0.674 (mark 0.65);
  - precision lower bound 0.70 (mark 0.5);
  - eligible C2 + C4 = 188 (mark 175).
- **N2 SHOWN:** re-reading the day for names adds +12.0 recall (p = 0.0007). Recall from weights alone is now 88%, against an eligibility ceiling of 94. Facts that changed are now known in their new form 97% of the time (b4: 70%).
- **G1 PASS:** 27 of 78 two-hop questions had a kept chain dream (mark 20).
- **G2 SHOWN:** guided two-step dreams add +23.1 on two-hop (p = 0.0001).
- **G3 PASS:** recall 77.0 vs 76.0.
- No wrong-if fired. No harm in any arm: ARC 92.6 to 93.2, and diary within 1.5 points of the reference.
- Cost: about $3.50 at list price. That covers six boxes, including three that never started (about $0.17) and two whose hosts were slow to release a stopped box. `vast.py cat` now waits up to 10 minutes for the output.

What this suggests (one seed for the two new arms):
- The two fixes act on different questions. Names fixes noticing; bridge fixes two-step links. They should combine.
- The names arm has the fewest chain dreams (3), because its REM uses the old prompt.
- The next round should combine names + bridge at 4x, on two seeds.

## Addendum 9: names re-read + guided two-step dreams together, on two seeds (Week-2)
Code b7d29b1929 (arm `ab_ob_b4_nb` = the addendum-8 names pass + the bridge prompt, both unchanged, at 4x work). The seed-2 names run used 297d8b4082 (the same sleepb.py as addendum 8). All runs used RTX 5090 boxes. References: addendum 8's ab_ob_b4_names (seed 1) and ab_ob_b4 seed 2 (`results_a8/`). The JSONs are in `results_a9/`. Prereg sealed at commit 297d8b4082 before any addendum-9 code or run.

| arm | seed | wall | C4 | C2 | recall | reverse | two-hop (dreamed) | changed new | routine | tagger recall / precision | eligible C2 / C4 | + diary pool | ARC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob_b4_names (reference) | 1 | 3,856 s | 95 | 81 | 88.0 | 86.5 | 1.3 (3) | 96.7 | 85 | 0.674 / 0.700 | 94 / 94 | 81.6 | 92.6 |
| ab_ob_b4 (reference) | 2 | 3,821 s | 87 | 66 | 76.5 | 75.5 | 5.1 (8) | 70.0 | 85 | 0.533 / 0.691 | 72 / 87 | 82.6 | 92.6 |
| **ab_ob_b4_names** | 2 | 4,210 s | 94 | 85 | **89.5** | 87.5 | 2.6 (5) | 93.3 | 85 | 0.674 / 0.700 | 94 / 94 | 84.6 | 91.6 |
| **ab_ob_b4_nb** | 1 | 3,653 s | 95 | 88 | **91.5** | 85.0 | **38.5 (32)** | 96.7 | 85 | 0.674 / 0.700 | 94 / 94 | 86.4 | 92.2 |
| **ab_ob_b4_nb** | 2 | 3,764 s | 96 | 86 | **91.0** | 88.0 | **35.9 (28)** | 93.3 | 85 | 0.674 / 0.700 | 94 / 94 | 86.0 | 91.8 |

Paired tests (exact McNemar):
- names vs b4, seed 2: recall **+13.0** (11 vs 37), **p = 0.0002**; reverse +12.0, p = 0.0005.
- nb vs names, seed 1: two-hop **+37.2** (0 vs 29), **p < 0.0001** (3.7e-9); recall +3.5 (7 vs 14), p = 0.19; reverse −1.5, p = 0.71.
- nb vs names, seed 2: two-hop **+33.3** (1 vs 27), **p < 0.0001** (2.2e-7); recall +1.5 (9 vs 12), p = 0.66; reverse +0.5, p = 1.0.
- nb, seed 1 vs seed 2: recall −0.5, p = 1.0; two-hop −2.6, p = 0.84.
- Reported: nb vs bridge (seed 1, two-hop) +10.3 (8 vs 16), p = 0.15. nb vs the Week-2 control: recall 91.5 vs 53.0 (+38.5, 7 vs 84).

Verdicts:
- **R1 SHOWN:** re-reading the day for names replicates on seed 2 (+13.0, p = 0.0002; seed 1 was +12.0).
- **M1 PASS:** 32 (seed 1) and 28 (seed 2) of 78 two-hop questions had a kept chain dream (mark 20).
- **K1 SHOWN** and **K2 SHOWN:** guided two-step dreams add +37.2 and +33.3 on two-hop on top of names (both p < 0.0001).
- **K3 PASS:** recall did not drop on either seed (+3.5 and +1.5; mark >= −3).
- **Adopt:** R1, K1, K2 and K3 all pass, so ab_ob_b4_nb is the recipe carried to the next step.
- No wrong-if fired. No harm: ARC 91.6 to 92.2 (mark 87.6), diary 84.6 to 86.4 (all above their references).
- The expectation (recall 85-90, two-hop 20-35) was slightly low on both counts.
- Seeds change training order and dream sampling, not the notes: the tagger and the names pass are deterministic and gave identical items on both seeds (277 pairs asked, 175 items added). So the seed-2 runs test training noise, not note-taking noise.
- Cost: about $2.50 on Vast, including about $0.58 for a Japan box that ran about 2.5x slower than the Slovakia boxes and was replaced at 1.3 h.

What this suggests:
- From weights alone the recipe now answers 91% of C2+C4 forward questions (control 53%), against an eligibility ceiling of 94%.
- Two-hop correct stays close to the number of two-hop pairs with a kept chain dream (seed 1: 32 dreamed, 30 right; seed 2: 28 dreamed, 28 right; the per-question link is not logged yet; see `/mnt/project-files/research/sleep-gaps/two-hop-coverage-and-junk-notes.md`). The next two-hop gain should come from dreaming more of the 78 pairs (suggested, untested).
- About 28% of eligible items match no true fact. Most are half-facts with a common noun ("X owns boat"). The names pass added 16, all from two common words it took for names ("Sister", "Sail").

## Addendum 10: four tries per two-step dream (ab_ob_b4_nb_x4, Week-2, seeds 1 and 2)
Code a2e086cff4 (four samples per REM chain prompt, keep the first that passes every check, at most one kept dream per pair per cycle). RTX
5090 boxes: seed 1 on Slovakia machine 141056 (57665253, 1.46 h), seed 2 on Portugal machine 152963 (57665257, 1.56 h). References: addendum
9's ab_ob_b4_nb seeds 1 and 2 (`results_a9/`). The seed-2 JSON is in `results_a10/`. The seed-1 box finished, but its host's command API
never returned the JSON: about 16 tries over 4.5 hours, including a restart and a fresh stop, all "output not ready". The box was destroyed
at 17:00Z, so seed 1 has no per-question rows. Seed-1 numbers below come from its instance label (unpaired, at most suggested), as the
prereg's scoring rule says.

| arm | seed | wall | C4 | C2 | recall | reverse | two-hop (dreamed of 78) | chain dreams kept | changed new | routine | + diary pool | ARC | reverts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob_b4_nb (reference) | 1 | 3,653 s | 95 | 88 | 91.5 | 85.0 | 38.5 (32) | 87 | 96.7 | 85 | 86.4 | 92.2 | 0000000 |
| ab_ob_b4_nb (reference) | 2 | 3,764 s | 96 | 86 | 91.0 | 88.0 | 35.9 (28) | 85 | 93.3 | 85 | 86.0 | 91.8 | 0000000 |
| **ab_ob_b4_nb_x4** (label) | 1 | about 5,000 s | 94 | 79 | **86.5** | | **64.1** | | 96.7 | 80 | 90 | 92.2 | 1000000 |
| **ab_ob_b4_nb_x4** | 2 | 5,085 s | 95 | 78 | **86.5** | 82.0 | **60.3 (53)** | 217 | 93.3 | 85 | 86.3 | 92.0 | 1000000 |

Paired tests (exact McNemar), seed 2: two-hop **+24.4** (2 vs 21), **p = 0.0001**; recall **−4.5** (19 vs 10), p = 0.14; reverse −6.0 (24 vs
12), p = 0.065. Seed 1 (label, unpaired): two-hop +25.6, recall −5.0.

Chain yield, seed 2: 217 kept of 8,160 samples (2.7%; nb kept 85 of 2,040, 4.2%). Per pair and cycle, the four tries turned about 4% into
about 10% (217 kept of 2,040 pairs tried); 125 extra passing samples were dropped by the keep-first rule.

Verdicts:
- **X1 PASS** (seed 2): 53 of 78 two-hop questions had a kept chain dream (mark 45; nb 28). Seed 1: not available without the JSON.
- **X2 SHOWN** on seed 2 (+24.4, mark +8, p = 0.0001) and suggested on seed 1 (+25.6, label only). The wrong-if does not fire.
- **X3 FAIL** on both seeds: recall −4.5 (seed 2, p = 0.14) and −5.0 (seed 1, label), against a mark of −3.
- **X4 SHOWN** (seed 2): dreamed two-hop questions are answered 86.8% (46 of 53), not-dreamed ones 4.0% (1 of 25), +82.8 points, Fisher
  p = 7e-13 (mark +30). Dreaming a two-step pair is what makes the model answer it.
- **Adopt: no.** X2 passes, but X3 fails on both seeds, so x4 is not added to the recipe as it stands.
- No harm: ARC 92.0 / 92.2 (mark 87.6), diary 86.3 / 90 (reference 86.0 / 86.4).
- The expectation (dreamed 45-60, two-hop 50-65) was met; the recall cost was not expected.

What this suggests (not shown):
- The two-step gain is real and large, and coverage explains it (X4). The cost is on single facts, mostly C2 facts (mentioned on 2 days):
  C2 78-79 vs 86-88. Reverse questions also dropped (−6, p = 0.065).
- REM has a fixed number of training steps a night (510 at 4x). With 2.5x as many chain dreams the REM pool grows (532 dreams by night 7,
  against 397), so each dream and each gist is rehearsed less, and two-step questions may pull answers toward the second hop. Either
  could cost single-fact recall. Untested.
- Night 1 was reverted on both seeds (ARC validation 0.83 against a base of 0.87, mark −0.03). On night 1 the REM pool held exactly one
  chain dream, so REM's steps that night trained on one example many times. nb's night-1 pool was empty. Suggested cause: repeating a
  tiny pool. A floor (no REM steps from a pool under about 8 dreams) would remove it.
- Next single change to test: x4 with REM steps scaled so each dream gets the same rehearsal as in nb (more work, not a different
  recipe), with pass marks two-hop ≥ nb + 15 and recall ≥ nb − 2.

Cost: about $1.60 (seed 1 about $0.72 at $0.489/h; seed 2 about $0.88 at $0.563/h), against the coordinator's $1.90 cap after the runs
took longer than planned (x4 adds about 40% to each night's wall time).

## Addendum 12: the adopted recipe on the big tier, Qwen3.6-35B-A3B on a 4-bit base (q36_q4, Week-2, seed 1)

Prereg: PREREG-sleepB-addendum12.md (sealed before the code and the run). One RTX PRO 6000 WS box (57683866, $1.252/h, 15:21Z to 20:20Z,
about 4.98 h, about $6.25 against the coordinator's $7.50 cap; the bench estimated 4.4-4.6 h). Run wall 17,878 s. JSON and log in
`results_a12/`. Thinking off, routed experts frozen, LoRA on attention / DeltaNet / shared expert, MLX-affine 4-bit base as preregistered.

| arm | C4 | C2 | **recall C2+C4** | reverse | two-hop (dreamed of 78) | changed new | routine | tagger recall / precision | eligible C2+C4 | base_diary -> diary | ARC base -> after | reverts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-2B ab_ob_b4_nb s1 (addendum 9, reference) | 95 | 88 | 91.5 | 85.0 | 38.5 (32) | 96.7 | 85 | 0.674 / 0.700 | 188 | 79.7 -> 86.4 | 92.2 | 0000000 |
| K2-3.7B bf16 (addendum 11c) | 97 | 96 | 96.5 | 91.5 | 3.8 (5) | 93.3 | 100 | 0.826 / 0.802 | 200 | 80.0 -> 84.5 | 89.4 -> 91.0 | 1100000 |
| **Qwen3.6-35B-A3B, 4-bit base** | 98 | 94 | **96.0** | 96.5 | **67.9 (74)** | 96.7 | 30 | 0.775 / 0.737 | 197 | 85.7 -> 95.6 | 99.4 -> 99.0 | 0000000 |

- **B1 PASS (shown):** recall 96.0 (mark >= 75). The wrong-if cannot fire (recall is not below 60). Tagger mention recall 0.775, names
  pass yes on 142 of 247 questions (57%).
- **No harm PASS:** ARC-Easy 99.0 vs 99.4 before sleep (floor 94.4); diary 95.6 vs 85.7 (floor 80.7). No night was reverted.
- **Against Qwen3.5-2B nb seed 1 (paired, same questions):** recall +4.5 (17 vs 8 discordant, p = 0.11); reverse +11.5 (30 vs 7,
  p = 0.0002); two-hop +29.5 (31 vs 8, p = 0.0003). Against K2 bf16: recall -0.5 (7 vs 8, p = 1.0), reverse +5.0 (16 vs 6, p = 0.053).
- **Two-hop (shown):** the big model kept 375 chain dreams (yield 18% of 2,088 chain samples, against 4% on Qwen3.5-2B), and 74 of the
  78 two-hop questions were dreamed. But only 53 of the 74 dreamed ones were answered (72%, against 94-96% for Qwen3.5-2B nb). The wrong
  answers are other names of the world (for example a boat name for a workplace). The REM pool reached 669 dreams with REM steps fixed at
  510 a night, so each dream was practised less than in nb (pool 375-397); suggested cause, tested on K2 in addendum 14.
- **Routine 30 (shown, a port problem):** the tagger extracted 1 of the 20 routines (habit facts), so routine questions fall back on
  the base. Not marked; untested why (suggested: this model's tagger replies skip habit phrasing).
- **Expectation** (recall 75-90, two-hop 30-50) was too low on both counts.
- Caveats: one seed; our PyTorch MLX-style 4-bit grid; routed experts frozen.

## Addendum 13 + 13b: does a small whole-model sleep change survive 4-bit? (ab_ob_full_s, `--freeze-lora --q4-eval`, Week-1, seed 1)

Prereg: PREREG-sleepB-addendum13.md (7df6784ee3) and 13b (21e6fe5d32), sealed before the code and the run. Code 107137a57d (`--q4-eval`) and
1170b38400 (`--freeze-lora`). One RTX PRO 6000 Max-Q box (57692265, Czechia, 0.99 h, about $1.40 against a $1.30 cap; the run finished on
its own at 0.95 h). JSON and log in `results_a13/`. Week-1 has 80 C2+C4 recall questions, so one question is 1.25 points.

**Found on the way (shown, CPU, 13b):** leaving `pm.disable_adapter()` makes every LoRA tensor trainable again (peft 0.21), so addendum 2's and
3's delta arms (ab_ob_full, ab_ob_full_s, ab_ob_local) also trained the LoRA at the delta's lr. With `--freeze-lora` the LoRA stayed at zero
in this run (`lora_B_nonzero` False), so the model is exactly the base plus the fp32 change.

| condition | what it is | recall C2+C4 | C4 | C2 | reverse C2+C4 | two-hop | changed new | ARC-Easy (500) |
|---|---|---|---|---|---|---|---|---|
| F0 | base, bf16, no change | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 89.8 |
| **F** | base + fp32 change (the arm as scored) | **60.0** | 82.5 | 37.5 | 68.8 | 3.7 | 60 | 92.8 |
| Q0 | base, 4-bit, no change | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 89.6 |
| **Q** | base + change, re-quantized to 4-bit (fresh grid) | **56.25** | 85.0 | 27.5 | 58.8 | 3.7 | 55 | 91.0 |
| Qf | base + change, codes re-rounded on the base's 4-bit grid | 56.25 | 82.5 | 30.0 | 61.3 | 3.7 | 50 | 91.0 |

- **S1 PASS (shown on this seed):** gain(F) = 60.0 (above the 20-point floor, so S1 is judged), gain(Q) = 56.25, retained share rho =
  0.94 (mark >= 0.75; wrong if < 0.25). Paired on the 80 questions, F vs Q: F-only 4, Q-only 1, p = 0.375; F vs Qf: 3 vs 0, p = 0.25.
  Qf's rho is also 0.94.
- **No harm (4-bit) PASS:** ARC-Easy(Q) 91.0 >= ARC-Easy(Q0) 89.6 - 3. The change also raised ARC in bf16 (92.8 vs 89.8, one seed).
- **How small the change is (shown):** mean |change| is 1.9% of one 4-bit step. Only 2.8% of the 4-bit codes differ from Q0 under Q, and
  1.85% under Qf. The expectation (5-30% of codes) was wrong; the change is far smaller than guessed, yet nearly all the recall survives.
- **Why it survives (suggested, now with a matching number):** the base weights sit at effectively random places inside their 4-bit bins,
  so a shift d flips about |d| / step of the codes, and on average the dequantized change equals d (stochastic rounding for free). The
  predicted flip share on the frozen grid is the mean |d| / step = 1.91%; the measured share is 1.85%. This needs a full-precision base to
  re-quantize from. A model kept only in 4-bit (the Qwen3.6 big tier) has no position inside the bin, so small changes would round back
  to the same code unless the change is dithered (stochastic rounding) or accumulated until it crosses a step (untested).
- **Replication (reported):** F 60.0 vs addendum 3's 63.5, where the LoRA also trained: -3.5, inside the 4-point seed spread, so the LoRA
  probably carried little of addendum 3's gain (suggested, one seed each).
- Diary pooled 80.6 (base_diary 84.9); no night was reverted; wall 3,203 s.
- **Caveats:** one seed, the Week-1 world, Qwen3.5-2B (not K2 or Qwen3.6), and our PyTorch min/max 4-bit grid, which differs slightly from
  MLX's (about 0.3% relative error, per the bug-hunt thread). It shows survival of a change trained alone, not a gain on top of the adopted
  recipe.
- **Next (per the prereg, not yet preregistered):** a multi-week arm, nightly add-on plus a slow whole-model change, against the add-on
  alone, judged on week-1 recall in week 3. It needs Week-3 and Week-4 worlds (built through the Message Batches API) and more than 30 GB
  of GPU memory, so it waits for next week's budget.

## Addendum 11 + 11b + 11c: the adopted recipe on K2-Horizon-3.7B, bf16 base vs 4-bit base (Week-2, seed 1)

Prereg: PREREG-sleepB-addendum11.md, 11b (memory, low-effort names thinking) and 11c (213e14c9ea: names question with K2's full thinking,
512 tokens; K2-only negative-reply parse), all sealed before their code and runs. Code f671a0fb8a. `SLEEPB_TOK=1024`, expandable segments.
Boxes: bf16 57694829 (RTX 5090, Australia machine 153968, 1.82 h, about $0.91), q4 57697815 (RTX 5090, Portugal machine 152963, 2.62 h,
about $1.47). JSONs in `results_a11/`. Earlier tries are in RUNLOG (night-3 OOM at 2,048 tokens; 11b's names pass answered no to everything,
so its abort rule stopped the run).

**Why the names question failed, and the fix (shown):** a probe on the Week-1 world (46 names questions, 36 linked; `results_a11/k2probe_week1*`)
asked it seven ways. With its thinking closed, or at low effort (which closes at once), K2 answers "no" to everything (accuracy 0.22).
With high effort and up to 512 thinking tokens it is right on 32 of 36 linked and 9 of 10 unlinked pairs (0.89). In the Week-2 runs the
names pass then answered yes to 41 of 50 pairs on bf16 night 1 (Qwen3.5-2B: 38 of 55), with 250-400 thinking tokens per question.

| arm | C4 | C2 | **recall C2+C4** | reverse | two-hop (dreamed of 78) | changed new | routine | tagger recall / precision | eligible C2+C4 | base_diary -> diary | ARC base -> after | reverts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-2B ab_ob_b4_nb s1 (addendum 9, reference) | 95 | 88 | 91.5 | 85.0 | 38.5 (32) | 96.7 | 85 | 0.674 / 0.700 | 188 | 79.7 -> 86.4 | 92.2 | 0000000 |
| **K2-3.7B, bf16 base** | 97 | 96 | **96.5** | 91.5 | 3.8 (5) | 93.3 | 100 | 0.826 / 0.802 | 200 | 80.0 -> 84.5 | 89.4 -> 91.0 | 1100000 |
| **K2-3.7B, 4-bit base** | 90 | 82 | **86.0** | 83.5 | 6.4 (10) | 83.3 | 75 | 0.775 / 0.838 | 191 | 60.1 -> 85.5 | 85.6 -> 86.8 | 0000000 |

- **T1 PASS (shown):** K2 bf16 recall 96.5 (mark >= 75). Against Qwen3.5-2B on the same questions: +5.0 (5 vs 15 discordant, p = 0.041).
  K2's note-taker is better (mention recall 0.83 vs 0.67; every C2 and C4 fact eligible, against 94%).
- **No harm PASS on both:** ARC-Easy 91.0 vs 89.4 before sleep (bf16) and 86.8 vs 85.6 (q4); diary 84.5 vs 80.0 and 85.5 vs 60.1.
  The bf16 run's ARC gate undid nights 1 and 2 (validation ARC 0.86 and 0.84 against 0.90 - 0.03); it still reached 96.5.
- **Q1 FAIL, shown harm from sleeping on the 4-bit base:** q4 - bf16 = -10.5 on recall (26 vs 5 discordant, p = 0.0002); reverse -8.0
  (p = 0.017). A small part is note-taking on the 4-bit base (tagger 0.78 vs 0.83, 191 vs 200 eligible); most is learning: 19 eligible
  facts missed against 7 (suggested). The 4-bit base also reads the diary much worse before sleep (60.1 vs 80.0). q4 recall 86.0 is still
  above T1's 75 and 5.5 under Qwen3.5-2B bf16 (p = 0.11).
- **Two-step dreams do not work on K2 yet (shown, a new port problem):** only 9 (bf16) and 17 (q4) chain pairs were kept all week, so two-hop
  is 3.8 / 6.4 against Qwen's 38.5. Most chain replies fail to parse: K2 with its thinking closed writes only the question line
  ("Question: Who mentors Sotraflil?") or only a name, not the "Question: ... / Answer: ..." pair (night 5: about 200 parse failures of 372
  chain samples). Suggested fix, the same as for the names pass: let K2 think before it writes the two-step dream.
- **What it means for the small tier (suggested):** sleeping on the 4-bit model costs about 10 points of recall on K2. Addendum 13 showed that a
  change trained on a full-precision base keeps 94% of its recall after re-quantizing to 4-bit (Qwen3.5-2B, whole-model change). So the
  small tier should sleep on a full-precision master and re-quantize each morning, not sleep on the 4-bit model, if the night's machine has
  the memory (K2-3.7B bf16 is about 10 GB, more than the 8 GB Mac). Untested for K2's add-on.
- Wall time: 6,300 s (bf16) and 8,236 s (q4); the names pass adds about 1 minute per night.
- Cost: K2 total about $3.57 of the $4.00 K2 cap (first try $0.60, 11b abort $0.07, four probe hosts about $0.20, a q4 host that never
  started $0.09, bf16 $0.91, q4 $1.47; Vast's own bill may be lower for boxes that never started).

## Addendum 15: recorded before any run (2026-10-25 22:45Z)
Code 7d04e81894 (`--text-scale`, `--dream-vary`, `--reword`); every flag defaults to the old behaviour. Old-arm smoke runs match the earlier code apart from a null `budget.text_scale`, and the saved adapters are byte-identical. All 18 selftest sections pass.
- New-wording questions: `data/week2_reworded.json`, sha256 d0b24af8d0be30cff18e811adc882203c2407306f67b726c2f976913cc7cf46b, made from week2.json (sha256 70db7146...). It has 478 tests (200 forward, 200 reverse, 78 two-hop) with 3 rewordings each, 1,434 in all, written through the Message Batches API: a main batch of 478 plus a retry of 4. Cost: $0.42, plus a $0.01 pilot.
- Choices made now, before any run, where the PREREG wording left room:
  - **V2's cramming gap** is `cramming_gap_pts`: the mean share of a test's practised cards answered right minus the mean share of its 3 rewordings answered right, over tests with at least 1 matching card. This is like-for-like. The majority-of-3 version is reported, not marked.
  - The two-hop card gap asks up to 3 kept chain dreams per test (both items covered, answer = the target), not exactly 1. It is report-only.
  - Card variety uses the first 40 texts per item (paraphrases first).
- Schedule (coordinator, 21:43Z): R8, then V8, back to back on Ben's PC after Think-2; D8 on Vast after the Oct 31 budget reset.

## Addendum 14: probe result and choices made before any arm (2026-10-25 23:35Z)
The step-0 probe ran on a free Kaggle T4 (fp16, gen-bs 24, code d9d283fad1), 6,021 s, with no empty replies and no OOM. Files: /mnt/project-files/sleep/k2chain/ (probe.json, probe_rows.json, probe.log). On Week-1 at day 7 there were 295 items, 166 eligible, 87 REM pairs and 27 two-hop tests, all 27 reachable. Results after 4 cycles, both directions:

| variant | tests dreamed forward | any direction | kept / samples | thinking tokens (mean), capped at 512 | wall (T4) |
|---|---|---|---|---|---|
| default | 13 | 18 | 40 / 620 (6.5%) | none | 257 s |
| q | 8 | 17 | 33 / 632 (5.2%) | none | 255 s |
| think | 19 | 24 | 78 / 519 (15.0%) | 449, 330 capped | 2,437 s |
| q_think | **20** | 23 | 72 / 537 (13.4%) | 441, 339 capped | 2,440 s |

- Selection rule (sealed): **q_think** wins. Its 20 of 27 forward is 74% of reachable, below 90%, so **--rem-tries 2**.
- Most rejected samples fail the question check (238-448 per variant are "bad") or open-book verification (102-210).
- Some pairs join two notes of the same fact written two ways (for example "Bouzeibas is the mentor of Glisemu" and "Bouzeibas has Glisemu as a mentor"). No valid two-step card can come from such a pair (suggested, from the rejected examples).
- **Budget:** the coordinator allowed only arm B now (hard cap $2.20; the week's credit is nearly gone). Arm A waits for the Nov 1 budget, or a free GPU slot. C1 and C2 need A, so they wait too. G is judged on B as soon as it finishes.
- **Speed setting (not a design change):** both arms use `--gen-bs 48` instead of 32. The thinking cards make REM writing about 10x slower, and this keeps B inside the cap. k2s_bf16 ran with 32, so C1 carries this small extra difference.
- Both arms also take `--reword data/week2_reworded.json` (report-only, addendum 15's new-wording test, run after the result JSON is written). This gives addendum 15 its 4x reference.

## Addendum 16: recorded before any run (2026-10-26 ~01:00Z)
PR #130 (sleep-efficiency flags) was reviewed and merged into this branch: merge d01aa01281, review fixes 3267a6bce8.
- With all flags off, and with only `--card-stats`, CPU smoke result JSONs and adapter tensors are byte-identical to a7ed69d79d for `ab_ob_b4_nb`, `ab_ob` and `ab_ob_b4_nb_x4`. All 19 selftest sections pass.
- Review fixes, both made before any run and both flag-on only:
  - a reverted night now also restores `--skip-known`'s known flags (before, a reverted night's flags survived into the next night);
  - `--rem-views` spreads each dream's practices evenly over the cycle (before, small pools got all their practices in the first steps).
- `--rem-views V` accounting, as coded and as the note's arithmetic assumes: a dream in the pool all night gets about V practices; a dream made in cycle c gets V times the share of the night's REM steps from cycle c on.
- `--rem-views` with `--rem-steps-mult` other than 1 is refused (ap.error).
- The runs use addendum 9's settings otherwise: `--tok-budget 2048 --gen-bs 32`, Week-2, seed 1. They run on one RTX 4090 (Ben's borrowed pair, free), all three in one job on the same card.

## Addendum 14, arm B: thinking chain cards + twice the REM practice (k2c_r2, K2 bf16, Week-2, seed 1)
Box 57736062, an RTX 5090 in Australia at $0.476/h, from 23:29Z to 02:48Z (3.3 h, about **$1.58**). Code a7ed69d79d. Flags: `--rem-chain-mode q_think --rem-dirs both --rem-tries 2 --rem-steps-mult 2 --think-eval --gen-bs 48 --reword data/week2_reworded.json`. Wall 11,615 s. Files: `results_a14/result_k2c_r2.json`, `results_a14/run_box_k2c_r2.log`.

| (weights only) | k2s_bf16 (11c) | **k2c_r2 (B)** | paired |
|---|---|---|---|
| recall C2+C4 | 96.5 | **82.5** | -14.0 (31 vs 3), p < 0.0001 |
| C2 / C4 | 96 / 97 | 69 / 96 | |
| reverse C2+C4 | 91.5 | 78.0 | -13.5, p = 0.0001 |
| **two-hop** | 3.8 (3 of 78) | **50.0 (39 of 78)** | **+46.2 (0 vs 36), p < 0.0001** |
| two-hop dreamed (chain dream covers both facts) | 5 | **76** | |
| right when dreamed | 3 of 5 | 39 of 76 (51%) | |
| changed new / stale | 93.3 / 7 | 53.3 / 46.7 | -40.0, p = 0.0005 |
| routine | 100 | 95 | |
| diary pooled (base_diary) | 84.5 (80.0) | 87.0 (80.5) | |
| ARC-Easy 500 (pre) | 91.0 (89.4) | 89.2 (89.4) | |
| nights undone by the morning gate | 1, 2 | **1, 2, 3, 7** | |
| REM pool at night 7 | 14 | 261 (146 at night 6) | |

Verdicts (sealed marks):
- **G FAIL:** two-hop 39 of 78. The mark was 75.
- **No harm, B:** recall 82.5 is below 93.5, so it **FAILS**. ARC 89.2 against a mark of 84.4 passes. Diary 87.0 against a mark of 75.5 passes.
- C1 and C2 need arm A, which runs on Ben's PC next.

What happened (shown, from this JSON):
- **Coverage is fixed.** Thinking before writing a card lifted chain dreams from 9 in a week to 227, and the tests covered from 5 to 76 of 78.
- **The last night was thrown away.** The morning gate undid night 7: ARC on its 100 validation questions was 0.86, under 0.90 - 0.03. All of B's recall loss comes from that night:
  - Of the C2 facts first eligible on day 7, B gets 1 of 28 right, against 26 for k2s_bf16.
  - Of the other 72 C2 facts, B gets 68 right, against 70.
  - Changed facts whose change came on day 7: 5 of 15 right.
  - Night 7 also made 115 of the pool's 261 chain dreams, and those were never kept in the weights.
- **The gate is noisy.** Its 100-question ARC check also undid nights 1-3: 0.84, 0.86 and 0.82. Yet ARC-Easy on 500 questions after night 6 was 89.2, against 89.4 before sleep. A 4-point drop on 100 questions is within the noise of the answers that flip each night (suggested).
- **No cramming.**
  - New-wording recall (C2+C4, both directions, 400 tests) is 80.25, the same as the usual questions' 80.25.
  - The practised cards score 77.3, so the cramming gap is -3.9 points, partly because night 7's cards were never trained.
  - Two-hop on new wordings is 50.0, the same as the usual 50.0.
  - Chain cards on their exact wording score 65.6 against 64.5 reworded.
  - 23 of the 1,434 rewordings appear word for word in some kept text.
- **Thinking at test time hurts:** two-hop 38.5 with high-effort thinking, against 50.0 without. Forward C2+C4 is 73 against 82.5.
- Night 5 kept no chain dream: all 268 tries ran to the 512-token thinking cap on 134 leftover pairs that never yield a card.

What this suggests for the 95% goal (untested): the next blocker is the morning gate, not card writing. A gate that measures ARC on all 570 validation questions instead of 100 would undo fewer good nights. That should be the next one-change test, on this recipe.

## Addendum 17: recorded before any run (2026-10-26 ~03:30Z)
Code 0f2df52dce adds `--gate-arc-n N` (default 100, which is the old gate byte for byte: the smoke result JSON is identical apart from timing; all selftest sections pass). The run (k2c_r2_g570 = arm B's flags + `--gate-arc-n 570`) is filed as GPU-queue job `add17-g570` for Ben's borrowed RTX 4090s. B ran on an RTX 5090, so GPU type differs (small numeric differences, like a sampling-seed change).

## Addendum 14 arm A and addendum 16: run on Ben's PC (recorded 2026-10-26 ~18:20Z, before either run)
Ben's PC (RTX 5070 Ti, 16 GB, WSL) came free before the borrowed 4090s, so both jobs run there, one after another, by
`pc/sleepb_pc.sh`. Code is unchanged: arm A from a7ed69d79d, addendum 16 from 5fc4b87a23 (git archives). Differences from the queue jobs:
- **Arm A uses `--gen-bs 24`, not 48** (arm B used 48 on a 5090). 48 does not fit 16 GB. Generation batches change which samples are drawn
  together, so this acts like a sampling-seed change, on top of the GPU-type change. If 24 runs out of memory, arm A restarts from the
  beginning at 16; the log says which.
- **Addendum 16 keeps `--gen-bs 32`** for all three runs. If C runs out of memory at 32, all three run at 16 (the prereg fixes only that
  the three match); `pull/add16-genbs.txt` says which.
- The PC's venv has transformers 5.20.2 and peft 0.21.2 as required; the accelerate version is reported, not enforced.

## PC run, first launch (2026-10-26 19:00-19:09Z): every run ran out of GPU memory
Logs: `results_pc/` (pushed by the Mac watcher). The PC venv was missing `datasets`; datasets 5.1.0 was added and nothing else changed
(torch 2.9.1+cu128, transformers 5.20.2, peft 0.21.2, accelerate 1.15.0, fla 0.6.0). In WSL, running out of GPU memory can show as
"CUDA driver error: device not ready".
- **Arm A never started.** Three tries (gen-bs 24, then 16) died in the startup self-test `selftest_shy`, before any training. That check
  held every LoRA module's full fp32 weight change at once: about 14 GB on K2-3.7B (252 modules), on top of the model. gen-bs has no effect
  on it. Arm B passed it on a 32 GB card.
- **Addendum 16's three runs** each died at night 1's first training step, in the full-vocabulary KL with `--tok-budget 2048`. No result
  was produced, so nothing was looked at.
- **Fix for the self-test (memory only):** the check keeps each module's small randomized factors and rebuilds one module's weight change
  at a time, with the same operations.
  - On CPU, against a7ed69d79d's version on a tiny LoRA model in fp32 and bf16, it gives the same output, the same global random state
    afterwards and the same restored weights.
  - Smoke runs with arm A's and arm B's flags (`--rem-chain-mode q` on the smoke model) give result JSONs identical to a7ed69d79d's in all
    1,119 fields apart from timing.
- **Arm A goes back to the 4090 queue** with the fixed commit.

## Addendum 16 rerun and addendum 17 on Ben's PC (recorded 2026-10-26 ~19:30Z, before either run)
PC order (coordinator): the thinking thread's short check, then this launch (`pc/sleepb_pc2.sh`, which starts by itself when the GPU is
handed over), then the thinking thread's P1/P2. Both runs use the commit with the self-test fix; training is unchanged by it.
- **Addendum 16 (C, T1, T2): `--tok-budget 1024` for all three, not 2048.** The token budget only cuts each training batch into smaller
  pieces: loss and gradients are the same up to rounding. The sealed prereg fixes only that the three runs match. If any of the three
  runs out of memory, all three start again at 512; `pull2/add16-tokbudget.txt` says which. gen-bs stays 32.
- **Addendum 17: an RTX 5070 Ti (16 GB), not a 4090; `--gen-bs 24`, not B's 48; `--tok-budget 512`, not 1024.**
  - The gen-bs change acts like a sampling-seed change, as noted for arm A.
  - The token budget changes rounding only.
  - If it runs out of memory, it starts again from the beginning at gen-bs 16; the log says which.
  - Marks are unchanged: S1 and S2 are against B's sealed numbers.

## Addendum 16 result (2026-10-27): neither efficiency fix helps
Ben's PC (RTX 5070 Ti), Qwen3.5-2B, Week-2, seed 1, `ab_ob_b4_nb` at 2x work, `--tok-budget 1024` and `--gen-bs 32` for all three runs (no
memory fallback was needed). The fast `causal_conv1d` kernel is not installed on the PC, so transformers used its slower reference version
of that layer in all three runs. Code 7325e1ea60. Results: `results_pc/run2/add16-{C,T1,T2}/`. About 78 min per run.

| | C (control) | T1 (+ skip known 0.25) | T2 (+ REM views 20) |
|---|---|---|---|
| recall C2+C4 (200) | 75.5 | 75.5 (25 vs 25, p = 1.0) | 78.0 (+2.5; 19 vs 24, p = 0.54) |
| C2 / C4 | 71 / 80 | 68 / 83 | 67 / 89 |
| reverse C2+C4 | 73.5 | 74.5 (p = 0.89) | 79.0 (+5.5, p = 0.15) |
| two-hop (78) | 32.1 | 26.9 (-5.1; 13 vs 9, p = 0.52) | 29.5 (-2.6; 11 vs 9, p = 0.82) |
| two-hop dreamed / right when dreamed | 32 / 78% | 28 / 75% | 26 / 88% |
| changed new | 96.7 | 86.7 | 93.3 |
| ARC-Easy 500 | 94.0 | 92.4 | 92.6 |
| diary pooled (base 79.7) | 82.5 | 81.4 | 84.8 |
| nights undone | none | none | none |
| known_share, mean of nights 3-7 | 0.35 | 0.28 | 0.29 |
| REM practices per night (nights 2-7) | 2,805 each | 2,805 each | 100, 478, 926, 1,503, 2,259, 2,788 |

**E0 (waste meter, C):**
- known_share over nights 3-7 averages 0.35. That is between the marks (>= 0.40 room for E1; < 0.20 unlikely), so no decision mark fires.
- `rem_cb` known_at_step is 0.97-0.99 on nights 2-5: REM over-practice **confirmed**. Every REM practice was of a card the model
  already answered right.
- The last quarter's known_share is 0.46-0.53, never >= 0.80, so no plateau stop.
- Not wrong: known_share is above 0.20 on every night.

**E1 (skip known cards): FAIL, and refuted.** T1 recall equals C's (75.5), so the "wrong if T1 <= C" condition fires. The mechanism did act:
known_share fell from 0.35 to 0.28, and about 2,800-3,000 known draws a night were redrawn. Two-hop -5.1 also misses its >= C - 5 mark by
0.1. No harm passes, with changed-new at exactly its mark (86.7).

**E2 (cap REM drill): FAIL, not refuted.** +2.5 recall, p = 0.54 (the mark was +3 with p < 0.05). Two-hop 29.5 >= C - 5 passes. No harm
passes. Bonus check: no night was undone. The cap moved 2,000-2,700 REM practices a night to NREM cards on nights 2-5.

**What it means (suggested):**
- Over-practising known cards is real waste, but it is not what limits recall at 2x work.
- Freeing those steps for other cards does not buy a measurable gain on one seed.
- The 4x reference (91.5) shows that more total work helps. Spending the same work more cleverly did not.
- Neither fix is adopted. Per the prereg, there is no seed-2 rerun and no E7.
- C's recall (75.5) is below my expectation of 82-87. Possible reasons are the PC differences above (card, token budget, slow conv
  kernel) or plain run-to-run noise (untested).

## Addendum 17: second and third PC tries (recorded 2026-10-27 ~03:50Z, before any result)
- **Second try (sleepb_pc2.sh, 02:17Z):** add17 died at night 1's first training step, in the KL's `log_softmax`, with "CUDA driver error:
  device not ready". This happened at gen-bs 24 and again at 16, with tok-budget 512.
  - By estimate, that step needs well under 16 GB: replay KL covers about 400 target positions.
  - So the error may not be plain memory exhaustion (suggested).
- **Third try (sleepb_pc3.sh, launched ~03:50Z):** the same flags and code, but with PyTorch's default CUDA allocator instead of expandable
  segments, and a 5 s nvidia-smi memory log. The allocator does not change any numbers.
  - If it fails again, add17 waits for a 24 GB+ card (the 4090s, or Vast after the Nov 1 budget reset), and the PC goes to the thinking
    thread.

## Arm A and addendum 15 on Ben's PC (recorded 2026-10-27 ~06:30Z, before any of these runs)
Ben's borrowed 4090s are treated as not coming. K2 bf16 can only run on Ben's PC: Kaggle's T4/P100 have no proper bf16, and the Macs use
the 4-bit path. The coordinator set the PC order: addendum 17, the thinking-loop thread's segment 1, the sleep race's round 1, then arm A,
looping P1, R8, looping P2a, V8, looping P2b. `pc/sleepb_pc4.sh` waits for each turn on flag files and passes the turn on when a run ends,
even if it fails. Every run uses code 7325e1ea60 and PyTorch's default CUDA allocator. Differences from the sealed plans:
- **`--tok-budget 512`** everywhere, not 1024. This only cuts training batches into smaller pieces, so it changes rounding only.
- **Arm A at `--gen-bs 24`** (B: 48), or at 16 from the start again if 24 runs out of memory. As noted before, this acts like a
  sampling-seed change.
- **Addendum 15's base** is chosen by the sealed rule. B failed no harm (recall 82.5), so the base is A's flags if A passes no harm
  (recall >= 93.5, ARC >= pre - 5, diary >= base - 5), else the defaults. The script writes the decision and its numbers to
  `pull4/base.txt` before R8, and I check it before R8 starts. If A has no result, R8 and V8 are skipped.
- **R8 and V8 at `--gen-bs 16`**, as sealed. If R8 runs out of memory at 16, both run at 8; `pull4/add15-genbs.txt` says which.
- D8 and V8p come later, if the PC has room.

## Addendum 17, third try: training crawled; fourth try recorded (2026-10-27 ~07:00Z, before it runs)
- **Third try (sleepb_pc3, 05:01Z):** it got past every earlier failure point, but night 1's training (296 steps, 175 s on the 5090) had
  logged nothing after 1 h 36 min, at 100% GPU use with 15.9 of 16.3 GB in use. That is at least 30x slower than expected.
  Suggested (untested): the full card spilled into system memory under WSL. It was stopped by hand, with no result.
- **Code change (log and memory only):**
  - `cuda_tidy()` (gc plus `torch.cuda.empty_cache()`) runs before each night's training and after each REM writing pass.
  - A log line every 200 training steps, and one per night with seconds, peak and reserved CUDA memory.
  - The result JSON is unchanged: the CPU smoke with arm A's flags matches a7ed69d79d in all 1,119 fields apart from timing. These calls
    only run on CUDA.
- **Fourth try (sleepb_pc5, same PC slot):** the same flags, but with `--tok-budget 256` (rounding only), the new code, and a watchdog
  that stops the run if its log is silent for 90 min. It ends by writing pull3/DONE, so the next PC job starts.
- **The arm A / R8 / V8 chain (sleepb_pc4)** uses the same code and `--tok-budget 256`, with the same watchdog.

## Addendum 17, fourth try: still about 9x slow; fifth try with a memory cap (recorded 2026-10-27 ~07:45Z, before it runs)
- **Fourth try (sleepb_pc5, 06:46Z):** night 1 no longer stalls. It trained its 296 steps in 1897 s, and the whole night took 2051 s
  (arc_val 0.881, probe_post 0.667, not reverted). On the 5090, arm B's night 1 took 227 s, so the PC is about 9x slower per step. The
  5090 took about 3.1 h for B's seven nights, so at this rate add17 would need about a day of PC time.
- **Cause, suggested:** PyTorch's reserved memory reached 16.0 GiB on a card with 15.9 GiB in total, with only 12.9 GiB in use. The
  rest can only have been system memory. Under WSL a full card does not report out of memory, so PyTorch never hands its cache back.
- **Code change (memory only, no number changes):** `cuda_cap()` reads `SLEEPB_CUDA_CAP_GIB` and caps PyTorch with
  `torch.cuda.set_per_process_memory_fraction`. Under the cap, the allocator frees cached blocks and retries instead of spilling. The
  night line also logs the most memory reserved. Nothing runs off CUDA or without the variable.
- **Rule, fixed now:** Windows' shared GPU memory counter for the WSL process is read while the fourth try runs.
  - If it shows 512 MiB or more in system memory (the spill), the fourth try is stopped (without its DONE), and **the fifth try
    (sleepb_pc6)** runs the same flags with a 14 GiB cap. If it runs out of memory under the cap, it starts again once at `--gen-bs 16`.
  - If not, the cap would not help: the fourth try keeps going under `sleepb_pc5guard.sh`, which applies pc6's deadline rule below.
  - pc6 stops itself if its log is silent for 90 min, or if, after night 2 or later, the remaining nights at 1.25x the last night's time
    plus 75 min of final scoring would end after 18:00Z. Either way it writes pull3/DONE, so the looping thread's segment 1 starts.
- **The arm A / R8 / V8 chain (sleepb_pc4)** uses the same cap and code.

## Addendum 17, fourth try stopped by its watchdog; add17 moves into my next PC slot (recorded 2026-10-27 ~11:10Z, before it runs)
- **Fourth try (sleepb_pc5):** after night 1 (2051 s), night 2's names pass finished, and then the log stayed silent for 90 min while
  it wrote the night's dreams. On the 5090, the whole of night 2 took 1379 s. The watchdog stopped it at 09:20Z and wrote pull3/DONE,
  so the looping thread's segment 1 took the PC at 10:07Z. No result. Neither pc6 nor pc5guard ran.
- **Spill check, not done:** Windows' shared GPU memory counter was read only after add17 had stopped, so it says nothing about add17.
  In pc5's last 90 min, the card sat at up to 15,961 of 16,303 MiB at about 100% use. That fits a spill but does not prove it.
- **Code (no number changes):** `cuda_tidy()` now also runs at the start of each night, before the names pass and dream writing. A
  log line gives each night's writing time. Both run only on CUDA.
- **New PC chain, `pc/sleepb_pc7.sh`, replacing sleepb_pc4 in my slots:** add17 runs in my first slot (after the sleep race's round
  1), then arm A after looping P1, then R8 after looping P2a. V8 waits for its own flag (`handoff/GO-SLEEP-V8`) in a slot still to be
  agreed. Every run uses the 14 GiB cap and code src-cap2. Each run stops if its log is silent for 90 min, or if, once night 2 or later
  ends, the projected end passes its time budget: add17 10 h, A 10 h, R8 and V8 16 h each. add17's flags are the sealed ones, as in
  pc5, at `--gen-bs 24` (16 on running out of memory).

## Why arm B's two-step stopped at 50%: the card writer (analysis of arm B's JSON, 2026-10-27 ~12:00Z)
Arm B, results_a14/result_k2c_r2.json. Labels: shown / suggested.
- **Shown: few two-step cards get written.** Chain cards kept / written per night:

  | night | 2 | 3 | 4 | 5 | 6 | 7 |
  |---|---|---|---|---|---|---|
  | kept / written | 6/138 | 15/346 | 32/612 | **0/1072** | 78/1920 | 96/1586 |
  | thinking tokens per sample | 453 | 442 | 327 | **17** | 390 | 431 |
  | night undone by the gate | yes | yes | no | no | no | yes |

  - On night 5, 1064 of 1072 samples never closed their think block, at 17 tokens each. **Suggested:** the writer is the model as
    trained so far (adapter on), and night 4's training broke its thinking.
  - On night 6, 1362 chain units were open, but the per-night cap let only 960 be tried.
- **Shown: two-step depends on when a test's cards could first be written** (the night both of its facts had been said on 2+ days):

  | first dreamable night | 2-3 | 4 | 5 | 6 | 7 |
  |---|---|---|---|---|---|
  | two-hop right | 9/9 | 12/16 | 9/19 | 9/15 | 0/19 |

  - When both single facts are answered, two-hop is 34 of 54 right; when either one is missed, it is 5 of 24.
- **Suggested:** fixing the gate alone (addendum 17) would rescue night 7's 19 tests only as far as one night of cards allows. That
  points to about 50-55 of 78, not 75. Chains first dreamable on nights 5-7 need cards written on their first night.
- **Shown (addendum 14 probe, Week-1, one night, base model):** of 537 samples, 72 were kept, 244 dropped as bad, 210 unverified and
  2 failed to parse. The rejected examples show a 20-token verifier cut before the answer, pairs made of one fact extracted twice,
  and questions followed by more thinking on the same line.
- **Shown (B's eligible items at week end, rebuilt offline with REM's pairing rule):** 186 pairs, of which 42 have far ends that
  contain one another (one fact extracted twice). The other 144 pairs include a pair for 77 of the 78 two-hop tests, so dropping the
  42 removes no test chain. 186 pairs make 372 units against a cap of 240 tried per cycle; the 144 make 288.
- **Next:** addendum 18 (sealed 85a786fd95) fixes the writer with four switches: the base model writes, distinct pairs only, the
  question is cut at its first "?", and the verifier gets 96 tokens. A one-hour generation-only pre-check on Week-1 decides whether the
  full arm runs; its Go mark is fixed in the addendum. Code: the switches default to today's behaviour. A CPU smoke run with them off
  matches 005265d6fb apart from timing and the four new `args` entries. selftest_add18 and selftest_rem_k2 pass.
- **PC chain `pc/sleepb_pc8.sh`** replaces pc7: slot 1 runs the pre-check and then add17; slot 2 runs add18 if Go, else arm A; then R8
  and V8 as agreed. If add18 takes arm A's slot, addendum 15's base is the defaults (the sealed rule's fallback when A has no result).
- **PC disk (2026-10-27 ~18:40Z):** C: on Ben's PC has about 210 MB free. Each run's results and logs take a few MB, but the LoRA
  adapter that sleepb saves at the end takes ~70-140 MB, and nothing reads it back. `SLEEPB_SAVE_ADAPTER=0` now skips that save; it
  changes no number. The chain is `pc/sleepb_pc9.sh`: pc8 plus that setting, code src-cap4, and C:'s free space in its log.

## The small tier moves to LFM3-1.7B; addendum 19 sealed (2026-10-27 ~20:45Z)

- Ben (19:45Z): "remember we use LFM3 now instead of K2." So the two-step goal now applies to LiquidAI/LFM3-1.7B.
- **Port (f35dd7e840):** sleepb runs LFM3 with every K2 think path (names pass, REM `q_think` writer, think-eval) and LoRA on 142
  modules.
  - Shown, CPU: the K2 and Qwen smoke results are unchanged.
  - Shown, real LFM3 weights: batched left-padded generation equals one prompt at a time (`results_a19/pad_check.log`).
- **Addendum 19 (sealed 09e4139256):** addendum 18's recipe on LFM3, Week-2, seed 1.
  - It runs in this thread's next PC slot instead of addendum 18 (K2), after a 1 h Week-1 card-writer check that stops it only if the
    port is broken.
  - Marks: G two-hop >= 75/78; recall >= 88.5; two-hop >= 39 (K2 arm B's), paired; the usual no-harm marks.
- Addendum 17 (K2) keeps running. Its gate result carries over to any model.
- The chain script `pc/sleepb_pc10.sh` takes over from pc9 once addendum 17 has passed its turn on (mock-tested on all three slot-2
  paths).
- **LFM3 no-think check (shown, CPU fp32, real weights, results_a19/leak_check):** the store test saw the served 4-bit LFM3 write
  reasoning and a stray `</think>` with thinking off (70 of 80 chats). With sleepb's own prompts, the full-precision model wrote no
  `</think>` in any of 32 replies (16 test questions, 8 tagger messages greedy and 4 sampled, 4 verifier prompts). No code change for
  addendum 19.

## Addendum 17's fifth try stopped by its budget; addendum 20 moves R8 and V8 to LFM3 (recorded 2026-10-28 ~00:30Z)
- **Addendum 18's pre-check (shown, Ben's PC, Week-1, one night, generation only, `results_pc/run4/probe18`):** GO.
  - The fixed writer carded 27 of 27 reachable two-hop tests forward; the old writer carded 16.
  - It kept 112 of 163 samples (69%); the old one kept 72 of 534 (13%). Bad and unverified samples fell from 241 and 208 to 19 and 19.
- **Addendum 17, fifth try (shown):**
  - At `--gen-bs 24` it ran out of memory in night 2. The 14 GiB cap now turns a full card into a real out-of-memory error, not a
    slow spill.
  - At 16, night 1 took 826 s and night 2 took 5265 s, against 227 and 1379 s on the RTX 5090: 3.6-3.8x slower, not 9x.
  - Its projector stopped it after night 2 (projected end 07:48Z, budget 05:38Z), so there is no result.
  - It is not tried again: the small tier is now LFM3, and addendum 19 carries the same gate.
- **Addendum 20 (sealed):** addendum 15's R8 and V8 run on LFM3, not K2, with addendum 19's flags as their base if addendum 19
  passes no harm and P1 (else the defaults).
  - Addendum 19's K2 fallback is dropped.
  - Chain script `pc/sleepb_pc11.sh` replaces pc10 while pc10 waits.

## Addendum 19 on LFM3: pre-check RUN, the week stopped at its budget after night 5; addendum 21 reruns it (recorded 2026-10-29 ~15:15Z)
- **Why it started 29 h late (shown):** pc11 waited forever. Its turn test asked for the GPU under 4000 MiB, but Ben's desktop apps
  (Discord, Chrome, Lunar Client) hold ~6.7 GB of the idle card. `pc/sleepb_pc12.sh` (cbf3c79f10) tests GPU-BUSY, under 9000 MiB and
  under 30% utilization, and caps PyTorch at the card's free memory (8.5 GiB). It started at 05:11Z Oct 29.
- **Pre-check (shown, `results_pc/run4/probe19`): RUN.** The fixed writer carded 22 of 27 reachable tests forward (today's writer 19) and
  kept 105 chains (72). No `</think>` in any reply.
- **The week (shown, `results_pc/run4/add19/sleepb.log`): stopped by its projector after night 5, no result.**
  - Nights took 768, 3389, 3491, 4434 and 7984 s. Night 5 was ~2x slower in every part at the same memory use (suggested: something
    else used the PC).
  - The 570-question gate: base 0.693, then 0.816, 0.828, 0.853, 0.840 and 0.844. Night 5 was undone by the consolidated-recall check
    (0.845 < 0.90).
  - Forward recall after night 4: C2 17%, C4 55%.
  - Addendum 20's base fell to the defaults (no addendum 19 result).
- **Addendum 21 (sealed):** the same arm runs again with a 16 h budget in the slot R8 had (`pc/sleepb_pc13.sh`). R8 moves to V8's slot,
  and V8 gets a new slot (`handoff/GO-SLEEP-V8B`). Addendum 20's base is decided again from the rerun.
- **For the app thread's gate:** on 570 questions, LFM3's nightly gate score moved with an SD of about 1.4 points (81.6-85.3) while
  rising overall. Scaled to 40 questions, that is about 5.3 points (suggested), which matches the app thread's 5-10 point swings.
