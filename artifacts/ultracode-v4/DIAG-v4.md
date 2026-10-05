# Ultracode v4 diagnostics: where exactly is the learning blocker?

Written 2026-10-05 01:32 UTC (9:32 PM ET Oct 4), before any of these ran (commit 0f6e0ce08; jobs started 01:33 UTC). Fast lane, exploratory. Same rows as the fit screens: worst-8 families, the 2,000 fixed rows of seed 1, trainfit = their first 320, held-out = the 320 in_dist rows of those families. Code: `scripts/cap256_launch/uc_diag_v4.py`; box: `scripts/cap256_launch/ultracode_box.sh` (one Vast RTX 5090, queue in `queue/`).

## Questions and marks (fixed now)

1. **bare (can the frozen 1.2B do these at all?)** Chat template + "only the final answer"; chat template + worked steps then "Answer:"; the raw copy-path format with no prefix.
   - "LM can do them with worked steps" if chat_steps >= 70% on trainfit. "LM can't, even with steps" if < 40%.
   - chat_direct is the no-steps ceiling of the LM alone; compare it with main2 (trainfit 121/320 = 38% at update 0).
2. **chan (can 8 vectors steer the frozen LM to the right answer?)** On up to 64 trainfit rows main2 gets wrong (8 per family), optimise 8 free vectors from main2's own prefix, max 150 Adam steps, placed in front of the question (today's layout), after it, or alone (no question).
   - "front channel is enough" if front solves >= 90% of rows. "front placement is a bottleneck" if front solves < 60% and after-question solves 30+ points more.
   - "alone" says whether 8 vectors can carry the whole answer with no question to read.
3. **direct (can reader+core learn these rows when the signal is clean?)** main2's reader+core plus a new answer-class head on the core state (8 pooled slots x 256), no LM in the loss; 6,000 updates at batch 1 in the fit screen's order (seed 1). MLP head, linear head, and MLP head with a re-initialised core.
   - "core can fit with a clean signal" if MLP-head fit >= 85% at 6,000. "core can't fit even with a clean signal" if < 60%.
   - Held-out is reported (answers never seen among the 2,000 rows count as wrong, and their number is reported).

## How the readings combine
- direct fits and chan front solves: the core can hold the answers and the channel can deliver them, so the fault is the learning signal through the frozen LM. Next: losses or layouts that give the core a stronger signal (two-path loss, after-question vectors).
- direct can't fit: the core itself is the limit for these rows at this budget, so no exit or LM change alone will reach the mark; the fix must add capacity or a different computation route.
- chan front fails where after-question works: placement is a real bottleneck; test after-question vectors on the fit screen.

## Limits
One seed, one box, exploratory. Exact-match scoring. Nothing here touches GOLD-PRIVATE, reserved or blind panels.

## Added 01:35 UTC, before it ran: a generation-layout bug check (job 06)
Reading `skills_pretrain_v1.py` with `--copy-path`: `ad.forward` is patched to `with_prompt(o_fwd(...))`, but `o_fwd` (StatePrefix.forward) calls `self.project_training`, which is the *patched* instance attribute, so generation appends the prompt twice: the LM sees `[pooled][prompt][prompt][BOS]` at generation but `[pooled][prompt][BOS]` in training. The zero-pool lesion then also zeroes the first prompt copy, and the shuffle lesion swaps twice per row (so v3's S scores the current row's own vectors). Every copy-path fit/held-out number so far is a generation score, so all of them were measured on the doubled layout.
- New flag `--gen-fix` makes generation use exactly the training layout; each eval now logs `gen-layout` (LM input length before BOS) so the bug is visible directly (buggy = 8 + 2N, fixed = 8 + N).
- Job 06 scores main2 (no training) on the seed-1 trainfit rows and the 320 worst-8 held-out rows, with and without the fix, then on all 1,360 in_dist rows with the fix, intact / zero-pool / shuffle-pool.
- Marks: "the doubled prompt hurts" if the fix raises trainfit or held-out by 5+ points. Lesions under the fix: "core carries question-specific information" if shuffle drops 20+ points below fixed intact; "core carries little" if within 10 points; zero-pool reported.

## Added 02:05 UTC, before they ran: geometry, lesions under the training layout, exit capacity (jobs 09, 10)
From the critic pass of the understand workflow. All teacher-forced on the training layout `[pooled][prompt][BOS]` (teacher-forced exact = greedy exact when the layouts match), main2, no training. Rows: seed-1 trainfit (320) and worst-8 held-out (320).
- **09 geom.** Fixed point: mean relative change of h per round (rounds 2-8) and |e|/|h|. Mark: "loop is a contraction" if the change at round 4 is below 1e-2. Prefix geometry: mean pairwise cosine of pooled prefixes, spread around the family mean. Lesions: intact vs family-mean prefix vs global-mean prefix vs same-family shuffle vs 8 rounds. Marks: "core is a mode signal (c)" if the family-mean lesion is within 3 points of intact on trainfit; "core carries row content" if it drops 15+ points.
- **10 exitcap.** On up to 64 main2-wrong trainfit rows (8 per family), optimise (i) the core output h (N x 256) through the frozen exit, (ii) the exit's per-token hidden (N x 32) through its last layer and chunk means; max 150 Adam steps. Mark: "the exit is not the limit (b out)" if (i) solves >= 90% of rows; "the exit is a limit (b)" if (i) solves < 50% while free vectors solved 64/64.

