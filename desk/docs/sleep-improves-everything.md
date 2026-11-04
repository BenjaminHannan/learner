# Sleep improves every part (plan, 2026-11-04)

Ben (2026-11-04): "Figure out how to make sleep improve every single feature that contributes to the model's intelligence. Once you come up with mechanisms, test them on toy models on the Mac until they're proven to work, then implement them into Premonition."

## One rule for all of it
During the day, every part makes predictions or choices, and the truth often arrives later: the code ran, Ben replied, the quiz was graded, a site confirmed a note. Each part LOGS its (prediction, truth) pairs. Sleep then does the same 4 steps for every part:
1. **Replay** the logged pairs (older days to train, the latest day held out).
2. **Update** the part to make fewer errors (refit / gradient steps / counts).
3. **Seatbelt:** score the new version vs the old on held-out data and the fixed tests.
4. **Keep it or roll it back:** keep the update only if it isn't worse; otherwise roll back and log why.

This is automatic and mathematical (Ben's rule, 2026-09-21): the model never decides what is stored or learned. `maybe` notes never train. Text is the anchor for the senses.

## Every part and what sleep does to it
| Part | Today at night | Sleep mechanism to add | Toy track |
|---|---|---|---|
| 🧠 Thinking (Nanbeige adapter) | trains on notes + surprises + re-study | (a) surprise-picked replay vs uniform at the same budget; (b) corrections that really replace old facts (model of Ben in weights); (c) skills from poking: sandbox truths train it | T2 |
| ✅ Checker head + calibration | nothing | refit the head on new labels + refit calibration, with the seatbelt | T1 |
| 📣 Speak-o-meter | refit | add the seatbelt | T1 |
| 🔮 Guesser + ⏱️ when-model | old habits fade at a fixed 0.8 | learn the fading rate from next-day error; also learn when Ben goes idle (feeds "wait for a break") | T1 |
| 🎚️ Think-longer threshold | fixed | fit from logs: extra tries vs answers they actually fixed | T1 |
| 👁️ Where to look | none | learn which windows/regions tend to hold surprises | T1 |
| 🔎 Website trust | none | per-site counts from confirmed vs wrong | T1 |
| 🧪 Scientist's experiment chooser | online only | recompute learning progress over all logs | T1 |
| 🗺️ Imagining (world model) | uses the rulebook | learn "what happens after move a" from game logs, then plan with it | T3 |
| 🔁 Analogy | rule-based masking, failed at ceiling | learn shape keys from the patterns sleep finds (same-pattern = similar); harder test | T3 |
| 🧩 Patterns | made in sleep by formula | prune by next-day surprise | T3 |
| 👀👂 Eyes / ears (projectors) | none | cross-sense sleep: text-anchored practice, 2-of-3 rule, echo-loop guard, seatbelt (design §9) | T4 |
| 🗄️ Desk + cabinet memory | n/a | learns by sleep by design | Experiment M1 (running) |
| 🌱 Growing experts | n/a | freeze + add an expert when full | Experiment G1 (toy stage added) |

## How "proven" works
- Each mechanism gets a toy test on the Mac, with pass marks fixed BEFORE it runs and a result that would prove it wrong.
- If it fails: diagnose, make ONE change, and register a new version. At most 3 versions per mechanism, then report to Ben. No moving the goalposts.
- Passing toy tests means "works on the toy". The real Glim gets its own check after implementation (real nights, the seatbelt numbers in the morning).
- Implementation only after a toy PASS:
  - app parts in desk/ (this worktree);
  - brain-sleep parts as a patch + tests for the sleep app (~/learner-ops/sleepmlx-src). The lead applies the patch: the app runs that folder every night.
- Senses wait for the picture projector to be plugged into the app.

Briefs: /tmp/aon/task-sleep-common.md + task-sleep-T1..T4.md.

## Added 2026-11-04 ~12:00 (Ben's paper notes + general rule)
- **General rule (Ben):** anything in Glim that involves a neural net is trained in sleep, with the seatbelt. That includes the frozen encoders (SigLIP eyes, Whisper ears): the ears look encoder-limited.
- **Ben's focus:** intake, i.e. taking in information well (what to look at, how often, how cheaply).

| New track | What | Toy? |
|---|---|---|
| E1 intake + speed engineering | lock the brain in RAM (wired memory, reserved cache); prompt-prefix ordering for cache reuse; real batching of Motes; change-only intake (process only what changed, so it can look more often) | engineering; tiny MLX model for measurements |
| T5 stuck list + sleep insight | stuck problems are kept; sleep mixes them with related memories, the checker/executor verifies, and only verified solutions become cards ("Sleep inspires insight", Wagner et al. 2004) | yes |
| T6 small fast nets distilled in sleep | (a) watcher: a tiny net that samples inputs often and learns what's worth waking the big brain for (intake); (b) reflex for real-time games (muscle memory); (c) draft model for speculative decoding (speed) | yes |
| T4b encoders in sleep | LoRA on the eye/ear encoders inside cross-sense sleep, in an encoder-limited toy world | yes |
