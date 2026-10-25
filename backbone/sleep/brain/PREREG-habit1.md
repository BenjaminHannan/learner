# Habit-1: a nightly habit spotter that looks across days (written 2026-10-25 ~21:50Z, before any Qwen3.6 reply or run)

Labels: shown / suggested / untested. Week-2 world (sha256 70db7146...), tests and scoring as addendum 12. Sleep-B (the village / week
model) only; not the card experiments. Owner: thread "Make the model great at spotting patterns" (branch claude/project-thread-9q2vwk),
built on the sleep thread's code (claude/project-thread-cqc4bi, 3fc095a3f) without changing any existing arm.

## Why
Ben (2026-10-25 21:26Z) wants the model "super good at pattern recognition". The clearest pattern failure in sleep: on Qwen3.6-35B-A3B
(addendum 12) routine (habit) questions scored 30 while K2 scored 100. Routines in the week are never stated as habits: Sam mentions one
occasion at a time ("climbing session with Vraskel at Vrelais this evening") on 3 or 4 days, and the test asks "Where does Sam usually
have a climbing session with Vraskel?".

Shown (addendum 12 result JSON): the day tagger turned 1 of the 20 routines into a person-place item (RT tagger recall 0.014). It wrote
activity triples instead ("jam session | with | Klefinir", "jam session | at | Fledas"). The diary router (notes in context) gets all 20,
so the knowledge is in the messages; the per-message notes miss the repeat.

Shown (text only, no model, this commit): counting pairs of candidate names that come up together in one user turn on 2+ different days,
minus the pairs addendum 12's items already link, leaves 21 pairs at the end of the week, 19 of them routines (the 20th is the one already
linked). Run night by night, the spotter would ask 6, 6, 6, 8, 21, 15 questions on nights 2-7, and 19 of 20 routines by night 6.

## Mechanism (`--habit spot`, habit.py, Brain.habit_pass)
Each night, after tagging and the names pass and before refresh: list the pairs of candidate names (sleepb.name_vocab, diary text only)
that share a user turn on >= 2 distinct days so far, that no live item links and that were not asked at the same day count before; most
days first; at most 40 a night. Show the model the latest message of each of those days (at most 6, 400 characters each) and ask
(habit.habit_user) whether it is a habit, answer "Sam usually ..." naming both, or "no". A reply that starts with "Sam usually"-style
text, contains "usually" and both names becomes a HabitItem: key and subject/object in the order the sentence names them, fact = the
sentence. Everything after (refresh day counts, eligibility, NREM dreams from the diary, gist dreams, REM chains, training, probes) is
the unchanged ab_ob_b4_nb pipeline. With `--habit off` (default) nothing changes for any arm (selftest_habit; the existing selftests pass).

**Control (`--habit ctrl`)**: the same prompt, the same number of questions each night (the spot candidate count), asked about pairs
that came up together on ONE day only (drawn with its own rng, seed + 41). Equal compute: the training steps are the fixed schedule
(work scale 4) in both arms, and the questions are equal in number and length.

## Stage 1: does the model answer the spotter's question? (habit_probe.py, no training)
Qwen3.6-35B-A3B, mlx-community 4-bit (the deployed model; the sleep run's base is a PyTorch copy of the same 4-bit recipe), thinking off,
temperature 0, max 48 tokens, through an OpenAI-compatible server (mlx_lm.server on Ben's Mac). 95 questions: R2 (each routine with its
first 2 days), Rall (each routine with all its days), N (the 15 non-routine questions the spotter would ask over the week, addendum 12's
items standing in for the notes), F (40 C2/C4 fact pairs on 2+ days that are not habits; never asked in a real run).
- **S1 pass:** Rall valid yes >= 16 of 20 AND false yes on F <= 30%.
- **Wrong if:** Rall < 10 (the model cannot name the repeat even when shown it): then fix the question before any training run.
- Reported: R2 yes, N yes, how many yes sentences name the activity.

## Stage 2: does sleeping on the spotted habits fix the routine score? (needs a big GPU, about $6 an arm)
Arm **q36_hab**: addendum 12's q36_q4 exactly (ab_ob_b4_nb, `--q4-base --q4-mlx-moe`, Week-2, seed 1, work scale 4) plus `--habit spot`.
- **H1 pass:** routine (weights only) >= 75 (addendum 12: 30), and paired against q36_q4 on the same 20 questions, exact McNemar p < 0.05.
- **No harm:** recall C2+C4 >= 91.0 (q36_q4 96.0 - 5); ARC-Easy >= its own pre-sleep - 5; diary >= base_diary - 5.
- **Wrong if:** 16+ routines become eligible items but routine < 50: spotting works and the learning does not (look at the gist dreams).
- Control: **q36_habc** (`--habit ctrl`), same everything. Expected near 30. If the budget allows only one arm, q36_q4 (same seed, same
  steps, no spotter) is the control, and the report says it is the weaker one (it does not ask the extra questions).
- Reported: RT eligible (diagnostics), spotter counts per night, routine through the router, two-hop, changed-new, reverse.

## Limits (said now)
Week-2 routines have one shape (person + place + activity). Habits by time ("every Friday"), by task ("always asks for a summary") or
with one name are untested; a later week with varied habit shapes is the honest generalisation test. One seed.
