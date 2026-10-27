# Addendum 1 to 02 and 03 (Director, 2026-09-28 21:19 UTC)

Ben supplies the questions himself (not the uncle). Read "uncle" in 02 and 03 as "Ben"; the uncle's judging role becomes Ben's, or is dropped. Nothing uncle-specific is built. These new rules add to 02 and 03; the files themselves are unchanged.

1. **Who runs scoring.** Ben, or a non-Claude runner he starts. Answers restate the questions, so no Claude thread runs it or reads the answers. Claude threads receive only counts ("x of N").
2. **Second judge.** A non-Claude judge (GPT or GLM) may see the raw text, but only after Ben's privacy pass, and only after Ben names its provider. This is the one thing to bring to Ben, when scoring is near. Until then no text goes to any judge.
3. **Pass mark (replaces the pass line in 03).** PASS = the joined model's helpful count is within 3 of the best rival's, AND its wrong-or-made-up count is no higher than the best rival's, AND Ben marks "would use" for at least 10 of 30. A bigger gap in either direction is "suggested" unless at least 6 of 30 in the same direction for both judges, then "shown".
4. **Script check.** Before the real seal, run scripts/claude_dir_uncle_seal.py on a dummy file, then change one byte and run --verify: it must FAIL. Log both runs.
5. **Order.** Item 8 is scored only after item 1's joined model exists.
