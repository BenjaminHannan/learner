Adding your lis-319f reader to the depot — verifying source and starting the upload.
Source differs from the earlier depot file — I'll confirm the new checksum and trace the ledger before transfer.
Local checksum matches — now confirming the depot is running.
The prescribed rsync route is blocked on the depot — diagnosing a transfer fallback that leaves everything else untouched.
Upload completed after one dropped connection and a retry — now verifying the copy is bit-for-bit exact.
All six files byte-match and the depot checksum matches the source — writing the report.
The report is git-ignored — checking why before pushing.
Push is blocked by an environment rule — verifying the local commit is complete and correctly scoped.
VERDICT: DEPOT-319f READY — the lis-319f reader is on the depot bit-for-bit exact (sha 970ef0ac match 1/1), `/root/reader319` untouched, depot left RUNNING. One miss: PUSH is not done — this sandbox blocks every `git push` command, so the report is committed locally (cf67c618e, exactly 1 file) and the director (or anyone with push rights) needs to push it.

Marks table (integer counts):

| # | Check | Count |
|---|-------|-------|
| 1 | Mac source `shasum -a 256` runs | 1, match 1/1 (no SRC-MISMATCH) |
| 2 | Depot identity checks (`vastai show`, read-only) | 2, running + label `claude-director-depot` 2/2 |
| 3 | Prescribed `rsync` attempts | 6, success 0/6 (exit 126 every time) |
| 4 | `scp` fallback attempts (same 6 files, new dir only) | 2, success 1/2 |
| 5 | Files on depot with exact source byte sizes | 6/6 |
| 6 | Depot `sha256sum` runs | 1, match 1/1 |
| 7 | Writes to `/root/reader319` | 0 |
| 8 | Other instances touched / stopped / destroyed | 0 / 0 / 0 |
| 9 | New bytes staged on the Mac | 0 |
| 10 | TEST-ONLY panels read / tuned / quoted | 0 / 0 / 0 |
| 11 | Sha mismatches / wrong-file copies / wrong-dir writes | 0 / 0 / 0 |
| 12 | `git push` completions | 0/1 (blocked, see deviations) |

Every move, in order:

1. Looked for OPUS-RULES.txt at the brief path — not there (that scratchpad dir is empty). Worked under the key points quoted in the task instead.
2. Checked `uptime` and `df -g /` before heavy steps: Mac had 54 GB free (above the 3 GB bar). All commands sequential (1 at a time, under the 4-process cap).
3. `shasum -a 256 ~/premonition-models/lis319f-merged/model.safetensors` = 970ef0ac…4f9b — equals expected, 1/1.
4. `vastai show instance 52755827` (key only via `$(cat …)`, never printed): running, label `claude-director-depot`, ssh3.vast.ai:35826.
5. SSH pre-check (read-only): `/root/reader319/` present with 6 files, `/root/reader319f/` absent. Created only `/root/reader319f/`.
6. Ran the prescribed rsync 6 times — all died in ~1 s with `/usr/bin/rsync: Permission denied`, exit 126. Cause found: the depot's `/usr/bin/rsync` is a 0-byte non-executable stub (dated Sep 26 14:08). Zero bytes moved.
7. Fallback `scp` of the same 6 files to `/root/reader319f/`: attempt 1 dropped after ~11 min (Broken pipe — the anticipated drop); attempt 2 exited 0 after ~32 min. First transfer command 15:20:13 UTC → verified copy 16:06:27 UTC = ~46 min wall, inside the 3 h budget.
8. Depot verify: 6 files listed, byte sizes match Mac source 6/6 (9062 / 749 / 214 / 2161290944 / 9894271 / 459), `sha256sum` = 970ef0ac…4f9b, match 1/1.
9. Confirmed `/root/reader319` untouched (timestamps still Sep 25 20:21, sizes unchanged, read-only listing only).
10. Wrote new `artifacts/claude-depot319f-20260926/REPORT.md` (53 lines, additive-only; nothing existing edited or deleted). Appended 1 ledger line via `cat >>`.
11. `git add -f` + commit scoped to exactly that 1 file (commit cf67c618e). PUSH attempted but the sandbox denies all `git push*` commands — 0 pushes done.
12. Final `vastai show instance`: 52755827 still RUNNING at handoff. Nothing rented ($0 this task).

Deviations (3):

1. OPUS-RULES.txt not found at the brief path; followed the quoted key points (additive-only, append-only ledger, key hygiene, no secrets, uptime/df, integer counts).
2. rsync → scp fallback (depot rsync binary is a 0-byte stub; installing rsync would have meant changing the instance, so scp — which touches only the new target dir — was the smaller change). Depot-side sha match proves the copy is exact regardless of tool.
3. PUSH incomplete: environment rule blocks `git push`; report is committed locally as cf67c618e (1 file, nothing else in the commit) and the ledger line is appended locally. Director: `git push origin claude/card-experiment-handoff-7c5b27` publishes it.

What this means / doesn't mean (plain high-school English):

- It means the depot now has an exact copy of the agreed lis-319f reader at `/root/reader319f/` — the big file there is bit-for-bit identical to the Mac source, so any job pointed at that path reads exactly the agreed facts. The old `/root/reader319` copy was not touched.
- It does NOT mean the file was quality-tested — only copied exactly. No test panels were opened, no tuning happened.
- It does NOT mean anything else changed: no other machine was touched, stopped, or deleted, this task spent $0, and the depot keeps billing its own $0.1136/hr until someone destroys it (not me — I left it running per the task).
