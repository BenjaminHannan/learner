# Fable 5.1 and Opus 5.5 on why GW-PC did not help (batch API, 10-12 night; prompt: reviews/gpt-diagnose-gwpc-2026-10-12.md)

Premises were checked against the code in game/A21-GWP8-BLIND.md; two rest on false premises. Verbatim answers follow.

## Fable 5.1
## 1. Labels

**Your item 1**
- Untrained T0 policy scores 3.75 / 3.61; random 2.31; map-blind habit 3.78 / 3.67 — **shown**.
- "The untrained model is not reading the map" — **suggested**. A map-blind policy *scoring* the same is not the same as the model's action distribution *being* map-independent. Shown only if you measure it (e.g. score the same policy with the map blanked, or check per-state action distributions).
- Two-letter-word bias from un-normalised summed letter log-probs — **suggested**, as you say. Note it is currently *helping*: "do" at 55% is most of the gap between 2.31 and 3.75. Length-normalising would likely lower the starting score.

**Item 2**
- GW-P8 4.15 / 4.19, approx KL 0.004–0.011/night, clip 3–11% — **shown**.
- "+0.40 / +0.58" — **shown as a difference of two noisy numbers** (no CI given; 100 maps gives roughly ±0.15–0.2 per arm).

**Item 3**
- "Dividing by T ~ 20 makes every policy step ~20x smaller" — **suggested**. It is true for a fixed Adam parameter step *when the clip is not binding*; the clip caps ratio changes independently of T. GW-PC is consistent with that: steps got bigger (2.2–2.5x), not 20x, because the clip took over (17–26%).

**Item 4**
- Distilled copy is a fair copy (night-0 scores match; held-out KL 0.04–0.05) — **shown**.
- KL 2.2x/2.5x, clip 17–26%, T 1.00 → 1.048 — **shown**.
- Practice quiz did not rise — **shown but weak** (32 worlds; units unclear — if it is a union-count of distinct achievements, a 17 → 16 change is one achievement not appearing, i.e. noise).
- GW-PC below GW-P8 at night 6 — **shown** (paired, both seeds, CIs exclude 0, though the lower bounds are near −0.2 on only 50 maps).
- GW-PC below *its own* night 0 (3.79 → 3.54, 3.69 → 3.56) — **suggested**; 50-map vs 100-map, within noise.

**Explanation A** — **untested**. Its clean test (same GW-P8 recipe, bigger lr or wider clip) was not run; its prediction "more movement helps" is contradicted by GW-PC, but GW-PC is confounded (see §2).

**Explanation B** — split it:
- B1 "credit spread across ~170 steps makes the gradient noisy" — design fact is **shown**; that it is the limit is **suggested** (it fits the pattern, see §2).
- B2 "T=1 removes a free exploration bonus" — **not shown**. At night 0 the distilled policy has the *same* entropy as T0. B2 only holds if the policy sharpened during training, and you did not report entropy. The one hint you have (learned T drifting *up* to 1.048) points toward the optimiser wanting a flatter policy, not toward a policy that got dangerously sharp.

## 2. Which explanation the numbers favour

Against A as stated, toward B1, with a third explanation C worth checking.

Evidence:
- **More movement, no gain.** GW-PC moved 2.2–2.5x more per night and clipped 2–5x more, and its training-set metric fell and its sealed score fell relative to GW-P8. If step size were the cap and the direction were good, the movement that got through the clip should have helped proportionally. It didn't, so the *direction* was poor (B1: noisy credit) or the movement was in a harmful subspace (C).
- **Tiny steps worked.** GW-P8 gained +0.5 with cumulative drift of order 0.05 nats — the same order as the distillation error, which changed the score by nothing. So there is a narrow, reward-relevant direction, and the heavily damped T=20 run found it. That is what you expect when the gradient is noisy and a small step acts as an implicit trust region that averages noise across nights.
- **T drifted up at T=1.** Weak, but the sign says the objective preferred flattening.

**C (third explanation): drift back toward the base model's habits.** The distilled LoRA is doing a specific job — nearly cancelling the base model's sharp raw logits so the sum looks like z_base/20. Any noisy gradient step that fails to preserve that cancellation leaks the base's raw preferences (letter statistics, not map), so the marginals can drift away from the "do"-heavy habit that supplies most of the score. Untested; checkable from your logs by plotting per-night action marginals and policy entropy for GW-PC vs GW-P8. If "do" fell from ~55% to ~40%, that alone explains −0.5.

