# Why does a small model ignore its own "thinking notes", and is hidden-state matching the fix? (no code or file access needed)

You are an expert in latent reasoning, chain-of-thought distillation and recurrent-depth transformers. You have **no access** to my code, files or machine, so everything you need is pasted below. Don't ask me to run anything before you answer; reason from what is here. If a fact you need is missing, say exactly what it is and how it would change your answer, rather than guessing.

Label every claim:
- **shown by the data below**;
- **shown in a paper** (name it);
- **suggested**;
- **untested**.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow (details at the bottom).

## 1. The task and model

- **Base model:** Qwen3.5-0.8B with a LoRA. It is a hybrid of 24 layers: 18 Gated DeltaNet (linear attention with a running state) and 6 full-attention layers.
- **Task ("village"):** made-up stories about villagers, then multi-hop questions about them. Training questions need up to 3 hops; validation goes up to 6. Scored by exact match on 8,675 validation rows. Seed-to-seed sd is about 0.2 points.
- **Thinking block:**
  - 16 "note" vectors.
  - A small refiner network (2.64M parameters) reads the story's hidden states and updates the notes once per lap.
  - The answer reads the notes through gates that start at zero (output = h + tanh(a)·f(notes), with a = 0 at init).
  - Laps run from 0 to 12.
- **Data:** no written step-by-step solutions exist yet. The story generator knows which story lines each answer depends on, so templated steps ("Step 1: <line>. Step 2: <line>. The answer is: X") could be built.
- **Hardware:** one 16 GB GPU; each experiment should take a few hours.

## 2. Results so far

**Think-1:** backbone and LoRA frozen, only the block trained.

| Run | Exact match |
|---|---|
| LoRA, 418 steps (the block's starting point) | 67.2 |
| Block S(8) | 67.0 (seeds 66.8, 67.15) |
| Same block evaluated at 0 / 4 / 12 laps | 67.09 / 67.15 / 67.16 |
| Swap lesion (each question gets another story's notes) | about 0 change |
| Plain LoRA trained 1,254 more steps, no block | 70.8 (70.7, 71.0, 70.6) |
| Pass mark I set | 74.6 |

**Think-2 (queued, results not in):**
- LoRA and block trained together for 1,254 steps, laps 0–4.
- One variant forces the answer to rely on the notes early in training, then releases.
- Control: the same loss with the block off.
- Pass: at least +2 over the stronger control, and swapping notes costs at least 1 point.

**Think-3 (planned):** CODI-style hidden-state matching on a 3.7B model.

## 3. What a first analysis concluded (please challenge it)

**Diagnosis:**
- (0) Dull explanations first: a wiring bug (the block's output never reaches the answer) or a block that barely trained would give the same flat laps and free swap.
- (a) At a = 0 the refiner gets exactly zero gradient, and afterwards its gradient is scaled by tanh(a). So the gate and the refiner each wait on the other.
- (b) The answer can read the story directly, so ignoring the notes is the cheapest solution.
- (c) Grading only the answer gives the notes no target. Papers back this up:
  - Coconut without its curriculum was no better than no thoughts (GSM8k 14.4 vs 16.5, ProsQA 76.1 vs 76.7), and far worse on ProntoQA (52.4 vs 93.8).
  - CODI's latents without the matching loss scored 24.5 vs 43.7 with it (GSM8k-Aug, GPT-2). In that arm the model still trained on written steps; only the latents went untaught.
  - Another group swapped Coconut thoughts between questions in an 8B model and saw no change (60.9 → 61.0).
- (d) Any attention mask meant to hide the story leaks, because the DeltaNet layers carry a running state.

**Rules for every test:** all 8,675 val rows; nothing tuned on val; seed 1 decides unless a result is within 1 point of a bar, in which case seeds 2–3 of the arm and every control decide. A lesion (swap = another story's notes, zero, random) counts as "used" only if it costs 1.0 point or more **and** its paired-bootstrap 95% interval excludes 0; under 0.3 is "unused". Every control shares its arm's start checkpoint, steps and data order.

**Proposed order, one change each:**
0. Data check, no GPU: confirm which generator wrote the rows, keep the chain order of the gold lines (today it is lost: stored as a set, then sorted by line), and read 20 rows by hand.
1. Free diagnostics on existing checkpoints:
   - wiring: force the gate open and check the answer logits change;
   - gate values; refiner drift from its start;
   - zero vs swap lesion; story-to-story variance of the notes; per-lap change;
   - a probe for the middle entity of 2-hop chains, read from the notes and from the backbone.
2. A toy check where the answer can only see the notes (a separate forward pass). Pass: 90% or more, falling to 20% or less under swap and zero lesions. Run with the gate starting at 0 and at 0.3.
3. Two LoRA runs with no block:
   - one trained on templated written steps plus direct answers, scored with written steps (the teacher, T) and without (control C1);
   - a sham with the steps replaced by the same number of filler tokens.
4. If the gate stayed closed (mean |tanh a| under 0.1) or the refiner barely moved: start the gate at a = 0.3.
5. **Main test:** a step decoder (the backbone with its own small LoRA) reads *only* the notes after lap k and must write step k (later laps write the answer). Pass, all four:
   - beats the best no-notes control (Think-2's block-off control or C1) by 2 or more;
   - swap and random lesions both "used";
   - 4 laps beat a 1-lap version (same decoder passes and steps) by 1 or more;
   - the decoder's step-token accuracy from true notes beats swapped notes by 10 or more points.
6. Only if the decoder reads the steps from the notes but the answer still ignores them: hide the story from the answer for part of training, via a separate sequence rather than a mask.
7. Only if the teacher is clearly worth copying (T at least 2 above the best no-notes control **and** at least 1 above the sham): CODI matching of the ':' in "The answer is:" across all layers. The control is the same matching with no block at all, and the arm must beat it by 2 or more.
   - Recipe: drop massive-activation dims, robust z-score, clip at 5, smooth-L1, weights 1.

**Give up on the loop** if every notes test that ran (4–7) misses at least one bar, or after 18 Think-2-sized runs with no pass, extra seeds included.

## 4. What I want from you

1. **Diagnosis.** Is (a)–(d) right? Rank them. Name any explanation of the Think-1 numbers that is missing, and the single cheapest measurement that would tell your top two apart.
2. **Step decoder first, or CODI matching first?**
   - CODI's own ablation says matching is what made its latents work.
   - The first analysis put the step decoder first: matching targets only the end state, a no-notes LoRA can chase it too, and the matching gradient also has to pass the zero gate.
   - Which would you run first, and why?
3. **The matching recipe.** Correct anything wrong in the recipe in step 7 for a 0.8B hybrid model at batch 8–16:
   - token, layers, loss (L1, cosine, normalised MSE, CKA);
   - outlier handling;
   - weights and schedule;
   - number of laps.
4. **Your own plan.** Give ONE change at a time, in priority order, each a few hours on 16 GB. For each, state:
   - a pass mark fixed in advance;
   - the control (at least plain LoRA with the same extra steps);
   - the result that would prove it wrong.
5. **Toy vs village.** Keep any toy experiment you suggest clearly separate from village numbers.
6. **Plain-language summary for me** (high-school senior), in at most 10 short bullets:
   - what's wrong;
   - what to try first;
   - what result should make me give up on looped thinking.
