# G-BASELINE (PROPOSED by the G builder; the Director writes and seals the real G-BASELINE.md, PASSMARKS "Entry")

Written 2026-09-28 (date -u at commit) from files only; no G score exists. Labels: SHOWN = read from a file.

- **Recipe G trains on:** the H2 wide pool (`scripts/claude_dir_h2_pool.py`: 36,782 practice pairs over 1,519 hands, 0 held-out hands), the runner default `--pool h2`. Entry rule met: H2's blind recount is WRONG-cannot-fit (`artifacts/claude-dir-h2-recount-20260928/RECOUNT.md`, SHOWN; subject to that file's own V3 caveat).
- **B_s (held-out numbers4 of 300, the one-stream loop on this recipe, from its own tests.json via RECOUNT.md):** seed 13 = 4, seed 14 = 4. (plain s13 = 6, plain s14 = 4, for the fair-comparator line; both give the same bar.)
- **F4 (SHOWN, `artifacts/claude-dir-g-build-20260928/f4.json`, `scripts/claude_dir_g_floor.py`):** 19.219 of 300 for this recipe (strategy B; A 9.269, C 16.757). Old-pool value 20.951 for reference.
- **Bars this gives (sealed rules, applied):** PASS-G on each primary seed needs S_pick >= max(30, 4 + 15) = 30, S_pick >= 2 x S_rand and S_pick > 19.219 (so 30 binds). WRONG needs S_any <= 4 + 8 = 12 on both seeds (note: 12 < F4, see ADDENDUM-1 reading notes). "Candidates fine, check not" needs S_any >= max(30, 19, 19.219 + 10) = 30.
