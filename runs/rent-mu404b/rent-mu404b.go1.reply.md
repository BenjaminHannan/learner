Starting mu-404 rental — fetching latest configs and checking gates.
Credit 5.09 — above gate. Checking duplicate and reader route.
No duplicate, depot running (52755827). Searching for GPU.
Rented 52775913 ($0.469/hr). Waiting for running state.
SSH ok, 5090, torch CUDA. Streaming tree now.
Tree streamed, head sha ok. Copying reader depot-to-rental.
Reader copy still in transit (556MB/2.1GB). Waiting.
Big file never landed (only 9.5MB present). Re-initiating depot copy.
Stale dentry cleared of small files; re-running depot copy onto clean dir.
Small files copy; the 2.1GB file never lands. Trying single-file copy to dodge the stale dentry.
Single-file copy transferring (1.8GB/2.1GB). Waiting for completion.
Fresh-name copy landed complete (2,161,290,944 B). Verifying sha.
Reader sha MATCHES. Assembling /root/reader319 into spec layout.
Stale dentry removed (rm exit 0). Retrying placement.
Stale file handle on poisoned paths. Trying fresh directory swap.
Reader verified at spec path. Cleaning poisoned dir, then setup.
Downloads done, BASE pinned at 87179e5c. Running seals + selftests.
All seals + selftests pass. Verifying zero FAILED lines for the record.
Seals: 14 OK + 336 OK, 0 FAILED. Launching all four arms.
Arms launched 16:56:08 UTC (R=1049 F=1050 P=1051 T=1052). Checking V0 lines.
Wordlist seal matches. Relaunching all four arms (one ssh each, properly detached).
SSH timed out under load — commands may still have launched. Checking state.
All four launched (17:04). Checking V0.
Fast: R/F/P 29/80, T 60/80. On track for ~17:30 finish. Continuing watch.
All four arms done, facts lines present. Scoring (counts only).
Score: 446 rows/arm as expected. Copying results back.
All 9 sha match. Gathering timing + spend, then destroying.
Instance destroyed, confirmed gone. Writing RESULTS + ledger.
Verdict: **RUN-COMPLETE** — four arms, 80/80 conversations each, 446 rows/arm, scored, 9 files copied back sha-verified, rental destroyed and confirmed gone. Judging is thread-side.

Integer counts
- Credit at gate: 5.094352626269782 (balance 0); spend ~$0.67 (1 rental, ~1.33h × $0.5037, of $0.87 new-spend cap; thread total ~$0.70 of $1.00)
- Rentals: 1 (52775913, RTX 5090, offer 45669449 host 406325 mu-402 sibling class), re-rents 0, live mu404b after destroy 0; depot 52755827 untouched, still running
- Seals/selftests: mu403 SEAL 14 OK / 0 FAILED; SEAL-code 336 OK; mu404 5/5; pick403 13/13; readersha 9/9
- Arms: R/F/P/T 80/80 dev lines each; tracebacks 0; exits 0/0/0/0; rows 446/446/446/446; wall ~23/~23/~23/~13 min; median ms/turn R 2094.8, F 2133.7, P 2157.0, T 1774.0
- Facts: R 318/34/36/0, F 318/34/36/34, P 318/34/36/0 (calls/with_facts/facts/blanked) — note with_facts 34 < V404's 40, for judging
- Copy-back: 9/9 sha match (4 chat jsonl, summary, 4 logs) in artifacts/claude-mu403-20260926/run/
- Key lines verified: BASE commit 87179e5c1f455ef22e6223592d2d61351b525bfc; reader e688e1b2…776a76 match; V0 readersha + R404/F404-nofacts/P403-sysline arm lines, adapter none

Every deviation (also in RESULTS-rent.md, which I overwrote as allowed)
1. Task tree list omitted artifacts/fable-nameval171-20260922, which sealed code reads at runtime — first R launch crashed FileNotFoundError on wordlist171.txt (7 dev lines, no output). Streamed that dir from origin/main; wordlist sha matches its SEAL line; one SEAL line (unstreamed design doc) unreadable, runtime-irrelevant.
2. First launch misfire: one chained `&`/`&&` ssh left F/P/T unstarted; cleaned logs+out404, relaunched each arm detached. Exactly one complete run per arm; crashed R partial deleted, unused.
3. `vastai copy` dir-sync failed 3× on the 2.1GB reader file (full transfer then ESTALE vanishing dentries); fresh-name single-file copy + dir swap fixed it, sha verified at spec path. Unremovable junk dir left on rental; rental destroyed anyway. Depot never written/stopped.
4. Arm start ~17:03:30 approximate (ssh clients timed out under load; server-side confirmed); end times exact mtimes.
5. Exit codes inferred 0 (0 tracebacks, facts lines, complete outputs, processes gone; no wait()).
6. No credit re-check — single rental, no re-rents.
7. Scorer wrote pair/turns/grammar/key files on rental; listed only, never opened, never copied back. No TEST-ONLY panel involved (DEV devchat only).

PUSH for watcher (force-add, artifacts/ ignored): artifacts/claude-mu403-20260926/run, artifacts/claude-mu403-20260926/RESULTS-rent.md, artifacts/fable-predictions-ledger.md. No weights pushed; nothing written to repo-root notebook/.
