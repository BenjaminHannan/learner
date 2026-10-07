# No hard-coding: the learned replacement for every hand-written part, test order, sealed marks (2026-10-07)

Asked by Ben 12:01 PM ET 10-07. Thread "No hard-coding + richer input" (Opus, ultracode). Written before any run of anything in it.
Labels: **shown** = read in code or result files, **suggested** = reasoned, **untested** = not run. The custom reader/talker thread owns B2's code and runs; this file fixes definitions and marks only. Parts list with file:line: `INVENTORY-2026-10-07.md`. Input question: `INPUT-UNITS-2026-10-07.md`.

## 0. Ben's rule, as I apply it

1. Nothing hand-written may run between the question and the answer except inside a tool. A tool is something the model calls by writing text; its reply comes back as text the model reads like the question.
2. Teaching material may be hand-written (labels, worked steps, traces), the way a teacher writes worked examples. It never runs when the model answers. Disclosed; a backlog rung L1 (inventory section B) would remove the one piece of hand algebra in it.
3. Tests and scoring may be hand-written.
4. If removing a hand-written part costs points, the fix is in the learned link that broke, never putting the part back (Ben 10:35 AM ET, for the calculator; I apply it to every part).
5. Your message answers the architecture thread's open question: the outside calculator **replaces** the numbered slots, it does not sit alongside them. I'm taking that as decided; say if you meant otherwise.

## 1. Where it ends: "B3", everything learned (suggested)

One question, worked through B3:

```
context  = "Tom has 12 apples, gives away 5, buys 3. How many?"
turn 1   reader reads the context as bytes -> thinker loops -> writer writes  CALL 12-5
         calculator tool (hand code, allowed) returns "7"; appended:  ... | 12-5=7
turn 2   reader re-reads question + transcript -> thinker -> writer writes   CALL 7+3
         tool returns "10";                                    ... | 12-5=7 | 7+3=10
turn 3   reader -> thinker -> writer writes                    ANSWER 10      (stop)
```

| Part | B2 today (shown) | B3 (suggested) |
|---|---|---|
| Input unit | 108 hand-listed chars + hand place code | raw bytes (256), learned position only |
| Reader | 2 conv blocks, +-4 window | the window (it matters: R0 -6.3/-6.8) + global attention (W1) |
| Numbers in | regex -> int64 -> exact digit code in 16 slots | only the bytes; nothing parses a number before the model |
| Thinking | 2 blocks x 8 fixed rounds, picks 1 of 9 ops + 2 slots | same looped blocks and state vectors, cross-attending to the reader; no slots |
| Arithmetic | Python executor inside the forward pass | calculator tool; the model writes an expression, the tool returns text |
| Steps | at most 7, fixed schedule | as many calls as needed (safety cap 12); stops by writing an answer |
| Output | 3 hand renderers: `str()`, word slicing, 8 reversed registers | one learned byte writer with copy attention over question + transcript |
| Training | teacher-forced slot programs from a hand parser | teacher-forced traces (calls + tool replies + answer); the tool's real reply is inserted, never the label's |

