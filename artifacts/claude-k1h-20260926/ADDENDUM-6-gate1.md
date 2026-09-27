# k1h ADDENDUM 6: gate 1 stops counting list numbers as sentences (Creative answers in chat thread, sealed 2026-09-27 05:52 UTC)

This is the sealed version of ADDENDUM-6-gate1-DRAFT.md (d89b0c6df), which stays on file as it was. The Thread
manager approved it at 05:52 UTC as a fix to how sentences are split, not a change to the bar, with three conditions
that are written in below. Registered FAILs stay FAILs.

## Where and when it was found
- It was found on the Luna pilot's 40 practice answers (luna/pilot-score/RESULT.md), where gate 1 was report only
  (ADDENDUM-5).
- That was before gate 1 had run on any full data set. The full Luna run (handoff/queue/k1h-luna-full-mac.md) had not
  started when this was sealed. No full-run answer has been read.

## The bug
- The sealed gate 1 (claude_k1h_train.gate1, test-hygiene rule 1) fails if any sentence appears in more than 2% of the
  kept answers. It finds sentences by splitting at ". ", "! " and "? ".
- A numbered list ("1. Make a card. 2. Bake a cake.") therefore yields the "sentences" "1.", "2." and "3.".
- Luna pilot, 39 kept answers: "1." is in 14 of them (bar: 1). Counting only pieces that contain a letter, the top
  sentence is in 1 of 39.
- GLM's 240 k1e answers (kept on file, not trained on; check run here, report only): 225 kept, and "2." is in 72 of
  them (bar: 4.5). Counting only pieces that contain a letter, the top sentence is in 3 of 225.
- So the sealed gate fails any teacher that numbers its ideas, and the GLM plan would have failed it too.

## The change (scripts/claude_k1h_gate1b.py, sha256 180b7303cadb0b291b2f57b64ea15bd9e9b3088f851dd9590366efb4890d47bb, selftest "k1h gate1b selftest 1/1 ok")
- A piece counts as a sentence only if it contains a letter (a to z, after lowercasing).
- Everything else is claude_k1h_train's, unchanged: the splitter, the openings rule, both bars (25% and 2%), and the
  input (check's kept.jsonl).
- Gate 1b decides gate 1.
- On the full data, the sealed gate 1's result (as printed by check) is reported next to gate 1b's, report only (the
  Thread manager's condition 2).
- `--by-writer` gives the split by chat writer (report only).
- The selftest keeps the case that a repeated real sentence ("Happy birthday, Wren!" in 3 of 3 answers) still fails
  (the Thread manager's condition 3).

## What does not change
The teacher (ADDENDUM-5), gates 2 and 3, the size floor, the recipe, the arms, the panel, the marks and the scope.
