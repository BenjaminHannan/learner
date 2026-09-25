Starting rent-336b setup — fetching latest and reading your run specs.
No duplicate found, seals look good — setting up your rented GPU run.
Found a cheap 5090 that meets spec — building your code tree and checking weights now.
Tree built and weights verified — renting the GPU now.
GPU is running — connecting and uploading your tree.
SSH key hiccup — attaching the right key now.
Key is attached but auth still fails — checking how prior rentals connected.
API execute isn't cooperating either — trying alternate connection methods.
Fresh key registered — attaching it to the instance.
Checking for stale SSH processes that might be colliding with the tunnel.
SSH is dead on this host — destroying it and re-renting elsewhere.
First box destroyed ($0.10 lost) — searching fresh and renting a different host.
SSH works on the new box — uploading tree and reader, and checking how the runner resolves model names.
Tree is up — tracing how the arms locate the reader and base models.
Still tracing model path resolution — checking the reader loader.
CUDA torch works — installing deps and downloading base models, while the reader uploads.
Reader uploaded — verifying checksums and wiring up model paths.
All 232 seal lines pass — rebuilding sleep's base checkpoint now.
Checkpoint rebuilt — launching the four arms in sequence, starting with G.
Arm G is running clean (already on life 8 of 40) — polling until it finishes.
Arm G finished clean — launching arm P.
Bad launch killed before it wrote anything — relaunching P correctly.
Arm P running correctly as a single process — polling till done.
Arm P done (800 rows, 120 sleep rows) — launching arm T.
Arm T done — launching the final arm B.
All four arms complete — running the scorer.
Scorer printed all four arms — copying results back to the Mac.
All 21 files verified — pulling logs and computing sleep stats.
Everything checks out — destroying the rental and closing the books.
Ledger appended — writing RESULTS-rent.md now.
Verdict: RAN COMPLETE. The registered 336b follow-up ran once on bank B (40 lives × 4 arms) on a rented RTX 5090. All arms + scorer exited 0. No DUPLICATE, no SEAL-MISMATCH, no SLEEP-NOT-LEARNING. Counts only; bank, judge, grammar and gram360-parts files never opened or quoted.

Marks table (integer counts from the scorer's mechanical output; judged/grammar marks need blind judging, not done here):

| Mark | G counts | P counts | Bar | Note |
|---|---|---|---|---|
| M3 facts saved/total | 156/333 | 156/333 | ≥85% | director evaluates |
| M4 answerable asks right | counts in RESULTS-rent.md | same | ≥70% | needs gold-type cut; director evaluates |
| M5 never_told RIGHT | 36 of 38 (36 RIGHT, 1 CONFIRM_OTHER, 1 WRONG) | 36 of 38 | ≥95% | director evaluates |
| M6 P minus T right counts | two_hop P 3 RC/37, T 3 R+3 RC/37; reversal P 1 R+4 RC/23, T 2 R/28; edit P 5 RC/39, T 3 R/39; never_told+partial P 36 R/51, T 7 R/50 | — | ≥+20 pts each | director evaluates |
| M8a most_common/user | 27/619 | 27/619 | ≤5% | 4.4% |
| M8b clarify/user | 17/619 | 17/619 | ≤15% | 2.7% |
| M9 day1 kept | 87/90 | 87/90 | 100% | director evaluates |
| M11 ms median / p90 / confirm/user | 755.7 / 1155.2 / 180/619 | 761.7 / 1150.4 / 181/619 | ≤3000 / ≤8000 / ≤1/8 | director evaluates |
| M1/M2/M7/M8c/M10 | pending blind judges | — | — | packets in score/, unopened |
| B1 G−P grammar | pending graders | — | ≥+5 both | mechanical lines differ only in confirm_rows (G 180, P 181) |
| B2 sleep learned | 120 rows, 120 checkpoint_exists true, 0 attempted true (G, P, B each); sleep_T absent (expected) | — | 0 missing; attempted ≥1/arm | reason every row: 0 word episodes (<8); accepted true throughout |

Every move: fetched main; confirmed no run/ on builder-outbox (not DUPLICATE); built combined tree + self122/READER shas matched; rented 5090 #52513837 ($0.4944 dph) — ssh refused 10+ min — destroyed (~$0.09); re-searched offers, rented #52514776 — setup (torch CUDA ok, pip, BASE snapshot 87179e5c…, MiniLM), uploaded READER (rsync-resumed), seals 229/229 + 3/3 OK, route122 ok; rebuilt base-seed4102.pt (JSON seconds 14.4, sha 1dfd95f5…); ran G (799 rows), P (800), T (619), B (619) each single-process with correct sleepcheck+twinb header lines; scorer printed 4 lines; copied run/ (8 files) + score/ (13 files) back, 21/21 sha match; destroyed (0 live rent-336b); ledger appended (~$0.66 total of $4.00); wrote RESULTS-rent.md.

Every miss/deviation: (1) rental 1 SSH-FAIL, re-rented; (2) first G launch died on missing run/ dir for GRAM360_LOG (FileNotFoundError, full tail in RESULTS), mkdir + relaunched once, first launch wrote nothing; (3) first P launch missed SLEEPCHECK env vars, killed pre-output (no arm_P.jsonl existed), relaunched correctly, never 2 live; (4) sleep attempted=true on 0/360 rows (gated, checkpoint present, no stop triggered).

What it means in plain English: the end-to-end run itself worked — the agent answered all 40 test lives four ways and every file came home intact. The two things the director must decide: whether the sleep step actually learned anything (it ran but attempted zero learning updates because each sleep saw too few word episodes), and whether the grammar finisher helped (G and P gave nearly identical memory answers, so any grammar difference is up to the blind graders). No code was changed; TEST-ONLY bank B was only read by the runner/scorer.

PUSH: artifacts/claude-e2e336b-20260925/RESULTS-rent.md artifacts/claude-e2e336b-20260925/run artifacts/claude-e2e336b-20260925/score artifacts/fable-predictions-ledger.md
