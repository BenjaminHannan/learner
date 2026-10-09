# Test GX: many experts in the thinker, then many layers (spec and marks, Fri Oct 9 2026, 10:45 AM ET, before any build or run)

Owner: thread "many experts with many layers" (Ben, 10:18 AM ET 10-09: "can you add first to queue trying many experts with many
layers?"). Ben's design approval 09-29: "do a sparse moe (however many active experts frontier models have) for our model, and add
many layers... even if its hard to train." Claims below are labelled shown / suggested / untested.

## 1. What came before (why this is not a repeat)

- **The deep-experts test of 09-29 never ran** (shown): its PC job stopped at the disk check (6 GB free), then was held.
- **The old main core's experts were dead** (shown, model audit 10-05): routers started at exactly 0 and experts 0 and 1 were exact
  copies, so no gradient could ever split them; experts 2-7 never trained. Lesson built in here: the router starts random (not zero),
  every expert starts from its own random draw, and a guard checks that experts are actually used.
- **The small side-by-side experts net (Test D, 09-28) was not promoted** (shown) on the maze race. Different model, different task.
- **No expert test has run on this thinker (B2).** The big run is dense by default (`FINISHED-MODEL-2026-10-09.md` item 10).

## 2. The one change

Each thinker block's feed-forward layer (Linear d -> 1,228 -> d at d = 256) becomes an expert layer:

- **52 experts, 8 used per token per round** (8 active is what DeepSeek-V3, Qwen3 and Kimi K2 use). Each expert is Linear d -> 154 -> d,
  so 8 experts hold 1,232 hidden units, the same work per token as the old layer (1,228).
- **Router:** Linear(d, 52) with no bias, on the same LayerNorm'd input, computed in fp32. Softmax over all 52, keep the top 8, rescale
  those 8 weights to sum to 8 (so with an even split each picked expert gets weight 1 and the layer starts out acting like the old layer
  cut into 8 pieces). Dropless: no token is ever skipped.
- **Balance:** the standard load-balancing loss (Switch Transformer: 52 x sum over experts of (share of picks) x (mean router
  probability)), averaged over every block and round, weight 0.01, added to the training loss and logged as `moe_lb`.
- **Init:** router N(0, 0.02); each expert's first layer N(0, 0.02), its output layer N(0, 0.02 / sqrt(3 x blocks x rounds)) as the dense
  layer's; biases 0. All expert weights are drawn after every other weight, so every weight the two models share starts identical at
  the same seed (same convention as the copy, span and Gemma switches).
- **The same blocks run every round** (12 rounds, as G-B2). The router sees the round's input, so different rounds can pick different
  experts. Nothing in the routing is hand-written; which expert handles what is learned.
- **On the PC every expert is computed and only the 8 picked are kept** (gates of the other 44 are exactly 0, so they get no gradient):
  the same answers and the same learning as computing only the 8, at extra wall time. Disclosed, not a design choice.
- Switch off (`experts` = 0, the default) is exactly G-B2: same weights at the same seed, same loss, same answers (unit test).

Everything else is G1's: code 612f5c5b01 + the caps.py fix (sha256 3da2dfbb), the frozen EmbeddingGemma 2 front, caps_g.json (36
registers, 12 rounds), the seed's pool and row order, 24,000 updates of 256 rows, lr 1e-3, AdamW (decay 0.1 on matrices only; expert
biases stored flat so they get none, as the dense biases), grad clip 1.0, bf16.

## 3. Sizes (shown, counted by the code at ad93c24259 for G-B2; GX by the formula, checked by the build's tests)

| model | blocks x rounds | trained, total | used per token per round ("active") | whole, with Gemma's 271.0M |
|---|---|---|---|---|
| G-B2 3M (G1) | 2 x 12 | 3,544,913 | 3,544,913 | 274.5M |
| **GX-3M** | 2 x 12 | **10,553,929** | **3,579,225** (+1.0%) | 281.6M |
| G-B2 10M (G1) | 8 x 12 | 10,496,537 | 10,496,537 | 281.5M |
| GX-10M (stage 2) | 8 x 12 | 38,532,601 | 10,633,785 (+1.3%) | 309.5M |

