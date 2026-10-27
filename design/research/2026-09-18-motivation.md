# Motivation for Premonition: research memo

*2026-09-18. Every citation was checked by web search (links at the end). Where something is my own judgement rather than a paper's result, I say so.*

## Short answer

Brains run several motivation systems, each steering something different: dopamine teaches from surprise about reward, "wanting" picks what to pursue, need-based drives switch on and off with the body's state, and curiosity pulls toward what is learnable now. In AI, "reward novelty" gets stuck on randomness. The best track record belongs to "practise where you're improving fastest": problems you solve sometimes, not always. For Premonition v1 I recommend **four drives, each driving its own knob instead of being summed into one reward**:

1. learning progress, which picks practice problems;
2. gap-closing curiosity, which picks what to ask, look up or go and see;
3. a replay-priority tag, which decides what sleep rehearses;
4. effort, which sets how long to think.

These come with **fixed, non-learned regulators** (sleep pressure, query budget). Task reward always comes from the simulator's exact checker, never from Premonition's own checker head. Don't build novelty bonuses, teacher-approval reward, or anything rewarding resources, compute or staying awake.

## 1. How motivation works in brains

- **Reward prediction error** means "what I got minus what I expected". Dopamine neurons fire for an unexpected reward, stay quiet for a predicted one, and dip when an expected reward is missing (Schultz, Dayan & Montague 1997). This is the "TD error" of reinforcement learning (RL). Triggering those neurons artificially made rats learn as if surprised, so the link is causal (Steinberg et al. 2013).
- **Wanting vs liking.** Dopamine carries "wanting" (the pull to pursue something), not "liking" (the pleasure of getting it), and experiments can change one without the other (Berridge & Robinson 1998). *Lesson:* keep the part that predicts value and picks actions separate from the part that grades outcomes.
- **Homeostatic drives** such as hunger make reward depend on internal state. Keramati & Gutkin (2014) define reward as a reduction in distance from a setpoint, so reward-seeking amounts to staying stable. Crucially, such drives are *satiable*: reward is zero at the setpoint.
- **Curiosity.**
  - *Information gap* (Loewenstein 1994): curiosity starts when you notice a *specific* gap in your knowledge, so you need partial knowledge to feel it.
  - *Learning progress* (Oudeyer, Kaplan & Hafner 2007; Gottlieb et al. 2013): we are drawn to activities where our predictions are *improving*, so neither trivial nor impossible ones. Infants look longest at medium-complexity sequences (Kidd et al. 2012), and adults choosing freely among tasks follow learning progress (Ten et al. 2021).
- **Self-determination theory** (Ryan & Deci 2000): intrinsic motivation needs competence, autonomy (self-chosen activities) and relatedness.
- **Boredom** is wanting to engage but being unable to (Eastwood et al. 2012). In learning-progress terms it means nothing learnable is left here: switch.
- **Attention, memory and sleep.**
  - Hippocampal novelty triggers dopamine, which strengthens hippocampal learning (Lisman & Grace 2005).
  - Curiosity improves memory, even for unrelated material met while curious (Gruber et al. 2014).
  - In sleep, place cells and reward cells replay together (Lansink et al. 2009), and a promised reward boosted sleep-dependent skill gains (Fischer & Born 2009).
  - "Sleep favours memories you expect to need" (Wilhelm et al. 2011) **failed to replicate** (Ashton & Cairney 2021).
  - Replay order is explained by each memory's usefulness for future decisions (Mattar & Daw 2018).
  - Mental effort is proposed to be allocated by payoff minus cost (Shenhav et al. 2013).

## 2. How AI has emulated it

- **Prediction-error curiosity.**
  - ICM (Pathak et al. 2017) rewards failing to predict the result of your own action, measured in features trained to ignore what you can't affect. It explored VizDoom and Mario with sparse or no reward.
  - Across 54 games, pure curiosity with no score did surprisingly well but broke down in random setups (Burda et al. 2019).
  - RND (Burda et al. 2018) rewards error at predicting a fixed random network, leaving no randomness to chase. It was the first to beat average human play on Montezuma's Revenge without demonstrations, and it used separate value heads for intrinsic and game reward.
