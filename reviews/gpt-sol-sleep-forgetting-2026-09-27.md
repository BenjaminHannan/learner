# Why do "sleep" nights make a 1B model forget some general facts, and what one change should I test next? (no code or file access needed)

You are an expert in continual learning, catastrophic forgetting, parameter-efficient fine-tuning (LoRA), and the neuroscience of sleep and memory consolidation. You have **no access** to my code, files or machine. Everything you need is pasted below. Do not ask me to run anything before you answer; reason from what is here. If a fact you need is missing, say exactly what it is and how it would change your answer. Label every claim **shown** (by the numbers below), **suggested** (fits them but not tested) or **untested**. I label mine the same way. Two seeds per arm is a screen, not a reliability estimate.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow.

## 1. Setup (the same in every run unless the run says otherwise)

- **Model:** MiniCPM5-1B, a borrowed 1-billion-parameter chat model (pinned revision, "thinking" off, bf16). Its own weights are **frozen** in every run. Only an add-on learns.
- **Add-on:** plain LoRA, rank 16, alpha 32, dropout 0.05, on the q, k, v and o attention projections of every layer. It starts at zero, so night 0 is exactly the base. **One adapter grows across all nights and is never reset.** It is always on, so it answers every question afterwards.
- **Day (the "work"):** 150 fresh arithmetic puzzles ("Use each of the numbers 3, 5, 8 exactly once, with + - * / and brackets, to make 17. Reply with only the expression, nothing else."; 3 or 4 numbers; the 4-number ones target 24). On each, the model gives 1 greedy answer and 30 sampled guesses at temperature 1.5. Sampling is restricted to legal expressions over the given numbers. An exact checker marks every guess.
- **Night (copy practice, arm "S"):** cross-entropy on the answer tokens only (the prompt is masked). The rows are the day's greedy right answers plus the first lucky right guess on each missed puzzle, about 100-110 rows by night 7. Training is 3 epochs, lr 2e-4, batch 8, AdamW. Each seed runs 7 nights.
- **Day skill (TEST):** 100 fresh puzzles (never practised) x 20 guesses at temperature 1.5. "Lucky" = the number of right guesses out of 2,000. "Reached" = the number of puzzles with at least one right guess. L0 = the base's lucky.
- **Harm panel:** 300 fixed, code-made, one-line short general questions (not chat), never trained on and never used to choose training data. The kinds are: which number is bigger (119, the only kind with digits), capital city (70), next day/month/letter (31), opposite (30), plural (30), and "how many legs does a spider have" (20). Each ends in an instruction such as "Reply with the city name only." The model answers greedily with at most 16 new tokens. An answer is right if the gold word appears in its first 8 words (for numbers, if the first integer matches). The base gets 200/300 right, including 58 of the 70 capitals.
  - **lost** = right at base, wrong after night N (always counted against the base, not the night before).
  - **gained** = the reverse.
  - net harm = lost - gained.
- **KL** = mean per-token KL(current || base) on the base's own greedy replies (up to 40 tokens) to 60 fixed prompts: 30 one-sentence chat requests ("Give one tip for keeping a plant alive.") and every 5th panel question. Measured only, never trained.
- **Hardware:** runs dl-1 to dl-7b used a rented RTX 5090 for about 66-93 minutes each. From now on there is **no money**: one RTX 5070 Ti (16 GB) plus CPUs, at $0.
- **Marks** were fixed and committed before each run, and a separate agent recounted every verdict blind. **A registered FAIL stays a FAIL.**

