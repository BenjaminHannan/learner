# Why didn't looping a pretrained model's middle layers help? Pick the one next test (no code or file access needed)

You are an expert in looped / recurrent-depth transformers, adaptive computation, and fine-tuning small language models. You have **no access** to my code, files or machine, so everything you need is pasted below. Do not ask me to run anything before you answer; reason from what is here. If a fact you need is missing, say exactly what it is and how it would change your answer rather than guessing. Mark every claim as **shown by the data below**, **suggested**, or **untested**. All numbers are one seed on one GPU, so treat differences under about 1 point as noise unless a paired interval says otherwise.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow (details at the bottom).

## 1. Goal

I want a small local assistant that "thinks by looping": it runs some internal computation several times before answering (no written-out reasoning), and decides by itself how many loops each question gets. The test below is on a 0.8B model I can train cheaply. It is a test bed, not the final model.

## 2. The task ("village", synthetic, scored by exact match)

Each prompt is a story of a day in a village (about 1,180 tokens): people, objects, containers, places, and rules such as "lost things are returned to their owners every night". Then one question with a short phrase answer. Every question has a **depth** = the number of reasoning hops needed (1-6; depth 0 = "the story doesn't say").

- **Training rows have depth 1-3 only.** Depth 4-6 is never trained, so it tests whether the model can go deeper than it was taught.
- Validation: 8,675 rows. By depth: 1: 2,656; 2: 2,057; 3: 1,868; 4: 1,168; 5: 364; 6: 26; 0: 536.
- For every question the generator also knows the gold evidence lines, in the order a person would chain them (about 38 tokens of step text on average).

## 3. The model and the looped arm ("br")

- Backbone: Qwen3.5-0.8B. 24 layers: 18 Gated DeltaNet (linear attention / recurrent state) layers and 6 full-attention layers.
- All arms use a LoRA adapter (rank 16, all layers). They all start from the same short LoRA run "a" (418 steps).
- **br:** layers 8-11 (a 4-layer middle block) are run r times in a row. Same weights and same LoRA each time; each pass has its own attention / DeltaNet cache, so pass k+1 attends to its own keys and values. **There is no input injection.** Pass k+1 takes pass k's output hidden state, and nothing re-feeds the output of layers 0-7. **The loss is answer cross-entropy at the final pass only.** Gradients flow through all passes.
- Training: 1,254 steps, batch 16, ~24M tokens in total. r is drawn per step as 1 + Poisson(m-1), capped at 6, with m ramped from 1 to 4 over the first 75% of steps (mean r 2.80; r = 1 on 24% of steps).
- Controls:
  - **aplus:** the same LoRA trained 1,254 more steps with no loop.
  - **aplong:** the same, trained 1,630 steps. That matches br's extra layer compute (1.30x).
  - **tc:** the best earlier control (LoRA with a slightly different loss recipe, 1,254 steps).
- Scoring: greedy decoding, br evaluated at fixed r = 1, 2, 3, 4, 6, 8.

## 4. Results (validation %, seed 0, all arms on the same GPU)

| slice | n | br r1 | br r2 | br r3 | br r4 | br r6 | br r8 | aplus | tc | aplong |
|---|---|---|---|---|---|---|---|---|---|---|
| all | 8,675 | 70.37 | **72.20** | 71.80 | 71.26 | 69.82 | 66.05 | 70.26 | 71.99 | 71.97 |
| depth 1-3 | 6,581 | 76.77 | 78.35 | n/a | 76.86 | n/a | 70.57 | 76.58 | 77.83 | 77.89 |
| depth 4-6 | 1,558 | 44.74 | 47.18 | n/a | 47.37 | n/a | 43.77 | 44.74 | 46.79 | 47.05 |

The pass marks were fixed before the run:
- **F1:** br at r = 4 beats the best control by at least 2 points, with the paired interval above 0. Result: r4 − best control = −0.73, 95% CI [−1.49, −0.20]. **Proved wrong.**
- **F2:** on depth 4-6, r4 − r1 is at least +2, and r8 is at least r4 − 1. Result: the rise is +2.63 [+1.03, +4.30], but r8 − r4 = −3.59. **Fail.** Also, the r1 → r4 rise is no bigger than what plain extra training gives (aplong 47.05 vs aplus 44.74).

**Training-free halting.** Stop at the first r (from 1, 2, 3, 4, 6, 8) whose answer equals the previous r's answer. This scores 72.16% at a mean of 2.17 loops. Mean loops by depth:

| depth | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| mean loops | 2.21 | 2.11 | 2.14 | 2.21 | 2.24 | 2.42 |