## Added 04:23 UTC, before they ran: core test battery PR and LD (design panel, `PANEL-v4.md`)
Asked of this round (Ben wants the core, not the LM, to do the reasoning): why can't the core compute? Both are fast, LM-free or eval-only, box B.
- **PR (probe):** `uc_diag_v4.py --mode probe` on main2 and on a random reader+core (`--fresh-core`). Do number identities survive LM features f -> 32-wide reader r32 -> e -> h1 -> h4? Token probe on number tokens (1-NN and ridge, held tokens with seen values), row probe (ridge R2 for x0, step1, answer on the 4 chain families).
  - Marks (fixed now): "reader bottleneck destroys number identity" if f >= 90% and r32 < 50%; "identity reaches the core" if h4 >= 80%; "the loop loses identity" if e >= 80% and h4 < 50%; "final layer lacks identity" if f < 50%. Row probe: "the core makes the first step more visible" if R2(step1|h4) >= R2(step1|f) + 0.10 and >= 0.5; "the core adds nothing" if R2(step1|h4) <= R2(step1|f).
- **LD (learning ladder):** `--mode direct --head vocab --families chain_ops,state_update,chain_story2,var_chain --warmup 200`, 2,000 rows x 3 passes, held-out = their 160 in_dist rows (single-token targets only; drops reported). Learners: main2 core, fresh core, lmread (linear readout of the LM features, no core), tfm (a generic 4-layer d=256 transformer on the LM features). Targets: step1 (first intermediate value) and answer.
  - Marks (fixed now), held-out: step1 "one step is learnable here" if any learner >= 50%; "regime limit" if all four <= 25%; "core-specific defect" if max(lmread, tfm) >= max(core, fresh core) + 15 points; "the core computes one step" if max(core, fresh core) >= 50% and >= lmread + 10. answer: "a generic learner computes the chains" if tfm or lmread >= 40%; "answer-only regime limit" if all three <= 15%.
- The conditional follow-ups (OR, PL, LDD, DS, FZ) and their marks are in `PANEL-v4.md`; each is added here with its own timestamp before it runs.

## PR result (job 26, read 04:27 UTC)
Number-token identity on held tokens (best of 1-NN and ridge; 1,389 tokens, 99% with values seen in training): LM features f **98.5%**; main2's 32-wide reader hidden r32 **17.6%**; e 15.7%; h1 8.6%; h4 **8.9%**. A random (fresh) reader keeps more: r32 29.8%, h4 24.8%. Row probe R2 for step1: f 0.22, r32 0.09, h4 0.085 (main2).
- By the marks: **"reader bottleneck destroys number identity"** (f >= 90% and r32 < 50%). Not "identity reaches the core" (h4 8.9% < 80%). Row probe: **"the core adds nothing"** (R2(step1|h4) <= R2(step1|f)).
- Per the decision tree: OR is skipped (it would fail for an input reason). LD runs as planned (the lmread and tfm learners read the full 2,048-wide f, so they test whether a small learner can learn the step when it does see the numbers).
- LD smokes (60 updates, each learner) ran clean; 23 / 1,977 fixed rows and 1 / 160 held rows are dropped for multi-token step1 targets (all var_chain).

## LD result (job 27, read 06:11 UTC)
Held-out single-token rows (step1: 159 rows; answer: 151 rows), at the end of 3 passes (5,931 / 5,811 updates). Fit = the first 320 fixed rows.

| learner | step1 fit | step1 held-out | answer fit | answer held-out |
|---|---|---|---|---|
| main2 core | 7/320 | 5/159 (3.1%) | 6/320 | 1/151 (0.7%) |
| fresh core | 11/320 | 5/159 (3.1%) | - | - |
| lmread (linear readout of LM features, no core) | 147/320 | 1/159 (0.6%) | 146/320 | 4/151 (2.6%) |
| tfm (generic 4-layer d=256 transformer) | 26/320 | 5/159 (3.1%) | 20/320 | 4/151 (2.6%) |

- By the marks: step1 **"regime limit"** (all four <= 25%). Not "core-specific defect" (max(lmread, tfm) 3.1% = max(core, fresh core) 3.1%). answer: **"answer-only regime limit"** (all three <= 15%). The prediction (lmread 10-40% on step1) was wrong: the frozen final-layer features do not hold the first step linearly for new rows. lmread memorises (147/320 fit) but does not generalise; the cores cannot even memorise in 6k updates.
- Per the decision tree (c): run **LDD** and **PL**.

## Added 06:11 UTC, before they ran: LDD (marks as in `PANEL-v4.md`, copied here)
`--fresh-rows 17000` (new, 3 lines in mode_direct): 17,000 distinct rows of the 4 chain families, one pass each (17,000 updates), trainfit = the first 320 of them, held-out = the same 159 rows as LD. Learners: tfm (box B, job 29-ldd-tfm) and fresh core (box C, job 29-ldd-core-fresh).
- **"Data-limited (learnable with about 17k distinct rows)"** if either learner reaches >= 50% held-out on step1. **"Not learnable at this scale either"** if both stay < 25%. In between: inconclusive.
- If both < 25%, learned arithmetic from step labels is out of reach for a learner this size on these features at a practical budget, and the faithful core-side path for the chain families is the tool route (PL).

