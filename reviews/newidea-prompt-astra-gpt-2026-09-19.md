# Find one genuinely new, game-changing idea for a small learning model

You are a research scientist with deep knowledge of machine learning, neuroscience and cognitive science, and you can search the web. You have no access to my code or files.

## The project (everything you need is here; you cannot see my files)

I am Ben, a high-school senior. With AI help I am building **Premonition**: my own small model that should *genuinely keep learning*, with reasoning first and language second. The brain is inspiration, not a constraint. The goal is **more intelligence per weight and per unit of compute** than a plain transformer of the same size, and a system that learns new things without forgetting old ones. Models are tiny (2-30M parameters) and train from scratch on a synthetic "village" world whose simulator knows every true answer and the steps behind it.

**The design so far**
- A small **reasoner** that should hold skills, not facts: a recurrent reader (minGRU + one local-attention layer), 16 entity slots, a shared "Think" block looped up to 8 times over a small workspace, and a decoder.
- A **knowledge store** the reasoner queries "out loud": every fact line becomes an index card (key + value). The model writes a search request, fetches a card, may fetch again, then answers. A test we hold sacred: wipe the store and fact questions must fail.
- **Agreed but unbuilt vision:** an abstract thought space (a learned, growing codebook "private language", with new codes born only during sleep); JEPA-style prediction with entity knock-out; a diary (raw, permanent) + cards (hippocampus-like index) + sparse knowledge slots (cortex-like, trained only in sleep); **sleep as a transaction** (weights change only in sleep; changes are kept only if wake-up checks pass, else rolled back); a **told-ledger** (a permanent record of exactly what it was told, so it can honestly say "never told" or "I lost that"); a "consolidation pressure" counter that decides when to sleep; motivation drives (learning progress, gap curiosity, effort); a hint ladder; self-tutoring with the card in hand; training path imitation -> RL with the simulator as checker.

**What the experiments show today (small card task, synthetic vocabulary, ~2M-parameter design at d_model 32; five seeds per test; pass marks fixed in advance)**
- Task: stories of fact lines ("Mira's friend is Oren", "Oren's shoes are blue"); one-step questions and two-step questions ("What colour are Mira's friend's shoes?"). Held-out test: two-step questions using a kind of fact never seen in two-step form during training.
- With 4,000 training steps: given both right cards it answers ~100%; finding them itself, practised two-step passes in 2 of 5 runs, held-out in 0 of 5. The failure is building the *second search request*.
- With 12,000 steps: 4 of 5 runs become essentially perfect on one-step and practised two-step (340-341/341); the "right fact, wrong person" error disappears (it was undertraining); one run in five never learns at all. Held-out: 1 of 5 barely passes (88/171). In the trained runs the second request names the right person 162-171 of 171 times but the right kind of fact only 72, 84, 8 and 1 times.
- A learned **shortcut wire** that copies the question's relation word into the search request (545 parameters, starts switched off) fixes that: right kind of fact 146-171 of 171 in 5 of 5 runs (baseline 0-94), and one run passes held-out at 138/171 even at 4,000 steps. A 12,000-step rerun is in progress. Side effect under short training: in 3 of 5 runs the *first* request stopped asking for the friend card.
- Earlier finding: when cards with look-alike distractors are simply supplied, answer-only models follow the *value word* and ignore whose value it is; a selector that is told where the person and relation words sit fixes that (1/3 -> 9/10).
- Separate track: a plain 4M transformer trained on the full village text scores 23% on held-out questions (44% on familiar ones); new question wordings and the tiny share of answer tokens are the walls there.

**Already considered (do not re-propose these as new):** memory networks / key-value memories / retrieval augmentation; memory layers and sparse memory fine-tuning; looped / recursive reasoners (Universal Transformer, TRM, HRM), adaptive halting; entity slots and relational bottlenecks; pointer/copy mechanisms; VQ / FSQ codebooks and growing codebooks (ART-style); JEPA; latent chain-of-thought (Coconut etc.); sleep replay, generative replay, shrink-and-perturb, model merging for consolidation, nested / multi-timescale optimisers; complementary learning systems; curiosity, learning-progress curricula, hint ladders, STaR-style self-training, RL with verifiable rewards; counterfactual / invariance losses; ordered multi-hop supervision; learned write gates; fast weights / delta-rule memories (Titans, DeltaNet); test-time training; neurosymbolic program induction and library learning; holographic / tensor-product binding; hippocampal indexing and barcode keys; told-ledger; sleep as a transaction; consolidation pressure; refault meter.

**Constraints:** one free consumer GPU (RTX 5070 Ti, 16 GB) plus a laptop; at most $30 of cloud compute, ever; experiments should be runs of minutes to about an hour; I change **one thing at a time**, with pass marks fixed before I look; I must be able to understand every step.

## What I want from you

Find **one genuinely new idea** that could be **game-changing for this model's intelligence**: a change in *kind*, not a tuning trick. "Game-changing" means it would plausibly give an order-of-magnitude gain in something that matters here (examples: samples needed to learn a new skill, reliability on unseen combinations, intelligence per parameter, learning new worlds without forgetting old ones) or unlock an ability the current design cannot express at all.

**Your starting lens (you may leave it if you find something better): how the model LEARNS over time — what gets stored where, learning something from being told once, consolidation and sleep, self-teaching loops, and how new learning avoids damaging old learning.**

Work like this:
1. **Generate at least eight candidate ideas**, deliberately from different directions (other sciences, neuroscience, developmental psychology, information theory, compilers, databases, control theory, evolution, education...). One line each.
2. **Try to kill each one.** Search the literature and the web for prior art (2015-2026, including 2025-26 preprints and lab blogs). For each candidate give the closest existing work with a real link and say honestly whether it already exists. Discard anything that does. Never invent a citation; if you cannot verify a paper, say so.
3. **Also kill for smallness and for fit:** discard ideas that are incremental, that only make sense at billion-parameter scale, or that cannot be tested on my hardware.
4. **Pick the single strongest survivor** and write it up:
   - the idea in three plain sentences;
   - the mechanism precisely enough that an engineer could build it (what is stored, what is computed, what is trained by what signal, what happens at inference);
   - **why it is a change in kind** and what measurable thing should jump, by roughly how much, and why you believe that;
   - the **five closest prior works** (real links) and exactly what is different;
   - your honest confidence (0-100%) that it is (a) new to the world, (b) going to work at my scale;
   - **the cheapest decisive experiment** on my setup: one change against a stated baseline, five seeds, pass marks fixed in advance, and the result that would prove you wrong;
   - what it would replace or make unnecessary in my current design, and how to introduce it one step at a time;
   - the two most likely reasons it fails.
5. **Runner-up:** two sentences on the second-best survivor.
6. **If nothing survives, say so plainly.** "I found no idea that is both new and big" is an acceptable answer; an inflated one is not.
7. **Plain-language version for me:** 8-12 sentences with an everyday analogy; explain every technical term in one line.

Rules: label claims as **established**, **plausible** or **speculative**. Do not flatter the project. Do not bundle several ideas into one. Do not propose anything that needs private data, large pretrained models as a crutch, or more than my compute.
