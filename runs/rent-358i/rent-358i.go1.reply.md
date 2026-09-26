Starting the 358i build — checking gates, credit, and rental status.
No duplicate results found — now checking Vast credit and live rental status.
Credit and duplicate gates pass — renting a 5090 for the training run.
First host stuck in loading past 6 minutes — destroying it and trying the next host.
Second host also stuck — destroying it and trying the third and final allowed host.
Third host is running — setting up SSH and preparing the training environment.
Files are on the rental — running seal verification and environment checks.
Seal checks pass — launching all eight training runs in parallel.
All eight runs healthy — plain nets at step 10k, loop nets at step 6k. Projected finish fits the time and budget caps. Waiting for completion.
All eight trainings finished — sealing checkpoints and running the sealed evals.
Evals complete — inspecting the result structure to build the verdict report.
Checkpoints sealed and copied back — gathering comparison data for the results report.
Comparison data gathered — verifying which test files are shared with 358a, then writing the verdict.
Verdict computed: INCONCLUSIVE on validity (loop seed 4 grids collapse). Writing the results file.
Results file written — pushing to builder-outbox with the ledger entry.
Push needs a rebase — retrying.
rv-387 seal passes — running check-load on the four loop checkpoints.
All four rv-387 runs finished — copying them back and pushing to main.
Both parts pushed — destroying the rental and confirming it's gone.
Verdict: INCONCLUSIVE (rsn-358i; G0 validity not met, G1 FAIL, G2 FAIL, G3 PASS; proved-wrong clause NOT triggered).

Integer counts (n=300 each; plain, loop own-stop, loop-plain; seeds 1/2/3/4; means):
- sums4 (practised): plain 300/300/300/300, loop 299/299/300/298, mean -1
- sums6 (bigger): plain 188/209/177/217 (mean 197.75), loop 220/255/196/285 (mean 239), diffs +32/+46/+19/+68, mean +41.25
- sums8 (report): plain 133/116/65/146 (mean 115), loop 163/197/121/258 (mean 184.75), diffs +30/+81/+56/+112, mean +69.75
- sums10 (report): plain 93/60/27/112 (mean 73), loop 140/162/104/238 (mean 161), diffs +47/+102/+77/+126, mean +88
- sums12 (report): plain 65/44/7/89 (mean 51.25), loop 97/120/74/218 (mean 127.25), diffs +32/+76/+67/+129, mean +76
- grids5 (practised): plain 299/300/297/300 (mean 299), loop 256/239/269/122 (mean 221.5), diffs -43/-61/-28/-178, mean -77.5
- grids6 (bigger): plain 230/248/237/236 (mean 237.75), loop 180/158/218/63 (mean 154.75), diffs -50/-90/-19/-173, mean -83
- grids7 (report): plain 136/149/130/142 (mean 139.25), loop 104/81/121/15 (mean 80.25), diffs -32/-68/-9/-127, mean -59
- numbers4 (practised): plain 0/0/2/3 (mean 1.25), loop 0/2/0/1 (mean 0.75), mean -0.5
- numbers5 (bigger): plain 0/0/1/1 (mean 0.5), loop 0/0/0/0, mean -0.5
- G0: loop seed 4 grids5 122 makes it 1-of-3 practised kinds >=210 -> FAIL -> INCONCLUSIVE. G3: 4/4 seeds pass (own-stop >= fixed-16 -5 on every bigger test; mean rounds sums6 > sums4 on all seeds).
- 358a beside (shared byte-identical sums/numbers files; grids files DIFFER by legend fix, not apples-to-apples): 358a plain sums6 197/255, loop 256/244; 358i plain 188/209/177/217, loop 220/255/196/285.
- GPU: RTX 5090. Minutes/run: plain 55.7/55.6/55.6/55.7, loop 75.3/75.2/75.4/75.4 (8 concurrent, ~80 min wall). Dollars: ~$0.94 of $1.50 (dph $0.48519; kill lines $1.35 / 16:32Z never hit).
- Credit gate: 5.523763126269863 (gate: none). Pushed to origin/builder-outbox (RESULTS.md, SEAL-run.sha256.txt, runs/, ledger line, commit e75ef5be8); no weights pushed. Rental 52757832 destroyed, confirmed gone (0 rent-358i live).

Every deviation: (1) 3 rentals used: two US $0.4481 hosts stuck in loading past 6 min, destroyed (~$0.10); third KR $0.4852 host ran. (2) Audit lines carry an extra clause after the required substring (present on all 4 lines). (3) rv-387 archive copied to rental during training; untouched until its section. (4) No code/test opened, printed, or edited; eval exactly once per checkpoint; tests/ items never printed. (5) No PIDs killed, no seed stopped (no TOO-SLOW).

rv-387: seeds 1, 2, 3, 4 all passed check-load and ran; printed solved counts in run order s1: grids7 keep 120/guess 131/back 131, grids6 keep 192/guess 214/back 214; s2: grids7 100/117/117, grids6 155/194/194; s3: grids7 141/152/152, grids6 220/241/241; s4: grids7 37/51/51, grids6 72/95/95 (n=300 each). No marks computed. Pushed to origin/main ("rv-387 raw results (358i rental)", first try). rv-387 section ~4 min (~$0.04 of thought-memory's $2), 358i files untouched. Extra file START.txt (my timestamp marker) included in run/; noted here.
