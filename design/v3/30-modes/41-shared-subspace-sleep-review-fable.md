# 41 — Shared-Subspace Sleep: skeptical review (Fable coordinator, 2026-09-21)

Request: Ben's "Shared-Subspace Sleep" proposal (full text: scratchpad `sss_request.txt`).
Baseline preserved: Experiment 42 / 42b exactly as registered (`artifacts/fable-autosleep42-20260921/RESULTS.md`).
Nothing below claims a method works unless a measured table says so.

## 0. Short verdict

| Part of the proposal | Verdict | Why |
|---|---|---|
| 1. Recurrent core `z' = F(z, x)` | Architecture change, not a sleep change. Right idea for tasks whose number of steps grows with length (carries, multi-hop). NOT the cause of our current length wall. | Probe: even old skills that are a plain copy (+3 to each digit) fall to 0% at length 12. That is a position-addressing failure, not a depth failure. |
| 2. Independent groups | Valid and cheap. | It is just computing the batch gradient in m pieces. |
| 3. Top-k SVD of group gradients | Math as written is weak; needs two repairs (below). | SVD finds the LARGEST directions, not the most AGREED ones; and with m groups the mean already lies in their span. |
| 3b. Sign agreement | Valid, known (AND-mask). Known to be fragile. | It mostly throws gradient away; published follow-ups show small or no gain over plain training when groups are random splits of the same data. |
| 4. Low-rank reversible update | Safe and reversible, but NOT a sample-efficiency tool on our evidence. | Exp 42b: limiting sleep to 3,040 numbers changed nothing at 100 episodes and did not help at 20. |
| 5. Old-skill replay + gate | Keep. Already works (exp 42: old skills within 0.02). | Gradient projection (GEM/OGD/PCGrad) is only needed if replay is unavailable. |
| 6. Held-out picks the checkpoint | Keep, with one rule: the held-out episodes come from the awake log, never from the test sets, and longer lengths are never used for selection. | Otherwise it is training on the test. |
| 7. Surprise != consolidation | Agree, and exp 42 already supports it (surprise-ranked replay was slightly worse). | |

## 1. Math check of each claim

**Claim 2 ("memorisation differs between groups, a reusable skill recurs").** Half true.
The gradient that memorises episode j only appears in the group holding j — true. But
at the start of learning, the memorising solution and the general solution push the
weights in nearly the SAME direction (both reduce loss on every episode). They only
separate late, when training loss is near zero. So agreement filters act late, mostly
as a brake on fitting leftovers (noise, exceptions). Expect a noise benefit, not a
sample-efficiency benefit. This is the "coherent gradients" picture (Chatterjee 2020).

**Claim 3 (SVD finds the shared subspace).** Two problems.
1. *Rank.* G has m rows, so rank(G) <= m, and mean(g_i) already lies in the row space.
   Projecting onto the top k < m right-singular vectors can only REMOVE parts of the
   mean. It cannot add information. With m = 4..8 this is a 4..8-dimensional choice.
2. *Largest is not most shared.* The top singular direction maximises sum_i (g_i . v)^2.
   One group with a huge gradient (exactly what a noisy exception produces) wins the
   top direction by itself. So un-normalised SVD is attracted TO outliers — the
   opposite of the intent. Repair: normalise each g_i to unit length first, and check
   that the top left-singular vector is close to uniform (every group loads on it).
   When gradients do agree, the top direction ~ the mean direction and the projection
   is nearly a no-op. So the method only changes anything when groups disagree, where
   it behaves like a soft vote.
*No giant matrix is needed:* per weight tensor, stack the m flattened group gradients
(m x n), form the m x m Gram matrix K = Ĝ Ĝᵀ, eigendecompose (m = 4: trivial), and
map back: v = Ĝᵀ u / |Ĝᵀ u|. Cost O(m² n) per tensor — less than one backward pass.

**Claim 4 (low rank = information bottleneck that forces abstraction).** Unproven, and
our data says no at this scale: 3,040 free numbers (0.25% of the model) matched full
fine-tuning at 100 episodes (0.69–0.77 vs 0.42–0.76) and was no better at 20
(0.08–0.24 vs 0.01–0.10). Few numbers != the right numbers. Low rank is still useful
for a different reason: it is reversible and cheap to gate, and "LoRA learns less and
forgets less" (Biderman et al. 2024) matches our squeeze arms.

**Claim 6 (select on held-out).** Valid as long as the held-out set is a random part of
the awake log. It estimates same-length generalisation only; it cannot see length
generalisation, and must not be given longer examples.

**Claim 7.** Valid; consistent with exp 42 (P149 false: surprise replay did not help).

## 2. What the length wall really is (new probe, no claim)

Old skills, registered exp-42 bases, exact match, mean of six ops (seeds 4102/4103/4104):
length 8: 0.98 / 0.99 / 1.00 · length 9: 0.67 / 0.59 / 0.77 · length 10: 0.17 / 0.18 / 0.18 · length 12: 0.00 / 0.00 / 0.00.
Even `+3 to every digit` (a copy) dies at length 12. So no sleep rule could have passed
the exp-42 long-input mark on this model. The goal "train 1–3, work at 4–8" needs an
architecture that can address positions it has never seen. That is Experiment 43A.

