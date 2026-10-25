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
