# Should a small reasoning model be a team of small models? (no code or file access needed)

You are an expert in ensembles, mixture-of-experts, multi-agent learning and compositional generalisation in small neural
networks. You have **no access** to my code, files or machines, so everything you need is pasted below. Do not ask me to
run anything before you answer; reason from what is here. If a fact you need is missing, say exactly what it is and how it
would change your answer. Mark every claim as **shown by the data below**, **suggested**, or **untested**. Two seeds is a
screen; my own rule is that a claim needs 6 or more paired seeds.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow.

## 1. My goal and the idea

Goal: a model built around a small reasoner that does the thinking and beats similar-size models when you count the whole
model's size, ideally with nothing pretrained.

The idea I want judged: "What if we have like 32 different models that act as a swarm, and then we train them to work
together to solve problems? They all start on the same base (they can think, adapt and develop skills), but then we train
them so that they learn skills in different ways."

Keep the two experiments below separate. They use the same question generator but different models, and their numbers
are not comparable with each other.

## 2. The questions (both experiments)

A synthetic "skills" curriculum: 200,000 generated training questions across about 33 kinds ("families"), such as
multi-step arithmetic stories (`chain_ops`, `chain_story2`, `var_chain`), tracking a value through updates
(`state_update`), letter ciphers (`cipher_map`), inferring a number rule from a few examples (`fewshot_number_rule`),
grouping (`group_induct`), repeating cycles (`seq_cycle`), copying, comparing and so on. Answers are short (at most 8
characters) and scored by exact match. Held-out test splits, 40 questions per family per split:

- `in_dist`: new questions of practised kinds.
- `answer`: answers never seen in training. `frame`: unseen wordings. `vocab`: unseen words.
- `variant`: **twisted versions of practised kinds** (for example a few-shot rule of a type never practised). This is the
  split that matters most to me, because it is the closest thing here to "a new problem".
- `family`: kinds never practised at all (near zero for every model so far; ignore it).

## 3. Experiment A: the real model (frozen 1.2B language model + small thinker + calculator)

A frozen pretrained 1.2B language model reads the question. A small looped "thinker" (about 9M parameters, 256 wide,
4 rounds; its feed-forward layers are an 8-expert top-2 mixture-of-experts with one router reused on every round) writes a
plan: which numbers in the question to use and which operations to apply. An exact calculator executes the plan, and the
language model writes the answer. Trained on 8 practised families (2,000 rows x 3 passes, plus 17,000 plan rows). When
the plan is swapped for another question's plan, chain answers drop to 2-3 of 160 on every seed, so the thinker really
decides those answers.

**What I measured (no new training): 6 seeds of this exact recipe, voting on each question.**

| split | one model (mean of 6) | best of 6 | 6-model majority vote | right for at least one seed | all 6 wrong |
|---|---|---|---|---|---|
| in_dist (n=320) | 89.7 | 92.8 | 93.9 | 98.8 | 4 |
| answer (n=280) | 88.6 | 92.5 | 94.5 | 98.6 | 4 |
| frame (n=320) | 85.5 | 88.8 | 93.4 | 99.4 | 2 |
| vocab (n=120) | 97.6 | 99.2 | 100.0 | 100.0 | 0 |
| variant (n=280) | 49.2 | 52.9 | 53.7 | 66.1 | 95 |

On `variant`, when one seed is wrong, another seed is wrong on the same question 85% of the time (pairwise "both wrong"
divided by the geometric mean of the two error counts). On the other splits that figure is 20-48%. The 95 questions all six
miss are concentrated: few-shot number rules 39 of 40, sequence cycles 26 of 40, var_chain 19 of 40, grouping 10 of 40,
the chain-arithmetic kinds 0-1 of 40.

## 4. Experiment B: small models trained from scratch (no pretraining at all)

Every model is about 3.3M parameters, trained 24,000 updates at batch 256 on the same 200,000 rows with the same
optimizer (AdamW, lr 1e-3, warmup, cosine), seeds 100 and 101. The recipes ("ways of learning"):

- **B2:** a character reader, then a looped core that writes a short program over the numbers it found in the question
  (operation + which two numbers, step by step); an exact executor runs it; a pointer-generator "talker" writes the
  answer and can copy from the question.
- **B:** the same without the copy path.
- **A0:** a looped register model that answers directly.
- **plain_tf:** a 4-layer causal transformer that answers directly. **tfp:** the same plus place-value codes for digits.
- **l2x2:** a 2-layer, 2-loop variant.
- **plain_tf_steps:** a transformer that writes worked steps, then the answer, and **A:** a register loop that writes
  steps (both still being re-scored when I wrote this; not in the tables).
- For size reference: a 10.8M plain transformer (seed 0, lr 7e-4, otherwise similar): in_dist 76.0, variant 21.7.

| model | in_dist s100 / s101 | variant s100 / s101 |
|---|---|---|
| B2 | 89.0 / 90.1 | 32.3 / 34.6 |
| B | 84.3 / 86.3 | 30.6 / 32.8 |
| A0 | 82.8 / 80.0 | 20.8 / 22.0 |
| tfp | 76.8 / 76.8 | 23.3 / 22.4 |
| plain_tf | 73.8 / n/a | 21.2 / n/a |
| l2x2 | 71.0 / 70.1 | 17.0 / 17.8 |

