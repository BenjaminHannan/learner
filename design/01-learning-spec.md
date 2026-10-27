# Step 1 — What "able to learn" means

Decided with Ben, 2026-09-18. This replaces the recurrent-transformer-plus-side-memory design; that code stays in `memorylab/` as a measured baseline.

## The goal

A model of Ben's own design that keeps permanently changing itself from new experience after it is built. The human brain is a source of ideas, not a blueprint.

## Decisions

| Question | Answer |
|---|---|
| What it learns after being built | Facts it is told; new skills and methods; improvement with experience; patterns it discovers on its own |
| What it learns from | Being told or taught; right/wrong feedback; its own practice between inputs; raw observation |
| Learning speed | Both: facts from a single exposure, skills gradually with practice |
| Starting knowledge | Almost nothing: built from scratch, starting in a simple controlled world and language |

## What these answers force

Each answer requires a specific piece of machinery:

1. **Learning from raw observation** requires the model to constantly **predict what comes next** and learn from its own prediction errors. This is the always-on learning signal, and it doesn't need a teacher.
2. **Facts from one exposure** require a **fast memory** that stores an episode immediately in one shot.
3. **Skills gradually through practice** require a **slow learner**: the main network's own weights, changing a little at a time.
4. **Both speeds together** require **consolidation**, meaning a way to move what the fast memory holds into the slow learner over time. This is also the main defence against forgetting old knowledge.
5. **Right/wrong feedback** requires **learning from reward**, i.e. strengthening whatever led to success.
6. **Its own practice** requires an **offline phase** in which the model replays and rehearses without new input.
7. **Starting from nothing** requires a **world** for it to live in: a controlled environment and language simple enough to learn from scratch on one RTX 5070 Ti.

## Honest status

No existing system does all of this well. Continual learning without forgetting is an open research problem. The plan is to build one piece at a time, testing each with a measured experiment before adding the next.

## Additions (2026-09-18, round 2)

Agreed:
- **Large but sparse knowledge.** The knowledge store can be very large, but each thing learned touches only a small part of it, so new learning overwrites little.
- **The world is the text village**, built on a grid underneath from day one. The model first reads the narration (text only); later it acts in the same world (move, pick up, drop). There is one world, not two.

Agreed in round 2 (continued):
- **Transfer is a core goal, and it is measured:** the more the model knows, the faster it must learn something new. For example, a model that has lived in several villages should learn a new village's rules in fewer lessons than a fresh model.
- **Attention over knowledge and skills** (Ben's idea) is the leading design for the slow learner. A modest core network pays attention to a large library of knowledge/skill pieces, pulls in only the few relevant to the moment (sparse), and learns which pieces go together. Learning a new skill should mostly mean finding a new combination of old pieces plus a small new piece.
- **The teacher is Ternary Bonsai 2 27B (a compressed Qwen3.8-27B) running on the Mac**, not the model's brain. It writes sentence patterns that the fast simulator fills with fresh names, and it sends natural explanations and corrections to the training PC in parallel, without ever blocking training. The simulator stays the source of truth. This keeps the RTX 5070 Ti free for training.
  - Measured on the Mac (M1 Pro, 32 GB), 2026-09-18: installed in `.runtime/teacher/` (8.7 GB model, 0.7 GB packages). Loads in 3 s, generates 12 tokens/s, peak memory 9.6 GB. On a rewording test it produced 8 correct, simple paraphrases with the placeholders intact. Script: `design/pilots/bonsai_speed.py`.
