# Sleep-B addendum 4: rotating regions, twisted dreams, therapy replay, and guess + dopamine (written 2026-10-24 ~18:35Z, before any addendum-4 code or run)

Labels: shown / suggested / untested. Same model (Qwen3.5-2B), week, tests, scoring, seed (1), step schedule (AB stage 1) and
open-book rehearsal as addenda 2 and 3. Not the village model, not the card experiments.

## Why (Ben, 17:40Z and 18:00Z)
- "Could we train different parts of the model at different times?"
- "Can we try to incorporate [Hoel's] strange practice questions where the model has some twisted version of what [it learned],
  basically mimics dreams?" Also the "four ideas" except the fire drill: filing, therapy, anti-cramming.
- "For the guessing brain, can you have the model predict it and then also include the dopamine thing when something goes better
  than it predicted?"

Filing (sorting the day into long-term storage) is already Sleep-B's interleaved replay. Anti-cramming is Hoel's twisted dreams.
So the new arms are rotating regions, twisted dreams, therapy and guess + dopamine.

## Control
The seed-1 `ab_ob` (addendum 2; LoRA add-on, open-book rehearsal). Weights only: recall C2+C4 56, two-hop 4, changed-new 70,
routine 67, integration 47, pool 37. With the diary: pooled 82. ARC-Easy (500): 92.4. Base ARC is 89.6.

## Arms (each one change from `ab_ob`; all train only the LoRA add-on, so each fits a 16 GB card)
- **ab_ob_rot, "different parts on different nights":** the layers are split into 4 equal, contiguous quarters. On night d, only
  the add-on modules in quarter (d - 1) mod 4 can train, and the rest are frozen for that night. Over 7 nights the quarters run
  0, 1, 2, 3, 0, 1, 2.
  - Downscaling (SHY) still trims every module each night: learning is local, and the trim is global.
  - Steps, batches and the KL guard are unchanged.
  - Brain (suggested): local sleep (Huber 2004; Vyazovskiy 2011) and one-hemisphere sleep in dolphins and birds (Rattenborg 2000).
- **ab_ob_twist, "twisted dreams" (Hoel 2021, the overfitted brain):** while dreaming each night, the base model also writes
  2 short, strange, dream-like scenes for each item. The real fact stays true, but the setting and wording are odd.
  - A scene is kept only if three checks pass. It must name both of the item's entities, and it must not leak a test question.
    The base model must also answer one of the item's kept dream questions correctly when given only the scene as context.
  - Kept scenes join the item's practice texts, next to its normal paraphrases.
  - Twisted scenes are built from real diary facts, never from random noise. The multistep thread found that off-distribution
    practice hurt.
- **ab_ob_ther, "therapy replay" (Walker & van der Helm 2009):** salient items get 2x replay priority, and each of their practice
  examples has loss weight 0.5. An item is salient if it was flagged important, was corrected, or replaced an older value.
  - So these items come up more often, but each step on them is gentler. The total push stays about the same, spread over more
    and smaller steps.
- **ab_ob_guess, "guess, then dopamine":** before each night's practice, the model answers each item's probe question and gives
  a confidence. The confidence c is the probability of the first answer token. Outcome o is 1 if the answer is right, else 0.
  Surprise is o - c.
  - When the result is better than predicted (o - c > 0, right but unsure), the item's replay priority is multiplied by
    1 + 2(o - c), up to 3x.
  - Wrong answers keep Sleep-B's existing 2x priority, and confident right answers are unchanged.
  - Brain (suggested): reward and dopamine tag memories for replay in sleep (Singer & Frank 2009; Lansink 2009).
  - The separate "dopamine after deployment" thread works on rewards while the model is in use. This arm only changes what
    sleep replays.

## Pass marks (fixed now; control = seed-1 ab_ob above)
- **No harm (every arm):** ARC-Easy >= 87.6 and diary pooled >= 77.
- **ab_ob_rot:**
  - R1 is the no-harm mark.
  - R2 memory, non-inferior: recall >= 52 (control - 4). This arm trains a quarter of the add-on each night, so matching the
    control counts as a pass.
  - Reported, not marked: training seconds per night and peak GPU memory.
  - Wrong if recall < 46: one quarter at a time cannot hold the facts.
- **ab_ob_twist:**
  - T1 is the no-harm mark.
  - T2 memory: recall >= 61 (control + 5). Every test question is worded differently from the practice, so recall measures
    generalization.
  - Reported, not marked: reverse and two-hop.
  - Wrong if recall < 51: twisted dreams blur the facts.
- **ab_ob_ther:**
  - H1 is the no-harm mark.
  - H2 updates: changed-new >= 80 (control + 10).
  - Wrong if changed-new < 60.
  - Changed-new has only 20 questions (5 points each), so H2 needs a gain of at least 2 facts.
- **ab_ob_guess:**
  - G1 is the no-harm mark.
  - G2 memory: recall >= 61.
  - Reported, not marked: the share of probed items with o - c > 0.2 each night, and their recall the next morning.
  - Wrong if recall < 51.
- One seed. Any gap under 4 points is not called shown. That is the seed spread in addendum 2.

## Code rules
- New arms are gated by name. The control `ab_ob` and the addendum 2/3 arms must run exactly as before, with the same random
  streams. A CPU smoke check must confirm that `ab_ob` is unchanged.
- Each arm's new random draws use their own RNG. The twist arm's extra generation uses a separate torch generator or a fixed seed.

## Compute
- These are LoRA arms, about 50 minutes each on an A100. Plan: Vast A100 40GB boxes, 2 arms per box, with a cap agreed with the
  coordinator. Ben's PC is an option if it is free.
- Each box is destroyed as soon as its results reach its label. If training has not started within 20 minutes, the box is
  destroyed.
