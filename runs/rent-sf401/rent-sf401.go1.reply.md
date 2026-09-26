Starting your sf-401 rental — checking credit, duplicates, and the release source.
Credit and duplicate checks pass — now locating the reader source.
No duplicate run found and the local reader checks out — setting up the depot watch.
Depot report not yet published — poll loop running. Preparing the offer search while waiting.
All tree paths verified and BensPC reachable. Waiting on the depot report.
Depot is ready with verified reader. Renting the GPU now.
First rental missed the 6-minute start — destroying and trying the next host.
Rental running on an RTX 5090. Setting up access and streaming the tree.
Tree on rental verified (32M, head sha matches). Starting the depot reader copy and adapter stream.
Reader copy initiated, adapter streaming. Starting kit-C environment setup on the rental in parallel.
Adapter verified. Waiting on the reader copy and model snapshots.
Multiple data files missing — enumerating all data dependencies at once instead of one-by-one.
Reader copy complete (nested one level deep — fixing layout and verifying).
Torch upgraded and CUDA live. Relaunching arm A.
Found it — old torchvision clashes with the new torch. Upgrading the matching set.
Component data landed (tree 452M). Clearing partial crash logs and relaunching arm A.
Arm A is running lives. Monitoring to completion.
Arm A complete (747 rows, 24 lives). Launching arm B.
Arm B complete (759 rows, 24 lives). Checking scorer usage, then scoring.
Scored. Gathering counts and verifying outputs for copy-back.
All 15 files verified identical on both sides. Writing RESULTS, then destroying.
Instance destroyed and confirmed gone. Finalizing the ledger.
RUN COMPLETE — rent-sf401, the registered run of sf-401.

- Credit gate: credit **4.536206896269867** (above $3.00 floor). Duplicate gate passed.
- Depot REPORT.md found on poll 2 (~14:18 UTC): DEPOT READY, depot 52755827, /root/reader319 sha e688e1b2…776a76.
- Rental: 2 starters destroyed under the 6-min rule (52760159, 52761301, never ran); working rental 52762309, RTX 5090, $0.4944/hr, 14:37:13–15:58:07 UTC (2.35h, $1.16). Whole-task ~$1.27 of $1.50 budget. Destroyed and confirmed gone.
- Tree streamed (self122_head.pt sha 5ca02173…ee25 OK). READER319 via depot rental-to-rental `vastai copy` (sha e688e1b2…776a76 MATCH; depot untouched). Adapter via BensPC→Mac pipe→rental, nothing kept (sha a33211dc…7936f5 MATCH).
- Seals: SEAL-code all OK (364 lines), SEAL-sf401 17/17 OK, readersha 9/9, sleep02c 9/9 OK. sf401 test prints **14/14** (task text said 13/13; addendum-2 added s14 — deviation reported).
- Step 4 base-seed4102.pt sha **bc44f919…8d93a** (differs from 0.2c's 4655b761…, reported not a stop; both arms used it).
- Arm A: rows=**747**, lives=**24**, exit 0. Arm B: rows=**759**, lives=**24**, exit 0. Each measured ONCE (two crashed A attempts wrote nothing; partial logs cleared).
- Scorer mechanical counts: A WRONG_CANDIDATE ALL **23** (edit 9), RIGHT+RIGHT_CONFIRM 86; B WRONG_CANDIDATE ALL **13** (edit 3), RIGHT+RIGHT_CONFIRM 96. ms median/p90: A 807.8/1284.4, B 811.6/1293.0. Guard counters B: doubt_a 25, doubt_b 8, doubt_c 0, fired 17 (confirm 17, hedge 0), offer_yes 16 / offer_no 1, events 759 lines.
- **M1-M6 pending judges** — no verdict computed. No reply or panel text quoted; judge_/grammar_/arm_ contents never opened.
- Copy-back: 15 files, sha256 identical both sides before destroy. RESULTS-rent.md written; ledger line appended. PUSH paths ready for the watcher: RESULTS-rent.md, run/, score/, ledger.

Deviations (code never edited): `--bank P` needed the full panel path; ~100 small read-only data dirs streamed extra from origin/main (tree 32M→452M, no *panel*/*bank* dirs); container torch 2.2.1→2.11.0+cu128 (+torchvision/torchaudio) for transformers 5.17 + 5090; no ep382_A/B.jsonl written by runner; vastai copy landed nested, fixed with mv. Full tracebacks in RESULTS-rent.md.
