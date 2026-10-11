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

## 13. Addendum F (Sat Oct 10, 9:15 PM ET, before any GX run): seed 400 may start now, beside G1's two 10M runs

- **Ask:** Ben, 8:23 PM ET: "Can you move that to the front of the queue?" GX was already first after G1. The coordinator's default: start
  it now beside G1's two 10M runs if it fits on the card and does not badly slow G1; never stop or restart G1.
- **The card now (shown, PC read 8:28 PM ET):** 82% busy, 12,342 of 16,303 MiB used, so 3,961 MiB free; G1's two B2 processes hold 5,398
  and 6,190 MiB, 82 MiB shared each. 10M s400 B2 at update 12,000, s401 B2 at 6,500, each about 3,210 s per 500 updates.
- **What runs:** `custom_io/queue_local/gx-share/gx_share.ps1` sets up `src-8gxs` (this branch; the only code change since c1464d19b7 is an
  opt-in memory cap in `train.py`, `CUSTOM_IO_MEM_CAP_MIB`, which does nothing when unset; test_moe ALL OK), then starts
  `gx-share/8aGXs400-pc.txt` if at least 3,500 MiB are free and G1 still runs. Same job name and results folder as the chain's 8aGXs400
  (`WORK\results\8aGXs400-pc\8aGX-3M-s400`), so analyze_gx reads it as usual and the chain's own launch skips it once it is done.
- **Differences from the planned run (disclosed; no mark changes):** accumulation 8 instead of 4 (the spill rule's first step: the same 256
  rows per update, split into 8 passes of 32 rows; the loss is the mean of 8 pass means instead of 4, and the balancing nudge, which runs
  after every pass, moves 8 times per update instead of 4); this run's PyTorch memory capped at 2,800 MiB; the GPU is shared, which changes
  speed only. G-B2's controls stay G1's own 3M runs at accumulation 4.
- **Stop rules (stop GX only, never G1):** shared GPU memory of the python processes more than 400 MiB above its level before GX, or the
  card's dedicated memory above 16,000 MiB, on 2 checks 60 s apart; or a G1 B2 arm still training going more than 4,300 s since its last
  500-update line (1.35x its shared pace; it fires mid-stretch, before G1's own share watcher's 5,000 s rule could stop G1 seed 401). A
  stopped or failed GX folder is renamed aside (never deleted), and the post-G1 chain then runs GX seed 400 alone after G1, exactly as before
  this addendum (accumulation 4, src-8gx).
- **Gain (suggested, untested):** it depends on GX's speed while sharing. Waiting means G1 ends about Mon 10-12 midday ET and GX alone takes
  about 10-12 h. Sharing helps if GX runs faster than about 7 s per update while G1 runs, and it speeds up as G1's arms finish. GX's pace
  after its first 1,000 updates decides whether it keeps running.
- Marks X1-X5 and D1-D5, the seed-401 rule (addendum E) and stage 2 unchanged.
- **Launch record (shown, PC logs).** The 8:50 PM ET launch failed after 1.3 min (arm_failed): the memory-cap call got a bare
  `cuda` device with no index. Fixed in 9e2dd5f9a1 (int index). Relaunched 9:01 PM ET from a re-unpacked src-8gxs (old one renamed
  aside), code folder `8aGXs400-pc-27397d06ea`. The card went from 12,341 to 15,067 MiB used (GX about 2.7 GB; about 1.2 GB left
  free), and shared GPU memory went from 164 to 246 MiB (rule 1 limit 564). G1 was at B2 update 12,500 (s400) and 7,000 (s401).
- **Result of sharing (shown, PC logs): stopped by rule 2 at 10:06:50 PM ET.** GX ran 1,000 updates at 2.97 s per update (1,000 at
  2,970 s), but G1 slowed too much. G1 seed 400's B2 stretch from update 12,500 to 13,000 took 4,432 s, against 3,201-3,224 s for its
  three stretches before GX. That stretch includes about 400 s before GX started and about 110 s after it stopped, so with GX running
  G1 seed 400 went at about 9.3 s per update instead of 6.45 (about 1.44x slower; inferred from those times). The watcher stopped only
  the GX processes. It renamed the job folder to `8aGX-3M-s400.share-stopped-20261010-2207` (kept, not deleted), and the card went back
  to 12,348 MiB used. Seed 400 now runs alone in the post-G1 chain, as first planned. Lesson: on this card, 82-86% busy with two 10M
  runs, a third process takes GPU time from both runs. It does not just fill idle gaps, even though memory fit.

