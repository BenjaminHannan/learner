Sample-first decode queued — verifying seals before the GPU run.
The routing slip is blank, so I'll pull the task spec straight from the repo.
Found the task files on origin — reading the run spec now.
Seals check out and local weights verified — now connecting to the GPU machine.
GPU is free and a working Python env is present — staging the weights and code next.
Weights are staged — confirming integrity and shipping the sealed code.
Staging done — launching the one allowed GPU run.
The run finished suspiciously fast — checking whether it actually decoded.
Outputs are clean — placing them in the artifacts folder and running the recount.
All counts in hand — writing the results file.
VERDICT: PASS on every mark I was asked to measure. The sample-first mouth spoke on all 1000 rows, the recount found 0 gate failures, variety is fixed (461 distinct replies, top reply only 42), and there were 0 crashes. Grammar (Pm1v.4) is not mine to grade — the mouth thread runs the blind graders on dev_out.jsonl next.

Marks table (integer counts):

| Mark | Bar | Got |
|---|---|---|
| Pm1v.1 spoke within 5 tries | >= 990/1000 | 1000/1000 (fell back 0) |
| Pm1v.2 fresh slot_check recount failures | 0 | 0 (1000/1000 spoken rows rechecked) |
| Pm1v.3 distinct slotted replies | >= 300/1000 | 461/1000 |
| Pm1v.3 most common single reply | <= 50/1000 | 42/1000 |
| Pm1v.4 grammar | blind graders (mouth thread) | not graded by me |
| Pm1v.5 crashes | 0 | 0 |

Every move:
1. SEAL: worktree is behind origin/main, so I verified in /tmp/own-m1v-seal (git archive origin/main). All 8 lines of SEAL-code.sha256.txt OK.
2. Weights: Mac ~/premonition-models/own-m1n-mouth/merged/ model.safetensors sha256 matches de12daf4…1564a. Copied the folder to BensPC C:/Users/benja/own-m1n/merged via scp; re-verified the same sha256 on BensPC with CertUtil.
3. Code: git-archived the 4 sealed paths from origin/main, copied to BensPC, extracted to C:/Users/benja/own-m1n/m1v-run keeping paths. Never edited any sealed file.
4. Run: exactly ONE real run on the RTX 5070 Ti (CUDA, driver 591.86), `--samples 4 --seed 1`, exit code 0, ~14 min. Try histogram {"1": 1000} — every row passed the gate on the first sampled try, greedy fallback never used. Per-status spoke: OK 350/350, SAVED 150/150, UNKNOWN 150/150, ABSTAIN 100/100, CLARIFY 150/150, FORGOT 100/100. Median 866.1 ms/row, p90 1032.8 ms/row.
5. Copied back dev_out.jsonl (1000 lines) and the printed summary (re-encoded UTF-16→UTF-8, content identical) to artifacts/claude-own-m1v-20260924/, wrote RESULTS-run.md. Fresh Pm1v.2 recount with the sealed slot_check on raw[tries-1]: 0 failures.
6. No training, no TEST-ONLY panel touched, no existing file edited or deleted (3 new files only). Mac disk had 64 GB free, BensPC C: ~53 GB free. GPU was free before/after (the process exited).

Misses/deviations (all reported, none hidden):
- The OPUS-RULES.txt path in the task does not exist (that scratchpad dir is empty), so I worked from the task text's key points.
- No `lis-301` venv exists on BensPC; I used C:/Users/benja/lis300/venv (torch 2.11.0+cu128, transformers 5.17.0, cuda True).
- My first remote-launch attempt died instantly (shell arg-splitting → argparse usage error, zero output written). The second launch is the single real run — no re-runs, no other seeds.
- Note for the mouth thread: 165/1000 filled replies print a raw underscore relation (e.g. "work_location", "favorite_food"). The sealed run code fills raw names; the say-forms printer fix is yours.

What it means / doesn't mean (plain English): the old mouth always picked the single most likely wording, so 1000 answers collapsed into just 59 distinct replies. Letting it sample first fixed that — 461 distinct replies, no single reply over 4.2% — while still passing the faithfulness gate every time. What it doesn't mean: this says nothing about grammar quality (your blind graders decide Pm1v.4), and since the first sample passed every time, we learned nothing about tries 2–5.

PUSH (watcher, please push — I did not check out, merge, or push anything myself):
- artifacts/claude-own-m1v-20260924/dev_out.jsonl
- artifacts/claude-own-m1v-20260924/dev_summary.json
- artifacts/claude-own-m1v-20260924/RESULTS-run.md
