# Sleep efficiency: where a night's steps go, and how to learn more per step (2026-10-25)

Labels: **shown** = measured in this repo or stated in a paper's abstract; **suggested** = follows from a measurement plus arithmetic or a
paper, not tested here; **untested** = an idea. All numbers below are from the simulated weeks (Week-1, Week-2), weights only, unless a
line says otherwise. Nothing here uses the village model or the small card experiments.

## Bottom line

- Training is 76-83% of a night. A step costs 0.39 s on an RTX 5090 for Qwen3.5-2B, and 1.30 s on Ben's RTX 5070 Ti, which is where
  the "1.4 s" figure comes from. K2 costs 0.66 s in bf16 and 0.83 s at 4-bit (shown, from the result JSONs).
- The steps are spread by fixed rules that do not look at what the model already knows:
  - every night after night 1 gets the full 1,200 steps at 4x;
  - REM always takes 11 of every 16 slots in its 510 steps, however small the REM pool;
  - items are drawn in proportion to how often they were mentioned.
- Two places look wasteful.
  - **REM over-practice (shown in counts):** on night 2 of the adopted run, the first REM dream was practised about 2,700 times. The
    average per dream was 255 on night 3 and 77 on night 4, against about 15 by night 7 and about 4-5 per ordinary card.
  - **Practice on cards already known (suggested):** before training, 61-77% of eligible facts are already answered right on nights
    4-7, and their cards keep being drawn.
- I added the measuring tool and five opt-in changes to `sleepb.py`. Every flag is off by default. Off is bit-identical to the old
  code (shown on CPU, below).
- First test: three cheap Qwen3.5-2B runs at 2x work, one control and two single changes. Each run takes about 35 min on a 5090. The
  question is whether "skip cards it knows" or "cap REM practice per dream" gets 2x work to the 4x recall.

## 1. What a night does today (read from the code and the logs)

Code: `backbone/sleep/brain/sleepb.py` (`Brain.night`, `Brain.nrem`, `Trainer`, `rem_plan`). Logs: `results_a9/result_ab_ob_b4_nb.json`
(the adopted recipe, seed 1) and the other result JSONs named below. All facts in this section are **shown**.

- **Steps per night:** min(300, 40 + 4 x active items) x s. At 4x that is 1,200 from night 2 to night 7 (the cap binds; nb has 71-147
  active items). Night 1 had 224.
- **Each step:**
  - 16 practice examples;
  - 8 generic replay prompts for the KL guard, two forward passes each (with and without the add-on).
- **Learning rate:** a fresh AdamW every night, with cosine from 2e-4 to 0 over the night and no warmup.
- **LoRA:** rank 16, alpha 32, on every attention, DeltaNet and MLP linear layer, for both Qwen and K2 (`train.LORA_TARGETS`; K2 uses
  the same module names).
- **NREM sampling:**
  - Facts right on 2 mornings in a row ("consolidated") get 25% of the slots.
  - The other 75% go to the remaining facts, drawn by priority = days mentioned x (1 + important + corrected) x (1 + wrong this
    morning) x (2 if it gave the old value).
  - Inside a fact, a card is drawn uniformly from its paraphrases (about 10) and Q&A cards (about 5.5).
  - Half of the Q&A draws are open-book (the diary-test prompt with the top-8 diary turns).
- **REM:**
  - 42.5% of steps (510 of 1,200 at 4x).
  - In a REM step, 11 of 16 examples come from the REM pool whenever it holds even one dream.
- **The morning probe** uses one held-out question per fact; it is never trained on. Before training, recall of eligible facts was
  0.05, 0.43, 0.61, 0.70, 0.76 and 0.77 on nights 2-7; after training it was 0.89-0.94.

Practice counts per night in the adopted run (arithmetic from the logged step counts, pool sizes and item counts):

