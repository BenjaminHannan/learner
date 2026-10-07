# Stage 8a: is bigger better for our design? Spec and pass marks

Sealed before any 8a run (written 2026-10-07, about 1:15 PM ET). Changing a mark after the first run needs a dated
addendum that says why, and it cannot use any 8a result.

Labels: **shown** = measured in this repo; **suggested** = reasoned; **untested** = a plan or guess.

Asks this answers:
- Ben, 3:43 PM ET 10-06: ship "at least hundreds of millions", "big enough where the scaling up is beneficial".
- Ben, 8:57 PM ET 10-06 (card): yes to free human-written web text, after a 13-gram overlap check against sealed tests.
- Ben, 10:48 AM ET 10-07: "as deep as possible".
- Ben, 1:05 and 1:06 PM ET 10-07: "Just get more words then." "then just get more words for our model and make our
  model bigger."
- Ben, 1:08 PM ET 10-07 (card, relayed): "Rent GPUs" for the growth ladder, about $30-50, after the overlap check.
- No-hard-coding thread (relayed): train the plain LLM-style transformer on the same web pool at every rung, and add
  U0's prompt-BPE variant once U0 has run.

## 1. The one change

Size, with the data growing in step. Everything else stays as it is today:
- **Design:** today's B2 (calculator inside the loop, 8 fixed rounds, copy talker). Ben's design changes (2c1 learned
  numbers, 2c2 calculator as a tool, 2d learned stop) are tested separately at 3.3M and are not in 8a. So 8a measures
  whether today's design scales (disclosed). If 2c/2d pass, their design repeats the 10M rung on 2 seeds before 8c,
  to show it scales the same way (proposed).
- **Reader:** stage 2b's winner from q39. EGE (EmbeddingGemma 2 in front of the letter window) if its 6-seed confirm
  passes `custom_io/PASS-MARKS.md` addendum 15; otherwise today's letter reader. It is recorded in the run manifest
  before the first run and never changes inside 8a.

## 2. Rungs and shapes (depth first, Ben 10:48 AM ET)

Trained parameters = every weight that gets gradients. A frozen EmbeddingGemma, if used, is reported on top (whole
size), and every arm that is compared with B2 gets the same frozen front.

| rung | trained params | B2 shape | plain shapes |
|---|---|---|---|
| 3M | today's B2: 3,302,481 (shown, q33) | width 256, 2 blocks, 2 reader layers (today's S) | width 256, layers set to match B2 within +-2% |
| 10M | 10.0M +-5% | width 256, blocks added until the target (about 10-12, suggested) | width 256, layers to match +-2% |
| 30M | 30.0M +-5% | width 384, blocks added until the target (about 14-16, suggested) | width 384, layers to match +-2% |

- A parameter counter asserts every band before any run; a run outside its band does not count.
- Init: B2's existing depth-scaled init (std 0.02 / sqrt(3 x blocks x rounds), `ledger.py`). Plain arms use their
  existing init.
- **Depth check, reported, not gated (10M, 2 seeds):** B2-M as it exists today (width 384, 3 blocks, 10,814,968) on the
  same data, beside the deep 10M. If deep is behind on both seeds, Ben hears before the 30M rung.

## 3. Arms (per seed, all arms run on the same rented box)

- **B2:** questions plus web text as fill-in-the-blank rows (section 4).
- **PT, plain_tf_steps (gate baseline):** same width, same reader front as B2 (EmbeddingGemma included if 2b picked
  EGE), same rows, writing its steps as in q33. It was the hardest same-size baseline (B2 led it by +6.9, shown).
- **LLM, the plain LLM recipe (reported, not gated):** a plain causal transformer of the same trained size reading
  letters, with no borrowed parts. It is trained with a next-word loss on the raw web text, plus the same question rows
  written as text with the loss on the answer (and on the steps, as plain_tf_steps does). It sees the same word pieces.
  Its whole size is reported beside B2's.
