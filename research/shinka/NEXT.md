# If there is a trial 2: three changes

Written 2026-10-20 after trial 1 (`results/evo1/REPORT.md`, verdict FAILURE, $3.389 spent). This is a proposal only: no runs, no spend. Ben decides whether there is a trial 2.

Trial 1 costs used for the estimates below:
- Opus 5.5 mutation: about $0.087 per call (shown: $2.175 / 25 calls).
- Opus 5.5 judge: about $0.21 per finalist (shown: $1.06 / 5).
- Haiku 5.5 mutation: about $0.0015 per call (shown in the smoke test, at about 3k input / 2.4k output).
- Sonnet 5.5: about $0.017 per call (shown in the first plumbing test).

The toy, the seed noise, and the BETTER / NOT KNOWN marks stay exactly as in `CARD.md`. Trial 2 uses new fresh seeds, **2001 and 2002**, because 1001 and 1002 have now been seen.

## 1. An idea-level novelty filter, before evaluation
**What failed (shown).** Code-similarity rejection never fired: 0 rejections out of 15 proposals. Every rewrite was new code for the same idea ("deflation pursuit").

**Change.** Before a proposal is evaluated:
- a cheap model (Haiku 5.5) writes a one-sentence "core operation" for it;
- a second Haiku call compares that sentence with the run's list of core operations so far and with `KNOWN_SHORT.md`;
- a proposal judged to be the same family as an archived program, or a listed known method, is sent back for resampling (at most 2 resamples, then it is accepted and flagged);
- the core-operation list is stored with each program.

**Cost.** About $0.003 per proposal (suggested), so about $0.50 for 150 proposals.

**Marks, fixed in advance:**
- Pass: after the run, a separate blind Opus call clusters the core-operation sentences of all correct programs. It finds **at least 4 families**, and **no family holds more than 50%** of correct programs.
- Proves the filter useless: one family holds more than 50%, as in trial 1, where one family held 100% of the finalists.

## 2. Several different seed programs, one per island
**What failed (shown).** Every finalist came from one family that appeared in generation 1. The strange slot fired 6 times but only had the seed and generation 1 to choose from.

**Change.** 4 islands, each started from a different seed family. The seeds may be known methods; they are starting points, not candidates. Suggested families:
- the PremonitionMini single pool;
- a GRU line encoder;
- slot competition;
- outer-product (role × filler) binding.

Migration is off for the first 40% of generations. The strange slot starts only once at least 10 correct programs exist.

**Cost.** CPU only: 3 extra seed evaluations, with no API spend.

**Marks, fixed in advance:**
- Pass: at the end, the best programs on **at least 2 islands descend from different seed families**, and the finalists span **at least 3 seed families**.
- Proves it useless: all finalists come from one seed family again.

## 3. A cheap mutation model; Opus only for judging
**What failed (shown).** Opus mutations cost about $0.087 each, so trial 1 got about 20 generations. That is too few to leave the first family (suggested).

**Change:**
- mutations by Haiku 5.5 (80%) and Sonnet 5.5 (20%);
- Opus 5.5 kept only for the novelty judge and for one "meta" review every 25 generations, which reads the archive and suggests unexplored directions;
- every finalist gets a judge budget reserved in advance. Trial 1 lost one verdict because it checked the budget against a worst case per turn.

**Cost.**
- Mutations: about $0.005 per mutation on average, so about $0.75 for **150 generations**, plus about $0.60 of novelty-filter calls (covering change 1).
- Opus meta reviews: about $0.30.
- Judge: 6 finalists at about $0.25 each, reserved, about $1.50.
- Total about $3.15 (suggested), inside a new $5.00 limit with the same $4.50 stop.

**Marks, fixed in advance:**
- Process: at least 120 generations are completed.
- Result: the trial passes if at least one finalist is BETTER on fresh seeds 2001/2002 (CARD.md section 7, unchanged), judged NOT KNOWN, and also beats the multi-head pool by more than 0.045 on both seeds.
  - In trial 1 that last mark was only "reported"; I would make it required. Beating only the seed is easy, as trial 1 showed.
- Proves the trial a failure: no such finalist.

## What I would not change
- the toy, the isolated scorer, the sealed card, the hand-reading of finalists;
- the four-way report: both / better-but-known / novel-but-not-better / neither.

Trial 1's harness worked as intended. What went wrong was the search: it covered too few generations and never moved beyond the first idea family it found.

## Trial 2 status (2026-10-21): G0 failed; G0b (512-name probe) PASSED, Stage 1 ready, not launched

Update: G0b passed (novel-name person-position 0.968, `trial2/G0B-REPORT.md`). It does not test the 16-name transfer. Stage 1 (`trial2/ideate.py`, cap $5.00, stop $4.50) waits for the coordinator's GO. Older text below is the state at the G0 failure.

Trial 2 (idea-first, `TRIAL2-PLAN-OPUS.md`) stopped at its sealed $0 gate G0. Details: `trial2/CARD2.md`, `trial2/G0-PASSMARK.md`, `results/trial2/g0.json`. Spend: $0.110 (plumbing test only). Stage 1 was never started.

- **Result (shown):** a probe that sees one line's reader states found the person's position on 43% of novel-name lines (mark 60%; seeds 33%, 34%, 62%; chance 10%). Controls valid. The coordinator ruled the FAIL final.
- **Caveat (suggested, not tested):** the probe was trained on only 16 names and scored 100% on them, so it probably memorised those names' vectors. Multi-head already finds the person on about 57% of novel lines, more than the probe did. The FAIL may therefore say more about the probe than about the toy.
- **Redesign option (needs Ben's decision; new gate, new pass mark written first, never tuned on this result):** a probe that must find the person by role structure, for example "the token that is not a filler, relation or value", with training that gives it no way to memorise names (many more names, or random name vectors per batch).
- **Side results:** one Sonnet prosecutor call with web search cost $0.092 (plan estimated $0.25-0.35). The +0.05 bar held against the existing noise (2 x SE = 0.037, wide interval). The money guard is built and tested but its scripts are PARKED, with 8 review findings open (`trial2/REVIEW-STATUS.md`).
