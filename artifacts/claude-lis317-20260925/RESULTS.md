# lis-317 results (REPORT ONLY, DEV data): the reader misreads chat; a sampling gate does not help

Thread "Fix: reading facts from chat", verified 02:09 UTC 2026-09-25 from the builder's files (RESULTS-rent.md,
reads_*.jsonl on builder-outbox; one rental, $0.68). Recounted on CPU with scripts/claude_lis317_score.py and
scripts/claude_lis317_gates.py; the scorer line matches the builder's score_e2edev.txt.

## Verdict
- Before any gate the lis-301 reader finds 89 of 131 DEV chat facts (68%), with owner and value right and a saving mode.
  PLAN rule band 60-80%: "both; the gate first".
- The gate-first half is answered already: the agreement gate (same fact in >= a of 8 samples) fails the selection rule
  fixed in PLAN.md. On lis-301 dev no agreement level gets down to the live gate's 2 wrong turns (8/8 still has 5).
  The reader repeats its mistakes as confidently as its right reads.
- So the reader itself is the lever: lis-318 = train it on chatty turns (one change).

## Counts
- DEV, 131 gold facts: 89 found (82 pass the live structural check, 7 blocked as relation not in the table), 42 not found.
  At the live gate (min token prob >= 0.995): 20 saved, 0 wrong.
- Writable facts in greedy reads that match no gold fact: 52 across all 194 turns (teach 27, ask 11, correct 6,
  smalltalk 5, creative 3). Of those that pass the structural check, 21 (20 turns). Some are true but unlabelled
  (e.g. a tortoise's age); many are real misreads: a smalltalk line read as "your father is monday energy", two
  corrections saved with the OLD value as ASSERT, a question word read as a value.
- Not found (42): relation-table gaps (species, breed, interest), "our X" read as owner "we" (Ben's our/we ruling),
  pronouns pointing to earlier user turns, asides and lists dropped ("kids are Teddy, he's 9, and Vada").

## Gate table (right / wrong facts / wrong turns, per-fact release)
```
[lis] gold writable facts 771; structurally writable greedy facts 753
gate                       right  wrong_facts  wrong_turns
min >= 0.0                    743           10           10
min >= 0.9                    702            5            5
min >= 0.98                   631            2            2
min >= 0.99                   594            2            2
min >= 0.995                  535            2            2
min >= 0.999                  343            1            1
agree >= 0/8                 743           10           10
agree >= 1/8                 743           10           10
agree >= 2/8                 743           10           10
agree >= 3/8                 743            8            8
agree >= 4/8                 743            8            8
agree >= 5/8                 740            8            8
agree >= 6/8                 738            8            8
agree >= 7/8                 731            5            5
agree >= 8/8                 706            5            5
agree >= 5/8 & min >= 0.9     701            5            5
agree >= 5/8 & min >= 0.98    630            2            2
agree >= 6/8 & min >= 0.9     701            5            5
agree >= 6/8 & min >= 0.98    630            2            2
agree >= 7/8 & min >= 0.9     699            4            4
agree >= 7/8 & min >= 0.98    630            2            2
agree >= 8/8 & min >= 0.9     676            4            4
agree >= 8/8 & min >= 0.98    619            2            2

[e2e] gold writable facts 131; structurally writable greedy facts 103
gate                       right  wrong_facts  wrong_turns
min >= 0.0                     82           21           20
min >= 0.9                     50            3            3
min >= 0.98                    32            1            1
min >= 0.99                    28            1            1
min >= 0.995                   20            0            0
min >= 0.999                    8            0            0
agree >= 0/8                  82           21           20
agree >= 1/8                  82           20           20
agree >= 2/8                  82           19           19
agree >= 3/8                  81           17           17
agree >= 4/8                  81           16           16
agree >= 5/8                  79           14           14
agree >= 6/8                  75            9            9
agree >= 7/8                  72            6            6
agree >= 8/8                  63            4            4
agree >= 5/8 & min >= 0.9      49            2            2
agree >= 5/8 & min >= 0.98     32            1            1
agree >= 6/8 & min >= 0.9      49            2            2
agree >= 6/8 & min >= 0.98     32            1            1
agree >= 7/8 & min >= 0.9      48            2            2
agree >= 7/8 & min >= 0.98     31            1            1
agree >= 8/8 & min >= 0.9      41            2            2
agree >= 8/8 & min >= 0.98     29            1            1
```
