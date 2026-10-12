# Prompt for GPT (web): learning skills with no right answer during "night" self-training (2026-10-12)

Paste everything below the line into GPT. It cannot see our repo, so the prompt stands alone.

---

I am designing how a small self-improving model learns, and I want a critical outside opinion. Please label every claim **shown**
(measured or stated in a paper you can cite), **suggested** (one result, an abstract, or reasoning) or **untested**.

## The model and its rules

- A ~100M-parameter learned "thinker" (looped transformer blocks) on top of a frozen 271M text encoder (EmbeddingGemma), plus a small
  writer that today outputs only short answers (up to 8 letters) and calculator calls, and moves in a text version of Crafter (a 2D
  Minecraft-like game). It cannot yet write free English or draw.
- It ships to one person's own PC or Mac and keeps learning there. By day it works and tries things; at night ("night mode") it trains on
  its own tries from that day. Today it keeps only tries it can check itself: a question's own worked examples, a calculator, game
  outcomes (+1 per new achievement). Two-night recipe that kept old skills in a small test: learning rate 3e-4, 32 visits per kept try,
  replay of old training rows picked by how much their loss rose against a frozen copy.
- Hard rules: (a) no outside teacher, judge or reward model, in training or at home; (b) the only outside data ever allowed is a fixed
  set of 171,940 short comprehension questions and the FineWeb-Edu web text (used as fill-in-the-blank rows); (c) every night step may
  use only what the model itself saw plus fixed constants, with no human or researcher choosing anything at run time; (d) everything
  inside the model is learned; hand-written code is allowed only as an outside tool the model calls (like a calculator or a renderer).
- An existing rule in our design: "the deciding filter is always a real check; checkers are part of the task, never a learned judge's
  say-so; a learned filter may only rank tries before the real check runs".

## The question

The owner asked: night mode only learns from checkable tries, so how could the model get better at things with no right answer: using
Shakespeare's literary devices after reading Shakespeare, building a cool house in Minecraft, or drawing a nice picture in Microsoft
Paint?

## Relevant results we already have (small card experiments, 3M-parameter models; NOT the real model)

| Test | Result |
|---|---|
| Learned "will my answer pass the check" guesser on the model's own features | within-kind AUC 0.543 and 0.597 on two seeds (mark was 0.65): FAIL |
| Learned practice picker vs hand rule | beat the rule on one seed (+8.8), not the other (-1.2): not confirmed |
| Creative loop learning from its own fit/fail reward vs a shuffled-reward placebo | real beat placebo by +17.2 and +18.4 points (reach@32) on two seeds |
| Game: copying the model's own most-likely moves | +0.01 and -0.08 achievements per game: learned nothing |
| Game: value guesser + random-network-distillation curiosity | -1.48 and -0.28 vs the copy loop: worse |
| Taking the first program that fits a question's examples | right on the hidden answer 64.5% of the time at 1,000 candidates |

## Our proposed answer (untested)

1. Reading as checkable practice: hide words or lines of what it read and guess them (the real text is the answer key).
2. Split each goal into checkable parts (walls closed, door walkable, 14 lines, rhyme) that tools check as now.
3. A learned "taste critic" head trained by day on finished good examples the model saw versus its own tries (with a replay buffer of
   older tries, gradient penalty, bounded output), frozen at night, used only to pick the best of N tries that already pass every check
   (best-of-N filtered self-training, no policy gradient through the critic). Guards: a copy guard (too close to a seen example = fail),
   a nightly exam on held-back and deliberately broken examples, a variety check, and an undo guard on old skills.
4. The person's reactions (kept/deleted/redone/edited, read by the model itself) only as a capped tie-breaker, never bare approval;
   personal preferences stored as readable notes, not weights.
5. Later, a learned value head ("inner motivator", dopamine-like) learns to predict the combined score.
The brain analogy we used: a zebra finch memorises its tutor's song, practises alone, and dopamine neurons signal when its own song
misses its expectation (Gadagkar et al. 2016); song replays in sleep.

## First test we sealed (a card experiment, separate from the real model)

A toy Paint: 12x12 canvas, 4 colours, a hand-written renderer with rectangle/triangle/dot commands (max 6). A <2M-parameter maker
writes command programs; it starts out drawing random clutter. It never sees how examples were drawn: the critic sees only 200 finished
house pictures from a hidden generator (body, stepped roof on top, centred door). A hidden 5-trait house score (never seen by maker or
critic) measures progress on 1,000 raw samples (no picking at test time). 512 requests per day, 8 tries each, one kept per request,
6 nights. Arms: critic pick (C), random pick (R), random pick with sharper sampling (R07), blank untrained critic (B), hand simplicity rule
(H), oracle pick by the hidden score (O, ceiling only), no nights (N). Main mark: mean over 3 seeds of C - R >= max(0.05, 0.25 x the
oracle's pick-only headroom), positive on every seed; C must beat B, H, R07 and N by >= 0.03; copies <= 5%; no collapse; old skill kept.
Verdicts: PASS, SHORTCUT (H or B within 0.03 of C), NO GAIN (C - R <= 0.02), TOY TOO HARD (O - R < bar), else UNDERPOWERED (one
pre-set extension to 6 seeds and 12 nights).

## What I want from you

1. Is the layered answer above sound under rules (a)-(d)? What is the strongest alternative we have not considered, and what is the
   evidence for it (cite papers)? Keep claims about the small card experiments separate from claims about the real 100M model.
2. The biggest ways the taste critic could fail or be gamed at this scale, and which guard catches each.
3. Is the TC-1 toy a fair test of the idea? What would you change, one change at a time, with the pass mark fixed in advance and the
   result that would prove the idea wrong?
4. For each of the three examples (Shakespeare devices, Minecraft house, Paint picture), the single most promising next test after
   TC-1, with its pass mark and its proved-wrong result.
5. Finish with a plain-language summary (6 sentences at most) for the owner, a high-school senior: no jargon.
