# Gap check #3: self-controlled global mode switching (neuromodulation)

Claim being checked: neuromodulators shift the whole brain between focused/exploit and diffuse/explore based on how well
things are going; in AI the same knob (temperature, entropy bonus, learning rate) is set by a human or a fixed schedule,
and models do not learn to set it from an internal sense of being stuck.

---

## 1. Verdict (80 words)

**Already well covered.** The brain half is real but softer than advertised. The AI half of the claim is simply out of
date: SAC tunes its own temperature, Agent57 runs a bandit meta-controller over exploration rates, meta-gradient RL and
STAC self-tune those knobs online, Pîslar et al. trigger exploration bouts from a value-prediction-mismatch "stuck"
signal, and a Feb-2026 paper has an LLM learn a temperature policy from its own hidden states. What is thin is
per-step, inference-time persistence control — a narrow slice, not a missing mechanism.

---

## 2. What the brain does — and how good the evidence is

**The story.** Aston-Jones & Cohen's adaptive gain theory (2005) says locus coeruleus (LC) neurons have two modes.
Phasic bursts locked to a decision = focused exploitation. High tonic baseline firing = disengagement and search for
something else. Noradrenaline released cortex-wide acts like a gain (contrast) knob on everything at once, so one small
nucleus changes the operating point of the whole network. Yu & Dayan (2005) add a division of labour: acetylcholine
signals *expected* uncertainty (this cue is known to be 20% unreliable), noradrenaline signals *unexpected* uncertainty
(the rules just changed). Serotonin from the dorsal raphe controls waiting/persistence. Dopamine carries reward
prediction error and also sets vigour.

**Quality, honestly:**

- **Moderate-to-strong for "one nucleus globally changes gain."** Anatomy is not in doubt (LC projects almost
  everywhere), and optogenetic LC stimulation causally shifts cortical state and dilates the pupil in mice
  (J. Neurosci. 2025; PubMed 40039165).
- **Moderate for "tonic LC causes disengagement/exploration."** The one clean causal test is Kane et al. (2017): DREADD
  stimulation of tonic LC in rats caused them to leave patches early. But the paper's own reading is unflattering — the
  effect was carried by **increased decision noise** (less sensitivity to reward value) plus reduced task participation,
  more omissions, slower responses. That is "the animal got sloppier," which is not obviously the same thing as
  "the animal switched into a smart search mode."
- **Weak-to-moderate for the pupil evidence that most of the field rests on.** Gilzenrat et al. (2010) and Jepma &
  Nieuwenhuis (2011) found bigger baseline pupil before exploratory choices, which is correlational. Megemont,
  McBurney-Lin & Yang (2022, eLife) then showed pupil diameter predicts only a small fraction of LC spiking
  moment-to-moment and the pupil↔LC relationship drifts a lot between sessions. So a large pile of human pupillometry is
  a noisy proxy for the thing it claims to measure. Recent human work also splits *directed* from *random* exploration
  and finds baseline pupil tracks random exploration / global uncertainty, not goal-directed information seeking — which
  is a weaker and partly different claim than adaptive gain theory made.
- **Moderate-to-strong for serotonin and patience** — the part most relevant to our "stops after 3 calls" bug. Miyazaki
  et al. (2014, *Current Biology*) optogenetically activated dorsal-raphe serotonin neurons and mice waited longer in
  reward-omission trials — a causal, replicated-in-lab effect. Miyazaki et al. (2018, *Nat Commun*) sharpened it: the
  patience boost only appears when reward probability is **high** (75%, not 50/25%) and timing is **uncertain**. A 2024
  follow-up (Front. Neurosci.) found the effect **does not transfer** to sustained *acting* for reward, only to
  *waiting*. So serotonin is not a general "keep going" knob; it is closer to "keep waiting when you have good reason to
  believe something is coming."
- **Contested framing:** LC/ACh/5-HT/DA do not map cleanly onto four separate hyperparameters. That one-to-one mapping is
  a modeller's convenience, not an established finding.

**Bottom line for us:** the brain does have global, internally-triggered mode switches, and they are driven by
value/uncertainty signals rather than a clock. But the strongest causal version of the explore switch looks like
"add noise and disengage," and the patience switch is narrow and reward-expectancy-gated.

