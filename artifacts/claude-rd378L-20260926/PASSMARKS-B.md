# rd-378L addendum B: same turn budget for both stores (registered 2026-09-26 ~12:35 UTC, before 007g ran)

Why: Benchmarks pointed out (via the coordinator, 12:27 UTC) that a note counts as one item but credits every turn it
cites (up to 7), so store B's top 10 items can cover more turns than store A's, and L1 could pass just from showing more
turns. Checked in the code (scripts/claude_rd378L_recall.py, score): true.

Change to the script (before any note was written): it also reports, per mode and k,
- turns@k: distinct turns covered by the top k items (summed over questions; mean = turns@k / questions);
- anyT@k: an evidence turn is among the first k DISTINCT turns reached by walking the ranked items in order (a note's
  cited turns taken from its own turn backwards). For store A, anyT@k = any@k.
Recall depth is raised from 20 to 60 items so the turn budget can always be filled. any@k / all@k are unchanged.
SEAL.sha256.txt covered the script before this change; SEAL-B.sha256.txt covers the script now in use.

## Added mark (fused mode, questions of categories 1-4)
| Mark | Bar |
|---|---|
| L3 | B anyT@10 >= A anyT@10 + 5 points (same 10-turn budget) |
PASS now = L1 and L2 and L3. If L1 passes but L3 fails, the result reads "notes widen what is shown", not "notes help
search". The proved-wrong clause is unchanged (B any@10 <= A + 1 point) and is also reported for anyT@10.
Report only: mean turns@10 for A and B.
