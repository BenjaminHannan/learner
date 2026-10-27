# Lead 0 pass marks: can the plain LFM talker retell a checked grid exactly?
Written 2026-09-28 21:5x UTC (`date -u` 21:51 at script selftest), BEFORE any model run. Never edited after a score is seen.

Change under test: none (read-only). Plain LFM2.5-1.2B-Instruct @0f604ada, no adapter, greedy, max 160 new tokens, thinking off, the 0.2d talker input (claude_e2e02d.system_text with the H1 note `reasoner_note`).
Items: code-made squares, sizes 5/6/7 split 34/33/33, grid seeds 1 and 2 (100 items each). The note holds the code-made true solution.
Score (code only): the last size x size run of numbers in the reply (`claude_rsn358b3_panel.final_grid`) equals the note's grid cell for cell. Count "x of 100".

## Marks
- **PASS (no fix needed, "shown"):** arm R exact >= 95 of 100 on seed 1 AND on seed 2.
- **FAIL (fix owed):** arm R exact < 95 of 100 on either seed. Fail branch: a small copy-trained talker adapter on code-made note-to-reply rows (Luna-worded replies), judged by this same test on fresh grid seeds. No rule-based patch.
- Reading: both seeds must clear the bar (the "every seed" rule); one seed under 95 is FAIL, not "not shown". A 90-94 result is reported as a narrow FAIL with its failure modes counted.
- Result that proves the "plain talker is fine" claim wrong: any seed at 94 of 100 or lower.

## Controls (reported, not gating)
- Arm N (no note, puzzle only): if N exact is high, R would not show copying, only solving. Expected near 0 (358b2: the 1B alone solved 0 of 300). If N >= 20 of 100 the R result is flagged as not a clean copy test.
- Failure modes counted for R misses: no grid, wrong grid that still solves the puzzle, wrong grid, cut off at 160 tokens.

## Marks self-check (H8 list)
1. Noise: decoding is greedy and deterministic, so the only spread is which 100 grids; the two seeds measure it. The bar (95) is a fixed threshold from H4/standing-05, not a gain over a baseline; no gain is claimed.
2. "Every seed" reading: yes, both seeds must clear 95 for PASS.
3. Comparator: not a comparison. Baseline evidence: 358b2's plain 1B copy from the message text was 25/39/28 of 100 (a different task: copying a puzzle out of chat, not retelling a note).
4. Plain-net control: N arm above. A plain same-size net is the thing under test, so a "plain-net cannot pass" row does not apply; this test asks whether the plain one already passes.
5. F_few: not applicable (no learning or examples).
6. Sleep gates: not applicable.
Small-card experiments and the village model are not used.