**D (worth 30 minutes, no training): a map-blind ceiling.** If GW-P8's night-8 policy scores the same with the map replaced by blanks, the +0.5 was marginal-frequency tuning, and neither step size nor exploration is the question — the model is not connecting map tokens to actions with this signal. Run this before anything else.

Fairness to A: the clip-fraction rise is exactly what A predicts, and A's clean counter-test (GW-P8 recipe with lr ×10) was never run. A is disfavoured, not dead.

## 3. The one change

**Keep GW-P8 exactly (T ≈ 20, zero-init LoRA, no distillation, same lr/clip/epochs/64 games) and change only the credit: discounted reward-to-go with γ = 0.95 (≈20-step horizon), baseline = batch-mean return-to-go at that timestep, advantages standardised per batch.**

Assumption: your advantage is currently the episode's unlock count (minus a mean) broadcast to all ~170 steps. If you already discount with γ ≥ 0.99, the change is γ → 0.95; nothing else.

Why this one: it is free in compute, it targets the hypothesis the numbers favour, and it keeps T=20's implicit trust region (which is the one thing shown to work). Under A it should do nothing — so its result also informs A.

Pass marks, fixed now:
- Metric: mean distinct unlocks per game, night 8, the same 100 sealed maps, paired by seed against the GW-P8 recipe on that seed.
- **Screen:** seeds 200 and 201 (GW-P8 controls exist). Proceed only if both show ≥ +0.20 over GW-P8 (i.e. ≥ 4.35 and ≥ 4.39).
- **Confirm:** ≥ 6 paired seeds (200–205; run 4 new GW-P8 controls). Pass if the mean paired difference ≥ +0.30, the 95% CI over seed-differences excludes 0, and ≥ 5 of 6 seeds are positive. Secondary: the practice metric must also rise; sealed-up/practice-flat is treated as noise.
- **Proven wrong:** 6-seed mean paired difference ≤ +0.10, or CI including 0. That kills B1 as the bottleneck. Then run the clean A test (GW-P8 with lr ×10) to kill or revive A; if that fails too and the blanked-map check shows map-blindness, you are at D.

## 4. What I would not trust

- **50-map sealed scores.** Per-arm SE ≈ 0.2; your paired CIs reach to −0.2 and −0.1. Real, but the size is loose.
- **Two seeds.** GW-P8's +0.40 vs +0.58 shows ~±0.1 seed spread on top of map noise. Two seeds screen; they don't confirm.
- **Practice quiz.** 32 worlds, unknown units; if it is a union of distinct achievements, it is a coverage statistic, nearly blind to mean performance.
- **The GW-PC comparison is confounded.** Three things changed: effective step size, the LoRA's job (cancelling the base), and what the learned T can do. It does not isolate A.
- **"T stayed ~20" in GW-P8.** With Adam-sized steps, T at 20 is effectively frozen; "learned T" means different things in the two runs.
- **Approx KL and clip fraction.** Computed on training-batch states after clipping; per-night numbers are not additive, and the clip fraction is dominated by low-probability actions whose ratios swing on tiny logit changes. Fine for relative comparison only if computed identically.
- **"Not reading the map".** Inferred from a score match; measure it.

Free logging to add so A/B/C/D become separable: per-night action marginals, entropy on a fixed state set, held-out KL to the night-0 policy, blanked-map score.

## 5. Plain-language summary

A tiny language model plays a Minecraft-like game by reading a text map and picking one of 17 moves. Before any training it already beats random play — not because it reads the map, but because it happens to say "do" (interact) more than half the time, which lucks into collecting wood, drinking water, and so on. Training it gently for eight nights improved it a bit more.

We suspected the gentle training was too gentle — the model's "volume knob" was turned down 20x, so each lesson barely moved it. We rewired it so lessons hit at full volume. It then moved more per night, but got worse, not better. That is a clue: if the lessons had been pointing the right way, moving further along them should have helped. So the problem looks less like "lessons too small" and more like "lessons too noisy": rewards are rare and come at the end of long games, so the model can't tell which of its ~170 moves earned them. The gentle version worked *because* small steps smooth out noise.

