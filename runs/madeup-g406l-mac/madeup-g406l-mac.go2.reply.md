All steps verified complete — the previous agent finished 1–7 just before the cut-off; I re-checked every artifact rather than redoing any step (no duplicate ledger prediction: none exists for g406l, and I added none).

**VERDICT: partial** — pilot PASS, full run time-stopped at 220/240 usable packets, count verdict INCONCLUSIVE.

**First 13 lines of origin/main:handoff/queue/lis-302-gpu.md (followed, reported as ordered):**
1. COMMON RULES (the listener thread, Claude, wrote this task on 2026-09-23). You are a build/verification agent working in the git worktree .../card-experiment-handoff-7c5b27 (run every command from there).
2. First read .../scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
3. - Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
4. - Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
5. - Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
6. - TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
7. - Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
8. - Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
9. - You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
10. Your final reply: verdict first, then a marks table with integer counts, every move, every miss, deviations, and what it means / doesn't mean in plain high-school English.
11. BENSPC BUSY MARKER (Director 09-26): while a queue "GPU: yes" job runs, C:\Users\benja\GPU-BUSY.txt exists and names it. If that file exists, do not start anything on the GPU, whatever nvidia-smi shows.
12. (blank)
13. GETTING YOUR FILES: run git fetch -q origin main and read files with git show origin/main:<path> ... Builder outputs are on origin/builder-outbox ... Never check out, merge or push any branch yourself; the watcher pushes your PUSH paths.

(I also read OPUS-RULES.txt as line 2 requires.)

**Marks table (integer counts, counts only — no transcript or Luna reply text)**

| mark | count |
|---|---|
| packets total / usable / unlabelled / failed rows | 240 / 220 / 20 / 0 |
| pilot usable / limit errors / exit | 10 / 0 / 0 |
| replies / judge either / judge both | 1100 / 158 / 122 |
| glm flags / catches-both / catches-either / clean | 363 / 121 / 149 / 737 |
| judge-either inside glm-clean | 9 |
| V / G1 / G2 / G3 / proved_wrong | false / true / true / true / false → INCONCLUSIVE |
| arms H packets-replies-glm-either-both-catch | 57 / 285 / 80 / 33 / 23 / 23 |
| arms N | 55 / 275 / 80 / 24 / 18 / 17 |
| arms U | 53 / 265 / 144 / 83 / 72 / 72 |
| arms W | 55 / 275 / 59 / 18 / 9 / 9 |
| seal lines OK / selftests | 24/24; 7/7, 7/7, 5/5, helper ok |
| error prefixes (distinct, 60-char) | 1 (`''` × 220) |

**Every move** (origin/main aa34f14d1ba050d78b360c6e1357b45fb3f7af9d at TREE; later e49be974d0cc4ac5b04e2ec112dd1e2cfcb5efa9; all via git fetch + git archive, never checked out or pushed):
05:28:13 fetch → 05:28:25 archive → 05:28:28 seal 24/24 OK → 05:29:35 pre-check → 05:31:55–05:34:39 pilot (2.6 min, `stopped: done`, pilot-check `{"pilot_packets": 10, "rows": 10, "usable": 10, "limit_errors": 0, "pass": true}` exit 0) → 05:34:47 full run PID 82254 → polls 05:39:51/05:44:55/05:49:57/05:55:00/06:00:04/06:05:08/06:10:12/06:15:15/06:20:18 all alive → 06:24:22 not alive (self-stopped, `stopped: time`, 48.9 min) → 06:24:36 error-prefix count → 06:24:45 copy to worktree → $D `/var/folders/6q/.../tmp.dhGZGcKiq1` removed, re-confirmed gone this session. Counts: luna_b.jsonl 220 lines, best_b.jsonl 220 lines, `{"packets": 220, "usable": 220}`, verdict_b.json and arms_b.json as tabled. labeller: Luna (gpt-6-luna), helper sha256 342a0fb7e15ebf22da763c21eddecb0c58cfcbd43c74481d8421b5709023024e (matches the sealed hash).

**Misses:** 20 of 240 packets never got a usable row (45-minute cap hit, 0 failed calls); 70-minute kill rule never fired (run exited by itself); ratios printed by the scorer: recall_both 0.992, recall_either 0.943, yield_clean 0.67, kappa 0.465.

**Deviations:** `--selftest` needed one extra rubric file (artifacts/claude-mu402-20260926/JUDGE-claims.md) from the same commit — not in the SEAL list, reported, no other extra files; origin/main moved mid-run (aa34f14 → e49be974), work stayed on aa34f14; run stopped by time cap → "partial"; RESULTS.md's dangling "see cleanup command" resolved here by the confirmed `rm -rf` above (file itself left unedited, additive-only).

**What it means:** Luna flagged 363 of 1100 replies and caught 121 of the 122 both-judge cases; only 9 judged-bad replies hid inside its "clean" pile. **What it doesn't mean:** with 20 packets missing, V stayed false, so this does not clear mu-406 to pick training replies with Luna's marks — the gates G1–G3 passed on the 220 packets that exist, but the run must be called partial/INCONCLUSIVE, not a pass.
