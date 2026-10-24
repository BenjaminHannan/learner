# Aha-2: prefer the simplest rule (pre-registration, 2026-10-24 ~12:35Z)

Small puzzle model only (Qwen3.5-0.8B program puzzles). Follows Aha-1 (`RESULTS-aha1.md`, FAIL): hiding one example let
threshold cheats such as `x if x < 23 else 4` through (14 of 16 wrong answers).

**One change from arm aha (flag `--shortest`, run with `--aha --shortest`):** among the C16 samples that fit all 3 examples,
answer with the one that has the fewest AST nodes, not the first one. For sleep data, keep the 2 shortest fitting programs per
pool puzzle (1 per dream), not the first ones. Everything else is identical to Aha-1's aha arm (same PC, seed 0).
Known risk: a verbose correct rule (`int(str(x)[-1])`, 17 nodes) loses to a shorter cheat (13 nodes); `x % 10` is 9.

## Marks (fixed now), C2 dev, post-sleep C16, compared with Aha-1's PC run
- P1: acc >= 72.2 (nb 74.2 - 2).
- P2: precision among answered >= 95%.
- **Wrong if** precision <= 91.3 (aha's), i.e. preferring short rules does nothing to the cheats.
- Reported: branching answers and their precision, by kind, HARD, sleep pairs with a branch.
Compute: Ben's PC, ~25 min, $0. Seed 0 only; nb's two runs differed by ~7 points, so a P1 near the line is not conclusive.