Why it can work (suggested):
- Exact intermediate values beat latent ones (`REPORT.md` lesson 1, shown). In B3 the exact values still exist, as text in the transcript, which the model must read and copy itself.
- With the arithmetic in a tool, the model never has to compute on digits, only copy them. Copying is a pointer job that attention does well (Jelassi 2024, 2402.01032: a 2-layer transformer can copy long strings, shown in the abstract). Place value, which is what the hand place code supplies, matters for computing, and computing moves into the tool. Every paper trick that makes small models good at numbers (Abacus, position coupling, FoNE, xVal) feeds place or value from code that already knows where numbers start and end, i.e. hand-written features (papers file, numbers section).
- Teacher forcing on traces is how every tool-use paper the helpers opened starts (Toolformer, TALM, Calc-X, NPI, ReTool's cold start; abstracts). None of them is at 3M params, so this is untested at our size. TALM-style self-training (keep the model's own traces that end in a right answer) is the fallback if teacher forcing stalls; it is not in the ladder.
- The text baseline already runs a regex-triggered version and gets chain-5 96 (C1', shown), so the open question is the gap to B2's 99.7, not whether it runs at all. D0b (below) finds where that gap comes from before T1 is built.

## 2. The test order: one change at a time

Every rung is one change on top of the previous rung, paired by seed. Recipe as B2 unless stated: same 200k skills rows and order, 24,000 updates, batch 256, lr 1e-3, bf16, size within +-3% of B2's 3,302,481 trainable. Screens use seeds 200 and 201 against the previous rung on the same seed (rung 1 against the q33 B2 checkpoints, branch `claude/b2-confirm-checkpoints` f41d0f7d5). Scores: pooled-5 (in_dist, answer, frame, vocab, variant; 6,040 rows) and chain-5 (1,000 rows), as in `REPORT.md`.

| Rung | One change | Removes (INVENTORY ids) | Depends on | Owner of spec |
|---|---|---|---|---|
| D0 | no training: can the reader carry digits, can the talker copy them | none (diagnosis) | B2 checkpoints | architecture thread, sealed |
| D0b | no training: on the text baseline with its calculator (C1'), classify every failed chain-5 row by its first wrong link | none (diagnosis) | existing plain_tf_steps checkpoints | this file |
| T1 | calculator outside: writer writes a call, reply returns as text, no value codes, no result slots | A2, A5, A6, A7, A17 | D0 | architecture thread, sealed |
| O1 | one writer for every answer: delete NUM / WORD / GEN renderers and word keys | A10 (output use), A11-A15 | T1 | this file |
| N1 | delete whatever number machinery T1 kept: regex spans, number slots, constants (skipped if T1 already removed them) | A1, A3, A4 | O1 | this file |
| P1 | delete the place code | A9, A10 (last use) | N1 | this file |
| V1 | raw bytes instead of the hand-built vocab | A16 | any | this file (no screen, see below) |
| H1 | learned number of rounds per turn | A8 (rounds) | T1 | roadmap 2d / architecture thread (note for them: Popescu 2026, 2607.20519, abstract: a jointly trained halt gate distorts the loop; supervising every round and stopping on a confidence readout did as well or better. In B3 the stop is already supervised: the trace says when to answer) |
| B3 | 6-seed confirm of the result vs B2 and plain_tf_steps | | all above | this file |

Gain tests for richer input run beside the ladder on today's B2 (they do not depend on it): W1 (global attention in the reader; architecture thread's spec), U0 (letters vs word pieces, direct test of Ben's question), U2 (learned chunks), EGE (q39, running). Winners are folded into the ladder once they pass. See `INPUT-UNITS-2026-10-07.md`.

## 3. Sealed marks

### 3.0 D0b, report only (no pass mark; it decides where T1's effort goes)
On the plain_tf_steps checkpoints already saved (`/mnt/project-files/custom-io/checkpoints/20-screen-s100-w1/tfsteps_s100`, `22-screen-s101-w1/tfsteps_s101`), CPU only, run the C1' lesion on the 1,000 chain-5 rows and label each wrong row by its FIRST wrong link, comparing the written text with the row's gold steps: (a) an operand's digits copied wrong, (b) a wrong number chosen, (c) a wrong operation, (d) a tool result copied wrong into a later step, (e) the final answer copied wrong, (f) a step format the calculator did not fire on, (g) stopped early or ran too long. Report the counts per seed. If (a) + (d) + (e) (copying) is the biggest group, T1's risk is the copy path; if (b) + (c) (choosing), T1's risk is the thinker's state. No paper the helpers opened measures where a small text-plus-calculator model loses (papers file, tools section, gaps).

### 3a. Every parity rung (O1, N1, P1), 2-seed screen against the previous rung, same seed
- **S1** pooled-5 (rung - previous) >= -2.0 on both seeds.
- **S2** chain-5 >= 95 on both seeds.
- **S3** cipher_map in_dist >= 90 on both seeds (exact-letter guard; B2 reads 95-100).
- **S4** no dev split down by more than 4.0 on either seed.
- **S5** zero-round in_dist (loops:0 or the rung's equivalent) <= max(5, previous rung on that seed + 1).
- **S6** the rung's own link check (below).
- **Pass** = S1-S6. **Proved wrong** = pooled-5 mean of the two seeds below -4.0, or chain-5 below 90 on both: the removed part was doing work the learned path cannot do at this size. Then the part stays removed, the shortfall is reported, and the named fix runs (one change, re-screen). A second miss goes to an ultracode diagnosis of that link. Putting the part back is never the fix.

Link checks and named fixes:
- **O1.** On dev rows T1 answered right, O1's written answer string matches exactly on >= 99% of number answers; copy_word and cipher_map each within 2.0 of T1. Named fix: writer depth 2 -> 3 layers, paid for inside the size budget.
- **N1.** Digit probe (D0's method) on N1's own reader output: per-digit accuracy >= 99% at every place 1-9, and arith_bare, chain_ops, div_exact each within 2.0 of O1. Named fix: add W1 (if it has not already passed and been folded in).
- **P1.** Digit probe >= 99% at every place; rows whose numbers have 6+ digits within 2.0 of N1. Named fix, in this order: (1) W1's attention if it is not already in; (2) a learned boundary logit per byte from the reader, with a soft "distance from the next boundary" computed from it (cumulative sum from the right), trained only by the task loss (helper's suggestion after H-Net and ACT, untested).

### 3b. V1 (bytes), no screen
Today's vocab is exactly 13 specials + the 95 printable ASCII chars (108 ids, `data.py:24, 55`), so every train and dev char is printable ASCII and its byte is the same symbol. V1 changes only the embedding table's size (256 bytes instead of 95 chars: +161 rows, about +41k params at d 256, +1.3%). Mark: a unit test confirms every row is ASCII before the switch. The effect is read in the B3 confirm. If any row is not ASCII, V1 gets a normal 3a screen instead.

### 3c. B3 confirm, 6 paired seeds (200-205) against q33's B2 and plain_tf_steps
1. **Parity with B2:** mean(B3 - B2) pooled-5 >= -1.0, 95% CI lower bound >= -2.0, and B3 at or above B2 - 1.0 on >= 5 of 6 seeds.
2. **Still beats its size:** mean(B3 - plain_tf_steps) >= +3.0 with CI lower bound > 0 (B2 is +6.9, shown).
3. **Chains:** chain-5 >= 99.0 on >= 5 of 6 seeds.
4. **Tool off:** with the calculator replying "error", program-family rows (the noexec set) < 5%.
5. **Swap:** with + and - swapped inside the tool, >= 99% of affected chain rows follow the swapped value.
6. **Leaks:** zero-round in_dist <= 5 and donor in_dist <= 5 on every seed, with B2's value on that seed printed next to it.
7. **No split** down by more than 2.0 against B2 (6-seed mean).
8. **Audit:** a test that the model's forward pass takes bytes only and that no regex, `int()` or `str()` of a number runs outside `tools/`. Fails = not B3.
- **Pass** = 1-8. **Proved wrong** = mean(B3 - B2) below -3.0, or B3 not ahead of plain_tf_steps on the mean. Then, at 3M and this data, the hand-written parts were worth more than learning recovers; the finding goes to the roadmap's bigger rungs, and B3 stays the base anyway (Ben's rule).
- Noise: SD 0.94 is the spread of B2 - plain_tf across the 6 confirm seeds (`results/CONFIRM-ANALYSIS.json`, shown). The build thread prints the actual paired SD next to each verdict.

## 4. Creative and sleep (specs for the creative roadmap thread)

Parts D1-D10 are in section D of the inventory. Papers: `no-hardcoding-papers.md`, section "Learned masks and memory gates" (abstracts only; every result there is RL or a large language model, nothing at 3M). Proposed replacements (untested):

- **The used-number mask (D1, `creative/legal.py`).** In B3 it goes away by construction: the puzzle becomes a tool (the model writes a move; the tool applies it or replies "error: 5 already used"), which is the world's rules, like Minecraft refusing a block, and allowed. On B2 before that, two changes, tested one at a time:
  1. *Coverage input:* feed the slots each step has read back in as a learned "read" embedding on those slots (information, not a rule; the coverage idea of Tu 2016 and See 2017).
  2. *Legality head:* a small learned head, trained on the executor's own "used / illegal" labels, that the sampler consults instead of the hand mask (Zahavy 2018's action-elimination design). The hand mask stays only as the ruler it is compared against.
  - Not a bare penalty: Zabounidis 2026 (abstract) shows unmasked training with penalties suppresses valid moves at unseen states, and a learned feasibility classifier fixes it.
  - Marks (fixed now, scored on C1's DEV puzzles, never the sealed test): legal share without the hand mask >= 0.90 (raw 0.29, masked 1.00, PR #45, shown); answer accuracy within 0.5 of the masked model; proved wrong if the head lets through an illegal pick on more than 1% of held-out steps.
- **Tool-side rejection (D1/D3 as tools).** Closest to Ben's rule. Papers (Fission-GRPO 2026, Su 2025; 8B-class, RL) say small models repeat a bad call after an error unless recovery is itself taught, so the teaching data needs rows of the form "bad move, tool's error text, corrected move", made by our own tool.
- **The notebook gate (D6, memory sleep).** The hand-set threshold (theta 0.9, raised to the 0.99 quantile) and the c = 50 boost become a tiny learned gate on the top-16 similarity scores and vote share, labelled by whether the stored programme was right on the night's own practice rows (Drozdov 2022, Zheng 2021, Yogatama 2021). Marks: no more wrong answers from the notebook than today's gate at equal coverage, on a held-out frame split; proved wrong if it admits more confident-wrong answers there. Always compared with a no-notebook control (Xu 2023, Wang 2023: retrieval gains are often smaller than they look).
- **Later (B3):** the notebook becomes a recall tool the model calls, replying with stored programmes as text it can adapt, and the model is trained with the memory present (TRIME 2022, RETRO) so it learns when to trust it. Today's notebook replays slot ids, so 3x+7 cannot become 5x+2 (affine 0%, shown).
- **Settings and tests stay:** try budgets, temperature grids (D2, D5) are search settings around the model for now; the harm switch, checkers and blind baseline (D8, D10) are tests; the breadth-first solver's programmes (D9) are teaching material.

## 5. Order and compute (suggested)

1. D0 and D0b now, on CPU, by the build thread (no GPU).
2. T1 build, then its screen on the PC after q39 (about 9 PM to midnight ET), unless Ben OKs Vast.
3. W1 and U0 screens whenever a machine is free; they don't wait for T1.
4. O1, N1, P1 in that order, then B3.
Rough cost: a B2 run took 3.7 h on the PC (q33, 13,160 s, shown); T1-style runs read the context once per call, so expect about 1.5-2x per run (untested). The ladder is about 4 screens plus one 6-seed confirm, roughly 3-4 PC days, or about $10-15 on rented 5090s (untested estimate; credit is $5.22).

## 6. What would change this plan

- D0 fails badly on reading (expected, Amendment 1 of the D0/T1 file): not a stop, it is the baseline; T1 then needs the reader to learn digits, which is what N1's link check measures.
- T1 is proved wrong (more than 2 below B2): fix the named link first; the rest of the ladder waits.
- U0 shows word pieces beat letters by >= 2 on both seeds: add a learned word-piece side channel next to the bytes (like EGE, from scratch), as a gain test.