## 14. Addendum G: stage 1 on two rented RTX 5090s, both seeds at once (written 2026-10-11 about 02:30 UTC, 10:30 PM ET 10-10, before any box result)

- **Why:** Ben (10:16 PM ET): "how much money would it cost to have the many experts and layers run its test? It would have until 7am tomorrow",
  then (10:19 PM ET): "i just need it by tomorrow at 7am. So if there's a cheaper option, go with that". Sharing the PC failed (addendum F),
  and the PC is busy with G1 until about Monday midday. The cheapest setup that gives the full 2-seed readout by 7 AM ET Sunday is two rented
  RTX 5090s, one seed each. One box doing all four runs would likely not finish in time. The cheaper one-seed option cannot give GO (addendum E).
- **Runs:** box A has seed 400 and box B has seed 401 (`custom_io/queue/gxA`, `gxB`, `custom_io/box/gx_box.sh`). Each box trains GX-3M
  (`{"eg_embed": true, "experts": 52, "top_k": 8}`) and G-B2 3M (`{"eg_embed": true}`, G1's flags) side by side. Both use arms B2 only,
  accumulation 4 (the spec's setting, as both G1 3M controls), the same code commit and the same rebuilt data (`get_data` with the
  manifest hash the PC uses).
- **Judged control:** this changes, as the project's same-machine rule requires (custom_io/PASS-MARKS.md addenda 10 and 11). X1-X3 compare
  GX with **G-B2 trained on the same box and seed**. G1's PC G-B2 3M of each seed is reported only, as a device check (box G-B2 minus PC
  G-B2).
- **Unchanged:** marks X1-X5, readout, proved-wrong line and hair rule. X5's spill part is n/a (32 GB card). The seed-401 rule (addendum E)
  is waived only because the deadline does not allow waiting. Its logic still holds for the reading: one seed alone is never GO.
- **Cost (prices checked live 10:17 PM ET: 5090 from $0.44/h):** about $4-5 expected (untested estimate). Each box stops every job after
  6.5 h (MAXH) and is destroyed after its results are collected. The hard cap is about $7 for both.
- **Speed (estimate, untested):** GX did 2.97 s per update sharing the PC (about 1.2-1.5 s alone, inferred). A 5090 ran EGW about 4x the
  PC (shown, PASS-MARKS.md addendum 11), so each box should take about 3-4 h of training plus about 45 min of setup. If the first 500
  GX updates project an end after 6 AM ET, the control moves to a third box.

## 15. Addendum H: stage 1 result (written 2026-10-11 about 09:00 UTC, 5:00 AM ET, after both box runs; marks unchanged)

**Shown** (`custom_io/results/gx-box/`, `python -m custom_io.g8a.analyze_gx --results custom_io/results/gx-box`; pooled-5, same-box pairs):

| Seed | G-B2 3M (box) | GX-3M (box) | GX minus G-B2 | X2 chain-5 | X3 | X4 even use |
|---|---|---|---|---|---|---|
| 400 (box A2) | 72.55 | 70.93 | **-1.62** | 99.9 ok | +15.5 ok | fail (block 1: 2 unused, top 3.5x; block 2: 4 unused, top 4.3x) |
| 401 (box B) | 73.25 | 72.05 | **-1.19** | 100 ok | +22.2 ok | fail (block 1: 2 unused, top 4.4x; block 2: 2 unused, top 4.0x) |

- **Readout by the marks: UNCLEAR.** X1 misses on both seeds (2-seed mean -1.41). STOP and "proved wrong" need X4 to pass, and it
  failed on both seeds ("experts not evenly used", so it cannot be GO). Stage 2 (GX-10M) does not start.
