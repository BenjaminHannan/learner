# D7: Literature scout B (arXiv): why decoders ignore latent state, and which recipes make them use it

Date: 2026-10-08 (ET; clock time not recorded). Scout: Haiku worker, literature only.
Budget used: 14 of 14 arXiv fetches; about 20 of 35 tool calls. No repo files read, no edits, no GPU, no training.

## Scope and labels

- **shown** = I read the arXiv abstract page (arxiv.org/abs/<id>) in this session.
- **suggested** = from a search snippet, a secondary summary, or my recall of the paper body. Not on the abstract page.
- **untested** = a proposal I have not run.
- These results are literature. They belong to neither the card experiments nor the village model.
- The PR #37 numbers (talker 13.6% vs 78.2%; pretrained 1.2B "allptr" 92.6%, 350M 66.1%) come from the task brief. I did not open the PR branches or the diag files, so I have not checked them.

## Why a decoder ignores the state (the "why" part)

1. **Bypass when the input is visible.** 2602.00449 (shown) finds that CODI builds intermediate "bridge" states on 2-3 hop tasks, but the final input reaches the answer readout through a near-direct, copy-like route. On longer chains the partial latent path collapses under regime shift. This is the closest match to the PR #37 symptom (the LM barely uses the core on unseen kinds), though that link is my reading, not a result from either paper.
2. **Latent slots are not used.** 2512.21711 (shown) finds Coconut tokens barely respond to steering, unlike explicit CoT tokens. On MMLU and HotpotQA, Coconut exploits dataset artifacts.
3. **Posterior collapse.** 1909.00868 (abstract shown for the title and result; mechanism suggested): a strong decoder can fall into a trivial optimum that ignores the latent. Suggested mechanism, from the search snippet and recall.
4. **Auxiliary hidden-state losses can change the state without changing the output.** 2605.15394 (shown): of 22 JEPA-style auxiliary losses added to LoRA fine-tuning, none survived multiple-comparison correction, and a decoder-visible variant aligned gradients with cross-entropy but left exact match within seed noise.

## Papers (12 verified abstracts)

1. **arXiv 2412.06769**, "Training Large Language Models to Reason in a Continuous Latent Space" (Coconut), 2024.
   - Shown (abstract): the last hidden state is fed back as a continuous reasoning state. It beats CoT on logic tasks that need heavy planning search.
   - Suggested (not on the abstract): staged curriculum that swaps language reasoning steps for latent steps.
   - Relevance: the state is never decoded, so nothing checks whether it is used. See item 3.

2. **arXiv 2502.21074**, "CODI: Compressing Chain-of-Thought into Continuous Space via Self-Distillation", 2025.
   - Shown (abstract): an explicit-CoT teacher and an implicit student are trained together. The student matches the teacher's hidden activation at one chosen token. At GPT-2 scale it matches explicit CoT on GSM8k, with 3.1x compression.
   - Recipe: hidden-state matching as an auxiliary loss. See ranking item 3.

3. **arXiv 2512.21711**, "Do Latent Tokens Think? A Causal and Adversarial Analysis of Chain-of-Continuous-Thought", 2025.
   - Shown (abstract): Coconut tokens show little sensitivity to steering and carry little reasoning-critical information. On MMLU and HotpotQA they exploit dataset artifacts.
   - Suggested recipe: perturbation or steering tests as the faithfulness check. If the output barely moves when the state is edited, the state is not used.

4. **arXiv 2602.00449**, "Do Latent-CoT Models Think Step-by-Step? A Mechanistic Study on Sequential Reasoning Tasks", 2026.
   - Shown (abstract): on 2-3 hop tasks, CODI builds faithful intermediate bridges, while the final input goes through a near-direct route. Longer chains give only a partial path.
   - Suggested recipe: test per hop length, and ablate the direct route to see what breaks.

