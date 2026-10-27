# gram-361 pass marks (grammar thread, registered 2026-09-25 before any run on chatpanel361)

## Question
After gram-360 the 1B's own replies are the largest source of grammar misses (VERIFY-360.md). Does sampling the
1B's chat replies at temperature 0.3 instead of 0.7 make them clean, without making them less helpful?

## The one change
The chat338b layer samples at temperature 0.3 (its own Gen338 sharing the loaded 1B; top_p 0.9, 4 samples,
200 tokens, 338/338b guards and history unchanged). 333d creative stays at 0.7. Code: scripts/claude_gram361.py
(build_361 for the joined agent; run_chat_component for this test).

## DEV basis (report only)
54 DEV turns (smalltalk, creative, nosave), SYSTEM338, one sample each, two blind graders: 0.7 44/54 and 41/54
clean; 0.3 54/54 and 53/54; greedy 47/54 and 45/54.

## Test
chatpanel361 (artifacts/claude-chatpanel361-20260925, sealed): 12 conversations, 110 user messages (smalltalk 25,
feelings 20, advice 25, explain 20, followup 20), written blind by a separate agent that never saw any code
(names K to O). Component test on CPU (no reader, no GPU): 338b's chat layer on a stub agent that always gives up,
so the 1B answers every turn under the real guards and 12-message history. Arms t07 (today) and t03 (the change),
same seeds per turn (3610 + 100 x conversation + turn).
  python -B scripts/claude_gram361.py --panel <panel>/turns.jsonl --gen-model <MiniCPM5-1B 87179e5c> \
      --temperature {0.7,0.3} --out <run>/arm_{t07,t03}.jsonl --tmp <scratch>

## Grading and judging
scripts/claude_gram361_score.py prep: two blind Opus graders, each one shuffled file with both arms' distinct
replies + 336's 40 planted errors + 40 planted clean lines (seeds 3611, 3612); neutral question "Is this reply
grammatical, natural English with no simple mistakes (spelling, capitalisation, punctuation, agreement, word
order, missing or extra words, garbled or unnatural phrases)? Do not judge truth or helpfulness." A grader is valid
only with >= 36/40 planted errors caught and >= 36/40 clean kept. One blind Opus helpfulness judge sees each turn's
earlier user messages, the user message and the two replies in random order (seed 3613) and picks the more
natural and helpful reply for a friendly chat assistant, or "tie".

## Marks (fixed now)
| Mark | What | Bar |
|---|---|---|
| P361.1 | t03 replies graded clean, each grader | >= 97% |
| P361.2 | gain over t07 (t03 % minus t07 %), each grader | >= +8 points |
| P361.3 | helpfulness: t03 preferred or tied | >= 50% of turns |
| P361.4 | turns where every sample failed the guards (the give-up line stays) | t03 <= t07 + 3 |
| P361.5 | most common t03 reply | <= 5% of turns |

Proved wrong: if either valid grader gives t03 less than t07 + 3 points, sampling noise is not what makes the 1B's
replies ungrammatical.
Report only: invented person-facts are guarded by 338 G1-G4 in both arms (counts from the stats line); per-kind
clean counts; whether 0.3 changes reply length.