Spearman(depth, loops) = 0.06. It saves compute, but it does not spend more loops on harder questions.

The same r = 1 checkpoint scores a separate copy of the adapter on a different GPU (AMD) to within 0.02 points, so the hardware is not the issue.

## 5. Earlier results that bear on this

Several things have failed on the deep rows:

- **Notes block.** A separate "thinking block" had 16 note vectors refined once per lap by a small network, and the answer read them through gated cross-attention. It did not help. Laps 0, 1, 2, 4 and 8 were flat. In a blind read (answer sees only the notes), accuracy was 26 / 25 / 25 / 26 / 23% across laps, with no gain on deep rows. The notes did carry story content (37% with the true notes vs 6.5% with notes swapped between stories), but with the story visible the answer ignored them.
- **A different, bigger model.** K2-3.7B, base, untrained on this task, about 300 rows:
  - Its written thinking mode scored 8.75 points WORSE on depth 4-6 than answering directly.
  - Giving it the gold evidence lines did not help the deep rows (25.0 vs 27.5).
  - Repeating any of its blocks without training hurt or tied.
  - This is weak evidence: base K2 only gets about 25% overall.
- **Not yet run:**
  - **P1.** The 0.8B LoRA is trained to *write* the gold steps and then the answer, against a sham that writes the same number of dot tokens. This tells us whether explicit step-by-step reasoning helps this model on this task at all, including depth 4-6.
  - **P2a and P2b** are variants of the notes block.

## 6. What published work suggests (as I understand it; correct me)

- **McLeish et al. 2025, "retrofitted recurrence"** (TinyLlama / OLMo / Llama-1B):
  - The model is split into prelude, recurrent middle and coda. The state starts as noise, and a linear adapter merges [state, prelude output] at every step (input injection).
  - The loop count is sampled with its mean ramped up, with backprop through the last 8 steps.
  - About 50B tokens. Gains appear at large loop counts (r = 32) and vanish at r = 1.
- **Huginn-3.5B** was trained from scratch on 800B tokens: GSM8K 0 at r = 1 and 34.8 at r = 32.
- **Ouro / LoopLM** (1.4B and 2.6B, 7.7T tokens, 4 loops) has a learned exit gate trained with a loss at every loop step plus an entropy term. On MMLU the gate gives about 66% at 2.5 loops vs 67% at 4 fixed loops.
- **Training-free halting** ("stop when the answer stops changing") is reported within 1-2 points of a trained gate. Evidence that loops rise with difficulty is thin.

## 7. Constraints

- One consumer GPU (16 GB). One run of this size takes 2-7 hours. No paid cloud this week.
- One change at a time. Every test needs pass marks fixed in advance, a compute-matched no-loop control, and the result that would prove it wrong.
- The 0.8B test bed and the bigger models are kept separate. Do not mix their results.

## 8. What I want from you

1. **Diagnosis.** Why does br peak at r = 2 and collapse by r = 8? Why does the deep-row gain match plain extra training? For each explanation, give the result from data I already have, or from one cheap test, that would tell it apart from the others. Candidates I have, but don't limit yourself to these:
   - (a) far too little training (24M tokens vs billions);
   - (b) no input injection, so the state drifts off-distribution past the trained loop counts;
   - (c) loss only at the final pass, so intermediate passes are never asked to be useful;
   - (d) depth 4-6 failures are not a compute-depth problem at all (for example, long-context retrieval, or rule types never seen in training), so no amount of looping helps;
   - (e) looping layers 8-11 is the wrong block, or a 4-layer block of a 24-layer model is too small or too large.
2. **The single next test.** Name exactly one change against br, or one diagnostic, to run next on the 0.8B. Give:
   - the arms and the matched control;
   - pass marks fixed in advance;
   - the result that would prove it wrong;
   - roughly how long it takes on one 16 GB GPU (br took about 3 hours).

   If you think a diagnostic must come before any new loop arm (for example, "first show depth 4-6 is a compute problem"), say so and make that the single test.
3. **Halting.** Given the flat loops-by-depth, is "the model decides how many loops" worth pursuing on this task yet? What signal should halting be trained on, and what result would show it is spending more loops on harder questions for a reason?
4. **Is there a known recipe** for retrofitting recurrence onto a pretrained model with only about 25M fine-tuning tokens? Or is the honest answer that it needs billions? If billions, what is the cheapest credible alternative for my goal? Examples: an open model that is already looped, such as Ouro, or written reasoning distilled into silent loops.
5. **A plain-language summary for me** (a high-school senior): what went wrong, what to try next, and why, in 5-8 sentences without jargon.