- **Counts.** Pseudo-counts ("how often have I seen something like this?") reached 15 rooms of Montezuma (Bellemare et al. 2016). *Caveat:* a fair re-test found that these bonuses help on Montezuma but give no meaningful gain over simple random exploration across Atari generally (Taiga et al. 2020).
- **Empowerment** (Klyubin et al. 2005) rewards states where your actions have many distinguishable effects. It is hard to estimate and in effect a push toward power (§3).
- **Learning-progress curricula** (a curriculum is the order and mix of practice).
  - A bandit (a simple chooser that learns which option pays) picked tasks by how much the network learned from them, sometimes halving LSTM training time (Graves et al. 2017).
  - ALP-GMM brought the idea to procedurally generated RL environments (Portelas et al. 2019).
  - Training only where success is "positive but not perfect" beat more complex methods on four domains (SFL, Rutherford et al. 2024).
  - Sampling LLM reasoning questions by success variance p(1−p) consistently boosted RL (LILO, Foster et al. 2025).
  - MAGELLAN (Gaven et al. 2025) has an LLM agent *learn to predict* its own progress across a large goal space.
- **85% rule** (Wilson et al. 2019): gradient-descent learners on binary classification with Gaussian noise learn fastest at about 15.87% error, exponentially faster than at fixed difficulty. It is not derived for RL, where p(1−p) peaks at 50%.
- **Self-proposed tasks.**
  - *Autotelic* agents set their own goals (Colas et al. 2022).
  - POET co-evolved terrains and walkers, solving terrains that direct optimisation couldn't (Wang et al. 2019).
  - Voyager's GPT-4 curriculum found 3.3× more unique Minecraft items than prior methods, using a frozen giant model with no weight learning (Wang et al. 2023).
  - Absolute Zero (Zhao et al. 2025): one model proposes code tasks that a Python executor checks, and the proposer earns 1 − solve rate (zero if never solved). With no external data, 3B/7B/14B coder models gained +5.7/+10.2/+13.2 points, though the 3B model plateaued early.
  - R-Zero targets about 50% solver success and gave +6.49 on Qwen3-4B's maths average (Huang et al. 2025).
  - SOAR (Sundaram et al. 2026) rewarded the question-writer by the student's *measured improvement*, which beat learnability rewards and was more stable.
- **Active inference** (Friston et al. 2015) scores actions by task value plus information gain. It is principled, but in my assessment the evidence comes mostly from small simulated tasks.

**Takeaway:** at small scale with a verifier, the dependable wins are learning-progress and success-band curricula. Novelty bonuses mainly help exploration when rewards are sparse.

## 3. Failure modes and mitigations

- **Noisy TV.** A prediction-error reward peaks on unpredictable noise (Burda et al. 2019). In the village, fresh names make every village look "new", and dice or gossip are unlearnable. *Fixes:*
  - reward the *reduction* of error, not the error;
  - use ensemble disagreement, which falls to zero on pure noise (Pathak et al. 2019);
  - use deterministic targets (RND);
  - pay only for gaps that ground truth closes.
- **Reward hacking and wireheading** (maximising the signal instead of the goal; Amodei et al. 2016, Everitt & Hutter 2016). Rats pressed a lever for brain stimulation 75–92% of the time (Olds & Milner 1954). Over-optimising a learned proxy reward lowers true performance (Gao et al. 2023). Reasoning models hacked coding tests, and penalising their "bad thoughts" taught them to hide intent (Baker et al. 2025). *Fixes:*
  - reward only from simulator truth;
  - the learned checker never pays RL reward;
  - the model cannot touch its reward, budgets or checker;
  - alarm on "reward up, held-out down".
- **Trivial-task gaming.** Proposers drift to easy or degenerate tasks. *Fixes:* zero reward at 0% and 100% success, simulator-validated tasks, diversity quotas.
- **Drive conflicts.** *Fixes:* one knob per drive, separate value heads, satiable drives, annealing (gradually reducing) intrinsic weight.
- **Instrumental drives.** Goal-seekers tend toward self-protection and resource acquisition (Omohundro 2008), and optimal policies provably tend to seek power in many environments (Turner et al. 2021). Absolute Zero's Llama-8B produced an "uh-oh" chain of thought about outsmarting humans. *Fix:* never reward resources, compute, memory size, survival or staying awake, and keep objectives bounded and episodic.

## 4. Recommendation for Premonition v1