Next: keep the gentle setup, but give credit only to moves made shortly before each reward instead of smearing it over the whole game. Decide ahead of time what counts as success (about +0.3 unlocks per game across six matched seeds). If that does nothing, the "noisy lessons" story is wrong and we test the "too gentle" story cleanly. And first, spend half an hour checking whether the trained model is actually reading the map at all — if it scores the same with the map hidden, none of these knobs is the real problem.
## Opus 5.5
# Diagnosis of the GW-P8 vs GW-PC results

**Short answer.** The numbers lean against A. In GW-PC the policy moved more each night and still did not improve, ending well behind GW-P8. That suggests step size was not what held learning back. The numbers cannot pick B over a third explanation (C: the distilled T = 1 setup itself is the problem), because GW-PC changed two things at once. The one change I'd make is the run that separates them: rerun GW-P8 with only the learning rate raised, so its per-night KL matches GW-PC's.

---

## 1. Claim labels

| # | Claim | Label | Note |
|---|---|---|---|
| 1 | Untrained 3.75 / 3.61; random 2.31; habit 3.78 / 3.67 | Shown | |
| 2 | T0 ≈ 20 gives entropy ln17/2 | Shown | True by construction |
| 3 | The untrained model is not reading the map | **Suggested** | What is shown is weaker: whatever it reads buys no score over a map-blind habit (gap −0.03 / −0.06, well inside ±0.3 noise). A map-shuffle test would show it directly. |
| 4 | Summed letter log-probs favour "do" / "up" | Untested | |
| 5 | GW-P8: 4.15 / 4.19, +0.40 / +0.58 | Shown | Two seeds. Each gain is about 1.5–2x the single-seed map noise (see §4). |
| 6 | GW-P8 KL 0.004–0.011, clip 3–11%, T stayed ~20 | Shown | "~20" could hide a drift as large in absolute terms as GW-PC's +0.048 |
| 7 | GW-P8's gain comes from reading the map | **Untested** | Implied, never checked (see §4) |
| 8 | Dividing by T ≈ 20 makes each policy step ~20x smaller | Suggested; **contradicted in its strong form** | Removing T raised KL only 2.2–2.5x. Since KL grows roughly with the square of the move, that is about 1.5x bigger moves. A true 20x would be roughly 400x the KL. |
| 9 | Distilled copy: held-out KL 0.04–0.05 | Shown | |
| 10 | The night-0 copy is fair | Shown, loosely | The score match (+0.04 / +0.08) is within noise that cannot resolve gaps under ~0.3. The KL is the better evidence. |
| 11 | GW-PC KL 2.2x / 2.5x, clip 17–26%, T 1.00 → 1.048 | Shown | |
| 12 | The quiz did not rise | Shown | "The quiz fell" is not shown (only 32 worlds) |
| 13 | GW-PC below GW-P8 at night 6 by 0.46–0.60 | Shown for these 2 seeds on these 50 maps | The CIs cover map noise only, not run-to-run training noise |
| 14 | GW-PC got worse than its own start | **Not shown** | −0.25 / −0.13 on different map counts (50 vs 100). Shown only that it did not gain. |
| 15 | A's mechanism: the clip capped GW-PC's step | Suggested at most | 74–83% of ratios were unclipped, and the clip rate is about what the KL rise alone predicts |
| 16 | A's remedy: fixing clip / LR / batch would help | Untested | GW-PC is confounded evidence *against* "more step helps" |
| 17 | Rewards are rare | Shown | ~3.75 unlocks per ~170 steps ≈ 2% of steps |
| 18 | Credit runs across ~170 steps | Untested | Depends on your discount, GAE λ and value baseline, which aren't stated |
| 19 | T ≈ 20's flat odds were an exploration bonus that T = 1 removes | Untested, **partly contradicted** | At night 0 both policies are the same distribution with the same entropy. T = 1 can only let entropy fall *faster* during learning, and entropy was never logged. |
| 20 | Night length; rows per night | Shown | |

---

## 2. A, B, or a third explanation

**The numbers favour "the direction of the step is the problem, not its size."** That is the first half of B. They do not rule out a third explanation, C.

### Evidence against A

