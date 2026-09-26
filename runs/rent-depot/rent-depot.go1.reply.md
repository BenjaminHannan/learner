Renting your reader depot — waiting on source, then copying rental-to-rental.
The rules file and rent-kit path from the brief don't exist at those locations — noting that and proceeding under the quoted key points. Now checking rentals.
Depot is running. Now polling the 319f source (read-only).
Source file is complete and no writer remains. Verifying checksum.
Checksum matches. Copying rental-to-rental now.
Server-side copy initiated. Polling depot for arrival.
Checksum matches on the depot. Confirming final state and billing.
Everything checks out. Writing the report and ledger line.
VERDICT: DEPOT READY — source verified, copy verified, depot left RUNNING.

- Depot instance id: 52755827 (label `claude-director-depot`), RTX 4070, $0.1136/hr
- Depot SSH: ssh3.vast.ai:35826 (user root)
- Depot path: /root/reader319 (6 files)
- Depot sha256 (`/root/reader319/model.safetensors`): e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76 — MATCHES source and expected value
- Copy: `vastai copy 52751954:/root/old/lis319-merged 52755827:/root/reader319`, initiated 14:08:28 UTC, verified complete 14:12:32 UTC → about 4 minutes, rental-to-rental, 0 bytes on the Mac
- Depot rented 13:45:36 UTC, left RUNNING (not destroyed). Source rent-lis-319f (52751954) untouched except reads, still running. No other instance touched, stopped, or destroyed.

Marks table (integer counts):

| # | Check | Count |
|---|-------|-------|
| 1 | 319f source polls (read-only ssh) | 5 polls |
| 2 | Polls seeing partial upload + live rsync writer (correctly waited) | 4 |
| 3 | Polls seeing complete file + no writer | 1 |
| 4 | Source sha256 runs on 319f | 1, match 1/1 |
| 5 | Depot rentals created by this task | 1 (52755827) |
| 6 | Duplicate-label conflicts | 0 |
| 7 | `vastai copy` attempts | 1, success 1/1 (rsync fallback not needed) |
| 8 | Files on depot with exact source byte sizes | 6/6 |
| 9 | Depot sha256 runs | 1, match 1/1 |
| 10 | Foreign instances touched / stopped / destroyed | 0 |
| 11 | Writes to rent-lis-319f | 0 (reads only) |
| 12 | Bytes staged on the Mac | 0 |
| 13 | Misses (bad copies, sha mismatches, failed rentals) | 0 |

Deviations (3, minor, none affecting the result):
1. OPUS-RULES.txt not found at the brief's path, and no such file under origin/main — worked under the key points quoted in the task (additive-only, append-only ledger, key never printed, uptime/df checked: Mac had 57 GB free).
2. `design/v3/30-modes/330-rent-kit.md` absent from this checkout — read it via `git show origin/main:...` and followed it (label, never destroy foreign instances, ledger line appended).
3. Budget: cheapest qualifying box (rel ≥ 0.98, disk ≥ 20 GB, inet_down ≥ 500) bills $0.1136/hr, so 6 h projects to $0.68 vs the $0.60 line (+$0.08); no cheaper qualifying offer exists. Actual spend to handoff (~0.46 h) ≈ $0.05. Also `vastai copy` nested one extra dir level; I flattened it on the depot so `/root/reader319/model.safetensors` is the exact spec path, then re-verified sha.

What this means / doesn't mean (plain high-school English): the depot is a bit-for-bit identical copy of the agreed reader file, so any job pointed at /root/reader319 on instance 52755827 reads exactly the agreed facts. It does NOT mean the file was quality-tested — only that the copy is exact. No test panels were opened or tuned on. The depot costs ~11 cents per running hour until someone destroys it.

Artifacts: created `artifacts/claude-depot-20260926/REPORT.md` (new file, additive-only); ledger line appended to `artifacts/fable-predictions-ledger.md`. Note: `artifacts/` is gitignored in this checkout so I could not stage the report — left on disk for the watcher to push per PUSH path (I did not commit, print the vast key, repeat the rented instance's api key, or write to the repo-root notebook).