- **LLM-BPE (reported, added later):** the LLM arm with U0's prompt BPE (`/mnt/project-files/no-hardcoding/
  INPUT-UNITS-2026-10-07.md`), added at each rung that has not started yet once U0 reports.

## 4. Data

- **Unique pool per rung:** 20M / 60M / 190M word pieces (GPT-2 count), nested, so each rung's pool contains the one
  below it. Manifests are hash-stable (`data_pool/web_slice.py`, PR #47).
- **Fixed mix at every rung, so size stays the one change:** 38% our own text (generator rows plus TEACH), 62% web text
  (FineWeb-Edu sample-10BT, grade 12 and below). Own text per rung: 7.6M / 22.8M / 72M. Today there is 14.3M (shown,
  PR #47), so the 10M and 30M rungs need more generator rows first (data plan step 3, at most 10% duplicates).
- **Web text into B2 and PT:** fill-in-the-blank rows built by a script from the human-written text, never by a model.
  A chunk of up to 280 letters has one word of 3-12 letters, drawn uniformly, replaced by a blank mark. The answer is
  that word. Rows where the word also appears elsewhere in the chunk are kept, and their share is reported. Every
  B2-vs-PT comparison sees identical rows in the same order per seed.
- **Web text into LLM:** the same chunks as raw text with a next-word loss.
- **Seen:** 20 word pieces per trained parameter: 66M / 200M / 600M, about 3.3 passes; no row more than 4 times.
  (Changed by addendum B1: at least 24,000 updates of 256 rows; 3M and 10M share the 60M pool and rows. Cloze sizes
  changed by B2.)
- **Overlap gate:** every web document passes `overlap13.py scan` against all panels, the protected panels' hashes
  included, before it enters a pool (changed by addendum A1: the protected panels may join the index after 8a starts).
  Generator rows rely on their existing hold-out splits; their 13-gram result is
  reported, not gated (PR #47 suggestion, adopted).
- **Never trained on:** the dev splits behind pooled-5, chain-5, B1's 12 new kinds, FRESH-EN-R3, bAbI, ARC-Easy,
  GSM8K, and every protected panel. Nothing is ever scored on GOLD-PRIVATE.

## 5. Training

- As q33: AdamW, bf16, batch 256 rows, copy talker on. Updates = seen word pieces / (256 x mean row length).
- Learning rate: 1e-3 at 3M and 10M (width 256), 6.7e-4 at 30M (width 384; 1e-3 x 256/384). Every arm at a rung uses
  the same value. If any arm goes non-finite, every arm at that rung re-runs once at half the rate (disclosed). A second
  failure counts as a failed run for that arm.
- Seeds 400-405 at every rung, paired across arms and across rungs by seed (same init seed and data order).

## 6. Machines and money (Ben's "Rent GPUs", 1:08 PM ET)

**Replaced by addendum C (Ben, 1:35 PM ET: run on the home PC). Kept for the record.**

- One rented 5090 per seed per rung. Each box runs B2, PT and LLM in sequence, then is collected and destroyed
  (`custom_io/box/vast.py collect` then destroy). Never touch boxes this stage did not start.
- **Caps per box (self-stop by hours; 3M changed by addendum B3 to $2.50, MAXH 5 h):** 3M $0.60 (MAXH 1 h); 10M $1.50 (MAXH 3 h); 30M $5.00 (MAXH 9 h).
  The depth check adds about $1.
- **Total cap: about $43** for the 18 boxes; expected about $25 (our estimate, could be off 2x; the 3M rung measures
  real speed and the 10M and 30M caps are re-set from it before they launch). Keep the balance at $1 or more.
- Order: 3M, then 10M, then 30M. **Stop rule:** if B2's 10M-minus-3M pooled-5 mean is below 0, stop before 30M and
  report, which saves about $30.
- The ~100M build (8c) is not covered by this budget and is asked separately after 8a passes.

## 7. Marks

Primary metric: pooled-5 (micro exact over dev in_dist + answer + frame + vocab + variant, 6,040 rows, as in
`custom_io/PASS-MARKS.md`). Differences are per-seed paired, mean +- t x sd / sqrt(n), n = 6.

**Pass needs all three, plus marks 4 and 5 in addendum A2 (good enough):**
1. **B2 grows.** B2's pooled-5 rises by >= +3.0 from 3M to 10M and from 10M to 30M, each with its 95% CI above 0.
2. **Its lead holds.** Mean (B2 - PT) at 30M >= mean (B2 - PT) at 3M - 1.0.
3. **Still ahead at 30M.** B2 - PT >= +3.0 on at least 5 of 6 seeds.

**Proved wrong:** B2's 3M-to-30M gain under +2.0 (flat, like PR #18), or its lead over PT at 30M under half its lead
at 3M.

**Guard:** B2's chain-5 >= 99 at every rung (the calculator path is intact).

**Reported, not gated:**
- B2's leak (loops:0) and donor checks at every rung, beside the 3M values. A leak at 30M more than 5 points above 3M is
  flagged, because the gain may then come from the reader.
- The LLM arm per rung, and B2 - LLM per rung. This answers the no-hard-coding thread's question: does the plain LLM
  recipe close the gap with more words?
- B1's 12 new kinds (384 rows) per arm, with b2t beside the 10M rung (10.9M, TEACH only, 2 seeds: new kinds pooled
  11.20, FRESH 22.92; PR #41 section 7).
- FRESH-EN-R3 per arm; bAbI at 30M; whole sizes with borrowed parts counted; GPU hours and dollars per arm.

**Diagnostic, 2 seeds at 30M:** B2 on a quarter of the unique pool with the same seen budget. If it scores within 1
point of the full pool, data variety, not size, is the limit, and the web share should rise.

**Predictions (written now, suggested):** B2 gains +3 to +6 per step. PT gains the same or less, so the lead holds.
The LLM arm gains most on FRESH and new kinds, where wording matters.

## 8. What happens next

- **Pass:** 8c, the ~400M build (thinker about 100M), asked first for money.
- **Fail:** do not grow. Fix data variety or the design first, then re-run.

## 9. Waits on

1. The reader pick (q39, on the PC; expected 9 PM to midnight ET 10-07).
2. ~~The protected panels' hashes merged into the overlap index.~~ No longer a wait (Ben, "Start now", 1:23 PM ET;
   addendum A1): the check runs in parallel and must pass before 8c.
3. Web slices from FineWeb-Edu shard 0, which is enough for all three rungs (0.46 of a shard is needed at 30M; PR #47).
4. More generator rows for the 10M and 30M rungs (own text 22.8M and 72M). The 3M rung needs 7.6M, which exists.
5. The build list below.
6. Vast credit: $9.18 at 1:09 PM ET. The 3M rung's cap ($3.60) fits now; 10M and 30M need Ben's top-up.

## 10. Build list (implementation)

- `cloze.py`: fill-in-the-blank rows from web slices, deterministic per seed, with the copyable share reported.
- Pool assembler: fixed mix, nested pools, manifest with hashes; asserts no row more than 4 times.
- Depth configs: B2 `blocks`, plain `layers`; the parameter counter that asserts section 2's bands.
- The LLM arm: raw next-word loss on text plus question rows as text.
- Box launcher: one box per seed per rung, arms in sequence, MAXH self-stop, collect, destroy.
- `analyze_8a.py`: section 7's marks, written and tested on fake numbers before any run.

## 11. Addendum A: good enough, start now, and the B3 switch (2026-10-07, 1:31 PM ET, before any 8a run)

No 8a run has started, so these add marks rather than change them, and nothing here uses an 8a result.

Asks this answers:
- Ben, 1:23 PM ET 10-07 (card, relayed): "Start now" on growing the model on web text before the test-leak check
  finishes.
- Ben, 1:23 PM ET 10-07 (no-hard-coding thread): "I need you to demonstrate scalability with a model that is good
  enough though. do u understand?"
- The no-hard-coding thread's stated default, told to Ben (he can override): grow B2 now, since it is the good one;
  switch to the all-learned B3 once B3 matches B2 at 3M.

### A1. Start before the protected-panel check (replaces section 9 item 2)
- 8a may train on web text before the protected panels' hashes reach the overlap index. Every web document still passes
  `overlap13.py scan` against every panel already indexed before it enters a pool.
- The protected-panel check runs in parallel and must pass before 8c starts. If it flags a web document 8a used, that
  document leaves the pool before 8c and the list is reported. 8a never scores on a protected panel, so its marks are
  unaffected, and no 8a checkpoint that saw a flagged document is ever scored on the panel it matched.

### A2. Good enough: two more marks (gated)
Starting point, today's B2 (q33, seeds 200-205, `results/33-pc-confirm-b2/*/RESULT.json`, shown): pooled-5 mean 74.0
(73.0 to 74.7); in_dist 90.5, answer 74.2, frame 87.7, vocab 87.4, variant 34.7. Same rows: plain_tf_steps 67.1,
plain_tf 53.7.

4. **Starts good (3M rung).** B2's pooled-5 mean >= 72.0, at most 2.0 below today's confirmed B2. If the web mix costs
   more than that, it weakened the model being grown: stop before 10M, report, lower the web share and re-run 3M.
5. **Ends good (30M rung).** B2 beats a real public model of about its whole size given the same practice: B2's
   pooled-5 >= the public model's + 2.0, paired by seed over seeds 400-405, with the CI lower bound above 0 (the form of
   PASS-2's sealed P2.pythia_ft mark). The public model is fixed now by the reader pick:
   - letter reader (B2's whole size about 30M): `EleutherAI/pythia-31m`;
   - EGE (B2's whole size about 30M trained plus EmbeddingGemma's frozen part, about 300M): `HuggingFaceTB/SmolLM2-360M`.
   - Practice: the same question rows B2 sees at 30M, in the same order and number of passes; the web fill-in rows are
     left out (it was pretrained on web text). Fine-tuned with `custom_io/hf_baseline.py --mode finetune` at its
     default lr 1e-4, trained to write the steps and then the answer exactly as plain_tf_steps does (`target_text`),
     scored on the text after the last '#'. No calculator. Runs on the same box as that seed's 30M arms. Whole sizes
     printed side by side.

**Proved wrong (good enough):** B2's 30M mean below the public model's. Then the design being grown is not yet good
enough at that size, and Ben hears before 8c.

**Reported beside mark 5:** the same public model with a calculator (exact results forced in after "a op b =", as
plain_tf_steps' `calc` lesion); SmolLM2-360M and Qwen3-0.6B 8-shot with no training, run once on our own machines;
every split per rung beside today's values above, variant (the unpractised sub-task, B2's weak spot at 34.7) first.

**Money:** pythia-31m adds about $0.10 per 30M box; SmolLM2-360M about $1 per box (estimate, re-set from the 3M rung's
measured speed). With EGE, the 30M cap per box rises from $5.00 to $6.50 (MAXH 12 h) and the total cap from about $43
to about $53; expected about $30. With the letter reader, caps are unchanged.

### A3. Which design grows: B2 now, B3 when it is ready (stated default, Ben can override)
- 8a grows B2, because it is the model that is good today (+20.3 over plain_tf and +6.9 over plain_tf_steps, 6 of 6
  seeds, shown).
- When B3 passes its 3M confirm (`/mnt/project-files/no-hardcoding/PLAN-AND-MARKS-2026-10-07.md` section 3c, which
  includes parity with B2), B3 joins every 8a rung that has not started, as one more arm on the same boxes. So that size
  stays its one change too, B3 also runs every finished rung on the same pools, seeds and marks, with marks 1-5 read with
  B3 in B2's place. Those catch-up boxes need their own money ask.
- 8c builds the design that passed 8a, and B3 if both pass (Ben's no-hard-coding rule).

### A4. Build list additions
- `hf_baseline.py`: a steps target (plain_tf_steps' `target_text`, scored after the last '#') and the calc variant.
- Box launcher: the public-model arm at the 30M rung; the HF weights pinned by revision in the run manifest.
- `analyze_8a.py`: marks 4 and 5 and the good-enough proved-wrong line, tested on fake numbers before any run.

## 12. Addendum B: enough training, rows that fit, speed first (2026-10-07, 1:40 PM ET, before any 8a run)

No 8a run has started; nothing here uses an 8a result.

Asks this answers:
- Ben, 1:27 PM ET 10-07 (project chat, relayed): "demonstrate ability to improve with scalability and you can spend the
  gpu money".
- Coordinator (relayed): if the reader pick is the only thing holding the 3M rung, start it on plain B2 and disclose it.

Why: checking the spec against the code and today's runs found three things that would have spoiled the test.
1. **Too little training at 3M.** Section 4's 20 word pieces per parameter gives the 3M rung about 7,000 updates of 256
   rows (estimate: mean row about 38 word pieces), against q33's 24,000. Short training hides size: at 8,000 updates
   the 10.8M plain transformer scored below the 3.2M one (pooled-5 45.5 vs 47.0), and at 24,000 it scored above
   (54.9 vs 52.7) (`custom_io/CALIBRATION.md`, `results/01-calib`, `02-calib-long`, one seed, shown). Mark 4 compares
   with q33's B2, which had 24,000.
2. **Rows that do not fit.** B2's data code asserts prompts of at most 208 letters and answers of at most 8
   (`custom_io/data.py:107-109`, `MAX_PROMPT, MAX_ANS = 208, 8`). Section 4 allowed 280-letter chunks and 12-letter words.
3. **Cost.** q33's B2 took 3.66 h for 24,000 updates on the PC, 7.8x slower per update than plain_tf_steps (0.47 h)
   (shown). A deep B2 runs every block 8 times, so the deep rungs are likely far slower per update than section 6's
   estimate assumed (suggested; untested until timed).

Changes:
- **B1. Update floor.** Every arm at every rung trains for at least 24,000 updates of 256 rows (q33's recipe). Seen =
  the larger of that and 20 word pieces per parameter. So the 3M and 10M rungs train on the same rows in the same order
  per seed, from the 60M pool (about 3.9 passes, estimate), and the 3M-to-10M step changes only size. If the measured
  passes exceed 4, the floor wins at 3M and 10M and the count is reported (q33 itself made about 30 passes).
  The 3M rung now needs the 22.8M own-text prefix. 30M stays at 20 per parameter (about 600M, 190M pool).
- **B2. Rows fit B2.** ~~Cloze chunks are at most 200 letters including the blank mark; the blanked word has 3-8
  letters.~~ Withdrawn by addendum E2: the caps rise to fit the data instead. Every other section 4 rule stays.
- **B3. Speed first.** Before the 3M rung, one rented 5090 times 200 updates of each arm at the 3M, 10M and 30M shapes
  (about $0.20, reported). The 3M cap per box becomes $2.50 (MAXH 5 h); the rung is expected near $10 at $0.49/h. The
  10M and 30M caps are set from the timing. If the ladder's total would pass $50 (Ben's card: about $30-50), Ben gets the
  measured cost and the options before those rungs start.
- **B4. If the reader pick is the only wait.** If the code, web slices and own text are ready before q39 reports, the 3M
  rung starts on the letter reader, and 8a keeps the letter reader at every rung (recorded in the manifest before the
  first run; mark 5's public model is then pythia-31m). If EGE passes q39, it is checked inside 8a as one extra reported
  arm at the 10M rung (B2 with EGE, 2 seeds, same rows), which informs 8c's reader. Disclosed.

Vast credit at 1:37 PM ET: $8.92, with one box from another thread running (not ours). The speed check and the 3M rung
(cap $15) need Ben's top-up.

## 13. Addendum C: run 8a on the home PC (2026-10-07, 1:45 PM ET, before any 8a run)

No 8a run has started; nothing here uses an 8a result.

Ask this answers: Ben, 1:35 PM ET 10-07 (project chat, relayed): "can you just use the home gpu for this?"

Changes (they replace section 6 and the money lines in addenda A2, B3 and B4):
- **Machine.** Every 8a run is on BensPC (RTX 5070 Ti, 16 GB), through `custom_io/local_runner.py` queue files
  (`custom_io/queue_local/`, `# MEM` lines, `{WORK}` paths). No Vast unless Ben asks again. All arms and seeds of a rung
  run on the PC, so pairs share a device. The Mac runs only the report-only 8-shot public-model evals (SmolLM2-360M,
  Qwen3-0.6B), once.
- **Data on the PC.** The PC cannot read the project's shared files. It rebuilds the pools with the same scripts
  (`web_slice.py` on FineWeb-Edu shards 0-1, the generators for own text, `cloze.py`) and checks every manifest hash
  against the data-pool thread's manifests before training. A mismatch stops the rung.
- **Speed check on the PC (replaces B3's rented box).** The first job when the PC is free: 200 updates of each arm at
  the 3M, 10M and 30M shapes, printing seconds per update and peak GPU memory (about 20 minutes, our estimate).
- **16 GB at 30M.** If an arm's peak memory at batch 256 is above 15 GB, its batch is split into equal pieces with
  gradients added up before each update: the same 256 rows and the same number of updates, only slower (disclosed).
- **Order (default; the coordinator can move it):** speed check right after q39, then q40 (T1 screen) and U0 (short),
  then 8a 3M, then 8a 10M, then the T1 confirm if T1's screen passes. 30M waits for Ben (next point).
- **Time, estimated (suggested; the speed check replaces these):**
  - 3M, 6 seeds, all arms: about 9 hours. q33 ran the same 18-run shape at 3.3M on this PC, 3 at a time (shown).
  - 10M: about a day. B2-M (10.9M, 3 blocks at width 384) ran 16,000 updates in 39 to 44 minutes on this PC, 2 at a
    time (queue 35, shown); the deep 10M is 8 blocks at width 256 (10,254,105 with the copy talker, counted at 085431a7f;
    the plain match is 13 layers, 10,368,768), each run 8 times, so it is likely 2-3x slower per update.
  - 30M: about 4 to 5 days (about 62,000 updates at 20 word pieces per parameter, 15 or so blocks), plus about 2 days
    if the public model is SmolLM2-360M (its 6 fine-tunes). Before 30M starts, Ben gets the measured PC time and
    decides: run it on the PC, or rent for that rung only.
- **Stop rule unchanged:** no 30M if B2's 10M-minus-3M pooled-5 mean is below 0.

## 14. Addendum D: a fair plain baseline, and near-repeats in our own text (2026-10-07, 1:53 PM ET, before any 8a run)

No 8a run has started; nothing here uses an 8a result.

- **Why:** D0b (no-hard-coding thread, `/mnt/project-files/no-hardcoding/D0b-RESULT-2026-10-07.md`, shown) found that
  plain_tf_steps writes its steps only when steps plus answer fit in 64 characters (`plain_tf_steps.py:15, 21-27`).
  Longer rows are trained answer-only, which caused 58 of its 72 chain-5 misses. That handicaps the yardstick, not the
  plain recipe. The no-hard-coding plan's C0 (section 3.1, sealed) removes the cap (MAX_POS raised to fit), on seeds
  200 and 201 on the PC, right after q39.
- **D1. The PT arm follows C0's sealed consequence.** If C0's 2-seed pooled-5 mean is at or above plain_tf_steps', PT at
  every 8a rung is plain_tf_steps with C0's uncapped settings, and the LLM arm's question rows use the same uncapped
  steps target. Otherwise PT stays as written. Either way, the stronger yardstick is used, which only tightens marks 2
  and 3. C0's own runs are the 3M pair for the first look, so there is one fair plain run, not two.
- **D2. Near-repeats in our own text.** The data-pool thread measured 23% of own-text rows at 22.8M as the same problem
  with new numbers (target was 10% or less; it cannot drop without new kinds of questions). Accepted for 8a: every arm
  and rung sees the same mix, so it does not favour any arm. It can cap the gain from size, which the quarter-pool
  diagnostic (section 7) checks. The rate is reported per rung: 20% at the 7.6M prefix, 23% at 22.8M (3M and 10M
  rungs), 26% at 72M (30M rung) (data-pool thread, shown).

## 15. Addendum E: no caps that cut long answers (2026-10-07, 2:07 PM ET, before any 8a run)

No 8a run has started; nothing here uses an 8a result.

Ask this answers: Ben, 2:04 PM ET 10-07 (no-hard-coding thread, relayed): "I don't think you should have it cut off long
answers". The no-hard-coding plan made it a standing rule (PLAN section 2, b3832445e5).

- **E1. Caps fit the data, never the other way round.** In every 8a arm, every length cap is set to the longest case in
  that rung's training data: prompt letters and answer letters (`MAX_PROMPT`, `MAX_ANS`), plain arms' positions and
  step targets (`MAX_POS`, `CAP`), the LLM arm's context, and B2's program steps, prompt numbers and words (`N_RES`,
  `N_NUM`, `W_MAX` in `progparse.py:8`). No arm has an answer-only fallback. Today these B2 caps are fixed constants
  (7 steps, 16 numbers, 64 words), so this needs code (build list).
- **E2. Addendum B2 is withdrawn.** Cloze rows go back to section 4's sizes (chunks up to 280 letters, one 3-12 letter
  word) and the caps rise to fit them.
- **E3. Reported with every rung:** the caps used, and the number of training and dev rows any cap touches (target 0).
  Raising caps can change B2-S's parameter count slightly; the 3M rung reports it beside q33's 3,302,481, and mark 4
  still reads against q33's 74.0 (disclosed).
- **First look:** it keeps q33's exact recipe, caps included, so that size is its only change from q33. PT13-C0 already
  sets its cap to its longest target (107). The B2 rows that q33's caps touch (programs over 7 steps, prompts with over
  16 numbers or 64 words) are counted and reported with it.