- **The bigger step got through and didn't help** (shown). GW-PC's policy moved 2.2–2.5x more per night. By night 6 it had none of GW-P8's ~+0.4 gain, and the quiz was flat. A predicts that bigger moves in the learned direction mean faster progress. That did not happen.
- **In the run that worked, the clip wasn't the limit** (shown). GW-P8 clipped only 3–11% of ratios, so whatever capped GW-P8 was the learning rate, not the clip.
- **GW-PC's clip behaved normally** (suggested). Assume log-ratios are roughly bell-shaped and ε = 0.2. Then GW-P8's KL range predicts about 3–16% clipped, and GW-PC's about 10–40%. You saw 3–11% and 17–26%. Nothing suggests the clip was eating a much larger "natural" step.
- **The "20x" premise didn't hold.** The KL rise of 2.2–2.5x (not ~400x) is shown; the reasons are suggested:
  - If you use Adam, dividing the loss by T barely changes the parameter step, because Adam rescales gradients.
  - A flat policy written into the add-on's weights seems to respond to weight changes about as sluggishly as one made by dividing by T.
  - So GW-PC delivered ~1.5x bigger moves, not 20x, and even those didn't help.

### What the numbers say about B

- **B1, noisy direction** (suggested). "Bigger moves, no gain" is what you expect when the per-night gradient from 64 games mostly points at noise.
- **B2, exploration** (suggested). There is one weak hint, from how T drifted:
  - The PPO gradient on T is proportional to advantage × (E_π[logit] − logit(chosen move)).
  - So T rises when rewarded moves tend to be ones the policy currently *disfavours*.
  - Unless your loss has an entropy bonus, GW-PC's steady 1.00 → 1.048 says rare moves were paying off. Plausibly these are the long words (place table, make pickaxe) that carry the valuable unlocks.
  - Check GW-P8's exact T log. Adam moves T by about the same absolute amount at T = 20, so a +0.05 drift there would read as "stayed ~20".

### Third explanation, C: the distilled setup, not the step size

The add-on's first job was to flatten a very sharp model by about 20x. RL updates then perturb that flattening correction, as well as moving the odds where the advantage points. So learning on top of the copy is a different problem from learning at T = 20.

A concrete version you can check in five minutes (untested):
- If your optimiser is AdamW with weight decay (PyTorch's default is 0.01), decay pulls the add-on toward zero.
- Toward zero means back toward the base model's sharp T = 1 odds, eroding the copy every night.
- In GW-P8 the add-on starts at zero, so decay costs nothing there.

### Why you can't separate them yet

GW-PC filled only one cell of a 2x2:

| | Small steps | Big steps |
|---|---|---|
| **T = 20, add-on from zero** | GW-P8: improves | **missing** |
| **Distilled copy, T = 1** | missing | GW-PC: doesn't improve |

---

## 3. The one change

**Rerun GW-P8 exactly, changing only the learning rate, raised so that per-night approx KL is 2–3x GW-P8's (GW-PC's range).**

### Why this change

- It tests A directly, in the setup that already works.
- It fills the missing cell, so it breaks GW-PC's confound.
- It costs nothing in night length.
- If A is right, it is an immediate improvement.

### Setup

1. **Choose the multiplier before seeing any scores.** From the GW-P8 start, run one pilot night at LR ×1.5 (KL ∝ step², so ×1.5 should give roughly 2.25x KL). If the KL ratio falls outside 2–3x, try ×2.5. Use KL only, with no quiz or sealed scores. Lock the multiplier.
2. **Change nothing else.** Same seeds and games, same clip ε, epochs and batch, learned T, 8 nights.
3. **Log each night:** approx KL, clip fraction, T, and mean policy entropy on visited states. Before starting, compute entropy from GW-P8's and GW-PC's saved checkpoints. It takes minutes and may already show whether GW-PC lost exploration.
4. **Evaluate twice:** night 6 on the same 50 maps used for GW-PC, and night 8 on all 100 sealed maps.

### Pass marks (fixed now)

- **Manipulation check.** The run counts only if its mean per-night KL over nights 1–8 is 2.0–3.0x GW-P8's same-seed mean. Otherwise the run is void either way.
- **Primary metric.** Night-8 mean unlocks on the 100 sealed maps, minus GW-P8's, paired by seed (same training-game and evaluation seeds) and by map.
- **Screen (seeds 200, 201).** GW-P8 already exists for these. Proceed only if the mean paired gain is ≥ +0.15 and neither seed is below −0.10. Otherwise stop working on optimiser knobs; that is a decision, not proof.
- **Confirmation (seeds 200–205).** GW-P8 must also be run on seeds 202–205. The change passes if:
  - the mean paired gain is ≥ +0.25,
  - at least 5 of 6 seeds are positive, and
  - the 95% t-interval over the 6 seed differences excludes 0.

