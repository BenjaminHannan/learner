Starting the rental run — checking credits, duplicates, and reader route.
Credit gate passed. Checking live instances and required reads.
All gates passed. Setting up tracking and searching for GPU offers.
Renting the cheapest 5090 offer ($0.406/hr).
Host can't pull images (proxy refused). Destroying and trying the next host.
Instance 52769291 running. Setting up SSH access.
Key attached but auth still fails. Rebooting the instance to reload authorized keys.
Host's SSH tunnel is broken. Checking for a direct connection route before giving up on this host.
No direct route. Destroying this broken host and trying a third one.
Same registry-proxy failure as host #1. Checking the depot's known-good image for the report, then making a final status check.
Host #3 is past the 6-minute mark with a fatal pull error. At the 3-rental cap — destroying it and closing out with a failure report.
All instances destroyed and confirmed gone. Writing the paper trail.
**Verdict: HOST-FAIL** — no run. All 3 allowed live rentals were host-broken; everything destroyed and confirmed gone (0 `claude-madeup-mu404` live). No arm launched, 0 rows, ~$0.03 of $1.00 spent.

**Integer counts**
- Credit gate: 4.87558057626984 (≥3.00, pass). Duplicate gate: 0 run files on builder-outbox, 0 live same-label instances (pass). Depot 52755827 running, sha-match (pass).
- Live rentals: 3/3 cap (52768279 proxy-dead in loading; 52769291 running but ssh-tunnel-dead; 52770417 proxy-dead in loading). Stillborn `success:false` husks: 2 (52769227, 52769253, $0). Arms launched 0/4, conversations 0/80, rows 0 (446/arm expected), files copied 0, bytes staged on Mac 0.
- Exact errors: `proxyconnect tcp: dial tcp 127.0.0.1:7890: connect: connection refused` (hosts 1, 4); `remote port forwarding failed for listen port 19290` + all-keys-denied incl. after reboot (host 3). Same proxy failure already in ledger for mu402/lis-319f/brd8/y1d — known fleet flakiness, not task setup.

**Every deviation (5)**: (1) 5 creates vs "max 3" = 3 live + 2 husks destroyed to obey single-instance rule, no 4th live try; (2) credit checked once at gate, not re-checked before re-rents; (3) no `run/` outputs — this RESULTS-rent.md reports HOST-FAIL instead; (4) one `reboot instance` tried for ssh keys, no help; (5) fresh ssh key (account id 1438174) left registered for a retry.

**Paper trail**: `artifacts/claude-mu403-20260926/RESULTS-rent.md` written (new file), 1 ledger line appended to `artifacts/fable-predictions-ledger.md`. Depot untouched, no code run/edited, no weights moved, no TEST-ONLY panel. PUSH paths with content: RESULTS-rent.md + ledger (no `run/` — nothing existed to copy back).

**Recommendation**: re-queue with a fresh cap; prefer a host class with a recent working sibling job (e.g. mu402's offer-45669386 class) and/or image `pytorch/pytorch:2.8.0-cuda12.9-cudnn9-runtime`.
