# Critical-thinking reasoner: design and experiment plan

Written 2026-10-03, revised the same day after a check against the integrated design v5 and its `CURRENT.json` (branch `claude/premonition-launch-recovery-96c708`, commit `c5cfd9176`; cited as "v5 l.N" and "C.json"). Design only: nothing was trained or run. This merges two earlier reports after a red-team pass. Every code claim below was checked against the files on branch `claude/project-thread-knhc46`.

**What this is:** a menu of proposals, each a separate decision after v5 step 1 (current-size reasoning on today's English interfaces). It asks for no GPU time now; the F-checks are CPU-only. The C-rows come after the terminal eval, the English pilot and the curriculum have reported, and each needs approval. v5 l.8: "New architectural or reasoning-method changes remain separate decisions." The menu keeps its order.

Labels: **shown** means read in this repo's code or results, or in v5 and C.json. **Suggested** means literature or reasoning; papers are cited from earlier notes and have not been re-opened. **Untested** means our guess.

There are three rulers, and their numbers are never mixed:
- **Puzzle ruler**: the few-example 9×9 mazes, F_eq, in the repo.
- **Assistant panel**: one 16-question panel (8 matched ADD/SUB pairs) run through 8 fixed checkpoints, giving 128 answers. It is consumed. Its scores are readable in C.json.
- **Village model**: not used anywhere here, and neither are the small card experiments.

## 1. Summary for Ben

- The reasoner's inputs and outputs are narrow pipes (shown in the v6 code). Answers come out as 8 *averages* squeezed through 32 numbers. That could explain "right calculator call, wrong final number" (71 of 128), but nobody has checked yet (untested). We also don't know yet if the panel pipeline uses that same exit (F0).
- **Step 1 is free and runs on the CPU:** are the wrong answers near-misses (46 written as 51)? Do they cluster by carry or borrow? Does the number survive inside the reasoner but get lost on the way out?
- **Step 2 is a cheap pipe test:** can the pipe carry "The answer is 46" through and back? The English pilot may already answer this. If the pipe fails, fix it first. The first fix is an "answer notepad": 8 slots the talker reads directly, with no averaging.
- Then, if the curriculum Ben approved doesn't fix it: training data that never repeats, "think longer" that really helps, and learning from solved examples kept in the experience store. Facts and corrections stay in the notebook. One change at a time, with pass marks written down first.
- No skill list. Stage one is a proof of concept. The goal is a model that beats bigger plain models *at its own size*, tested by running the same recipe at three sizes.
- The reasoner takes in a list of vectors and doesn't care whether they came from text, images or sound. That keeps it ready for the vision and audio threads.

## 2. Current system (facts)

| Part | What the code does | Where | Label |
|---|---|---|---|
| Reader | v6 code: the frozen LM's *static* word vectors, then LayerNorm → 32 → GELU → 256, per token. The panel pipeline has two arms, frozen lexical embeddings or frozen causal LM states, each into a thin adapter. Neither gave fresh pairs (finals 6/64 static, 9/64 contextual). Seed 1/contextual never fit TRAIN stably (24/32, 29/32). | `sol_translator_grounding_v6.py:42-49, 174-177`; v5 l.10, l.71; C.json | shown |
| Input caps | Question up to 48 tokens plus an EOS token. Notebook (context) up to 256 tokens. | same file, `:65-70` | shown |
| Core | 2 shared width-256 attention blocks per round. Each MLP is split into 8 upcycled experts, top-2 routing, router starts at zero. 9,007,790 total and 2,700,974 active parameters, from CPU construction. | `sol_spatial_attention_core.py:19-57`, `claude_fewex_net.py:22,28-48`; v5 l.117-124 | shown |
| One state stream | Each round: `z = h + e`, then 2 blocks, then LayerNorm. The state starts at zero. | `claude_fewex_net.py:77-81`, `sol_spatial_attention_core.py:95` | shown |
| Word order | Position bias is clipped at ±4. Half the heads only see ±1 neighbour. | `claude_fewex_net.py:23,35-45,66-71` | shown |
| Notebook | All notebook positions get the "same position as me" bias (index `CLIP`, offset 0). Nothing marks a vector as notebook rather than question. So the notebook is an unordered bag. | `sol_spatial_attention_core.py:83-94` | shown |
| Output | v6 code: only question positions are exported (`:102-105`), each 259 → 32 → LM width. `adaptive_avg_pool1d` averages *all* of them plus EOS into 8 prefix vectors. The LM sees those 8 plus BOS and nothing else. | `sol_translator_english_v6.py:15-46, 66-81` | shown |
| Training | v6 code: fixed 4 rounds, PonderNet-style loss, 500 updates × batch 2 on SQuAD TRAIN rows. Panel pipeline: a fixed four loops, 5120 updates on TRAIN32. | `grounding_v6.py:178-195`, `DEPLOYMENT-V6-PLAN.json`; v5 l.71, l.413 | shown |
| Stop | v6 code only: up to 48 rounds, checked by the untrained *puzzle-vocabulary head*. The panel pipeline decodes a fixed four loops (512 advances for 128 answers). | `sol_spatial_attention_core.py:107-131`; v5 l.413 | shown |
| Tool return | Four reserved value-and-status pairs, one call per loop, result written before the next advance. Every panel call fired at loop 0, before any core advance. | v5 l.83; C.json | shown |
| Puzzle ruler | Training uses a random 1..16 rounds, with gradient on the last 1..6. Practised loop scored 51.0 / 51.3 F_eq. A plain net with matched weights (1.65M vs 1.62M) scored 33.8 / 33.6. | `claude_fewex_net.py:120-131,161-172`, `artifacts/claude-fewex-20260927/RESULTS-EQ.md` | shown |
| Assistant panel | 8 checkpoints (2 seeds × static/contextual × 2 LRs) × 16 questions = 128 answers. 86/128 right call, 15/128 right final, 71 right call but wrong final, 38 wrong operation. Pairs: 0/64 by final, 25/64 by call. | C.json `current_science`; v5 l.413 | shown |

**Key gap (shown):** rounds, tool return and reader are now known. Native runs are on the Windows PC. Still open: does the panel pipeline export through v6's 8-vector pool?

## 3. Architecture proposal

```
[modality encoder(s)] --latent tokens + role+modality + coords--> [Workspace assembly]
  text: frozen-LM features -> thin reader (today)               |  question | notebook | examples | tool results | R draft registers
  vision / audio: other threads                                 v
                                               [Looped core: 2 shared blocks x N rounds, MoE held at 8/top-2]
                                                 |            |                 |
                                         [draft registers]  [halt head]   [tool port: op + args read
                                          (answer state y)  (+ optional    from registers; result
                                                            multi-start     appended as tool-segment tokens]
                                                            agreement)
                                                 v
                              [Talker: per-register map 256 -> h -> LM width, 1:1, no pooling] -> frozen LM
```

1. **Workspace assembly:** each vector gets a learned *role* and *modality* vector pair, optional *coordinates* and a validity mask. This fixes the bag-of-words notebook and is the §6 contract (untested).
2. **Draft registers:** R = 8 learned vectors attending every round. They hold the current answer (TRM's *y*); question positions are scratch (*z*). In TRM, two states beat one or three (suggested, cited abstract).
3. **Looped core:** today's blocks, trained with random depth so extra test-time rounds help. The puzzle ruler already trains this way (shown). The benefit on the assistant path is suggested by Huginn, which v5 notes is "a scale far beyond the proposed local setup" (v5 l.249).
4. **Talker:** reads the registers 1:1. One hidden layer, no attention, no reasoning; the width (32 today) is an open question.
5. **Tool port:** calls read from the registers, results re-enter as workspace tokens (untested). Today's pipeline uses one call per loop into reserved value-and-status pairs (shown, v5 l.83); the port would keep that budget.

## 4. Menu of experiments (proposals, in order)

**Rules for every row:**
- One change against the row before; **at least 6 paired seeds** (both arms use the same seeds; report the paired mean difference with its 95% CI); marks sealed by hash before the run. A result between the marks earns 4 more paired seeds, then the line stops. Why (shown, PR #29 reimplementation, 10-03): seed-to-seed noise on the copy-path baseline is 81.6% ± 11.9 SD for new-wording right-call rate and 90.8% ± 5.9 for overall accuracy, and a +14-point gain from 2 seeds vanished at 6 (+1.9, CI -20 to +24). Practice-side puzzle rows keep their own 3-seed rule until their noise is measured.
- Panels are parent-supplied and independently checked, built as matched ADD/SUB pairs with siblings grouped (SVAMP motivates contrast pairs, v5 [42]). A pair counts only if both answers are right. Pass marks are counted in pairs.
- Generation sees only the question. Answers are frozen before gold is opened; each panel is consumed once, never enters positive replay, and reserved panels are never inspected.
- Score call, operand order (ADD commutative, SUB strict) and final-given-right-call per seed and arm, with ties and negative results. (v5 l.19, l.65, l.175, l.414; shown)

### Free checks (CPU only; read-outs sealed first)

| # | Check | Reading that decides | Label |
|---|---|---|---|
| F0 | Output path only. Ask the execution owner: does the panel pipeline export through v6's 8-vector pool? | If not, §2's Output row and C2a are about a different pipe. Re-plan C2 before using it. | shown gap |
| F1 | Error shape on the 128 terminal outputs only: numeric distance from the right answer, carry/borrow category, operand copies, share of finals equal to a training target, number of distinct finals. Already measured: 10/12 TRAIN residuals within 5, no operand copies (v5 l.358); 63/64 depth-panel and 28/32 earlier-pilot finals matched training targets (v5 l.171). | Near-misses across carry/borrow categories point to a readout squeeze. Copy-from-train above 25% points to memorising, and the two earlier panels are already above that line (suggested). Scattered errors point to a skill gap. | facts shown; reading untested |
| F2 | Linear probe for the calculator result. First on TRAIN rows where the right result reaches the task signal but the final is wrong (3 low-LR rows, v5 l.408), against right-final rows; then on the panel's right-call cases. Probe (a) the core's states, (b) the output prefix. Needs forward passes, so CPU only. Coordinate with Derek's readout successor (v5 l.365) and C.json's diagnostics A and B (not readable here). | (a) ≥ 0.8 with (b) ≤ 0.4 means the output loses the number, so do C2. Both ≤ 0.4 means the number never gets in, so look at the tool return. Both ≥ 0.8 means the LM misreads the prefix. | suggested |
| F3 | Reader collision, static arm: send every digit and number token through the saved reader's →32 layer and look for nearest-neighbour clashes. | More than 2% clash means the reader loses token identity. | untested |
| F4 | Puzzle ruler only: start from 8 small random states on saved practised checkpoints and take a plurality vote. | Pass: ≥ +8 F_eq on both seeds. Fail: starts agree on >95% of mazes, or gain < +2. | untested |
| F5 | Optional, needs approval: compare matched meanings through English and a canonical input (v5 l.68). | Canonical right but English wrong points to semantic loss. Both wrong on the operation points to operation choice. | suggested |

### Single changes (in order; each a separate decision)

| # | Change (one) | Pass mark | Falsifier | Label |
|---|---|---|---|---|
| C1 | **Round-trip pipe probe** (a measurement, not a model change). First ask the English pilot's source-reconstruction arm (v5 l.420) for exact-number reproduction. A standalone probe waits for the pilot: reader + core (4 rounds) + current output path, trained so the frozen LM reproduces "The answer is N" (N fresh, within v5's "supported two-digit, single-token results", v5 l.77) and 4-12-word nonce sentences. 3,000 updates, no item repeats, 500 sealed items per bucket. | Pipe adequate: ≥95% exact on numbers and ≥90% on 8-word sentences, both seeds. | Squeeze: <80% on numbers or <60% on 8 words. If the probe passes, the squeeze does not explain the 71, so skip C2. | suggested |
| C2a | Only if C1 fails or F2 says the output loses the number. **Draft registers** (8, read 1:1) replace the average-pool. Talker hidden stays 32. v5 rejected forced copying and lists digit heads and pointers as unadopted options (v5 l.172); C2 must argue why it beats them. | Round-trip number exact rises ≥15 points over C1 baseline, both seeds. | Gain ≤ 5 points: pooling is not the squeeze, go to C2b. | facts shown; merit untested |
| C2b | Only if C2a's falsifier hits. Talker hidden 32 → 256 on the C1 baseline. Needs Ben's OK (§9). | Same as C2a. | Gain ≤ 5: the core, not the talker, is the limit. Ask for an outside opinion. | untested |
| C3 | First read the approved two-arm, 1024-example curriculum on the existing architecture (v5 l.417), which runs after the terminal eval. v5's coverage tests already scored 0/8 pairs and 0/32 fresh (v5 l.42, l.47). Only if the curriculum fails: a **never-repeating generated TRAIN stream**, with held-out splits by *structure* (unseen wording, deeper chains, unseen vocabulary; SCAN, CFQ and COGS, v5 [1-3]). v5's rules apply: a canonical form, siblings in one split, an oracle never deployed (v5 l.66). Task kinds stay open (§9). | On a fresh sealed panel of 16 matched pairs in the real format: ≥4/16 pairs and wrong operation ≤5/32, both seeds. | Generator held-out ≥90% but panel ≤1/16 pairs: skills tied to the templates. | suggested |
| C4 | **Random-depth training** on the assistant path: draw 1..16 rounds, backprop through the last ≤4. Gate: only on a recipe that already scores some fresh pairs (≥2/16 at 4 rounds). v5's depth test (64 vs 8 block visits) scored 0/8 pairs everywhere at 1.98× the training time (v5 l.9, l.131). Looped rounds are not distinct depth, but the prior is lower. Calls fire at loop 0, so extra rounds cannot fix the 38 operation errors without new call timing (v5 l.85). | 16 rounds beat 4 by ≥3/16 pairs, both seeds. The 4-round score drops ≤1 pair. | 16 within 1 pair of 4 on both seeds, or the stop fires by round 2 on >80% of questions. | suggested |
| C5 | **Segment + order vectors in the workspace**, meta-trained on few-shot episodes (k = 0-8) from held-out rule families. In v5 the notebook holds facts and corrections and the experience store holds examples (v5 l.54-56). It follows v5's first rapid-learning step, context learning (not yet run): no oracle method labels, a fresh query, cleared context, a revisit after intervening learning, contextual and persistent gains reported apart (v5 l.12, l.89-90). The earlier notebook result (24/32 and 20/32 vs inline 32/32, v5 l.47) supports the bag idea (suggested). MQuAKE (v5 [13]) sets the correction test. | k=8 at least 25 points above k=0. Shuffled-answer control within 5 points of k=0. Wrong-rule control below k=0. Gain survives context reset. Both seeds. | k=8 gain under 10, or shuffled examples score as well as real ones. | untested |
| S | **Per-parameter efficiency test** (§7). It follows a recipe that already produces fresh pairs at current size. | See §7. | See §7. | untested |

C2a, C2b, C4 and C5 are architecture changes. v5-check also proposed moving C5 after S; the menu keeps its order here, and that move stays open for the decision on C5.

Deferred until after S, each a single change later: a plan head for operation choice, a self-check pass, and noise in training if F4 shows the starts never disagree.

**Stopping rule:**
- A line stops when its falsifier hits on both seeds.
- Two falsified changes in a row aimed at the same failure means pause and write an outside-opinion prompt (Astra or GPT) before trying a third.
- Stage one ends when the C1 pipe passes (as is, or after C2) and S has reached either its pass mark or its falsifier. No more stage-one tuning after that, because more tuning at 9M says nothing about scale.

## 5. What not to do

- Don't reuse a consumed panel, tune on a sealed panel, stack changes or mix rulers.
- Don't add experts during the skill phase. Grow rounds and state first. Experts mainly add storage (suggested: Ouro); MoE plan step 2 already gates expert growth.
- Don't put attention or LM layers in the talker. Don't set a reader default here: the panel pipeline already has static and contextual arms, and the reader choice belongs to the execution owner's pilot.
- Don't force calculator copying. v5 rejected it (v5 l.172).
- Don't re-propose fast weights / Hebbian for the maze race (its forbidden list, `2026-09-28-reasoner-idea-harvest-r1-r5.md:10-13`). The ban covers that race only. v5 lists "an error-correcting fast-weight matrix" as a lower-ranked alternative "if binding or temporary-memory errors dominate", needing transfer and clean-restart evidence (v5 l.97; shown).
- Don't fix a skill list, put modality-specific code in the core, or rest a mark on an unopened paper.

## 6. Modality-agnostic interface contract (v1, untested)

**In:** `Workspace`
- `tokens [B, N, d]` with d = 256 (today's core width). Each modality adapter owns its own projection to d.
- `role [B, N]` and `modality [B, N]`, two int ids per vector (decision: a pair, matching the vision design on PR #22, not one combined segment id). Role ids (fixed 10-03, matching vision's `workspace.py` on PR #26): question 0, notebook 1, example 2, tool_result 3, register 4, action 5 (key/mouse action tokens; confirmed). Modality ids: text 0, image 1, audio 2, more appended later. Example order is not a role: within the example role, row = example index and column = token position. The core adds `Embedding(n_role, d) + Embedding(n_mod, d)`, both zero-init. A pair avoids a table that grows as roles x modalities, so audio needs one new modality id and no new roles.
- `coords [B, N, 3]` float (row, column, time) plus `coord_valid [B, N, 3]` bool, one flag per axis. Settled 10-03 (v1, after the audio thread's review on PR #25 §j3); all untested:
  - **Per-axis "no position".** Each axis has its own neutral bias index, new, not today's offset-0. If either token in a pair lacks an axis, that axis uses its neutral index. Audio sets row and column absent, so it no longer sits on image patch (0, 0).
  - **Row/column bias only within one source.** Row and column offsets count only between two tokens with the same (role, modality) pair; across sources they use the neutral index. So text position 3 and image column 3 are not "the same place". Text order uses the column axis with row absent.
  - **Time in seconds, relative to now.** `time` = when the token happened minus now, so it is ≤ 0 (audio's choice). Time differences go into log-spaced signed buckets: 0, 50, 100, 200, 400, 800 ms, 1.6 s, older (each side of zero), plus "no time". Time bias applies across all sources that carry time, so a sound and a frame can be ordered. The ±4 clip and the ±1 narrow heads apply to row and column only. Audio's S2 test (log buckets vs 50 ms buckets clipped at ±4) checks this choice.
  - **Who carries time.** Registers and action tokens: time = 0 ("now"), row and column absent, so the core can tell which slot is newest. Audio slots and video frames: their time. Tool results: when they arrived. The question: 0. Notebook text, guides and examples: time absent.
- `valid [B, N]` bool.
- `provenance` metadata. This is never used as an input feature.

**Out:** `FinalLatent`
- `registers [B, R, d]`: the final answer state.
- `stop_probability [B]` and `rounds [B]`.
- Optional `tool_calls`: a list of (op id, argument registers). The caller runs the tool and calls `resume(workspace + tool_result tokens)`.

**Rules:** the core never sees raw text, pixels or audio, and any encoder that emits this shape can plug in. `begin_latent` already accepts a 2-D `[B, H, W, 256]` grid with row and column biases (shown), so images fit with little change; audio would be a 1 × T grid (untested). The talker reads `registers` only and does not know the input modality.

## 7. Per-parameter efficiency test (the stage-one goal)

**Aim:** beat bigger plain models per parameter, with an edge that holds or grows with size. **Design (untested; marks fixed now):**

- *Ours at three sizes*: reuse the fair-scaling ladder (PR #18) so the two plans do not diverge: core width D = 256 / 384 / 512 (9.0M / 20.2M / 36M stored core weights, shown there), experts held at 8. **3 seeds per size**, the same small LR grid per size chosen on a TRAIN-derived dev split, one fresh start recipe for every size (no warm-start for the base only), and the larger identical TRAIN set. PR #18's matched-condition rules and void conditions apply here unchanged.
- *Compute:* S needs its own compute decision when it is reached; today the PC GPU is on the English pilot and the vast credit is earmarked for pilot seeds.
- *Plain baseline:* a non-looped transformer with the same reader, talker and data, at 1×, 2× and 4× each size. Compared at **matched stored params** (plain gets equal training FLOPs, so more data) and at **matched training FLOPs**.

The puzzle ruler already gives one point (shown): loop 51.0 vs plain 33.8 F_eq at ~1.6M matched weights, at one size and without matched compute.

*Rulers, kept separate:* puzzle F_eq, and a fresh sealed held-out set from C3's structural splits. The main curve is held-out loss; accuracy is reported too. At each size, score at 4, 8 and 16 rounds.

**What "improves with scale" means (all three must hold):**
1. At every size, ours beats the plain model with **2× our stored params** by more than the noise bar: +8 F_eq on the puzzle ruler, and ≥2 SE on the held-out set. Both seeds.
2. On a log-log fit of held-out loss against params, and against training FLOPs, our slope is at least as steep as plain's: our CI is not shallower.
3. More rounds still help at the largest size (16 rounds > 4 rounds).

**Falsifier.** Our advantage over the equal-params plain model shrinks at each size step, and the fitted curves cross before 10× the largest size tested. That would mean the gain is a small-model artifact. Results in between: add a fourth size before claiming anything.

## 8. Roadmap (a menu, not a run order)

Separate proposals after v5 step 1, each needing approval. In menu order: A: F0-F5 (CPU only) → B: C1, then C2a/C2b only if needed → C: C3, C4 → D: C5 → E: S → F: scale up. In F, facts arrive through the notebook, not the weights (suggested). Experts grow via MoE plan step 2 once data is large, and vision and audio encoders plug into §6.

**North star (Ben, 13:20-13:21 UTC): beat Minecraft, playing like a person** from the screen with keyboard and mouse, and reading online guides. This is a long-term target, not a stage-one eval. What it asks of the reasoner (all untested, nothing here is built):
- **Closed-loop acting:** the §6 tool port generalises to actions. Registers emit a key/mouse action, the next frame re-enters as a new workspace segment, and the loop repeats. This needs the vision thread's encoder and C4's "more rounds help".
- **Long-horizon plans:** a plan has to survive many frames, so state must carry across steps. The first route is the notebook and experience store, with segment and order vectors (C5). v5's error-correcting fast-weight matrix is a lower-ranked option if binding or temporary-memory errors dominate (shown, v5 l.97).
- **Guides as notebook facts:** looked-up text goes in as a notebook segment, the same route facts will use later. Reading a guide and then acting on it is the few-shot test in C5 with a longer horizon.
- Nothing in stage one needs to change for this. It only constrains the interface: keep §6 modality-agnostic and keep the output able to name an action as well as words.

## 9. Open questions and decisions

Settled under Ben's standing autonomy (coordinator, 13:26 UTC; defaults taken, reversible):
1. **Talker width:** stays 32 unless C1 fails; only then widen (C2b). Not a "thin" violation to test it.
2. **Reader:** not ours to set. The v6 code is static; the panel pipeline has static and contextual arms. The choice belongs to the execution owner's pilot, so this doc sets no default.
3. **Shared width:** d = 256, matching the vision design (PR #22), which uses `tokens [B,N,256]`, a layout tag (grid / seq / set), a zero-init modality embedding and optional coordinates. §6 should be merged with that contract rather than kept separate. Reconciled (13:28 UTC): each vector carries a (role, modality) pair, as in the vision design, plus `coords` and a `valid` mask.
4. **Scaling sizes:** per §7 (PR #18 ladder, 3 seeds). Compute is its own decision when S is reached.

Still open:
5. **Peeking (Ben, 13:29 UTC, "yes" to my question; read as permission):** the 128 saved panel outputs may be mined for F1-F3 even though that panel is consumed. They are used only to steer design, never as a score, and the panel is not reused for any pass mark. The output-path question (F0) goes to the execution owner once the pilot is frozen.
6. **Task kinds in the C3 stream:** deliberately left open.

## 10. More model-shape ideas

See critical-thinking-shape-shortlist.md (ranked shortlist from the 10-03 literature search).

## Appendix: corrections to the earlier reports

**Mechanism report:**
- Wrong line numbers:
  - `step` is at `claude_fewex_net.py:77-81`, not 74-78;
  - the random-depth recipe is at `:120-131` and `:161-172`, not 154-161;
  - the pooling call is at line 45, not 44.
- Calling `N.CLIP` a "neutral" bias is wrong. It is the offset-0 (same-position) bias, and it also stops the narrow heads from masking. Registers given this index would look positionally identical to notebook tokens. They still differ through their learned `e`, but a new neutral index is cleaner.
- The pool covers every question position *plus the EOS separator*, because `slots = valid`.
- It omits that the v6 code runs up to 48 rounds at inference with a stability check built on the untrained puzzle head, while training uses only 4 rounds. This applies to v6 code only; the panel pipeline decodes with a fixed four loops (v5 l.413).
- "~9M / 2.6M" was arithmetic. CPU construction gives 9,007,790 total and 2,700,974 active (v5 l.117-124).

**Curriculum report:**
- Wrong line numbers: static embeddings are at `grounding_v6.py:174-177` (not 183-186), and `unsqueeze` is at `:49` (not 53). The content is correct.
- "Beyond 4 tokens apart the core cannot tell order" is overstated. The bias saturates at ±4 per hop, but 2 blocks × several rounds of local attention can relay order further, like stacked convolutions. Order sense is weak, not absent (suggested).
- "Averages the answer-slot positions": this path has no separate answer slot. It averages all question tokens plus EOS.
- The 1,000 row visits were SQuAD grounding rows, not calculator problems. The panel pipeline trained 5120 updates on TRAIN32 instead (v5 l.413).
- Its six skill families are examples only, per Ben's newer instruction.

**Brief:** "contextual reader" is wrong for the v6 code, which works per token on static embeddings (shown). It is not wrong for the panel pipeline, which has a contextual arm (v5 l.71).

**Checked and correct:** the input caps, the v6 4-round / batch-2 / 500-update plan, the PonderNet loss, top-2 MoE, the notebook bag, question-only export, 8 prefix vectors plus BOS, the forbidden list, and the PC-C result.

**Changes from v5 check (10-03):**
1. Panel facts (16 questions × 8 checkpoints, C.json scores) in rulers and §2. Applied, plus 25/64 pairs right by call.
2. Reader: two arms; our static default removed (§2, §5, §9.2, Brief). Applied.
3. Fixed four loops, 5120 TRAIN32 updates; 48-round stop is v6 only; C4 line deleted. Applied.
4. Key gap and F0: three gaps closed, only the output path open. Applied.
5. Fast-weight ban limited to the maze race; v5's alternative added (§5, §8). Applied.
6. Compute: modified. The $10 cap and GPU hold are out of date (13:40 UTC records); §7 uses the current wording.
7. Core counts from CPU construction. Applied.
8. C3 reads the approved curriculum first; generator only if it fails. Applied; pair marks are ours.
9. C1 asks the English pilot first; two-digit numbers. Applied.
10. F1 and §1 example: two-digit near-misses, measured facts. Applied.
11. F2: TRAIN rows first, CPU only, coordinate with Derek and A/B. Applied.
12. C4: depth result, call timing, gate on fresh pairs. Applied; gate and marks are ours.
13. C5 and §1: notebook vs experience store, v5's context-learning rules. Applied.
14. Menu framing. Modified: the menu keeps its order as Ben asked, so C5 stays before S (the move is noted in §4). "During the hold" became "now", since the hold ended when Qwen stopped.
15. C2: v5's rejected copying, digit heads, pointers. Applied.
16. §4 panel rules. Applied.
17. F5 canonical-vs-English, optional. Applied.
18. Citations and Huginn caveat. Applied.

Rejected: none. Source notes: v5 l.428 gives $6.77 headroom (05:32 UTC); v5-check's $6.55 is C.json at 11:38 UTC. Both are now superseded. C.json's diagnostics A and B are a four-cell diagnostic and a return-intervention protocol; their files are not in that commit.
- §6 contract v1 (13:55 UTC 10-03): per-axis coord flags with per-axis neutral bias, row/column bias only within one (role, modality) source, time as seconds-before-now in log-spaced buckets, registers and actions at time 0. From the audio thread's review (PR #25 §j3).
- §6 role table fixed (14:20 UTC 10-03): question 0, notebook 1, example 2, tool_result 3, register 4, action 5; example index goes in the row coordinate. Note from vision (PR #26): `read_latent` returns question positions only, so inputs held in the notebook can't be lesioned through the output; registers (C2a) would fix this.
- 6-paired-seed rule (18:00 UTC 10-03) replaces the 2-seed rule for assistant-format rows, from PR #29's measured noise. Think-before-calling tested on vast: no gain over 6 seeds (shortlist rank 1 demoted). Copy path (shortlist rank 0) held across 12 runs.
- Current recipe (18:35 UTC 10-03, PR #29 reimplementation): copy route + varied wording (180 frames). New-wording call 98.1% (paired +16.5, CI +5.6 to +27.4, 6 seeds), overall 99.0%, unseen 99.3%. Shape ideas are to be judged next on two-step chained problems, since one-step questions are near ceiling.
