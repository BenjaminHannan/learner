# Looped thinking block: why the notes are ignored, and what inner-state matching can fix

Written 2026-10-25 by Claude (lead agent) with small research subagents. Research only: apart from this note and the GPT prompt in `reviews/`, no repo file edited, nothing trained or run.

Labels:
- **shown** = measured in the cited source or in Ben's brief, or read from a repo file;
- **suggested** = my reasoning;
- **untested** = nobody has run it on the village ruler.

How to read the evidence:
- Every paper number here is from math, logic or toy tasks. **None is a village result.**
- The toy plumbing check (§9) is kept apart from the village plan, and its numbers say nothing about village.
- Papers were read through a fetch tool that returns a machine summary of each page. Each fact was re-checked by a second agent. Check a number against the paper before building on it.

## 1. Plain-language summary for Ben

**Words used below**
- **Notes**: the 16 vectors the block writes for itself.
- **Lap**: one round in which the block rewrites its notes.
- **Gate**: a volume knob, set to zero at the start, that controls how much the notes reach the answer.
- **Two-hop question**: one that needs two facts chained, like "Ana is with Bo; Bo is in the mill; where is Ana?". Bo is the middle person.
- **Swap test**: give each question the notes from a different story, and see whether the score drops.
- **CODI**: a method that trains the model to copy a teacher's inner state just before it answers.
- **Teacher**: the same model when it writes its steps out in words.

**What your numbers show (shown)**
- In Think-1 only the notes block was trained; the rest of the model was frozen.
- 0, 4 and 12 laps all scored about 67. Swapping notes between stories cost nothing.
- Plain training for 1,254 more steps (no block) reached 70.8, so the block arm finished 3.8 points behind it.
- Think-2 trains both together and hasn't run yet.
- In a different test (an 8-billion-parameter model on a general-knowledge quiz), another group also saw no drop when hidden thoughts were swapped between questions.

**What might be going wrong (not checked yet)**
- **The knob may never have moved (suggested).** While the knob is at exactly zero, the note-writer gets no feedback at all. Once it moves, the feedback is multiplied by the knob's setting, so while the knob is small the feedback stays small. One free check reads the knob.
- **The answer has a shortcut (suggested).** It can read the whole story directly, so notes only help if they hold something the model can't work out in one look.
- **Nobody tells the notes what to hold (suggested).** Grading only the final answer never tells the note-writer what the notes should contain.
- **It could also be a plumbing bug.** That would also give flat laps and a free swap. A free check (force the knob open and see whether the answer changes) can show whether this is happening. It hasn't been run yet.

**Is copying the teacher's inner state (CODI) the fix? (suggested)**
- **It's a real lever.** In the CODI paper (shown there, on school maths), the copying loss is what made the hidden thoughts work.
- **But it's not the first thing to try, for two reasons.**
  - It grades the model's final "about to answer" state, and a plain model with no notes might learn to copy that state too. That is untested, so it needs a no-notes control that gets the same copying lesson.
  - Its feedback to the notes also has to pass through the knob.
- **Try it only if the teacher is clearly better** than answering directly (at least 2 points, set in §6 P1).

**What to try first** (in the full report these are Step 0, P0, T, P1, P2a and P2b)
0. **Check the data (no GPU).** Confirm which program made your stories. Keep the order of the reasoning steps in the data; this is a small code change. Read 20 examples by hand.
1. **Free checks on the checkpoints you have (about an hour, no training):**
   - force the knob open and see whether the answer changes, which shows whether the notes reach the answer at all;
   - read the knob;
   - see whether the notes differ between stories;
   - see whether the notes "know" the middle person.
2. **A tiny fake task (about a third of a Think-2 run).** The answer can't see the story, so only the notes can carry it. Pass: at least 90% correct, falling to near chance when the notes are swapped. Near chance even with the right notes means the code is broken. This is not village evidence.
3. **Two runs (about 3 Think-2 runs of time): one teaches the model to write its steps in words, the other uses filler text instead, as a check.** It gives the direct-answer score the notes must beat. Its written-steps score decides only whether copying a teacher is worth trying.
4. **If the knob stayed near zero:** start it at 0.3 instead of 0 (suggested value), and change nothing else.
5. **The main test.** A helper reads *only* the notes, and after lap k it must write step k of the reasoning (laps past the last step must write the answer). That gives the note-writer a real teacher.

**One decision for you before Think-2's results arrive**
- **Your rule now:** if Think-2 fails, drop looped thinking.
- **Proposed rule:** if Think-2 fails, run checks 0–5 above, plus the hide-the-story and copy-the-teacher tests if their entry conditions in §6 are met, then apply the give-up rule below. Think-2 still grades the notes only through the answer, so a fail can't tell "the loop is useless" from "the notes were never taught". If Think-2 passes, the loop continues, but run the free checks and swap test before saying the notes are used.
- Pick one now, before seeing the numbers.

**When to give up on the loop**
- **Keep the loop** only if at least one notes test (open the knob, step-graded notes, hide the story, or copy the teacher) clears every one of its bars. For step-graded notes, the bars are:
  - beat the best no-notes model by 2 or more points;
  - lose 1 or more points when notes are swapped or replaced by random ones;
  - beat a version that writes its notes in a single lap by 1 or more points;
  - the helper writes the steps clearly better from the right notes than from another story's notes (10 or more points).