| night | REM pool (end) | REM-pool examples | practices per REM dream (mean) | the oldest dream | active facts | consolidated | examples per active fact | per consolidated fact |
|---|---|---|---|---|---|---|---|---|
| 2 | 2 | 3,795 | **1,898** | **2,722** | 71 | 0 | 217 | - |
| 3 | 22 | 5,610 | **255** | 321 | 141 | 3 | 72 | 1,132 |
| 4 | 73 | 5,610 | **77** | 100 | 135 | 52 | 76 | 65 |
| 5 | 173 | 5,610 | 32 | 40 | 144 | 95 | 71 | 36 |
| 6 | 306 | 5,610 | 18 | 21 | 140 | 151 | 73 | 22 |
| 7 | 375 | 5,610 | 15 | 16 | 147 | 199 | 69 | 17 |

On night 2 the pool was empty for the first two cycles (sizes 0, 0, 1, 2 by cycle), so its first dream alone took 1,650 practices in
cycle 3. With about 15.6 cards per fact, an active fact's card is practised about 4-5 times a night. A consolidated fact's card is
practised about 1-4 times.

Other measurements:
- **Duplicate cards are rare.** Exact duplicates are already dropped (99-304 a night). Among the 20 example facts saved in the JSON,
  2% of paraphrase pairs and 0% of question pairs have word overlap (Jaccard) of 0.8 or more (shown, small sample).
- **Card yield:** about 49% of generated Q&A cards survive the checks, mostly lost to "bad answer" (shown, `dream_stats`). Paraphrases
  survive at about 85-90%.
- **Open-book cost (suggested, arithmetic):** the speed thread measured open-book prompts at about 346 tokens and a 16-example step at
  1,828 real tokens (`speed/qwen36_step/NOTES.md`, Qwen3.6 tokenizer). About 4-5 of the 16 examples are open-book on average, so they
  carry roughly two-thirds of the trained tokens. Whether step time follows tokens on the 2B is untested: on Qwen3.6 the GPU sat idle
  63% of a step (launch-bound).

## 2. Where sleep likely wastes effort

Each item gives what we know, its label, and the evidence from outside.

### a. Cards it already knows (suggested; biggest candidate)

- **Here:**
  - **Shown:** on nights 4-7, 61-77% of eligible facts are right before training starts.
  - **Shown:** those facts keep 25% of NREM slots once consolidated, and every fact keeps its share until it has been right twice.
  - **Not measured until now:** how many training examples were already answered right at the moment they were practised. That is
    what `--card-stats` records. A strong guess is that REM dreams are mostly known early in the week, given 77-2,805 practices each.
- **Outside:**
  - In people, once a word pair was recalled, more study of it "had no effect on delayed recall", but more testing "produced a large
    positive effect" (Karpicke & Roediger 2008, Science; abstract). This is an analogy only: a teacher-forced training step is not
    the same as a recall test.
  - Training on high-loss examples is a standard speed-up:
    - Loshchilov & Hutter 2015 report about 5x on MNIST (abstract).
    - Selective-Backprop skips the backward pass of low-loss examples, up to 3.5x faster (Jiang et al. 2019, arXiv 1910.00762;
      search summary).
    - RHO-LOSS trains "in 18x fewer steps" on Clothing-1M. It also warns that hard, high-loss points "are often noisy (not
      learnable)" (Mindermann et al. 2022, ICML; abstract).
    - Prioritized experience replay picks transitions by TD-error size and corrects the bias with importance weights (Schaul et al.
      2016, ICLR).
  - Brain analogue: hippocampal replay prioritised by "gain" and "need" (Mattar & Daw 2018, Nature Neuroscience; abstract).
- **Caution:** a 2023 paper is reported to find that Selective-Backprop did not beat random subsampling (arXiv 2312.05021). This was
  reported by the citation checker and not read.

### b. Duplicate cards (shown small; low priority)

- **Here:** near-duplicates are about 2% of pairs.
- **Outside (not our setting):** de-duplicated pretraining data needs fewer steps for the same accuracy and emits memorised text 10x
  less often (Lee et al. 2022, ACL; abstract). Duplicated data makes facts be forgotten faster (Chang et al. 2024, NeurIPS; abstract).
- **Verdict:** not where the time goes. Card variety is already being tested in addendum 15.

### c. Steps after the loss flattens (suggested: not the main waste yet)

- **Shown:** doubling the work still pays. 1x to 2x gave +14.5; 2x to 4x gave +9.0 and +12.5 (two seeds).
- **Shown:** the end-of-night loss is single-batch and noisy (0.03-0.27). It cannot reach 0, because paraphrase texts carry loss on
  every token.