52 experts were picked so that GX-3M's total size equals G-B2 10M's (+0.55%). So stage 1 compares two ways at once, using runs G1
already makes: against G-B2 3M at the same work per question, and against G-B2 10M at the same total size (Ben's counting rule).
GX-10M is G-B2 10M's deep shape (8 blocks, "many layers") with the same expert layers.

## 4. Stage 1: experts on the small thinker (first in the PC queue after G1)

Runs: GX-3M, seeds 400 and 401, B2 arm only. Controls: G1's own G-B2 3M runs on the same seeds (`8aG1d-3M-s400`, `8aG1e-3M-s401`);
nothing is re-run. Metric: pooled-5 on the 6,040 dev rows (`analyze.P5`), paired by seed.

**Marks (fixed now).** Hair rule (MARKS-D0-T1 Amendment 10 item 1, Ben 10-08): a single-seed mark missed by no more than 0.5 point,
with every other mark passing on both seeds and the miss disclosed, counts as a pass on a screen.
- **X1 (experts help at the same work):** GX-3M minus G-B2 3M >= +1.0 on each seed.
- **X2 (chains):** chain-5 >= 99 on each seed.
- **X3 (thinker drives):** on each seed, (GX in_dist minus GX loops:0 in_dist) >= 80% of (G-B2 in_dist minus G-B2 loops:0 in_dist).
- **X4 (experts alive):** in every block, at most 5 of the 52 experts get under a tenth of an even share of picks (all rounds, the dev
  in_dist rows). A model that fails X4 is reported as "the expert layer collapsed": its score says nothing about experts either way.
  (One expert taking a big share is allowed: a learned "always-on" expert is not a collapse.)
- **X5 (trained cleanly):** status ok, finite loss, no shared-memory spill past the rule in section 6.

**Readout:** GO = X1-X5 pass. STOP = GX-3M minus G-B2 3M <= 0 on both seeds (with X4 passing). Anything else = UNCLEAR.
**Proved wrong** (for "experts help this thinker at the same work"): the 2-seed mean of GX-3M minus G-B2 3M <= -1.0, with X4 passing.

**Reported, not judged:** GX-3M minus G-B2 10M (same total size, a quarter of the thinker work); GX-3M minus G-PT 3M; every split and
family, the rule families above all (fewshot_number_rule, seq_next, order_chain, rule_apply) and cipher_map; training-loss parts and
`moe_lb`; routing per block and round (share per expert, unused experts, top share, entropy, how much the expert sets of different rounds
overlap); speed; peak memory; total, active and whole sizes.

**Prediction (suggested, written now): UNCLEAR or STOP.** In 8a, B2 gained little from 3x more dense weights (+0.49 over 6 seeds, with
the 8-letter bug), so stored weights do not look like this thinker's limit, and experts add stored weights, not work. What would prove
the prediction wrong: GO on both seeds, above all with gains on the rule families.

## 5. Stage 2: experts plus many layers (only after stage 1)

Runs: GX-10M, seeds 400 and 401. Controls: G1's G-B2 10M and G-PT 3M / 10M on the same seeds. Starts only if stage 1 is GO; on
UNCLEAR, Ben decides with one word; on STOP or proved wrong it does not run.

**Marks (fixed now, same hair rule):**
- **D1 (experts help when deep):** GX-10M minus G-B2 10M >= +1.0 on each seed.
- **D2 (Ben's bar, experts version):** (GX-10M minus GX-3M) minus (G-PT 10M minus G-PT 3M) >= +1.0 on each seed.
- **D3-D5:** X2, X3 and X4 at 10M (X3 against G-B2 10M).
**Readout:** GO = D1-D5 pass (then the big-run thread weighs a sparse thinker, with 6 seeds first). STOP = D1's difference <= 0 on both
seeds. Else UNCLEAR. **Proved wrong:** 2-seed mean of D1's difference <= -1.0.

## 6. Running it

- **Where:** BensPC (RTX 5070 Ti, 16 GB) only. No rentals, no paid compute. G1 is never stopped or slowed: stage 1 starts only after G1's
  last queue (`8aG1f`) prints done, and only with Ben's go in the Mac session.
- **Order asked for the PC queue:** G1 -> **GX stage 1** -> GX stage 2 (only on GO) -> token test TK (PR #56) -> G2.
- **Code:** a new folder on the PC from this branch; G1's `src-8ag` is never edited. CPU test `python -m custom_io.tests.test_moe` must
  print ALL OK there first.
- **Memory:** 3M at gradient accumulation 8 (32 rows per pass; G1 used 4), 256 rows per update either way (changes only bf16 summing
  order). Spill rule as G1 (8a-G addendum F): shared GPU memory past 1 GB -> stop, rerun with accumulation doubled, up to 32. Stage 2's
  accumulation is set from G1's measured 10M memory before it starts.
- **Hours (suggested, untested on GPU):** about 9 h per 3M seed (range 7-14 h), so about 18 h for stage 1. Stage 2 is set from G1's
  measured 10M speed; likely 1.5-2 days.
- **Results:** `results/8a-g/pc/8aGX-pc/` on branch `claude/8a-g-pc-results` (no checkpoints, unless the CPU-side copy is cheap).

## 7. What each outcome means for the big run

- Stage 1 STOP / proved wrong: the big run stays dense; experts drop off the list for this thinker (the deep version is not run).
- Stage 1 GO, stage 2 GO: the big-run thread weighs an expert thinker (needs 6 seeds and Ben's yes; the big run is dense today).
- Stage 1 GO, stage 2 not GO: experts help only the shallow thinker; dense stays for the deep big-run thinker.

## 8. Addendum A (Fri Oct 9, 10:40 AM ET, before any build finished or any run): Ben's "used about evenly"

Ben, 10:18 AM ET (project chat, right after his ask): "and ensure they get used about evenly". Changes, made before any run:

- **Design: a balancing nudge on top of the balance loss** (the method DeepSeek-V3 uses to keep experts evenly used). Each expert layer
  keeps 52 balancing numbers (one per expert, start 0). The router picks its 8 experts by score + balancing number; the weights given to
  the picked experts still come from the plain router scores, so the nudge changes who is picked, not how much they count. After every
  training pass, each block's numbers move by 0.001: down for experts picked more than average in that pass (all rounds), up for those
  picked less. The numbers change only while learning, never while answering, and are saved with the model (104 numbers at 3M, 416 at
  10M; not trained by gradient, so not in the trained counts; disclosed). The balance loss (weight 0.01) stays. Both are part of how the
  model learns; nothing is picked by hand at run time.
- **Mark X4 is replaced by (applies to D3-D5 too):**
  **X4 (used about evenly, and every expert trains):** in every block, over all rounds on the dev in_dist rows, every one of the 52
  experts gets between half and double an even share of the picks (an even share is 1/52 of picks, about 1.9%). Hair rule: on a screen,
  up to 2 experts per block may fall in [0.4, 0.5) or (2.0, 2.5] x even share if everything else passes; disclosed. An expert that is
  picked is an expert that gets gradient, so this also shows every expert trains. A model that fails X4 is reported as "experts not
  evenly used" and cannot be GO, whatever its score.
- **Measured and reported:** each expert's share per block and per round (dev rows); the training log every 500 updates (`moe_top` =
  the busiest expert's share x 52, `moe_low` = the least used x 52, `moe_lb`); the balancing numbers at the end.
- The old "one expert taking a big share is allowed" note is withdrawn: Ben asked for even use.
- Header time corrected: the spec above was written about 10:30 AM ET, not 10:45.

## 9. Addendum B (Fri Oct 9, 10:45 AM ET, before any run): one router per block, shared by the 12 rounds (design note; marks unchanged)

Question (coordinator, from Ben's 10-05 paper drop, Chain-of-Experts arXiv 2506.18945): its ablation found one router reused on every
loop pass plateaus worse than plain experts (loss only, one 544M model, 2 passes; weak evidence). GX does reuse each block's router on
all 12 rounds. **Choice: keep it shared.** Reasons: (1) the router is not blind to the round: B2 adds a learned round embedding into the
thinker state every round (`ledger.py:362`, `Z = Z + self.step_emb.weight[ts]`), and the router reads that state, so it can pick
different experts per round (shown in code); (2) one change at a time: per-round routers would be a second change and add 11 x 13,312
weights per block (+293k at 3M, +8% of the active count); (3) the paper's evidence is weak. The routing report already measures how much
the expert sets of different rounds overlap (section 4). If GX is GO but the rounds pick nearly the same experts, per-round routers are
the follow-up test, not a change to this one.

## 10. Addendum C (Fri Oct 9, 10:50 AM ET, after the build, before any run): memory, size check, hair reading, queue

- **Memory (shown on CPU, fp32, 32 rows, Gemma stubbed; `custom_io/g8a/moe_cost.py`):** computing every expert stores 2.72x G-B2's tensors for
  learning. The build now recomputes the expert step during learning instead of storing it (`moe_ckpt`, on by default; tested: same loss and
  exactly the same gradients). With it GX stores 1.035x G-B2's (0.85x without the weights). So **GX-3M runs at accumulation 4, the same as
  both G1 3M controls** (section 6's "8" is replaced), and GX-10M at 16, the same as G1's 10M B2. Spill rule unchanged (double, up to 16 / 32).
  CPU wall time GX / G-B2 = 3.7x with the Gemma reader stubbed; on the PC the real Gemma reader is a large share of each step, so the ratio
  there is smaller (untested). Revised estimate (suggested): 10-12 h per 3M seed on the PC, about a day for stage 1.
- **Size check (launcher refusal, not a mark):** a GX config passes if its dense twin (the same config with experts off) passes today's rung
  check and GX's active count is within 3% of that twin: GX-3M +0.97%, GX-10M +1.31%. (Comparing GX-10M with the 10.0M target directly, as
  the first build did, put it at +6.3%, outside the 5% band, because G-B2 10M itself sits at +5.0%.)
- **Hair reading, fixed before any score (`custom_io/g8a/analyze_gx.py`):** at most one hair use per stage across all marks. A 0.5-point
  single-seed miss is one use; one seed's X4 inside its hair band is one use. So a hair miss on X1 plus an X4 hair seed, or X4 hair on both
  seeds, is not a pass. X5's spill part is checked from the PC log by hand (it is not in RESULT.json).
- **Queue (staged, not started):** `custom_io/queue_local/8aGX-pc.txt` (stage 1, the two 3M runs), `8aGXD-pc.txt` (stage 2, held),
  card `8aGX-card.md`. Not before G1's last queue is done (no local_runner running; 8aG1s401, or 8aG1f) and Ben's go in the Mac session.
- Marks X1-X5 and D1-D5 unchanged.

## 11. Addendum D (Fri Oct 9, 11:45 AM ET, before any run): the Mac speed check; both runs stay on the PC

- **Shown (M1 Pro, 32 GB, MPS, fp32, torch 2.14.1; 100 updates of GX-3M seed 400 at accumulation 4, run by the Mac session):** step 50 at
  1,096.7 s, step 100 at 2,344.8 s, so **25.0 s per update** (the step-25 line was not logged). Peak memory footprint 9.4 GB, no errors.
  A full 24,000-update run would take about **6.9 days** on this Mac, against the 36 h limit set before the check.
- **Decision:** both stage 1 runs stay on the PC, in the shared post-G1 chain (`results/8a-g/pc-job-cards/after-g1/q8aPost_wait.ps1` on
  claude/project-thread-yha868: G1, then 8aGX, then 8aFC, then 8aC30). Nothing moves to a Mac, so no cross-machine disclosure is needed.
- **Suggested, untested:** the M3 Pro is unlikely to be 4x faster than the M1 Pro, so it does not fit a GX run either.
- The PC timing is still the section 10 estimate (untested); the card's 15-minute memory look will report the PC's real step speed.
- Marks X1-X5 and D1-D5 unchanged.

## 12. Addendum E (Fri Oct 9, 12:45 PM ET, before any run): run seed 401 only if seed 400 can still reach GO (roadmap thread's split; Ben's card)

- **The rule (proposed by the roadmap thread, which runs the PC chain; it goes to Ben on a card):** stage 1 is split into queues 8aGXs400
  and 8aGXs401 (same g8a lines, same job names). Seed 401 runs only if seed 400 has GX-3M minus G-B2 3M of at least +0.5 and X4 did not
  fail; `WORK\GX-S401-GO.txt` forces it.
- **Why it fits the marks (shown from sections 4 and 10):** GO needs X1 >= +1.0 on each seed with at most one hair use of 0.5, and an X4
  fail rules GO out. So below +0.5 on seed 400, or with X4 failed, GO is already impossible, and seed 401 could only tell UNCLEAR from STOP.
  Skipping it saves one PC run (about 10-12 h, suggested).
- **Reading when seed 401 is skipped:** "not GO after one run". Stage 2 does not run. The report gives seed 400's difference and X2-X5. It
  does not claim STOP or proved wrong, which need both seeds. `analyze_gx` (default seeds 400,401) already reads a missing seed as n/a and
  never as GO; with seed 400 below +0.5 it prints UNCLEAR, which this addendum reads as "not GO after one run".
- **Unchanged:** GO still needs both runs; marks X1-X5 and D1-D5; stage 2 rules.
- **PC install check (shown by the roadmap thread on BensPC, CPU):** `test_off_is_base` fails there because the PC's torch build draws
  different starting weights for the same seed (the first weight created already differs; the code is the same commit that passes on the
  cloud CPU). The installer runs the other 8 tests. Same-machine identity of GX's shared weights with G-B2's is still checked on the PC by
  `test_shared_weights_identical`, so the comparison with G1's PC runs stays like for like.
