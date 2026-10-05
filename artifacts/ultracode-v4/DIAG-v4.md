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