- **Outside:** new facts are "learned significantly slower" than known ones (Gekhman et al. 2024, EMNLP; abstract). A late plateau
  may still hide slow learners.
- **Next:** `--card-stats` splits the known share by quarter of the night. If the last quarter is mostly known cards, a plateau stop
  becomes worth a test.

### d. The learning-rate schedule (untested)

- **Shown, arithmetic:** with cosine to 0, the average lr over a night is half the peak. The last 20% of steps run below 10% of the
  peak.
- **Outside:**
  - A constant lr plus a short cooldown matches or beats cosine in pretraining (Hägele et al. 2024, NeurIPS; from search summaries).
  - MiniCPM uses a warmup-stable-decay schedule (Hu et al. 2024; abstract).
  - LoRA+ gives the B matrices a larger lr than A and reports "up to ∼2X SpeedUp" and 1-2% better results "at the same
    computational cost" (Hayou et al. 2024, ICML; abstract).
  - The best LoRA lr is "consistently 10x" the full fine-tuning lr ("LoRA Without Regret", Thinking Machines blog, 2025).
- **The direction is genuinely open.** Our best whole-model lr was 5e-6, and 10x of that is 5e-5. That is below the 2e-4 we use, but
  that rule was found on general fine-tuning, not personal facts (untested here).

### e. Ordering and repetition inside a night (suggested)

- **Shown:** the REM rule gives each dream 77-2,805 practices on nights 2-4 (table above).
- **Shown:** priority grows with days mentioned, so a fact said on 4 days gets twice the draws of one said on 2 days.
- **Shown:** the 2-day facts are the weaker group in every run (C2 86-88 vs C4 95-96 for nb) and become eligible later in the week.
- **Shown:** an early flat-priority arm was worse on C2 (Week-1, 1x, one seed), so dropping "days" is not obviously better.
- **Outside:** curricula help mainly "with limited training time budget or in existence of noisy data". Otherwise randomly ordered
  samples "perform as well or better" (Wu, Dyer & Neyshabur 2021, ICLR; abstract).

### f. Spacing across nights (suggested, lower priority within one week)

- **Shown:** consolidated facts get a flat 25% share every night, and there are no expanding intervals.
- **Outside:**
  - For a 1-week test, the best gap between reviews is about 20-40% of that week (Cepeda et al. 2008, Psychological Science;
    abstract).
  - Half-life regression predicts recall and cut prediction error by "45%+" at Duolingo (Settles & Meeder 2016, ACL).
  - Two 2026 papers schedule LLM replay by forgetting curves: FOREVER (arXiv 2601.03938, ACL 2026) and MSSR (arXiv 2603.09892).
    Reported by the citation checker; not read in full.
