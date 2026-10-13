# Make the model's inner motivator real: a model that wants to help and wants to learn, with both rewarded by its own dopamine signal.

Ben, the project lead, 9:30 AM ET 10-12: "I want to do more research into the dopamine. I want it to really be like an inherent motivator. Like the model truly wants to be a good helper and to learn. I want those two things to be rewarded with dopamine." Earlier (10-10, 10-11): the model's ultimate reward should be being a good helper, the way all human rewards trace back to one ultimate goal; curiosity and similar drives are welcome as stand-ins; being pleasant to talk to counts extra later, but only on top of being right and honest; proactively making the person's life easier is one of the model's goals; reward checked helping, never bare approval.

Today the "motivator" is a learned guess plus hand-written formulas that use it. We want to know what would make helping and learning the model's own learned goals (the things its choices are trained to reach), what the first fair test of that is at our small size, and what to avoid.
You cannot see our code or files, so everything you need is below. The numbers were copied from our result files by a helper; where it was unsure of a detail it wrote "inferred". File paths in the facts are only for our own reference.

## What we need from you (applies to every part below)

Please give your best one to three changes, ranked, for the problem described. They can change the model, the training, the practice data the model makes for itself, the test, or how we read the results. For each one give:

- **Mechanism**, precise enough that we can code it: what is computed, from what data, when, and how it changes the loss, the update, the data or the model.
- **Why it should work on our evidence.** Point to specific numbers below.
- **Cost** at our test size (3M-parameter thinker, a free 4-core CPU or one 16 GB GPU) and whether it still makes sense at the shipped size (about a 100M trained thinker plus a frozen 271M reader).
- **One test**: exactly one change against a named baseline arm, pass marks fixed in advance, and the result that would prove the idea wrong. Two seeds are fine for a first screen; a confirm needs at least 6 paired seeds.

Please label every claim **shown** (we or a paper measured it), **suggested** (evidence points to it) or **untested** (an idea). If you cite a paper, give the arXiv number and say what it showed and at what model size; we will check it. Keep claims about these small 3M experiments separate from claims about the full shipped model; label any claim about scale as untested.

Also tell us briefly: where our reading of the problem is wrong or incomplete, anything we should stop doing, and a plain-language summary for Ben, the project lead. He is a high-school senior. Under 150 words, no jargon.

## Hard constraints (no exceptions)

- **Deployable autonomy.** Everything that makes the model work (learning, practice, picking data, deciding when to practise or stop) must be something the deployed model does by itself, with no human or researcher step at run time. A method that needs a person to pick data, kinds, rules, gates or settings per subject does not count. Fixed constants chosen once before shipping are fine.
- **No hard-coding inside the model.** Everything inside the model is learned. Hand-written code is allowed only as an outside tool that the model itself chooses to call (a calculator, a spreadsheet engine, a game, a checker), or as the fixed night routine.
- **No new teacher.** Training data is only our existing 171,940-row teacher set, FineWeb-Edu, our own generated puzzles, and what the model makes or checks for itself. No new teacher model, no human demonstrations, no gold labels at run time.
- **The frozen Gemma embedding model stays the main reader.**
- **The talker (English writer) may read the question and the thinker's thoughts, but has no copy or pointer mechanism.**
- **No cut-off targets:** training targets are never truncated or reduced to answer-only.
- **Compute:** one RTX 5070 Ti (16 GB), an M1 Pro Mac (16 GB) and a 4-core cloud CPU; about $30 a month of cloud GPU. No large rentals.
## The model (short primer)

**Important:** the primer describes the finished design that will ship. The experiments in this problem were run on an earlier, small test model (about 3.3M parameters, called T1SDR) with its own small reader (two convolution blocks, window 5) instead of Gemma, a small looped thinker of width 256, and calculator calls written as text. Results from it are "card" experiments; treat any claim about the shipped model as untested.


Labels: **(shown)** read in code or results; **(Ben)** his words, dated; **(inferred)** my reading. Source: FINISHED-MODEL-2026-10-09.md.

## What it is

- **Reader (frozen, borrowed).** EmbeddingGemma 2's text part, 271,002,624 numbers. Each letter gets the meaning of its Gemma token. A learned letter window lets each letter see 4 letters each side. Gemma is the main reader and the window stays (Ben, 10-09).
- **Thinker (learned, loops).** Control and memory vectors loop through the same dense blocks, up to 32 rounds. A learned stop head ends it. Training draws 4, 8, 16 or 32 rounds per batch.
- **Answers.** Calculator calls are written as text, at most one per round. The calculator is plain Python outside the model (shown). Answer writers: WORD (one-word) and GEN (free-text) heads (inferred). Group 2 adds one learned writer.
- **Talker (not built).** A planned ~25M English writer, trained from scratch. It reads only the thinker's thoughts, with no copy and no pointer (Ben, 10-11). It may also read the question (10-11; being tested).
- **Agent turns, no plug (Ben, 10-11).** Each turn: think, write one line, read the reply. From 30M up, the thinker reads Gemma's 512-wide state with no plug.

## Sizes

