# mu-404 + mu-403 rental — RESULTS-rent.md (2026-09-26)

## Verdict: HOST-FAIL (no run; 3 live rentals, all host-broken, max-3 cap reached)

No arm was launched. Nothing was copied to any rental (no tree streamed, no reader copied).
No code was run or edited. No weights moved. Depot untouched. No TEST-ONLY panel involved.

## Gates (all passed before renting)

- Credit gate: `vastai show user --raw` credit = **4.87558057626984** (>= 3.00, proceed).
- Duplicate gate: `git ls-tree origin/builder-outbox artifacts/claude-mu403-20260926/run` empty (0 files);
  no live instance labelled `claude-madeup-mu404` (0). Proceed.
- Reader route: depot REPORT (origin/builder-outbox) names instance **52755827** (`claude-director-depot`),
  live and `running` at check; depot sha e688e1b2...776a76 matches. No NO-READER.
- Read first: kit 330-rent-kit.md (sections A-D, full), PASSMARKS.md (full), claude_mu404.py docstring (full).

## Rental attempts (integer counts)

| # | Instance | Offer | GPU | dph $/hr | State reached | Outcome | Billed |
|---|----------|-------|-----|----------|---------------|---------|--------|
| 1 | 52768279 | 43165153 (US) | RTX 5090, rel 0.9956 | 0.4060 | loading 15:15-15:21 UTC (~0.10 h) | docker-proxy dead (see error A), destroyed | ~$0.00 |
| 2a | 52769227 | 45668978 | RTX 5090 | 0.4690 | stillborn (`success: false` husk) | destroyed, $0 | $0.00 |
| 2b | 52769253 | 45043241 | RTX 5090 | 0.4690 | stillborn (`success: false` husk) | destroyed, $0 | $0.00 |
| 3 | 52769291 | 45043241 (KR) | RTX 5090, rel 0.9922 | 0.5037 | **running** 15:24:35 UTC, destroyed ~15:28 (~0.06 h) | ssh tunnel dead (see error B), destroyed | ~$0.03 |
| 4 | 52770417 | 46753295 (US) | RTX 5090, rel 0.9957 | 0.4060 | loading 15:29:40-15:38 UTC (~0.14 h) | docker-proxy dead (error A again), destroyed | ~$0.00 |

- Live rentals (reached loading/running): **3** (cap: max 3). Stillborn husks: **2**. Total creates: **5**.
- Task spend: **~$0.03 of $1.00** budget. Post-destroy live `claude-madeup-mu404`: **0** (verified).
- All rentals: image `pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime`, disk 80 GB, label `claude-madeup-mu404`,
  one at a time (each destroyed before the next create, except husks destroyed immediately after).
- Arms launched: **0** of 4. Conversations run: **0** of 80 per arm. Rows: **0** (expected 446/arm on success).
- SSH keys: fresh key `~/.ssh/mu404` registered on account (id 1438174) and attached; left in place for a retry.
  Pre-existing `~/.ssh/id_ed25519` (already on account) and sibling keys all rejected by the broken hosts.

## Exact errors

- Error A (hosts 1 and 4, fatal in `loading`, past the 6-min rule), from `vastai show instance --raw`
  `status_msg`: `Error response from daemon: Get "https://registry-1.docker.io/v2/": proxyconnect tcp:
  dial tcp 127.0.0.1:7890: connect: connection refused` — host-side docker proxy down, image unpullable.
- Error B (host 3, `running` but unreachable): `vastai logs` shows
  `Error: remote port forwarding failed for listen port 19290` repeating; all ssh keys
  (freshly attached mu404 key included, before and after `reboot instance`) get
  `Permission denied (publickey,password)`.
- Same proxy failure is already in the ledger for mu402 (2 hosts), lis-319f (1), brd8 (1), y1d (1):
  this is known fleet flakiness on cheap hosts, not the task setup.

## What was NOT done (nothing reached these steps)

Steps 1-7 of the task past renting: tree stream (0 bytes), reader copy (0 bytes), setup/seals/selftests (0),
four arms (0 launched), V0 (n/a), scoring (n/a), copy-back (0 files), wall/median minutes (n/a).
BASE commit, reader sha-on-rental, seal lines: none (no usable rental).

## Deviations (5)

1. **5 creates vs "max 3 rentals"**: 3 live attempts (the cap) + 2 `success: false` stillborn husks
   (52769227, 52769253) that had to be created-then-destroyed to obey "never 2 instances at once".
   Counted honestly above; no 4th live rental attempted.
2. **Credit re-check skipped before re-rents**: checked once at gate (4.8756); not re-run before rentals
   3 and 4. (Account auto-refills; post-task credit 7.7211, so no budget risk materialized.)
3. **No RESULTS rows / run/ dir**: steps 5-7 outputs do not exist; this file reports HOST-FAIL instead.
   Nothing pushed under `run/` (nothing to copy back).
4. **Reboot attempted on host 3** (`vastai reboot instance 52769291`) for ssh-key reload; did not help.
5. **SSH key left on account** (id 1438174, `~/.ssh/mu404*` on Mac, ~1 KB; DISK ~0 of 1 GB) for retry use.

## Recommendation for the thread

Re-queue with a fresh rental cap; prefer offers whose hosts have recently run a sibling job
(e.g. mu402's working offer 45669386 class), and/or image
`pytorch/pytorch:2.8.0-cuda12.9-cudnn9-runtime` (mu402-verified). Depot 52755827 still running;
reader route unchanged.
