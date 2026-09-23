# Learning English from Books and Scaling Reasoning on One 16 GB GPU

## Bottom line

Ben’s two ideas are both worth testing, but the evidence points to an important distinction:

1. **Good, developmentally simple data helps small models.** There is much weaker evidence that simply presenting it in the order “easy book → hard book” produces a large benefit. BabyLM found most curriculum-learning attempts unsuccessful or only modestly helpful. Data quality, model architecture, objectives, and how efficiently the model uses its limited data seem more important. [ACL Anthology+1](https://aclanthology.org/2023.conll-babylm.1/?utm_source=chatgpt.com)
2. **Reasoning can be improved substantially after pretraining**, even in models around 1.5B parameters. On one 16 GB GPU, the realistic path is a strong pretrained 1.5–3B model plus reasoning distillation, small-scale RL with verifiable rewards, and adaptive test-time compute—not training an R1-like system from scratch.

For an assistant that must actually use tools and understand Ben, I would put **90% probability on a pretrained 1–8B model being the right main engine, versus 10% for a tiny model trained from scratch**. I would still keep a tiny scratch model as a research branch.

* * *

## 1\. Does “learn English like a child” work?

There is a real idea here, but not quite in the literal child-development sense.

The **BabyLM Challenge** deliberately limits models to roughly 10M or 100M words, comparable in scale to human childhood exposure. Its 2023 analysis found that surprisingly capable models can be built at these data scales. Techniques such as better architectures, shorter training sequences, and teacher distillation worked well. However, **many entrants tried curriculum learning and most did not obtain a clear advantage**. [babylm.github.io+1](https://babylm.github.io/archive_2023.html?utm_source=chatgpt.com)

Later BabyLM work found exceptions. Carefully designed, linguistically motivated curricula can beat shuffled training, and 2026 work on LM pretraining reports gains from using easy material as an initial warm-up. But newer controlled studies also find that neither easy→hard nor hard→easy wins universally. [ACL Anthology+2ACL Anthology+2](https://aclanthology.org/2024.conll-babylm.15/?utm_source=chatgpt.com)

So:

**Proven:** what text you train on matters enormously.

**Plausible:** beginning with short sentences, concrete vocabulary and simple narratives can make early training more sample-efficient.

**Not proven:** reproducing school reading levels in chronological order is intrinsically better than shuffling the same good corpus.

TinyStories is especially relevant. Eldan and Li showed that synthetic stories written using vocabulary understandable to young children could teach models under 10M parameters to produce surprisingly coherent multi-paragraph English (*TinyStories*, 2023, arXiv:2305.07759). [arXiv](https://arxiv.org/abs/2305.07759?utm_source=chatgpt.com)

Likewise, *Textbooks Are All You Need* (Gunasekar et al., 2023, arXiv:2306.11644) showed that unusually curated and synthetic “textbook-quality” data let a 1.3B coding model become much stronger than its size suggested. That paper is evidence for **data quality**, not proof that textbook ordering works for general language. [arXiv](https://arxiv.org/abs/2306.11644?utm_source=chatgpt.com)

* * *

## 2\. A legal reading ladder

I would build a roughly **100M-token experimental curriculum**, then sort documents within each rung using **Flesch–Kincaid Grade Level**, sentence length, and word-frequency statistics. For conversational transcripts, use age plus mean utterance length instead of relying heavily on Flesch scores.

| Rung | Material | Suggested tokens |
| --- | --- | --- |
| 1 | TinyStories / simple child-directed material | 10M |
| 2 | Very easy public-domain children's stories | 15M |
| 3 | Broader children's / middle-grade public-domain fiction | 20M |
| 4 | Simple English Wikipedia | 25M |
| 5 | More complex public-domain fiction + nonfiction | 30M |

**TinyStories** is distributed under CDLA-Sharing-1.0 and contains roughly two million synthetic stories. [Hugging Face+1](https://huggingface.co/datasets/roneneldan/TinyStories/tree/main?utm_source=chatgpt.com)

**Project Gutenberg** is excellent for the book stages. As of 2026, works qualifying under its standard U.S. copyright rule and published in 1930 or earlier are unrestricted by U.S. copyright; individual Gutenberg headers still need checking because a small number of works remain restricted. [Project Gutenberg+1](https://www.gutenberg.org/help/copyright?utm_source=chatgpt.com)

**Simple English Wikipedia** supplies explanatory/nonfiction prose instead of letting the model see only stories. Wikimedia text is generally reusable under CC BY-SA, subject to attribution/share-alike conditions. [Wikimedia Foundation](https://foundation.wikimedia.org/wiki/Legal%3AWikimedia_Developer_App_Guidelines?utm_source=chatgpt.com)

**CHILDES** is scientifically valuable because it contains real child-directed speech, but its legal conditions are different: TalkBank says most data is CC BY-NC-SA 3.0 and imposes citation and non-commercial-use conditions. I would use it for Ben’s private research only after recording the precise corpus license, rather than silently folding it into a future distributable model. [TalkBank+1](https://talkbank.org/0share/rules.html?utm_source=chatgpt.com)

The **BabyLM corpus itself mixes many sources**, so I would use BabyLM primarily as a benchmark/research resource and audit source licenses before treating the entire bundle as deployable training text.

Modern copyrighted children's books should **not** simply be scraped into the training set. Public-domain books can provide more literature than this experiment needs anyway.

* * *

## 3\. How to tell whether reading actually helped

Do not use “the generated story sounds nicer” as the primary metric.

For **English ability**, keep material completely unseen during training and measure:

- perplexity/cross-entropy on human-written sentences;
- exact-answer reading comprehension;
- grammatical minimal pairs: “The dogs **are/is** running”;
- story-cloze tests where it must select the causally sensible ending.

For **creativity**, separate originality from fluency. Give prompts such as “write a story involving a broken watch, a tree, and a promise, where the obvious villain turns out to be helping.” Score constraint satisfaction and causal coherence, then measure copying using n-gram overlap and nearest-neighbor similarity against the training corpus. Finally do blind pairwise ratings of originality.

A fluent but memorized story is not creative. A random but novel story is not creative either.

The key experiment has three equal-compute arms:

**A:** easy→hard curriculum  
**B:** exactly the same tokens, randomly shuffled  
**C:** same number of tokens but repeatedly drawn from one easy rung

That separates *ordering* from *better data*.

* * *

## 4\. Stories should be an interest, not a reward

I would not give Premonition a standing reward for reading stories. It could learn that “read fiction” is an easy way to satisfy its objective even when something else is more useful.

Instead, **Stories/Literature becomes one curiosity topic** beside physics, programming, doors, economics, etc. Ben can explicitly assign it, or the curiosity controller can choose it when its uncertainty or unanswered questions make literature useful.

After reading, the NOTEBOOK might receive:

- source, author, license and provenance;
- compact plot summary;
- characters and their motivations;
- interesting language or narrative technique;
- inferred theme/lesson, explicitly marked as inference;
- unanswered questions or links to prior reading.

During sleep, repeated useful patterns—English constructions, narrative techniques, common concepts—can become consolidation candidates. Exact book passages generally should not be what the system tries to memorize.

* * *

## 5\. How far can reasoning be pushed on 16 GB?

More than a tiny-from-scratch system can achieve, but nowhere near frontier-scale R1 training.

DeepSeek-R1 demonstrated large-scale reinforcement learning with verifiable rewards and released distilled models down to **1.5B parameters** (*DeepSeek-R1*, 2025, arXiv:2501.12948). [arXiv](https://arxiv.org/abs/2501.12948?utm_source=chatgpt.com) TinyZero subsequently reproduced interesting RL behavior on small Qwen models; its repository says single-GPU training works up to roughly 1.5B in its setup, while its 0.5B model failed to acquire the desired Countdown reasoning and its main 3B experiment used two GPUs. [GitHub](https://github.com/Jiayi-Pan/TinyZero?utm_source=chatgpt.com)

That makes **1.5B the comfortable RL research scale** for Ben’s GPU. A 3B model is plausible with optimized LoRA/quantization, short rollouts and memory-saving tricks, but much less comfortable. A 7–8B model can reasonably be QLoRA/SFT-trained on 16 GB; online RL with many simultaneous long rollouts is a different matter and will be severely memory/throughput constrained.

Rough **5070 Ti estimates**, not published measurements:

| Experiment | Rough compute |
| --- | --- |
| 1.5B LoRA SFT on a few million tokens | 0.5–3 GPU-hours |
| 3B LoRA SFT | 1–6 GPU-hours |
| useful 1.5B short-output RLVR experiment | 5–30 GPU-hours |
| 3B RLVR | roughly 10–50+ GPU-hours |
| serious 7–8B long-reasoning RL | tens to hundreds of hours and awkward on 16 GB |

For this hardware, **reasoning-trace distillation is probably the highest-return first move**: have a stronger open teacher solve difficult problems, verify answers automatically, discard failures, then SFT the smaller student on successful solutions. RL can then improve behavior the teacher data did not solve.

At inference time, self-consistency or best-of-*n* with a verifier can improve difficult answers, but four samples cost roughly four times as much generation. This is useful precisely because Premonition already has an external budget controller.

Most importantly, **more thinking is not monotonically better**. Recent work documents substantial overthinking and redundant verification. [ACL Anthology](https://aclanthology.org/2026.acl-long.773/?utm_source=chatgpt.com)

There is already direct evidence for Ben's stopping idea. **Thinkless** (Fang et al., NeurIPS 2025, arXiv:2505.13379) trained a 1.5B system to select short versus long reasoning using learned control tokens and reported 50–90% reductions in long-chain use. **AdaptThink** reported a 53% reduction in response length on a 1.5B DeepSeek-R1-distilled model while improving its evaluated accuracy by 2.4 points. [NeurIPS Papers+1](https://papers.neurips.cc/paper_files/paper/2025/hash/de2ad3ed44ee4e675b3be42aa0b615d0-Abstract-Conference.html?utm_source=chatgpt.com)

And *s1: Simple test-time scaling* (2025, arXiv:2501.19393) showed “budget forcing”: either terminate reasoning or force additional thinking by appending “Wait.” Extra thought sometimes corrected mistakes, demonstrating both sides of the stopping problem. [arXiv](https://arxiv.org/abs/2501.19393?utm_source=chatgpt.com)

* * *

## 6\. Two experiments that fit under 30 minutes

### A. Reading ladder

Train a **15–25M parameter scratch transformer** three times from identical initialization, about **6M tokens per arm**:

1. easy→hard;
2. same 6M tokens shuffled;
3. 6M easy-only tokens.

Evaluate on unseen human-written grammar and 100 exact-answer comprehension questions.

**Pass:** curriculum beats shuffled by at least **3 percentage points on comprehension plus ≥3% relative held-out loss**, without losing story originality. One run is only a screening test; a pass earns a later multi-seed experiment.

### B. Learned stopping

Use a reasoning-capable **1.5B model**. On ~100 short math problems, save reasoning at 64-token checkpoints. Use an exact-answer verifier to mark the first checkpoint after which further reasoning no longer changes a correct answer. Train a tiny LoRA/control head to choose **CONTINUE** or `</think>`.

Compare against the unchanged model using a fixed reasoning budget.

**Pass:** **≥25% fewer reasoning tokens while held-out accuracy falls by no more than one percentage point**. That directly tests the idea Ben actually cares about: *has enough thinking happened?*, rather than rewarding short answers blindly.

* * *

## Recommendation

For Premonition as a **real working agent**, my engineering probabilities are:

**90% — pretrained 1.5–8B engine.** It already knows English, tools, general knowledge and instruction following; Ben can devote his limited GPU budget to the genuinely novel parts: persistent learning, reasoning, memory, stopping and curiosity.

**10% — tiny scratch model as the main engine.** It remains extremely useful scientifically, especially for studying developmental curricula and novel learning mechanisms, but tens of millions of parameters trained on one GPU are unlikely to become a reliable general-purpose agent.

The most promising architecture is therefore not “give up on the tiny model.” It is **a capable pretrained worker plus Ben’s experimental learning/memory/reasoning machinery around it, with a tiny scratch model maintained as the controlled research platform.**
