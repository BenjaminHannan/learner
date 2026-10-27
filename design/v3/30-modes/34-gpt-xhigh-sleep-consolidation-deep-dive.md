# Sleep that internalizes lessons instead of answers

The central idea is **plausible and testable, but not solved**. Research already shows that neural networks can move useful information from temporary context/replay into weights, sometimes even learning an algorithm rather than examples. What nobody has demonstrated is a general-purpose assistant that autonomously decides, night after night, which experiences contain reusable lessons, safely consolidates them into weights, and avoids accumulating mistakes. Ben's design should therefore treat sleep as a **compiler from episodic experience → verified training curriculum → candidate weights**, not as ordinary fine-tuning on yesterday's conversations.

## 1\. What research already tells us

| Research line | Main finding | Shown at ≤8B / tiny scale? |
| --- | --- | --- |
| **STaR — *Bootstrapping Reasoning With Reasoning* (2022, arXiv:2203.14465)** | Generate reasoning, retain solutions that reach correct answers, then train on those traces. It improved reasoning more than answer-only fine-tuning. [arXiv](https://arxiv.org/abs/2203.14465) | **Yes.** GPT-J 6B was used; importantly, GPT-2 could not bootstrap even arithmetic, showing a lower-capability limit. [arXiv](https://arxiv.org/abs/2203.14465) |
| **ReSTEM — *Beyond Human Data* (2023, arXiv:2312.06585)** | Generate attempts, filter them using verifiable feedback, fine-tune, repeat. This substantially improved math/coding reasoning. [arXiv](https://arxiv.org/abs/2312.06585?utm_source=chatgpt.com) | Original result used PaLM-2; ≤8B evidence from this paper: **no**. |
| **Context distillation — *Learning by Distilling Context* (2022, arXiv:2209.15189)** | A model can solve problems using instructions/scratchpads, then train itself to produce the result without that context. The paper explicitly demonstrated internalizing addition reasoning. [arXiv](https://arxiv.org/abs/2209.15189) | **Strong yes:** T5-small went from 0% to 94.7% direct addition accuracy after distilling scratchpad reasoning; InCoder-6.7B was also tested. [arXiv](https://arxiv.org/abs/2209.15189) |
| **Prompt Baking (2024, arXiv:2409.13697)** | Minimizes KL divergence between a prompted teacher and unprompted updated model, transferring prompt-induced behavior into weights; chain-of-thought baking improved reasoning benchmarks. [arXiv](https://arxiv.org/abs/2409.13697) | Sub-8B applicability looks plausible, but the exact model-size detail I would cite from the paper is **unverified**. |
| **Complementary Learning Systems — McClelland, McNaughton & O'Reilly (1995)** | Fast episodic memory plus slow interleaved cortical learning avoids destructive interference and extracts structure shared across experiences. [PubMed](https://pubmed.ncbi.nlm.nih.gov/7624455/?utm_source=chatgpt.com) | **Yes, conceptually**, in small neural models; not originally transformers. |
| **Deep Generative Replay (2017, arXiv:1705.08690)** | Generate approximations of old experiences and mix them with new training to reduce catastrophic forgetting. [arXiv](https://arxiv.org/abs/1705.08690?utm_source=chatgpt.com) | **Yes**, small networks. |
| **Sleep-like replay — Tadros et al. (2022)** | Offline spontaneous replay reduced catastrophic forgetting across MNIST, Fashion-MNIST, CIFAR-10 and CUB-200. [Nature](https://www.nature.com/articles/s41467-022-34938-7?utm_source=chatgpt.com) | **Yes**, small/non-language networks. |
| **EWC (2016, arXiv:1612.00796)** | Penalizing changes to weights important for old tasks reduces forgetting. [arXiv](https://arxiv.org/abs/1612.00796?utm_source=chatgpt.com) | **Yes**, small nets; less convincing as the sole solution for LLMs. |
| **LoRA / QLoRA (2021/2023, arXiv:2106.09685, 2305.14314)** | Keep base weights frozen and learn small low-rank updates; QLoRA makes this feasible with quantized models. [arXiv+1](https://arxiv.org/abs/2106.09685?utm_source=chatgpt.com) | **Yes**, including well beyond 8B. Very relevant to a 16 GB GPU. |
| **Sparse fine-tuning — SpIEL (2024, arXiv:2401.16405)** | Store/update a small selected subset of parameters instead of dense weight changes; competitive with LoRA in instruction tuning. [arXiv](https://arxiv.org/abs/2401.16405?utm_source=chatgpt.com) | **Yes**, LLaMA-2 7B and 13B. |
| **Model merging — Task Arithmetic / TIES (2022/2023, arXiv:2212.04089, 2306.01708)** | Independently trained weight deltas can sometimes be combined, but conflicting directions cause interference; TIES explicitly tries to remove those conflicts. [arXiv+1](https://arxiv.org/abs/2212.04089?utm_source=chatgpt.com) | **Relevant**, but not a guarantee that many nightly updates remain composable. |
| **Knowledge editing — ROME/MEMIT (2022, arXiv:2202.05262, 2210.07229)** | Individual factual associations can be changed directly in model weights. ROME worked on GPT-J 6B; MEMIT scaled to thousands of edits. [arXiv+1](https://arxiv.org/abs/2202.05262?utm_source=chatgpt.com) | **Yes**, including 6B. But brittle: MQUAKE showed edits often failed to propagate through multi-hop consequences. [arXiv](https://arxiv.org/pdf/2305.14795?utm_source=chatgpt.com) |
| **Synthetic “textbooks” — phi-1 (2023, arXiv:2306.11644)** | Carefully written synthetic explanations/exercises can train far more efficiently than dumping raw data into a model. [arXiv](https://arxiv.org/abs/2306.11644?utm_source=chatgpt.com) | **Yes:** 350M and 1.3B models. |
| **Grokking (2022, arXiv:2201.02177)** | Tiny transformers can first memorize an algorithmic dataset and only much later discover a rule that generalizes perfectly. [arXiv](https://arxiv.org/abs/2201.02177?utm_source=chatgpt.com) | **Yes, tiny scale.** |
| **Test-Time Training (2019, arXiv:1909.13231)** | Updating weights from self-supervised test-time experience can adapt models to changing distributions. [arXiv](https://arxiv.org/abs/1909.13231?utm_source=chatgpt.com) | **Yes**, but mainly vision in the original work and fundamentally different from safe long-term memory. |

The strongest direct evidence for Ben's goal is **context distillation + STaR + replay**, not knowledge editing. Knowledge editors are designed to implant associations; Ben wants **compression of repeated structure**.

## 2\. What makes weights learn a procedure rather than answers?

Suppose the notebook contains:

> 47 × 6 → 282  
> 38 × 7 → 266  
> 64 × 8 → 512

Repeating those examples during training rewards memorization. Instead, sleep should extract:

> Multiply right-to-left. Carry tens into the next column.

Then generate hundreds of **new operands** from that rule.

The important levers are:

1. **Never train mainly on the practised instances.** Generate fresh instances from the hypothesized lesson.
2. **Hold the original episodes out of the main exam.** Otherwise memorization looks like learning.
3. Train on **worked intermediate steps**, not merely answer tokens.
4. Create an explicit **abstraction stage**: episodes → proposed lesson → synthetic exercises.
5. Mix old capabilities/replay data into training so the new gradient cannot dominate everything else.
6. Prefer small adapters or sparse deltas initially; committing directly into all base weights is harder to undo.
7. Train across varying surface forms, lengths and contexts. Otherwise the model learns a template rather than the procedure.

The decisive evaluation is a **card-hidden exam**: remove the notebook, remove demonstrations, and ask genuinely fresh questions generated after training. Also measure an adjacent skill—e.g. train two-digit × one-digit and test three-digit × one-digit. Then compare closed-notebook and open-notebook modes.

For arbitrary taught facts, do the reverse. Put nonsense facts such as “Object Z17's assigned color is mauve” in the notebook but exclude them from consolidation. **Open notebook should know; closed notebook should not.** That becomes a direct leakage test.

## 3\. Proposed sleep pipeline

1. **Freeze a wake snapshot.** Never train the live model.
2. **Select candidate experiences.** Priority should rise when an idea recurs, produced useful outcomes, corrected repeated errors, or appears transferable.
3. **Separate facts from lessons.** A useful operational test is: *Can I generate many independently checkable new problems from this information?* If yes, it may be a procedure. If it is an arbitrary entity→value association, default to notebook-only.
4. **Abstract the lesson.** Convert several episodes into a short rule, prerequisites, worked procedure, failure cases and boundaries.
5. **Generate fresh practice.** Most training examples should never have occurred while awake.
6. **Verify every synthetic target.** Use executable checks for math/code whenever possible. For fuzzy domains, use a separate checker and reject uncertain examples rather than teaching them.
7. **Mix consolidation data with replay.** Include representative old capabilities and explicit “do not internalize” controls.
8. **Train a background copy**, preferably a LoRA/sparse adapter first.
9. **Wake-up exam:** fresh target problems, neighbouring transfer, old-skill regression suite, factual-leak test, quarantined-web test.
10. **Commit only if every gate passes.** Otherwise discard the adapter. Keep the pre-sleep snapshot and a manifest of exactly what generated the update.

For a tiny-from-scratch model, **steps 3–6 should not depend on the tiny model being its own teacher**. It may lack enough reasoning ability to discover the abstraction—exactly the limitation STaR found with GPT-2. [arXiv](https://arxiv.org/abs/2203.14465) Use deterministic generators/verifiers or a stronger teacher. A capable 1–8B model can propose lessons itself, but its proposals still need independent checks.

## 4\. Missing pieces I would add now

Ben's design also needs:

- **Permanent regression suites**, sampled secretly rather than reused nightly.
- **Weight provenance:** every adapter/update links back to lessons and source episodes.
- **Unlearning/rollback**, not just adding new knowledge.
- **Poisoning defenses:** quarantined web material must never silently become consolidation data.
- **Checker calibration:** if the checker drifts, sleep can confidently teach false lessons.
- **Evaluation-contamination controls:** generate key tests *after* the training set is frozen.
- **Interference measurements between subjects**, not only overall benchmark averages.
- **A “do not consolidate” policy** for one-off facts, uncertain conclusions, preferences likely to change, and inadequately verified lessons.
- **Consolidation frequency limits.** More updates are not automatically better.
- **Compute accounting.** On a 16 GB 5070 Ti, 1–8B QLoRA is realistic; repeated full-model fine-tuning is not. QLoRA exists precisely to backpropagate through frozen 4-bit weights into small adapters. [arXiv](https://arxiv.org/abs/2305.14314?utm_source=chatgpt.com)
- **Adapter accumulation control:** eventually many individually good LoRAs may conflict. TIES shows that sign disagreement between task deltas is a real merging problem. [arXiv](https://arxiv.org/abs/2306.01708?utm_source=chatgpt.com)

## 5\. Smallest honest experiment: under 30 minutes

Do **not** start with multiplication, because a pretrained model already knows some multiplication. Invent a new algorithm called, for example, **CardFold**.

Define a deterministic operation on digit strings that the base model cannot have encountered. Give it 20 awake worked examples and a natural-language explanation. During “sleep”:

- **Sleep arm:** infer the rule, then generate perhaps 400 fresh worked examples.
- **Raw-log baseline:** repeatedly fine-tune on the original 20 episodes for exactly the same number of training tokens/optimizer updates.
- Same initial checkpoint, same LoRA rank, same learning rate, same compute.

Before running anything, freeze a secret test generator.

**Pass mark:** on 200 fresh closed-notebook cases, the sleep model must reach ≥80% exact accuracy **and** beat the same-compute raw-log baseline by ≥20 percentage points. On a neighbouring longer input length never trained during sleep, require ≥50%. A small unrelated regression set must fall by <3 percentage points.

None of the 200 test inputs may appear in awake logs or sleep training.

If the sleep arm remembers the 20 examples but fails fresh CardFold cases, it learned answers. If it solves fresh instances and especially longer ones, there is meaningful evidence that **a procedure entered the weights**.

That single experiment is much more informative than watching training loss decrease.

## 6\. Probability estimates

For a preregistered demonstration like the CardFold experiment within one month on the 5070 Ti, my subjective estimates are:

**Tiny model trained from scratch: ~55%.** Algorithmic generalization unquestionably occurs in tiny networks, but discovering abstractions from natural-language episodes is the weak point. Grokking also warns that generalization may require much more optimization than memorization. [arXiv](https://arxiv.org/abs/2201.02177?utm_source=chatgpt.com)

**Pretrained 1–8B model + LoRA/QLoRA: ~85%.** Context distillation has already demonstrated essentially the key phenomenon—reasoning available with scratchpad/context becoming usable without that context—and did so at small scales. [arXiv](https://arxiv.org/abs/2209.15189) The difficult unsolved part is not whether one skill can be consolidated; it is whether **hundreds of nights of autonomous consolidation remain correct, selective, reversible and non-destructive**.

So the evidence supports building sleep, but initially as a **strictly evaluated consolidation experiment**, not as unrestricted self-modification.
