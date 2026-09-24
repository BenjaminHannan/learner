Re-running the 8 lost evals on CPU — verifying seals and recounting from files.
Code and panel seals check out — now verifying the 8 checkpoints.
Checkpoints verified. Running the 16 evals in batches of 4.
All 16 evals done. Now extracting the totals for REEVAL.md.
**Verdict: RECOUNT DONE, 15 of 16 match — 1 real difference found.**

Marks table (checked_right integers; RESULTS.md = number printed on origin/builder-outbox):

| file | reeval checked_right | RESULTS.md | match? |
|---|---|---|---|
| plain-s1 / panel296 copy | 167 | 167 | yes |
| plain-s1 / panel296 final | 225 | 225 | yes |
| plain-s2 / panel296 copy | 181 | 181 | yes |
| plain-s2 / panel296 final | 217 | 217 | yes |
| loop-s1 / panel296 copy | 57 | 57 | yes |
| loop-s1 / panel296 final | 106 | 106 | yes |
| loop-s2 / panel296 copy | 47 | 47 | yes |
| loop-s2 / panel296 final | 101 | 101 | yes |
| plain-s1 / panel294 copy | **194** | **195** | **NO, off by 1** |
| plain-s1 / panel294 final | 238 | 238 | yes |
| plain-s2 / panel294 copy | 205 | 205 | yes |
| plain-s2 / panel294 final | 238 | 238 | yes |
| loop-s1 / panel294 copy | 59 | 59 | yes |
| loop-s1 / panel294 final | 89 | 89 | yes |
| loop-s2 / panel294 copy | 49 | 49 | yes |
| loop-s2 / panel294 final | 87 | 87 | yes |

Full total blocks are in `artifacts/claude-rsn296-20260924/reeval-cpu/REEVAL.md` (new file) plus the 16 JSONs. Extra totals for the record: the "invented answers" counts in RESULTS.md match my `raw_answered_without_fact` values exactly on all 8 finals (plain-s1 fresh 5, plain-s2 fresh 6, loop-s1 fresh 4, loop-s2 fresh 0, both plain transfers 0, loop-s1 transfer 2, loop-s2 transfer 1).

**Every move I made:**
1. Tried to read the OPUS-RULES.txt at the given scratchpad path — file is gone (empty scratchpad dir) and also not on origin/main. Worked from the rules pasted in the task instead.
2. `git fetch -q origin main` (+ builder-outbox); exported clean `origin/main` to /tmp/rsn296re; ran everything from there.
3. Seal checks on the export, all OK on every line: SEAL-code (6/6 incl. both run scripts), SEAL-v2 (panel296 items), SEAL-v3 (panel294 items).
4. All 8 local checkpoints match SEAL-run.sha256.txt exactly (8/8).
5. Ran all 16 evals exactly once each, `--device cpu`, max 4 at once, no code edits. Disk was fine (59 GB free).
6. Wrote 16 new JSONs + new REEVAL.md under `artifacts/claude-rsn296-20260924/reeval-cpu/`. Never edited or deleted any existing file. Never opened/printed any panel item; outputs hold category counts only.

**Every miss / deviation:**
1. THE difference: plain-s1 copy-only on the transfer panel recounts to checked_right = 194, not the printed 195 (raw_right = 195 in my run; 194+95 idk+11 wrong = 300, internally consistent). I report it as-is with no explanation.
2. `checked_answered_without_fact` does not exist as a key in ANY of the 16 total blocks, so I could not report it as an integer; I reported `raw_answered_without_fact` instead (absent in 5 files, noted in REEVAL.md).
3. OPUS-RULES.txt was missing (see move 1).
4. Note for the watcher: `artifacts/` is gitignored in this worktree (`.gitignore:5`), so the PUSH path `artifacts/claude-rsn296-20260924/reeval-cpu` (17 new files, all on disk, verified listed) will need a force-add — I did not push anything myself.

**What this means in plain English:** The lost rental numbers check out almost perfectly — rerunning the same tests on this Mac's CPU gives back the same scores in 15 of 16 cases, including every final-checkpoint score, so the pass/fail verdict in RESULTS.md is unaffected. What it doesn't mean: one copy-only transfer score came back 1 point lower (194 vs 195), and I can't say why — it's just a number that doesn't match, flagged for the director. PUSH: artifacts/claude-rsn296-20260924/reeval-cpu