## 3. Prior work and contrary evidence (from memory; verify before citing outside the project)

| Idea | Closest prior work | What it found | Bearing on us |
|---|---|---|---|
| Keep only gradient parts that agree | Parascandolo et al. 2020, "Learning explanations that are hard to vary" (AND-mask); Chatterjee 2020 "Coherent gradients"; Rame et al. 2022 Fishr | Helps when groups are truly different ENVIRONMENTS and against label noise; later tests (Shahtalebi et al. 2021 SAND-mask; DomainBed-style comparisons) show little or no gain over plain training in general | Our groups are random splits of one log, the weakest case. Expect a noise effect at most. |
| Gradients live in a low-rank subspace | Gur-Ari et al. 2018 "Gradient descent happens in a tiny subspace"; Zhao et al. 2024 GaLore | True, and useful for MEMORY saving. Not shown to improve generalisation. | Supports feasibility, not benefit. |
| Low-rank update as regulariser | Hu et al. 2021 LoRA; Biderman et al. 2024 "LoRA learns less and forgets less" | Less forgetting, also less learning | Matches our squeeze arms; does not promise fewer episodes. |
| Protect old skills by projecting gradients | Lopez-Paz & Ranzato 2017 GEM; Chaudhry et al. 2019 A-GEM; Farajtabar et al. 2020 OGD; Yu et al. 2020 PCGrad; Kirkpatrick et al. 2017 EWC | Work, but plain replay is usually as good or better when old data can be replayed | We can replay; keep replay + a gate. |
| Same block applied repeatedly | Dehghani et al. 2019 Universal Transformer; Fan et al. 2024 looped transformers for length generalisation; Yang et al. 2024 looped transformers as learners | Helps when the number of steps must grow with input size, and only with an adaptive step count | Right tool for carries / multi-hop; our own canonical-operator result (10 hops, 2/3 seeds) agrees. |
| Length generalisation is mostly a POSITION problem | Kazemnejad et al. 2023 (no positional encoding); Ruoss et al. 2023 randomised positional encodings; Zhou et al. 2024 "Transformers can achieve length generalization but not robustly"; McLeish et al. 2024 Abacus embeddings | Simple position changes move copy/reverse/addition from 0% to high accuracy at 2–5x length, but seed-fragile | Directly matches our probe. Tested in 43A. |
| Compression makes the general solution win | Power et al. 2022 grokking; Nanda et al. 2023; Liu et al. 2023 "Omnigrok" | Needs very long training and enough data fraction; below a data threshold it never happens | Matches exp 42: 4x longer squeezed sleep did not rescue 20 episodes. |
| Sleep replay | McClelland et al. 1995 complementary learning systems; Kumaran et al. 2016 | Interleaved replay is the mechanism that protects old knowledge | This is exp 42's recipe. |

Contrary evidence to the whole proposal: nothing above shows a gradient FILTER reducing
the number of examples needed. Filters remove information; sample efficiency comes from
the prior (architecture, pretraining, data augmentation). CardFold's software lesson
worked because it manufactured 380 extra correct examples.

## 4. Hidden failure modes and confounds

1. Filtered arms take smaller effective steps. A "win" can be a learning-rate effect. Control: report gradient energy kept; if an arm wins, rerun plain with the matched step size.
2. Un-normalised SVD chases outliers (section 1). Fixed by unit-normalising group gradients.
3. Adam rescales whatever survives the filter, so tiny agreed coordinates get full-size steps. Known AND-mask issue.
4. With 6 rows per group, sign agreement across 4 groups is strict; most energy is dropped early. Could slow learning enough to look like "less noise memorised" simply because less of everything was learned. H2 therefore also requires fresh accuracy not to drop.
5. Held-out selection with 20 episodes is noisy (2 of them are wrong on purpose). Same for every arm, so fair, but weak.
6. "Rank-4 after every update" is hard truncation, not a learned adapter; it is merged by construction, which is what the requirement needs, but it is not identical to LoRA training dynamics.
7. Length: any gain on 9–10 must be credited to the 43A position change unless a filter beats plain on the same base.
8. One toy, three seeds. No claim beyond the toy.

## 5. Architecture changes vs sleep-algorithm changes

| Architecture (decide with base-training experiments, no sleep involved) | Sleep algorithm (decide with 43B-style experiments) |
|---|---|
| position scheme (43A) | how group gradients are combined |
| shared looped block, adaptive number of loops | update shape: full / low-rank / sparse |
| halting / "repeat until done" signal | replay mix, held-out checkpoint choice, acceptance gate |
| task with growing step count (carry chain) to test recurrence honestly | how many raw episodes are needed |

Rule: never test both columns in one experiment.

## 6. Sleep-vNext — one exact algorithm

