# 365 — Sleep roadmap: how sleep makes Premonition better over time (Fix-sleep thread, 2026-09-25)

Ben, 02:18 UTC: "Try to get as much done tonight as possible. You should architect a road map." Plan 360 says
what sleep does each night; this file says in what order it gets built, what each step must show, and what
depends on other threads. Every step is one change with sealed marks; a registered FAIL stays FAIL.

## Decisions taken tonight (defaults, written down)
- **362 chat re-read: PARKED** (my recommendation on the decision card; Ben had not picked by 02:19 and the
  coordinator said take the default). The base 1B cannot extract facts (DEV test: copied the prompt's examples,
  invented facts). Sleep will re-run the reading thread's improved reader over the whole day, once it exists
  (it also fixes "she/he" pointing back to earlier turns). No sleep-owned reader training.
- **No rentals tonight.** GPU work goes to BensPC through the director's queue; tonight is CPU work at $0.

## Where we are (all verified, card tests, CPU, $0)
| # | Piece | Result |
|---|---|---|
| 360 | Scrap layer: sleep writes 0 rows into the main notebook (was 3 per night) | FAIL as registered, only on my own mark typo (40 vs 50; 50/50 intact); all else pass |
| 361 | Undo a whole night | PASS 7/7, 2 seeds |
| 364 | Self-check gate on a blind bench of 20 faulty + 20 clean nights | running |
| — | Found: sleep skips learning and still says "accepted" when its base checkpoint is missing (likely all of 336) | reported; 364's gate rejects such nights |

## Stage 1 (tonight, CPU, $0): a night that is safe and honest
1. **364 self-check gate** (running). Kept only if no taught answer changes, no wrong or made-up answer appears,
   no right answer is lost, and the sleeper really ran.
2. **366 multi-night scorecard** (sleep research round 2, item 6). A world that grows over 6 simulated days with
   a sleep each night; after every night, score old taught facts, old learned words, new words, lures, and
   practice variety. It is the ruler for everything after: "learning over time" in numbers, and it catches
   forgetting before any multi-night training run. First run: today's word-route sleeper with 360+361+364.
3. **367 idle sleep** ("sleep pressure", Ben: while it isn't used it should be doing something). Sleep starts
   when the assistant has been idle for a set time and has unreplayed turns, not only at a forced end of day;
   a new message always wins (274 reply-first rule). Test: same scorecard, idle-triggered vs end-of-day.

## Stage 2 (needs sleep research's fix 0 first): practice school, the real self-improvement
4. **363 practice school on the loop reasoner.** Each night: build puzzles from the assistant's own taught rows
   (chains, missing rows -> "I don't know", corrections, many-valued relations, near misses), plus checked
   creative wins from `wins/wins.jsonl`; exact code grades every answer; train with sleep research's recipe; keep
   a slow averaged copy of the weights as the answering model; the 364 gate decides keep or undo.
   Arms (round 2, item 2): no sleep, the same amount of plain practice, placebo sleep (grades shuffled), and
   real sleep. Sleep counts only if it beats all three on FRESH blind puzzles about facts taught after the recipe
   froze. Held-out families differ in features the model can see (round 2, item 3). Log variety every night and
   count distinct visible families of wins, not raw wins (item 5).
   Blocked on: the shared step embedding (the third-step input slot is untrained, round 2 item 1). Until it lands,
   363 registers only 1-2 step arms.
5. **Self-check lines for the reasoner** added to the gate when 363 trains it: both answers of a one-fact twin
   pair right; never "I don't know" when the fact is present.

## Stage 3: sleep reads and dreams
6. **Re-read the day (362, parked)** with the reading thread's improved reader, whole day at once, candidates
   to the scrap layer, one or two morning questions, saved only on the user's yes.
7. **Sleep-time thinking** (job D): pre-compute likely answers from taught rows into the scrap layer; they never
   answer unless re-derived live. Only after checking that questions are predictable enough to be worth it.
8. **Creative recombination** (job G) once 364 guards against creative turning into made-up facts.

## What "better" means, measured
- Learning over time: the 366 scorecard's after-night-N scores, old and new, with forgetting shown.
- Reasoning: 363's fresh blind puzzles, against no-sleep, plain-practice and placebo twins.
- Safety: 0 derived rows in the notebook (360), every bad night undone (361, 364), 0 made-up answers.
- Memory: when 362 lands, saved-fact rate on a fresh blind bank vs 0.1's live reader alone.

## Dependencies
- Sleep research thread: reasoner recipe, shared step embedding, one-fact twins (363 waits on them).
- Reading thread: better reader (362 waits on it).
- Creative thread: `wins/wins.jsonl` records (format agreed 00:54 UTC).
- Month-end / director: the rent kit must rebuild sleep's base checkpoint on every rental (reported).
