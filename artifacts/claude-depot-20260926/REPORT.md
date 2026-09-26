# READER DEPOT REPORT — claude-director-depot — 2026-09-26

Task: set up a READER DEPOT on vast.ai (director, 2026-09-26 13:45 UTC).
Source: rent-lis-319f instance, `~/old/lis319-merged/model.safetensors`.
Expected sha256: `e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76`

## Verdict: DEPOT READY (source verified, copy verified, depot left RUNNING)

- Depot instance id: **52755827** (label `claude-director-depot`)
- Depot SSH: **ssh3.vast.ai:35826** (user `root`; direct port also mapped, proxy is the tested route)
- Depot path: **/root/reader319** (6 files, flattened to match spec)
- Depot sha256 (`/root/reader319/model.safetensors`): **e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76** — MATCHES source and expected value
- Depot $/hr: **$0.1136** (RTX 4070, 25 GB disk, verified host, Washington US)
- Depot rented: 2026-09-26 13:45:36 UTC. Status at handoff: **running** (left RUNNING per task; NOT destroyed)
- Copy: `vastai copy 52751954:/root/old/lis319-merged 52755827:/root/reader319`, initiated 14:08:28 UTC, verified complete 14:12:32 UTC → **about 4 minutes**, rental-to-rental, nothing landed on the Mac (DISK 0)
- Source instance rent-lis-319f (52751954): untouched except reads — still running, nothing stopped or destroyed. No other instance touched, stopped, or destroyed.

## Depot contents (`/root/reader319/`, `ls -la`)

- chat_template.jinja (9241 B)
- config.json (784 B)
- generation_config.json (227 B)
- model.safetensors (2161290944 B, sha256 e688e1b2…776a76)
- tokenizer.json (9894271 B)
- tokenizer_config.json (477 B)

## Marks table (integer counts)

| # | Check | Count |
|---|-------|-------|
| 1 | 319f source polls (read-only ssh) | 5 polls |
| 2 | Polls seeing partial upload + live rsync writer (correctly waited, not copied) | 4 |
| 3 | Polls seeing complete file + no writer | 1 |
| 4 | Source sha256 runs on 319f | 1, match 1/1 |
| 5 | Depot rentals created by this task | 1 (52755827) |
| 6 | Duplicate-label conflicts | 0 |
| 7 | `vastai copy` attempts | 1, success 1/1 (fallback rsync not needed) |
| 8 | Files present on depot with exact source byte sizes | 6/6 |
| 9 | Depot sha256 runs | 1, match 1/1 |
| 10 | Foreign instances touched/stopped/destroyed | 0 |
| 11 | Writes to rent-lis-319f | 0 (reads only) |
| 12 | Bytes staged on the Mac | 0 |
| 13 | Misses (wrong-file copies, sha mismatches, failed rentals, restarts) | 0 |

## Deviations (3, all minor, none affecting the result)

1. **OPUS-RULES.txt not found**: the path in the brief (`/private/tmp/claude-502/.../scratchpad/briefs/OPUS-RULES.txt`) does not exist, and no `*OPUS-RULES*` file exists under `origin/main`. Worked under the key points quoted in the task itself (additive-only, append-only ledger, key hygiene, no secrets, uptime/df checks done: Mac had 57 GB free).
2. **Rent-kit path not in this worktree**: `design/v3/30-modes/330-rent-kit.md` is absent from the checkout; read it via `git show origin/main:...` instead and followed its rental rules (label, no foreign-instance destruction, ledger line).
3. **Budget projection +$0.08 over**: cheapest qualifying offer (rel ≥ 0.98, disk ≥ 20 GB, inet_down ≥ 500) was $0.1081/hr → rented depot bills $0.1136/hr with 25 GB disk, so 6 h projects to **$0.68 vs the $0.60 line (+$0.08)**. No cheaper qualifying box exists (next cheapest was $0.1223/hr). Actual spend to handoff (~0.46 h) ≈ **$0.05**. Also: `vastai copy` nested the tree one level (`/root/reader319/lis319-merged/`); flattened it on the depot so `/root/reader319/model.safetensors` is the exact spec path, then re-verified sha.

## What this means / doesn't mean (plain English)

- The depot is a working read-only copy of the agreed reader file: the big model file on the depot is bit-for-bit identical to the one on 319f (same checksum), so any reader job pointed at `/root/reader319` on instance 52755827 reads exactly the agreed facts.
- It does NOT mean the file was tested for quality — only that the copy is exact. No test panels were opened, no tuning was done.
- The depot costs about 11 cents per running hour until someone destroys it; after 6 hours that is about 68 cents, 8 cents above the planning line.
