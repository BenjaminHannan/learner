# What makes the model worse or slower: ranked audit

Written 6:40 PM ET, Mon Oct 5 2026, for Ben's ask ("look through things in the model like [the separate Hearer and Reader] that are making the model worse/less efficient").

Labels: **shown** = measured or read directly from code or saved weights; **suggested** = a reading of the evidence, not tested; **untested** = a guess with no evidence either way yet.

Code references are on branch `claude/ultracode-learning-blocker-gh011t` (commit fc89780) unless they start with `pipeline/`, which is on `claude/real-pipeline-code`. Result files are on the same branch under `artifacts/ultracode-v4/`. My own measurements (CPU only, no GPU) are in this folder: `inspect_weights.py/.json` (reads the saved checkpoints) and `probe_prefix_cpu.py/.json` (runs main2 and parent0 inside the real LFM2.5-1.2B on 32 hand-written questions, 8 kinds x 4).

This audit only reads and measures. It does not repeat the blocker thread's running tests (WD, PXH, PXW2048, CRT, MH) or the custom reader/talker thread's from-scratch designs. Proposed GPU tests are at the end, with pass marks fixed now.

## Ranked list

| # | What | Worse or slower | Label | Already being worked on? |
|---|---|---|---|---|
| 1 | The thinker only passes on the puzzle type, not the question | worse + slower | shown | yes (blocker thread: MH, WD) |
| 2 | Learning speed never slows down in the main model | worse | shown on the planner, untested on the main model | no -> test T1 |
| 3 | The Reader squeezes 2,048 numbers to 32 (Ben's example) | worse (info lost) | loss shown; effect on score untested | yes (MH tonight, WD) |
| 4 | The thinker's 8 notes are about 1,300x louder than words | probably worse | the facts are shown; the harm is untested | no -> test T2 |
| 5 | The trained thinker learns new jobs worse than a blank one | worse | shown | worked around (planner starts fresh) |
| 6 | Half the thinker's attention can only see 1 word either side | probably worse | code shown; harm untested | partly (PXH) -> test T3 |
| 7 | Training wastes time (one question at a time, Hearer re-run, checks) | slower | code shown; time shares untested | no -> test T4 |
| 8 | Two thinkers (the planner is a second copy) | bigger | shown | no |
| 9 | "8 experts" is really 1, run twice: 1.6M of 9.0M thinker numbers train | bigger + slightly slower | shown | no -> test T5 |
| 10 | Worked steps make answers about 4x longer | slower | shown | no (it pays for itself) |

Ranking = how much it costs times how sure we are. 1-3 are the big, well-supported ones; 4 is the biggest new finding; 7-10 are size and speed waste rather than accuracy.

## 1. The thinker only passes on the puzzle type (shown)

- Swapping the thinker's output for the output from a *different question of the same kind* barely changes answers: 1,012 vs 1,014 right out of 1,360 (74.4 vs 74.6%; job 06 in `SCREEN-v4.md`).
- Replacing it with the average for that kind (family-mean lesion) costs at most 5.3 fit points on every SR2/CF run and at most 4.7 points (0-15 rows) on CRDC4-9 (`SCREEN-v4.md`, MH marks section). Replacing it with one global average costs 18-46 points. So it says "which kind of puzzle", not "this puzzle".
- New, independent check (my CPU probe): the 8 notes for two questions of the same kind point the same way (cosine 0.959); for different kinds 0.831. In parent0 it was 0.921 vs 0.900. Training pushed the notes towards a per-kind label.
- Geometry run (`results/09-diag-geom`): intact 160/122, family-mean 161/130.
- Exception, shown: on chain questions the separate planner now decides the answer (plan_swap drops chain held-out to 2-3 / 160 on CRDC).
- Cost: the first answer word takes 2.97x as long as the bare 1.2B (R7, `RESULTS-R7.md` on `claude/project-thread-ajo58u`). Suggested: the extra time is one extra LM pass plus reader and thinker, paid for a puzzle-type label.

## 2. Learning speed never slows down in the main model (shown on the planner; untested on the main model)

- The main model trains at a constant lr 1e-3 with weight decay 0: `scripts/cap256_launch/english_pilot_runtime_v1.py:28` (`ADAM_RECIPE`). In `skills_pretrain_v1.py` the cosine decay `--lr-final-mult` defaults to off (`:555`) and `--wd` to 0 (`:590`).
- When the planner got a cosine decay, it went from 132.8 to 156.2 / 160 held-out (83.0% -> 97.6%), ahead on every one of 6 seeds by +13 to +30 (PLC vs PLCD, `DIAG-v4.md`).
- CRDC (the current best) decays the planner only (`--plan-cosine`); the main thinker and doors still run at constant lr.
- Signs of noise from constant lr: held-out jumps by up to 9 points between checkpoints of one run (plateau `RESULT-v1.md`, branch `claude/project-thread-aya9pk`); PLD's last 1,000 updates cost 10 rows (`DIAG-v4.md`).
- Untested: whether decay helps the other 4 kinds (the ones the main thinker + talker answer). Test T1.

## 3. The Reader squeezes 2,048 numbers to 32 (Ben's example; information loss shown, effect on score untested)

- Probe of number identity (`DIAG-v4.md` PR probe): the Hearer's own features keep 98.5%; after the 32-wide Reader, 17.6%; after the thinker's 4 loops, 8.9%.
- A *random, untrained* 32-wide Reader keeps 29.8%. So training made the Reader worse at keeping numbers, not better (shown).
- All 32 of the Reader's channels are used (effective rank 32 of 32 in main2; `inspect_weights.json`), so it is not a case of a few dead channels.
- But widening it alone did not help: Reader 256 gave +0.2 fit (W); PXW (256) 75 vs PX (32) 77 / 160 on the planner (`DIAG-v4.md`).
- Suggested: the squeeze loses information, but the talker reads the question itself, so it rarely needs the thinker's copy. Being tested tonight by the blocker thread: MH (merged Hearer and Reader, seeds 4-9 vs CRDC) and WD (both doors 2,048 wide).

## 4. The thinker's 8 notes are about 1,300x louder than words (facts shown; harm untested)

The 8 vectors the thinker places in front of the question (the "exit", `scripts/sol_translator_english_v6.py:16`, pooled to 8 at `:45`) go straight into the LM where word vectors would go.

- Size (shown, my CPU probe, 32 questions): a word vector is 0.74 long. main2's notes average 964.5 (range 468-1,771): **1,307x**. parent0's (5,120 updates) were 391 (530x). The blocker thread's own geometry run measured the same thing on different questions (all 8 notes together 4,931.5 long; `results/09-diag-geom`).
- They keep growing (shown, saved weights): exit output weights grew 27.3 -> 42.0 -> 53.4 and output bias 5.0 -> 6.9 -> 12.1 (bootstrap -> parent0 -> main2). Weight decay is 0 everywhere.
- The LM never changes them (shown): each of the LM's 16 layers adds a small change to every position. On the note positions that change is tiny next to a 964-long vector, so the note leaves layer 15 pointing exactly where it came in (cosine to its own input 1.000 at every layer). Question words are reworked from layer 1 on (cosine 0.32 after layer 1, 0.02-0.08 later).
- The answer still looks at them a lot (shown): 22-42% of each attention layer's attention from answer words lands on the 8 note positions in main2 (0.33, 0.42, 0.24, 0.22, 0.42, 0.27 for layers 2/5/8/10/12/14).
- The correction signal is weak (shown): the gradient reaching each note is 650x smaller than the gradient reaching each question word (0.018 vs 11.8; parent0 194x), and it is exactly sideways to the note (cosine 0.0). That is what you expect when every layer normalises its input first: size is invisible to the LM, so only direction can be corrected.
- Suggested mechanism for harm: with Adam, each update moves the exit weights by about the same amount, but the bigger the note, the less that amount turns it. So the notes' learning rate quietly falls as they grow (2.5x slower from parent0 to main2). The LM also uses BOS as a "parking spot" for attention (its BOS hidden size jumps to 8.3-8.7 in layers 8-14 of the bare model); our notes may be acting as a giant version of that, soaking up attention while carrying little. Both untested.
- Test T2 makes them word-sized.

## 5. The trained thinker learns new jobs worse than a blank one (shown)

- Planner test (PL, `DIAG-v4.md`): starting from main2's thinker, held-out plan 43 / 160; starting from a fresh random one, 97 / 160. Same data, same updates.
- That is why the planner starts fresh (`skills_pretrain_v1.py:304-309`, `uc_diag_v4.reset_fresh`).
- Suggested: 55,000 updates at constant lr with no weight decay left the main thinker's weights large and set in a puzzle-type pattern (items 1, 2, 4). Untested which part matters.

## 6. Half the thinker's attention can only see 1 word either side (code shown; harm untested)

- `scripts/claude_fewex_net.py:23` `CLIP, WINDOW = 4, 1`; `:42` `far = (dc - CLIP).abs() > WINDOW`; `:44` `narrow[: self.h // 2] = True`. The thinker was built for 2-D puzzles: the sentence is laid out as one row of a grid, 4 of its 8 attention heads only see neighbours within 1 word, and position bias is clipped at 4.
- Fine for grids; for a sentence it means half the heads cannot connect "the code for d" to a table entry 20 words away.
- Related, shown: lookups by content fail on the planner (PX content pointers 44 / 120; PXW 40). The blocker thread's PXH (two-hop pointer) is the current fix attempt.
- Test T3 (after PXH reports): make all 8 heads global.

## 7. Training wastes time (code shown; how much time each costs is untested)

- One question at a time (shown): every update is one row (`skills_pretrain_v1.py:928`). Measured on the 5090: our model answers 19 questions/s one at a time vs 358/s in batches of 256 (`/mnt/project-files/notes/speed-5090-2026-10-04.txt`).
- The Hearer is re-run on every row on every pass (`skills_pretrain_v1.py:913`) though it is frozen, so its features never change. A feature cache already exists (`english_feature_cache64_v1.py`).
- Receipts on every update (shown): a nonzero check on every parameter's gradient (`train_english_paraphrase_pilot_windows_v1.py:104`) and a finite check plus `.item()` per module (`english_pilot_common_v1.py:159-160`). Each forces the GPU to stop and report to the CPU; roughly 340 such waits per update (my count, untested as time).
- Full 32-bit LM with no TF32 (`sol_translator_english_v6.py:136` refuses anything else). bf16 doubled big-batch speed (71k vs 37k tokens/s at batch 64) but did nothing at batch 1 (68 vs 71 tokens/s).
- Test T4 profiles one update, then removes the waste.

## 8. Two thinkers (shown)

- The planner is a full deep copy of the Reader and thinker, re-initialised (`skills_pretrain_v1.py:304-309`). It adds about 9M stored numbers and is the part that actually decides chain answers.
- Suggested: this is a workaround for items 1 and 5. Since the size comparison counts everything (Ben's rule), a single thinker that can plan would be smaller.

## 9. "8 experts" is really 1, run twice (shown)

- The thinker's MLP is a mixture of 8 experts with a router that starts at exactly zero and experts that start as identical copies (`scripts/sol_spatial_attention_core.py:23-26`; `pipeline/scripts/cap256_launch/fresh_core_calculator_constructor.py` asserts both).
- Saved weights (shown, `inspect_weights.json`): after 55,120 updates the routers in main2 are still exactly zero; expert 0 and expert 1 are identical to the last bit (max difference 0.0); experts 2-7 are identical to each other and never trained. With identical experts the router's gradient is exactly zero, so this locks itself in. (The blocker thread noted the zero router in code; the checkpoint shows the two running experts are also identical.)
- Result: about 1.58M distinct trained numbers out of 9.01M stored (including 65k in unused puzzle heads). Every token runs the same MLP twice.
- Speed effect small (suggested: the thinker is about 1% of the LM's work per token). Size effect large: honest thinker size is 1.6M, not 9M.
- `--moe-revive` exists (`skills_pretrain_v1.py:587`) but only ran in a 40-update smoke. Fresh planner thinkers do train their experts; per-round routers (PLR) were wrong (131.2 vs 132.5).
- Test T5 folds the copies into one MLP (exactly the same answers, fewer numbers).

## 10. Worked steps make answers about 4x longer (shown; a trade worth making)

- SR2 targets run up to 45 tokens (limit 48, vs 12 before), so the talker writes about 4x more per answer. It bought +19.8 fit points. Listed for completeness, not as a fix.

## Checked and fine (not waste)

- The talker re-reading the question: needed. Talker with thinker notes only: 19%; with the question: 83%; question-first reuse 75%; all the same speed (R7).
- Notes in front of the question: front placement fixes wrong rows fastest (free front vectors fix 64/64, median 2 steps; at the back, median 8, max 95; `results/02-diag-chan`).
- More loops: 8 loops = 4 loops, identical answers (geom); the state barely changes after round 1 (0.016, then about 0.006).
- Input cap: 64 tokens in the skills runs (`skills_pretrain_v1.py:117`), not 160, and no prompt goes over it (plateau `RESULT-v1.md`).
- Wider exit (+0.7), pointer exit (-2.5), learned pooling (0): no effect.
- Ruled out earlier by the plateau thread: stiffness, thinker size, truncation, too little practice, wider input pipe, 8 loops, lr 3e-4.
- LoRA rank 8 at lr 1e-3 hurt (50 -> 12%); a gentler lr is untested.

## Proposed tests (marks fixed 6:40 PM ET Oct 5, before anything runs)

One change each, on Ben's own machines first. Routed through the coordinator to the blocker thread (T1-T3, T5) and to an implementation thread (T4). Not run here.

**T1, slow down the main model.** CRDC recipe + `--lr-final-mult 0` (cosine to 0 for the whole optimizer, not just the planner). Seeds 4-9, paired with CRDC4-9 (other-4 held 138 / 125 / 135 / 133 / 130 / 123, mean 130.7; held 297 / 277 / 291 / 289 / 287 / 281, mean 287.0).
- Helps if other-4 held mean >= 136.7 (+6) and ahead on >= 5 of 6 seeds.
- Wrong if the mean gain is under +2 or it is ahead on <= 3 of 6.
- Prediction: +3 to +8 on other-4.

**T2, quiet notes.** CRDC recipe + one change: the exit's 8 output vectors are RMS-normalised and multiplied by one learnable gain that starts at the mean word-vector size (about 0.74). Needs a small new flag. Seeds 4-9 paired with CRDC4-9 (family-mean lesion 0 / 6 / 0 / 15 / 3 / 12 rows of fit).
- Helps if mean held >= 292.0 (CRDC + 5) and ahead on >= 5 of 6 seeds.
- "The thinker now carries each question" if the family-mean lesion costs >= 32 rows of fit (10 points) on every seed.
- Wrong (loudness does not matter) if mean held is within 5 of CRDC and the family-mean lesion stays under 16 rows on every seed.
- Report the first 500 updates' loss too: the change is not function-preserving, so expect a dip at the start.
- Prediction: within 5 of CRDC on held; family-mean lesion rises but stays under 32 rows.

**T3, all heads global.** Only after PXH reports. PX recipe (fresh planner, 4 content kinds, 17,000 rows, `--op-attend --lr-cosine`) with `WINDOW` off for all 8 heads, seed 1 vs PX (77 / 160; content pointers 44 / 120). If PXH passes, run it on top of PXH instead.
- Helps if content pointers >= 74 / 120 (+30) or held >= 121 / 160.
- Wrong if held < 96 and content pointers < 60.

**T4, speed (implementation thread, PC 5070 Ti).** Profile one SR2 update by part. Then (a) cache Hearer features across passes and (b) run gradient receipts every 500 updates instead of every update.
- Pass: >= 25% less time per update, with the first 100 updates' losses matching the old code to 1e-6.
- Wrong: under 10% saved.

**T5, fold the copied experts (CPU is enough).** Replace each block's 8-expert MLP with expert 0 alone (exact, since the router is zero and experts 0 and 1 are identical).
- Pass: main2's in_dist answers are identical (1,014 / 1,360) and the thinker's stored size drops from 9.0M to about 1.6M.
- Wrong: any answer changes.

## Outside opinion (optional)

Whether the loud notes actually hurt has two plausible answers (they are harmless because each layer normalises its input, or they are slowing learning and acting as an attention sink). A GPT prompt with these numbers could help pick the test; not written yet.
