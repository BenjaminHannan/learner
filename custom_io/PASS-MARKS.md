# Pass marks: custom reader/reasoner/talker screen and confirm (fixed before any design trains)

Written 2026-10-05 about 05:58 UTC (1:58 AM ET), committed and pushed before any A, A0, B, plain_tf_steps, L2x2 or
open-LM run starts. Only the calibration runs in CALIBRATION.md (plain_tf, no verdict) have trained so far.
Designs and judging: `design/SYNTHESIS.md`, `design/JUDGES.md`, `design/design-*.md`. Fast lane: dev splits of the
seed-1 skills build only; nothing touches GOLD-PRIVATE, reserved or blind panels.

## Arms (all from scratch, character input, 24,000 updates, batch 256, shuffled order, bf16, AdamW as in train.py)
- **A (register loop):** shared shallow reader (char + position + place codes, 2 masked conv blocks, receptive field
  about +-4 chars); 16 slots (9 answer registers + 7 scratch) updated for 6 weight-shared rounds of
  self-attention + cross-attention to the reader output + MLP; linear per-register talker that sees only the final
  slots. Loss: per-round register cross-entropy; on rows whose `steps` give 2+ values, round r targets the r-th value.
- **A0:** A with the answer as the target on every round (one change: no step targets).
- **B (Ledger-lite):** same reader; a looped controller emits (op, operand, operand) steps executed by an exact
  integer executor; talker = print a pointed value, copy a pointed prompt word (content-free keys), or a linear
  register readout. Programs teacher-forced from `steps` where they parse.
- **plain_tf (S):** d256 x 4 layers, 3.24M params. Matched params and compute.
- **plain_tf L2x2:** 2 layers looped twice, 1.67M params, matched compute.
- **plain_tf_steps (S):** plain_tf trained to write `steps` then ` # ` then the answer on the 11 arithmetic families
  (targets capped at 64 chars), scored on the text after the last `#`. Also scored as **C1'**: a calculator fills each
  `a op b =` while decoding, no retraining.
- Size rule: A and B within +-3% of 3.24M params (S). A 10.8M (M) pair runs only if money remains.
- lr 1e-3 (S); one retry at 5e-4 is allowed only if every arm gets it. A run counts only with status ok.

## Metrics
- **pooled-5 (primary):** micro exact match over dev in_dist + answer + frame + vocab + variant (6,040 rows).
- **chain-5:** the five chain families (chain_ops, chain_story2, story_chain3, state_update, var_chain) on the
  200-per-cell in_dist build (1,000 rows; built on the box with `--dev-per-cell 200`, train.jsonl hash asserted).
- Also reported: multi-step in_dist (12 families), variant, each split, held-out families (expected 0-5% for all).
- Statistic: per-seed paired difference d = design - baseline at the same seed (same init seed and data order).
  Report mean d, 95% CI = mean +- t*sd/sqrt(n), seeds positive; paired McNemar on chain-5 rows for confirm.
- Noise (from CALIBRATION.md, 4 seeds of plain_tf S): one-seed paired-difference sd sigma_P = 1.4 (pooled-5),
  sigma_V = 1.5 (variant). sigma_C (chain-5) is not measured yet: 3.0 is used.

## Screen (seeds 100 and 101 shared by every arm; 2-seed means)
GO for a design needs ALL of:
- **G1:** pooled-5 d vs plain_tf >= +1.0.
- **G2:** chain-5 d vs plain_tf >= +8, both seeds positive.
- **G3:** in_dist d vs plain_tf >= -2.0.
- **G4:** pooled-5 d vs plain_tf_steps >= -1.0 (for B also vs C1').
- **G5:** the wiring lesions below hold in both seeds.

## Confirm (fresh seeds 200-205; the screen winner vs plain_tf S and plain_tf_steps S)
- **PASS-1 (beats a same-size transformer):** pooled-5 d vs plain_tf >= +2.0 with CI above 0 and >= 5 of 6 seeds
  positive; chain-5 d >= +8 with CI above 0 and McNemar p < 0.01; in_dist d >= -1.0.
- **PASS-2 (Ben's criterion, beats similarly sized models):** PASS-1, plus pooled-5 d vs plain_tf_steps >= +1.0 with
  CI above 0, plus pooled-5 at least 2 points above fine-tuned EleutherAI/pythia-31m (30.5M params, same rows, order,
  batch and updates; paired on seeds 200-202; its lr picked from {1e-4, 3e-4, 1e-3} by 6k-update runs, which can only
  flatter it), plus above 8-shot HuggingFaceTB/SmolLM2-135M and pythia-31m without fine-tuning.
- **Secondary:** variant d vs plain_tf >= +2.0 with CI above 0.
- **FAIL:** pooled-5 d < +1.0, or in_dist d < -2.0. Between FAIL and PASS: inconclusive, no claim, no more spend.
- L2x2 joins confirm only if it came within 2 pooled-5 points of the winner in the screen.

## Lesion marks (every seed)
Wiring checks (hold by construction; they show the plumbing, not reasoning):
- shuffle_state in_dist <= 10; zero_state <= 5; loops:0 <= 5; loops:2n within 3 of intact;
- same-family donor swap drops in_dist by >= 20, with donor_match >= 50% on number and string families.
Real evidence, A:
- round-1 register interchange with a same-family donor: counterfactual match (the row's own steps 2..k applied to the
  donor's first value) >= 40% and own-answer match <= 30%;
- prompt-blind after round 1 (cross-attention off from round 2) puts chain-5 <= 10;
- in A0 only: loops:1 puts chain-5 <= 15 while one-step families stay within 5 points;
- A - A0 >= +8 on chain-5.
Real evidence, B:
- loops:1 puts chain-5 <= 5; loops:2 cuts chain-5 by >= 40 while one-op families stay within 5 points;
- noexec (every executor result invalid) puts program families <= 10;
- opswap (ADD and SUB swapped at inference): >= 90% of outputs equal the swapped program's value.

## Results that prove a design wrong
- **A:** chain-5 d < +3; or A - A0 < +3 (and if A0 - plain_tf < +3 too, answer-only recursion is ruled out); or
  counterfactual match < 15% (the loop recomputes from the prompt, the sandwich's failure); or in_dist d < -4.
- **B:** chain-5 d < +10; or pooled-5 d <= 0; or C1' within 3 points of B on both chain-5 and pooled-5 (then the
  credit belongs to the calculator plus the steps, not to B's structure).

## Budget
Screen about $1.1, confirm one design about $1.5, open LMs about $0.5 (box $0.45-0.55/h). If over $3, drop
pythia-14m first, then shrink the lr grid to {1e-4, 3e-4}. A second confirmed design or the 10.8M pair only if money
remains above the $1 floor.
