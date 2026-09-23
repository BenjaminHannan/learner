Publishing lis-300 results — verifying the sealed files.
All 8 result files are present. Now locating the dev-set files to copy.
Dev files copied with matching sizes. Now the seal check.
All hashes match. Final sanity counts and full file list.
Verdict: PUBLISH READY — lis-300 result files recovered without any re-run. All 8 expected files were already in the worktree, all 3 dev files copied from BensPC with byte- and hash-exact matches, and the seal verifies 3/3 when each line is checked where it resolves.

## Marks table (integer counts)

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| Expected result files present in `artifacts/claude-lis300-20260923/` | 8 of 8 | 8 of 8 (RESULTS.md, THRESHOLD.txt, SEAL-run.sha256.txt, dev_sweep.txt, panel_score.json, panel_score_T0.json, train_summary.json, train_log.jsonl) | PASS |
| Dev files copied to `dev/` (dev.jsonl, dev_rows.jsonl, dev_pred.jsonl) | 3 of 3 | 3 of 3, sizes match BensPC exactly | PASS |
| Copied dev files hash-match BensPC originals | 3 of 3 | 3 of 3 (sha256 identical) | PASS |
| Dev files line counts = 867-row dev set | 867 each | 867 / 867 / 867 | PASS |
| SEAL-run lines verify | 3 of 3 | 2 of 2 local OK on Mac + 1 of 1 weights OK on BensPC = 3 of 3 | PASS |
| Panel predictions / panel turns copied or opened | 0 | 0 | PASS |
| New runs launched | 0 | 0 | PASS |
| Existing files edited | 0 | 0 (only new `dev/` dir + 3 copies) | PASS |

## File list with byte sizes

Existing (untouched): RESULTS.md 5445, THRESHOLD.txt 1691, SEAL-run.sha256.txt 407, dev_sweep.txt 809, panel_score.json 520, panel_score_T0.json 557, train_summary.json 589, train_log.jsonl 22149.
New copies in `dev/`: dev.jsonl 567831, dev_rows.jsonl 85845, dev_pred.jsonl 328004. Total dir: 1013847 bytes.

## Every move

1. Read OPUS-RULES.txt in full first; checked `uptime` (load ~53, but no heavy steps needed) and `df -g /` (9 GB free, above the 3 GB floor).
2. Listed `artifacts/claude-lis300-20260923/` — all 8 files present, so no recovery copies needed for them.
3. Found the lis-300 work dir on BensPC (`C:\Users\benja\lis300\work\`): `data/dev.jsonl`, `dev_rows.jsonl`, `dev_pred.jsonl` present alongside panel files, which I did not touch.
4. Created `artifacts/claude-lis300-20260923/dev/` and scp-copied exactly the 3 dev files — no panel predictions, no `perfam/`/`persrc/` per-family panel breakdowns, nothing with panel turns.
5. Ran `shasum -a 256 -c SEAL-run.sha256.txt` from the worktree root: THRESHOLD.txt OK, dev_sweep.txt OK, third line (BensPC Windows weights path) not resolvable on Mac — expected, weights never in git.
6. Verified the third seal line where it resolves: `certutil -hashfile` on BensPC gives `112880d6…` for model.safetensors, exactly the SEAL value. Also hash-compared all 3 copied dev files against BensPC: identical.
7. Confirmed ledger already holds 6 P300 lines (builder's); appended nothing. No new files beyond the dev/ copies.

## Misses and deviations

- Misses: none. Zero files missing, zero mismatches.
- Deviation 1 (by design, not a fault): the SEAL's third line points at a BensPC-only Windows path, so `shasum -c` on the Mac reports 2 OK + 1 unreadable (exit 1). Resolved by hashing that file on BensPC itself: match. Full seal is effectively 3/3 OK.
- Deviation 2 (not mine, recorded): `artifacts/` is gitignored in this worktree (`.gitignore:5`), so the 8 existing files plus my 3 new copies do not appear in `git status`. The watcher must force-add the PUSH paths; I pushed nothing myself per instructions.

## What it means (plain high-school English)

- The lis-300 training result (a FAIL on recall: 71 of 137 facts at the sealed threshold) is now fully publishable: every result file exists, the seal checks out, and the dev data behind the threshold decision is archived next to it.
- Anyone reviewing this later can re-check the threshold call from the saved dev files without re-running the GPU training.

## What it doesn't mean

- It doesn't mean the model passed — the published verdict is still FAIL on P300.2 (51.8% recall vs the 85% bar). Publishing only saves the evidence; it changes no score.
- It doesn't mean the blind panel leaked: no panel file was opened, copied, or quoted — only dev-set files (867 rows) and category-level score JSONs.

PUSH: artifacts/claude-lis300-20260923 artifacts/fable-predictions-ledger.md
