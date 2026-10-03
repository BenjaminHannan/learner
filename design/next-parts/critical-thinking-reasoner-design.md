# Critical-thinking reasoner: design and experiment plan

Written 2026-10-03. Design only: nothing was trained or run. This merges two earlier reports (mechanism and curriculum) after a red-team pass. Every code claim below was checked against the files on branch `claude/project-thread-knhc46`.

Labels: **shown** means read in this repo's code or results. **Suggested** means literature or reasoning; papers are cited from earlier notes and have not been re-opened. **Untested** means our guess.

There are three rulers, and their numbers are never mixed:
- **Puzzle ruler**: the few-example 9×9 mazes, F_eq, in the repo.
- **Assistant panel**: the 128 calculator questions, which live on Ben's Mac only.
- **Village model**: not used anywhere here, and neither are the small card experiments.

## 1. Summary for Ben

- The reasoner's inputs and outputs are narrow pipes (shown in the code). Words go in one at a time with no context. Answers come out as 8 *averages* squeezed through 32 numbers. That could explain "right calculator call, wrong final number" (71 of 128), but nobody has checked yet (untested).
- **Step 1 is free:** are the wrong answers near-misses (4,827 written as 4,872)? Do longer numbers fail more? Does the number survive inside the reasoner but get lost on the way out?
- **Step 2 is a cheap pipe test:** can the pipe carry "The answer is 4827" through and back? If not, fix the pipe first. The first fix is an "answer notepad": 8 slots the talker reads directly, with no averaging.
- Then: training data that never repeats, "think longer" that really helps, and learning from examples placed in the notebook. One change at a time, with pass marks written down first.
- No skill list. Stage one is a proof of concept. The goal is a model that beats bigger plain models *at its own size*, tested by running the same recipe at three sizes.
- The reasoner takes in a list of vectors and doesn't care whether they came from text, images or sound. That keeps it ready for the vision and audio threads.

## 2. Current system (facts)

| Part | What the code does | Where | Label |
|---|---|---|---|
| Reader | Takes the frozen LM's *static* word vectors (not its hidden states). Then LayerNorm → 32 → GELU → 256, per token, with no context. | `sol_translator_grounding_v6.py:42-49, 174-177` | shown |
| Input caps | Question up to 48 tokens plus an EOS token. Notebook (context) up to 256 tokens. | same file, `:65-70` | shown |
| Core | 2 shared width-256 attention blocks per round. Each MLP is split into 8 upcycled experts, top-2 routing, router starts at zero. About 9M stored and 2.6M active weights (my arithmetic). | `sol_spatial_attention_core.py:19-57`, `claude_fewex_net.py:22,28-48` | shown (count: arithmetic) |
| One state stream | Each round: `z = h + e`, then 2 blocks, then LayerNorm. The state starts at zero. | `claude_fewex_net.py:77-81`, `sol_spatial_attention_core.py:95` | shown |
| Word order | Position bias is clipped at ±4. Half the heads only see ±1 neighbour. | `claude_fewex_net.py:23,35-45,66-71` | shown |
| Notebook | All notebook positions get the "same position as me" bias (index `CLIP`, offset 0). Nothing marks a vector as notebook rather than question. So the notebook is an unordered bag. | `sol_spatial_attention_core.py:83-94` | shown |
| Output | Only the question positions are exported (`:102-105`). Each goes 259 → 32 → LM width. `adaptive_avg_pool1d` then averages *all* question positions plus EOS into 8 prefix vectors. The LM sees those 8 vectors plus BOS and nothing else. | `sol_translator_english_v6.py:15-46, 66-81` | shown |
| Training (v6) | Fixed 4 rounds, full backprop, PonderNet-style expected loss. 500 updates × batch 2 on SQuAD TRAIN rows. | `grounding_v6.py:178-195`, `DEPLOYMENT-V6-PLAN.json` | shown |
| Inference stop | Up to 48 rounds. Stops on the learned halt plus a 3-round stability check, and that check uses the *puzzle-vocabulary head*, which gets no English loss. | `sol_spatial_attention_core.py:107-131` | shown; effect untested |
| Puzzle ruler | Training uses a random 1..16 rounds, with gradient on the last 1..6. Practised loop scored 51.0 / 51.3 F_eq. A plain net with matched weights (1.65M vs 1.62M) scored 33.8 / 33.6. | `claude_fewex_net.py:120-131,161-172`, `artifacts/claude-fewex-20260927/RESULTS-EQ.md` | shown |
| Assistant panel | 86/128 right setup, 15/128 right final answer, 71 right call but wrong answer, 38 wrong operation. Trained on 32 problems. | brief only (Mac) | shown by Ben, not readable here |