5. **arXiv 2204.14198**, "Flamingo: a Visual Language Model for Few-Shot Learning", 2022.
   - Shown (abstract): adapts to new image and video tasks from a few in-prompt examples, with no fine-tuning. It beats models fine-tuned on thousands of times more task data.
   - Suggested (secondary search summary, not the abstract): the LM stays frozen. New gated cross-attention blocks sit between LM layers. Their output is multiplied by tanh(alpha), with alpha initialised to 0, so the model starts identical to the frozen LM. Visual input goes through a Perceiver Resampler to 64 tokens.
   - Recipe: zero-initialised gated bridge into a frozen LM. Untested here.

6. **arXiv 2301.12597**, "BLIP-2: Bootstrapping Language-Image Pre-training with Frozen Image Encoders and Large Language Models", 2023.
   - Shown (abstract): a lightweight Q-Former bridges a frozen image encoder and a frozen LLM, trained in two stages. It beats Flamingo80B by 8.7% on zero-shot VQAv2 with 54x fewer trainable parameters.
   - Recipe: a query bottleneck, so the decoder sees only learned query outputs and never the raw input. Stage 1 learns the representation against the encoder; stage 2 trains generation against the frozen LLM.

7. **arXiv 1909.00868**, "A Surprisingly Effective Fix for Deep Latent Variable Modeling of Text", 2019.
   - Shown (abstract): combining two known collapse heuristics improves held-out likelihood, reconstruction, and latent representation over prior SOTA.
   - Suggested (search snippet, not the abstract): the two heuristics are autoencoder pretraining of the encoder and KL thresholding (free bits). A strong decoder can settle into ignoring the latent.
   - Recipe: pretrain the encoder as an autoencoder, then apply a free-bits KL floor. Untested here.

8. **arXiv 1803.00144**, "Learning Longer-term Dependencies in RNNs with Auxiliary Losses", 2018.
   - Shown (abstract): an unsupervised auxiliary loss makes the RNN reconstruct earlier events or predict upcoming ones. It helps both truncated and full BPTT. Results go up to 16,000-step sequences.
   - Recipe: reconstruction or prediction loss on the state. This is an RNN, not an LM, so the transfer to a talker is suggested.

9. **arXiv 2502.08213**, "LLM Modules: Knowledge Transfer from a Large to a Small Model using Enhanced Cross-Attention", 2025.
   - Shown (abstract): a frozen Qwen2-1.5B feeds its representations through added attention layers into GPT-Neo-125M. After 15 epochs on Bespoke-Stratos-17k, its responses are comparable in quality to distillation.
   - Limits: one dataset, not a QA benchmark. No from-scratch arm.

10. **arXiv 1511.06349**, "Generating Sentences from a Continuous Space", 2015 (CoNLL 2016).
    - Shown (abstract): an RNN-VAE encodes a whole sentence as a latent vector. Sampling and interpolation give well-formed sentences.
    - Suggested (recall, not the abstract): word dropout on decoder inputs and KL annealing as counters to collapse. Untested here.

11. **arXiv 2107.14795**, "Perceiver IO: A General Architecture for Structured Inputs & Outputs", 2021.
    - Shown (abstract): a flexible querying mechanism supports outputs of varying size and meaning. It beats a BERT-style Transformer on GLUE without tokenisation.
    - Suggested: the query-decoder details (learned queries attending to a latent array) are not on the abstract.

12. **arXiv 2605.15394**, "Representation Without Reward: A JEPA Audit for LLM Fine-Tuning", 2026.
    - Shown (abstract): 22 JEPA-style auxiliary losses on LoRA fine-tuning of Llama-3.2-1B-Instruct for natural-language-to-regex. None survive multiple-comparison correction. A decoder-visible variant gives the first positive gradient alignment with cross-entropy, but exact match stays within seed noise, and full fine-tuning gives the same null.
    - Recipe: a negative result. Hidden-state auxiliary losses need an output-level check.