## Added 06:11 UTC: CF8 and BL1 re-run
Both crashed with CUDA out-of-memory on box C (six runs shared one 32 GB GPU; tracebacks in `results/24-conf-s8/CF8/stdout.events.txt` and `results/20-base-lesion-s1/BL1/stdout.events.txt`), so they produced no score. They re-run unchanged (same flags, same seeds) on box A as `28-conf-s8-rerun` and `28-base-lesion-s1-rerun`, two runs on one GPU. Runs are deterministic, so this is the same experiment, not a new draw.

## Added 06:24 UTC, before they ran: PL (can the core learn the plan for an exact calculator?), marks as in `PANEL-v4.md`
LD's best core variant scored 3.1% on step1 (< 25%), so PL runs. `uc_diag_v4.py --mode plan` (new): no LM in the loss. reader+core (main2, or re-initialised with `--fresh-core`) plus two new heads on the core output: a pointer head (6 slots over the question's tokens: the start number and up to 5 operands) and an op head (5 steps x {+, -, *, /, STOP}). Labels come from the curriculum steps; checked on all 17,981 chain-family training rows and the 160 held-out rows: every row parses and executing the gold plan reproduces the answer on all of them. Scoring executes the predicted plan with exact integer arithmetic. Same 2,000 rows x 3 passes as LD (seed 1), held-out = the 160 in_dist rows of chain_ops, state_update, chain_story2, var_chain. Box B, jobs 30-plan-main2 and 30-plan-fresh.
- **"Core can plan; build the calculator route"** if held-out plan-exact >= 85% and fit plan-exact >= 90% (main2 core). **"Core cannot plan these chains"** if held-out plan-exact < 60%. In between: the op and pointer accuracies locate the failure.
- Wrong if held-out plan-exact < 60% or op-sequence exact < 80%: then reader+core cannot even read which operation each sentence asks for at this budget; close the tool route and keep LM steps as the only route for the chain families.
- Prediction (panel): held-out op-sequence exact 85-97%, pointer exact 75-95%, plan-exact 65-90%; fresh core within 10 points of main2. For comparison, SR2's LM-written steps on these families score about 93% fit and 89% held-out; the CF4-6 audit says 67% of the LM's chain misses are misreads.

## LDD result, tfm (job 29-ldd-tfm, read 06:25 UTC)
16,815 distinct single-token rows, one pass each: held-out step1 **5 / 159 (3.1%)** at the end (best 8 / 159 at 16.5k); fit 10 / 320. The generic transformer learns no first step from 8.5x more distinct rows either. Fresh core (box C) still running; the LDD mark is read when both are in.

## LDD result, fresh core (job 29-ldd-core-fresh, read 07:35 UTC)
Same 16,815 rows, one pass: held-out step1 **4 / 159 (2.5%)** at the end (best 6 / 159); fit 5 / 320. By the LDD marks, both learners < 25%: **"not learnable at this scale either"**. Learned arithmetic from step labels is out of reach for a learner this size on these features at a practical budget (batch 1, AdamW 1e-3, no weight decay; a different recipe is untested). Per the decision tree, the core-side path for the chain families is the tool route (PL), which is the next result below.

## PL result (jobs 30-plan-main2, 30-plan-fresh, read 06:33 UTC)
Held-out = 160 new chain-family rows, after 6,000 updates (2,000 rows x 3 passes). plan = the executed plan gives the exact answer; ops = all 5 op slots right; ptr = every used pointer on the right number.

| core | fit plan | held plan | held ops | held ptr |
|---|---|---|---|---|
| main2 core | 94/320 (29%) | 43/160 (26.9%) | 52/160 (32.5%) | 93/160 (58.1%) |
| fresh core | 206/320 (64%) | **97/160 (60.6%)** | 98/160 (61.3%) | **146/160 (91.3%)** |

Fresh core over training, held plan: 1 -> 51 -> 73 -> 97 (updates 0 / 2k / 4k / 6k), still rising. By family at 6k (fresh, held plan / ops / ptr of 40): chain_story2 39 / 40 / 39, state_update 23 / 23 / 36, chain_ops 21 / 22 / 36, var_chain 14 / 13 / 35.
- By the marks: main2 core **"core cannot plan these chains"** (26.9% < 60%) and the wrong-if is hit (op-sequence 32.5% < 80%). Fresh core: **in between** (60.6%, just above the 60% line), with op-sequence 61.3% < 80% (the wrong-if's second clause). Not "core can plan" (needs >= 85% held and >= 90% fit).
- Locating the failure (the in-between rule): pointers are nearly solved on new questions (91.3%); the op sequence is the limit (61.3%), and plan-exact tracks it almost one for one (97 vs 98). var_chain's ops (13 / 40) are worst: its op symbols sit in a chain of definitions, and the op head reads 8 position-pooled chunks, not the tokens themselves.
- The prediction "fresh core within 10 points of main2" was wrong: the fresh core is 34 points better on held-out plan. main2's skills training left a core that learns this worse than a random one.
- This is the first test in which the core learns something about individual questions that carries over to new ones: which numbers to use (91%) and, partly, which operations (61%). Every learner failed to compute even one step (LD, LDD).

## Added 06:36 UTC, before it ran: PLD (does the plan route reach the mark with more distinct rows?)
One change from PL fresh: `--fresh-rows 17000` (new in mode plan, the same 3 lines as in direct): 17,000 distinct chain rows, one pass each (about 17,000 updates), fresh core, eval every 2,000 updates on the same fit-style first 320 rows and the same 160 held-out rows. Box B, job 31-pld-fresh.
- **"The plan route reaches the mark with more data"** if held-out plan-exact >= 85%. **"Ops stay the limit"** if held-out pointer >= 90% and op-sequence < 80%. Below 70% held-out plan: more data alone does not get there; the op head needs a redesign (read op words per token, as the pointer head does).
- For comparison, the LM writing steps on these four families' held-out rows: SR2 seeds 1-3 86.2 / 88.1 / 86.2% (mean 86.8%), CF4-CF6 83.1 / 84.4 / 86.9% (the panel's "about 89%" in the PL marks was high).
- Prediction: held-out plan 75-90%; pointer >= 93%; var_chain ops the slowest.

