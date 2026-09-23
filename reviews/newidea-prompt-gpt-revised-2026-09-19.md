# Revised brief: make a small retrieving reasoner learn dependably AND generalise

You are a research scientist with deep knowledge of machine learning, neuroscience and cognitive science, and you can search the web. You have no access to my code or files. This brief replaces the earlier one: the 12,000-step results are now in, and they change the question.

## The project (everything you need is here)

I am Ben, a high-school senior. With AI help I am building **Premonition**: a small model that should genuinely keep learning, reasoning first and language second. Goal: more intelligence per weight and per unit of compute than a plain transformer of the same size, and learning new things without forgetting old ones. Models are tiny (2-30M parameters), trained from scratch on a synthetic world whose simulator knows every true answer.

**Design.** A small reasoner that should hold skills, not facts: a recurrent reader (minGRU + one local-attention layer), 16 entity slots, a shared "Think" block looped over a small workspace (the question's rows stay in the workspace throughout; 4 register rows), and a decoder. Facts live in a **card store**: every fact line ("Mira shoes red") becomes a card with a search label (key) and content (value). The reasoner writes a search slip (query) from register 0, the store scores `kappa * cosine(query, key)`, the best card is fetched (the choice is not differentiable for the answer loss), and it may fetch again before answering. Key and value are both made from ONE pooled summary of the line: a learned softmax weighting over the line's token states.

**Unbuilt vision (context only):** abstract thought codes, sleep as a transaction with rollback, a permanent told-ledger, consolidation pressure, self-tutoring. None of it is tested.

## Evidence today: small card task only

Synthetic vocabulary, ~2M-parameter design at width 32, 25 cards per story (6 people x 3 relations + 6 friend links + a NULL card), validation split, pass marks fixed in advance. Nothing here is evidence about the separate "village text" track (a plain 4M transformer scores 23% on held-out village questions; different problem, keep it separate).

Task: one-step questions ("Mira shoes?") and two-step questions ("Mira friend shoes?"). Held-out test: two-step questions about a relation that appears in one-step questions but never in two-step training. 512 one-step, 341 practised two-step, 171 held-out two-step questions.

Training schedule (12,250 steps): steps 0-1,225 all needed cards are handed over and only answering (plus language modelling) is trained, **no search training at all**; steps 1,225-2,245 a teacher hands over a needed card after each loop and search is trained (cross-entropy over the set of still-needed cards); then a ramp to the model's own fetches.

**Shown**
1. Given both right cards, every trained model answers ~100%. Reading and combining are not the problem.
2. Baseline, 12,000 steps, 5 seeds: 4 learn one-step and practised two-step essentially perfectly (340-341/341); 1 never learns to search. Held-out: 1 of 5 barely passes (88/171). In learned runs the second request names the right person 162-171/171 but the right relation only 72, 84, 8, 1 times.
3. **Relation shortcut wire** (545 parameters, starts at zero; a gate reading the current state lets the question's relation word into the search slip). 12,000 steps, 5 seeds: three runs score **171, 170 and 132 of 171 held-out**; **two runs never learn to search**. In the three learned runs the first request is the friend card 512/512, 512/512 and 468/512 (the 44 misses pick another person's friend card; none skips the lookup). So the first-request regression seen at 4,000 steps was undertraining, **not a lasting conflict inside the architecture**. Discard that story.
4. **The remaining blocker is training reliability: 3 of 10 long runs are "stuck".** Twenty more control runs are training to pin the rate down.
5. What a stuck run does (read-only probes on saved models): its first request picks the right KIND of card 100% of the time and the right PERSON 15-20% (chance 16.7%); equally bad for every person and relation, no position habit. Rescoring with kappa 3/10/30/100 changes nothing, so low final kappa (11-15 vs 79-147 in learned runs) is a consequence, not the cause.
6. Where the person is lost: in stuck runs a linear read-out names the person from the reader state at the person word 98-100% of the time, but from the state at the value word only 16-23%, and the pooled summary puts 97-99% of its weight on the value word. So key, value and query all carry no person (16-31%). Learned runs either keep pooling weight on the name or carry the name forward into the value word's state (55-100% readable there); their keys and queries are 100% readable.

**Suggested (not shown)**
- Answer-only training in the first 1,225 steps locks the shared summary onto the value word. Afterwards there is a chicken-and-egg: the push on keys to encode the person is proportional to how much the query encodes the person, and the reverse; both start near zero, and the pooling softmax is saturated, so some seeds never leave.

**In test now (untested so far):** give the key its own pooling weights (32 numbers, cloned at start so the model begins identical). 15 seeds vs 15 controls, a run is stuck if one-step < 384/512; if promising, 40 seeds per side with a two-sided Fisher test.

## Already proposed or assessed: do not re-propose as new

From your earlier replies and mine: memory networks / key-value memories / retrieval augmentation; looped reasoners and halting; entity slots; pointer/copy and gated copying; codebooks; JEPA; latent chain-of-thought; sleep replay and consolidation methods; curiosity and curricula; counterfactual / invariance / paired-consistency losses; ordered multi-hop supervision; fast weights; test-time training; program induction; tensor-product binding; hippocampal indexing. Also: early search supervision from an empty workspace; separate key pooling; a shared person code added to query and key; kappa schedules; waiting for retrieval before removing the teacher; learning-rate restarts; stage-specific gates for the copy wire (the gate already reads the state, and the interference it targeted is gone); separate control and working states (largely present); a small bank of operation modules; protecting modules during sleep; intervention-based circuit allocation (your near miss, under 15% by your own estimate); and the other thirteen candidates you already killed.

## What I want now

The research question has changed from "why does the second request generalise badly?" to: **what makes learned addressing (writing a search slip that matches a search label) start up dependably in a tiny model, and can one mechanism serve both dependable training and generalisation to unseen combinations?** Judge every idea on BOTH axes: the fraction of random seeds that succeed, and held-out accuracy in the seeds that do.

1. **Check my reading.** Rank explanations for the seed lottery given items 4-6. What would distinguish "pooling locked by early answer training" from "symmetric query-key cold start" from something I have missed? Use eval-only measurements on saved models where possible.
2. **What is known.** Search for work on cold-start or seed sensitivity of learned retrieval and addressing: memory networks, dual encoders, slot attention, product-key memories, differentiable neural computers, attention "induction" phase changes, tied vs untied query/key embeddings, saddle-to-saddle learning dynamics. Real links only; say when you cannot verify. What do they say removes the lottery rather than just shifting it?
3. **Candidates.** Generate at least eight ideas from different directions and try to kill each (prior art, smallness, fit to my hardware). Usefulness is now the first criterion; label novelty honestly (exists / close variant / possibly unpublished) instead of discarding everything that exists. Reject ideas that hand the model the answer structure at inference (for example telling it which token is the person) unless you argue why that is a fair, general inductive bias rather than a crutch.
4. **Strongest survivor**, written up: the idea in three plain sentences; the mechanism precisely (what is stored, computed, trained by what signal, what runs at inference); why it should help reliability AND held-out generalisation, or an honest statement that it helps only one; the five closest prior works and what differs; your confidence (0-100%) that it works at my scale; how it interacts with the separate-key-pooling test (replace it, stack on it, or made unnecessary by it).
5. **Cheapest decisive experiment:** one change against a stated control; pass marks fixed in advance on both axes (for example: stuck runs at most 1 of 15, and held-out at least 86/171 in at least 80% of non-stuck runs, with no loss on practised questions); the number of seeds needed and the power calculation; the result that would prove you wrong.
6. **Runner-up** in two sentences. **If nothing survives, say so plainly.**
7. **Mistakes in my reasoning**, directly.
8. **Plain-language version for me:** 8-12 sentences, everyday analogy, every technical term explained in one line.

Rules: label every claim about my model as **shown / suggested / untested**, and every literature claim as established or your inference. Keep the small card experiments and the village-text track separate. One change at a time. Do not flatter the project. No large pretrained models, no private data, nothing beyond one consumer GPU (RTX 5070 Ti) with runs of minutes to about an hour.
