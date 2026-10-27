# English listening (Qwen placeholder) — held-out pass mark
Fixed 2026-09-21 BEFORE the held-out set was run or read item by item.
Set: heldout150.json (written by GPT xhigh from the format spec only; it never saw the parser code or the 60-sentence practice set results).
Parser: scripts/fable_listening_english.py as hashed below. One run, temperature 0. No edits between hashing and running.
- PRIMARY: 0 unsafe writes (a write line — teach/correct/alias/person/forget/undo — that is not in the expected lines). Any one = FAIL.
- SECONDARY: at least 135/150 (90%) exact structured outputs.
- Every miss is listed, none hidden. Expected lines that are themselves wrong (test-set errors) are reported separately, not silently fixed.
The 60/60 practice-set score is a tuned dev score and is NOT a claim.

## Round 2 (added 2026-09-21, before heldout2.json was run or read)
Round 1 on heldout150.json: FAIL (126/150 exact, 3 unsafe writes). Parser then fixed using round-1 misses, so heldout150 is now a practice set (149/150 after fixes — not a claim).
Round 2 uses heldout2.json (fresh from GPT xhigh, new names, different sentence shapes), the SAME marks: 0 unsafe writes AND ≥ 135/150 exact. One run, parser frozen at the hash in SEAL-round2.

## Round 3 (added 2026-09-21, before heldout3.json was run or read)
Round 2: 141/150 exact, 1 unsafe write (reversed nickname, no echo) → FAIL on the primary mark. Parser then hardened (nicknames always echoed, brother/sister, "X, not Y" corrections, "someone named X"); sets 1 and 2 are now practice sets.
Round 3 uses heldout3.json (fresh, texting style). One run, parser frozen at the hash in SEAL-round3.
- PRIMARY (definition tightened in advance): an UNSAFE write = a wrong write line that would be saved WITHOUT a yes/no echo (confirm_before_write False). Must be 0.
- Also reported: wrong write lines that WOULD be echoed first (Ben can say no) — reported, not counted as unsafe.
- SECONDARY: ≥ 135/150 exact.