## PLD result (job 31-pld-fresh, read 07:05 UTC)
Fresh core, 17,000 distinct chain rows, one pass. Held-out plan-exact over training (of 160): 59 / 71 / 79 / 105 / 102 / 114 / 114 / 121 at 2k ... 16k, and **111 / 160 (69.4%) at the end** (17,000). End: op-sequence 115 (71.9%), pointer 139 (86.9%); fit plan 233 / 320 (72.8%). By family at the end (plan / ops / ptr of 40): chain_story2 37 / 39 / 38, state_update 30 / 32 / 35, chain_ops 25 / 25 / 38, var_chain 19 / 19 / 28.
- By the marks: not "the plan route reaches the mark with more data" (69.4% < 85%). "Ops stay the limit" is not met as written at the final point (pointer 86.9% < 90%; it was 93.8% at 16k). The final point is **below 70%: more data alone does not get there; the op head needs a redesign.** The last 1,000 updates cost 10 rows (constant lr, batch 1), so the plateau is about 70-76%.
- Plan-exact still tracks op-sequence (111 vs 115): the ops are the limit, worst on var_chain.

## Added 07:07 UTC, before they ran: PLO and PLOD (the op redesign the PLD mark calls for)
One change: `--op-attend`. Each step's op logits also read the core's state at the token its operand pointer picks: op_j += Linear(256, 5)(sum_t softmax(ptr slot j+1)_t z_t), with the pointer weights detached (the pointer keeps its own loss only). The pooled op head stays (it still decides STOP). In "gets 6 more" or "p = q * 4" the operand sits next to its operation word, which the 8 position-pooled chunks blur.
- **PLO** = PL fresh + `--op-attend` (2,000 rows x 3 passes; paired with PL fresh: held plan 97, ops 98 of 160). **PLOD** = PLD + `--op-attend` (17,000 distinct rows; paired with PLD: 111 / 115). Box B, jobs 32-plo-fresh and 32-plod-fresh. Primary reading = the final eval; the best eval is reported too.
- **"Reading the op at its operand fixes the op limit"** if PLO held-out op-sequence >= 80% (128 / 160) and held plan >= 121 / 160 (+15 points over PL fresh).
- **"The plan route reaches the mark"** if PLOD held-out plan-exact >= 85% (136 / 160). Then the next step is wiring the plan heads and the exact calculator into the real model (core plans, calculator computes, LM speaks the result), judged on the fit screen with lesions.
- Wrong if PLO held-out op-sequence < 70% (112 / 160): the operand's neighbourhood does not carry the op either.
- Prediction: PLO held ops 75-90%, plan 70-85%; PLOD plan 80-92%; var_chain still the weakest.

## PLO and PLOD results (jobs 32-plo-fresh, 32-plod-fresh, read 07:29 UTC)
`--op-attend`: each step's op also reads the core state at its pointed operand. Held-out = the same 160 new chain rows.

| run | fit plan | held plan | held ops | held ptr |
|---|---|---|---|---|
| PL fresh (2k x 3, before) | 206/320 | 97/160 (60.6%) | 98 (61.3%) | 146 (91.3%) |
| **PLO** (2k x 3, op-attend) | 273/320 (85.3%) | **124/160 (77.5%)** | **129 (80.6%)** | 137 (85.6%) |
| PLD (17k rows, before) | 233/320 | 111/160 (69.4%) | 115 (71.9%) | 139 (86.9%) |
| **PLOD** (17k rows, op-attend) | 285/320 (89.1%) | **139/160 (86.9%)** | 141 (88.1%) | 151 (94.4%) |

PLOD held plan over training: 73 / 110 / 126 / 118 / 132 / 126 / 141 / 128 / 139 (2k ... 16k, end); best 141 (88.1%). By family at the end (plan of 40): chain_story2 40, state_update 37, chain_ops 32, var_chain 30.
- By the marks: PLO **"reading the op at its operand fixes the op limit"** (ops 80.6% >= 80% and plan +27 rows >= +15 over PL fresh). PLOD **"the plan route reaches the mark"** (86.9% >= 85%). Predictions held (PLO ops 75-90, plan 70-85; PLOD 80-92).
- For comparison, the LM writing worked steps scores 84.4-88.1% on the same four kinds' held-out rows (SR2 seeds 1-3 mean 86.8%, CF4-CF6 mean 84.8%). Here no LM is in the loop at all after the reader: the core reads the question into a plan and an exact calculator computes the answer.
- Limits: one seed; the final eval moves by up to 13 rows between checkpoints (constant lr, batch 1); 17,000 distinct rows vs the screen's 2,000 x 3; four chain kinds only; the core still reads the frozen LM's features (the reader side of the sandwich is unchanged).

