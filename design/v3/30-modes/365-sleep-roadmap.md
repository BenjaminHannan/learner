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

## Status 2026-09-25 ~03:30 UTC (Fix-sleep thread)
| Job | State | Evidence |
|---|---|---|
| 360 scrap layer | registered FAIL on a mark typo; behaviour as intended (50/50 rows to scrap, 87/87 replies same) | artifacts/claude-slp360-20260925/RESULTS.md |
| 361 whole-night undo | PASS 7/7 both seeds | artifacts/claude-slp361-20260925/RESULTS.md |
| 367 idle sleep | PASS 5/5 both seeds, blind recount agrees | artifacts/claude-slp367-20260925/ |
| 364 self-check gate | registered FAIL: 13/20 bad nights caught (bar 18), 0/20 clean rejected, twin 0/20 | artifacts/claude-slp364-20260925/RESULTS.md |
| 368 write lock | sealed, running (from the 364 finding: sleep code could write "taught" rows) | artifacts/claude-slp368-20260925/ |
| 366 multi-night scorecard | run 1 VOID (crashed at scoring, no numbers seen); run 2 running | artifacts/claude-slp366-20260925/ |
| 363 practice school | sealed, queued for BensPC after the rsn/lis jobs (4 arms, 2 seeds, --base 296 --arm plain) | artifacts/claude-slp363-20260925/PASSMARKS.md |
| 364b gate v2 | claim check, new-people sandbox, per-word probe budgets, main-log check, optional restart check; a fresh blind bench is being written by a separate agent | scripts/claude_slp364b_gate.py |
Correction to an earlier claim: a message that arrives during a running sleep waits for it (~1.5 min on CPU);
interrupting sleep needs sleep in its own process (later step).

## Status 2026-09-25 ~06:50 UTC (Fix-sleep thread)
| Job | State | Evidence |
|---|---|---|
| 366 multi-night scorecard | PASS 5/5, blind recount agrees (limits: one world run twice; taught facts sampled at 120) | artifacts/claude-slp366-20260925/RESULTS.md |
| 368 write lock | PASS 5/5, recounted | artifacts/claude-slp368-20260925/RESULTS.md |
| 364b gate v2 | registered FAIL: caught 17/20 but its new-people sandbox broke later teaching on 20/20 honest nights (cause: a deep copy swapped the inner notebook) | artifacts/claude-slp364b-20260925/RESULTS.md |
| 364c gate v3 | registered FAIL on P364c.4 (39/40: one bad night wrote to the log file directly); caught 18/20 vs v1 11/20; 0/20 honest rejected; honest replies 20/20 unchanged; missed both made-up-answer faults | artifacts/claude-slp364c-20260925/RESULTS.md |
| 369 notebook restore | PASS 5/5, recounted (evidence thin on P369.2: 1 restored night): a night that changes the main notebook files is put back | artifacts/claude-slp369-20260925/RESULTS.md |
| 364d gate v4 | registered FAIL: 15/20 bad nights caught (bar 18) vs v1 10/20; 0/20 honest rejected; replies 20/20 unchanged; main log 40/40. Misses all use question forms or people the gate never asks about (yes/no, multi-step, "Tell me", people with no facts) | artifacts/claude-slp364d-20260925/RESULTS.md |
| 363 practice school | queued on BensPC (after rsn-353-pc) | handoff/queue/slp-363-train.md |
| 364e gate v5 | registered FAIL: 17/20 bad nights caught (bar 18) vs v1 9/20; new rules alone 2 (bar 3); 0/20 honest rejected; replies 20/20 unchanged; main log 40/40. Misses: spelled-out word questions, an extra word installed without evidence, reverse "Whose R is X?" questions | artifacts/claude-slp364e-20260925/RESULTS.md |

Reading after 364e (11:00 UTC): four gate versions failed the same way (each fresh blind bench finds a question kind
the gate does not ask). Best stack so far: slp-360 scrap + 368 lock + 369 restore + 361 undo + gate v5.

## Status 2026-09-25 ~12:50 UTC: switched to learning (Ben 11:03: "as long as sleep improves the model, it's fine")
| Job | State | Evidence |
|---|---|---|
| 363w school night inside idle sleep (tiny reasoner, CPU) | registered FAIL on no-harm: seed 1 lost 20 of 600 on a fixed panel although every night passed its self-check; plumbing marks pass (notebook untouched, 13/13 bad nights thrown away) | artifacts/claude-slp363w-20260925/ |
| 363x same, self-check adds a fixed general set compared with the start | PASS 5/5 on fresh seeds 3-4, recounted; no learning claim (panel +7 / -4) | artifacts/claude-slp363x-20260925/ |
| 363 practice school, full size | the learning test; BensPC, 6th in queue after rd-371 and rsn-353-pc | handoff/queue/slp-363-train.md |
Next once 363 reports: if SCHOOL beats PLAIN and PLACEBO, run the 363x night on the full-size reasoner (GPU) with the
same guard. Learned from 363w/x: practice on a narrow set of taught relations lowered general answers at tiny size.
