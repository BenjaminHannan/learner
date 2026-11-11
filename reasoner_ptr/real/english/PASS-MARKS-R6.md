# English, 12 practised kinds instead of 6: pass marks (fixed 2026-10-04 before any training run)

Ask: coordinator relay 14:36 UTC 10-04 (Ben: "start now"). Practise 12 kinds of question instead of 6 to push the score on never-practised kinds past 80%. Round 5 scored 79.9% against the bare 8-shot model's 67.7%. Fast lane, 6 or more paired seeds, cap about $6.

## Two runs per seed (seeds 0 to 5)
Both runs use allptr, `--gen 8000`, 2000 updates of 16 rows and `--block-r6`.

- **six:** the six round-4 kinds (`--kinds 6`).
- **twelve:** the same six plus six more generated kinds: owner_possession, agent_action, companion_with, feeling_state, naming and activity_place (`--kinds 12`).
- **Total size is the same:** 8000 generated examples in both runs, so the twelve run has half as many examples per kind.
- **The one change** is the number of practised kinds.
- **`--block-r6`** keeps every name and answer word of both unseen-kinds test sets out of the generator, in both runs. This also changes the six run's word pools slightly from round 5, which is why the six run is rerun here rather than reused.

## Test sets
- **NEW-KINDS-R5.json** (sha256 eafb2a556ba8…): 192 questions, already scored once in round 5. It covers counting, location, cause, time, attribute and instrument.
- **NEW-KINDS2-R6.json** (sha256 a3b8ec7baddb…): new for this round, written by a helper agent and checked by script. It covers speech, weather, price, direction, duration and origin, with 192 questions.
- None of the 12 practised kinds is one of these 12 test kinds. The runner asserts that no generated text equals a test text.
- **FRESH-EN-R3.json:** the six old kinds, as before.

## Bar
lm_fewshot is the bare 1.2B model shown the same 8 bank examples, run once (deterministic). Its exact accuracy on NEW-KINDS-R5 is 67.7%.

## Judged A: twelve − six on NEW-KINDS-R5, exact accuracy, paired by seed
- **PASS:** a mean of at least +5 points, with the 95% t-interval's lower bound above 0 (df 5, t = 2.571).
- **FALSIFIED:** a mean below +1.
- **In between:** anything else.

## Judged B, the goal: twelve on NEW-KINDS-R5
- **REACHED:** a mean of at least 80.0%, and the lower bound of the interval of (seed score − 67.7) above 0.
- **NOT REACHED:** otherwise.

## Read, not judged
- **The cleaner check:** Judged A's comparison and the bar comparison repeated on NEW-KINDS2-R6. This set had never been scored before this round.
- twelve − six on FRESH-EN-R3, to see whether spreading practice thinner costs the old kinds.
- Per-kind accuracy.
- "contains" accuracy.
- The zero-pool core lesion.