**Do different recipes make different mistakes?** (pairs of models; "overlap" = both wrong / geometric mean of the two
error counts; "B2's mistakes shared" = of the better model's mistakes, the share the other model also makes)

| split | pairs | overlap | better model's mistakes shared | phi of the error indicators |
|---|---|---|---|---|
| variant | same recipe, 2 seeds (5 pairs) | 91.7 | 92.6 | 0.67 |
| variant | different recipes, same seed (25 pairs) | 88.0 | 92.8 | 0.54 |
| variant | B2 vs another recipe (9 pairs) | 86.5 | 92.8 | 0.54 |
| in_dist | same recipe (5 pairs) | 71.3 | 74.3 | 0.65 |
| in_dist | different recipes (25 pairs) | 52.0 | 65.4 | 0.41 |

Teams of models trained apart (variant split):

| team | best member | majority vote | right for at least one |
|---|---|---|---|
| all recipes, seed 100 (6 models) | 32.3 | 31.6 | 46.4 |
| all recipes, seed 101 (5 models) | 34.6 | 33.7 | 48.9 |
| B2 + B, seed 101 | 34.6 | n/a | 41.8 |
| B2 + A0, seed 101 | 34.6 | n/a | 39.5 |
| B2 seed 100 + B2 seed 101 | 34.6 | n/a | 40.6 |

My reading (check it): on the twisted questions, a weaker recipe adds little that a second copy of B2 doesn't, and a plain
vote is pulled down by the weaker members. The union of all recipes is large (46-49% vs 32-35% for the best), so there is
something there for a team that knows whom to trust.

## 5. The "trained together" test now running (Experiment B only, Ben's own GPU)

Three members, one of each: B2, plain_tf_steps, plain_tf (about 10.2M in total with the coach). Each member starts from
exactly the same initial weights as its solo run at the same seed. A coach (a 0.44M character encoder, output layer
initialised to zero so it starts uniform) reads each question and scores the members. Every step draws a pool of 512
training rows; each member trains on 256 of them with its own loss and optimizer.

- **ON (test):** the coach decides who practises what: member i's rows are drawn with probability
  0.5 / 512 + 0.5 x coach_i(row) / sum over the pool of coach_i.
- **OFF (control):** each member's rows are drawn uniformly (independent training).
- Both: every 8 steps, all members answer 64 pool rows; the coach learns who was right (soft target = right / number
  right; rows nobody got right are skipped).
- Team answer, fixed before running: coach-weighted vote (each member's answer gets that member's coach probability).

Marks fixed before any run: PASS (go to 6 seeds) if ON beats OFF on `variant` by at least 3.0 points (mean of seeds 100
and 101), ahead on both seeds, with `in_dist` no more than 2.0 lower. Proved wrong if the mean gain is under 1.0 point or
ON is behind on either seed. Void if the coach's mean top probability per row stays under 0.40 (it routed nothing).

## 6. What I want from you

1. **What is actually new?** Compare the swarm idea with mixture-of-experts (including the original Jacobs et al. 1991
   "adaptive mixtures of local experts"), plain ensembles, Branch-Train-MiX (Sukhbaatar et al. 2024), multi-agent debate
   and "More Agents Is All You Need" (Li et al. 2024), Diversify-and-Disambiguate (Lee et al. 2022) and D-BAT, negative
   correlation learning, and "Joint Training of Deep Ensembles Fails Due to Learner Collusion" (Jeffares et al. 2023).
   Correct me if I have any of these wrong. What, if anything, is left that is new for a small from-scratch reasoner?
2. **Will the running test find anything?** Given section 4 (other recipes miss B2's twisted questions about as often as
   a second B2 does), how likely is the coach-routing test in section 5 to pass? What failure modes should I check in its
   logs (coach collapse onto B2, members starving, collusion)?
3. **One next change** that gives a team its best real chance on the twisted questions, for Experiment B. Candidates I
   know of: training members to disagree on unlabeled questions (DivDis / D-BAT), negative correlation learning, members
   that exchange messages while thinking, branching copies from one shared base and training each on different data
   (Branch-Train-MiX), or something better. Pick one. Give the exact change, the control, the pass mark and the result
   that would prove it wrong, all fixed in advance, sized for one 16 GB consumer GPU and about 3 hours per run.
4. **Fair size accounting.** The team is about 10.2M parameters and runs every member on every question. What single-model
   baseline would convince a skeptic (same parameters, same compute per question, same training compute)? Is my 10.8M
   plain transformer a fair bar, or should it be a 10M version of the best recipe (B2)?
5. **Experiment A only:** would several thinkers sharing the one frozen language model be a good use of compute compared
   with making one thinker better? Answer separately from Experiment B.

Format: answer the five points in order, each claim labelled shown / suggested / untested, then the plain-language summary
for me (a high-school senior): a few short paragraphs, no jargon, saying whether the swarm idea is worth my time and the
one experiment to run next.