**Key gap (shown):** the repo cannot answer three things. Does the Mac pipeline use this v6 reader and output path? How does the calculator result get back into the core? How many rounds run at test time?

## 3. Architecture proposal

```
[modality encoder(s)] --latent tokens + role+modality + coords--> [Workspace assembly]
  text: frozen-LM word vectors -> thin reader (today)          |  question | notebook | examples | tool results | R draft registers
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
3. **Looped core:** today's blocks, trained with random depth so extra test-time rounds help. The puzzle ruler already trains this way (shown); the benefit on the assistant path is suggested (Huginn).
4. **Talker:** reads the registers 1:1. One hidden layer, no attention, no reasoning; the width (32 today) is an open question.
5. **Tool port:** calls read from the registers, results re-enter as workspace tokens (untested; the Mac code may differ).

## 4. Ordered experiment plan

**Rules for every row:** one change against the row before; 2 seeds; marks sealed by hash before the run. Panels are fresh (authoring subagent, independent checker, hash seal), and the consumed 128 panel is never reused. A score between the marks earns one extra seed, then the line stops.

### Free checks (zero cost; read-outs sealed first)

| # | Check | Reading that decides | Label |
|---|---|---|---|
| F0 | Pipeline identity, on the Mac. Which reader and output path does it use? How does the tool result re-enter? How many rounds run at test? Does the stop fire? | If it is not v6, every code fact in §2 is about a different pipe. Re-plan before C1. | shown gap |
| F1 | Error shape on the saved 128 outputs: near-miss edit distance and digit count, failure rate by answer length, share of wrong answers equal to some training answer, number of distinct answers. | Near-misses and a length effect point to a squeeze. Copy-from-train above 25% or collapsed answers point to memorising. Scattered errors point to a skill gap. | untested |
| F2 | Linear probe for the calculator result, cross-validated over the right-call cases: (a) on the core's question states, (b) on the 8 prefix vectors. | (a) ≥ 0.8 with (b) ≤ 0.4 means the output loses the number, so do C2. Both ≤ 0.4 means the number never gets in, so fix the tool return (Mac). Both ≥ 0.8 means the LM misreads the prefix. | untested |
| F3 | Reader collision: send every digit and number token through the saved reader's →32 layer and look for nearest-neighbour clashes. | More than 2% clash means the reader loses token identity. | untested |
| F4 | Puzzle ruler only: start from 8 small random states on saved practised checkpoints and take a plurality vote, on CPU. | Pass: ≥ +8 F_eq on both seeds. Fail: starts agree on >95% of mazes, or gain < +2. | untested |

### Single changes (in order)

| # | Change (one) | Pass mark | Falsifier | Label |
|---|---|---|---|---|
| C1 | **Round-trip pipe probe** (a measurement, not a model change). Train reader + core (4 rounds) + current output path so the frozen LM reproduces "The answer is N" (N fresh, 1-6 digits) and 4-12-word nonce sentences. 3,000 updates, no item repeats, 500 sealed items per length bucket. | Pipe adequate: ≥95% exact for 1-4 digits and ≥90% on 8-word sentences, both seeds. | Squeeze: <80% on 4 digits or <60% on 8 words. If the probe passes, the squeeze does not explain the 71, so skip C2. | untested |
| C2a | Only if C1 fails or F2 says the output loses the number. **Draft registers** (8, read 1:1) replace the average-pool. Talker hidden stays 32. | Round-trip 4-digit exact rises ≥15 points over C1 baseline, both seeds. | Gain ≤ 5 points: pooling is not the squeeze, go to C2b. | suggested |
| C2b | Only if C2a's falsifier hits. Talker hidden 32 → 256 on the C1 baseline. Needs Ben's OK (§9). | Same as C2a. | Gain ≤ 5: the core, not the talker, is the limit. Ask for an outside opinion. | untested |
| C3 | **Never-repeating generated TRAIN stream** replaces the 32 problems. Fresh draws, nonce vocabulary, held-out splits by *structure* (unseen wording, deeper chains, unseen vocabulary). Which task kinds go in stays open (§9); this is a property of the data, not a skill list. | On a fresh sealed 128 panel in the real format: right final answer ≥45/128 and wrong operation ≤19, both seeds. | Generator held-out ≥90% but panel ≤20/128: skills tied to the templates. | suggested |
| C4 | **Random-depth training** on the assistant path: draw 1..16 rounds, backprop through the last ≤4. Today's training uses 4 rounds while inference runs up to 48. | Panel at 16 rounds beats 4 rounds by ≥ +8/128, both seeds. The 4-round score drops ≤5. | 16 ≤ 4 on both seeds, or the stop fires by round 2 on >80% of questions. | suggested |
| C5 | **Segment + order vectors in the notebook**, meta-trained on few-shot episodes (k = 0-8) from held-out rule families. | k=8 at least 25 points above k=0. Shuffled-answer control within 5 points of k=0. Wrong-rule control below k=0. Both seeds. | k=8 gain under 10, or shuffled examples score as well as real ones. | untested |
| S | **Per-parameter efficiency test** (§7), on the recipe that survives C1-C5. | See §7. | See §7. | untested |

Deferred until after S, each a single change later: a plan head for operation choice, a self-check pass, and noise in training if F4 shows the starts never disagree.

**Stopping rule:**
- A line stops when its falsifier hits on both seeds.
- Two falsified changes in a row aimed at the same failure means pause and write an outside-opinion prompt (Astra or GPT) before trying a third.
- Stage one ends when the C1 pipe passes (as is, or after C2) and S has reached either its pass mark or its falsifier. No more stage-one tuning after that, because more tuning at 9M says nothing about scale.

## 5. What not to do

- Don't reuse the consumed panel, tune on a sealed panel, stack changes or mix rulers.
- Don't add experts during the skill phase. Grow rounds and state first. Experts mainly add storage (suggested: Ouro); MoE plan step 2 already gates expert growth.
- Don't put attention or LM layers in the talker, or feed LM hidden states to the reader without Ben's decision.
- Don't re-propose items on the maze race's forbidden list, such as fast weights / Hebbian (`2026-09-28-reasoner-idea-harvest-r1-r5.md:10-13`).
- Don't fix a skill list, put modality-specific code in the core, or rest a mark on an unopened paper.

## 6. Modality-agnostic interface contract (v0, untested)

**In:** `Workspace`
- `tokens [B, N, d]` with d = 256 (today's core width). Each modality adapter owns its own projection to d.
- `role [B, N]` and `modality [B, N]`, two int ids per vector (decision: a pair, matching the vision design on PR #22, not one combined segment id). Roles: question, notebook, example_k, tool_result, register. Modalities: text, image, audio, and more later. The core adds `Embedding(n_role, d) + Embedding(n_mod, d)`, both zero-init. A pair avoids a table that grows as roles x modalities, so audio needs one new modality id and no new roles.
- `coords [B, N, ≤3]` optional (row, column, time), turned into relative-bias indices. Coordinates left empty get the neutral "no position" index, which should be a *new* index rather than today's offset-0.
- `valid [B, N]` bool.
- `provenance` metadata. This is never used as an input feature.

**Out:** `FinalLatent`
- `registers [B, R, d]`: the final answer state.
- `stop_probability [B]` and `rounds [B]`.
- Optional `tool_calls`: a list of (op id, argument registers). The caller runs the tool and calls `resume(workspace + tool_result tokens)`.

**Rules:** the core never sees raw text, pixels or audio, and any encoder that emits this shape can plug in. `begin_latent` already accepts a 2-D `[B, H, W, 256]` grid with row and column biases (shown), so images fit with little change; audio would be a 1 × T grid (untested). The talker reads `registers` only and does not know the input modality.

## 7. Per-parameter efficiency test (the stage-one goal)

**Aim:** beat bigger plain models per parameter, with an edge that holds or grows with size. **Design (untested; marks fixed now):**

- *Ours at three sizes*: reuse the fair-scaling ladder (PR #18) so the two plans do not diverge: core width D = 256 / 384 / 512 (9.0M / 20.2M / 36M stored core weights, shown there), experts held at 8. **3 seeds per size**, the same small LR grid per size chosen on a TRAIN-derived dev split, one fresh start recipe for every size (no warm-start for the base only), and the larger identical TRAIN set. PR #18's matched-condition rules and void conditions apply here unchanged. Compute stays inside the PC GPU plus the vast budget the execution owner holds.
- *Plain baseline:* a non-looped transformer with the same reader, talker and data, at 1×, 2× and 4× each size. Compared at **matched stored params** (plain gets equal training FLOPs, so more data) and at **matched training FLOPs**.

The puzzle ruler already gives one point (shown): loop 51.0 vs plain 33.8 F_eq at ~1.6M matched weights, at one size and without matched compute.

*Rulers, kept separate:* puzzle F_eq, and a fresh sealed held-out set from C3's structural splits. The main curve is held-out loss; accuracy is reported too. At each size, score at 4, 8 and 16 rounds.

**What "improves with scale" means (all three must hold):**
1. At every size, ours beats the plain model with **2× our stored params** by more than the noise bar: +8 F_eq on the puzzle ruler, and ≥2 SE on the held-out set. Both seeds.
2. On a log-log fit of held-out loss against params, and against training FLOPs, our slope is at least as steep as plain's: our CI is not shallower.
3. More rounds still help at the largest size (16 rounds > 4 rounds).

**Falsifier.** Our advantage over the equal-params plain model shrinks at each size step, and the fitted curves cross before 10× the largest size tested. That would mean the gain is a small-model artifact. Results in between: add a fourth size before claiming anything.

## 8. Roadmap

A: F0-F4 (free) → B: C1, then C2a/C2b only if needed → C: C3, C4 → D: C5 → E: S → F: scale up. In F, facts arrive through the notebook, not the weights (suggested). Experts grow via MoE plan step 2 once data is large, and vision and audio encoders plug into §6.

**North star (Ben, 13:20-13:21 UTC): beat Minecraft, playing like a person** from the screen with keyboard and mouse, and reading online guides. This is a long-term target, not a stage-one eval. What it asks of the reasoner (all untested, nothing here is built):
- **Closed-loop acting:** the §6 tool port generalises to actions. Registers emit a key/mouse action, the next frame re-enters as a new workspace segment, and the loop repeats. This needs the vision thread's encoder and C4's "more rounds help".
- **Long-horizon plans:** a plan has to survive many frames, so state must carry across steps. That is the notebook, with segment and order vectors (C5), not fast weights.
- **Guides as notebook facts:** looked-up text goes in as a notebook segment, the same route facts will use later. Reading a guide and then acting on it is the few-shot test in C5 with a longer horizon.
- Nothing in stage one needs to change for this. It only constrains the interface: keep §6 modality-agnostic and keep the output able to name an action as well as words.

## 9. Open questions and decisions

Settled under Ben's standing autonomy (coordinator, 13:26 UTC; defaults taken, reversible):
1. **Talker width:** stays 32 unless C1 fails; only then widen (C2b). Not a "thin" violation to test it.
2. **Reader:** stays on static word vectors. No LM hidden states.
3. **Shared width:** d = 256, matching the vision design (PR #22), which uses `tokens [B,N,256]`, a layout tag (grid / seq / set), a zero-init modality embedding and optional coordinates. §6 should be merged with that contract rather than kept separate. Reconciled (13:28 UTC): each vector carries a (role, modality) pair, as in the vision design, plus `coords` and a `valid` mask.
4. **Scaling sizes and compute:** per §7 (PR #18 ladder, 3 seeds).

Still open for Ben:
5. **Peeking:** the 128 saved panel outputs come from an already-scored fresh panel, so mining them for F1 and F2 counts as peeking at a consumed set. Ben decides whether that is allowed. Without it, F1-F3 are replaced by C1's fresh generated items. The Mac pipeline code (F0) will be requested from the execution owner once the pilot is frozen.
6. **Task kinds in the C3 stream:** deliberately left open.

## Appendix: corrections to the earlier reports

**Mechanism report:**
- Wrong line numbers:
  - `step` is at `claude_fewex_net.py:77-81`, not 74-78;
  - the random-depth recipe is at `:120-131` and `:161-172`, not 154-161;
  - the pooling call is at line 45, not 44.
- Calling `N.CLIP` a "neutral" bias is wrong. It is the offset-0 (same-position) bias, and it also stops the narrow heads from masking. Registers given this index would look positionally identical to notebook tokens. They still differ through their learned `e`, but a new neutral index is cleaner.
- The pool covers every question position *plus the EOS separator*, because `slots = valid`.
- It omits that inference runs up to 48 rounds with a stability check built on the untrained puzzle head, while training uses only 4 rounds. This strengthens its change 2.
- "~9M / 2.6M" is arithmetic, not a printed count.

**Curriculum report:**
- Wrong line numbers: static embeddings are at `grounding_v6.py:174-177` (not 183-186), and `unsqueeze` is at `:49` (not 53). The content is correct.
- "Beyond 4 tokens apart the core cannot tell order" is overstated. The bias saturates at ±4 per hop, but 2 blocks × several rounds of local attention can relay order further, like stacked convolutions. Order sense is weak, not absent (suggested).
- "Averages the answer-slot positions": this path has no separate answer slot. It averages all question tokens plus EOS.
- The 1,000 row visits were SQuAD grounding rows, not calculator problems. Neither report can tie v6 to the Mac panel (that is F0).
- Its six skill families are examples only, per Ben's newer instruction.

**Brief:** "contextual reader" is wrong for v6. The reader works per token on static embeddings (shown).

**Checked and correct:** the input caps, the 4-round / batch-2 / 500-update plan, the PonderNet loss, top-2 MoE, the notebook bag, question-only export, 8 prefix vectors plus BOS, the forbidden list, and the PC-C result.