- **Where GX lost (shown, in_dist rule families, mean of 2 seeds, GX vs G-B2):** seq_next 36.3 vs 51.3, rule_apply 45.0 vs 62.5,
  cipher_map 66.3 vs 80.0, order_chain 75.0 vs 85.0. Splits: in_dist 84.4 vs 87.3, answer 70.0 vs 71.9, variant 35.8 vs 33.9.
- **Even use (suggested, not judged):** while training on the mixed rows (38% questions, 62% web fill-in), use was even at the end.
  Busiest expert 1.40x / 1.26x an even share, least used 0.66x / 0.77x, inside X4's band (training-log `moe_top` / `moe_low` at
  update 24,000, which are not per-block). X4 is measured on dev question rows only, where use is uneven. The likely reading
  (inferred) is that experts specialised by kind of row, not that the balancing failed. That does not change the X4 result.
- **Device check (reported):** box G-B2 minus PC G1 G-B2 = 72.55 - 73.0 and 73.25 - 73.7, about -0.45 each. The PC values are G1's
  reported 3M scores, assumed to be the same pooled-5 metric.
- **Cost and time (shown):** $6.19 of Vast spend (account total). Box B ran about 5.6 h; box A stalled and was replaced after
  37 min (about $0.31). GX trained at 1.26 updates/s against G-B2's 1.46 while the two shared each card (5.3 h against 4.6 h).
- **PC queue:** the post-G1 chain's GX runs are skipped (GX-ON-MAC.txt, as agreed with the roadmap thread). They would only repeat
  this result.

## 16. Addendum I: stage 2 runs on Ben's word after the UNCLEAR stage 1 (written 2026-10-11 about 12:20 UTC, 8:20 AM ET, before any stage 2 run)

- **Why:** section 5 says that on an UNCLEAR stage 1, "Ben decides with one word". Ben, 8:08 AM ET 10-11, after reading the stage 1
  result: "wait what? For the many experts many layers, I wanted both to be true during the same time". This is taken as his go for
  stage 2 (GX-10M: G-B2 10M's 8 blocks with the same 52-expert, top-8 layers). His standing rule (8:50 PM ET 10-10) is not to ask him
  for OKs.
- **Where (default, free):** BensPC, first in the roadmap thread's post-G1 chain, after G1's 10M runs end (about Monday 10-12 midday ET).
  Queue `custom_io/queue_local/8aGXD-pc.txt`: seeds 400 and 401, arms B2, accumulation 16 and MEM as G1's 10M B2, re-set from G1's
  measured 10M memory before release. Same code tree as the PC's GX setup. The spill rule is unchanged. If Ben says "rent" instead, the runs move to two
  rented 5090s, each with a same-box G-B2 10M twin as in addendum G (estimated $25, up to $35; untested). The PC runs then do not start.
- **Judged controls (PC):** G1's own PC runs on the same seeds: G-B2 10M (`8aG1f-10M-s400`, `8aG1s401-10M-s401`) for D1, D3 and D4,
  and G-PT 3M / 10M for D2. Same device, so no twin is needed.
- **D2 uses GX-3M, which only ran on the rented boxes.** The device check in addendum H measured box minus PC at about -0.45 on both
  seeds, which would favour D2. D2 is therefore computed twice: once raw, and once with GX-3M raised by that seed's measured box-minus-PC
  G-B2 3M gap (+0.45, +0.45). D2 passes only if both pass. This is fixed now, before any stage 2 score.
- **Unchanged:** marks D1-D5, readout (GO / STOP / UNCLEAR), proved-wrong line, hair rule (at most one use per stage). The seed-401
  rule (addendum E) applies: seed 401 runs only if seed 400 can still reach GO.
- **Prediction (suggested, written now): STOP or UNCLEAR.** Stage 1 lost at the same work (-1.41 mean), and the 8a dense results gave
  little gain from more stored weights. What would prove the prediction wrong: D1 >= +1.0 on both seeds with D4 (even use) passing.
- **Hours (estimate, untested):** G1's two 10M B2 runs shared the PC at about 6.4 s per update each, so about 3.2 s alone (inferred).
  GX-3M ran 1.16x G-B2 3M's time on the 5090; at 10M the thinker is a larger share of each step, so 1.2-1.6x is assumed. That gives about
  25-34 h per seed and 2-3 days for both.