## Added 07:30 UTC, before they ran: PLC, the 6-seed confirmation of PLOD
PLOD with seeds 2-6 (jobs 33-plod-s2..s6, box B; seed changes the init, the row order and which 17,000 of the 17,981 rows are used; held-out rows are the same 160). Together with seed 1:
- **CONFIRMED** if the mean final held-out plan-exact over the 6 seeds is >= 85% (136/160) and every seed is >= 80% (128/160). Wrong if the 6-seed mean is < 80%.
- The best-checkpoint numbers are reported next to the final ones but do not decide.

## PLC partial (jobs 33-plod-s2..s6, read 08:03 UTC)
Seeds 3, 5, 6 finished; seeds 2 and 4 crashed with CUDA out-of-memory (three 10.5 GB runs started together on one 32 GB GPU; no score) and re-run one at a time (`36-plod-s2-rerun`, `36-plod-s4-rerun`, `# MEM 30000`), unchanged.
| seed | final held plan | best held plan | final ops | final ptr | fit plan |
|---|---|---|---|---|---|
| 1 (PLOD) | 139 (86.9%) | 141 | 141 | 151 | 285 |
| 3 | 125 (78.1%) | 138 | 128 | 151 | 267 |
| 5 | 128 (80.0%) | 136 | 130 | 148 | 272 |
| 6 | 135 (84.4%) | 137 | 138 | 152 | 261 |
- 4 of 6 seeds: final mean 131.75 / 160 (82.3%); seed 3 is below the 80% floor, so PLC **cannot be CONFIRMED** whatever seeds 2 and 4 give. Best-checkpoint mean 138 (86.3%), which does not decide. By family the weak spot moves between seeds (state_update 24 and 23 / 40 on seeds 3 and 5, 31-37 on the others).
- Reading: the plan route lands at about 82% final (86% at its best checkpoint) on new chain questions, against 85-87% for the LM writing steps. The last evals swing by up to 13 rows (constant lr 1e-3, batch 1, no decay), so the recipe's end point is noisy.

