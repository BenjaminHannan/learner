# Offline "sleep" and consolidation methods for Premonition after 0.1 (research note, 2026-09-24)

Labels: **SHOWN** means I read it in the paper's full text or in a repo file. **SUGGESTED** means an inference, or something I only saw in an abstract or search snippet (marked "abstract-only"). **UNTESTED** means an idea with no evidence yet. Papers were read as full-text arXiv PDFs unless marked otherwise.

## Repo facts checked
- `step()` checks `sleep_due()` before the inbox, so SLEEP runs before LISTENING (scripts/fable_agent_loop.py:293-298). `_sleep_tick` starts at :383. `StubSleeper` records the request and changes nothing (:189-198). The sleep threshold is a fixed 20 (:52). **SHOWN**
- 339 is a registered FAIL: 17/40 saved right (bar 32) and 2/20 control lives saved something (bar 0) (design/v3/30-modes/00-director-board.md:25). **SHOWN**
- One correction to the brief: on 296, varied practice fixed 294's style overfit. Two-step scored 30/30 and big notebooks 15/15, but three-step was 0/30 ("never practised"). The FAIL was on P296.4, the fresh total (225 and 217 vs 228) (00-director-board.md:35). So "6-11/30 blind two-step" fits 294, not 296. **SHOWN**

## 1. Why facts must stay out of the weights
- **Gekhman et al. 2024 (2405.05904).** Model: PaLM 2-S. Task: closed-book QA with the share of Unknown fine-tuning examples varied. The model fits Unknown examples much more slowly than Known ones, and as it fits them its hallucination rises roughly linearly (abstract; §1). Early stopping, or filtering out the Unknown examples, reduces the harm (§1). **SHOWN**
- The key result for Premonition is Table 3 (§7). Relabelling the Unknown examples as "I don't know" gave 61.8% accuracy on answered questions at both early stop and convergence. The plain mix fell from 43.0 to 38.8. The share of questions answered dropped to 58.7 and then 55.6. **SHOWN**
- **Fit: strong.** Training new facts into the reasoner teaches it to guess. Training "the fact is missing, so say I don't know" is protective. **SUGGESTED**, extrapolated from a single model family.

## 2. Sleep-time compute and agent memory systems
**Sleep-time compute (Lin, Snell et al. 2025, 2504.13171)**
- What it does: before any query arrives, the model rewrites the context c into c′, which holds inferences and likely questions (S(c)→c′, §3). **SHOWN**
- What was measured: about 5× less test-time compute for the same accuracy, up to +13% (Stateful GSM-Symbolic) and +18% (Stateful AIME), and 2.5× lower cost per query when related queries share a context (abstract). Gains track how predictable the query is from the context (abstract). **SHOWN**
- Scale: API models only (GPT-4o/4o-mini, o1, o3-mini, Claude 3.7 Sonnet, R1; §4). No weights change. **SHOWN**
- **Fit: exact match for the disposable derived layer.** c′ is derived, costs only inference, and never touches the notebook. The risk is wrong inferences, so every c′ line needs provenance pointers back to notebook entries. **SUGGESTED**

**MemGPT (2310.08560)**
- What it does: OS-style tiers. The model pages data between main context and recall/archival storage, and gets "memory pressure" warnings before a recursive summary evicts old messages (§2). **SHOWN**
- **Fit:** it is an engineering pattern, not learning. The summaries are derived, so they would belong in the disposable layer. **SUGGESTED**

**A-MEM (2502.12110)**
- What it does: Zettelkasten-style notes with links. "Memory evolution" rewrites the stored context, keywords and tags of older notes when a new note arrives (§3.3). **SHOWN**
- Measured on Llama-3.2-1B, LoCoMo benchmark (Table 1): single-hop F1 went from 12.86 (full-context LoCoMo baseline) to 28.51, and multi-hop from 11.25 to 19.06. It used about 1,376 tokens per question against 16,910. It ran locally via Ollama (§4.2). **SHOWN**
- **Fit: it breaks append-only.** Evolution overwrites old notes. Use it only on the derived layer, never on taught facts. **SUGGESTED**

**Generative Agents reflection (2304.03442)**
- What it does: reflection triggers when summed importance passes 150, about 2-3 times a game day. The model asks for the "3 most salient questions" over the 100 most recent records, then writes insights that cite the records they rest on ("because of 1, 5, 3") (§4.2). **SHOWN**
- Failure seen: agents "embellished" (§6.5.2). For example, one attributed *Wealth of Nations* to a neighbour named Adam Smith, pulling from the LLM's world knowledge. **SHOWN**
- Cost: 2 days of simulation cost "thousands of dollars" in tokens (§8). **SHOWN**
- **Fit:** the citation pattern maps onto provenance. The embellishment result is a direct warning for Ben's idea #31 (confabulation hunting): every reflection line has to be checked against the entries it cites. **SUGGESTED**

