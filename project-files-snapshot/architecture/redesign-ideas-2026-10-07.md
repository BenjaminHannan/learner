# Wider reading, adaptive depth, and an external calculator for B2 (ideas, 2026-10-07)

Asked by Ben 10-07 about 10:48 AM ET. Labels: **shown** = read in the code or results here, **suggested** = reasoned, **untested** = not run.
Nothing here was run. Papers: abstracts only, opened by a Sonnet subagent (`/mnt/project-files/papers/thinker-absorb-papers.md`).

## 1. What the thinker sees today (shown, `custom_io/models/ledger.py`)

- The +-4 letter window is only how each letter's own features are made (2 conv blocks, kernel 5).
- The thinker is not limited to it. Every round, the controller cross-attends over the 27 workspace slots and **every** reader output across the whole question (`CBlock.forward`, line ~120: the mask covers all prompt positions).
- So the thinker can see the whole question. What it gets for each position is a local summary: that letter plus about 4 neighbours each side. Anything that needs two far-apart words to be combined has to be done by the thinker's attention, in its few rounds.
- My first page drew it as "9 letters at a time". That was misleading and is being fixed.
- Window worth: removing it cost -6.8 / -6.3 pooled-5 and broke cipher_map (R0, shown). A window is also what Gemma-only readers lacked (EGR/EGO/EGM/EGW all failed).

## 2. Ways to widen what each position knows (suggested; paper claims from abstracts)