| Rung | Thinker shape | Notes |
|---|---|---|
| 3M | 2 blocks x 256 | Gemma arm ~274.5M whole |
| 10M | 7 x 256 | |
| 30M | 9 x 512 | no-plug spec (was 9 x 384) |
| 100M | 21 x 512 | 102.6M trained; 373.1M whole as built (group 1); ~397M planned in all |

10M and 30M whole sizes are not in these files (inferred: about 271M plus the rung's trained count). Depth: the deepest shape fitting 16 GB at up to 1.25x step time; 21 x 512 is the fallback.

Ladder (shown): at 3M, the Gemma model scored 73.01 and 73.68 against 67.12 and 68.01 for PT (plain step model; name inferred). At 10M, seed 400 scored 74.65, +1.64 over 3M.

## Training data

Stated rule: the TEACH stock (171,940 rows, from a 1.2B teacher; cleaned copy 94,831) plus FineWeb-Edu, with no new teacher. FineWeb-Edu enters as cloze rows (one 3-12 letter word blanked). Our own generated puzzles and English also train the model: 24.7% and 11.7% of G1's mix (shown).

## Domain mode and night learning

Night mode ships: it learns on the person's machine from its own checked tries only. The domain loop learns spreadsheet formulas, RPN or Python reading from a tool and a help page. Each night it practises by changing digits in the help examples, keeps tries that match the tool, trains a small add-on, and undoes a night that drops its 512-check agreement by more than 3. It stops when quiz gains level off.

- **near**: help shape with new numbers (DM1 needs +30). **far**: longer ranges, the other column, two kinds joined (DM2 needs +10). DM3: no harm to old skills.
- Results: sheet v7 near +38.1 on seed 200, but far (DM2) failed. Python reading +46.3 and +46.8. v9 far widening failed.

## Other names

- **B2**: the earlier model (calculator inside, copy pointer, fixed rounds), the usual baseline.
- **B3**: the finished design. Group 1 (any-round calls, Gemma) is built as PR #56; group 2 is built, not run.
- **G1**: the Gemma-front test of today's model against PT.
- **v7/v9 sheet**: versions of the domain loop on spreadsheet skills.

## Rules any fix must obey

1. Deployable autonomy: the model does everything itself at run time. Hand code only inside an outside tool it chooses to call.
2. No hard-coding in the model; fix the learned link instead.
3. No truncated training targets and no new teacher data.
4. Gemma stays the main reader; tool replies go through Gemma plus the window.
5. Talker may see the question; no copy, pointer, or reply access.
6. Marks written before training.
7. At least 6 paired seeds to confirm.
8. Size comparisons count borrowed parts.
9. Compute: a 16 GB RTX 5070 Ti, an M1 Pro Mac, a 4-core cloud CPU; Modal GPUs $30/month; no rented GPUs without Ben's yes.

## The problem: facts (as of 9:40 AM ET 10-12)

Tags: **shown** (in our result files) or **inferred**. All results below are small card experiments on the 3.3M test model (sheet = spreadsheet formulas checked by a spreadsheet tool), except section (e), which is the separate game ("village") model; keep them apart.

### (a) Current design (shown)
- Reward r comes only from outside checks: a tool says the answer is right (domain mode, sleep), the game scores an unlock, and for helping, the person's effort saved on a checked outcome. Praise alone earns nothing.
- Guesser V: a read-only head on the model's state (reader mean, pooled thinker state, answer confidence; 900 numbers at 3M) predicting r. No gradient flows into the body: two tries at training it into the thinker (SB-2, SB-2b) ranked worse (within-kind AUC 0.536, 0.523) and cost an old skill (85 -> 72.5 and 85 -> 75).
- Dopamine d = r - V (in the game: the TD error r_t + g V(s_t+1) - V(s_t)). Planned uses: learn harder from surprises, practise where the outcome is uncertain, replay surprising memories in sleep, stop when bored. Only "choose the practice" has been tested.
- Practice choice today (domain mode, each night 1,024 problems over 10 kinds): either a hand rule (a kind's share follows its quiz change over 2 nights), even shares, or a learned-guess drive: edge = pick problems with large V(1-V); progress = large |V_now - V_two_nights_ago|. Pool of 4x drafts, keep 1,024 (10% random). The drives are hand formulas on top of a learned guess, not learned end to end.
- Helping reward (scripted person): wanted and right unasked step +1, unwanted -0.25, wanted but wrong -1. Steps that are irreversible, cost money, delete, or go beyond permission are never done unasked, only offered.

### (b) The guess of its own success (shown)
| Setting | within-kind AUC s200 / s201 |
|---|---|
| D0: head fit on past days' practice, scored on the next day | 0.543 / 0.597 |
| Frozen model, 32,000 fresh questions, 5-fold: state head at 2.5k / 8k / 16k / 32k rows | 0.637, 0.662, 0.696, 0.703 / 0.656, 0.685, 0.690, 0.704 |
| Same, behaviour features only (answers agree at forced 2/4/16/32 loops, calls, log-prob, length) | 0.594 / 0.567 (at 32k) |
| Prompt length only | 0.575 / 0.571 |
| Head refit each night on an 8,000-question self-quiz of the current model (never trained on), scored on the next day's real practice | 0.642 / 0.671 (Brier 0.2016 / 0.1902 vs per-kind rate 0.2050 / 0.2037) |
So at 3M the state does carry "will I get this one right" within a kind once the head gets enough fresh rows from the current model; old days' rows fail because the model drifts. The self-quiz costs about 5 minutes per night at 3M (untested at 100M).

### (c) Helping unasked (scripted person, shown)
Frozen 3M sheet models; a session is one grid and 2-4 requests; each later request is the person's habit follow-up with probability 0.6 (SUM->MAX, MAX->MIN, ...), else random; "wanted" = equals the next request. Heads: next-need N (what will they ask next) and help-value (expected reward of an extra), both read-only, refit over 6 training days, then 400 sealed sessions. Effort = person actions per session (lower is better).
| Test | Never help | Helper | Always add top guess | Perfect helper |
|---|---|---|---|---|
| P1: helper picks best of ~9 candidates, model's own answers | 2.97 | 3.39 / 3.33 (worse; 89% unwanted) | 3.47 / 3.26 | 2.39 / 2.27 |
| P2: help-value judges only the top next-need guess | 2.99 | 3.10 / 3.03 (no saving) | 3.50 / 3.38 | 2.42 / 2.31 |
| P3: same, the extra's value computed by the tool | 3.03 | 2.60 / 2.53 (saves 0.44 / 0.50) | 2.47 / 2.47 | 1.73 |
| P3 control: model answers, tool checks, wrong extras hidden | 3.03 | 2.81 / 2.76 (saves 0.22 / 0.27) | | |
Next-need guessing was near its ceiling (top guess = next request 35%). The blocker was wrong answers; checking unasked work with the tool fixed it.

### (d) Choosing practice (shown)
Sealed near score (%) on 420 held-out questions, 7 kinds; one question = 0.24 points.
| Arm | s200 at stop night | s201 at stop night | mean of last 3 nights s200 / s201 |
|---|---|---|---|
| Hand rule | 40.24 | 54.76 | 40.48 / 51.98 |
| Even shares | 50.00 | 56.90 | 43.89 / 50.79 |
| Edge (unsure) | 49.05 | 53.57 | 47.22 / 52.14 |
| Progress (improving) | 47.14 | 55.48 | 46.98 / 53.81 |
Progress - even on the last-3 mean is +3.10 / +3.02 (post-hoc). A confirm is running now: 6 paired runs (2 parents x 3 run seeds), progress vs even, 8 nights, mean near over nights 6-8; PASS if mean difference >= +3.0, paired 95% lower bound > 0 and >= 5 of 6 positive. Possible mechanism (suggested): progress spent ~4% on COUNTIF and 0-0.4% on IF (kinds it never learns) where even practice spends 10% each. At 3M every learnable kind still rises under even practice. The rule lost to even on s200 by starving stalled kinds.
Sleep loop (creative S1, own found answers kept and replayed): real reward beat a shuffled-reward placebo by +17.2 / +18.4 points of reach@32 (shown), so a checked reward does carry signal there.

### (e) The game model (separate; relayed from the game thread, not re-checked here)
Practising moves picked by the model's own odds learned nothing (+0.01 / -0.08), because its odds lock onto one habit and explore less than random play. After reward nights it scored 4.15 / 4.19 vs 3.75 / 3.61 before; a plain game AI gets about 4.0-4.2. A sampling temperature near 20 was found to flatten what each night teaches; a distillation fix is being tested. Rewards there are late (unlocks after many moves), which is where a TD-error dopamine should matter most.

### (f) Rules for any motivator (shown)
The deployed model does everything itself; hand code only as an outside tool or the fixed night routine; constants fixed once before shipping; no new teacher; reward never from approval alone; marks written before any run; >= 6 paired seeds to confirm.

## Specific questions for this problem

1. What does "the model truly wants to help and to learn" mean in a form we can build and measure? Which parts must be learned inside the model (a value head, a policy trained on its own TD error, a learned intrinsic reward whose own parameters are tuned so the policy it trains earns more checked reward, or something else), and which stay fixed outside (the checks)? Give the smallest design that makes helping and learning the model's own goals rather than our formulas, within our rules and compute.
2. The learning drive: what should "learning" be rewarded as (progress on its own self-quiz, now readable per (b); prediction-error curiosity; compression progress; something else)? How do we stop it chasing noise or unlearnable kinds, or practising only what is easy?
3. The helping drive is checked effort saved (c). How should the two drives share one dopamine signal and trade off (practise now vs help now; "learning to help better" counts for both)? Should there be one value head or two?
4. A model that makes its own reward can game it (wireheading, writing easy self-quizzes, chasing praise). Which anchors keep a self-made dopamine honest, and how would we test that it is honest?
5. The first test: at 3M, practice choice barely matters yet (d). In what setup would a learned motivator clearly matter (for example many kinds, some unlearnable, some mastered, some only reachable through others), can we build it at 3M on our spreadsheet tool fairly, and what are the marks? Then what should be tested at 10M/30M and in the game?

Please keep the answer under 3,000 words.
