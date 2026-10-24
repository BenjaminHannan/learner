# Sleep-B arms: evidence for doing each idea better next round (2026-10-24)

Labels. **shown** = measured in the cited paper (other models and tasks, not ours). **suggested** = my inference for our setting. **untested** = no direct test found. Every ID below was checked against arXiv or Crossref (title and year match). Sealed arms are not redesigned; "improvements" are for the round after. No sub-agent tool was available to me, so I searched myself and the final challenge was a self-review.

## 1. Rotating regions
**Evidence**
- LISA (arXiv 2403.17919, 2024): always trains embedding and head, re-samples a few random middle layers every K steps. It beat LoRA by 10-35% on MT-Bench at LoRA-like memory (shown; instruction tuning, not facts). Sampling is uniform across depth.
- ROME (2202.05262, 2022) and MEMIT (2210.07229, 2022): facts localise to mid-layer MLPs (shown). But Hase et al. (2301.04213, 2023): where tracing says a fact lives does not predict the best layer to edit (shown).
- LoRA for time-sensitive edits (2406.04496, 2024): MLP-only 98.8 reliability vs attention-only 43.7 on LLaMA-7B, but both about 99 on Falcon and Mistral (shown; model dependent).
- Brain: local sleep (Huber 2004, 10.1038/nature02663; Vyazovskiy 2011, 10.1038/nature10009), one-hemisphere sleep (Rattenborg 2000, 10.1016/S0149-7634(00)00039-7). Sleep depth tracks recent local use (shown in animals and humans). No ML transfer test (untested).
- Ours: tagging protected ARC but stored less (53.5 vs 56) (shown).
- Rotation, tagging or layer type? Suggested: pick module type first (MLP), spread the rotation across depth, and use tagging as a safety brake, not a storage selector.

**Best improvement:** swap contiguous quarters for strided layer sets (night d trains layers with index mod 4 = (d-1) mod 4), so every night touches mid-layer MLPs. Pass: recall >= 56 (control) and >= contiguous-arm recall + 4. Wrong if: strided is within 4 points of contiguous (depth coverage was not the limit) or recall < 46.

**Warning:** SHY trims every module nightly, but each quarter trains only 1 night in 4 (quarter 3 only once in 7). Trim may erase a quarter's facts before the test (suggested). Quarters 0 and 3 are the layers least tied to facts. If R2 fails, check per-quarter norm decay first.

## 2. Twisted dreams
**Evidence**
- Hoel 2021 (arXiv 2007.09560; Patterns, 10.1016/j.patter.2021.100244): dreams as corrupted input that fights overfitting. A hypothesis; no language-model test (untested).
- Allen-Zhu and Li, Physics of LMs 3.1 (2309.14316, 2023): knowledge is extractable only if text is varied (paraphrase, sentence shuffle, translation); one form is memorised but gives 0% on questions (shown; synthetic biographies).
- EntiGraph (2409.07431, 2024): repeated rephrasing gives fast-shrinking returns; entity-relation text scales log-linearly to 455M tokens (shown, 8B model). The generator was GPT-4-turbo; the authors warn weaker generators may hallucinate. Active Reading (2508.09494, 2025): varied self-chosen study strategies beat vanilla fine-tuning (shown, 8B).
- Noise: NEFTune (2310.05914, 2023) helps instruction tuning, not facts (shown). Dropout alone cured multi-epoch overfit (2305.13230, 2023).
- Harm: unknown or ungrounded content is learned slowly and raises hallucination (Gekhman 2405.05904, 2024; Kang 2403.05612, 2024). Training on own output loses rare content (2305.17493, 2023).
- Suggested: helpful distortion changes surface (setting, style, order, which entity comes first) with every relation intact; harmful distortion changes a relation or restates a stale value. I found no paper showing entity-swap or counterfactual augmentation helps memorisation (untested), and it risks teaching falsehoods.

**Best improvement:** make the scene filter slot-exact. Keep a scene only if it contains the item's current gold value, contains no other or stale value for that slot, and names both entities. Drop the "any one dream question answered" check. Pass: T2 recall >= 61, changed-new >= 70, and a 40-scene hand audit finds <= 2 false or stale facts. Wrong if: recall < 56 with a clean audit (twist adds nothing beyond ordinary paraphrase).

**Warning:** (a) The 2B base model both writes and judges the scenes, which is the weak-generator case EntiGraph flags. Answering one question correctly does not show the scene is faithful, and a scene that treats an old value as current undoes "newest wins". (b) Steps are unchanged, so two scenes displace about 20% of real practice. With no "two extra plain paraphrases" control, a T2 pass cannot be credited to the twist (suggested).

## 3. Therapy replay
**Evidence**
- Walker and van der Helm 2009 (Psychol Bull, 10.1037/a0016570): REM keeps content and dampens emotional tone. Later tests are weak: a 31-study meta-analysis found no overall preferential consolidation of emotional memory (Lipinska 2019, 10.3389/fpsyg.2019.01014); 24 studies found no significant change in physiological reactivity (Lipinska 2022, 10.3389/fnbeh.2022.976047) (shown, humans). It concerns emotional tone, so "salient item = gentler step" is a loose analogy (suggested).
- Importance sampling at rate p needs loss weight 1/p to stay unbiased (Katharopoulos and Fleuret, 1803.00942, 2018). Byrd and Lipton (1812.03372, 2019): importance weights lose influence over epochs in deep nets (shown, vision).
- Updates: sequential edits cause forgetting (2401.07453, 2024); edits do not reach related facts (2307.12976, 2023); unlearning the old value helps (CoME, 2502.15826, 2025) (shown, editing benchmarks).
- mix-cd (2402.08096, 2024): rehearse items the update just made the model forget (shown).