## Added 08:06 UTC, before they ran: PLCD (does an lr decay steady the plan route's end point?)
One change from PLOD / PLC: `--lr-cosine` (new in mode plan): after the 200-update warmup, the lr decays from 1e-3 to 0 along a cosine over the 17,000 updates. Same seeds 1-6, same rows, same held-out 160 rows. New box D (queue `d/`, two runs at a time), jobs 37-plcd-s1..s6.
- **CONFIRMED** (the plan route reaches the mark on new chain questions) if the mean final held-out plan-exact over the 6 seeds is >= 85% (136 / 160) and every seed is >= 80% (128 / 160).
- **"The decay steadies the end point"** if the 6-seed mean final is within 3 rows of the 6-seed mean best checkpoint (PLC's gap on 4 seeds: 131.75 final vs 138 best).
- Wrong if the 6-seed mean final is below PLC's 6-seed mean final: the noise is not from the constant lr.
- Prediction: mean final 136-141, every seed >= 130.
- If CONFIRMED, the trainer's planner (`--plan-route`) gets the same decay before the next real-model run; CR1-CR3 (running now) use the constant lr.

## PLC result, 6 seeds (jobs 32-plod-fresh, 33-plod-s3/s5/s6, 36-plod-s2-rerun, 36-plod-s4-rerun, read 08:29 UTC)
| seed | final held plan | best held plan | final ops | final ptr | fit plan |
|---|---|---|---|---|---|
| 1 (PLOD) | 139 (86.9%) | 141 | 141 | 151 | 285 |
| 2 | 130 (81.3%) | 134 | 137 | 141 | 273 |
| 3 | 125 (78.1%) | 138 | 128 | 151 | 267 |
| 4 | 140 (87.5%) | 140 | 143 | 151 | 284 |
| 5 | 128 (80.0%) | 136 | 130 | 148 | 272 |
| 6 | 135 (84.4%) | 137 | 138 | 152 | 261 |
| **mean** | **132.8 (83.0%)**, sd 6.1 | 137.7 (86.0%), sd 2.6 | 136.2 (85.1%) | 149.0 (93.1%) | 273.7 (85.5%) |

- By the marks: **not CONFIRMED** (mean 83.0% < 85%, seed 3 at 78.1% < 80%) and **not wrong** (mean >= 80%). The plan route lands at 83% final on new chain questions, 86% at its best checkpoint, against 84.8-86.8% for the LM writing steps on the same rows (SR2 and CF4-6 means).
- The final-vs-best gap (4.8 rows on average, up to 13 on seed 3) is the end-point noise PLCD (cosine lr decay, box D) tests. Ops still trail pointers by 13 rows; state_update is the weak family on seeds 2, 3 and 5 (23-25 / 40).

## Added 08:35 UTC, before they ran: PX and PXA (does the thinker's plan extend to the other four kinds?)
One new flag, `--plan-fams` (mode plan). The plan language gains one op, CAT (append the pointed token to the answer), and the other four worst-8 kinds become plans the thinker writes:
- seq_cycle, group_induct: point at the answer token in the question (the letter that comes next; the group's letter).
- cipher_map: point at each answer piece in the code table, joined with CAT ('7 6 6', 'h e a').
- fewshot_number_rule: a calculator plan built from the examples: add rule = query - in1 + out1 (sign of out1 folded into the op), mult rule = query * out1 / in1, pair sum = a + b. The thinker has to pick the rule from the examples.
Recipe as PLOD (fresh reader+core, `--op-attend`, 17,000 distinct rows, one pass, constant lr 1e-3, warmup 200), seed 1. Defaults (chain kinds only) stay bit-identical to PLOD/PLCD.
- **PX** (the other four kinds only). Held-out = the same 160 rows the skills screen scores for these kinds. The LM writing steps (SR2 seeds 1-3 + CF4-CF9, 9 seeds) gets **120.9 / 160** on them (75.6%; per seed 115-126; of 40: cipher_map 30.6, fewshot_number_rule 31.1, group_induct 35.6, seq_cycle 23.7).
  - **"The plan extends to the other kinds"** if held plan-exact >= 121 / 160 (the LM's mean); **"beats the LM"** if >= 136 (85%).
  - Wrong if < 96 / 160 (60%): pointers and a calculator do not carry these kinds.
  - Prediction: cipher_map 36-40, group_induct 28-38, fewshot_number_rule 28-38, seq_cycle 18-32 (kth_letter needs (k-1) mod p, the expected weak spot); total 115-140.
- **PXA** (all 8 kinds in one thinker, 34,000 distinct rows drawn from the 8 kinds' 39,788 train rows, one pass). Held-out = 320 rows.
  - **"One thinker plans all 8 kinds"** if held >= 85% (272 / 320), with its chain part within 10 rows of PLC's 6-seed mean (132.8) and its other-4 part within 10 rows of PX.
  - Wrong if held < 75% (240 / 320).
- One seed each (screens). If PX passes, the next step is the trainer's `--plan-route` for all 8 kinds (the thinker answers every worst-8 question, the LM only says it), judged on the fit screen with plan_swap lesions.

## PLCD result, 6 seeds (jobs 37-plcd-s1..s6, read 08:50 UTC)
PLOD/PLC plus one change, `--lr-cosine` (lr decays from 1e-3 to 0 along a cosine over the 17,000 updates). Same seeds, rows and held-out 160 chain rows as PLC.

| seed | final held plan | best | final ops | final ptr | fit plan | PLC final (paired) |
|---|---|---|---|---|---|---|
| 1 | 155 (96.9%) | 156 | 157 | 157 | 313 | 139 |
| 2 | 159 (99.4%) | 159 | 159 | 160 | 315 | 130 |
| 3 | 155 (96.9%) | 155 | 156 | 158 | 315 | 125 |
| 4 | 153 (95.6%) | 153 | 156 | 155 | 312 | 140 |
| 5 | 158 (98.8%) | 158 | 158 | 160 | 313 | 128 |
| 6 | 157 (98.1%) | 157 | 157 | 158 | 312 | 135 |
| **mean** | **156.2 (97.6%)**, sd 2.2 | 156.3 | 157.2 (98.2%) | 158.0 (98.8%) | 313.3 (97.9%) | 132.8 (83.0%) |

- By the marks: **CONFIRMED** (mean 97.6% >= 85%, lowest seed 95.6% >= 80%) and **"the decay steadies the end point"** (final 156.2 vs best 156.3). Paired gain over PLC +13 to +30 rows on every seed (mean +23.3). The prediction (136-141) was far too low: the constant lr, not the plan design, was holding the route at 83%.
- By family at the end (of 40, seeds 1-6): chain_ops 38/40/39/36/39/40, chain_story2 40 on all, state_update 40/39/39/38/39/40, var_chain 37/40/37/39/40/37.
- Against the LM writing worked steps on the same 160 rows (SR2 seeds 1-3 86.8%, CF4-CF6 84.8%): the thinker's plan plus the calculator is about 11 points higher, with no LM in the loop after the reader.
- Overlap check: no held-out chain prompt appears in train.jsonl; 15 of the 160 have the same numbers and steps as some training row (11 of them chain_story2, which every seed gets 40/40). Dropping all 15 still leaves every seed >= 95%.
- Not matched on data: the planner saw 17,000 distinct chain rows once; the screen's LM saw about 900 chain rows three times. The matched test (the plan route trained only on the screen's own chain rows) is next.
- Per the PLCD marks, the trainer's planner gets the same decay: new flag `--plan-cosine` in `skills_pretrain_v1.py` (default off, so CR1-CR3 stay reproducible).

## Added 09:34 UTC, before they ran: PLS (matched practice) and the PX/PXA recipe
**PX/PXA recipe amended before either ran:** both use `--lr-cosine` (PLCD confirmed it), otherwise as written at 08:35. Marks unchanged.

**PLS** = PLCD's recipe (fresh reader+core, `--op-attend`, `--lr-cosine`, warmup 200) trained only on the chain rows the skills screen practised: new flag `--screen-rows` draws the screen's own 8-family set (2,000 fixed rows x 3 passes, the trainer's RNG for that seed) and keeps the chain rows in order (about 890 rows x 3 passes, about 2,670 updates). Held-out = the same 160 chain rows. Seeds 1-6, paired with the LM writing steps on the same seeds: SR2 seeds 1-3 and CF4-CF6 get **138 / 141 / 138 / 133 / 135 / 139** of these 160 (mean 137.3, 85.8%).
- **"With the same practice, the thinker's plan beats the LM's steps"** if the PLS 6-seed mean held plan-exact is >= 140.3 (LM + 3 rows) and PLS is ahead on at least 5 of the 6 paired seeds.
- **"Ties"** if the mean is within 3 rows of 137.3; **"the LM learns more from the same practice"** if it is more than 3 rows under (then the 97.6% needs the extra practice rows, and the real-model route would train its planner on extra rows the LM never sees).
- Prediction: 115-140 (PLO, 2,000 chain rows x 3 at a constant lr, got 124).

## PLS result, 6 seeds (jobs 39-pls-s1..s6, read 09:48 UTC)
The thinker's plan trained only on the chain rows the skills screen practised (880-888 rows x 3 passes, 2,640-2,715 updates, `--lr-cosine`; `plan-screen` confirms the held-out rows are the usual 160).

| seed | PLS held plan | LM steps, same seed | diff | PLS ops / ptr | PLS state_update |
|---|---|---|---|---|---|
| 1 | 140 | 138 (SR2) | +2 | 144 / 148 | 36 |
| 2 | 141 | 141 (SR2) | 0 | 140 / 148 | 33 |
| 3 | 112 | 138 (SR2) | -26 | 112 / 148 | 9 |
| 4 | 131 | 133 (CF4) | -2 | 136 / 139 | 31 |
| 5 | 138 | 135 (CF5) | +3 | 142 / 141 | 29 |
| 6 | 133 | 139 (CF6) | -6 | 136 / 143 | 29 |
| **mean** | **132.5 (82.8%)** | 137.3 (85.8%) | -4.8 | 135.0 / 144.5 | 27.8 / 40 |

- By the marks: **"the LM learns more from the same practice"** (mean 4.8 rows under the LM, ahead on 2 of 6). Without seed 3, whose op head never learned state_update (9 / 40; pointers 148 / 160 were fine), the other five average 136.6, a tie. So with matched practice the thinker's plan is about level with the LM's steps, not ahead; the 97.6% of PLCD needs its 17,000 distinct rows.
- Open question this leaves: would the LM's steps also climb with those 17,000 rows? Arm LMDC (below in `SCREEN-v4.md`) tests it.

## PX result (job 40-px-s1, read 10:19 UTC)
The other four kinds as plans (fresh reader+core, `--op-attend`, `--lr-cosine`, 17,000 distinct rows, no drops). Held-out plan-exact over training (of 160): 53 / 60 / 57 / 69 / 68 / 68 / 74 / 75 at 2k ... 16k, **77 / 160 (48.1%) at the end**; fit 173 / 320.

| kind (of 40) | plan | ops | pointers | LM steps (9-seed mean) |
|---|---|---|---|---|
| cipher_map | **1** | 40 | 1 | 30.6 |
| fewshot_number_rule | **33** | 36 | 34 | 31.1 |
| group_induct | 26 | 40 | 26 | 35.6 |
| seq_cycle | 17 | 40 | 17 | 23.7 |

- By the marks: **wrong** (77 < 96): pointers plus a calculator, as built, do not carry these kinds. Not "the plan extends".
- Where it fails is specific. The ops are right on 156 / 160; the pointers are wrong. The kind that works (fewshot_number_rule, 33 / 40, above the LM's 31.1) needs pointers chosen by **role** (the query, the first example's input and output), like the chain kinds (98.8% pointers in PLCD). The kinds that fail need pointers chosen by **content**: cipher_map has to find the code-table entry whose letter or number equals a given one, seq_cycle the letter that matches the cycle position, group_induct the group whose numbers share the query's property. Suggested cause: the content-matching needs token identity inside the thinker, and the 32-wide reader drops it (probe: 98.5% in the LM features, 17.6% after the reader, 29.8% for a random 32-wide reader). Untested.
- PXA (all 8 kinds in one thinker) is cancelled before it ran: with the other four at 48%, its mark (85% on 320) cannot be met, and the run would cost about an hour of box C.

## Added 10:19 UTC, before it ran: PXW (does a wide reader let the plan do content lookups?)
PX plus one change: `--reader-hidden 256` (new in mode plan): the thinker's fresh reader is 2048 -> 256 -> 256 instead of 2048 -> 32 -> 256. Same rows, seed, held-out and recipe as PX. Box C (job 42-pxw-s1).
- **"A wide reader lets the plan carry the content kinds"** if held plan-exact >= 121 / 160 (the LM's mean on these rows, the PX mark).
- **"Identity was the limit"** if the pointers on cipher_map + group_induct + seq_cycle rise by >= 30 rows over PX's 44 / 120.
- Wrong if held < 96 / 160 again: a fixed query per pointer slot cannot do content lookups even with identity kept; the next design would compute each slot's query from the thinker's state (a content-addressed pointer).
- Prediction: 90-125. Identity should help group_induct and seq_cycle most; cipher_map stays hard, because "Write daa as numbers" splits the word into sub-word tokens ('da', 'a') and each lookup is two hops (find the letter's entry in the table, then point at its number).

## Added 11:26 UTC, before it ran: PXW2048 (the reader with no narrow door)
Ben asked for the door at 2048. PXW with `--reader-hidden 2048` instead of 256: the thinker's fresh reader is 2048 -> 2048 -> 256 (the thinker itself is 256 wide, so 256 is the most that can enter it without widening the thinker). Same rows, seed, held-out and recipe as PX and PXW. Runs on Ben's PC after PXW, or on the M1 Pro in parallel (`PC-JOB-pxw.md`).
- Same marks as PXW: **"carries the content kinds"** if held plan-exact >= 121 / 160; **"identity was the limit"** if the content-kind pointers (cipher_map + group_induct + seq_cycle) rise by >= 30 over PX's 44 / 120; wrong if < 96 / 160.
- Vs PXW: **"wider than 256 still helps"** if PXW2048 is >= 10 rows above PXW; otherwise 256 is wide enough for this.
- Prediction: within 10 rows of PXW.

## Added 11:38 UTC, before they ran: PLR (one router per round in the planner; Chain-of-Experts, arXiv 2506.18945)
Marks as fixed by the paper thread in `/mnt/project-files/papers/chain-of-experts-2506.18945.md`, copied here. PLS plus one change, `--round-routers` (being built): each UpcycledMLP in the planner's core gets one router per round instead of one router reused on all rounds; the experts stay shared; about 16k added parameters. Seeds 1-6, paired with PLS (140 / 141 / 112 / 131 / 138 / 133, mean 132.5); LM steps on the same seeds mean 137.3. Low priority: runs on Ben's PC or M1 after the door and talker-calculator runs, never on Vast.
- **Pass:** 6-seed mean held plan-exact >= 137.3 AND ahead of PLS on >= 5 of 6 paired seeds.
- **Proves it wrong:** mean gain under 1.6 rows, or ahead on 3 or fewer seeds. Then drop per-round routing.
- In between: inconclusive, do not adopt. **Void** if the logged per-round expert counts are near-identical across rounds.
- Checked in code: the main model's routers start at exactly zero (`scripts/sol_spatial_attention_core.py:24`), so with identical expert copies the router gets no gradient and experts 2-7 never train; the planner's fresh cores re-initialise them (`uc_diag_v4.reset_fresh`).

## Result 12:03 UTC: PXW (the wider reader, 256 instead of 32) — WRONG, the door was not the limit
It ran on box C after all (the box had already picked the job up when I removed its file from the queue). 17,000 rows, seed 1, same as PX.

| run | held plan-exact /160 | cipher_map | fewshot | group_induct | seq_cycle | content pointers (cipher+group+seq) /120 | ops right /160 | fit /320 |
|---|---|---|---|---|---|---|---|---|
| PX (reader 32) | 77 | 1 | 33 | 26 | 17 | 44 | 156 | n/a |
| PXW (reader 256) | **75** | 0 | 35 | 26 | 14 | **40** | 156 | 175 |

- Mark "carries the content kinds" (>= 121): **no**. Mark "identity was the limit" (content pointers +30): **no** (-4). **Wrong mark hit: held 75 < 96.**
- Shown (1 seed, as marked): an 8x wider reader changes nothing. The ops are right on 156 / 160 rows both times; the pointers are what fail, and they also fail on the PRACTISED rows (fit 175 / 320), so this is not overfitting.
- Verdict as written before the run: a fixed query per pointer slot cannot do lookups by content, even with identity kept. Next design (untested): compute each slot's query from the thinker's state (a content-addressed pointer), so "find the letter d in the table" can be asked as a question rather than learned as a fixed position.
- PXW2048 (reader 2048) is now expected to match PXW; kept as Ben asked for the 2048 door, but moved after WD and CRT on the PC.

## Added 12:08 UTC, before it ran: PXH (a two-hop, content-addressed pointer)
PX plus one change, `--ptr-hops 2` (being built): each pointer slot first attends with its fixed query (a new head, no labels of its own), reads the state it lands on, and turns that into a slot-specific content query over all tokens; the final pointer = the old fixed-query score + that content score (the content part starts at zero, so at update 0 it equals PX's pointer). Reader 32 as in PX; same rows, seed 1, held-out and recipe (17,000 rows, --op-attend, --lr-cosine, --plan-fams cipher_map,fewshot_number_rule,group_induct,seq_cycle). Runs on Ben's PC or M1 when they are back.
- **"A content query carries the content kinds"** if held plan-exact >= 121 / 160 (the LM's mean on these rows).
- **"The fixed query was the limit"** if the content-kind pointers (cipher_map + group_induct + seq_cycle) rise by >= 30 over PX's 44 / 120.
- **Wrong** if held < 96 / 160 AND content-kind pointers < 60 / 120: then the query's form is not the limit either; next suspects are that the thinker's token states do not hold the pairings (probe them) or the sub-word split of cipher words.
- Prediction: seq_cycle and group_induct gain most (seq_cycle >= 30 / 40); cipher_map stays under 15 / 40 because "daa" splits into 'da' + 'a', so one token holds two letters.

## Result 22:05 UTC: PLR (one router per round in the planner) — WRONG, drop per-round routing
Jobs 49-plr-s1..s6 on Vast box G (Ben said rent at 21:30 UTC because his PC was full with the swarm runs). Same rows and recipe as PLS; held plan-exact at the last eval.

| seed | PLS held /160 | PLR held /160 | gain | PLR fit /320 |
|---|---|---|---|---|
| 1 | 140 | 126 | -14 | 299 |
| 2 | 141 | 136 | -5 | 303 |
| 3 | 112 | 140 | +28 | 311 |
| 4 | 131 | 129 | -2 | 292 |
| 5 | 138 | 143 | +5 | 307 |
| 6 | 133 | 113 | -20 | 268 |
| mean | 132.5 | **131.2** | **-1.3** | 296.7 |

- Pass (mean >= 137.3 and ahead on >= 5): **no**. **Wrong mark hit:** mean gain -1.3 (< 1.6) and ahead on 2 of 6 (<= 3).
- Not void: the rounds do pick different experts (cosine between two rounds' expert counts, mean 0.40-0.55 per seed, minimum 0.14-0.19), so the routers did learn per-round choices; they just do not help.
- Shown (6 paired seeds): per-round routers do not lift the planner. Seed 3's +28 is PLS's weak seed (112) recovering, and seeds 1 and 6 fall by 14 and 20, so the spread grows rather than the mean. Dropped as written.
