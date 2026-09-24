Renting the GPU box for your dress rehearsal — fetching the latest kit and queue rules.
Your full spec is in hand — now inspecting the workspace and credit.
Local weights check out — now reviewing the runner scripts.
Credit and capacity look good — narrowing down the cheapest rental.
I've got a rental candidate — checking prior setups before launching.
Staging bundle is ready — now securing the GPU rental.
GPU secured — waiting for it to boot.
Box is live — connecting and pushing the code up.
Upload is crawling — switching to resumable transfer.
Environment is staged — running the preflight check.
The run failed fast — reading the full log to diagnose.
Environment fixed — relaunching all five arms.
One more library mismatch to fix, then verifying the reader loads.
First arm finished clean — the rest are running. Polling progress.
All five arms and the scorer finished — pulling the results home.
Scorer lines captured — now extracting the flagged triples for the chat arm.
Results verified locally — destroying the rental and closing the ledger.
Catching a transcription slip in my results draft — verifying against the log.
All lines verified byte-exact — final compliance check.
VERDICT: PASS (rehearsal). rent-330-dev ran end to end on a rented Linux GPU: seal 3/3 OK, 5/5 arms + scorer clean, files copied back and verified, box destroyed, ~$0.49 of the $2.00 budget spent.

Marks table (integer counts, from the scorer's printed lines):

| arm | user_rows | RIGHT | RIGHT_CONFIRM | ABSTAIN | CONFIRM_OTHER | WRONG_CAND | facts_saved/131 | new_triples (unsupported) | ms med/p90 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| G | 194 | 12 | 3 | 44 | 7 | 5 | 33 | 34 (0) | 725/995 |
| 330a | 194 | 12 | 3 | 44 | 7 | 5 | 33 | 34 (0) | 730/1002 |
| 330a_cre | 194 | 11 | 5 | 44 | 8 | 3 | 49 | 52 (2) | 745/1151 |
| 330a_chat | 194 | 12 | 5 | 38 | 8 | 8 | 49 | 52 (2) | 934/1156 |
| twin | 194 | 13 | 0 | 14 | 0 | 44 | 0 | 0 (0) | 1364/1380 |

Every move: rented 5090 (contract 52415640, 12:38:26Z), staged tree (self122 sha match) + READER (safetensors sha match), BASE commit 87179e5c (match), seal 3/3 OK, ran arms G 163s / 330a 163s / 330a_cre 173s / 330a_chat 193s / twin 257s (all exit 0), scorer exit 0, copied 5 run + 16 score files (row totals 226/226/247/247/194, user rows 194 each — match), destroyed 13:37:18Z (0 live after), ledger line appended, RESULTS-rent.md written (5 scorer lines byte-exact vs the rental log).

Every miss/deviation:
1. Setup needed 2 env-only upgrades the kit didn't foresee (0 code edits): transformers>=5 refused the image's torch 2.4.0, so torch went 2.4.0→2.14.0+cu130, which then forced matching torchvision 0.29.0+cu130 + torchaudio. First two launches failed all arms in 2–3 s (ImportError / torchvision::nms / .so load), 0 rows written; third launch clean.
2. lis-302's OPUS-RULES file path doesn't exist on origin/main — followed the 13 summarized rules instead (additive only: RESULTS-dev.md untouched; fictional names kept; no TEST-ONLY panel — only DEV bank + own outputs read; report here).
3. One self-caught typo (330a_chat distinct_replies) fixed and verified byte-exact before finishing.
4. First rental offer (45669552) was already gone; re-searched, took 49337314 ($0.4944/h). Rental ran 0.98 h ≈ $0.49. Sibling boxes (rent-339-style, cairn-smoke) never touched.

330a_chat unsupported triples (2 of 52): [Kim, partner, Thea] <- (Vaughn, fiancee, Thea); [Wyatt, allergy, talking] <- tie (Wyatt, pet, Slinky) / (Wyatt, age, 16).

What it means (plain English): the dress rehearsal the Windows box couldn't start now runs start to finish on Linux — the harness, reader, and DEV bank work together. The creative/chat layers lift saves from 33 to 49 facts at the cost of 2 unsupported triples each; the twin saves nothing by design. What it doesn't mean: nothing registered passed — this is DEV-only mechanical counts, blind judges never ran, and the Windows bug itself was sidestepped, not fixed.

PUSH (on disk for the watcher): artifacts/claude-e2e330-dev-20260924/RESULTS-rent.md, .../run (5 files), .../score (16 files), artifacts/fable-predictions-ledger.md (1 line appended).
