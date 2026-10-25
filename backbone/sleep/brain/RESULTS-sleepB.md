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
