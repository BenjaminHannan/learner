# C. Creativity evidence: generate many ideas, filter them, learn from the hits (verified 2026-09-25)

Every quote below was copied from a page I fetched on 2026-09-25 (arXiv abstract/HTML, Crossref, PubMed, Europe PMC full text, Springer).
I could not find abstracts for Campbell 1960, Mednick 1962, Simonton 1997, Diehl & Stroebe 1987, Rietzschel 2006 or Organisciak 2023, so none of them has its own entry (see "Dropped" at the end).
Venue is given only where the fetched page states it, or for well-known journals. "arXiv" means the venue was not checked.
Labels: **SHOWN** = a controlled result in that paper. **SUGGESTED** = correlational, theory, one narrow setting, or an analogy to our model. **DISPUTED** = other good work contradicts it.
Scope warning: all of these are about humans or large models. None of them tests our small card experiments or the village model directly. Each "Design" line is an analogy, not proof.

## A. Human creativity: does quantity produce hits?

#### **1. Quantity yields quality when it comes to creativity: a brain and behavioral test of the equal-odds rule.** Jung et al., 2015, Frontiers in Psychology. DOI 10.3389/fpsyg.2015.00864
- Quote: "higher number of responses on the divergent thinking task was significantly associated with higher creativity (r = 0.73) as independently assessed by three judges."
- Shows: people who produce more ideas also produce more creative ones (N=246). Correlational. **SUGGESTED**
- URL: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi (PMID 26161075)
- Design: supports "maximize lucky hits". More blurts per sleep cycle is a reasonable default.
#### **2. Not Quite Equal Odds: Openness to Experience Moderates the Relation Between Quantity and Quality of Ideas.** 2019, Frontiers in Psychology. DOI 10.3389/fpsyg.2019.00355
- Quote: "while quantity does breed quality in creative production, the effect is moderated by individual differences, specifically the personality trait Openness to Experience."
- Shows: quantity helps, but how much depends on the person (N=154). **SUGGESTED**
- URL: https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=TITLE:"equal-odds"
- Design: the payoff from more blurts depends on the generator. Measure the hit rate per blurt; don't assume it.
#### **3. Scientific creativity as constrained stochastic behavior.** Simonton, 2003, Psychological Bulletin 129:475. DOI 10.1037/0033-2909.129.4.475
- Quote: "scientific creativity constitutes a form of constrained stochastic behavior. That is, it can be accurately modeled as a quasi-random combinatorial process."
- Shows: a review of real scientific careers. Theory built on archival data. This is the source for the equal-odds idea. **SUGGESTED**
- URL: https://eutils.ncbi.nlm.nih.gov (PMID 12848217)
- Design: "blind variation + selection" is a respectable model of real creativity, not only a trick for puzzles.
#### **4. Quantifying the evolution of individual scientific impact.** Sinatra, Wang, Deville, Song, Barabási, 2016, Science. DOI 10.1126/science.aaf5239
- Quote: "When productivity ... is accounted for, the paper with the greatest impact occurs randomly in a scientist's career. However, the process of generating a high-impact paper is not an entirely random one." (a model with randomness, productivity and a personal factor Q)
- Shows: in 2,887 physicists' careers, when your biggest hit comes looks like luck, and the number of tries matters. But a stable personal skill (Q) also matters. **SHOWN** (large real-world dataset, observational)
- URL: https://api.crossref.org/works/10.1126/science.aaf5239
- Design: real-world support for "hits = tries × a quality factor". Improving the generator's Q matters as much as the number of tries.
#### **5. Understanding the onset of hot streaks across artistic, cultural, and scientific careers.** Liu, Dehmamy, Chown, Giles, Wang, 2021, Nature Communications. DOI 10.1038/s41467-021-25477-8
- Quote: "hot streaks appear to be associated with neither exploration nor exploitation behavior in isolation, but a particular sequence of exploration followed by exploitation"
- Shows: in artists, film directors and scientists, hot streaks follow a wide phase (varied work), then a narrow phase (focused work). Observational. **SUGGESTED**
- URL: https://api.crossref.org/works/10.1038/s41467-021-25477-8
- Design: the closest real-world match to Ben's "growing circle, then egg": explore widely, then focus once something hits.
#### **6. Idea Generation and the Quality of the Best Idea.** Girotra, Terwiesch, Ulrich, 2010, Management Science. DOI 10.1287/mnsc.1090.1144
- Quote: the quality of the best ideas depends on "(1) the average quality ... (2) the number of ideas generated, (3) the variance in the quality ... and (4) the ability of the group to discern the quality of the ideas." Also: "building on others' ideas is counterproductive".
- Shows: an experiment. Working alone first, then as a group, gave more ideas, better ideas and better judging. **SHOWN**
- URL: https://api.crossref.org/works/10.1287/mnsc.1090.1144
- Design: this is our whole pipeline in one sentence. Only the best hit matters, so count, variance and judging skill all count, not the average. Our weak judge (3/10) is a first-class bottleneck.
#### **7. The creative cliff illusion.** Lucas & Nordgren, 2020, PNAS. DOI 10.1073/pnas.2005620117
- Quote: "people's creativity, on aggregate, remained constant or improved across an ideation session. However ... people expected their creativity to decline over time" and "people underinvest in ideation."
- Shows: across 8 studies, later ideas are not worse. Quitting early costs hits. **SHOWN**
- URL: https://eutils.ncbi.nlm.nih.gov (PMID 32747567)
- Design: supports continuing to generate after rejections, instead of stopping at the first dry spell. Fits the "growing circle".
#### **8. Opportunity Spaces in Innovation: Empirical Analysis of Large Samples of Ideas.** Kornish & Ulrich, 2011, Management Science. DOI 10.1287/mnsc.1100.1247
- Quote: "this redundancy is quite small in absolute terms in our data" and "the ideas that are least similar to others are not generally the most valuable ones."
- Shows: across 1,368 real product ideas, human idea pools rarely repeat. Ideas similar to many others tended to be more valuable. **SHOWN** (observational, 5 datasets)
- URL: https://api.crossref.org/works/10.1287/mnsc.1100.1247
- Design: warns against a blunt "avoid repeats". Drop exact duplicates, but don't punish closeness to a cluster, because clusters can mark valuable regions (the "egg").