- Each of the other tests has its own bars, fixed in §6 before it runs.
- **Drop it** if every notes test you run misses at least one bar, or if 18 runs the size of Think-2 are spent with no pass. A result that is close to a bar gets two more seeds before you decide.
- Your village target is 74.6, and plain training alone reached 70.8. A pass on these bars would not by itself mean 74.6 is reached. Report both.

## 2. What the brief's numbers show

| Run (Think-1: backbone and LoRA frozen, block trained) | Exact match, 8,675 val rows |
|---|---|
| LoRA, 418 steps (block's starting point) | 67.2 |
| S(8) block | 67.0 (seeds 66.8, 67.15) |
| Laps 0 / 4 / 12, same block | 67.09 / 67.15 / 67.16 |
| Swap lesion (another story's notes) | about 0 change |
| Plain LoRA, 1,254 more steps, no block | 70.8 (70.7, 71.0, 70.6) |
| Pass mark | 74.6 |

**shown:**
- The block's net effect is about 0 at every lap count, including 0 laps. Twelve laps move the score by 0.07, under one seed's spread (sd about 0.2).
- The swap lesion costs about 0.
- Plain training for 1,254 more steps is worth +3.6 (67.2 to 70.8). The block arm, with LoRA frozen at 418 steps, ended 3.8 below it. The brief doesn't say how many steps the block trained, so this is not a step-matched comparison.

**Not shown: why.** The same numbers fit three explanations:
1. The gate stayed closed. With tanh a ≈ 0, L0 must equal plain LoRA and any swap must cost 0.
2. The gate opened, but the notes are unused or constant.
3. A wiring bug means the block's output never reaches the answer.

P0 separates them. The brief doesn't give the block's learning rate or step count in Think-1. Record both, because a block that barely trained also gives these numbers.

**suggested:** Think-2's bar (+2 over the stronger control) sits below 74.6, so a Think-2 pass would not mean 74.6 is reached.

## 3. Diagnosis: why the notes are ignored

The thinking-block code is not in this repo (§11). The gate's form is taken from the brief: "the answer reads the notes through zero-init gates".

### 3.0 Rule out the dull explanations first

- **[untested] Wiring:** with the gate forced open, does the answer change at all? (P0, first row.)
- **[untested] Under-training:** did the refiner move from its start? A low learning rate or few steps would give flat laps without any deeper cause. (P0 reads its parameter drift.)
- **[suggested] The task may not need notes:**
  - Train questions need at most 3 hops, all facts are in the same context, and the no-block LoRA keeps improving.
  - Two-hop accuracy without thoughts is non-zero when both facts sit in one document, and near chance when they don't (two-hop curse paper, shown; no size recorded).
  - P0's per-depth accuracy shows where any headroom is.

### 3.1 The zero-start gate starves the note-writer at the start

- **[shown, algebra]** Write the read-out as h + tanh(a)·f(notes).
  - At a = 0, the gradient reaching the refiner and the note read-out is exactly 0; only a moves.
  - a's gradient is one number: the batch average of ⟨f(notes), ∂L/∂h⟩.
  - Once a ≠ 0, every gradient into the refiner is multiplied by tanh(a) ≈ a.
- **[suggested]** At the start the notes are whatever an untrained refiner writes, so that average is small and noisy. a may stay near 0 for a long time, and the refiner learns slowly; each waits for the other.
- **[suggested]** Compare LoRA, which also starts its B matrix at 0. B's gradient is a full matrix that can pick up any useful direction from step 1, whereas a scalar gate can only scale one fixed direction.
- **[untested]** Whether a stayed near 0 in Think-1.
- **[shown, Flamingo]** Flamingo used zero-init tanh gates for stability, and its side input was an image, which the model can't see any other way. Here the side input is computed from text the backbone already reads.

### 3.2 The answer has a direct path to the story (bypass)

- **[suggested]** The answer position can attend the whole story, so notes add value only if they compute something the backbone can't do in one pass. The cheapest solution for the optimiser is to ignore them.
- **[shown, other model and task]** Zhang et al. (Dec 2025, LLaMA-3 8B, MMLU) swapped Coconut hidden thoughts between questions: 60.9 → 61.0, no effect. Swapping written chain-of-thought dropped the score 62.8 → 43.4.
- **[shown, abstract only]** "Illusion of Superposition" reports that fine-tuned models leave latent thoughts unused and find shortcuts.

### 3.3 Answer-only grading gives the notes no target

- **[shown, other tasks]** Coconut without its step-replacing curriculum was no better than no thoughts, and much worse on ProntoQA:
  - GSM8k 14.4 vs 16.5;
  - ProntoQA 52.4 vs 93.8;
  - ProsQA 76.1 vs 76.7.
- **[shown, other tasks]** CODI with latents but without its matching loss scored 24.5 (GSM8k-Aug, GPT-2), against 43.7 with it.
  - In that arm the shared model still trained on written steps; only the latents went untaught.
  - The no-thought row reads 19.1, but the paper doesn't say which dataset that row used.
- **[suggested]** In both papers, slots taught only through the answer were far less useful than taught slots. Think-1 and Think-2 both grade the notes only through the answer.

### 3.4 Qwen3.5's mixed layers defeat attention masks

- **[shown, model card via fetch summary]** Qwen3.5-0.8B has 24 layers: 18 Gated DeltaNet (linear attention with a running state) and 6 full attention.
- **[suggested]** An attention mask changes only the 6 full-attention layers. The DeltaNet layers carry a running summary of every earlier token, story included, whatever the mask says.
- **[suggested] Consequence:** an "answer may not see the story" rule built as an attention mask would leak through the 18 DeltaNet layers. Check how Think-2's forced-reliance variant is built before reading its result (P0).

### 3.5 What P0 decides between

**Route in this order** (a row "fires" when its rule is met):
- Row 1 first.
- If row 2 or 3 fires, run P2a before P2b.
- Otherwise go straight to P2b.
- P3 comes only after P2b.

| # | Reading | Rule (fixed now) | Means | Next |
|---|---|---|---|---|
| 1 | Answer logits with the gate forced to tanh a = 0.5, 200 rows | max \|Δlogit\| ≤ 1e-3 | notes never reach the answer: wiring bug | fix the code; nothing else runs |
| 2 | Mean \|tanh a\| over gates | < 0.1 | gate closed (3.1) | P2a |
| 3 | Refiner drift ‖θ_end − θ_start‖ / ‖θ_start‖ | < 1% | block barely trained: starved or learning rate too low | P2a (and check the learning rate) |
| 4 | Zero-notes lesion vs swap lesion | zero "used", swap "unused" (§6.0) | notes act as a fixed prompt, not content | P2b |
| 5 | Story-to-story variance of notes / mean squared note norm | < 0.01 | notes barely depend on the story | P2b |
| 6 | Per-lap change ‖n(k+1) − n(k)‖ / ‖n(k)‖ after lap 1 | < 0.01 | refiner stuck at a fixed point | P2b |
| 7 | Bridge probe (P0): notes vs backbone ':' state | notes ≤ chance + 5 points while backbone ≥ chance + 20 | notes don't hold the chain (3.3) | P2b |

If the gate is open, the notes vary by story and the probe reads the bridge from them, yet swap is "unused", then the answer is ignoring good notes (3.2). P2b, then P3, is still the order.

## 4. Is hidden-state matching (CODI) the fix?

**Short answer [suggested]:** it is a real lever, possibly the strongest one. It isn't first in this plan, for reasons of cost and gating rather than evidence, and it needs a no-notes control.

**For matching:**
- **[shown]** In CODI's own ablation, matching is the ingredient that made the latents work: 43.7 with it vs 24.5 without (GSM8k, GPT-2).
- **[shown]** SIM-CoT step supervision on top of CODI added little at GPT-2 (42.0 → 42.6) and more at 1B (52.7 → 56.1). On top of Coconut it added more (GPT-2 36.6 → 44.8, 1B 33.2 → 42.2).
- **[suggested]** These are different comparisons: one *removes* matching from CODI, the other *adds* step supervision to CODI or Coconut. So the papers don't show which signal matters more, and matching may well be the stronger one. The GPT prompt in `reviews/` asks exactly this question.

**Against running it first:**
- **[untested]** CODI matches the *end* state (the ':' of "The answer is:"), not the steps. A LoRA with no notes might chase the same target straight from the story. CODI ran no "matching without latents" arm.
  - Two other methods learn from written steps with no thought slots, both **shown** on their tasks:
    - ICoT-KD: 4×4 multiplication 76.2 → 96.1 (GPT-2 Medium);
    - Stepwise Internalization: 9×9 multiplication 0.00 → 0.99 (GPT-2 Small).
  - So a CODI arm says nothing about the notes unless it beats a matched no-notes control (C2, P4).
- **[shown, algebra]** In Ben's block, the matching gradient reaches the refiner only through the gate (3.1). In CODI the latents sit in the sequence, with no gate.
- **[shown]** CODI needs a teacher worth copying. On GSM8k-style math, hidden-thought students stayed at or below written steps:
  - SIM-CoT reports explicit chain-of-thought SFT higher at every size (1B 58.4, 8B 71.7).
  - CODI LLaMA-1B was below written-steps SFT on all three out-of-distribution sets (12.8 / 96.1 / 61.1 vs 15.6 / 99.3 / 66.7).
- **[shown + suggested caveat]** On ProsQA (graph logic, nearest in shape to village chains), Coconut beat written steps, 97.0 vs 77.5. But blank pause slots with the same curriculum scored 96.6. So, suggested: most of the gain there came from the curriculum, not from what the slots held.
- **[shown]** Cost: CODI took about 36–48 h on one A100 80GB in the paper. No independent reproduction was found.

**So [suggested]:**
1. **P2b (step supervision) goes first.** It needs no teacher threshold, its signal reaches the notes without passing through the gate, and it is cheaper (one short decoder pass rather than a full teacher pass).
2. **P4 (matching) runs only if the written-steps teacher is clearly better** than direct answering and than filler text (P1). Its control gets the same matching with no notes.
3. **If outside opinions say "matching first", swapping the order is reasonable.** Both arms keep the same pass marks.

## 5. The inner-state matching recipe (for P4, and for Think-3)

| Choice | Recipe | Why / label |
|---|---|---|
| Token | The ':' ending "The answer is:" in both teacher (after written steps) and student (after the notes). First check how Qwen's tokenizer splits " is:" so the right position is matched. | CODI found nearby tokens within 2 std of each other, so the exact token barely matters (shown). The split is untested. |
| Layers | All 24 layer outputs (`hidden_states[1:]`), weight 1/24 each. Skip the embedding output, which is identical in teacher and student. Check whether the last entry is post-final-norm in Qwen3.5's HF code. | CODI uses all layers with equal weight (shown). |
| Teacher pass | Same live weights. The sequence is story + question + written steps (chain order) + "The answer is: X". Teacher CE keeps its gradient; the ':' states are detached as targets. | CODI trains teacher and student jointly with a stop-gradient on the teacher (shown). |
| Massive dims | On 200 teacher rows, per layer, flag dims whose median \|h\| at ':' is > 100× the layer median (threshold suggested, not from a paper), and leave them out of the loss. | In LLaMA2-7B, a few dims about 10,000× the median sit on the first token and the first '.'/newline; in LLaMA2-13B, on the first token only. They appear around layers 2–9 and fade in the last layers. Setting them to their mean is harmless; zeroing them breaks the model (shown). ':' and Qwen were not studied (untested); P0 scans for them. |
| Normalise | Per dim, z = (h − teacher median) / teacher IQR, from the same 200 rows. Clip z to ±5. | One massive dim inflates CODI's per-layer std and shrinks the loss on all other dims (suggested). CODI's prose says per-layer std, but its code listing uses one .std() (conflict seen in the fetch summary; check the PDF). |
| Loss | Smooth-L1 (β = 1) on z, mean over dims, then over layers. Log raw cosine per layer as a check only. | CODI uses L1 / smooth-L1 (shown). Cosine is dominated by the huge dims' direction (suggested). CKA on a batch of 8–16 is noisy and blind to scale (suggested). We found no paper comparing these at small batch (our searches weren't exhaustive). |
| Weights | Student CE = teacher CE = matching = 1 (CODI's GPT-2 setting). In the first 50 steps, log each term's gradient norm on the LoRA. If matching/CE is outside 0.1–10, rescale the matching weight once so the ratio is 1, and restart. | CODI's LLaMA weights appear three incompatible ways in the fetch summary of the paper; check the PDF or released scripts, and don't copy them blind. The rescale rule is suggested. |
| Learning rate | Keep Think-2's. | CODI's settings (3e-3 for GPT-2, 8e-4 for LLaMA-1B, rank 128, 10–40 epochs, batch 128) are for a far longer run (shown). |
| Memory | Compute LM-head logits only at the positions a loss uses (step and answer tokens, never the whole story). Use batch 1–2 with accumulation. Run a 20-step smoke test to measure peak memory and seconds per step before costing P4. | The vocabulary is large, and full-sequence logits for two passes are the main memory cost (suggested). |
| Per-lap alignment | Not with hidden states. Use the step decoder of P2b (lap k → written step k). | SIM-CoT aligns latent k to step k with a decoder (shown). Matching notes to teacher states at step ends is untested, and the notes may not live in the backbone's space. |
| Laps | Train at 4 (train questions have depth ≤ 3, plus one answer lap). Evaluate laps 0–6; claims only at 4. | CODI peaked at 6 latents, with more giving no gain and harder training (shown). In Think-at-Hard a second iteration broke 2.1% of correct answers (model and benchmark not stated; weak support). If the rows come from `learnlab/village`, val goes to depth 6 (scheduler.py:39); confirm from the rows' depth field. |
| Bypass | Open the gate (P2a); give the notes a direct target (P2b); hide the story by a separate forward pass, not a mask (P3). Never train against the swap lesion: it is the test. | §3. |

## 6. Experiments in order (one change each)

### 6.0 Rules for every test (fixed now)

**Rows:**
- Every pass mark uses all 8,675 val rows (Ben's ruler).
- Accuracy is also reported per depth (1–6) and as depth 1–3 vs 4–6, since train stops at depth 3 (scheduler.py:39, if the rows come from `learnlab/village`). The per-depth numbers carry no pass mark.

**Splits:**
- Tune nothing on val: learning rate, gate start and weights come from a dev split cut from train.
- The test split stays sealed until a final claim.

**Seeds (one rule):**
- Run seed 1 of the arm and of every comparator in its pass (each control inside a max(), the one-lap arm, C2).
- If every accuracy condition is met by ≥ 1 point, or missed by ≥ 1 point, decide on seed 1.
- Otherwise run seeds 2–3 of the arm and of the same comparators, and decide on the 3-seed means.
- Seed sd is about 0.2 (shown).
- Settings are never changed after a result is seen.
- Seed rounds come out of the 18 R cap. If the cap runs out first, a test still within 1 point of a bar is recorded as "not shown".

**Lesions** (eval only, on the trained arm):
- **Swap:** each row gets the final notes of a different story's row with the same depth.
- **Zero:** notes set to 0.
- **Random:** random notes with the same per-slot norm.
- A lesion counts as **"used"** if its cost is ≥ 1.0 point **and** the paired-bootstrap 95% interval excludes 0.
- It counts as **"unused"** if its cost is < 0.3.
- Anything else is "not shown".
- **Interval width (suggested arithmetic):** 1.96·√(flip rate / 8,675), about ±0.5 to ±0.7 points at 5–10% flipped rows. P0 measures the real flip rate between the two Think-1 S(8) seeds, if their per-row predictions were saved.

**Outcomes:**
- Pass (all conditions) = continue.
- Proved wrong = stop that test's line.
- Anything else = "not shown". It counts as a fail for the decision, but is reported as "not shown", not "proved wrong".

**Controls:**
- **C0'**: Think-2's "block off" control (same loss, block removed). It replaces 70.8 for joint-training arms.
- **C1**: from P1.
- **C2**: from P4.
- **Matching:** every control shares its arm's start checkpoint, optimizer steps, batch composition and data order. "Add X to arm Y" means "train Y's recipe from Think-2's start checkpoint with X added", never "continue training Y's checkpoint".

**Budget:** see §7. R = one Think-2-sized run, measured from Think-2's log before P1.

### Step 0. Data check (code only, no GPU)

- **Find which generator wrote the 8,675 rows** and the train rows. `learnlab/village` has no kinship relations, so it may not be the one.
- **If it is `learnlab/village`, keep the chain order.** Today the order is lost: Deriv.evidence is a frozenset (oracle.py:98-117), and the scheduler and data cache sort lines again (scheduler.py:278, data.py:348). Add an ordered `path` tuple beside the frozenset in `read/join/chain`, carry it into the shards, and rebuild them.
- **If it is another generator,** use its own record of the chain order if it keeps one. If no ordered step text can be built at all, P1, P2b, P3 and P4 can't run, and only P2a remains. Tell Ben before any GPU time is spent.
- **Dump 20 rows** (question, gold lines in chain order, answer) and check them by hand. If the lines don't answer the question, stop: P1, P2b, P3 and P4 all depend on them.
- **Rows without usable steps** get only "The answer is: X":
  - not-told questions (depth 0, no gold; data.py:350-352, 363);
  - rows whose evidence is long-range or from a prior visit.
  - Count these rows.

### P0. Free diagnostics on Think-1 (and Think-2) checkpoints (about 1 h, no training)

**The seven readings of §3.5, plus:**
- accuracy by depth for C0;
- the flip rate (§6.0);
- a massive-dim scan at ':' and at token 0, per layer;
- how the tokenizer splits "The answer is:";
- the block's learning rate and step count in Think-1.

**Bridge probe:**
- Use depth-2 rows. Label = the entity in both gold lines but not in the question.
- Chance = 1 / (number of candidate entities in the probe rows).
- Features: notes averaged over the 16 slots, at lap 0 and at the final lap. Compare with the backbone's ':' state on the same rows.
- Model: multinomial logistic regression, with L2 strength chosen by 5-fold cross-validation on the fit rows.
- Rows: fit on 2,000, test on 1,000, taken from val. That's allowed because P0 only reads checkpoints; no weights or settings are tuned on these rows.

**Code reads:**
- How the answer reads the notes (which layers and positions).
- How Think-2's forced-reliance variant hides the story: mask or separate pass (3.4)?

**Pass / wrong:** none. P0 routes only, by §3.5.

### T. Toy plumbing check (before P1; see §9)

### P1. Written-steps run: teacher and control (two runs, about 1.5 R each)

**The change:** train the LoRA with no block, from Think-2's starting checkpoint, for Think-2's 1,254 steps, on two formats.
- **Format:** every training row appears twice in its batch, once as "Step 1: <line>. Step 2: <line>. The answer is: X" (chain order, from Step 0) and once as a direct answer.
- **Effect on exposure:** every row's steps and every row's answer are seen. This matches P2b, where every row gets both an answer loss and step targets.

**Evaluation of this one run, two ways:**
- **T:** the model writes its own steps (greedy), and the answer after "The answer is:" is scored.
- **C1:** direct answer from the same weights.

**Sham run (second run):** the same, with each row's steps replaced by the same number of filler tokens (". . .", as in dot-by-dot).
- The sham is evaluated the same way as T: it writes its filler, then its answer is scored. So the extra test-time positions are matched and only the content differs.
- Report the mean generated tokens per row for T and the sham.

**Format check (no pass mark):** give the gold steps as input once and confirm the model reads the answer off them.

**What P1 decides (fixed now):**
- **P4 opens** only if T ≥ max(C0', C1) + 2 **and** T ≥ sham + 1. A teacher that isn't clearly better than answering directly is not worth copying; CODI and SIM-CoT students stayed at or below their teacher (§4).
- **C1 becomes a control** for P2b and P4.
- **Fixed reading for one case:** if T ≥ max(C0', C1) + 2 but T < sham + 1, P4 stays closed. Report it as "extra positions help; content not shown".
- **Proved wrong** (written steps teach this model nothing): T < max(C0', C1) + 0.5. P4 then closes, but the loop doesn't. Coconut on ProsQA gained from step data used as a curriculum even when written steps at test time didn't help (§4).
- **Report T against 74.6,** for the record.

### P2a. Open the gate (1 R; only if the rule in §3.5 row 2 or row 3 is met)

- **The change:** Think-2's recipe with every gate starting at a = 0.3 (tanh a ≈ 0.29) instead of 0. Nothing else changes.
  - If the loss blows up, record P2a as a failed run; don't patch it.
  - A zero-start low-rank read-out (LoRA-style) would be a separate later test, with its own control and pass mark, and is not part of this plan.
- **Controls:** C0' and the Think-2 arm it modifies.
- **Pass:** ≥ max(C0', Think-2 arm) + 2, **and** swap and random lesions both "used".
- **Proved wrong:** < Think-2 arm + 0.5, or swap "unused", while the gate is open on the new checkpoint (mean |tanh a| ≥ 0.1): the gate wasn't the problem.
- If the gate is still closed, the result is "not shown".
- **Afterwards:** if P2a ran, P2b keeps its gate start whether P2a passed or not. **[suggested]** An open gate only adds a path from the step-trained notes to the answer.

### P2b. Step-supervised notes: the main test of the loop (two runs, about 1.2 R each)

**The change:** add a step decoder that reads only the notes.

**Decoder:**
- **Weights:** the frozen base model with its own LoRA adapter (rank 16). The main LoRA is switched off during the decoder pass.
- **Input:** the 16 notes after lap k, mapped by one Linear(note_dim → 1,024) as `inputs_embeds` at positions 0–15. Read note_dim from the checkpoint.
- **Sequence:** the token embeddings of "Step k:" and the step text, with a causal mask and ordinary position ids.
- **Loss:** CE on the step tokens only.
- **It never sees the story or the question,** so the notes are its only source.

**Lap targets:** lap k → step k for k ≤ depth; later laps → "The answer is: X".

**Loss:** L = L_answer + 1.0 × mean over the 4 laps of L_step. Weight 1 throughout, as in SIM-CoT. Every lap has a target (a step or the answer), so every row gets the same weight.
- Untested variant, not this test: per-lap for half the run, then final only (LT2).

**Where the step gradient goes [suggested]:** into the decoder adapter, the linear map, the notes, and the refiner. It also reaches the main LoRA, through the backbone states the refiner reads. C1 controls for step text teaching the backbone directly. The lesions and the decoder swap test check that the notes themselves carry the gain.

**Base:** Think-2's recipe, 4 laps, gate start from P2a if it ran.

**Controls:**
- C0' and C1.
- A **one-lap arm** (the non-looped control): the refiner runs once, and the same lap-1 notes feed all four decoder passes ("Step 1:" … "Step 4:" or the answer).
  - Decoder passes, targets, optimizer steps, batches and parameter count all match the arm; the refiner is shared across laps, so the count is equal. Check that trainable-parameter totals agree.
  - Only the number of refiner laps differs, which is the thing tested.

**Pass (all four):**
- (a) arm ≥ max(C0', C1) + 2;
- (b) swap and random lesions both "used";
- (c) arm ≥ one-lap arm + 1;
- (d) decoder step-token accuracy from true notes beats swapped notes by ≥ 10 points.

**Proved wrong:** any one of these:
- arm < max(C0', C1) + 0.5;
- swap "unused";
- decoder gap (d) < 2 points (the notes don't hold the steps);
- arm < one-lap arm + 0.3 (looping doesn't help here; any one-shot gain is reported as a separate finding).

**Fixed reading for one case:** if (a), (b) and (d) pass but (c) doesn't, a one-shot side module with step targets helps, but looping isn't shown. P2b counts as a fail for the give-up rule, and the one-shot result is reported as a separate finding.

**Why no zero-notes-decoder or blank-slot control [suggested]:**
- If the decoder's input is zero or constant, the step loss can only train the decoder's own adapter and the bias of the linear map. No gradient reaches the notes, the refiner or the main LoRA, so the answer path is exactly C0' plus an unused decoder.
- The real confound is different. In the arm, step gradients reach the main LoRA through the backbone states the refiner reads, so the backbone itself could carry the gain.
  - Condition (b) catches the pure case: the answer would then not need the notes, and swap and random lesions would cost about 0.
  - For a mixed case, also report the arm's score under the swap lesion next to C0' as a rough split between "gain through the notes" and "gain in the backbone".

### P3. Make the answer use the notes (1.2 R; only if P2b's decoder gap (d) ≥ 10 but swap is not "used")

**The change:** add Think-2's force-then-release schedule to P2b, built as a **separate forward pass**.
- For a fraction p of rows, the answer is computed from [notes as `inputs_embeds`, question, "The answer is:"] with no story tokens at all.
- p goes from 0.5 to 0 over the first half of training.
- No packing, and no attention mask (3.4).

**Leakage test first:** hold the notes fixed and feed story A, then story B. The forced pass's answer logits must be identical to bf16 tolerance. If they aren't, the story leaks; fix it before P3 runs.

**Pass:** P2b's four conditions with P3 in place of the arm, **and** P3 ≥ P2b arm − 0.5. The P2b arm is P3's "schedule off" control.

**Proved wrong:** as for P2b.

### P4. CODI ':' matching (about 2 R per run, two runs; only if P1 opened it)

- **The change:** add the §5 matching loss to the recipe of the best notes arm that passed; if none passed, add it to the Think-2 arm's recipe (with P2a's gate start if P2a ran). Training starts from Think-2's start checkpoint (§6.0).
- **Control C2:** the identical setup with the block off, from the same start checkpoint. The student matches the teacher's ':' from story + question alone, as in no-slot distillation (ICoT-KD style).
- **Pass:** arm ≥ C2 + 2, **and** arm ≥ max(C0', C1) + 2, **and** swap and random lesions both "used".
- **Proved wrong:** arm < C2 + 0.5 (matching helped the backbone, not the notes), or swap "unused".
- **Fixed reading:** if arm ≥ max(C0', C1) + 2 but arm − C2 < 2, matching helps the model, but the loop isn't shown. P4 counts as a fail for the give-up rule.

### 6.9 The give-up rule (the same rule as §1, with test codes)

- **Keep the loop** only if at least one notes test (P2a, P2b, P3 or P4) passes every one of its bars.
- **Drop looped thinking on village at 0.8B** if every notes test that ran missed at least one bar, or if 18 R are spent with no pass.
- **When to check:** only after the seed rule has finished for every test that ran. A test that needed seeds 2–3 is judged on its 3-seed means.
- **What counts as having run:** P2a counts as a notes test only if it ran. If its gate stayed closed, its "not shown" counts as a miss.

**Amend Think-2's drop rule before its results arrive.** Ben decides, using the proposal in §1:
- If Think-2 fails: Step 0 → P0 → T → P1 → P2a (if routed) → P2b → P3 and P4 (each only if its entry condition is met), then this rule.
- If Think-2 passes: the loop continues, but run P0 and the three lesions before claiming the notes are used. If swap is not "used", the gain is not credited to the notes.

## 7. Order and budget

| Run | When | Cost (R = a Think-2-sized run) | Decides |
|---|---|---|---|
| Step 0 | always | no GPU | data is right; chain order |
| P0 | always | about 1 h eval, no training | route |
| T (toy, two runs) | always | about 0.3 | code works; lesions can detect use |
| P1 steps run (T and C1) | always | about 1.5 (rows appear twice) | C1; opens P4 or not |
| P1 sham run | always | about 1.5 | content vs extra positions |
| P2a | P0 row 2 or 3 | 1 | gate start |
| P2b arm | always | about 1.2 | **the loop test** |
| P2b one-lap arm | always | about 1.2 | looping vs one-shot |
| P3 | P2b decoder works, answer ignores | about 1.2 | bypass |
| P4 arm | P1 opened it | about 2 (teacher pass) | matching through notes |
| P4 control C2 | P1 opened it | about 2 | matching without notes |
| Seeds 2–3 for the deciding test and every comparator in its pass | only when within 1 point of a mark | about 6–10 (for P2b: arm, one-lap arm, C0', P1 runs) | noise |

**The cap:**
- Everything once is about 12 R. One seed round for the deciding test adds about 6–10 R, so the cap is **18 R**, seed rounds included. If it runs out, §6.0 says what is recorded.
- The usual path (no P2a, P3 or P4) is about 6 R without extra seeds, and about 16 R with one seed round for P2b.
- R is measured from Think-2's log before P1. Think-2 itself does not count.

**Not in this plan [suggested]:** Stepwise Internalization with no block (remove written steps a few tokens at a time).
- It is shown to work with no slots on multiplication and GSM8k.
- If the goal is the village score rather than the loop, it is a cheap, strong candidate.
- It is also the control any curriculum-style loop arm would have to beat.

## 8. Think-2 and Think-3

**Think-2 (queued):**
- Record the gate values, the three lesions and per-depth accuracy with the results.
- Read the forced-reliance arm with 3.4 in mind.

**Think-3 (CODI on K2-Horizon-3.7B, sealed plan):**
- **Define "off".** K2 offers reasoning_effort high/medium/low and no documented off (shown). For example, prefill an empty think block; check K2's chat template.
- **Gate 0 on a paired 1,000-row subset first,** stratified by depth, with the same rows for thinking on and off.
  - The paired 95% half-width is 1.96·√(flip rate / 1,000), about ±2.0 to ±2.8 points at 10–20% flipped rows, so an 8-point gap clears it (suggested arithmetic).
  - Unpaired it would be about ±3.5 to ±4.4, depending on accuracy (suggested arithmetic).
  - Run the full set only if the subset passes.
- **Teacher format:** use the generator's short written steps, not K2's long traces. K2 wrote about 2.4× the median length on one benchmark (shown).
- **Normalisation:** say which one you use; CODI's prose and code disagree (§5).
- **Memory:** 5.06B stored parameters is about 10 GB in bf16 before activations. A teacher pass plus a student pass will likely not fit 16 GB without a 4-bit base or short sequences (suggested, untested).
- **Timing:** don't start Think-3 before a village pass at 0.8B. If the loop can't use its notes at 0.8B, a bigger model adds cost, not a new answer.

## 9. Toy plumbing check (separate from village; its numbers say nothing about village)

**Purpose:** prove the code can carry information through the notes, and that the lesions can detect it (a positive control for the swap test).

**Task:**
- Two-hop facts with random names and 10 possible places (chance = 10%), such as "Ana is with Bo. Bo is in the mill. Where is Ana?".
- The story goes only to the refiner. The answer pass holds only [notes, question, "The answer is:"], as a separate forward pass.
- Same block and backbone as village. 2,000 training rows, 500 eval rows, 4 laps. 1,000 steps at batch 16, evaluated every 50 steps.

**Pass:** eval exact match ≥ 90%, with the swap and zero lesions both dropping it to ≤ 20%.

**Gate check:** run it twice, with the gate starting at a = 0 and at a = 0.3.
- If a = 0 needs more than twice as many steps to reach its first ≥ 90% check (or never reaches it), starvation (3.1) is shown on the toy.
- Log the refiner's gradient norm over the first 100 steps of both runs.

**Proved wrong (a code bug):**
- ≤ 20% with true notes; or
- ≥ 90% with a swap cost under 10 points (the lesion code isn't swapping).

**Cost:** under 1 h for both runs.

## 10. Sources

| # | Source | Read how | Notes |
|---|---|---|---|
| 1 | CODI, https://arxiv.org/abs/2502.21074 | HTML + PDF via fetch summary | Authors only; no independent reproduction found |
| 2 | SIM-CoT, https://arxiv.org/abs/2509.20317 | HTML, two fetches | Authors only |
| 3 | Coconut, https://arxiv.org/abs/2412.06769 | HTML via fetch | Authors only |
| 4 | Pause tokens, https://arxiv.org/abs/2310.02226 | HTML via fetch | |
| 5 | Dot by dot, https://arxiv.org/abs/2404.15758 | HTML via fetch | 3SUM numbers are best of 5 runs |
| 6 | Zhang et al., latent swap, https://arxiv.org/abs/2512.21711 | HTML via fetch | Independent of Coconut's authors |
| 7 | Illusion of Superposition, https://arxiv.org/abs/2604.06374 | abstract only | |
| 8 | Flamingo, https://arxiv.org/abs/2204.14198 | HTML via fetch | gate form |
| 9 | Gist tokens, https://arxiv.org/abs/2304.08467 | abstract | Exact mask from memory; not used for any decision |
| 10 | Huginn / recurrent depth, https://arxiv.org/abs/2502.05171 | HTML via fetch | |
| 11 | LT2, https://arxiv.org/abs/2605.20670 | HTML via fetch | No per-loop ablation number |
| 12 | LOTUS, https://arxiv.org/abs/2606.31779 | abstract | |
| 13 | Think-at-Hard, https://arxiv.org/abs/2511.08577 | HTML + PDF via fetch | Model behind the 8.7% / 2.1% not stated |
| 14 | Massive activations, https://arxiv.org/abs/2402.17762 | HTML via fetch | LLaMA-2 and Mixtral only |
| 15 | TinyBERT https://arxiv.org/abs/1909.10351; DistilBERT https://arxiv.org/abs/1910.01108 | fetch / snippets | TinyBERT loss formula from memory |
| 16 | ICoT-KD, https://arxiv.org/abs/2311.01460 | HTML via fetch | |
| 17 | Stepwise Internalization, https://arxiv.org/abs/2405.14838 | HTML via fetch | |
| 18 | Two-hop curse, https://arxiv.org/abs/2411.16353 | HTML + PDF via fetch | |
| 19 | Grokked transformers, https://arxiv.org/abs/2405.15071 | HTML via fetch | Toy, in-distribution only |
| 20 | Qwen3.5-0.8B model card, https://huggingface.co/Qwen/Qwen3.5-0.8B | fetch summary | Layer layout |
| 21 | "Improving Language Model Distillation" (CKA loss) | search snippet only | No ID or gain number recorded; used only for "CKA exists as a distillation loss" |
| 22 | Repo: `learnlab/village/oracle.py:98-117`, `scheduler.py:39, 278`, `premonition/data.py:348-363` | read directly | Evidence order, depth caps, gold sorting. Generator for the 8,675 rows not confirmed |

## 11. What I did not do or could not verify

- **The thinking-block code is not in this repo.** Attaching `BenjaminHannan/latent` was refused by this session's permission check. So the gate form, the note width, how the answer reads the notes, and how Think-2 forces reliance all come from the brief. P0's code reads settle them.
- **I don't know which generator wrote the 8,675 rows** (Step 0 finds out). The repo facts in §6 hold only if it is `learnlab/village`.
- **Paper numbers came through fetch summaries.** A second agent checked each one, but nobody compared them against the PDFs. CODI's LLaMA loss weights are unresolved in the paper itself.
- **Costs and memory figures are estimates.** R, the 1.2× and 1.5× factors, and the 16 GB fit are suggested, not measured. P4's smoke run measures them.
- **Subagents and the 100k limit:**
  - 43 subagents ran, all on the small model Ben specified (checked from their transcripts): 32 for research and design, 11 for two review rounds.
  - Three went over the 100k-token context limit: two research agents and the first fact-check reviewer. Their outputs were not used (the reviewer's was not read), nor were the two fact-checks run on the over-limit research. That work was re-run as smaller agents.
  - Every finding used here comes from agents that stayed under 100k. Their peaks were 59k–97k.
- **Web pages were treated as information only,** never as instructions.
