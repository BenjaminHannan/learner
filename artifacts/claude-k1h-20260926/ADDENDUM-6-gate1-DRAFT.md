# k1h ADDENDUM 6 (DRAFT, not sealed): gate 1 stops counting list numbers as sentences (Creative answers in chat thread, drafted 2026-09-27 05:49 UTC)

DRAFT for the Thread manager's review. Nothing is sealed or run with it yet. The full Luna run has not started, and
gate 1 has not been run on any full data set.

## What the Luna pilot showed (gate 1 was report only there, ADDENDUM-5)
- The sealed gate 1 (claude_k1h_train.gate1, test-hygiene rule 1) fails if any sentence appears in more than 2% of the
  kept answers. It finds sentences by splitting at ". ", "! " and "? ".
- A numbered list ("1. Make a card. 2. Bake a cake.") therefore yields the "sentences" "1.", "2." and "3.".
- Luna pilot, 39 kept answers: the top "sentence" is "1.", in 14 of them (bar: 1). Then "3." in 12 and "2." in 11.
  Counting only pieces that contain a letter, the most repeated sentence appears in 1 of 39.
- Checked on GLM's 240 k1e answers too (kept on file, not trained on; check run here, report only): 225 kept, and "2."
  is in 72 of them (bar: 4.5). Counting only pieces that contain a letter, the top sentence is in 3 of 225.
- So the sealed gate fails any teacher that numbers its ideas, and the GLM plan would have failed it too. The failure
  is in the measurement, not in the answers. Repeated frames are what the rule exists to catch, and these are not
  frames.

## The change (scripts/claude_k1h_gate1b.py, selftest 1/1)
- A piece counts as a sentence only if it contains a letter (a to z, after lowercasing).
- Everything else is claude_k1h_train's, unchanged: the splitter, the openings rule, both bars (25% and 2%), and the
  input (check's kept.jsonl).
- Gate 1b decides gate 1. Check's own gate 1 line is still printed and reported beside it.
- With `--by-writer` it gives the split by chat writer that the Thread manager asked for (report only).
- Result on the two sets above: Luna pilot top opening share 0.051, top sentence 1 of 39 (pass); GLM 240 top opening
  share 0.058, top sentence 3 of 225 (pass).

## What would show this rule is too loose
A frame made of words still counts under 1b. A phrase that appears in more than 2% of the answers, such as "Happy
birthday!", still fails (see the selftest). Only pieces with no letter at all are skipped.

## What does not change
The teacher (ADDENDUM-5), the pilot marks, gates 2 and 3, the size floor, the recipe, the arms, the panel, the marks
and the scope. Registered FAILs stay FAILs.