## 3. Replay and rehearsal against forgetting
**Deep Generative Replay (Shin et al. 2017, 1705.08690)**
- What it does: a generator plus a solver (together, a "scholar"). Generated old-task samples are mixed with new data at ratio r. Tested on MNIST/SVHN image tasks (§3-4). **SHOWN**

**van de Ven, Siegelmann, Tolias 2020, brain-inspired replay (Nature Comms 11:4069)**
- What it does: replays internal (hidden) representations generated by the network's own context-modulated feedback connections. Reported as state of the art on class-incremental CIFAR-100. Abstract-only, **SUGGESTED**.
- Its precursor, 1809.10635, shows that regularisation methods such as EWC fail when task identity must be inferred, while generative replay plus distillation works in all three scenarios (abstract). **SHOWN**

**Self-Synthesized Rehearsal, SSR (2403.01244)**
- What it does: the LLM version of generative replay. The base model makes synthetic inputs by in-context learning, the latest model writes the outputs, and diverse instances are kept for rehearsal (abstract). **SHOWN**
- Scale: Llama-2-7B, Llama-2-7B-chat and Alpaca-7B on 10 SuperNI tasks. It outperforms rehearsal baselines that use real data (§4). **SHOWN**

**Tadros et al. 2022 (Nature Comms 13:7742)**
- What it does: sleep as offline local Hebbian plasticity driven by noisy input. It recovers old tasks lost in incremental learning. Abstract-only via PubMed/escholarship, **SUGGESTED**.
- Follow-up (2402.10956): sleep helps MNIST models trained on 0.5-10% of the data. Above 10% it hurts slightly unless followed by fine-tuning. **SHOWN**
- **Fit:** only small networks were tested. It does not transfer to a 1B transformer without a new mechanism. **SUGGESTED**

**Wake-Sleep (Hinton et al. 1995, Science; not on arXiv)**
- What it does: recognition and generative networks train each other in alternating phases. Not fetched, **SUGGESTED**.
- Modern LLM descendant: "Dreaming" (Behrouz et al. 2606.03979). RL generates a synthetic curriculum to rehearse new knowledge (abstract), and one experiment uses a Llama-3.2-1B backbone (§5). **SHOWN**

**Fit for the whole section:** rehearse skills, not facts. The replay buffer should be Premonition's own frozen skill suite (answers built from the notebook, abstentions, style obedience), regenerated by SSR-style self-synthesis. **SUGGESTED**

## 4. Distilling context into weights
**Context distillation (Snell et al. 2022, 2209.15189)**
- What it does: the teacher is the same model conditioned on [instructions]+[input] and producing [scratchpad]+[answer]. The student learns the answer from the input alone (abstract). **SHOWN**
- What was measured: 8-digit addition on T5-small rose from 1% to 17% direct accuracy (§3.3, Table 3). It beat gradient descent by 9% on SPIDER Text-to-SQL (abstract). Instructions were internalised on T5-11B (§3.1), and later distillations "overwrite old ones" (abstract). **SHOWN**

**Prompt Baking (2409.13697)**
- What it does: a LoRA that minimises KL(P(·|u) ‖ P_θu(·)), "often in as little as 5 minutes" (abstract, §2). Base model: Llama 3. **SHOWN**
- What was measured:
  - Baking CoT prompts improves GSM8K/ASDiv/MBPP (abstract).
  - Baking one benchmark's prompt costs at most 3.4% on other benchmarks (§3.5).
  - Baking personas cuts persona drift (§3.7).
  - Knowledge baking on 20 questions scored 77.5% against 80% for prompting (Table 1).
  - "Half-baking facts sometimes caused models to hallucinate" (§3.6).
  **SHOWN**
- **Fit for 339 (style):** bake the habit of obeying whatever style rule is in the notebook's context, trained over many varied synthetic preferences. Do not bake "no buddy" itself. The preference stays a taught fact in the notebook, and the adapter learns to comply. **UNTESTED**

**SEAL (2506.10943)**
- What it does: RL teaches the model to write its own fine-tuning data ("self-edits"). **SHOWN**
- What was measured: on Llama-3.2-1B, simplified ARC reached 72.5% success against 20% without RL and 0% for ICL (Table 4.1). **SHOWN**
- Cost and limits: each reward evaluation takes 30-45 s because it fine-tunes and evaluates a whole model (§6), and it still forgets (§6, Fig. 6). **SHOWN**
- **Fit:** too expensive for a $4 job. **SUGGESTED**