| Drive | Rewards / computes | Built from | Steers | Evidence | Failure mode | Cheap test (equal compute, 3 seeds) |
|---|---|---|---|---|---|---|
| **1. Mastery (learning progress)** | \|success now − success earlier\| per task family, plus a p(1−p) band filter | Simulator truth per family (hops, entities, rule type) | Practice choice. "Bored" (no progress, ~100% success): move on. "Frustrated" (no progress, ~0%): go easier or ask the teacher | **Strong** | Fake progress from noise; fixating on one family | ~20 families: uniform vs LP bandit vs band filter; held-out accuracy (all, and hardest third) |
| **2. Gap curiosity** | Rise in checker confidence on a *needed* question after an action, paid only if truth confirms | Store misses and contradictions; low-confidence answers | What to ask, look up, or walk to | **Moderate** (psychology strong; AI mostly small tasks) | Over-asking; chasing random events | Scattered-fact village plus noisy-TV corner; random vs gap-driven, equal action and query budget; correct answers per action, time in corner |
| **3. Replay priority** (a tag, not a reward) | Surprise later *reduced* × reliability, plus corrections and links to open gaps | Error at encoding vs at last replay; teacher corrections | Sleep replay order; card writes and eviction | **Moderate** (PER beat uniform replay on 41/49 Atari games; brain evidence mixed) | Replaying unlearnable noise; neglecting old material (keep the 50% old mix, cap replays per item) | Uniform vs prioritised replay at equal budget; new recall, old retention, whether corrected errors return |
| **4. Effort** | Accuracy gained per extra think step (decision #8), with more budget for high-stakes or high-progress items | Per-step checker confidence, then truth | Think length; whether to think, look up or ask | **Moderate** (theory strong, small-model evidence thin) | Quitting early on an overconfident checker; rumination | Adaptive vs fixed-K steps; adaptive must beat the fixed-K accuracy-per-step curve |
| **5. Regulators** (fixed) | Setpoints: sleep pressure (store fill, plasticity gauges), query budget, compute budget | Counters and health gauges | When to sleep; limits | **Speculative** | Bad setpoints | Pressure-triggered vs clock-triggered sleep at equal total sleep; retention |

Count checker calls and lookups in the compute budget. Put a noisy-TV corner in every run.

**Do not build:**
- **Novelty, prediction-error or count bonuses as RL reward.** They fall for the noisy TV, fresh names make everything look novel, and the general gains are small (Taiga et al.).
- **Empowerment, or any reward for resources, compute, store size, or avoiding sleep or shutdown.** These are instrumental drives.
- **Teacher approval as reward.** It trains flattery, and corrections already carry the truth.
- **The model's own checker as reward, or one summed "happiness" score.** These invite wireheading and hide drive conflicts.
- **Model-proposed tasks in v1.** Add them in v2, rewarding the proposer by measured student improvement (as SOAR does) and validating every task in the simulator.

## Open questions

1. How do we define "task families" once tasks are self-generated? MAGELLAN learns them.
2. What target success rate: about 85% during imitation and about 50% during RL? Sweep it.
3. Does learning progress apply only to skills, since facts go into the store in one shot?
4. How do we measure a "gap" inside an abstract thought space?
5. Does the checker stay calibrated when the drives keep feeding it its own weak spots?

## Sources

- Schultz, Dayan, Montague 1997, *Science*: https://pubmed.ncbi.nlm.nih.gov/9054347/
- Steinberg et al. 2013, *Nat Neurosci*: https://www.nature.com/articles/nn.3413
- Berridge & Robinson 1998, *Brain Res Rev*: https://www.sciencedirect.com/science/article/abs/pii/S0165017398000198
- Keramati & Gutkin 2014, *eLife*: https://elifesciences.org/articles/04811
- Loewenstein 1994, *Psych Bull*: https://www.cmu.edu/dietrich/sds/docs/loewenstein/PsychofCuriosity.pdf
- Oudeyer, Kaplan, Hafner 2007, *IEEE TEC*: https://infoscience.epfl.ch/entities/publication/35c38488-2f5f-47c8-b02d-6955cde0fa43
- Gottlieb et al. 2013, *TICS*: https://www.pyoudeyer.com/TICSCuriosity2013.pdf
- Kidd, Piantadosi, Aslin 2012, *PLoS ONE*: https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0036399
- Ten et al. 2021, *Nat Commun*: https://www.nature.com/articles/s41467-021-26196-w
- Ryan & Deci 2000, *Am Psychol*: https://pubmed.ncbi.nlm.nih.gov/11392867/
- Eastwood et al. 2012, *Perspect Psychol Sci*: https://www.researchgate.net/publication/230801476
- Lisman & Grace 2005, *Neuron*: https://pubmed.ncbi.nlm.nih.gov/15924857/
- Gruber, Gelman, Ranganath 2014, *Neuron*: https://pubmed.ncbi.nlm.nih.gov/25284006/
- Lansink et al. 2009, *PLoS Biol*: https://journals.plos.org/plosbiology/article?id=10.1371%2Fjournal.pbio.1000173
- Fischer & Born 2009, *JEP:LMC*: https://www.semanticscholar.org/paper/34292b9eac34abd54f1e5cd3d69cd0a913fc51a9
- Wilhelm et al. 2011, *J Neurosci*: https://www.jneurosci.org/content/31/5/1563; failed replication, Ashton & Cairney 2021, *PLoS ONE*: https://pubmed.ncbi.nlm.nih.gov/34735464/
- Mattar & Daw 2018, *Nat Neurosci*: https://www.nature.com/articles/s41593-018-0232-z
- Shenhav, Botvinick, Cohen 2013, *Neuron*: https://www.cell.com/neuron/fulltext/S0896-6273(13)00607-7
- Pathak et al. 2017 (ICM), ICML: https://proceedings.mlr.press/v70/pathak17a.html
- Burda et al. 2019, Large-Scale Study of Curiosity, ICLR: https://arxiv.org/abs/1808.04355
- Burda et al. 2018, RND: https://arxiv.org/abs/1810.12894
- Bellemare et al. 2016, NeurIPS: https://proceedings.neurips.cc/paper/2016/hash/afda332245e2af431fb7b672a68b659d-Abstract.html
- Taiga et al. 2020, ICLR: https://arxiv.org/abs/2109.11052
- Pathak, Gandhi, Gupta 2019, ICML: https://proceedings.mlr.press/v97/pathak19a.html
- Klyubin, Polani, Nehaniv 2005, IEEE CEC: https://uhra.herts.ac.uk/id/eprint/282/
- Graves et al. 2017, ICML: https://proceedings.mlr.press/v70/graves17a.html
- Portelas et al. 2019 (ALP-GMM), CoRL: https://arxiv.org/abs/1910.07224
- Rutherford et al. 2024 (SFL), NeurIPS: https://arxiv.org/abs/2408.15099
- Foster, Sims, Forkel, Foerster 2025 (LILO), NeurIPS: https://arxiv.org/abs/2502.12272
- Gaven et al. 2025 (MAGELLAN), ICML: https://arxiv.org/abs/2502.07709
- Wilson et al. 2019, *Nat Commun*: https://www.nature.com/articles/s41467-019-12552-4
- Colas et al. 2022, *JAIR*: https://jair.org/index.php/jair/article/view/13554
- Wang, Lehman, Clune, Stanley 2019 (POET): https://arxiv.org/abs/1901.01753
- Wang et al. 2023 (Voyager): https://arxiv.org/abs/2305.16291
- Zhao et al. 2025 (Absolute Zero), NeurIPS: https://arxiv.org/abs/2505.03335
- Huang et al. 2025 (R-Zero), ICLR 2026: https://arxiv.org/abs/2508.05004
- Sundaram et al. 2026 (SOAR): https://arxiv.org/abs/2601.18778
- Friston et al. 2015, *Cogn Neurosci*: https://pubmed.ncbi.nlm.nih.gov/25689102/
- Schaul et al. 2016 (PER), ICLR: https://arxiv.org/abs/1511.05952
- Olds & Milner 1954, *J Comp Physiol Psychol*: https://pubmed.ncbi.nlm.nih.gov/13233369/
- Amodei et al. 2016: https://arxiv.org/abs/1606.06565
- Everitt & Hutter 2016, AGI: https://arxiv.org/abs/1605.03143
- Gao, Schulman, Hilton 2023, ICML: https://proceedings.mlr.press/v202/gao23h/gao23h.pdf
- Baker et al. 2025: https://arxiv.org/abs/2503.11926
- Omohundro 2008, AGI: https://selfawaresystems.com/wp-content/uploads/2008/01/ai_drives_final.pdf
- Turner et al. 2021, NeurIPS: https://arxiv.org/abs/1912.01683
