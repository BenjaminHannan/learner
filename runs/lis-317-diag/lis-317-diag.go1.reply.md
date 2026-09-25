Renting your 5090 and running the reader sweep — pulling the live plan first.
Reader checksum matches and no duplicate rental — now checking budget and capacity.
Counts check out — building the code tree and finding the cheapest reliable host.
Tree is staged with all inputs verified — now securing the GPU.
GPU rental secured — staging the upload while it boots.
Box is live — pushing the code and reader up.
Tree uploaded (slow link) — pushing the 2GB reader now.
Reader upload broke at 1.1GB — resuming it.
Uploads verified — extracting and setting up the environment.
Seal 3/3 OK — launching the first sampler.
First sampler is running — polling progress.
First sampler done (194/194) — launching the big 959-row sampler.
Big sampler running — waiting for it to chew through 959 rows.
Both samplers done (194 + 959) — running the scorer.
Scorer done: R0 89/131 (67.9%) — pulling the three outputs home.
Byte sizes match exactly — destroying the rental.
Rental destroyed and confirmed gone — staging the result files locally.
VERDICT: DONE, report only. lis-317-diag ran end to end on a rented RTX 5090: seal 3/3 OK, 194 + 959 sampler rows + scorer clean, all three outputs copied back byte-exact, box destroyed, ~$0.68 of the $1.50 budget spent. R0 = 89/131 = 67.9% → the 60–80% middle band: both; the gate first (no training). DEV data only, no marks, no TEST-ONLY panel touched.

Counts table (integers, from score_e2edev.txt):

| measure | count |
|---|---:|
| gold teach/correct facts | 131 |
| R0 (read, writable, owner+value match) | 89 |
| R0rel (also relation-word match) | 44 |
| RT (R0 facts clearing T=0.995) | 20 |
| not found in greedy read | 42 |
| W_total (writable facts in greedy reads) | 141 |
| W0 (writable, match no gold fact of turn) | 52 |
| ask turns / greedy act ASK | 71 / 55 |
| 8/8 agreement kept: right / wrong | 68 / 9 |

Every move: fetched origin/main + builder-outbox and read all files via `git show` (worktree not up to date); READER safetensors sha b4fd93a2… match; built tree (builder-outbox + main on top, skipped BASE/MiniLM/self122 per task); rented 5090 contract 52507626, offer 44173708 ($0.5037/h, 16 vCPU, label lis-317-diag) 00:41:59Z, running ~00:45Z; uploaded tree 119 s, reader 2.0 GB (scp broke at 1.1 GB, rsync --partial resume, sha match); image torch 2.8.0+cu129 CUDA True, transformers 5.17.0 clean (no upgrade needed); seal 3/3 OK 01:13:15Z; s1 e2e sampler 194 rows in 467 s; s2 lis301dev sampler 959 rows in 2354 s; scorer <1 s; copied back 194 lines/427668 B + 959 lines/1436426 B + 647 B, byte-exact; destroyed ~02:02:50Z, confirmed 0 lis-317-diag live (siblings untouched); ledger line appended; RESULTS-rent.md written with score_e2edev.txt verbatim.

Every miss/deviation: (1) cheapest offer 45669197 gone at rent time, re-searched to 44173708; (2) reader scp reset mid-transfer, resumed clean; (3) two ssh launches outlived the 60 s client timeout after printing their echo — both jobs had launched, verified via probe; (4) ledger gained concurrent sibling lines while I worked — mine present exactly once. Zero code edits, zero TEST-ONLY files opened.

What it means (plain English): the reader gets about 2 in 3 chatty DEV facts right before any gate — not good enough to blame only the gate (needed 105/131), not bad enough to blame only the reader (below 79/131). So per the pre-fixed rule: fix both, gate first because it needs no retraining. The live gate looks strict: only 20 of the 89 good reads clear 0.995. What it doesn't mean: nothing registered passed or failed — DEV counts only, no judges ran, and no new gate was built here.

PUSH (on disk for the watcher): artifacts/claude-lis317-20260925/reads_e2edev.jsonl, artifacts/claude-lis317-20260925/reads_lis301dev.jsonl, artifacts/claude-lis317-20260925/score_e2edev.txt, artifacts/claude-lis317-20260925/RESULTS-rent.md, artifacts/fable-predictions-ledger.md.
