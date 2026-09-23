Starting your mouth fine-tune — verifying sealed code and lining up a GPU.
Local copy is missing the task files — pulling the sealed specs from origin.
Specs reviewed — now checking spend ledger and GPU availability.
No live instances and spend is under cap — now finding the rental recipe.
Ledger clear, no live instances, credit $6.39. Searching for a reliable 5090.
Cheapest reliable 5090 found ($0.50/h). Checking SSH setup before renting.
Staging the code bundle locally first, then renting.
Instance live (different host than the dead one, $0.52/h). Waiting for SSH.
Still loading the image — polling SSH.
Instance is running but SSH auth fails — re-attaching key and checking via API.
Key not syncing — rebooting to force sync (disk persists).
SSH works now. Verifying GPU and uploading code.
Seal 5/5 OK. Starting venv install in background, rebuilding M0 meanwhile.
M0 verified identical. Building M1 data now (stdlib-only, no venv wait).
Data matches expected counts exactly. Setting up GPU venv.
pip installing torch 2.14 + deps in background. Polling.
Env good (torch 2.14 cu130, transformers 5.17). Downloading MiniCPM5-1B.
Download in progress (10/11 files). Polling.
Model downloaded (commit 87179e5c). Verifying and launching training.
gcc installed, no stale process. Relaunching training.
Training running (loss 2.81→1.19, ~1786 tok/s, 2500 steps). Watchdog polling.
Training complete. Collecting summary and hashes for the seal.
Writing the seal file locally before measuring.
Seal written. Running the dev measurement once.
Samples look fluent. Copying the 2.1GB model to the Mac now.
Destroying the instance and confirming.
My instance is gone; the other box is another agent's — leaving it. Writing RESULTS.md.
VERDICT: registered FAIL — 4/5 marks PASS, Pm1.4 (variety) FAILS. (OPUS-RULES.txt path in the brief does not exist; I followed the brief's quoted rules instead. No TEST-ONLY panel, panel folder, bench folder, or convbench file was ever opened.)

Marks table (dev measured ONCE, 1000 rows, integer counts):

| Mark | Bar | Measured | Result |
|---|---|---|---|
| Pm1.1 spoke within 5 tries | ≥990/1000 | 1000/1000, 0 fell back | PASS |
| Pm1.2 first-try pass | ≥950/1000 | 1000/1000 (tries {1:1000}) | PASS |
| Pm1.3 recount failures | 0 | 0/1000 (independent recount, sealed slot_check) | PASS |
| Pm1.4 distinct ≥300 AND top ≤30 | both | 45 distinct; top reply 175 rows (17.5%) | FAIL |
| Pm1.5 crashes | 0 | 0 | PASS |

"Proved wrong" clause NOT triggered (first-try 100% vs 80% floor). Fallbacks per status: 0 in all six (OK 350/350, SAVED 150/150, UNKNOWN 150/150, ABSTAIN 100/100, CLARIFY 150/150, FORGOT 100/100). Speak on RTX 5090: median 2137.2 ms, p90 2469.3 ms, max 4669.9 ms. Training: 19.93 min, 2501.7 tok/s, 2500/2500 steps, dev_loss 0.1571, batch 16 (no OOM fallback). Dollars: ~$0.88 (contract 52279343, $0.5156/h, ~102 min; ceiling $4/3h respected; ledger total far under $30).

Every move: rented ONE 5090 (reliability 0.9886, label own-m1b, fresh host, DUPLICATE check 0 live at rent); seal 5/5 OK; M0 rebuilt (20000+1000, dev byte-identical, stats identical); M1 data kept 20000+1000, dropped 0; MiniCPM5-1B commit 87179e5c; trained 2 epochs LoRA-r32 and merged (sha b40cc2d6); SEAL-run written BEFORE measuring; speak ran once; Pm1.3 recounted; 20 rows quoted in RESULTS.md; model (sha-verified) at ~/premonition-models/own-m1-mouth/; instance destroyed and confirmed gone (a sibling agent's rsn-294 box appeared mid-run — never touched). Misses: none besides the Pm1.4 FAIL. Deviations (3): SSH attach needed the full pubkey string, not the key id; torch 2.14 needed gcc for triton JIT so I apt-installed gcc and re-ran training fully from scratch (sealed code untouched, crashed attempt discarded); watchdog polls stretched to ~115 s during the 40-min speak run (log grew every poll, no stall). Diagnosis: M0 dev has 339 distinct templates (top 7 rows), so the collapse to 45 (top 175) is the model's greedy over-confidence, not the data — one follow-up is your call.

Plain English: the mouth learned to never garble a name — 1000/1000 safe replies, double-checked — but it talks like a robot with five sentences, repeating its favorite line on 1 in 6 turns. Format-perfect but boring fails the registered variety bar, so this mouth isn't shippable without your one follow-up change. Says nothing about conversation quality (convbench never opened). PUSH: RESULTS.md, SEAL-run.sha256.txt, dev_summary.json, dev_out_sample.jsonl, train_summary.json, train_log.jsonl, ledger.
