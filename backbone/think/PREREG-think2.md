# Think-2 preregistration: train the LoRA and the thinking block together (1-seed pilot, Ben's PC)

Written 2026-10-25, before any Think-2 run. Follows Think-1 (`PREREG.md`, `RUNLOG.md`): G-STS was refuted (S(8) 67.0,
laps flat, swap lesion ~0) while plain LoRA given the same 1,254 extra steps reached 70.8 (aplus, 3 seeds).

## The one question
Think-1 froze the backbone and arm a's LoRA, so nothing could learn to read the notes. Does training the LoRA **jointly**
with the block let the notes pay off, compared with plain LoRA given the same extra steps?
This is the last pilot of looped latent thinking on this setup. No other variants run.

## Arms (seed 0 only, all on Ben's PC, RTX 5070 Ti, bf16)
| arm | what it is |
|---|---|
| a | LoRA, 418 steps (stage 1, rerun on the PC because Think-1's adapters were not recovered) |
| aplus | a's adapter, LoRA trained 1,254 more steps (the control) |
| tj | a's adapter, LoRA **and** a new G-STS block trained together for 1,254 steps, laps 0..4 |

tj's loss per batch = aplus's loss (same full forward, no board) + the Think-1 board loss (answer CE at every lap
t = 0..4, read from board t, plus 0.01 x the update penalty). So tj gets every gradient aplus gets, plus the block's.
Same batch order as aplus, same LoRA learning rate and schedule; board learning rates as Think-1. L_max fixed at 4
(Think-1: 4, 8 and 12 laps scored the same, and 4 laps fit the PC's time budget).

## Scores (validation, 8,675 rows, greedy exact match)
- S(L): tj with the board read after L laps; L in {0, 1, 4}.
- gatesoff: tj's LoRA with gates at zero (what the joint LoRA learned on its own).
- swap: row reads the board of a different story at L = 4.
- A+: aplus.

## Pass marks (fixed now)
- **P1 gain:** S(4) - A+ >= +2.0 points, and the paired bootstrap 95% interval excludes 0.
- **P2 notes used:** S(4) - swap >= +1.0 point.
- **P3 laps (reported, needed only to call it "looped thinking"):** S(4) - S(1) >= +0.5.

## Decision rule
- P1 and P2 pass: run seeds 1 and 2 (same PC) before any claim. P3 then decides whether it is looping or just a note pad.
- Anything else: **stop**. Report, and drop looped latent thinking for v2 (spend the effort on plain LoRA training,
  which Think-1 showed still had +4 points left).

## Wrong-if (the result that refutes the idea here)
S(4) - A+ < +1.0, or the swap lesion costs < 0.5. Either means the block, even with a trainable reader, adds nothing a
LoRA cannot get from the same steps.

## Known biases, stated in advance
- tj gets more compute per step than aplus (extra slot and answer passes). This favours tj, so the +2.0 bar is deliberately
  higher than Think-1's noise (re-scoring 0.2, aplus seed spread 0.4).
- One seed: a pass is a signal to expand, never a result.
- Hardware differs from Think-1 (5070 Ti vs 5090); only within-PC comparisons count.

## Addendum A (2026-10-25 14:20Z, before any tj result): arm tf, forced then released
Added at Ben's request ("why not force the notes to get used?"). Runs on the PC right after tj, seed 0, whatever tj scores.
- tf = tj plus blind answer passes in the board loss: with probability p(step) = 0.5 x max(0, 1 - step / (0.6 x 1,254)),
  a micro-batch's answer passes see no prompt at all, only the notes (the slot laps still read the full prompt).
  The aplus loss is never blind. From 60% of training on, nothing is blind.
- Extra readout: blind(4), answers that see only the notes, on the first 2,000 validation rows (how much the notes carry alone).
- Pass marks: the same P1 and P2 as tj, against the same aplus. tj and tf are judged separately. Passing either one
  triggers the 2-seed expansion for that arm only. If both fail, looped latent thinking stops as planned.

## Addendum B (2026-10-25 16:15Z, before any tj or tf result): control arm tc
A review (bug-hunt thread) pointed out that tj's LoRA gets more than aplus's: the aplus loss PLUS the board-path answer CE,
which with closed gates is a second copy of the answer gradient taken through another path. So aplus is not a clean control.
- tc = tj's exact loss and loop with the block switched off: lmax 0, gates frozen at 0, no block parameters trained.
  It gets tj's extra LoRA gradient without anything the notes could carry. Seed 0, PC, queued after tf.
- P1 for tj and tf is now judged against B = max(aplus, tc): S(4) - B >= +2.0 with the bootstrap interval excluding 0.
- P2 is unchanged. A P1 pass with P2 failing is reported as "suggested", not a pass.
- Diagnostic: the LoRA gradient norm before clipping (gn_lora) is logged for tj against aplus's, to see how often the clip engages.

## Addendum C (2026-10-26 00:20Z, before any tj, tf or tc result): give-up rule
Decided by the coordinator under Ben's never-wait rule, after design/research/2026-10-25-think-inner-state-codi.md
(PR #131) showed that a Think-2 fail cannot separate "the loop is useless" from "the notes were never taught".
- If Think-2 fails (neither tj nor tf passes): do NOT drop looped thinking yet. First run PR #131's checks 0-5
  (data check, free P0 diagnostics, toy plumbing check, written-steps teacher + filler sham, gate start 0.3 if the gate
  stayed shut, step-supervised notes), plus its hide-the-story and copy-the-teacher tests if their entry conditions
  are met. Then apply PR #131's give-up rule (every notes test misses a bar, or 18 Think-2-sized runs spent with no pass).
- If Think-2 passes: the 2-seed expansion runs as planned, plus the free checks and the swap test before calling the notes used.
- Recorded for the P0 code reads: Think-1's block trained at refiner/e0/eta lr 5e-4 and gate lr 3e-3 for 1,254 steps.
  tf hides the story with a separate answer pass on a fresh, empty cache, so there is no DeltaNet state leak (a CPU test
  shows blind logits are unchanged when the prompt changes).
- Think-1 checkpoints were never recovered (Vast file copy failed), so P0 runs on Think-2's tj/tf checkpoints.

## Addendum D (2026-10-26 22:00Z, before any toy-0.3, P1, P2a or P2b result): optional JOLT+ arm
Raised by Ben ("use JOLT+"). JOLT+ = on-policy distillation: the student samples its own answer after its laps, and the
loss is reverse KL to a better teacher on those tokens (plus an exact-match reward term), as in Think-3 Addendum A.
- It needs a teacher that is clearly better than answering directly, so it runs only if P1 opens P4
  (T >= max(tc, C1) + 2 and T >= sham + 1). Teacher = the ws model writing its steps; student = the P4 notes arm.
- It is an extra P4 arm `jolt`, run after P4's matching arm, from the same start checkpoint with the same steps.
  Marks: P4's marks, plus J1: S_jolt - S_P4 >= +2.0 (interval excluding 0) to count as better than matching alone.
- It never replaces a P4 or P2b verdict, and its runs count toward the 18 R cap.


## Addendum E (2026-10-27 05:30Z, before any P1, P2a or P2b result): adaptive halting
Raised by Ben: the assistant must decide by itself how many laps each problem gets, not use a fixed count.
- Always reported, no pass mark: for every lap arm, accuracy by depth (1-6) at each scored lap count. Halting is only
  worth building if harder (deeper) questions gain more from extra laps than easy ones.
- Arm `halt` runs only if a notes test passes (P2a, P2b, P3 or P4 meets every bar) AND that arm's lap gain is larger on
  depth 4-6 than on depth 1-2. It is the passing arm's recipe plus a halting head on the notes (PonderNet-style: a stop
  probability per lap, loss = expected answer loss over the halting distribution + 0.01 x KL to a geometric prior with
  p = 0.25), L_max 8, from the same start checkpoint with the same steps. At test time it stops at the first lap whose
  stop probability is >= 0.5.
- Marks: H1: S_halt >= S_fixed - 0.5, where S_fixed is the passing arm at its own lap count, while the mean number of
  laps is <= 0.6 x L_max. H2: mean laps on depth 4-6 rows minus depth 1-2 rows >= 1.0 (bootstrap interval excluding 0).
- Wrong if the laps used don't rise with depth (Spearman rho <= 0.1 between depth and laps), or S_halt < S_fixed - 1.5.
- It never changes another test's verdict; its run counts toward the 18 R cap.

## Addendum F (2026-10-27 06:05Z, before any br or aplong result): loop the model's own layers
Ben: "You have to get the loop to work." The notes block has failed every test so far, but Think-1's arm b (the
model's own middle block run 3 times) beat aplus by about +0.85 over 3 seeds (suggested: not compute-matched, one loop
count). This tests that lead directly, with a matched control and with halting in mind.
- Arm `br`: from a_s0's adapter, the same rows, order seed, optimizer and 1,254 steps as aplus. Layers 8-11 (the
  default block, 4 layers) run r times with shared weights and the shared LoRA, each pass with its own KV / DeltaNet
  cache. r is drawn per step: 1 + Poisson(m - 1) capped at 6, with m ramped from 1 to 4 over the first 75% of steps
  (McLeish-style retrofit; Random(seed + 5000), a fixed list: mean 2.80 at seed 0). Scored on validation at
  r = 1, 2, 3, 4, 6, 8 (dev at r = 4 only); S = S(r4).