Ranked, cheapest first. Keep the window for exact letters (shown to matter) and ADD global mixing:
1. **Window, then 2-3 global self-attention blocks** (Conformer 2005.08100 pattern). Likely under 1M params (subagent's estimate). Zoology 2312.04927 and H3 2212.14052 report that local conv alone is weak at recall/lookup and that adding attention closes most of the gap. Lookups and ciphers are recall tasks.
2. **Charformer's GBST 2106.12672** as a parallel channel: learned soft mix of block sizes 1..M per position. A learned version of "how wide a window".
3. **CANINE 2103.06874**: downsample by 4, global attention on the short sequence, upsample and add back to the letters.
4. **4-8 memory tokens** in the reader (RMT 2207.06881): scratch space. Cheap.
5. EGE (frozen EmbeddingGemma 2 on top of the window) is already this idea with a pretrained whole-question encoder: +1.6 / +2.1 (2 seeds), 6-seed confirm running.
- Not recommended at 64 characters: Perceiver latent bottleneck (loses per-letter detail the copy talker needs), Hyena, MegaByte, Set Transformer.
- Nobody found a paper on why a local window helps ciphers (the subagent said so). Ours is a repo result, not a literature one.

## 3. Loop as long as it needs, and go deeper

What the code does now (shown):
- 8 loops, fixed. Round t = 1..7 writes program step t, so a program is at most 7 steps. Chain questions die if cut to 1 round (loops:1 chain-5 <= 5 by design).
- Running MORE loops than trained makes B2 slightly worse: in_dist at 16 loops minus at 8 = -1.91 / -1.62 on the q33 seeds (`RESULTS-EG2.md`, Test LR section, plain B2 rows).
- Test LR (train every round to give the answer) gained +1.14 / +1.27 but failed the stability mark on one seed (-0.51 vs -0.3) and leaked at loops:0 (15.88 on s200). So "just add loops" is not free: it needs training that makes extra rounds safe.
- Sizes: S = 2 controller blocks at width 256 (3.3M), M = 3 blocks at width 384 (10.8M). Looping already gives depth without parameters.
- Data limit (roadmap): about 12M word pieces supports roughly 2M trained params at <=4 reuses. A deeper separate-weight stack on the current data risks memorising (B1 students hit 91-96% on their own mix and about 11% on new kinds).

Ideas (suggested / untested):
1. **Learned halting**: the thinker emits "stop" each round (ACT / PonderNet style; from memory, papers not opened here). Train with random round counts so that rounds beyond the needed ones do not hurt. Cap at, say, 32.
2. **Depth**: raise blocks 2 -> 4+ with shared weights across loops first (no new data demand), judged against a same-size plain transformer, since the size rule is +-3% of the baseline.
3. Both depend on removing the 7-step cap (next section).

## 4. Calculator as an external tool the talker calls (Ben's design)

Today (shown): the calculator is inside the thinker's loop. Each round the thinker picks an op and two operand slots; an exact int64 executor writes the result into a workspace slot (exact 93-number code), which the next round reads.

Ben's version, as I understand it:
1. The thinker's state goes to the talker.
2. The talker writes a tool call as text, e.g. `add 12 5`, copying the numbers out of the question with its existing copy path.
3. The calculator runs outside the model and returns `17`.
4. The reader takes in the result as ordinary text, appended to the question, together with whatever else is needed.
5. The thinker loops again, and stops by emitting the final answer instead of another call.

Why it fits (suggested):
- Removes the 7-step cap: any number of calls.
- Gives the loop a natural stopping rule: answer vs call. Halting becomes a talker choice.
- Matches your earlier rule that the talker translates the thinker's state into words, and that the thinker does not do arithmetic.
- The "swap plus and minus" proof still works: swap them in the tool.
- Makes the reader the only input door, so results get the same wide reading as everything else.

Risks (suggested):
- Digits come back as characters. The reader must carry 9-digit numbers exactly through its window. The workspace code did this by construction; text may blur it.
- The talker now needs a new mode (CALL) and the data needs call/result traces. Only 11 arithmetic families have worked steps today.
- It changes reader, talker and training loop at once. It is a rewrite, not one change.

## 4b. Ben's point: it has to work just as well with the calculator outside (10:35 AM ET)

Ben's reasoning: if the calculator must sit inside the model for it to work, then reading or writing is failing somewhere in the chain. An external, text-only calculator is therefore a test of the input and output, not just a design choice.
Shown so far (REPORT.md): B2's inside executor gets chain-5 99.7-99.8. plain_tf_steps (writes steps as text, no calculator) gets 94, and C1' (the same model with a calculator filling each step at answer time) gets 96, pooled-5 +1.1. So a text model with an outside calculator already exists and does not match B2 on chains. Not shown: where it loses (reading numbers, choosing the step, or writing digits).
Suggested, so T1 doubles as the diagnosis:
- **T1 pass mark = parity with the inside version**, not the B2 floor: chain-5 >= 99 and pooled-5 within 1.0 of plain B2 on both seeds, calculator really outside (the model gets only text back). Proved wrong: chain-5 below 95.
- **D0 first, no training (CPU, existing B2 checkpoints s200-205):** probe whether each digit of a question number can be read back from the reader output (reading), and whether the talker can copy a 1-9 digit result string given the value (writing). If either is below ~99% per digit, the break is in that stage, which would explain why the inside executor was needed.
- Untested whether D0 will show a break. The 1.2B sandwich failure the team found earlier was also reading/writing, so Ben's suspicion has a precedent (suggested).

## 5. Proposed order (untested; marks to fix BEFORE running; the custom reader/talker thread owns the code and PC)

Per CLAUDE.md, one change at a time, each against plain B2 on the same seeds (2-seed screen, then 6-seed confirm):
- **W1, global attention after the window** (idea 1 above). Pass: pooled-5 >= B2 +1 on both seeds, cipher_map in_dist >= 95, no dev split drops more than 2, loops:0 leak no more than 1 above B2. Proved wrong: a cipher or lookup family drops by more than 2, or pooled-5 mean below 0.
- **H1, halting plus random round counts**. Pass: accuracy at 2x the needed rounds within 0.3 of at the needed rounds (the stability mark Test LR missed), chain-5 >= 99.
- **T1, external calculator call**. Pass: chain-5 >= 99, arithmetic families >= B2, swap lesion still >= 99% following. Proved wrong: below B2 by 3 on pooled-5.
- Deeper stack only after H1.
- Order recommendation: W1 first (cheapest, and it answers "more than 9 letters"), then H1, then T1.

## 5b. More thinking space: many hidden state vectors (Ben, 10:59 AM ET)

Shown (`ledger.py`): the thinker's state Z is 17 vectors: 8 control tokens plus 9 register tokens, each 256 wide (S) or 384 (M). The 8 controls pick the op, operands, mode and pointers. The 9 registers are tied one-to-one to the talker's answer characters. Only control 0 (step) and control 1 (final) are read by output heads. UPDATE (1:05 PM ET, from the custom reader/talker thread, s200 only): controls 2-7 ARE used. Zeroing them at test time costs -1.6 on pooled-5 and -7.8 on chain-5 (99.4 to 91.6). So the thinker has 6 used scratch vectors, and my 10:59 AM line "none is free scratch space" was wrong in wording (they are not free, they are used), and my 11:45 AM correction that they might be idle scratch was also wrong. W2's premise (more scratch could help) holds. The 17 vectors are the whole of the thinker's own memory.
So the families with no program in the data (rule_apply -6, fewshot_number_rule -9 vs plain_tf_steps, shown) have to be solved inside those 17 vectors.
Papers (suggested, only RMT's abstract was opened here): memory tokens in RMT 2207.06881 give a transformer extra writable slots. Pause tokens, register tokens in ViTs and Coconut continuous thought are from memory, not opened here, and say the same kind of thing: extra scratch positions or latent steps can help. Treat all as untested for our size.
Idea W2 (untested, cheap): add K = 16 learned scratch tokens to Z (on top of the 6 used scratch controls; the zeroing check has been run, see above). They take part in self-attention and cross-attention only; no head reads them. Extra parameters about 4k (16 x 256), no new heads. Compare B2 vs B2+W2, same seeds, 2-seed screen.
Pass: pooled-5 >= +1.0 on both seeds, rule_apply and fewshot_number_rule up, chain-5 >= 99, loops:0 in_dist no more than 1.0 above B2, no dev split down more than 2. Proved wrong: pooled-5 mean below 0, or the two no-program families do not move (then the limit is not space).
Caveat: space does not help if the limit is the data (the B1 students memorised), and the 7-step cap is separate (section 4).

## 6. A talker that speaks English (Ben, 10:50 AM ET)

Today (shown, REPORT.md): the talker writes short answers: a number, a copied word, or up to 8 letters. It does not produce sentences.
Earlier results that bear on this (shown, whole-model roadmap and PR #36/#37): a 350M reader+talker swap scored 66.1 vs 92.6, and a ~2M copy-and-gate talker scored 13.6 vs 78.2 on unseen questions. Talking from scratch is the roadmap's named main risk.
Suggested shape: the talker becomes a small language model that is conditioned on the thinker's state and on the question, and writes words token by token. Its tool calls (section 4) and its final reply would use the same English output, so the calculator call is just a sentence form like `calculate 12 plus 5`. Copying from the question stays (pointer-generator already exists), which keeps names, numbers and rare words exact.
It is a separate build from W1/H1/T1 (roadmap stage 9, "open-English talker", plus the stage 4b early talker probe). It needs English text to learn from. Ben already approved free human-written web text (FineWeb-Edu) for the bigger rungs, still no new teacher model; the pool plan is PR #47 and is waiting on the protected-panel overlap hashes. Untested: how small such a talker can be.
Open choices: train it with the thinker, or after (suggested: after, with the thinker frozen, so the thinker's score cannot be hurt).

## 7. Open question for Ben

Is T1 meant to replace the workspace (the exact numbered slots), or run alongside it? Alongside is a smaller first step; replacing is closer to what you wrote.

## 8. W1 and H1 specs, revised after review (12:55 PM ET, before any run)

**W1: global attention in the reader, as its own rung (one change).**
- First spec was 2-3 full global blocks at about 0.8M parameters each. That breaks the size band, because B2 is already +1.79% over plain_tf (3,302,481 vs 3,244,544) and the rule is +-3%, which leaves about 39k of headroom (3,244,544 x 1.03 = 3,341,880). It would count as two changes (widening and growing).
- Revised: low-rank global self-attention, inner width 32 (query, key, value and output at 256 x 32 each, about 32,768 weights plus biases, about 33k), one block after the +-4 window, same residual and LayerNorm pattern as the conv blocks. Whole size about 3,335,500, about +2.8% over plain_tf, inside the band. If the build thread needs more than about 39k, W1 stops and asks Ben for a size exemption (never silently).
- Marks, against plain B2 on the same seeds (2-seed screen 200/201, then a 6-seed confirm if it passes). Pooling is fixed here: "split down" and "family drops" are judged on the 2-seed mean at the screen and the 6-seed mean at the confirm, never per seed.
  - pooled-5 gain >= +1.0 on both screen seeds.
  - cipher_map in_dist >= 95 (2-seed mean) and no other family down more than 2.0 on the family splits (2-seed mean).
  - no dev split (in_dist, answer, frame, vocab, variant) down more than 2.0 (2-seed mean).
  - chain-5 >= 99.0 on both seeds; loops:0 in_dist <= B2's on the same seed + 1.0 and donor <= 5.
  - Proved wrong: pooled-5 mean below 0, or cipher_map (2-seed mean) down more than 2.0.
- Untested. Papers: Conformer 2005.08100, Zoology 2312.04927, H3 2212.14052 (abstracts only).

**H1: learned stopping, revised.**
- Per the no-hardcoding thread's note (not opened here, taken from them): Popescu 2026 (2607.20519) reports that a jointly trained halt gate distorts the loop, and that supervising every round plus a confidence stop often matched or beat it. So H1 changes from "a learned halt gate" to "per-round supervision plus a confidence-readout stop" (the same readout as Test LR's round readout, which already exists in code as `round_readout`), capped at 32 rounds.
- H1 is not required for B3 (T1's trace already says when to answer), so it stays on the roadmap as stage 2d and is not run before T1. Its mark is unchanged in spirit: accuracy at 2x the needed rounds within 0.3 of at the needed rounds, chain-5 >= 99, and no gain required at 8 rounds.

## 8a. W1 amendment 1 (1:45 PM ET, before any W1 run): the family mark is re-sealed

The custom reader/talker thread ran a null check on q33 (a plain B2 seed standing in for W1 against another; all 360 ordered choices of 4 of the 6 seeds; their report, not rechecked here). My mark "no other family down more than 2.0 (2-seed mean)" failed 100% of the time with no change at all (median worst family -6.6 pooled over the five splits, -10.0 on in_dist alone). So it could never pass, and it is replaced. No W1 result exists, so this is a repair of an impossible mark, not a loosening to fit a result.
For comparison from the same check: "no dev split down more than 2.0" fails 22% under the null, and the cipher_map proved-wrong line fires 6.7%. Both stay as written.

Replaced mark (the old family line is deleted; marks above it in section 8 are unchanged):
- **F1.** The four lookup-style families the bench named (cipher_map, fewshot_number_rule, group_induct, seq_cycle), pooled as one number on in_dist, 2-seed mean of (W1 minus plain B2): not down more than 2.0. cipher_map alone must still be >= 95 (2-seed mean).
- **F2 (usability check, fixed now).** `custom_io/analyze_gain.py` prints F1's null failure rate on the same 360 draws with every W1 verdict. If that rate is above 25% (the split mark's 22% is the accepted level), F1 is not usable and the fallback is automatic: only the cipher_map >= 95 line and the split mark apply, and the family check is reported, not judged.
- **F3.** Every other family's change is reported next to its null spread from the same check, never judged.
- Pass for W1 = the section 8 marks with the family line replaced by F1 (and F2's fallback if it applies). Proved wrong is unchanged: pooled-5 mean below 0, or cipher_map (2-seed mean) down more than 2.0.
- Untested. I have not seen the pooled null spread for the four families; F2 exists so nobody has to guess it.

## 8b. H1 is REQUIRED for B3, spec and marks sealed (2:55 PM ET, before any run)

Why required: Ben's rule 0 (2:45 PM ET): the deployed model decides how long to think itself. A fixed 8 rounds per turn is a researcher's choice at run time. (Source: no-hardcoding PLAN rule 0 and section 2a, as relayed; not mine to change.)

**Definition (suggested).** H1 changes the number of thinking rounds inside ONE turn of T1's loop, from a fixed 8 to a number the model picks, between 1 and a cap of 32. It is separate from the stop between calls (the call-or-answer choice T1 already makes).
- **Per-round supervision:** the existing round readout (`round_readout`, Test LR) is extended so T1's heads (call-or-answer and the call text) read the state after every round, each with the normal loss, weight 1.0, averaged over the rounds.
- **Stop head:** one linear layer (d + 1 = 257 params at d 256) reads the state after each round and predicts "this round's readout is already right". Its label is computed in training from the model's own readout against the target. No hand labels, no hand schedule.
- **Run rule:** the turn ends at the first round where the stop head says p >= 0.5, with at least 1 round and a hard cap of 32. 0.5 is fixed, not tuned on any data. (Per the no-hardcoding thread's note, Popescu 2026, 2607.20519, which I have not opened, reports that a jointly trained halt gate distorts the loop and that per-round supervision plus a confidence stop often matched or beat it. This design follows that note.)
- **Training rounds:** each batch draws its round cap K from {4, 8, 16, 32} and trains all rounds up to K, so extra rounds are seen and made safe. Cost: about 1.9x the forward passes per turn on average (an estimate; the speed probe fixes it).

**What it needs before it can be queued:**
1. T1 built and its speed probe done. H1 is a rung on T1's model, and its rounds-per-turn structure is T1's. The roadmap says H1 runs after T1 (stage 2d); to be queued it needs T1's screen result (2 seeds), not necessarily the 6-seed confirm, with T1 not proved wrong. If T1 is "not shown", H1 waits.
2. Code, from the reader/talker thread: (a) round readout over all rounds on T1's heads (extending `round_readout`), (b) the stop head and the early-exit inference loop, (c) per-batch round cap K, (d) per-row rounds-used logging, (e) a unit test that K=8 with the stop head ignored reproduces T1 exactly.
3. Size: +257 params, inside the band with T1.
4. A GPU slot: 2 screen runs (seeds 200 and 201), about 1.9x T1's cost each. Same-machine rule: T1's own screen scores on the same seeds are the baseline.
5. The PC time estimate comes from T1's speed probe; no rented GPU without Ben's OK.

**Marks (screen on seeds 200 and 201, each against T1 on the same seed; B3 copies them for its 6-seed confirm):**
- H-a Stability: pooled-5 with the rounds forced to the cap (32) minus pooled-5 at the model's own stopping point >= -0.3 on both seeds. (B2 reads -1.9 and -1.6 at 16 vs 8; Test LR missed this on one seed at -0.51.)
- H-b Parity: pooled-5 (H1 minus T1) >= -1.0 on both seeds; chain-5 >= 99.0 on both seeds; no dev split down more than 2.0 (2-seed mean).
- H-c Adaptive, not fixed: the mean rounds used on chain-5 turns is at least 2.0 above the mean on one-step families. Proved wrong on this line: the two means within 0.5 of each other, meaning the stop is not responding to difficulty.
- H-d Cap: turns that reach 32 rounds <= 1% (the world's safety cap, per PLAN section 2a), and the median turn stops before round 16.
- H-e Leaks: zero-round and donor in_dist <= 5 on both seeds under T1's definitions, with T1's and B2's values printed next to them. Test LR leaked at zero rounds (15.88 on s200), so a miss here is plausible and is read against T1's value on the same seed.
- H-f Audit: the stop rule is the learned head at fixed p >= 0.5; no per-dataset threshold anywhere in `generate()`.
- **Pass** = H-a to H-f. **Proved wrong:** pooled-5 (H1 minus T1) mean below -2.0, or H-c's line, or H-a below -1.0 on either seed.
- Untested. Not run. The build thread may tighten a mark before the first run, never loosen one after seeing a result.

## 8c. H1 amendment 1 (3:30 PM ET, before any H1 run): the stop label is "settled"

Question from the reader/talker thread (build 0526a2586, queue 49-pc-h1-screen, PASS-MARKS addendum 21): the sealed label ("this round's readout is already right") never fires on turns the model cannot get right, so a calibrated stop head thinks to the cap on exactly those turns. In q33 B2, 25% of pooled-5 rows sit in family cells below 50% (mostly the variant split; their figure, not rechecked), so H-d (cap hit <= 1%) could fail for that reason alone.

**Ruling: switch to `{"label":"settled"}` (right now, or no later round of this turn is right).**
- Why: with the sealed label, "when to stop" is only learned on solvable turns. Rule 0 means the deployed model also decides to stop when more thinking won't help, and "settled" teaches that. The label still comes only from the model's own per-round readouts against the target, so it needs no hand label, no hand schedule and no tuned threshold. H-f (audit) still holds as written.
- No H1 result exists, so this changes a design before any run; it is not tuned to a result. The "settled" code was tested for function only (their report), not for H1 outcomes.
- Marks: H-a to H-f unchanged, including H-d at 1%. I do NOT loosen H-d; "settled" is the fix for the reason H-d could fail. If H-d still misses, that is a finding and is reported, not re-marked.
- New reporting lines (not gates): (i) rounds used on rows right at the end versus wrong at the end; (ii) the share of stops that fired because the turn was already right versus settled-as-wrong; (iii) rounds used on the family cells below 50% in q33 B2.
- New risk, named: early in training the model is wrong at every round, so "settled" can label "stop at round 1" for everything and bias the head toward stopping early. If that collapses the head, H-c (chain-5 turns use at least 2.0 more rounds than one-step turns) and H-a catch it, and it is proved wrong on those lines. If it does, the named next change is a warm-up where the stop loss starts after the readout is right on most training turns (hand-set at build time, disclosed), not a threshold change.
- Disclosure from the build thread, accepted as is: each batch runs max(K, longest gold program + 1) rounds, so K=4 batches mostly run 8; cost about 1.9x T1. H1 still runs only after T1's screen is not proved wrong.
- Queue change: set the cfg to `{"label":"settled"}` in 49-pc-h1-screen before it starts.