**Best improvement:** keep 2x priority but set loss weight to 1.0 for corrected or replaced items, and report the stale-answer rate (old value given). Pass: changed-new >= 80 and stale-answer rate below control. Wrong if: changed-new < 70 (emphasis does not help).

**Warning:** as sealed, 2x priority times 0.5 weight leaves each salient item's expected push unchanged (suggested). H2 (>= 80) then tests variance reduction, not emphasis, and is likely a null. With 20 questions, H2 is a 2-fact gap.

## 4. Guess + dopamine
**Evidence**
- Lisman and Grace 2005 (10.1016/j.neuron.2005.05.002): a hippocampus-VTA loop gates entry to long-term memory (hypothesis). Singer and Frank 2009 (10.1016/j.neuron.2009.11.016): ripple reactivation is larger after rewarded outcomes. Lansink 2009 (10.1371/journal.pbio.1000173): hippocampus leads striatum in replaying place-reward information (shown, rats).
- Ambrose 2016 (10.1016/j.neuron.2016.07.047): reverse replay rises when reward rises and falls when it falls (shown, rats). Positive RPE strengthens memory (Jang 2019, 10.1038/s41562-019-0597-3); signed and unsigned RPE both enhance memory (Rouhani and Niv 2021, 10.7554/eLife.61077) (shown, humans). Replay priority = gain x need (Mattar and Daw 2018, 10.1038/s41593-018-0232-z). Confident errors are corrected best after feedback (Butterfield and Metcalfe 2001, 10.1037/0278-7393.27.6.1491).
- ML: PER (1511.05952, 2015) uses |TD error|, unsigned. SuRe (2511.22367, 2025): replaying the highest-loss sequences is state of the art for continual LLM learning (shown). Partly known facts are the useful ones to train on; unknown ones are slow and harmful (Gekhman). RHO-LOSS (2206.07137, 2022): skip points already learnt or unlearnable (shown).
- Positive or negative? Brain data lean positive; LLM replay data lean negative. Suggested: use both (unsigned).

**Best improvement:** unsigned surprise. Multiplier 1 + 2|o - c|, cap 3x, so confident-wrong items are boosted along with right-but-unsure ones. Pass: G2 recall >= 61 and changed-new >= 70. Wrong if: recall < 56, or changed-new < 60 (boosting errors over-fits).

**Warning:** (a) On a fresh week most facts are unknown (o = 0, c small), so the sealed positive-only boost fires on few items at night 1 and may be a no-op by construction. The reported share with o - c > 0.2 will show it; under ~5%, treat G2 as uninformative. (b) First-token probability is a weak confidence for multi-token answers; use full-answer probability (2207.05221, 2022).

## 5. Adaptive night budget
**Evidence**
- Repetition: up to about 4 epochs of repeated data matches unique data, then returns decay to zero (2305.16264, 2023); multi-epoch degradation (2305.13230, 2023); duplicated data is forgotten faster (2406.11813, 2024) (shown, pretraining).
- Diversity beats volume: EntiGraph vs its rephrase baseline (2409.07431); Active Reading (2508.09494); fact-based beats token-based scaling (2404.00213, 2024) (shown).
- Cost: forgetting grows with parameters updated and steps (2401.05605, 2024); LoRA learns less and forgets less (2405.09673, 2024); LoRA packed with new facts can lower benchmark scores (2502.14502, 2025).
- Offline compute pays when future use is predictable (sleep-time compute, 2504.13171, 2025; shown for reasoning).

**Best improvement:** at s > 1, generate the extra dreams from different style prompts (timeline, dialogue, teaching, contrast), and drop near-copies (n-gram overlap > 0.7) before training. Keep passes per text at the control level. Pass: B1 recall >= 61 with B2 and B3, and report the distinct-text rate. Wrong if: recall <= 56 with zero gate reverts (more varied work adds nothing).

**Warning:** (a) Resampling the same prompts at temperature is the "Rephrase baseline" that plateaued in EntiGraph, so s = 2 may mostly add near-duplicates (suggested). (b) Steps double at the same peak LR. Our full-rank result (lr 2e-5 broke ARC, 5e-6 did not) shows total movement matters. If the gate reverts s = 2 nights, "recall <= 56" would reflect reverts, not "no gain". Read the revert count first.

## Plain-language summary for Ben
1. Spread each night's learning over layers from front to back, not four solid blocks, because the facts mostly live in the middle.
2. Dream-style practice only helps if every scene stays true; a wrong or old fact in a "dream" teaches the model a mistake.
3. Replaying changed facts more often but gentler cancels out, so give corrected facts a full-strength push.
4. Replay the facts the model was surprised about in both directions, not only the lucky guesses.
5. A faster chip should buy more different practice, not the same practice again, and we must check the safety gate did not undo the extra work.
