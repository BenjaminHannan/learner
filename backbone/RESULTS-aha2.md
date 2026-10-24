# Aha-2 results (prereg `PREREG-aha2.md`; BensPC 13:04-13:26Z, seed 0, $0): FAIL, not wrong
Raw JSON `results/aha2/result_sleep.json` (sha256 prefix 656bad83).

| arm (C2 dev, post-sleep C16) | acc | answered | precision | branch answers (right) |
|---|---|---|---|---|
| nb ban (Aha-1 run) | 74.2 | 75.0 | 99.0 | 0 |
| aha (Aha-1) | 65.2 | 71.5 | 91.3 | 16 (2) |
| **aha + shortest** | **69.1** | 74.2 | **93.2** | 12 (1) |

By kind: affine 67, double_add 67, last_digit 43, sq_plus 69, square 100. HARD C16 17.3 (prec 74.3), F1 41.4.
Sleep pairs with a branch: 36 pool + 23 dream (aha: 38 + 23).

- P1 FAIL (69.1 < 72.2). P2 FAIL (93.2 < 95). Not "wrong" (93.2 > 91.3): shortest helps a little, within run spread.
- 11 of 13 wrong answers are still branch programs. Non-branch answers are 176/178 right (98.9%).
- The cheat `x if x < 23 else 4` (13 nodes) wins because Qwen never wrote `x % 10` (9 nodes) for that puzzle:
  "simplest" can only choose among what the proposer produced.

Conclusion for the creative loop: on these 3-example puzzles, neither hiding an example nor preferring short rules matches the
plain branch ban. Keep the ban as the default checker; a general replacement needs more examples per puzzle (more to hide)
or a proposer that writes the true short rule more often. Next brain test runs on top of the ban.
