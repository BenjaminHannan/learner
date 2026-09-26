Your evaluation build is underway — sealing code and verifying checkpoints before running.
Core specs are loaded. Now I'll track down the remaining rules and the prior run's checkpoints.
Checkpoint directories found locally. Now verifying their hashes against the seal.
The prior run's notes mention a Mac-side checkpoint copy. Checking for it.
Hand-copied strings are error-prone — re-verifying straight from the files.
Seal verified 7/7 OK. Now the smoke test.
Seed 1 finished cleanly. Running seed 2.
Both seeds complete. Now scoring the marks.
All marks computed. Checking the ledger format before writing results.
Writing the results file now.
VERDICT: FAIL (overall). Stop fix: NOT NEEDED — the v2 stop never fell 10+ below the fixed budget on any graded family on either seed, so K2 is vacuous both seeds and there was nothing for the answer-cell rule to recover. K1 FAIL (both seeds), K3 FAIL (both seeds), K4 PASS seed 1 / FAIL seed 2, V MET both seeds. "Proved wrong" did NOT trigger. 358a's registered FAIL stands.

MARKS TABLE (n=300 per check set; graded families only):

| mark | seed 1 | seed 2 |
|---|---|---|
| V (plain & loop-fixed each ≥210 on sums4, grids5) | MET: sums4 300/300, grids5 255/256 | MET: sums4 300/300, grids5 253/262 |
| K1 (ans ≥ fixed−3, all five) | FAIL: sums6 247 vs 252, miss by 5 (rest hold) | FAIL: sums6 221 vs 232 miss by 11; grids6 254 vs 255 miss by 1 (rest hold) |
| K2 (recover ≥half the gap where fixed−v2 ≥10) | NOT NEEDED (gaps 0/−1/4/−1/0) | NOT NEEDED (gaps 0/0/3/4/0) |
| K3 (ans ≥ v2−3, all five) | FAIL: sums6 247 vs 248, miss by 1 (rest hold) | FAIL: sums6 221 vs 229, miss by 8 (rest hold) |
| K4 (loop−plain: +30 on 2 of sums6/grids6/numbers5, ≥−10 third; ≥−10 practised) | PASS: sums6 +45 (247−202), grids6 +63 (261−198), numbers5 0; practised 0/+2 | FAIL: sums6 −38 (221−259) breaks floor; grids6 +78, numbers5 0; practised 0/+9 |

Key per-family counts (budget / fixed / v2 / ans / plain / mean-rounds v2,ans / any): s1 sums6 8/255/251/247/202/8.56,3.55/276; s1 grids6 12/260/261/261/198/10.82,9.51/261; s2 sums6 8/235/232/221/259/7.92,3.52/264; s2 grids6 24/258/254/254/176/11.12,9.02/260; numbers5 both seeds 0/0/0 everywhere (any-round best 1 on s1, 0 on s2). Full tables in artifacts/claude-rsn358c-20260926/RESULTS-c1.md.

EVERY MOVE: (1) Precondition: all 4 final.pt present at ~/premonition-models/rsn358a/<run>/; loop-s1, plain-s1, loop-s2 sha256 exact MATCH; plain-s2 accepted per typo rule (recorded 65 chars, doubled "a"; deleting index 35/36 gives real hash 2400fc1f…9583 exactly). READY, not NOT-READY. (2) SEAL: git-archive extract of origin/main, `shasum -a 256 -c SEAL-c1.sha256.txt` → 7/7 OK; smoke → "smoke ok". (3) RUN: sealed script exactly once per seed from the extract (required uv offline py3.12 command), exit 0 both; s1 00:02:45Z, s2 00:04:48Z (~2 min each); 7-line logs kept verbatim in runs/stop358c1-s<N>.log + JSONs (3791/3802 bytes). (4) Wrote new RESULTS-c1.md (verdict first); appended 6 ledger lines via cat >>. (5) Committed pathspec-only as b588f1e37 (5 new files + ledger, 707 insertions). TEST-ONLY tests/ never opened, printed, tuned on, or quoted; fresh pick/check sets only. Disk 9 GB free (≥3 GB rule); single process, well under the 4-process cap.

EVERY MISS: s1 sums6 ans−fixed −8, ans−v2 −4 (K1 by 5, K3 by 1); s2 sums6 ans−fixed −14, ans−v2 −11 (K1 by 11, K3 by 8; loop−plain −38); s2 grids6 ans−fixed −4 (K1 by 1; v2 also 254); numbers5 0/300 both arms both seeds (says nothing); report-only s2 sums8 plain 140 beats all loop measures, s2 sums8/sums6 plain sweeps match 358a's seed-2 pattern.

DEVIATIONS (6, all in RESULTS-c1.md): D1 OPUS-RULES.txt path nonexistent (empty scratchpad) → followed task text. D2 Mac checkpoint path instead of Windows C:/ path (hashes verified). D3 plain-s2 65-char typo, real hash recorded. D4 Mac CPU, no GPU on this machine (eval-only). D5 `shasum -a 256 -c` instead of missing `sha256sum`. D6 ran from /tmp git-archive extract (sealed files absent from this checkout); worktree otherwise untouched. EXTRA D7 (blocking): `git push` is denied by this environment's permission rules, so the PUSH step is NOT done — commit b588f1e37 is ready locally on branch claude/card-experiment-handoff-7c5b27 and needs one manual `git push origin HEAD:claude/card-experiment-handoff-7c5b27` from this worktree. Also note the ledger commit necessarily includes 77 previously co-staged sibling-agent lines plus my 6.

WHAT IT MEANS (plain high-school English): the old stop was already within 4 answers of the best fixed budget everywhere, so this test never got a real chance to show the fix working. Where the new stop differed, it quit much earlier (about 3–11 rounds vs 7–14) and lost answers on bigger sums both times. The loop still crushes plain on bigger grids (+63, +78) but loses bigger sums on seed 2 (−38), so the bar fails the same way 358a did. Numbers puzzles: nobody learned anything (0/300). WHAT IT DOESN'T MEAN: the idea is NOT disproved (proved-wrong clause quiet; K2 never had a case); v2 is NOT proven good (all 48 rounds still computed, no savings measured); 358a's FAIL is unchanged; nothing is claimed about harder puzzles or equal-compute comparisons.