## B. Incubation, sleep and insight (humans)

#### **9. Sleep inspires insight.** Wagner, Gais, Haider, Verleger, Born, 2004, Nature 427:352. DOI 10.1038/nature02223
- Quote: "more than twice as many subjects gained insight into the hidden rule after sleep as after wakefulness" ... "Sleep did not enhance insight in the absence of initial training."
- Shows: 8 hours of sleep doubled the rate of discovering a hidden shortcut in a number task. It only worked after practice. **SHOWN** (lab puzzle)
- URL: https://eutils.ncbi.nlm.nih.gov (PMID 14737168)
- Design: sleep helps only after awake practice on the same material. Train at sleep on today's attempts, not on random data.
#### **10. Sleep onset is a creative sweet spot.** Lacaux, Andrillon, ..., Arnulf, Oudiette, 2021, Science Advances. DOI 10.1126/sciadv.abj5866
- Quote: "spending at least 15 s in N1 during a resting period tripled the chance to discover the hidden rule (83% versus 30% when participants remained awake), and this effect vanished if subjects reached deeper sleep."
- Shows: light sleep at the edge of waking tripled insight. Deeper sleep removed the effect (N=103). **SHOWN** (same kind of hidden-rule puzzle)
- URL: https://eutils.ncbi.nlm.nih.gov (PMID 34878849)
- Design: "a little loosening helps, too much hurts". This is a human analogy for a moderate, not maximal, randomness level. Analogy only.
#### **11. REM, not incubation, improves creativity by priming associative networks.** Cai, Mednick, Harrison, Kanady, Mednick, 2009, PNAS. DOI 10.1073/pnas.0900271106
- Quote: "compared with quiet rest and non-REM sleep, REM enhances the integration of unassociated information for creative problem solving"
- Shows: a REM nap improved Remote Associates Test scores (Mednick's distant-association test) more than rest did. **SHOWN** (small nap study)
- URL: https://api.crossref.org/works/10.1073/pnas.0900271106
- Design: supports sleep as a phase that links distant ideas. For us, sleep training could mix today's hits with older material.
#### **12. Does incubation enhance problem solving? A meta-analytic review.** Sio & Ormerod, 2009, Psychological Bulletin. DOI 10.1037/a0014212
- Quote: "a positive incubation effect, with divergent thinking tasks benefiting more than linguistic and visual insight tasks" ... "Longer preparation periods gave a greater incubation effect".
- Shows: across many studies, setting a problem aside helps. It helps most for open-ended idea tasks and after real effort. **SHOWN** (meta-analysis)
- URL: https://eutils.ncbi.nlm.nih.gov (PMID 19210055)
- Design: an incubation break helps most after a hard awake session. This backs "blurt hard by day, consolidate at night".
#### **13. Sleep-like unsupervised replay reduces catastrophic forgetting in artificial neural networks.** Tadros, Krishnan, Ramyaa, Bazhenov, 2022, Nature Communications. DOI 10.1038/s41467-022-34938-7
- Quote: "sleep was able to recover old tasks that were otherwise forgotten."
- Shows: an offline "sleep" phase with replay protected old skills in a neural network. **SHOWN** (small nets)
- URL: https://eutils.ncbi.nlm.nih.gov (PMID 36522325)
- Design: sleep training should replay old material alongside new hits so the model doesn't forget. Compare item 27.

## C. Open-endedness in AI: novelty, stepping stones, quality-diversity

#### **14. Abandoning Objectives: Evolution Through the Search for Novelty Alone.** Lehman & Stanley, 2011, Evolutionary Computation 19(2). DOI 10.1162/EVCO_a_00025
- Quote (full text): "On the hard map, fitness-based NEAT was only successful in three out of 40 runs ... novelty search was able to solve the same map in 39 out of 40 runs"
- Shows: on a deceptive maze, searching only for new behaviour beat aiming at the goal, 39/40 vs 3/40. **SHOWN** (toy domains)
- URL: https://www.cs.swarthmore.edu/~meeden/DevelopmentalRobotics/lehman_ecj11.pdf ; abstract via Crossref
- Design: strongest evidence for novelty and stepping stones when the goal signal misleads. Keep a novelty term, not only a "good answer" score.
#### **15. Why Greatness Cannot Be Planned.** Stanley & Lehman, 2015, Springer (book). DOI 10.1007/978-3-319-15524-1
- Quote: "we would be wiser (and the outcomes better) if instead we whole-heartedly embraced serendipitous discovery and playful creativity."
- Shows: an argument book built on item 14. It is opinion, not new data. **SUGGESTED**
- URL: https://link.springer.com/book/10.1007/978-3-319-15524-1
- Design: the source of "stepping stones". Cite it for the idea, and cite items 14, 16 and 17 for the evidence.
#### **16. Illuminating search spaces by mapping elites (MAP-Elites).** Mouret & Clune, 2015. arXiv 1504.04909
- Quote: "because MAP-Elites explores more of the search space, it also tends to find a better overall solution than state-of-the-art search algorithms."
- Shows: keeping the best idea in each "kind" of idea gives variety and often a better single winner. **SHOWN** (3 domains)
- URL: https://arxiv.org/abs/1504.04909
- Design: a concrete form of "avoid repeats": keep a per-category archive of near misses and hits, and draw parents from it.
#### **17. POET: Endlessly Generating Increasingly Complex and Diverse Learning Environments and Their Solutions.** Wang, Lehman, Clune, Stanley, 2019. arXiv 1901.01753
- Quote: "many of which cannot be solved by direct optimization alone ... The ability to transfer solutions from one environment to another proves essential ... demonstrating the unpredictable nature of fortuitous stepping stones."
- Shows: solutions to one problem became stepping stones for others that direct training could not solve. **SHOWN** (simulated walkers)
- URL: https://arxiv.org/abs/1901.01753
- Design: supports reusing near misses from one puzzle as seeds for other puzzles.
#### **18. Go-Explore / First return, then explore.** Ecoffet, Huizinga, Lehman, Stanley, Clune. arXiv 1901.10995 (2019); Nature 2021, DOI 10.1038/s41586-020-03157-9
- Quote: "(1) remember previously visited states, (2) first return to a promising state (without exploration), then explore from it" ... "Montezuma's Revenge, Go-Explore scores a mean of over 43k points, almost 4 times the previous state of the art."
- Shows: remembering promising spots, going back to them and exploring from there cracked hard-exploration games. **SHOWN**
- URL: https://arxiv.org/abs/1901.10995 ; Crossref for the Nature DOI
- Design: the best AI match for "the egg". Centre the random blurts on remembered near misses, not on the start point.
#### **19. OMNI: Open-endedness via Models of human Notions of Interestingness.** Zhang, Lehman, Stanley, Clune, 2023. arXiv 2306.01711
- Quote: "countless learnable yet uninteresting tasks remain (e.g., minor variations of previously learned tasks)" ... "FM-based MoIs improve open-ended learning by focusing on tasks that are both learnable and interesting".
- Shows: using a big model to judge what is "interesting" beat uniform sampling or learning-progress alone. **SHOWN** (game tasks)
- URL: https://arxiv.org/abs/2306.01711
- Design: to steer the egg, a judge of "interesting and learnable" beats pure novelty. Our small judge is weak, though (see D).
- Also **20. OMNI-EPIC** (Faldor, Zhang, Cully, Clune, 2024, arXiv 2405.15568, https://arxiv.org/abs/2405.15568): generates "the next learnable (i.e., not too easy or difficult for the agent's current skill set) and interesting (e.g., worthwhile and novel) tasks." **SUGGESTED** (mostly qualitative). "Not too easy, not too hard" is a good rule for choosing which near misses to train on.
#### **21. Quality-Diversity through AI Feedback (QDAIF).** Bradley, Dai, Teufel, Zhang, ..., 2023. arXiv 2310.13032
- Quote: "QDAIF covers more of a specified search space with high-quality samples than do non-QD controls" and "human evaluation ... validates reasonable agreement between AI and human evaluation."
- Shows: an LLM can both generate and judge creative writing inside a MAP-Elites loop. **SHOWN** (with a large LLM judge)
- URL: https://arxiv.org/abs/2310.13032
- Design: a template for gift ideas: an archive by category plus a judge. It relies on a strong judge.
#### **22. FunSearch: Mathematical discoveries from program search with large language models.** Romera-Paredes et al., 2024, Nature 625:468. DOI 10.1038/s41586-023-06924-6
- Quote: "an evolutionary procedure based on pairing a pretrained LLM with a systematic evaluator ... we discover new constructions of large cap sets going beyond the best-known ones".
- Shows: generating then filtering with an exact checker made real math discoveries. **SHOWN**
- URL: https://eutils.ncbi.nlm.nih.gov (PMID 38096900)
- Design: generate-then-filter works in the real world when the filter is exact. Gift ideas lack one.
- Also **23. AlphaEvolve** (Novikov et al., 2025, arXiv 2506.13131, https://arxiv.org/abs/2506.13131): "found a procedure to multiply two 4 × 4 complex-valued matrices using 48 scalar multiplications; offering the first improvement, after 56 years, over Strassen's algorithm in this setting." **SHOWN** (white paper). The same lesson: the evaluator is what makes it work.
#### **24. Promptbreeder.** Fernando et al., 2023. arXiv 2309.16797
- Quote: "Promptbreeder mutates a population of task-prompts, and subsequently evaluates them for fitness on a training set. Crucially, the mutation of these task-prompts is governed by mutation-prompts that the LLM generates and improves".
- Shows: the way ideas get mutated can itself evolve. It beat Chain-of-Thought prompting on reasoning benchmarks. **SHOWN**
- URL: https://arxiv.org/abs/2309.16797
- Design: the "how much randomness" setting (the circle size) could be learned from which settings produced hits, not fixed by hand.

## D. LLM creativity, diversity collapse and training on your own outputs

#### **25. Can LLMs Generate Novel Research Ideas?** Si, Yang, Hashimoto, 2024. arXiv 2409.04109
- Quote: "LLM-generated ideas are judged as more novel (p < 0.05) than human expert ideas while being judged slightly weaker on feasibility." Full text: "out of the 4000 generated seed ideas, there are only 200 non-duplicate unique ideas" and "the best LLM evaluator ... only achieves an accuracy of 53.3%, lower than our inter-reviewer consistency of 56.1%" (random = 50).
- Shows: 100+ NLP experts rated the LLM ideas as more novel. But blurting saturates at 5% unique ideas, and LLM judges are near chance. Even the human experts only agree 56% of the time. **SHOWN**
- URL: https://arxiv.org/abs/2409.04109 ; https://arxiv.org/html/2409.04109
- Design: key evidence for "avoid repeats": without it, 95% of blurts are wasted. Also warns that judging is the weak link.
#### **26. The Ideation-Execution Gap.** Si, Hashimoto, Yang, 2025. arXiv 2506.20803
- Quote: "the scores of the LLM-generated ideas decrease significantly more than expert-written ideas on all evaluation metrics ... for many metrics there is a flip in rankings where human ideas score higher".
- Shows: once 43 experts actually carried the ideas out, the LLM's novelty advantage disappeared. **SHOWN**. It makes item 25's headline claim **DISPUTED**.
- URL: https://arxiv.org/abs/2506.20803
- Design: judge ideas on outcomes, not on how novel they look. For gifts, a "good" label should mean the recipient would like it, not that the idea sounds clever.
#### **27. AI models collapse when trained on recursively generated data.** Shumailov et al., 2024, Nature. DOI 10.1038/s41586-024-07566-y (arXiv 2305.17493)
- Quote: "indiscriminate use of model-generated content in training causes irreversible defects in the resulting models, in which tails of the original content distribution disappear."
- Shows: repeatedly training on unfiltered own output kills the rare cases first. **SHOWN**
- URL: https://api.crossref.org/works/10.1038/s41586-024-07566-y
- Design: matches our result that repeated known answers collapsed variety. The key word is "indiscriminate". See items 28 and 29 for the fixes.
#### **28. Is Model Collapse Inevitable? Breaking the Curse of Recursion by Accumulating Real and Synthetic Data.** Gerstgrasser, Schaeffer, et al., 2024. arXiv 2404.01413
- Quote: "accumulating the successive generations of synthetic data alongside the original real data avoids model collapse".
- Shows: collapse comes from replacing real data. Keeping all the old data avoids it. **SHOWN**. Items 27 and 30 are **DISPUTED** as universal claims.
- URL: https://arxiv.org/abs/2404.01413
- Design: at sleep, add new hits to a growing pile that keeps the original data. Never train on the new batch alone.
#### **29. Beyond Model Collapse: Scaling Up with Synthesized Data Requires Verification.** Feng, Dohmatob, Yang, Charton, Kempe, 2024. arXiv 2406.07515
- Quote: "verifiers, even imperfect ones, can indeed be harnessed to prevent model collapse".
- Shows: filtering self-generated data with a checker prevents collapse, even when the checker is imperfect. **SHOWN** (2 tasks)
- URL: https://arxiv.org/abs/2406.07515
- Design: direct support for "train only on checked hits". Matches our doubling result.
#### **30. Self-Consuming Generative Models Go MAD.** Alemohammad et al., 2023. arXiv 2307.01850
- Quote: "without enough fresh real data in each generation of an autophagous loop, future generative models are doomed to have their quality (precision) or diversity (recall) progressively decrease."
- Shows: image models degrade in self-training loops that lack fresh data. **SHOWN**
- URL: https://arxiv.org/abs/2307.01850
- Design: our "fresh real data" is new puzzles and the real-world checker. Keep them coming.
#### **31. STaR: Bootstrapping Reasoning With Reasoning.** Zelikman, Wu, Mu, Goodman, 2022. arXiv 2203.14465
- Quote: "fine-tune on all the rationales that ultimately yielded correct answers; repeat ... performs comparably to fine-tuning a 30× larger state-of-the-art language model on CommonsenseQA."
- Shows: training on your own correct attempts works. **SHOWN**
- URL: https://arxiv.org/abs/2203.14465
- Design: the published version of "sleep on lucky hits".
#### **32. Beyond Human Data: Scaling Self-Training (ReST-EM).** Singh et al., 2023. arXiv 2312.06585
- Quote: "(1) generate samples from the model and filter them using binary feedback, (2) fine-tune the model on these samples, and (3) repeat ... significantly surpasses fine-tuning only on human data."
- Shows: the same loop at PaLM-2 scale beats training on human data alone. **SHOWN** (math and code, which have exact checkers)
- URL: https://arxiv.org/abs/2312.06585
- Design: supports our loop when there is an exact checker. Only a few rounds were run ("a few times").
#### **33. Does RL Really Incentivize Reasoning Capacity Beyond the Base Model?** Yue et al., 2025. arXiv 2504.13837
- Quote: "While RLVR-trained models outperform their base models at small k (e.g., k = 1), the base models achieve a higher pass@k score when k is large."
- Shows: training on verified hits makes the first guess better but narrows the range of answers the model can reach. **DISPUTED** by item 34.
- URL: https://arxiv.org/abs/2504.13837
- Design: track pass@k at large k and the number of distinct answers, not just first-guess accuracy. Our variety collapse is this effect.
#### **34. ProRL: Prolonged RL Expands Reasoning Boundaries.** Liu et al., 2025. arXiv 2505.24864 (and **The Invisible Leash**, Wu et al., 2025, arXiv 2507.14843)
- Quote (ProRL): "RL-trained models consistently outperform base models across a wide range of pass@k evaluations, including scenarios where base models fail entirely". Quote (Leash): "the shrinkage of empirical support generally outweighs the expansion of empirical support under larger sampling budgets".
- Shows: whether self-training on hits expands or shrinks what a model can reach is still contested. ProRL's fixes were KL control, reference resets and diverse tasks. **DISPUTED**
- URL: https://arxiv.org/abs/2505.24864 ; https://arxiv.org/abs/2507.14843
- Design: if variety shrinks, try ProRL-style fixes (anchor to the old model, reset, keep tasks varied).
#### **35. Jointly Reinforcing Diversity and Quality (DARLING).** Li, Zhang, Yu, Saha, Khashabi, Weston, ..., 2025. arXiv 2509.02534
- Quote: "explicitly optimizing for diversity catalyzes exploration in online RL, which manifests itself as higher-quality responses" and "higher pass@1 ... and pass@k".
- Shows: rewarding variety together with quality improved both, including on math. **SHOWN**
- URL: https://arxiv.org/abs/2509.02534
- Design: supports a novelty bonus when choosing which hits to train on (e.g. weight unusual correct answers higher).
#### **36. Understanding the Effects of RLHF on LLM Generalisation and Diversity.** Kirk et al., 2023. arXiv 2310.06452
- Quote: "RLHF significantly reduces output diversity compared to SFT across a variety of measures, implying a tradeoff ... between generalisation and diversity."
- Shows: training toward a single reward trades away variety. **SHOWN**
- URL: https://arxiv.org/abs/2310.06452
- Design: a warning that our judge-driven training could narrow the model the same way.
#### **37. Does Writing with Language Models Reduce Content Diversity?** Padmakumar & He, ICLR 2024. arXiv 2309.05196
- Quote: "writing with InstructGPT (but not the GPT3) results in a statistically significant reduction in diversity."
- Shows: the feedback-tuned model made users' essays more alike. The base model did not. **SHOWN**
- URL: https://arxiv.org/abs/2309.05196
- Design: tuning for approval is what narrows variety. Keep an untuned (or less-tuned) generator for the blurt phase.
#### **38. Generative AI enhances individual creativity but reduces the collective diversity of novel content.** Doshi & Hauser, 2024, Science Advances. DOI 10.1126/sciadv.adn5290
- Quote: "generative AI–enabled stories are more similar to each other"; full text: five AI ideas raised novelty "8.1% ... over writers without generative AI access".
- Shows: a real-world writing experiment. Each writer got better, but the group's stories became more alike. **SHOWN**
- URL: https://api.crossref.org/works/10.1126/sciadv.adn5290 ; Europe PMC PMC11244532 full text
- Design: good individual hits and a narrower range can happen together. Measure both.
#### **39. NoveltyBench.** Zhang et al., 2025. arXiv 2504.05228 and **Artificial Hivemind** (Jiang et al., NeurIPS 2025 D&B oral). arXiv 2510.22954
- Quote: "larger models within a family often exhibit less diversity than their smaller counterparts"; Hivemind: "intra-model repetition ... and more so (2) inter-model homogeneity"; "LMs, reward models, and LM judges are less well calibrated to human ratings on model generations that elicit differing idiosyncratic annotator preferences".
- Shows: mode collapse is widespread in 2025 models. Judges are least reliable exactly where tastes differ, which is the case for gifts. **SHOWN**
- URL: https://arxiv.org/abs/2504.05228 ; https://arxiv.org/abs/2510.22954
- Design: gift judging depends on the recipient. A single "good" label is noisy by nature.
#### **40. Is Temperature the Creativity Parameter of LLMs?** Peeperkorn, Kouwenhoven, Brown, Jordanous, ICCC 2024. arXiv 2405.00492
- Quote: "temperature is weakly correlated with novelty, and unsurprisingly, moderately correlated with incoherence".
- Shows: turning up randomness buys a little novelty and a lot of nonsense. **SHOWN** (one model, one prompt)
- URL: https://arxiv.org/abs/2405.00492
- Design: a caution for the "growing circle". Growing raw randomness mostly adds junk. Grow the search radius in idea space (items 16, 18) rather than noise in word choice.
#### **41. Adaptive Temperature (AdapT) sampling.** Zhu et al., 2023. arXiv 2309.02772
- Quote: "We apply a larger temperature when sampling for challenging tokens ... smaller temperature for confident tokens".
- Shows: randomness applied only at uncertain points beat a fixed temperature for code. **SHOWN**
- URL: https://arxiv.org/abs/2309.02772
- Design: supports making the circle size adaptive: widen it where the model is stuck and keep it tight elsewhere.
#### **42. Verbalized Sampling** (Zhang, Yu, Chong, ..., Manning, 2025, arXiv 2510.01171) and **Prompting Diverse Ideas** (Meincke, Mollick, Terwiesch, 2024, arXiv 2402.01727)
- Quote: "VS increases diversity by 1.6-2.1x over direct prompting"; Meincke: "pools of ideas generated by GPT-4 ... are less diverse than ideas generated by groups of human subjects" and "Chain-of-Thought (CoT) prompting leads to the highest diversity".
- Shows: how you ask changes variety a lot, at no training cost. **SHOWN**
- URL: https://arxiv.org/abs/2510.01171 ; https://arxiv.org/abs/2402.01727
- Design: try changing how we ask for ideas before adding raw noise.
#### **43. Large Language Monkeys: Scaling Inference Compute with Repeated Sampling.** Brown et al., 2024. arXiv 2407.21787
- Quote: "SWE-bench Lite ... increases from 15.9% with one sample to 56% with 250 samples" and "In domains without automatic verifiers ... majority voting and reward models ... plateau beyond several hundred samples".
- Shows: more blurts give more lucky hits, but only a perfect checker can collect them. **SHOWN**
- URL: https://arxiv.org/abs/2407.21787
- Design: the core "maximize lucky hits" evidence, and the core warning. For gifts, gains will stall at the judge.

## E. Judging ideas: how well can people or models pick winners?

#### **44. The Limits of Inference Scaling Through Resampling.** Stroebl, Kapoor, Narayanan, 2024. arXiv 2411.17501
- Quote: "fundamentally limited when verifiers are imperfect and have a non-zero probability of producing false positives ... optimal sampling attempts are often fewer than 10".
- Shows: with a leaky checker, more blurts eventually add more false hits than real ones. **SHOWN** (code)
- URL: https://arxiv.org/abs/2411.17501
- Design: with a judge picking a good gift first only 3/10 times (base rate ~15%), training on "judged hits" will include many false ones. Measure the judge's false-positive rate before scaling blurts.
#### **45. Predicting Empirical AI Research Outcomes with Language Models.** Wen, Si, Chen, He, Feng, 2025. arXiv 2506.00794
- Quote: "off-the-shelf frontier LMs like o3 perform no better than random guessing" vs "our system achieves 77% accuracy"; experts 48.9% vs system 64.4% (NLP).
- Shows: judging idea quality is hard for experts and frontier models alike. A judge trained on real outcomes did much better. **SHOWN**
- URL: https://arxiv.org/abs/2506.00794
- Design: supports training our judge on outcome labels, as we do, and expecting it to be the bottleneck.
#### **46. The selection of creative ideas after individual idea generation.** Rietzschel, Nijstad, Stroebe, 2010, British Journal of Psychology. DOI 10.1348/000712609X414204
- Quote: "people do not perform optimally at idea selection ... We identified the strong tendency of our participants to select feasible and desirable ideas, at the cost of originality".
- Shows: people pass over their original ideas and pick safe ones. **SHOWN**
- URL: https://eutils.ncbi.nlm.nih.gov (PMID 19267959)
- Design: our judge may learn the same bias toward safe, typical gifts. Check whether its top picks are less original than the average hit.
#### **47. Looking Across and Looking Beyond the Knowledge Frontier.** Boudreau, Guinan, Lakhani, Riedl, 2016, Management Science. DOI 10.1287/mnsc.2015.2285
- Quote: "evaluators systematically give lower scores to research proposals that are closer to their own areas of expertise and to those that are highly novel."
- Shows: in 2,130 randomized evaluator–proposal pairs, novelty was penalized. **SHOWN**
- URL: https://api.crossref.org/works/10.1287/mnsc.2015.2285
- Design: judges punish novelty. Consider a separate novelty bonus so the judge doesn't erase the "lucky, unusual" hits.
#### **48. Balancing on the Creative Highwire.** Berg, 2016, Administrative Science Quarterly. DOI 10.1177/0001839216642211
- Quote: "creators were more accurate than managers when forecasting about others' novel ideas, but not their own"; the advantage "may be tied to the emphasis on both divergent thinking (idea generation) and convergent thinking (idea evaluation)".
- Shows: circus professionals, checked against 13,248 audience members. People who both generate and judge forecast best, but not for their own ideas. **SHOWN**
- URL: https://api.crossref.org/works/10.1177/0001839216642211
- Design: a judge separate from the generator may help. Self-judging is weakest on your own ideas.

## Dropped or title-only (could not fetch an abstract or key number)
- Campbell 1960, "Blind variation and selective retentions in creative thought as in other knowledge processes", Psych Review, DOI 10.1037/h0040373. Title verified only. It is the classic origin of generate-then-filter (item 3 builds on it).
- Mednick 1962, "The associative basis of the creative process", Psych Review, DOI 10.1037/h0048850. Title verified only. The test it introduced (the RAT) is used in item 11.
- Simonton 1997, Psych Review, DOI 10.1037/0033-295X.104.1.66 (equal-odds source). Title verified, abstract withheld by publisher. Use items 1–4 instead.
- Diehl & Stroebe 1987; Rietzschel et al. 2006, "Productivity is not enough"; Reinig & Briggs 2008; Organisciak et al. 2023 (LLM scoring of divergent thinking). Abstracts not retrievable, so no claims made.
- Wagner 2004 per-group percentages were not taken from the full text. Only "more than twice" is quoted.