---

## 3. What AI has already done

Closest works, newest-first weighted:

| Work | Year | What it showed | Scale |
|---|---|---|---|
| [IntroLLM: "Look Inward to Explore Outward"](https://arxiv.org/abs/2602.13035) | Feb 2026 | A small MLP head reads the LLM's **own final-layer hidden state** at each decoding step and outputs a sampling **temperature**; trained jointly with the token policy by hierarchical GRPO. This is literally "learn the exploration knob from an internal state." +0.122% params; AIME24 Avg@8 19.17 vs 15.00 for best baseline. | Qwen3 1.7B/4B, math benchmarks |
| [Stabilizing Extrapolation in Looped Transformers](https://arxiv.org/abs/2606.29983) | Jun 2026 | **Most relevant negative/diagnostic result for our bug.** Looped transformers fail to extrapolate to more loop iterations than trained because of a *spurious correlation between input length and loop count during training*. Fix: randomise the loop count at training time; they also test RL-Halting (learned stochastic stopping), which often helps the accuracy/stability trade-off but "can stabilize suboptimal computation." Their framing: when-to-stop is a **training-time design choice**, not an inference knob. | Binary addition, Dyck-1, Unique Set, Copy |
| [AER: adaptive entropy coefficient for LLM RL](https://arxiv.org/abs/2510.10959) | 2025 (Findings ACL 2026) | Fixed entropy-bonus coefficients are brittle; a difficulty-aware, dynamically adjusted coefficient anchored to initial entropy beats them and avoids entropy collapse in RLVR. | 7B-class LLMs |
| [Lifelong RL via Neuromodulation](https://arxiv.org/abs/2408.08446) (Lee, Liebana, Clopath, Dabney) | 2024 | Explicit ACh/NA-inspired framework for adapting learning rates/uncertainty handling across tasks. Validated only on a **non-stationary multi-armed bandit** — tiny scale. | bandit |
| [When should agents explore?](https://arxiv.org/abs/2108.11811) (Pîslar et al., ICLR 2022) | 2022 | Intra-episodic mode switching with an **"informed" trigger: value-promise discrepancy** — the gap between what the value function promised k steps ago and what actually happened. That *is* a "stuck" signal. Plus **homeostasis**: an adaptive threshold that holds the switching rate near a target so it needs no tuning. Beat step-level and episode-level baselines on 7 Atari games, R2D2, ~2B frames, 33 seeds. **Caveats: the trigger is hand-designed, not learned, and results were strongly game-dependent with no universally best variant.** | Atari, large |
| [Agent57](https://arxiv.org/abs/2003.13350) (Badia et al.) | 2020 | A sliding-window UCB **meta-controller** picks, per actor and over training, which (exploration-rate, discount) policy to run — the agent shifts from exploratory/short-horizon to exploitative/long-horizon on its own. First to beat the human benchmark on all 57 Atari games. | Atari, very large |
| [STAC](https://arxiv.org/abs/2002.12928) (Zahavy et al. 2020) / [meta-gradient RL](https://arxiv.org/abs/1805.09801) (Xu, van Hasselt, Silver 2018) | 2018–20 | Self-tune *all* differentiable loss hyperparameters (discount, bootstrapping, entropy weight) online by meta-gradient. Agents learned non-smooth schedules a human would not have written. | Atari / IMPALA |
| [SAC with automatic entropy tuning](https://arxiv.org/abs/1812.05905) (Haarnoja et al. 2018) | 2018 | Temperature becomes a Lagrange multiplier solving a **constraint** (hold entropy ≥ target). Removed per-task tuning. Note: the target entropy is still a human-set constant (−dim(A)). | MuJoCo, standard |
| [Backpropamine](https://arxiv.org/abs/2002.10585) (Miconi, Rawal, Clune, Stanley, ICLR 2019) | 2019 | A learned, network-produced scalar "dopamine" signal gates Hebbian plasticity — i.e. the net learns to control *its own learning rate* per-connection. Beat matched-param LSTMs on maze RL and language modelling. | small–medium |
| [ACT](https://arxiv.org/abs/1603.08983) (Graves 2016) / [PonderNet](https://arxiv.org/abs/2107.05407) (Banino, Balaguer, Blundell 2021) / [adaptive recurrent vision](https://arxiv.org/abs/2311.06964) (Veerabadran et al., NeurIPS 2023) | 2016–23 | Learned halting. **ACT is unstable, biased-gradient and needs a grid-searched ponder cost.** PonderNet reformulates halting as a geometric distribution with a KL prior and on parity trained at 1–48 elements it **extrapolated near-perfectly to 49–96 while ACT stayed at chance**, raising its own step count from ~3 to ~5. Veerabadran et al. show ConvRNNs with a learned halt zero-shot scale compute to unseen difficulty. | small–medium |

Also relevant background: Wang et al. (2018, *Nat Neurosci*) "prefrontal cortex as a meta-RL system" is the theoretical
bridge — a recurrent net trained by a slow RL signal learns a fast learning algorithm inside its activations, including
volatility-dependent effective learning rates. That is the mainstream AI answer to "who sets the knob": nobody, it falls
out of meta-learning.

---

## 4. The real gap

Almost nothing of the headline claim survives. What is genuinely thin:

1. **Learned, per-step, inference-time persistence control.** Agent57/STAC/SAC all adapt knobs on a *training* timescale
   or across a population of policies. Pîslar et al. do it within an episode, but the trigger is hand-designed.
   IntroLLM (2026) does it per-token and learned, but the signal is a raw hidden state, not an explicit
   progress/stuck measure, and it is only demonstrated during RL training of the token policy.
2. **A "stuck" signal defined over *symbolic sub-goal progress*** ("I've made three calls and still don't have the
   relation I need") rather than over value-function error or token entropy. Nobody has needed this because mainstream
   agents don't have an explicit call-chain to be stuck in.
3. **Separating the two knobs.** Biology uses at least two (NA: noise/gain; 5-HT: patience). AI work almost always
   adjusts one scalar (entropy/temperature). Whether an agent benefits from independently learned *noise* and
   *persistence* controls is, as far as I found, untested.

That is a real but narrow slice. It is a nice-to-have module, not an unexplored mechanism.

**And a warning that matters more than the gap:** the 2026 looped-transformer paper says our exact failure mode —
"learned to make 3 calls because 3 was the longest practised chain" — is a **spurious training-time correlation**, not a
missing exploration knob. Raising entropy on a confident "STOP at 3" policy makes the stop *noisier*, not *later*. So
the neuromodulation framing may be diagnosing the wrong organ.

---

## 5. Design proposals — three ways to put this into a model

### Option A — Probabilistic halting head (PonderNet ported onto the dispatcher). **Build first.**

**(a) Plain words.** Right now the dispatcher has a STOP button and it learned "press it on the third call." Instead of
a button, give it a *coin* it flips after every call: "given I haven't stopped yet, what's the chance I should stop
now?" Train it so the answer depends on what it has *found*, not on how many calls it has made — and add a gentle
pressure that says "your stopping pattern should look like a fixed-rate coin," which is exactly the pressure that stops
it memorising the number 3.

**(b) Concrete design.** Replace the discrete STOP action in the dispatcher with a halting head
`λ_n = sigmoid(w·h_n + b)` = P(halt at step n | not halted before), giving the geometric-style distribution
`p_n = λ_n · Π_{j<n}(1 − λ_j)`. Loss = expected task loss under `p_n` + `β · KL(p ‖ Geometric(λ_p) truncated at N)`.
Runs at every dispatcher step at both train and test time. Learned: `w, b` (~d+1 params, so **≈ 50–300 params** on top
of the 15–24k dispatcher — negligible). Fixed: `λ_p` and `β` (two hyperparameters; PonderNet reports it is far less
brittle to these than ACT's ponder cost, but they still need a 3-point sweep). Wiring: the operator is untouched and
frozen; only the dispatcher's terminal action changes. Crucially, **also randomise the maximum step budget N per
training episode** (the looped-transformer fix) so chain length and stop probability are decorrelated.

**(c) At LLM scale.** This is the "learn when to stop thinking" line — a halting head on a looped/recurrent transformer
block, or on reasoning-trace segments, trained with the geometric KL rather than a hand-set token budget.

**(d) Falsifiable toy test.** Train the dispatcher on 1–3-hop chains **with hints removed**, evaluate on 4- and 5-hop.
Controls: (i) current discrete-STOP dispatcher, same steps, same seeds; (ii) discrete-STOP dispatcher + randomised step
budget only — this isolates whether the halting head does anything beyond the training-distribution fix; (iii)
matched-compute: cap all arms at the same total operator calls per episode during training. 5 seeds. **Pass mark: ≥ 40/64
on 4-hop and ≥ 25/64 on 5-hop, with ≥ 3 of 5 seeds above chance, while 3-hop stays ≥ 60/64.** Fails if 4-hop accuracy
stays near the current 4/64, or if it only matches control (ii) — then the halting formulation added nothing and the bug
was purely the training distribution. **Artefact risk:** the KL prior can be satisfied by the model simply always
running to N and answering from the last step — check the realised halt-step histogram actually varies with true hop
count, and report correlation between predicted halt step and ground-truth hops. Also: a 64-item eval grid means ±6%
noise; pre-register the numbers.
**Cost: small** (a day; well under 30 min per run).

### Option B — Stall-gain head (the existing sketch, refined and partly criticised)

**(a) Plain words.** A tiny extra brain-part watches whether the last lookup actually made progress. If the answer is
"no, we're going in circles," it turns up two dials: make the next choice less predictable (more exploring) and make
"keep going" more attractive than "stop." It's the noradrenaline+serotonin story in ~2k parameters.

**(b) Concrete design.** Inputs (all cheap, all computed from what the dispatcher already has, deliberately **no step
counter**): (1) did the last lookup return a row that had already been retrieved this episode (repeat flag);
(2) cosine similarity between the current carried value and the previous one (progress); (3) whether the target relation
has been found yet (an operator-side "answer present" score); (4) the dispatcher's own current action entropy.
A 2-layer MLP (4→32→2, **≈ 230 params**; ≈1–2k if you widen it) outputs `g` (a gain multiplier applied to the dispatcher
logits, i.e. inverse temperature `logits × exp(g)`) and `c` (an additive bias on the CONTINUE/next-lookup logit). Runs
at every dispatcher step at train and test. Learned: the MLP, by the same RLOO signal as the dispatcher, with
**homeostasis** borrowed from Pîslar et al. — a slow controller on the threshold/offset that holds the realised
"high-gain fraction" near a target (e.g. 20%) so `g` and `c` do not need hand tuning and cannot collapse to a constant.
Fixed: operator, target switch rate. Wiring: sits between dispatcher trunk and action head; operator untouched.

**(c) At LLM scale.** A small head reading rollout-progress features (repeat-n-gram rate, self-consistency across
partial samples, retrieval-hit flag) that outputs per-step sampling temperature and a continue-vs-finish logit bias —
i.e. IntroLLM with interpretable inputs instead of a raw hidden state.

**(d) Falsifiable toy test.** Same 4/5-hop extrapolation eval as Option A. Extra controls: (iii) a **constant-gain
ablation** — freeze `g` and `c` at their average learned values. If the constant-gain ablation matches the learned head,
the "stuck sensing" contributed nothing and you have merely found a better constant, which is the most likely outcome.
(iv) a **shuffled-input** control: feed the head its progress features from a random other episode. **Pass mark:** the
learned head beats *both* the constant-gain ablation and the shuffled-input control by ≥ 10 cells on 4-hop, 5 seeds.
**Artefact risk:** RLOO on a 2-output head on top of an already-noisy dispatcher is a variance nightmare; and reward
hacking — `c` can just run out the clock and get the answer by exhaustive search, so log operator-call counts and
require efficiency not to degrade on 1–2-hop.

**(e) Honest criticism of this sketch — read before building it.** The halting literature predicts this will **not**, on
its own, fix length extrapolation.
- PonderNet's extrapolation win came from the **halting formulation and its prior**, not from an entropy/gain knob. ACT,
  which does have a learned continue/stop signal but a badly-shaped cost, stayed at **chance** on the same test.
- Raising entropy on a policy that confidently stops at 3 makes stopping *random*, not *longer*. Only the `c` term
  (CONTINUE bias) actually lengthens chains, and a learned scalar bias trained on 1–3-hop data has no gradient telling
  it that 5 is ever right — the training distribution never rewards a 5th call.
- Kane et al. (2017) is a caution from the biology side too: turning up tonic gain in rats mostly added decision noise
  and *reduced* task engagement.
So Option B is a plausible **complement** to Option A (it can help the dispatcher escape repeat-loops within an episode)
but is a poor primary fix for "stops after 3." **Cost: medium.**

### Option C — Meta-controller over a population of dispatchers (Agent57/STAC-style)

**(a) Plain words.** Instead of one dispatcher with a dial, train a handful of dispatchers that differ only in how
persistent and how random they are, and put a simple gambling algorithm on top that keeps picking whichever one is
currently learning fastest. The switch is learned from outcomes rather than from a hand-built stuck signal.

**(b) Concrete design.** Train K = 4–6 dispatcher heads sharing a trunk (and the one frozen operator), each with a fixed
(entropy weight, CONTINUE bias, max-hops) triple spanning e.g. 2–6 hops. A sliding-window UCB bandit picks which head
generates each episode; reward = task accuracy on a held-out chain-length mix that **includes lengths longer than the
training mix**. Params: K extra action heads at ~2k each ≈ **8–12k**, bandit is non-parametric. Runs during training;
at test time use the head the bandit converged on (or keep the bandit live). Alternative: meta-gradient / STAC variant —
differentiate the held-out longer-chain loss w.r.t. the entropy weight. Wiring: operator frozen and shared; only
dispatcher heads multiply.

**(c) At LLM scale.** This is exactly what Agent57 and STAC already do, and what production RLVR stacks approximate with
difficulty-aware entropy coefficients (AER).

**(d) Falsifiable toy test.** Same eval. Control: single dispatcher trained with the *best* fixed triple found by an
equal-compute grid search (K× the runs). **Pass mark: the meta-controller matches or beats the best fixed setting while
using the same total operator calls.** If a single tuned setting wins, the meta-controller is pure overhead — which is
the honest expectation on a problem this small. **Artefact risk:** with only 64 eval cells, UCB will chase noise; and
using longer chains in the meta-objective is arguably leaking the test distribution into training, so that held-out mix
must be a separate split from the reported 4/5-hop eval.
**Cost: large** relative to the payoff, and it violates "one change at a time."

### Ranking

**A > B > C. Build A first.** It is the only one where a published experiment tests the exact failure we have
(train short, test long) and reports a clean win over the obvious alternative, it costs a few hundred parameters, and it
comes bundled with the training-distribution fix (randomised budget) that the 2026 looped-transformer work argues is the
true cause. Run A with control (ii) so we learn *which* of the two ingredients did the work. If A works and the
dispatcher still gets stuck in repeat-loops on longer chains, add B on top as a second, separate change. Skip C unless
both fail.

---

## 6. Priority score

**2 / 5** as a "missing brain mechanism to import" — the mechanism is well covered by SAC/Agent57/STAC/Pîslar/IntroLLM
and the neuromodulation framing likely misdiagnoses our bug. **But Option A specifically is a 4/5 as a bug fix**, because
it is cheap, pre-registered, and directly targeted at the "stops after 3 calls" failure. Do Option A; do not sell it as
neuromodulation.

---

## 7. References

Neuroscience
- Aston-Jones G. & Cohen J.D. (2005). An integrative theory of locus coeruleus-norepinephrine function: adaptive gain
  and optimal performance. *Annu. Rev. Neurosci.* 28:403–450. https://pubmed.ncbi.nlm.nih.gov/16022602/
- Yu A.J. & Dayan P. (2005). Uncertainty, neuromodulation, and attention. *Neuron* 46:681–692.
  https://www.gatsby.ucl.ac.uk/~dayan/papers/yud2005.pdf
- Gilzenrat M.S. et al. (2010). Pupil diameter tracks changes in control state predicted by the adaptive gain theory.
  *Cogn. Affect. Behav. Neurosci.* https://link.springer.com/article/10.3758/CABN.10.2.252
- Jepma M. & Nieuwenhuis S. (2011). Pupil diameter predicts changes in the exploration–exploitation trade-off.
  https://pubmed.ncbi.nlm.nih.gov/20666595/ (journal/volume not separately verified)
- Kane G.A. et al. (2017). Increased locus coeruleus tonic activity causes disengagement from a patch-foraging task.
  *Cogn. Affect. Behav. Neurosci.* https://pubmed.ncbi.nlm.nih.gov/28900892/
- Megemont M., McBurney-Lin J. & Yang H. (2022). Pupil diameter is not an accurate real-time readout of locus coeruleus
  activity. *eLife*. https://elifesciences.org/articles/70510
- Miyazaki K.W. et al. (2014). Optogenetic activation of dorsal raphe serotonin neurons enhances patience for future
  rewards. *Current Biology*. https://pubmed.ncbi.nlm.nih.gov/25155504/
- Miyazaki K.W. et al. (2018). Reward probability and timing uncertainty alter the effect of dorsal raphe serotonin
  neurons on patience. *Nat. Commun.* https://www.nature.com/articles/s41467-018-04496-y
- (2024). The differential effect of optogenetic serotonergic manipulation on sustained motor actions and waiting for
  future rewards in mice. *Front. Neurosci.* https://pmc.ncbi.nlm.nih.gov/articles/PMC11461476/ (authors not verified)
- (2025). Optogenetic locus coeruleus stimulation improves pupil size tracking of cortical state.
  https://pubmed.ncbi.nlm.nih.gov/40039165/ (authors/journal not verified)
- Wang J.X. et al. (2018). Prefrontal cortex as a meta-reinforcement learning system. *Nat. Neurosci.* 21:860–868.
  https://www.nature.com/articles/s41593-018-0147-8

AI
- Graves A. (2016). Adaptive Computation Time for Recurrent Neural Networks. https://arxiv.org/abs/1603.08983
- Haarnoja T. et al. (2018). Soft Actor-Critic Algorithms and Applications. https://arxiv.org/abs/1812.05905
- Xu Z., van Hasselt H. & Silver D. (2018). Meta-Gradient Reinforcement Learning. NeurIPS.
  https://arxiv.org/abs/1805.09801
- Miconi T., Rawal A., Clune J. & Stanley K.O. (2019). Backpropamine. ICLR 2019. https://arxiv.org/abs/2002.10585
- Badia A.P. et al. (2020). Agent57: Outperforming the Atari Human Benchmark. https://arxiv.org/abs/2003.13350
- Zahavy T. et al. (2020). A Self-Tuning Actor-Critic Algorithm. NeurIPS. https://arxiv.org/abs/2002.12928
- Banino A., Balaguer J. & Blundell C. (2021). PonderNet: Learning to Ponder. ICML AutoML workshop.
  https://arxiv.org/abs/2107.05407
- Pîslar M. et al. (2022). When should agents explore? ICLR 2022. https://arxiv.org/abs/2108.11811
- Veerabadran V. et al. (2023). Adaptive recurrent vision performs zero-shot computation scaling to unseen difficulty
  levels. NeurIPS 2023. https://arxiv.org/abs/2311.06964
- Lee S., Liebana S., Clopath C. & Dabney W. (2024). Lifelong Reinforcement Learning via Neuromodulation.
  https://arxiv.org/abs/2408.08446
- (2025/26). Revisiting Entropy Regularization: Adaptive Coefficient Unlocks Its Potential for LLM RL (AER).
  https://arxiv.org/abs/2510.10959 (listed as Findings of ACL 2026; not independently verified)
- Zhou Y., Li Y., Cheng D., Fan H. & Cheng Y. (2026). Look Inward to Explore Outward: Learning Temperature Policy from
  LLM Internal States via Hierarchical RL. https://arxiv.org/abs/2602.13035
- Kuo H.-Y., Chayti E.M., Reizinger P., Brendel W. & Jaggi M. (2026). Stabilizing Extrapolation in Looped Transformers.
  https://arxiv.org/abs/2606.29983