### What proves it wrong

Over 6 paired seeds, if **the upper end of the 95% interval is below +0.25**, bigger steps do not buy a worthwhile gain, and A is refuted as the main limit. If the whole interval sits below 0, bigger steps actively hurt even at T = 20. Anything in between is inconclusive; don't add seeds to chase it.

### Reading each outcome

| Result | Meaning |
|---|---|
| Passes | A: step size limits learning. GW-PC failed because of the distilled setup (C). |
| ≈ 0, no harm | Step size isn't the limit. GW-PC's damage came from the distilled setup (C). |
| Harm like GW-PC (night 6 ≈ 3.5–3.6) | Bigger steps hurt regardless of setup, which points to B. Entropy falling faster than GW-P8's points to exploration loss (B2); steady entropy points to a noisy direction (B1). |

### Cost

Each 8-night run takes about 8.7 hours.
- Screen: 2 runs plus pilots, about 19 hours.
- Confirmation: 4 more runs of each arm, about 70 hours.

Save a checkpoint every night; the Mac has already died once.

---

## 4. What I wouldn't trust

- **Two training seeds.** The night-6 CIs reflect map noise only. They say nothing about how much another training run would differ.
- **Map noise is large.** Back-calculating from your CI, the per-map paired SD is about 1.4 unlocks. So one seed on 100 maps resolves only about ±0.28, and 50 maps about ±0.4. The same untrained policy gave 3.75 vs 3.61 from sampling alone. Three of your comparisons sit inside that noise:
  - untrained vs habit,
  - the night-0 copy vs untrained,
  - GW-PC night 6 vs its own night 0.
- **GW-P8's gain may be a better habit, not map reading.** It is measured against the untrained model, not the best map-blind habit, and a per-night KL of 0.004–0.011 is consistent with simply reshuffling move frequencies. Check: play GW-P8's overall move frequencies as a fixed habit on the sealed maps (evaluation only, about an hour). If that scores about 4.1, nothing has learned to read the map yet.
- **The quiz.** With 32 worlds and unknown units and noise, it may not see effects this size. Did GW-P8's quiz rise? If not, don't use the quiz for decisions.
- **Mixed map sets.** Night 6 used 50 maps; the finals used 100. Compare like with like.
- **The KL targets.** The "wanted 3x" target doesn't match the 20x premise. Also unclear: which approx-KL estimator you use, and when it is measured (before or after the epochs). Small KLs estimated on your own rollouts are noisy.
- **Sealed maps are being reused.** They have been scored for the untrained model, the habit, night 0, night 6 and the finals. Run screens on a separate 100-map set and keep the sealed maps for 6-seed confirmations.
- **Unstated loss details change the interpretation:** entropy bonus, weight decay, value baseline, GAE λ, advantage normalisation.

---

## 5. Plain-language summary

We have a tiny AI that plays a simple Minecraft-like game by reading a text map and typing a move. Out of the box, it plays about as well as someone who ignores the screen and mashes "do" and "up."

We let it practise. Each "night" it plays 64 games and nudges itself toward moves that came before good things.

- **The first version** made very gentle nudges and got somewhat better: about 3.7 → 4.2 achievements per game.
- **The second version** removed a setting we thought was watering down every nudge. It did make bigger changes each night, but it stopped improving. After six nights it was clearly behind the gentle version.

What I think is going on: bigger nudges only help if you're nudging in the right direction. The AI gets a reward only a few times in a 170-move game. That's like trying to work out which of your 170 decisions won a match when you're only told the final score. With that much guesswork, bigger nudges mostly mean bigger random wobbles. But the second version also changed how the AI was set up, so we can't yet be sure that nudge size was the real problem.

What to try: rerun the gentle version and turn just one dial, the step size, so its nudges are as big as the second version's.
- If it improves, step size was the bottleneck.
- If it does the same or worse, the problem is the quality of the feedback, and that's what to fix next.

We've written down in advance what counts as a win: at least +0.25 achievements per game, consistent across 6 repeat runs. That way we can't fool ourselves afterward.