## 5. Continual LoRA
**LoRA Learns Less and Forgets Less (2405.09673)**
- Model: Llama-2-7B. LoRA underperforms full fine-tuning on code and math but keeps more out-of-domain ability, and forgets less than weight decay or dropout does (abstract). **SHOWN**

**O-LoRA (2310.14152)**
- What it does: each task gets a LoRA subspace kept orthogonal to the others, with no replay data (abstract). **SHOWN**
- What was measured: on T5-large, the standard continual-learning benchmark averaged 75.8 against 80.0 for multi-task learning and 57.8 for Replay. On a long sequence of tasks, sequential LoRA collapsed to 1.6 (Table 2). On LLaMA-7B, MMLU fell to 33.6 against 23.3 for sequential LoRA (Table 3). **SHOWN**
- **Fit:** one orthogonal adapter per skill sleep keeps each sleep's gains separable and able to be rolled back, which matches the 145 merge work. **SUGGESTED**

**Nightly LoRA consolidation (Dennis et al. 2026, 2605.24657): the closest analogue to Premonition's setup**
- What it does: Claude Sonnet 4 extracts facts from a chat and writes 20 paraphrased chats per fact (about 18k examples). Qwen2.5-7B then trains a LoRA (r=16) for 8 epochs (§2, App. C). **SHOWN**
- What was measured: 80.4% knowledge retained against 36.8% for cascading compaction. Procedural corrections rose from 36.3% to 74.6% (abstract). **SHOWN**
- Cost: 8.2 h on an RTX 5090 per conversation, about $5 per user-night (§5). **SHOWN**
- Limits: it measures no abstention or false claims and no MMLU (Limitations). **SHOWN**
- **Fit:** it is the anti-pattern for facts, but its procedural numbers suggest the skill and style half does work. At 1B with fewer examples it should fit inside $4 (10 h at $0.40). **SUGGESTED**

## 6. The loop-ladder idea (#14)
**Offline recurrence (Lee et al. 2605.26099)**
- What it does: during sleep the model runs N offline recurrent passes, writing fast weights in its SSM blocks. **SHOWN**
- What was measured: larger N helps most on deeper reasoning, including GSM-Infinite on Jet-Nemotron-2B and Ouro-1.4B (abstract, §6.3). **SHOWN**
- Cost: about 12 H100 GPU-days per run (§5). It needs SSM blocks, which a plain transformer lacks. **SHOWN**
- **Fit:** the principle supports #14, but the method does not transfer at this budget or with this architecture. **SUGGESTED**

## What this means for Premonition after 0.1
1. **Two kinds of sleep with separate outputs:**
   - Derived-layer sleep: sleep-time compute or reflection with cited provenance. It is disposable and costs inference only.
   - Skill sleep: a LoRA trained only on episodes where the notebook text is in the context, so the model never learns a fact as a target without its source.
   **SUGGESTED**
2. **Every skill-sleep batch includes relabelled missing-fact items ("I don't know")**, following Gekhman Table 3, plus early stopping on a blind panel. **SUGGESTED**
3. **Replay the frozen skill suite at 10-20% of the mix, self-synthesised as in SSR.** Use one orthogonal adapter per sleep as in O-LoRA. **UNTESTED** (the mix ratio is my guess)

## One experiment to hand to the director (numbers are proposals for the director to fix in advance)
- **Change:** a skill-sleep LoRA on MiniCPM5-1B trained with notebook-in-context practice, 30% of it "I don't know" relabels, with early stopping on a held-out blind set. Nothing else changes. **UNTESTED**
- **Proposed pass marks:**
  - blind three-step at 10/30 or better (296 got 0/30);
  - 0 invented answers on missing-fact items;
  - 0 false saves;
  - at most 2 points lost on existing panels;
  - under $4.
- **Proves it wrong:** gains show up only on items in the generator's own style while blind items stay flat. That would repeat the D1 finding (00-director-board.md:60).

## Plain summary for Ben
Putting new facts into a model's weights teaches it to make things up (2405.05904). So your rule of facts in the notebook only is backed by research. Sleep should train habits instead: how to look things up in the notebook, how to chain facts together, when to say "I don't know", and how to follow a style rule it reads in the notebook. "Thinking ahead" during sleep (2504.13171) is a safe extra, as long as its outputs go only in the throwaway layer and point back to the notebook entries they came from.

Sources:
- [Tadros et al., Nature Comms 2022](https://www.nature.com/articles/s41467-022-34938-7)
- [van de Ven et al., Nature Comms 2020](https://www.nature.com/articles/s41467-020-17866-2)
- [arXiv 2605.26099](https://arxiv.org/abs/2605.26099)
- [arXiv 2605.24657](https://arxiv.org/pdf/2605.24657)
- [arXiv 2606.03979](https://arxiv.org/html/2606.03979v1)