- Control `aplong`: aplus with round(1,254 x compute ratio) steps, where the ratio is br's layer passes over plain
  passes (1.30 at seed 0, so 1,630 steps). Same start, rows and optimizer. This answers "is it the loop, or just more
  compute?"
- Marks (seed 0; seeds 1-2 if a margin is within 1 point of its bar):
  - F1: S(r4) - max(aplus, tc, aplong) >= +2.0, bootstrap interval excluding 0. Wrong if below +0.5.
  - F2 (depth 4-6 rows, beyond train depth): S(r4) - S(r1) >= +2.0 (interval excluding 0) and S(r8) >= S(r4) - 1.0
    (more loops must not break it). Wrong if S(r4) - S(r1) < +0.5.
  - PASS needs F1 and F2. F2 alone is reported as "loops help on deep questions, not beyond a matched control".
- Halting (Addendum E's marks, judged only if F1 and F2 pass; always reported): the training-free rule stops at the
  first r in 2, 3, 4, 6, 8 whose answer equals the previous r's answer (else 8). H1: its accuracy >= S(r4) - 0.5 at
  mean loops <= 0.6 x 8. H2: mean loops on depth 4-6 minus depth 1-2 >= 1.0 (point estimate: with ~1,500 and ~4,700
  rows its interval is about +-0.1). Wrong if Spearman(depth, loops) <= 0.1. A trained stop head (Addendum E's
  PonderNet arm) comes only after this rule passes or misses H1 alone.
- Accuracy by depth at r = 1, 2, 4, 8 against aplus, tc and aplong is always reported (no pass mark).
- PC order: br then aplong, ahead of P1. Both count toward the 18 R cap (about 1.0 R and 0.4 R).
- Known bias: S(r1) is not a trained-at-1 model; br saw r = 1 on about a quarter of its steps.
- Known bias: br is decoded with train.greedy (the board path cannot loop a block), while aplus and aplong use the
  board path. The two give identical hits on the CPU in fp32 (test TH); on the GPU only the batch grouping differs
  (arm a's reverse-order rerun moved 0.04 points).
- Seeds: with seeds 0-2 present, the 3-seed means decide (as in P1/P2b), so aplong and tc must run at the same seeds as br.
  The S(r8) >= S(r4) - 1.0 condition also counts toward the "within 1 point" seed rule.
- Fresh rows for final claims (fixed 2026-10-27 06:40Z, before any br result): validation shards 4-11 (visits 1,000-2,999,
  same v1 generator and seed), built by backbone/think/build_fresh.py: 17,481 questions, 2,934 at depth 4-6, fresh.jsonl
  sha256 ffc2e0e8f67927534385b327519bccfb8d9f270255abfed75d5d5f2c4853b07d. No screen has read them. They are scored only
  for an arm that already passed on validation (br at r4 with its halting rule, and aplong), once each, with the same marks.
- Hardware (added 2026-10-27 06:55Z, before any br result): the marks are judged on the RTX 5070 Ti runs (br, aplong,
  aplus and tc on one card). A second br seed-0 run on the Radeon 7700 XT (ROCm) starts earlier. It is reported as a
  hardware replicate, never used for the marks. It runs only after a numerics check: a_s0 scored on the Radeon must be
  within 0.3 points of its 5070 Ti score, with at least 98% of rows giving the same hit.

## Addendum G (2026-10-27 18:30Z; revised 19:00Z after an independent review of the code and this text, still before any hops run exists): can a loop work where depth really is serial?
Why. br failed on village (Addendum F: r4 71.26 vs aplong 71.97; r8 collapsed to 66.05). backbone/results/think2/DEEP_BREAKDOWN.txt
then showed that village's depth 4-6 slice is not a clean "more serial steps" measure:
- 83% of it is three question banks. plan_get (32%) has multi-step action-list answers. where_before (31%) uses a held-out
  question wording and scores 18-33% even at trained depth 3. compare_count (21%) is near its ceiling.
- An oracle over br's six loop counts (78.41) does not beat an oracle over three separately trained plain arms (78.93).
So the village null cannot tell "loops don't work" from "this task doesn't need serial depth". This addendum tests loops on a task
where depth is exactly the number of serial steps. It first runs a positive control: the one published recipe shown to install a
working loop in a small pretrained model with LoRA (Shapiro 2026, arXiv 2608.11233, 0.5B Qwen2.5 + rank-16 LoRA). It is a new
bed. No number from it is ever compared with a village number.

The hops bed (backbone/think/build_hops.py; rows fixed by seed; sha256 below and in HOPS_REPORT.json)
- Each row has 32 shuffled fact lines and one question, "Where is the {object}?".
  - The object sits in a container, which sits in another, and so on, until the last container sits at a place.
  - depth = the number of lines on that chain. The answer is the place (one token).
  - Every row has 7 chains: the query chain and 6 distractor chains of length 1-10, drawn until the row has 32 lines. Each chain
    ends at its own place. So the number of lines, chains and places does not depend on depth, and naming a random place of the
    row scores 1/7 = 14.3% at every depth (the floor).
  - Every name is one token, and is the located item (the thing said to be inside or at something) of at most one line, so the
    chain is unique. Each line uses one of two phrasings per relation, picked at random.
  - One weak depth trend remains: the distractor chains' mean length is (32 - depth) / 6 lines. It gives no answer.
- train: 128,000 rows at depths 1-4, so no arm sees a row twice. dev: 1,000 at depths 1-4. validation: 400 at each depth 1-10
  (4,000 rows; every mark reads these). fresh: 400 at each depth 1-10 from seed 1, for final claims only.
- sha256: train 81b37025025a4756..., dev 434db59ee77e5d5f..., validation c9b2c9f55aa07d28..., fresh 1b8817e3bf7ec012...
- Slices: "trained" = depths 1-4. "near" = depths 5-6 (800 rows): the marked unseen depths. "far" = depths 7-10: reported, no
  mark. Why near: Shapiro's adapter arm reached about 1.45x its trained depth (support 4 -> frontier 5.75). Depths 7-10 also need
  loop counts 7-12, which no arm trains, so a miss there cannot separate the loop from loop-count extrapolation.

Arms (Qwen3.5-0.8B; all start from a fresh LoRA r=16 with no stage-1 adapter; same batch stream, seed 0; LR and optimizer as
Think-2; batch 16, micro-batch 8, passed at launch; Ben's RTX 5070 Ti):
- `hloops` (positive control), 4,000 steps. The block is layers 8-11.
  - Every pass after the first starts from x + W.rms(e). e is the hidden state entering pass 1. W starts at zero.
  - Each row runs depth + U{0,1,2} loops (1-6 on the trained depths).
  - Loss: the answer after the last loop, plus the answer read after one random earlier loop k. That read is trained to name hop k
    of the chain (or the place, once the chain has ended).
  - Three things differ from br: re-injection, loops tied to hops, and graded laps. This is deliberate. It is the published
    recipe, run as a positive control, not a one-change arm.
- `hplains`: plain LoRA given hloops' layer passes as extra steps, fixed from hloops' plan before training: ratio 1.874 (the
  12-layer read counted), so 7,495 steps, on fresh rows.
- `hloop`: br's recipe exactly, 4,000 steps: random loop counts 1 + Poisson(m - 1), capped at 6, ramp 1 -> 4; no injection;
  final-pass loss.
- `hplain`: plain LoRA given hloop's extra layer passes: ratio 1.303, so 5,213 steps.
- All looped arms are scored at r = 1-12 on validation, with answers and answer log-probabilities kept. Dev is scored at r = 6.
  Arms with W are also scored at r = 6 with W = 0.
- PC order: pair B first (hplains, then hloops; about 4-5 h), between two race-mini arms. Pair A (hplain, then hloop; about 3-4 h)
  takes the GO-LOOP-P1 slot.
- Code: backbone/think/think1.py (arms), backbone/train.py (Inject, hidden_multi), backbone/think/summarize_hops.py (these marks
  and decisions; it prints each outcome with its next step), backbone/think/eval_adapter.py (fresh rows; loads W). Tests:
  backbone/think/test_hops.py.

Validity. If V1 or V2 fails, that pair is VOID, not a refutation.
- V1: plain >= 80 on depths 1-2 (it learned the task).
- V2: plain <= 70 on near (there is room above it).
- V3 (pair B only): hloops at r = depth >= 80 on the trained depths (the loop is installed). If it fails, the outcome is NOT
  INSTALLED.

Pair B: hloops vs hplains, at hloops' deployable score. That score is the answer-stable stop rule: stop at the first r whose answer
equals the answer at r - 1, else 12. A model that fits its targets stops at depth + 1, so on depth-6 rows the rule reads one lap (7)
that no arm trains.
- B1: near, halting - hplains >= +5, with the paired 95% interval above 0. Proved wrong below +1.
- B2: trained depths, halting - hplains >= -2.
- B3 (mechanism; no claim about deployment): near, hloops at r = depth - hplains >= +5, with the interval above 0. Below +1
  counts toward a fail.
- B4: Spearman(depth, loops chosen by the stop rule) over depths 1-6 >= 0.5, with a 2,000-resample row-bootstrap interval above
  0.3. Proved wrong at <= 0.1. On depths 1-4 the pattern (hop k at loop k, then the place) is trained. So B4 says the trained stop
  pattern holds and carries on into depths 5-6. It does not show that the model "decides" in any further sense.
- PASS B = B1, B2 and B4.

Pair B outcomes and decisions, checked in this order:
1. VOID (V1 or V2 fails). No claim either way. Redesign the bed in a new addendum before more loop runs on it.
2. NOT INSTALLED (V3 fails). Not a refutation. Check the wiring: |W|, step accuracy, the W = 0 lesion. If it is sound, run
   hloops + hplains once at 10,500 steps (Shapiro's length) before any claim.
3. PASS. The first working loop, on seed 0 only. Next:
   - a seed-1 replicate of hloops and hplains;
   - if that passes too, score the fresh rows once (eval_adapter.py --loops 1,...,12 --keep-preds, through these same functions);
   - then round 2, with marks fixed before it runs, removing one ingredient at a time: hloopd = hloops without the graded laps;
     hloopi = hloopd with random loop counts;
   - then transfer toward the assistant.
4. TOLD ONLY (B3 passes, B1 does not). The loop works when told how many laps; the stop rule is the gap. Next: a seed-1
   replicate, then a trained stop signal on hloops' states.
5. TRADE-OFF (B1 passes, B2 fails). Next: a seed-1 replicate, then find which trained depths lose.
6. NOT ADAPTIVE (B1 and B2 pass, B4 fails). The gain is real but the laps do not follow depth. Next: a seed-1 replicate, then a
   trained stop signal.
7. PROVED WRONG (B1 below +1 and B3 below +1). The published recipe does not install a working loop on this model at this budget
   (4,000 steps, seed 0). Next: one hloops + hplains run at 10,500 steps. If that also fails, we stop retrofitting loops onto the
   0.8B, and the loop line moves to one of:
   - a natively looped model (an Ouro-1.4B probe; it needs remote code, so it needs Ben's words on the PC);
   - written steps (P1, Think-3).
8. NOT SHOWN (anything else, between the bars). Next: a seed-1 replicate of both arms. No design change.

Pair A: hloop vs hplain, at a fixed 6 loops (br's own question, on this bed).
- A1: near, S(r6) - hplain >= +5, with the interval above 0. Proved wrong below +1.
- A2: trained depths, S(r6) - hplain >= -2.
- A3: near, S(r6) - S(r1) >= +5, with the interval above 0. Proved wrong below +1.
- PASS A = A1, A2 and A3. On a valid bed, anything else is "A fails". Both stop rules are reported for hloop, with no mark.

Pair A decisions. Pair B decides the loop line's next step; pair A only says how to read the village null.
- A passes. br's recipe works where depth is serial, so the village null is about village (its deep rows are not serial
  problems). Next, after B's step: a village measure that is.
- A fails and B passes. The recipe, not looping itself, is what failed on village. Next: bring the missing ingredients to village
  through round 2's ablations.
- A passes and B is PROVED WRONG. The results conflict. Run a seed-1 replicate of both pairs before acting on either.
- A fails and B does not pass. No step beyond B's.

Reported with no mark: far and deep (5-10) accuracies under every rule; the max-confidence stop rule (Fan et al. 2024); accuracy at
each fixed r; step accuracy (how often the answer after loop r names hop r, on rows deeper than r); the W = 0 lesion and |W|;
accuracy by depth; the floor.

Known biases and limits, stated in advance:
- One seed. A pass needs a seed-1 replicate before it is called a result. The fresh rows are then scored once for each passing arm.
- Budget: Shapiro's adapter arm passed its installation check at 4,000 steps, with an unknown batch, and was trained for 10,500.
  Our 4,000 steps at batch 16 may be short. A fail here is a fail at this budget; that is why decision 7 runs 10,500 steps before
  stopping.
- hloops differs from br in three ways, and it gets a second supervised target per row (hop k), which hplains never sees. A B pass
  credits the recipe as a whole, not looping alone. Round 2 separates the parts. A against B does not isolate one ingredient either.
- hplains gets 1.87x hloops' steps on fresh rows (the compute match): about 1.87x more distinct training rows. That is the usual
  equal-compute comparison, and it can only make the bar harder for hloops.
- hloops draws its read k per micro-batch, so micro-batch 8 (as registered) is a different random draw from micro-batch 4. No bias
  is expected.
- The 0.8B's block (layers 8-11) has 3 Gated DeltaNet layers and 1 full-attention layer. No paper we found loops DeltaNet layers.
- Two fixed-r comparisons (A1, A3) and two halting comparisons (B1, B4) are read. The +5 bars are large against a paired SE of
  about 2 points on the 800 near rows.

Revision note. The first text (18:30Z) and its code had these faults, all fixed before any run:
- "deep" was depths 5-10, which mixed chain-length and loop-count extrapolation.
- Places were drawn at random, so naming the most-mentioned place scored 19-23%, rising with depth.
- The number of chains fell with depth.
- There were 64,000 train rows, so the plain arms repeated rows.
- The arms were scored at r = 1-10 and 12, so the stop rule compared 12 with 10.
- There was no installation check (V3), and several outcomes had no decision.
- The code labelled a B fail without checking B3 < +1.
- eval_adapter.py dropped W.
The review is in backbone/results/hops/REVIEW-2026-10-27.md.

## Addendum H (2026-10-27 20:05Z, before any run of it): do extra laps help the assistant's own big model, with no training?
Why. Addendum G trains a loop into a 0.8B model on Ben's PC. This side test asks something cheaper first: can extra laps already help
the big model the assistant runs, with no training at all? The model is Qwen3.6-35B-A3B at 3 bits, run under MLX on the M3, for
inference only. It is a separate bed from village and from Addendum G's trained arms, and no number here is compared with theirs.
What is known (backbone/results/laps/RESEARCH-2026-10-27.md):
- Re-running middle layers with no training gave gains on one author's own probes for Qwen3.5-27B (RYS-II, same layer pattern; small
  n, no intervals). It gave about +1 point, within noise, on Gemma 2 and Llama 3 (Lys et al. 2026), and losses on 7B+ models in
  CircuitProbe (2026).
- Our own K2 pre-screen (Oct 27) found that training-free repeats hurt or tie on village depth 4-6.
- No source tests chain-following depth, a 3-bit MoE, or a stop rule on an untrained model. A null result is the likely outcome.

The bed (backbone/think/mac_laps.py build; rows from build_hops.make_row; sha256 in backbone/results/laps/LAPS_REPORT.json)
- Same row shape as Addendum G, but 64 lines and query chains of 1-16 hops. 7 chains per row, each ending at a different place, so
  the floor is 1/7 = 14.3% at every depth.
- dev: 40 rows per depth (640, seed 0). test: 100 rows per depth (1,600, seed 1, independent of dev).
- sha256: dev 0c871990c46bb557..., test d372f0a2ce93448f...
- Prompt: the facts and "Question: Where is the {object}? Answer with the place only." in one user turn, thinking off, and the
  assistant turn pre-filled with "The {object} is at the". The answer is the place with the highest next-token log-prob among the
  row's 7 places, each one token after a space (checked at run time; the run stops if not).

Laps
- A block is 1, 2 or 3 whole periods (4, 8 or 12 layers; each period is 3 linear-attention layers and 1 full-attention layer).
  It starts on a period edge from layer 4 and ends at least 4 layers below the top: 21 blocks for 40 layers.
- Lap 1 is the plain model. Lap r runs the block r times in a row, then the layers above it.
- Every pass is a full-sequence pass, so each re-run linear-attention layer starts its state from zero. This equals a repeated
  layer list with one cache entry per pass, which the tests check.

Stages (automatic, in this order; each decision uses only the rows named)
1. calib (dev, plain model): the deep slice D = the depths whose plain dev accuracy is in [24.3, 80]. If no depth qualifies, the
   outcome is VOID.
2. sweep (dev rows in D, lap 2, all 21 blocks): C* = the block with the highest dev accuracy on D. Ties go to the higher mean
   log-prob of the answer, then the smaller block, then the earlier one.
   If C* beats the plain model on dev D by less than +2 points, the run stops: NO CANDIDATE. The best of 21 blocks on dev is
   biased upward, so if it cannot reach +2, the +5 test bar cannot pass.
3. test (all 1,600 test rows): the plain model; C* at laps 2, 3 and 4; and a control block (same size as C*, the start farthest
   from C*'s; ties go to the earlier start) at lap 2.

Marks (test rows only; paired row bootstrap, 2,000 resamples, 95%)
- V: the plain model scores at least 80 on depth 1, else VOID (it cannot read the bed).
- H1: C* at lap 2 minus the plain model on D is at least +5, with CI lower bound above 0. Proved wrong: below +1.
- H2: C* at lap 2 minus the plain model on depths below D is at least -2.
- H3, adaptive, judged only after a PASS: answer-stable halting over laps 1-4 (the first r ≥ 2 whose answer equals lap r-1's,
  else 4). Its accuracy minus the plain model on D must be at least +5 with CI above 0, AND Spearman(depth, laps used) over all
  1,600 rows must be at least 0.3 with CI lower bound above 0.
- Outcomes, first match wins:
  - VOID: next, revise the bed so the plain model has headroom, before any rerun.
  - NO CANDIDATE: stop this path.
  - PROVED WRONG (H1 below +1): no free extra laps for this model; the trained loop (Addendum G) is the only route.
  - NOT SHOWN: no follow-up unless Addendum G passes.
  - TRADE-OFF (H1 passes, H2 fails): check H3 before anything else.
  - PASS (H1 and H2): next, (1) the same test at 4 bits, (2) a general-ability guard (MMLU-Pro, 300 items, at most -2), (3) only
    then ask Ben about a think-harder mode in the assistant.
- Reported with no mark: accuracy by depth at each lap; the control block's gain; the halting laps by depth; the dev table of all
  21 blocks; the hidden-state RMS at the last position per lap.

Known biases and limits, stated in advance
- One model, one quantization (3 bits), one prompt. Quantization error may add up with each extra pass, so a null here does not
  rule out laps at 8 bits.
- The control block is not a full compute-matched control: it shows whether the location matters, not whether any extra pass would
  do.
- Picking C* on dev and testing on fresh rows removes selection bias from H1, but D also comes from dev, which is fair because D
  uses only the plain model.
- The bootstrap SE of a paired difference on D (about 600 rows) is about 1.5-2 points, so the +5 bar is large.
- Runs on the M3 (Ben does not use it) in a slot from the coordinator, with a free-memory check before loading (20 GB). It needs
  about 2-4 hours, depending on the measured speed.

Revision H.1 (2026-10-27 20:50Z, before any run; after an independent review of mac_laps.py). Wording and code only; no mark,
bed or stage changed.
- H2 when no depth lies below D (D starts at depth 1): not evaluable, and it counts as met.
- Depths that are not in D but lie above its lowest depth (a gap in D, or the near-floor depths past it) count in neither H1 nor H2.
  They are still reported by depth.
- A depth whose true plain accuracy is at the floor (14.3%) can still reach 24.3 on 40 dev rows by chance (about 4% per depth).
  Such a depth in D dilutes H1 towards zero, so this bias works against a PASS, never for one.
- The run processes rows in depth-interleaved order, so a stopped run still covers every depth evenly. A summary made before every
  test row is in is labelled PARTIAL, is not a result, and writes no SUMMARY or analysis file.
- Stage files that end in a torn line (a crash mid-write) are cut back to their last complete record before resuming, and a resume
  with different settings (meta.json) stops instead of mixing runs.
- Every run starts with a self-check on the real model, before any row: all places in both splits are one token, the
  layer-by-layer pass matches the model's own forward, and lap 2 of a middle block matches the model run with that block's layers
  listed twice (largest log-prob gap below 0.05). If it fails, the run stops with no rows written. Both sides apply the head to
  the last position only (one row): on Metal, a quantized matmul over one row and over many rows rounds differently by about one
  bf16 step, which a second review showed could fail a correct run (emulated on the 0.8B model's 3-bit head).
- A summary reads stage files without rewriting them and counts each row id once; meta.json also records the bed's sha256.

## Addendum I (2026-10-28 10:00Z, before any hloopi or hloopd run, before pair A's seed-1 runs, and before any seed-1 pair B result was read; hplains seed 1 is training): round 2, which part of the loop recipe lets it stop by itself?
Why. Round 1 (Addendum G, seed 0, backbone/results/hops/pc/SUMMARY_hops.txt) passed both pairs. Near (depths 5-6): hloops halting
98.50 vs hplains 62.75; hloop at 6 laps 96.50 vs hplain 59.13. Ben's aim is a loop that decides by itself how much thinking each
problem gets, so what matters next is the stop rule, and which training labels it needs. Real requests have no hop labels and no
known depth, so only a recipe trained on the answer alone can move to the assistant. Of the round-1 arms, only hloop is one.
What seed 0 shows about stopping (read before this addendum; no mark; scratch script, numbers on the validation rows):
- hloops, answer-stable rule (online: it runs one lap past the lap it answers with): near 98.50, laps run = depth + 1. Its laps are
  graded, so each lap names one more hop, and the answer stops changing when the chain ends.
- hloop, answer-stable rule: near 87.25, about 2 laps at every depth (Spearman(depth 1-6, laps) 0.43). Its answer often repeats
  between laps 1 and 2 while still wrong, so the rule stops too early.
- hloop, max-confidence rule: near 95.88, and the lap it picks rises with depth (1.4 -> 6.2). But this rule is not a stop rule: it
  runs all 12 laps and then picks one, so it saves no compute. Online confidence rules did worse on the same rows: a threshold on the
  answer's probability (0.5-0.99) gave near 65.5-86.5, because wrong early answers are often very confident (log-prob above -0.01);
  "stop after 4 laps without a confidence gain" gave near 95.75 but ran 5.4 laps even on depth-1 rows.
So the answer-only recipe can pick a good lap only after running them all. Round 2 asks which ingredient gives a stop rule that
works online, and whether that ingredient needs labels that real data lacks.

The ladder (each arm differs from the one before it in one way; all exist in think1.py, seed 0, 4,000 steps, as in Addendum G):
- hloop (br's recipe, done): random lap counts per step (1 + Poisson(m - 1), capped at 6, ramped), no injection, answer loss after the
  last lap.
- hloopi = hloop + re-injection (W, as hloops). Needs only the answer. Its control is hplain (seed 0, reused: hloopi's lap schedule is
  hloop's, so the compute match holds; W adds a hidden x hidden matrix, about 1M trained parameters that hplain lacks).
- hloopd = hloopi with lap counts tied to depth (depth + U{0..2} per row, hops_plan) instead of random. Needs the depth. Its control
  is hplains (seed 0, reused; hplains was sized from hloops' plan with the extra read counted, so it gets slightly more compute than
  hloopd: a bias against hloopd).
- hloops = hloopd + graded laps (done). Needs the hop labels.

Runs, in this order, on Ben's PC (training is PC-only), each in a slot from the coordinator:
1. hloopi seed 0 (about 2 h). It runs whatever pair B's seed-1 result is: it tests the answer-only line.
2. Pair A's seed-1 replicate: hplain then hloop, seed 1 (about 3.5 h). Addendum G requires it before pair A counts as a result. It
   also runs whatever pair B's seed-1 result is.
3. hloopd seed 0 (about 4.5 h), only if pair B's seed-1 replicate passes (it takes hloops apart, which only matters if hloops holds).
4. Fresh rows, scored once (Addendum G), after the run they depend on: pair B's arms (hloops, hplains; seeds 0 and 1) once pair B
   seed 1 passes; pair A's arms (hloop, hplain; seeds 0 and 1) once pair A seed 1 passes; each round-2 arm that passes, with its
   control. Looped arms at r = 1-12 with answers and log-probs kept; plain arms one pass. The same marks are recomputed on fresh
   rows, by the same functions. A mark that passed on validation and fails on fresh rows is reported as "did not hold on fresh rows",
   and no claim rests on it. Every number told to Ben as a result is a fresh-row number.

Marks (validation rows, the same functions as Addendum G: paired row bootstrap, 2,000 resamples, 95%; near = depths 5-6; trained =
depths 1-4; the stop rule is Addendum G's answer-stable rule over r = 1-12 for every arm, fixed now; max-confidence is reported with no
mark, as a pick rule that runs all 12 laps)
- Validity: the reused controls already passed V1 and V2 at seed 0. For seed 1, pair A's V1 and V2 apply unchanged (hplain seed 1).
- Installed: hloopi at r = 6, and hloopd at r = depth, on the trained depths >= 80. Else NOT INSTALLED (not a refutation).
- For X = hloopi (control hplain) and X = hloopd (control hplains):
  - F1 (works at fixed laps): near, X at r = 6 minus control >= +5, interval above 0. Proved wrong below +1.
  - F2: trained, X at r = 6 minus control >= -2.
  - S1 (stops by itself): near, X under the stop rule minus control >= +5, interval above 0. Proved wrong below +1.
  - S2: trained, X under the stop rule minus control >= -2.
  - S3: Spearman(depth 1-6, laps chosen by the stop rule) >= 0.5, with the 2,000-resample row-bootstrap interval above 0.3. Proved
    wrong at <= 0.1.
  - WORKS = F1 and F2. STOPS ITSELF = S1, S2 and S3.
- Pair A seed 1 (hloop vs hplain): Addendum G's A1-A3, unchanged. New marks, fixed now, read at seed 1 only (seed 0 was seen):
  - A4: near, hloop under the stop rule minus hplain >= +5, interval above 0. Proved wrong below +1. (Seed 0, not a test: +28.12.)
  - A5: trained, hloop under the stop rule minus hplain >= -2. (Seed 0: -0.06.)
  - A6: Spearman(depth 1-6, laps chosen by the stop rule) >= 0.5, interval above 0.3. Proved wrong at <= 0.1. (Seed 0: 0.43.)
  - Pair A REPLICATES = A1, A2 and A3 at seed 1. STOPS ITSELF = A4, A5 and A6.
- One-change readouts (no mark; paired intervals on the same rows, seed 0): hloopi - hloop (injection), hloopd - hloopi (laps tied to
  depth), hloops - hloopd (graded laps), each at r = 6 and under the stop rule, on near and far, plus their Spearman values and laps
  by depth. The W = 0 lesion and |W| for hloopi and hloopd.

Decisions (fixed now):
- hloopi STOPS ITSELF: injection is what br's recipe lacked, and it needs no extra labels. It is the candidate for the assistant.
  Next: hloopi seed 1 (and hplain seed 1, if pair A's replicate has not run it) before any claim, then its fresh rows.
- hloopi WORKS but does not stop itself: injection alone does not give an online stop. Read hloopd (if it runs).
  - hloopd STOPS ITSELF: laps tied to depth, not graded laps, give the stop, but real data has no depth. Next (a new addendum): a lap
    count the model can set without depth labels, e.g. a curriculum that adds laps only while the answer loss still falls.
  - hloopd does not stop itself (and pair B seed 1 passed): the graded laps give the stop, and real data has no hop labels. Next (a
    new addendum): a trained stop signal that needs only the answer (a halting head trained on the model's own lap-by-lap
    correctness, PonderNet-style), on hloop or hloopi.
- hloopi does not WORK (F1 fails): with W, br's recipe loses its fixed-lap gain on this bed. Proved wrong (F1 below +1) means
  injection hurts here; else not shown. Either way, the stop-signal addendum above runs on hloop.
- Pair A REPLICATES: br's fixed-lap result holds on two seeds. If it also STOPS ITSELF at seed 1 (not expected from seed 0), the
  stop-rule question for hloop is reopened before anything moves to the assistant. If pair A does not replicate, no claim rests on
  pair A, and the village reading of Addendum G's pair A decision waits for a seed-2 run.
- Nothing moves into the assistant until one answer-only recipe both REPLICATES its fixed-lap gain and STOPS ITSELF on two seeds,
  with fresh rows. Until then, the assistant keeps no loop.

Known biases and limits, stated in advance:
- The stop rule was fixed after seeing seed 0's stop-rule numbers for hloop and hloops, but before any hloopi, hloopd or seed-1
  pair A run. Seed 0 of pair A is excluded from A4-A6. The rule is Addendum G's own, not one tuned here.
- hloopi and hloopd are seed 0 only. A round-2 pass is a lead until seed 1 agrees.
- hloopi has about 1M more trained parameters than hplain (W); hloopd's control gets slightly more compute than hloopd.
- The one-change readouts compare arms trained on the same batch stream; they are not compute-matched to each other (hloopd and
  hloops run more lap passes than hloop and hloopi).
- Max-confidence numbers are reported but never marked: as a pick over 12 laps it costs 12 laps on every row, which does not meet
  Ben's aim (deciding how much thinking to spend).