The retention marks (dl-3's F1-F5) are used by dl-3, dl-4, dl-6 and dl-7b. The arm is compared with S on the same seeds:
- F1: the arm's night-7 lost <= 0.5 x S's (summed over seeds), and each arm seed is below each S seed.
- F2: at most 1 of the arm's 14 nights has lost > 10.
- F3: the arm's lucky >= 2 x L0 on each seed, and the arm's gain over L0 >= 0.8 x S's gain (sums).
- F4: at most 1 night drops more than 15% below the night before.
- F5: reached >= the base's.
- Proved wrong: the arm's lost >= S's on both seeds.

## 2. Registered runs (number puzzles unless stated)

| run | the ONE change vs S (mechanism) | seeds, nights | TEST lucky, last night: S / arm (L0) | panel lost, last night: S / arm | verdict |
|---|---|---|---|---|---|
| dl-1 | R = REINFORCE with a group-mean baseline, one pass, lr 1e-4, on the model's right and wrong guesses; Z = R with the day's rewards shuffled (placebo) | 0,1; 3 | S 160,169 / R 63,148 / Z 62,79 (69) | S 8,16 / R 9,3 / Z 3,40 | FAIL |
| dl-2 | nothing changed except 7 nights instead of 3; P = placebo trained on the same number of legal but WRONG guesses | 2,3; 7 | S 237,249 / P 42,51 (64) | S 26,26 / P 17,19 | PASS |
| dl-3 | A = S + replay: as many extra rows as puzzle rows, each a general question the base wrote itself plus the base's own greedy answer (908-pair pool), trained with plain cross-entropy | 4,5; 7 | S 171,257 / A 227,216 (59) | S 39,24 / A 20,36 | FAIL (F1, F2) |
| dl-4 | K = S + a KL anchor: as many extra items as puzzle rows (base-written questions + base answer tokens, 880 pool); loss KL(base \|\| current) over the full vocabulary at every answer position, weight 1 ("base" = the LoRA switched off) | 6,7; 7 | S 184,353 / K 208,298 (59) | S 16,17 / K 6,19 | FAIL (F1, F2) |
| dl-6 | L = 1 epoch per night instead of 3 (same rows) | 10,11; 7 (27 of 28 nights ran; budget stop) | S 198,237 / L 140, [115 at night 6] (75) | S 25,27 / L 13, [7 at night 6] | FAIL (F3, F4; holds whatever the missing night) |
| dl-7b | F = dl-4's anchor, but the pool is only the base's **shakiest** short quiz answers: its lowest-confidence third (confidence = the smallest token probability among the first 4 answer tokens), 427 items; the panel's topics and any digit filtered out, so no panel fact is rehearsed | 12,13; 7 | S 273,204 / F 179,216 (66) | S 11,15 / F 3,4 | FAIL (F3 only: gain 263 vs bar 276, i.e. 76% of S's gain) |

dl-2's PASS was on marks that used **net** harm, which let gains hide losses. Its verify step, prompted by an outside review, split lost from gained, and that led to dl-3's marks. No run has yet passed dl-3's marks. Four runs were registered forgetting fixes (dl-3, dl-4, dl-6, dl-7b), and all four FAIL; no recipe has passed both forgetting and learning. dl-1 (a learning rule) and dl-5 (grid nights) were not forgetting fixes.

In dl-3, dl-4 and dl-7b the extra rows are added on top of the puzzle rows (a 1:1 mix), so those arms also take about twice as many training steps per night as S (shown by design). This matters for any "dose" explanation.

**Lost per night, nights 1-7 (S uses the same night rule in every row: shown):**
- dl-2: S 7,11,18,19,16,28,26 and 5,8,10,15,16,30,26; P (wrong answers) 6,14,17,9,8,13,17 and 8,5,11,12,16,22,19
- dl-3: S 3,11,15,17,20,35,39 and 4,8,11,12,13,14,24; A (greedy replay) 10,15,22,16,18,17,20 and 7,10,13,16,32,41,36
- dl-4: S 7,10,10,13,15,16,16 and 10,4,4,7,12,11,17; K (broad KL anchor) 4,5,7,9,3,8,6 and 4,9,8,12,19,16,19
- dl-7b: S 4,3,6,12,8,11,11 and 8,8,12,11,9,11,15; F (shaky-fact anchor) 0,7,4,5,8,8,3 and 2,0,0,0,4,3,4
- Across 10 seed-runs of the identical S night, night-7 lost ranges from 11 to 39 (shown).

