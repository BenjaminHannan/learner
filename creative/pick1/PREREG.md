# Pick-1: once the model has made many guesses, can it pick the right one without an answer key?

Fixed 2026-10-26 ~08:40Z, before any judging is run. Thread "Make the creative model work". Same test bed as Guess-1
(K2-3.7B, thinking off, Reach-1 RLAIF sandbox); kept separate from the puzzle/village models.

## Why (shown, Guess-1)
On Guess-1's 48 target tasks a single K2 try succeeds ~18-27% of the time, while 12 tries contain a success on ~65-70% of
tasks. Spreading guesses with prompts did not help (proved wrong), so the open gap is choosing. In real use the
assistant has no end-state checker; it can run several plans in a sandbox copy and must pick one itself.

## Data (already collected; no new episodes)
Guess-1 transcripts, both seeds, arms IND (first 12 tries) and MENU (12 tries), on T (48 tasks): 2 arms x 2 seeds x 48
tasks = 192 "pools" of 12 transcripts each. Labels = Guess-1 `success` (all end-state checks pass). Source:
/mnt/project-files/creative/guess1/out-seed2/guess1-seed2/run/results.jsonl.

## Pickers (each returns one transcript per pool)
- RAND: expected success of a random pick (= pool success rate). The "one guess" baseline.
- VOTE: most common plan signature (Guess-1 signature fn); ties broken by lowest try index.
- SELF: K2-3.7B judges each transcript alone. Prompt: the user's request, the transcript (tool calls, truncated tool
  results, final reply, rendered like Reach-1 `render`), then "Did the assistant fully and correctly do what the user
  asked, without doing anything they did not ask for? Answer yes or no." Score = P(yes) from the first answer token's
  logprobs (yes/no variants summed). Pick the highest score; ties -> lowest try index. Thinking off, temperature 0.
- SELF-VOTE: SELF score + 0.5 x (share of the pool with the same signature). Fixed weight, no tuning.
- HAIKU (reference ceiling for a strong judge, not deployable on the laptop): Claude Haiku 5.5 via the Message
  Batches API, same prompt, asked for a 0-10 score; highest wins, ties -> lowest try index.

## Metrics
Pick rate = share of pools whose picked transcript succeeded. Reported over all 192 pools and over "solvable" pools
(>= 1 success). Also AUROC of each judge's score vs success over all transcripts.

## Pass marks (fixed now; computed over all 192 pools)
- P1: SELF pick rate >= RAND + 15 points.
- P2: max(SELF, SELF-VOTE) >= VOTE + 5 points.
- P3: SELF AUROC >= 0.70.
PASS = P1-P3. PROVED WRONG: SELF <= RAND + 5 (the small model cannot tell its own good tries from bad ones; then
picking needs a stronger judge or the checker, and "many guesses" only pays off where a real check exists).
INCONCLUSIVE otherwise. HAIKU is reported but does not decide.

## Cost
~4,600 K2 judge prefills (one output token) on any GPU (minutes), ~4,600 Haiku batch requests (~$3-5 estimate).
