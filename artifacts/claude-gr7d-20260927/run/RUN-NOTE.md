# gr-7d run note (practice only; PLAN-gr7d.md)

- A correction: PLAN-gr7d.md's first line says "written 2026-09-27 07:46 UTC". That time was typed, not taken from
  `date -u`, and it is wrong. The plan, code, chain and practice set were committed in a017d5143 at
  2026-09-27T07:43:33Z (git commit time), 9 seconds before the chain's first STEP line. The sealed plan is not edited.
- First STEP line: STEP start 2026-09-27T07:43:42Z (from `date -u` inside chain.sh). Seals, adapter shas and both
  selftests passed; L7 on the lookalikes started at 07:43:42Z.
- Chain PID 26197 (bash artifacts/claude-gr7d-20260927/cpu/chain.sh), launched once, on this container's CPU (4
  threads), $0.
- 2026-09-27T07:44:45Z: running.
- 2026-09-27T08:45:38Z: L7 finished the lookalikes (150 rows, 6 read as a square), the squares (200, 200 read as a square) and the unseen formats (200, 195 read as a square); G5 finished the lookalikes (150, 6 read as a square). G5 on the squares started at 08:40:30Z. Exactness and kinds are left to the count and the recount.
- 2026-09-27T09:28:03Z: G5 finished the squares (200, 200 read as a square) and the unseen formats (200, 193 read as a square). The count ran at 09:27:19Z and the chain ended (STEP done 09:27:19Z), 1 h 44 min after the first STEP. Every task was launched once. Count: run/logs/count.log. A separate agent's recount is next.