**Verified but excluded:** arXiv 2411.16353 (two-hop latent reasoning). Abstract shown: facts learned in separate documents give chance-level two-hop answers without CoT. The v1 title is "The Two-Hop Curse: LLMs trained on A->B, B->C fail to learn A->C" (2024); the current title is "Lessons from Studying Two-Hop Latent Reasoning." Excluded because it is about composing facts (the thinker's job), not about decoders ignoring their conditioning.

**Search-only leads, not verified, not in the list:** 1712.08207 (bypass connections in seq2seq VAEs), 1711.11479 (auxiliary-guided autoregressive VAE; auxiliary loss as initialisation), 2108.02446 (finetuning pretrained transformers into VAEs), 1911.03976 (pooling against collapse), 2511.05963 (NextLat), 2604.04902 (interpretability of Coconut and CODI), 2602.22441 (latent step-count shortcut test), 1711.05411 (Z-Forcing), 1901.03416 (delta-VAE), 2212.10012 (latent situations with auxiliary decoding), 2501.07818, 2603.16413.

## Ranked recipes to test first

Shared falsifier, the **state-swap test**: on held-out questions, replace the thinker state with the state from a different example that has a different answer. Record whether the talker answers the swapped example or the original question. An answer that follows the original question means the decoder is bypassing the state.
- Pass and fail thresholds are my suggestion, fixed here, untested: pass if at least 80% of swapped cases answer the swapped example; fail if more than 20% still answer the original question.

1. **Remove the bypass path (suggested; BLIP-2 / Perceiver IO pattern).** The talker reads thinker states only through a small set of learned query vectors. It gets no raw question tokens.
   - Falsifier: if the state-swap test still fails with the question tokens absent, the bypass lives inside the thinker or the state itself, and this recipe does not hold.

2. **Zero-initialised gated bridge with two-stage training (suggested; Flamingo / BLIP-2 pattern), paired with 1.** The talker LM is pretrained on simple English and frozen. A gated cross-attention bridge into the thinker state starts with gate 0. Stage 1 trains the bridge alone; stage 2 unfreezes.
   - Pretraining alone is not enough. A pretrained LM that can see the question is the allptr pattern, which does not remove bypass.
   - Falsifier: the state-swap test still fails after stage 2.
   - Gap: no verified comparison of an LM-pretrained talker against a from-scratch talker on the same bridge.

3. **Output-level auxiliary decode-back loss (suggested; CODI-style matching as the alternative), tested last.** The thinker state must be able to reconstruct the question, or the auxiliary must alter held-out answers. Hidden-state alignment alone is not enough, per 2605.15394.
   - Falsifier: the auxiliary improves hidden-state alignment, but the state-swap bypass rate does not change.
   - Overlap: the project's TEACH "say-back question" target resembles this. That target comes from the user's memory index (talker rules, 2026-10-08); I did not re-read it.

## Open questions and gaps

- No verified paper compares a small decoder pretrained as an LM and attached to a frozen encoder against the same decoder trained from scratch on QA. LLM Modules and BLIP-2 are indirect evidence only, and both decoders were pretrained.
- The Coconut curriculum details and the Flamingo gate ablation numbers are not confirmed from full text.
- The PR #37 and allptr numbers are from the brief and are unchecked.
- Whether the state-swap test is a sufficient faithfulness check is untested. 2512.21711 supports perturbation tests as a practice, but not this exact test.

## Handoff for a fresh scout

Within 14 fetches, verify on the abstract page:
- ClipCap (a small mapping network into frozen GPT-2);
- TinyStories (very small LMs writing fluent English);
- 1712.08207 (bypass connections in seq2seq VAEs);
- 1711.11479 (auxiliary loss as initialisation);
- 2108.02446 (Park and Lee, finetuning pretrained transformers into VAEs);
- 2511.05963 (NextLat);
- 2602.22441 (latent step-count shortcut test).

Also check whether the Coconut curriculum and the Flamingo gate-ablation numbers appear in full text.
