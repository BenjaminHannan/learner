Backing up the v4.1 checkpoint — verifying rules and locating the file.
Found the checkpoint fingerprint — now tracking down the backup.
Remote checksum checks out — now copying the checkpoint locally.
Copy finished — now confirming the local file is bit-identical.
Verdict: PASS — v4.1 ear checkpoint backed up locally, sha256 matches exactly.

Marks table (integer counts):

| Mark | Bar | Got | Pass? |
|---|---|---|---|
| M1 | find file under out_v41 with sha256 starting 55284dec | 1 file found | yes |
| M2 | copy it to ~/premonition-weights/smolear235_v41/ outside repo, never git add | 1 file copied, 0 repo files created, 0 git adds | yes |
| M3 | Mac sha256 equals BensPC sha256 exactly | 1/1 match | yes |
| M4 | touch nothing else on BensPC, never touch pythonw 13036 | 0 other touches | yes |

Numbers:
- Path: /Users/ben-hannan/premonition-weights/smolear235_v41/smolear235.safetensors
- Size: 723673144 bytes (remote dir listing 723,673,144 bytes, stat size=723673144)
- SHA256: 55284dec92ea3e6d5d9d99c5afa99ae80a73eafaf644a0c2ca268dcb9fad0bd2
- Remote: C:\Users\benja\smolear235\out_v41\smolear235.safetensors
- Remote CKPT.sha256.txt: 55284dec92ea3e6d5d9d99c5afa99ae80a73eafaf644a0c2ca268dcb9fad0bd2 smolear235.safetensors
- Remote certutil hash: 55284dec92ea3e6d5d9d99c5afa99ae80a73eafaf644a0c2ca268dcb9fad0bd2
- Local shasum: 55284dec92ea3e6d5d9d99c5afa99ae80a73eafaf644a0c2ca268dcb9fad0bd2

Every move:
1. Read /private/tmp/claude-502/.../scratchpad/briefs/OPUS-RULES.txt (22 lines).
2. git fetch -q origin main, git show origin/main:design/v3/30-modes/264-qa-checker.md + origin/main:handoff/kit/briefs/261-earcheck.txt (read both).
3. Read artifacts/claude-earcheck261b-20260923/PASSMARKS.md (120 lines) + RESULTS.md (166 lines) in worktree.
4. Listed artifacts/claude-earcheck261b-20260923/ (14 files) + scripts/claude_earcheck261_*.py (19 files) + 261b scripts; imported nothing, edited nothing.
5. uptime + df -g / before heavy step: load 75.69/68.75/60.05/53.29 across run, disk Available 11 GB (>3 GB bar, proceeded).
6. ssh benspc dir C:\Users\benja\smolear235\out_v41: 4 files, 723,911,684 bytes total; target 723,673,144 bytes.
7. ssh benspc type CKPT.sha256.txt: 1 line, prefix 55284dec.
8. ssh benspc certutil -hashfile smolear235.safetensors SHA256: 1 hash, exact match.
9. mkdir -p ~/premonition-weights/smolear235_v41 (was missing, created outside repo).
10. scp attempt 1 with 120s tool timeout: partial 396139520 bytes, killed by timeout, 0 complete.
11. scp attempt 2 with 600s timeout: complete 723673144 bytes, SCP_EXIT 0.
12. shasum -a 256 local file: exact match, SHA_EXIT 0.
13. git status check: 0 repo files created/edited by me, weights not in repo, never git added.

Every miss:
- Miss 1: first scp hit the 120s default tool timeout at ~396 MB (~3.3 MB/s). No data lost; retried with longer timeout and finished. Counts as 1 interrupted copy, 1 successful copy.
- Misses 0 on identification, hash, size, and no-touch rule.
- 0 TEST-ONLY panels opened. 0 sealed files touched. 0 ledger lines appended.

Deviations:
- D1: Mac 1-min load was 75.69, 68.75, 60.05 at start (above OPUS-RULES 60 limit for heavy suites). scp+shasum are I/O, not a registered GPU/CPU suite; ran anyway, finished at load 53.29. No suite was run.
- D2: Created ~/premonition-weights/smolear235_v41/ outside the repo. Allowed by task (“NOT inside the repo”), not a repo additive-only violation.
- D3: Did not create scripts/claude_earcheck264_*.py, artifacts/claude-earcheck264-20260923/, or P264.n ledger lines. This run was the backup-only task; no 264 build was executed, so no predictions were claimed.
- D4: Did not run nvidia-smi on BensPC and did not start/stop llama-server. Left BensPC otherwise untouched.

What it means (plain high-school English):
- Cloud GPUs can now use the Mac copy. It is bit-for-bit the same file as BensPC’s v4.1 checkpoint.
- The ear other experiments used is preserved, so future runs don’t depend on BensPC being awake.

What it doesn’t mean:
- It does not mean the ear is good or bad. This was a copy check, not a test of answers.
- It does not mean exp 264 is built, sealed, or run. Zero 264 code was written here.
- It does not mean other files on BensPC were checked. Only the one safetensors file was hashed and copied.