The combine step is a slot. It is `mean` unless Experiment 43B passes a filter into it
(decision rule sealed in `artifacts/fable-sharedsleep43b-20260921/PASSMARKS.md`).

```
INPUT   theta0            base weights (toy: 1.2M numbers, 4 blocks, d=160)
        LOG               raw awake episodes of the new skill (input -> answer), N >= 100
        OLD               generator of old-skill practice (replay)
CONST   m=4 groups, 6 rows per group, 24 old rows, U=3000 updates, lr 1e-3, AdamW wd 0.01,
        clip 1.0, check every 250 updates, forget limit 0.02, held-out share 20%

1  split LOG at random: TRAIN (80%), HELD (20%).  HELD never trains.      # automatic, no model choice
2  before = old_skill_accuracy(theta0)
3  theta = theta0 ; best = None
4  for u in 1..U:
5      for k in 1..m:  g_k = grad( loss(theta, 6 rows sampled from TRAIN) )   # each g_k: same shapes as theta
6      g_old = grad( loss(theta, 24 rows from OLD) )
7      for every weight tensor T (largest: 640x160):
8          g_new[T] = COMBINE( g_1[T], ..., g_m[T] )                      # mean | sign | snr | subspace
9      theta = AdamW_step( theta, 0.5*g_new + 0.5*g_old )
10     every 250 updates: h = loss(theta, HELD); if h < best.h: best = (theta, h)
11 cand = best.theta
12 ACCEPT  if old_skill_accuracy(cand) >= before - 0.02
           and heldout_accuracy(cand) > heldout_accuracy(theta0)
13 if ACCEPT: base <- cand ; delete LOG cards ; test with notebook/cards disconnected
   else:      keep theta0 ; keep the cards ; try again after more experience
```

COMBINE options (per tensor, stack S of shape [m, *T.shape]):
- mean: S.mean(0)
- sign: mean * [all m signs equal]
- snr: mean * mean² / (mean² + var/m)
- subspace: S_hat = rows of S scaled to length 1 (m x n); K = S_hat S_hatᵀ (4x4); u = top eigenvector;
  v = S_hatᵀu/|S_hatᵀu|; output (mean·v) v.

Cost on the toy: memory = m+1 gradient copies = 5 x 1.2M x 4 bytes = 24 MB; compute = 5 small
backward passes per update = the same examples as plain replay, about 2.5x wall time (measured
0.08 s/update vs 0.03 on one Mac core). Scaling: gradient copies grow as (m+1) x model size, so
for a 50M model m=4 costs 1 GB — fine on the 16 GB card. Low-rank variant (if ever needed):
after line 9, for each block matrix W: W <- W0 + top-4 SVD of (W - W0); it is merged by construction.

Reversion: theta0 is kept until line 12 passes; rejecting costs nothing.
The final requirement (naked base weights hold the skill) is what line 13 tests.

## 7. Smallest decisive experiment = 43A then 43B

- 43A (architecture gate): can old skills work at lengths 10/12 after ONE position change? Marks G0–G4 sealed.
- 43B (sleep): five arms, identical data, 100 episodes with 10 wrong, 20 held out. Marks V0, H1–H4 sealed.
- Why lengths 4–8 -> 9–12 instead of 1–3 -> 4–8: reuses the registered toy and bases so exp 42 stays the baseline. A 1–3 -> 4–8 carry task is the follow-up once a position scheme passes.

## 8. Measured outcome (2026-09-21)

- 43A (randomised positions, looped block): all marks FAIL. Length 10 rose 0.18 -> 0.40-0.52; length 12 <= 0.03.
- 43C (segment-relative positions): all marks FAIL; length 12 = 0.00; the model ignored the shared position numbers.
- 43B (sign / snr / subspace / rank-4 vs plain): all marks FAIL. No filter joins Sleep-vNext. Caveats: held-out LOSS picked update 250 in all 15 runs; H2 had a floor problem; randpos base is less sample-efficient than the registered base.
- 43D (relative-position attention, no absolute positions): marks D1–D4 all FAIL, but first non-zero length-12 results. rel-both, seeds 4102/4103/4104 at length 12: INC3 0.91/0.90/0.82, REV 0.93/0.37/0.95, REV+INC1 0.94/0.44/0.99; SWAP and FOLD 0. REV is 0.00 without the end-index signal. Teacher-forced probe at length 16: only the last two answer places break. Seed-fragile; toy only; not a sleep result. Sealed rule followed: position work paused until the outside review.
- So Sleep-vNext today = section 6 with COMBINE = mean. Two repairs to test next, one at a time: select by held-out exact match (not loss) with a minimum of 1,000 updates; then rank-4 vs plain on the registered base with no noise, because rank-4 was the only arm never below plain.
- Open walls unchanged: episodes needed, and length. A self-contained outside-review prompt covering both was given to Ben for GPT.
Results files: `artifacts/fable-lengthgate43-20260921/RESULTS.md`, `artifacts/fable-sharedsleep43b-20260921/RESULTS.md`.
