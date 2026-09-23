# Experiment 44 — registered pass marks (written and sealed BEFORE any registered run)

Date written: 2026-09-21. Registered seeds: **4102, 4103, 4104**. Every mark is scored
**per seed**, never averaged across seeds. Development/smoke work used throwaway seed 9999 only.

## What is being tested

A notebook (a plain dict of `(person, relation) -> person`, ~15% of entries absent) holds all the
facts. Skill *r* is "look up relation *r*", a matrix built at run time from that notebook, with a
dedicated absorbing UNKNOWN sink for missing facts. The tape is a probability vector over the
people plus the sink. The only trained numbers in the base system are an 8x8 token→skill logit
table; the only trained numbers in sleep are 3x9 routing logits per new word. Supervision is the
final answer only.

## Definitions used by every mark

- **Village**: N people, R = 8 base relations (mother, father, spouse, boss, best_friend,
  neighbour, doctor, teacher), each an independent uniformly random partial function
  person → person with each entry absent with probability 0.15.
- **Training village**: N = 60, name prefix `T_`. **Fresh village**: N = 60, prefix `F_`.
  **Big village**: N = 200, prefix `B_`. The three name pools are disjoint by construction and the
  script asserts it. All marks below are measured on the fresh and big villages, never the
  training village.
- **Question**: a start person plus 1..k relation tokens. **Resolvable** = every hop of the true
  chain is present in the notebook. **Missing** = at least one hop is absent.
- **Exact answer accuracy**: predicted string equals the true answer, where the true answer of a
  missing chain is the literal string `unknown`.
- **Answer rule (given by hand)**: answer = the most probable person if its probability >= 0.9,
  otherwise `unknown`.
- **Set sizes**: 300 questions per hop-count or depth; 400 questions for the honesty mark.

## Registered marks

**R1 fit** — on the fresh N=60 village: pooled resolvable 1-, 2- and 3-hop questions
(300 each, 900 total) reach exact answer accuracy **>= 0.99**. Every seed.

**R2 depth** — on the fresh N=60 village: resolvable questions of depth 4, 6, 8 and 10 each reach
exact answer accuracy **>= 0.95**. Every seed. (Training uses 1–3 tokens only.)

**R3 new world** — the R1 and R2 thresholds also hold on the N=200 village whose names never
appear anywhere in training. Every seed.

**R4 honesty** — on the fresh N=60 village, 400 questions of 1–4 tokens whose true chain hits a
missing fact: `unknown` is answered in **>= 0.99** of them **and** a confident person is answered
in **0** cases. Every seed. (These two conditions together mean the unknown rate must in practice
be 1.000; that is intended.)

**R5 sleep** — for each of the three new words
(`maternal_grandmother` = mother→mother, `boss_of_spouse` = spouse→boss,
`doctor_of_mothers_friend` = mother→best_friend→doctor), taught only by raw
(person, new_word, answer) episodes drawn from the training village:
from **20** episodes the word is **installed by the gate** AND reaches **>= 0.95** exact accuracy
on 300 resolvable one-token questions in the fresh N=60 village. The same, separately, from
**50** episodes. Every seed, every word.
The gate is: 4-fold cross-validation (folds split by person, so repeated people cannot leak)
over checkpoints {0, 50, 100, 200, 400, 800} updates; a checkpoint is eligible only if its
out-of-fold exact match is **>= 0.80**; the eligible checkpoint with the lowest out-of-fold NLL is
refit on all episodes; install requires refit-vs-out-of-fold agreement **>= 0.90**, base answers
unchanged, and an identical weights-only reload. If no checkpoint is eligible, nothing installs.

**R6 reuse** — with all three 20-episode words installed in one model, 300 resolvable questions of
2–4 tokens, each containing exactly one slept word at a random position and base tokens elsewhere,
reach **>= 0.95** exact accuracy on the fresh N=60 village. Every seed.

**R7 safety** — every seed, for every sleep run:
(a) the 900-question base-relation probe on the fresh village returns **answer-for-answer identical**
predictions before and after each install (and after all three);
(b) saving and reloading with `weights_only=True` gives **identical** answers;
(c) a run whose 20 episodes have **100% uniformly random answers** is **REJECTED** (installed = false).

## Recorded, not gated

- Episodes with 10% wrong answers (2 of 20): the cross-validation table, whether the gate
  installs, and the accuracy if it does.
- Wall-clock seconds per stage; trainable parameter counts; the routing each word settled on;
  the number of distinct people available for episodes.
- The same R5 words measured on the N=200 village; reuse accuracy on the N=200 village.

## Given by hand (not learned) — must be stated in RESULTS.md

1. The hop loop: one routed skill call per token, in order.
2. The halt rule: stop when the token tape is empty. Nothing counts and nothing learns to stop.
3. The lookup matrices, built at run time from the notebook, including the UNKNOWN sink and the
   fact that it absorbs.
4. The 0.9 answer threshold and the "otherwise say unknown" rule.
5. A new word is exactly 3 routing stages, one of whose options is "keep" (do nothing).
6. Which three composites are taught, and that episodes are only drawn from people for whom the
   composite resolves.
7. The relation vocabulary size R = 8 and the 1–3 token training range.

## Failure protocol

If a registered run misses a mark, the FAIL is recorded in RESULTS.md first. Only then may ONE
clearly described change be made as "v2", with its own sealed marks, run in a single wave on
4102/4103/4104 AND on fresh seeds 4111/4112/4113. No further tuning.