**KL to base (section 1's 60 prompts) at night 7:**
- dl-2 S: 0.15 and 0.19, up from 0.04-0.05 at night 1.
- dl-3: S 0.17 and 0.13; A 0.28 and 0.28 (already 0.15-0.17 at night 1).
- dl-4: S 0.175 and 0.186; K 0.035 and 0.031.
- dl-6: L 0.22 vs S 0.19-0.21.
- dl-7b: S 0.153 and 0.176; F 0.018 and 0.013.

**Gained at night 7:**
- dl-2: S 36 and 34; P 41 and 41.
- dl-3: S 36 and 42; A 19 and 33.
- dl-4: S 45 and 46; K 54 and 26.
- dl-7b: S 47 and 50; F 14 and 20.

## 3. Report-only diagnostics (not registered claims)

**The trade in each forgetting fix, S -> arm (night-7 lost summed over seeds; gain in lucky over L0, summed; shown):**
- dl-3: lost 63 -> 56, gain 310 -> 325.
- dl-4: lost 33 -> 25, gain 419 -> 388.
- dl-6 (seed 10 only; seed 11's night 7 never ran): lost 25 -> 13, gain 123 -> 65.
- dl-7b: lost 26 -> 7, gain 345 -> 263.

- **Which items fall.**
  - fd-1 (a CPU diagnosis with a fixed bar): of the 29 items lost in dl-4's four night-7 models, 17 (58.6%) were in the base's lowest-confidence third of its 200 right items. The bar was 60% and chance is 33%, so it missed by one item and was not shown wrong. Median confidence was 0.55 for lost items and 0.75 for kept ones.
  - 19 of those 29 were capitals. 17 of the 19 sat in the less confident half of the base's right capitals.
  - 5 items were lost in all four models.
- **Fresh seeds.** In dl-7b's S arm, 22 of the 26 night-7 lost items (84.6%) were in the lowest-confidence third, against a bar of 60% fixed in advance. That is a pass on the second try, so it is only suggested. All 7 of F's lost items were in that third too.
- **Measurement noise.** The same greedy base, run on CPU and on GPU, disagreed on 2 of 300 panel items.
- **Dose (dl-6).** At matched cumulative training (right rows x epochs, summed over nights), 1-epoch and 3-epoch nights lost about the same and learned about the same:
  - near 220: lost 4 and 3 vs 3 and 6;
  - near 430-490: lost 7 and 12 vs 10 and 7.
  - Suggested reading: both forgetting and learning track the total amount trained.
- **Placebo loses too.** dl-2's wrong-answer placebo lost 17 and 19, against S's 26 and 26. Suggested reading: any training knocks over fragile items.
- **dl-7b's learning shortfall comes from one seed.** F's gain as a share of S's gain, by night:
  - seed 12: 0.62, 0.58, 0.99, 0.88, 0.83, 0.51, 0.55;
  - seed 13: 0.55, 0.50, 1.47, 1.07, 1.25, 1.03, 1.09.
  - On seed 12, F went 207, 200, 179 on nights 5-7 while S jumped to 329 on night 6, then 273. Whether the anchor stalls late learning or S had a lucky night is untested.

## 4. Grid runs: findings only (they feed nothing we build)

- **dl-5 (FAIL; a finding only).**
  - Setup: the same S night, but the day was a backtracking search on 150 fresh 5x5 Latin-square grids. Rows = (grid state, correct next number), 925-1,337 rows a night, 3-4x the puzzle nights. Seeds 8 and 9, 5 nights.
  - Grid skill on fresh grids went from 48.8 to 93.8 and 93.4 points after 5 nights (seed 8 was already at 714 of 762 grid states on night 1). The wrong-number placebo scored 6.6 and 7.2 points.
  - Lost per night: 8, 21, 38, 46, 98 on seed 8 and 7, 14, 46, 48, 61 on seed 9 (bar 20). An answer-key arm lost 135 by night 5. Grid skill stayed flat while losses climbed.
  - Why it is a finding only: every training target began with the fixed prefix "The number in row R, column C is ", written by Claude. My rule bans Claude-written text in any training target (section 6).
  - Reply check afterwards: the base answers 0 of 300 panel questions in a "The X of Y is V" sentence. The grid adapters answered 299 and 300 of 300 that way. The lost items are wrong facts, not cut-off replies ("The capital of Australia is Sydney", "The day after Monday is Wednesday"). The gained items are mostly format.
  - Carry-over to number puzzles, never practised: base 66 lucky; the two grid adapters 67 and 53. There is no placebo adapter to compare.
- **dl-5s (FINDING ONLY; CPU).**
  - Mechanism: a logistic-regression switch reads the frozen base's last-layer state at the last prompt token and turns dl-5's adapter on or off per question. It was fitted on 600 practice grid states (label 1) and 412 base-written quiz questions (label 0).
  - Served this way, the panel lost 0 and 0 (always-on: 98 and 61). The switch was on for 762 of 762 grid test states and off for 300 of 300 panel items.
  - The fit loss was 0.0, so the task was very easy to separate. The grid states share one Claude-written wording, and the quiz questions all end in "?" with no digits. The switch most likely keys on wording, not on "puzzle vs question".
  - It reused saved answers instead of serving live. It is a finding only for the same wording reason as dl-5.

## 5. Sealed or planned, with no result yet

- **dl-9 (sealed; its re-run just started on the RTX 5070 Ti; no result seen).** It is dl-5s done cleanly on number puzzles.
  - Training is S's night unchanged. The only change is how the adapter is served:
    - S: always on;
    - X: a learned switch, refit each night (label 1 = day puzzles practised so far; label 0 = base-written quiz questions, half with a GLM-written "Answer only, no explanation.");
    - R: a random switch with X's on-rate.
  - Marks:
    - H1: X lost <= 5 on each seed and <= 0.25 x S's (sums).
    - H2: X's gain >= 0.9 x S's gain on each seed.
    - H3: the switch is on for >= 95 of 100 TEST puzzles and off for >= 285 of 300 panel items, on each seed.
    - H4: X's gain >= 2 x R's gain, and X lost <= R lost.
    - Proved wrong: X lost > 0.5 x S lost, or X gain < 0.8 x S gain, on either seed.
  - Report-only rows: the switch should be off for >= 126 of the 139 number-type panel items; a row of TEST puzzles reworded in 4 unseen GLM wordings.
  - The first attempt stopped at a disk check before doing anything, and the re-run is in progress. Seeds 16 and 17, 7 nights.
- **dl-8 (sealed, held until dl-9 reports): error-gated nights.**
  - Arms: S = every row; E = the half of the day's rows with the highest current loss; R = a random half (dose control).
  - Marks: E lost <= 0.5 x S's and each E seed below each S seed; E lucky >= 2 x L0 on each seed and E's gain >= 0.8 x S's gain; E's gain >= R's gain + 0.1 x S's gain, and E lost <= R lost.
  - Proved wrong: E and R within 20% of each other on both gain and lost.
- **dl-10 (plan, not sealed): replay + switch.** dl-7b's shaky-fact anchor during training, served through dl-9's switch. It runs only if dl-9 leaves a gap: panel items switched on and then lost, or near-kind questions routed to the add-on.
- **Named but not designed:**
  - an EWC-style per-weight guard (weights important to the base become less plastic);
  - serving the adapter at a scale below 1 (for example 0.5) without retraining;
  - a "noise-floor placebo" night, to learn how many panel flips any training at this dose causes before judging a fix.
- **Levers never varied (untested):** the replay/anchor ratio (always 1:1), the learning rate (2e-4 in every copy-practice run), and resetting the adapter (it is never reset). dl-1's copy-vs-reward harm comparison could not be tested.

## 6. Constraints (hard)

- **No Claude-written training data.** Anything trained on (inputs, labels or targets) is written by GLM 5.3 Flash, by the base model itself, or generated and checked by code. A fixed one-line instruction is allowed in tests if it is masked from the loss and the same in every arm; Claude-written text in a target never is.
- **Compute:** one RTX 5070 Ti (16 GB) plus CPUs, $0. My 1B nights have only run on a rented 5090 so far; how long they take on the 5070 Ti is not yet known.
- **Blind test panels** are never read, tuned on or used to choose data. The 300-item harm panel is my own code-made measure, not a blind panel, but it is also never trained on or used to pick anchors. Use fictional names only for any new people in data.
- **The goal (Ben):** the model "gets better overnight" at "everything, but mostly the work of the previous day", and nights should almost never make it worse. It sleeps only while dormant, and sleep must stop cleanly at any moment (interruptible). A night must be checkable and undoable.
- **Brain analogies are welcome but must be labelled.** For example: the hippocampus replays new and old memories interleaved during sleep while the cortex learns slowly; weak memories may get more replay; context gating by prefrontal cortex and basal ganglia. Where silicon can do better (exact replay, undo, per-weight bookkeeping), say so.
- **Keep the small experiments separate from the full joined build.** Everything above is small, isolated test runs on the borrowed 1B. The full joined "village" build (0.2d) is not described here. Do not reason about it. It matters only because its sleep-retention gate, H-B (a verified PASS on dl-3's retention marks), is still open. It is one of three open gates that build waits on (with H-A, the reasoner, and H-R, the reader). The small puzzle networks of a separate line of work are also left out; do not mix their numbers in.

## 7. What I want from you

1. **Ranked mechanisms for the loss**, each with the numbers above that support it, the numbers that argue against it, and what is untested. Please consider at least:
   - (a) fragile, low-margin facts pushed over by any gradient step (dose-dependent; the placebo loses too);
   - (b) output-format or template spill from an always-on adapter. Note that the puzzle prompt ends "Reply with only the expression, nothing else." and every panel item ends "Reply with ... only.";
   - (c) interference in shared attention projections from a LoRA that grows and is never reset;
   - (d) the KL anchor holding average drift (KL about 5x lower than S) while dl-4 still lost 6 and 19: why broad matching failed where matching shaky facts worked;
   - (e) measurement noise in a 16-token greedy panel with a first-8-words match, and whether S's night-7 losses (11-39 of 200 across 10 seed-runs) are above noise at all;
   - (f) anything I have missed.
2. **Critique the untried ideas:** EWC per-weight guard, serve-time adapter scale < 1, noise-floor placebo, error-gated nights (dl-8), replay + switch (dl-10). Also critique what dl-9 can and cannot show. For each: what it predicts, its cheapest honest control, and how it could fool me.
3. **ONE change for the next experiment** against S (or against dl-7b's F if you argue for that), on number puzzles, 2 seeds x 7 nights, on the 5070 Ti at $0. It must obey section 6. Give:
   - pass marks fixed in advance (in F1-F5's style, or better ones, with reasons);
   - an INCONCLUSIVE rule;
   - **the result that would prove your mechanism wrong**;
   - then the next two experiments, each conditional on the previous result.
   One change at a time: no bundles.
4. **Mistakes in my design or my reading.** For example: marks that cannot pass at 2 seeds, whether F3's 80% learning bar is the right trade, whether "gained" panel items (mostly format, and cut by the anchors) should count at all, and whether lost should be judged against a placebo night instead of against S. Be direct.
5. Cite real literature where it bears on this (continual learning, LoRA forgetting, replay or distillation anchors, EWC, sleep replay). Say so if you are unsure a paper exists.
6. **Plain-language summary for me:** 8-12 sentences, for a high-school senior, with every technical term explained in one line. End with what you would run next and why.
