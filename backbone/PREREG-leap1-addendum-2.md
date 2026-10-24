# Leap-1 addendum 2 (2026-10-24 ~02:40Z): a creative that is not just "the worker with more tries"

Written after seeing one result (LEAPU seed 0: 12.5 -> 20.8 after round 1, then 21.7, 21.8, 22.0, 22.7) and
before any SELF or LEAP result. LEAPU's explorer is the same 0.8B with more samples; on depth >= 3 pool puzzles it
verified only 5-19 of ~167 per round, and repair added 5-20 pairs out of ~800 tries. So the creative barely pushes
past the worker (suggested reading). Ben's idea needs a creative that can go where the worker can't.

New arm, one change from LEAP:
- LEAPS (leapfrog with a search creative): LEAP's explorer plus premonition's creative program search: enumerate
  every chain of 1-3 steps over the same 8 primitives and constants (add/sub 1-9, mul/fdiv 2-5, mod 2-9), run it on
  the puzzle's 3 examples, and keep the shortest chains that reproduce them (max 2 per puzzle). Chains whose step
  sequence is a held-out EVAL/DEV signature are never used (no leak of held-out rule forms). The kept pair is
  (puzzle prompt -> the chain written as a canonical lambda), plus any LLM-verified programs as in LEAP.
  Same frontier pool, rounds, sleep and scoring as LEAP.
Marks (fixed now, both seeds unless stated):
- L6: LEAPS round-5 mean >= LEAP round-5 mean + 5 points, and >= SELF + 8.
- L7 climb: LEAPS rises >= 1 point in at least 3 of rounds 2-5 (keeps climbing, not one jump).
**Wrong if** LEAPS round 5 <= LEAP round 5 + 2 (a stronger creative does not help the worker learn), or
LEAPS depth 4-6 accuracy after round 5 <= its round 1 (the worker cannot absorb what the search found).