- **Why it waits:** within a 7-night week, the per-night allocation in (a) and (e) is the bigger lever. Spacing matters more across
  weeks (addendum 13's multi-week plan).

### g. Which layers the add-on covers (shown: already all of them; low priority)

- **Shown:** LoRA already covers attention, DeltaNet and MLP everywhere.
- **Shown:** training one quarter of the layers per night broke recall (8.5).
- **Outside:**
  - Facts are mediated by "middle-layer feed-forward modules" (Meng et al. 2022, ROME).
  - Feed-forward layers act as key-value memories (Geva et al. 2021, EMNLP).
  - LoRA on all layers, "in particular, the MLP", beats attention-only ("LoRA Without Regret").
- **Verdict:** no change suggested.

### h. The KL guard's second forward (shown elsewhere: an exact 9%)

- **Shown:** caching the base model's replay outputs is exact and made a Qwen3.6 step about 9% faster (`speed/box/RESULTS-box2.md`).
- **Not yet:** it has not been ported to the 2B and K2 runs. That is the speed thread's patch (`speed/qwen36_step/fast_step.py`).

## 3. What I changed in the code

All new behaviour is behind flags. Every flag is off by default and listed in `main()`'s `OFF`, so old result files keep their keys.

| flag | what it does | why |
|---|---|---|
| `--card-stats` | Report only. For every practice example it records whether the model already answered it before the step: every target token except the final eos is the argmax, so greedy decoding would write it exactly. The stats come from the logits the loss already computed (no extra forward). Writes `nights[i].cards`: shares by kind (`text`, `qa_cb`, `qa_ob`, `rem_cb`, `rem_ob`) and by quarter of the night. | measures section 2a |
| `--skip-known F` | A card that was right at its last closed-book or text practice is kept with probability F, else the slot is drawn again (at most `SKIP_TRIES` = 8 draws). A wrong morning probe marks all of that fact's cards unknown again. Implies `--card-stats`. | section 2a |
| `--rem-views V` | Each REM cycle gives the pool about V x pool x (cycle's REM steps / night's REM steps) slots, at most the usual 11 a step, spread evenly. Each dream gets about V practices a night, and the unused slots go to NREM cards. | section 2e |
| `--lora-plus R` | The lora_B matrices step at lr x R. | section 2d |
| `--lr-sched wsd` | The lr stays at `--lr`, then falls linearly over the last 20% of the night's steps. | section 2d |
| `--ob-share P` | The open-book share of practice Q&A (was a fixed 0.5). | section 1, open-book cost |

Checks, all on CPU with the tiny smoke model (**shown**; plumbing only, no learning claim):
- `--selftest` runs the new `selftest_cards` and all the older checks. `selftest_cards` checks:
  - with stats on, CE, KL and every LoRA gradient are bit-identical on the single, weighted and split + KL paths;
  - "known" is exactly "greedy decoding writes this answer": the model's own greedy continuation is known, and one changed token is
    not;
  - LoRA+ puts exactly the lora_B tensors at lr x R;
  - the cosine and wsd schedules give the expected values;
  - `--rem-views 20` gives night 2's last cycle of nb (2 dreams, 195 of 510 REM steps) 15 REM examples instead of 2,145, and leaves
    night 7's unchanged;
  - `Brain.nrem` / `rem_ex` with skip off draw exactly the examples, and leave the same RNG states, as the old code;
  - with skip on, a known fact is drawn about 1% of the time, against 50% before;
  - a wrong probe resets that fact's cards.
- `--smoke` of `ab_ob_b4_nb` with every flag off, and with only `--card-stats`, gives result JSONs (timings aside) and adapter tensors
  bit-identical to the code before this change.
- Smokes with all flags on, x4 with skip, and local with skip all complete.

Not combined yet: the speed thread's `fast_step.install()` replaces `Trainer.step` with a version that does not take `rows=`. To use it
together with `--card-stats` or `--skip-known`, that patch must pass `rows` through.

## 4. One change at a time, in priority order

Rules for every test:
- Week-2 world, seed 1, Qwen3.5-2B, the adopted recipe `ab_ob_b4_nb`, unless a line says otherwise. A pass is confirmed on seed 2
  before adoption.
- **Primary measure:** recall C2+C4, forward, from weights, on 200 questions, compared question by question with the exact McNemar
  test (`paired.py`).
- **Also reported:**
  - two-hop (78 questions), reverse, changed-new;
  - ARC-Easy (500 questions) and diary pooled;
  - train seconds per step and wall time;
  - the `cards` record.
- **No harm, every arm:**
  - ARC-Easy >= 87.6;
  - diary pooled >= the control's - 3;
  - changed-new >= the control's - 10;
  - no more reverted nights than the control.
- **Toy runs stay separate.** CPU smokes and self-tests prove only the plumbing. Week-1 may be used only to choose a setting before a
  prereg, never as evidence, and its numbers are never pooled with Week-2's.

Shared runs: C (control) = `ab_ob_b4_nb --budget-scale 2 --card-stats`, which is today's recipe at 2x work with identical training. R
(the 4x reference) = addendum 9's nb seed 1: recall 91.5, two-hop 38.5, diary 86.4, ARC 92.2. Expected nb at 2x (not a mark): recall
82-87.

### E0. The waste meter (free; it is the C run)

- **Measure:** from `nights[i].cards`:
  - `known_share`: the share of closed-book Q&A, text and closed-book REM examples already right before their step;
  - the same by kind and by quarter of the night;
  - wall time against the reference 2x runs (about 1,900-2,200 s on a 5090).
- **Decision marks, fixed now:**
  - If nights 3-7 average known_share >= 0.40, E1 has room. If it is < 0.20, E1 is unlikely to pass, but it still runs and is
    reported.
  - If `rem_cb` known_at_step >= 0.80 on nights 2-5, REM over-practice is confirmed (supports E2).
  - If the last quarter's known_share >= 0.80 on most nights, a plateau stop goes on the list.
- **Proved wrong if:** known_share stays under 0.20 on every night. Then the model is still learning from almost every example, and
  "skip what it knows" has nothing to skip.

### E1. Skip cards it already knows (`--skip-known 0.25`, 2x work)

- **Change:** T1 = C + `--skip-known 0.25`.
- **Pass, both needed:**
  - T1 recall >= 90.0 (R - 1.5: matches 4x within 1.5 points at half the steps);
  - T1 - C >= +3 with p < 0.05.
- **Also:** T1 two-hop >= C - 5, and the no-harm marks.
- **Proved wrong if:** T1 recall <= C's. Practice on known cards was not the waste. Also wrong if T1's known_share is not below C's:
  the mechanism did not act.
- **Wall time:** the same steps, so about the same time. The stats add an argmax over the target rows.

### E2. Cap REM practice per dream (`--rem-views 20`, 2x work)

- **Change:** T2 = C + `--rem-views 20`.
- **Why 20:** nb at night 7 gave about 15 practices per dream and was right on 94-96% of dreamed two-hop questions. x4's pool of 532
  gave about 10.5 and 87%. So 20 sits above both (suggested).
- **Shown, arithmetic for nb at 4x, using the logged pool size of each cycle:** 16,418 of the week's 118,784 examples (14%) move from
  REM to NREM. That is 3,774, 5,242, 4,408, 2,684 and 310 on nights 2-6, and none on night 7.
- **Pass:** T2 - C >= +3 recall with p < 0.05, and T2 two-hop >= C - 5.
- **Proved wrong if:** T2 recall <= C's, or two-hop falls by more than 10. In the second case, the many early REM practices were
  doing two-hop work.
- **Bonus check:** addendum 10's night-1 revert came after repeating a pool of one dream. With the cap, no night with a pool under 8
  dreams should be reverted.

E1 and E2 share the control, so C, T1 and T2 can run at once: about 35 min each on a 5090, about $1 in all, or three nights on Ben's
PC (about 1.6 h each).

### E3. LoRA+ (`--lora-plus 4`, 2x work)

- **Change:** T3 = C + `--lora-plus 4`. The ratio is 4, not the often quoted 16, because the paper's LLaMA settings are reported at
  2-4 (from body excerpts, not read). Smaller is safer for ARC.
- **Pass:** recall >= C + 3 with p < 0.05, plus no harm.
- **Proved wrong if:** recall <= C's. If ARC drops more than 3 points, the B-side step is too large: halve R once.

### E4. Flat-then-decay lr (`--lr-sched wsd`, 2x work)

- **Change:** T4 = C + `--lr-sched wsd`, which roughly doubles the average lr at the same peak.
- **Pass:** recall >= C + 3 with p < 0.05, plus no harm. Two-hop is reported, because the last REM cycle now trains at the peak lr.
- **Proved wrong if:** recall <= C's, or ARC falls below 87.6. The second means the night drifts.

### E5. Less open-book practice (`--ob-share 0.25`, 4x work): a speed test

- **Change:** T5 = nb at 4x + `--ob-share 0.25`. Control: an nb 4x rerun with `--card-stats` on the same GPU type.
- **Pass, both needed:**
  - train s/step <= 0.85 x the control's;
  - recall >= control - 1.5 and diary pooled >= control - 3.
- **Proved wrong if:** s/step falls by less than 5%. The step is not token-bound, so cut kernels, not tokens. Also wrong if diary
  falls by more than 5: open-book practice is what protects reading, as addendum 1 showed.

### E6. Port the exact KL cache (speed only, no learning change)

- **Change:** the speed thread's `kl_cache`, with `rows` passed through, on the 2B and K2.
- **Pass:** the speed thread's own GPU parity marks (CE rel diff < 1e-2, KL < 5e-2, LoRA-grad cosine > 0.99) and s/step -5% or more.
- **Proved wrong if:** parity fails, or s/step drops by less than 3%.

### E7. The winner on the small tier you deploy (K2-Horizon-3.7B, 4-bit base, 4x)

- **When:** only after E1 or E2 passes on seed 2.
- **Control:** k2s_q4 (recall 86.0, `results_a11`), rerun with `--card-stats`.
- **Pass:** recall >= 91.0 (+5) with p < 0.05, plus no harm.
- **Proved wrong if:** recall <= 86.
- **Why it matters:** your stated plan is to keep 4-bit and close the gap with better sleep. The 4-bit base missed 19 eligible facts
  against 7 for bf16, which is exactly the kind of gap targeted practice should help.
- **Cost:** about 2.3 h per run on a 5090 (8,236 s for k2s_q4).

### Later (untested, no code yet)

- **A plateau stop:** end training when the last window's known_share >= 0.9. It must also skip the remaining REM generation cleanly.
- **A per-night step budget** that follows the number of active facts that are not yet known, instead of the 1,200 cap.
- **Expanding review intervals** for consolidated facts (Leitner-style), in place of the flat 25%.
- **Naps:** a short midday session only on facts whose probe failed.
- **Higher card yield:** half the Q&A cards are thrown away as bad answers. That is about 10% of night time spent writing cards that
  are never used.

## 5. Plain summary for Ben

- **What's slow:**
  - Most of the night is training steps, and the steps are handed out by fixed rules that never ask "does it already know this?".
  - Early in the week, the two-step practice part spends thousands of repetitions on the first one or two two-step cards. By midweek
    most facts are already right before the night starts, but they still get their full share of practice.
- **What to try first:**
  - Turn on the waste meter. It counts how many flashcards the model already answered right before it practised them.
  - Then run two small changes against the same control at half the night's work: "practise known cards a quarter as often" and
    "cap each two-step card at about 20 practices a night".
  - Each is a 35-minute run on a rented 5090, or an evening on your PC.
- **How we'll know it worked:**
  - The marks are fixed before the runs. Half the work has to get within 1.5 points of today's full-work recall (91.5), and beat
    the half-work control by at least 3 points on the same 200 questions, with p < 0.05.
  - The general-knowledge and diary scores must not drop.
  - If the meter shows the model is still learning from almost every card, or the skipping arm is no better than the control, the
    idea is wrong and we drop it.

## Sources (checked by citation helpers against abstracts or search excerpts, not full text, unless noted)

- Karpicke & Roediger 2008, Science 319:966, doi 10.1126/science.1152408: more study after recall had no effect; more testing helped.
- Roediger & Karpicke 2006, Psychological Science 17:249: testing beats restudy at 2 days and 1 week.
- Cepeda et al. 2006, Psychological Bulletin 132:354: the best gap grows with the retention interval. No ratio is given in the
  abstract.
- Cepeda et al. 2008, Psychological Science 19:1095: the best gap is about 20-40% of a 1-week delay, falling to 5-10% of a 1-year
  delay.
- Settles & Meeder 2016, ACL, doi 10.18653/v1/P16-1174: half-life regression, "45%+" lower error.
- Tabibian et al. 2019, PNAS 116:3988: optimal review timing tied to the predicted recall probability. No fixed threshold.
- Amiri, Miller & Savova 2017, EMNLP (D17-1255): spaced repetition for training networks. Uses 34-50% of data per epoch and is
  2.9-4.8x faster.
- Toneva et al. 2019, ICLR (arXiv 1812.05159): many "unforgettable" examples can be dropped. The fraction is not in the abstract.
- Chang et al. 2024, NeurIPS (arXiv 2406.11813): forgetting follows a power law; larger batches resist forgetting; duplicated data
  forgets faster.
- Zucchet et al. 2025, COLM (arXiv 2503.21676): fact learning has a plateau phase; imbalanced data shortens it; fine-tuning on new
  facts corrupts old ones.
- Muennighoff et al. 2023, NeurIPS (arXiv 2305.16264): up to about 4 epochs of repeated data is about as good as new data.
- Schaul et al. 2016, ICLR (arXiv 1511.05952): prioritised replay by TD error, with importance-sampling correction.
- Loshchilov & Hutter 2015 (arXiv 1511.06343): selection by most recent loss rank, "about 5" times faster on MNIST.
- Katharopoulos & Fleuret 2018, ICML (arXiv 1803.00942): importance sampling from a gradient-norm bound. The abstract reports lower
  loss at fixed wall clock, not a speed-up factor.
- Jiang et al. 2019 (arXiv 1910.00762): Selective-Backprop, up to 3.5x (from a search summary).
- Mindermann et al. 2022, ICML (arXiv 2206.07137): RHO-LOSS, 18x fewer steps; high-loss points are often noisy.
- Lin et al. 2024 (arXiv 2404.07965): Rho-1, training on selected tokens; matches DeepSeekMath with 3% of the tokens.
- Paul, Ganguli & Dziugaite 2021, NeurIPS (arXiv 2107.07075): EL2N lets half of CIFAR-10 be pruned.
- Sorscher et al. 2022, NeurIPS (arXiv 2206.14486): data pruning. The "keep easy when data is scarce" rule is in the body, not the
  abstract (not read).
- Lee et al. 2022, ACL (arXiv 2107.06499): de-duplication gives 10x less memorised text and fewer steps.
- Abbas et al. 2023 (arXiv 2303.09540): SemDeDup, halving LAION with little loss.
- Bengio et al. 2009, ICML: curriculum learning. The convergence claims are hypotheses.
- Wu, Dyer & Neyshabur 2021, ICLR (arXiv 2012.03107): curricula help under a time budget or noisy labels.
- McClelland, McNaughton & O'Reilly 1995, Psychological Review 102:419: complementary learning systems. The interleaving detail is from
  a later description.
- Kumaran, Hassabis & McClelland 2016, Trends in Cognitive Sciences 20:512: replay allows "goal-dependent weighting".
- Mattar & Daw 2018, Nature Neuroscience 21:1609: replay priority from "gain" and "need".
- Stickgold & Walker 2013, Nature Neuroscience 16:139: sleep triages which memories to process.
- Wilhelm et al. 2011, Journal of Neuroscience 31:1563: sleep helped only when a test was expected. A 2021 non-replication is
  reported (Ashton & Cairney, PLoS ONE; not read).
- Tononi & Cirelli 2014, Neuron 81:12: sleep renormalises synaptic strength. This is the SHY trim.
- Frey & Morris 1997, Nature 385:533: synaptic tagging.
- Hayou, Ghosh & Yu 2024, ICML (arXiv 2402.12354): LoRA+, up to about 2x speed-up. The ratio is not in the abstract.
- "LoRA Without Regret", Thinking Machines blog, 2025-09-29: LoRA on all layers, especially MLP; the best lr is about 10x full
  fine-tuning; LoRA is less tolerant of large batches.
- Biderman et al. 2024, TMLR (arXiv 2405.09673): LoRA learns less and forgets less.
- Hägele et al. 2024, NeurIPS (arXiv 2405.18392): constant lr plus cooldown matches cosine (from search summaries).
- Hu et al. 2024, MiniCPM (arXiv 2404.06395): the WSD schedule.
- Kalajdzievski 2023 (arXiv 2312.03732): rsLoRA, scaling by alpha/sqrt(r).
- Meng et al. 2022, NeurIPS (arXiv 2202.05262): ROME, mid-layer MLP.
- Geva et al. 2021, EMNLP (arXiv 2012.14913): feed-forward layers as key-value memories.
- Allen-Zhu & Li 2024 (arXiv 2404.05405): 2 bits per parameter. The exposure counts are not in the abstract (not used here).
- Gekhman et al. 2024, EMNLP (arXiv 2405.05904): new facts are learned slower and raise hallucination.
- Ovadia et al. 2023 (arXiv 2312.05934): variations of a fact "could alleviate" poor fine-tuning.
- Berglund et al. 2023, ICLR 2024 (arXiv 2309.12288): the reversal curse.
- Balesni et al. (arXiv 2411.16353, v4 2025): models fail to compose two synthetic facts without chain of thought.
