Read-only rental check — verifying CLI, balance, and prior spend without renting anything.
CLI not found — skipping the live instance checks and gathering the prior rental history from memory and ledger.
VERDICT: read-only check complete. vast.ai CLI is NOT installed, so live instance/balance steps were skipped per instructions. Nothing was rented, created, edited, or printed from config. All spend/recipe facts below come only from memory files + ledger grep.

MARKS TABLE (integer counts)
| check | result |
|---|---|
| `command -v vastai` found | 0 (not found, exit 1) |
| `vastai --version` worked | 0 (command not found, exit 127) |
| `vastai show instances` runs | 0 (skipped, no CLI) |
| `vastai show user --raw` runs | 0 (skipped, no CLI) |
| running instances observed live | 0 (unknown, API not queried) |
| balance number obtained | 0 (unknown, not queried) |
| memory files read | 5 (compute-availability, gpu-budget-cap, rental-create-blocked-by-classifier, rented-cpu-slow-for-this-workload, rented-cpu-standing-ok, plus a3-teacher-delay-v2-result = 6 files total) |
| ledger lines matching `vast\|rent` (case-insensitive) | 14 of 2633 total ledger lines |
| genuine rental mentions among those 14 | 3 (P27, P28, P29 "rental box"); other 11 are substrings (different/parent/current/differential) |
| dollar amounts recorded in ledger | 0 |
| files created/edited/deleted | 0 |
| secrets printed | 0 |

EVERY MOVE (what I ran, from the worktree)
1. Read the OPUS-RULES file first (22 lines, in full).
2. `uptime` + `df -g /`: load averages 88.03/79.80/65.04 (above the 60 rule, but I ran zero heavy steps so no waiting was needed); disk 18 GB available, above the 3 GB stop line.
3. `command -v vastai` → not found; `vastai --version` → command not found. Step 2 stopped here per task.
4. Read the 3 assigned memory files + 3 related spend memos; grepped the ledger (used `grep`/`sed`, not `rg` — `rg` is a broken x86 binary on this Mac: "bad CPU type in executable").

MISSES / unknowns (stated plainly)
- Live running-instance count, ids, hourly costs: UNKNOWN (no CLI, no API calls made).
- Current credit/balance: UNKNOWN (same reason; I did not curl as fallback — task said stop step 2, and the key must never be printed).

DEVIATIONS
- `rg` → `grep` substitution (tool only, read-only equivalent, no effect on numbers).
- No other deviations. No TEST-ONLY panels touched. No config files read or printed.

EXACT RECIPE USED LAST TIME (key shown only as `$(cat ~/.config/vastai/vast_api_key)`)
- Read-only calls that worked 2026-09-19: offer search with no key; `GET /instances/` and `/users/current/` with `-H "Authorization: Bearer $(cat ~/.config/vastai/vast_api_key)"`.
- Create call 2026-09-19: `PUT /asks/{id}/` for two 4x RTX 5060 Ti boxes (option A, $2.50 hard stop, Ben-approved) — BLOCKED by the desktop app's auto-mode classifier ("Real-World Transaction"). Hand Ben a ready bash block or have him click in console; agent takes over by ssh after.
- 2026-09-18 GPU recipe: RTX 5090 on-demand (~$0.52/h), image `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime`, runtype `ssh_direc ssh_proxy`, attach key via `POST /instances/{id}/ssh/`, rsync repo (minus artifacts/.runtime/.budget/data/village), `runtime.remote.json` with empty import_roots, `python -B run.py --runtime runtime.remote.json step1 ...` (~55 min ≈ $0.48, 4M core ≈ 1.67M tok/s).
- 2026-09-19 recipe: many fast cores + several GPUs (not one big GPU), ON-DEMAND ONLY (a bid box paused mid-wave, whole wave lost); 4x RTX 5060 Ti + 112 vCPU (80 twelve-thousand-step runs, ~48 min) and 8x RTX 3060 + 80 old Xeon (~88 min); CUDA MPS nearly doubles throughput; upload only scripts + archive + exp1/data minus test.pt (~1 MB); keep both arms on one machine; bracket-trick pkill; save ids; verify copy-back BEFORE DELETE; confirm `GET /instances/` empty.
- 2026-09-20 CPU probe: AMD EPYC 7763 64-core, $0.376/h — ~3x SLOWER than the Mac (memory-bandwidth bound), wave aborted.

TOTAL SPENT (memory only; ledger holds $0.00 — no dollar figures in it)
- $3.40 spent by 2026-09-18 (per gpu-budget-cap; does NOT count toward the $30 cap).
- ~$3.00 for the 2026-09-19 rentals (approval up to $3.25; all destroyed same day; includes ~$2.20 for the A3 two-box run; a same-day note says ~$2.30 — snapshots differ, so I do not sum them).
- ≈$0.12 for the aborted 2026-09-20 CPU wave.
- Cap status: $30 lifetime cap on new spending stands; no live balance to quote against it.

WHAT IT MEANS (high-school English): We spent a few dollars learning that renting works but only with permission, on-demand boxes, and the right setup — and that renting CPUs for this job is a waste. Right now we can't see the live account because the CLI tool isn't installed, and the memory says every rented box was already deleted, so most likely nothing is billing at this moment, but that part is not verified.

WHAT IT DOESN'T MEAN: It doesn't mean the balance is fine or that zero boxes are running — I never checked the live account, so I can't promise either. It also doesn't give one exact lifetime total, because the notes record overlapping snapshots ($2.30 vs ~$3.00 same day), not one adding-up ledger.
