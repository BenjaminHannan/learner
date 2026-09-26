Starting the clock — credit check and duplicate gate first.
Credit check shows a split worth reporting before proceeding.
5090s available at $0.47/hr — fits the $2 budget. Now reading the rest of the run script.
Renting the 5090 now.
Rental #1 live (contract 52669927). Waiting for it to run.
SSH works, 5090 + torch/CUDA ready. Installing transformers.
Model is down (2.1 GB). Running selftest.
Selftest ok. Launching the registered run detached.
Wrong CWD on that launch — relaunching from /root/dl2.
Fast pace (~2.5 min/arm-night). Continuing to poll.
S arm complete (14/14). P arm now.
One night left. Waiting for completion.
Run finished. Pulling the marks block.
Files are back. Verifying marks independently from raw fields before destroying.
Recount matches. Destroying the rental now.
Destroy needs confirmation — retrying.
Rental destroyed and confirmed gone. Now writing the report.
Push raced with another agent — rebasing and retrying.
**Verdict: PASS** (dl-2 registered run, all marks W1–W5 true, proved-wrong false; independent recount of raw night fields matches the JSON marks block).

Integer counts:
- Base TEST (100 fresh puzzles × 20 guesses): lucky L0 = 64, reached 34, greedy 3; HARM right 200/300.
- S final lucky: 237 (s2), 249 (s3); mean 243. W1 bar was 2×64 = 128 → both pass.
- P final lucky: 42 (s2), 51 (s3); mean 46. W5: 243 ≥ 1.3×46 = 60, min S 237 > max P 51 → pass.
- S worse nights (>15% below prior night): 0 of 14 → W2 pass.
- S nights with net harm > 5: 0 of 14 (max 5); final net harm −10, −8 → W3 pass.
- S final reached 62, 60 vs base 34 → W4 pass.
- Proved-wrong: 237/249 > 1.1×64 = 70; 0 worse < 3; 243 > 46 → false. Not inconclusive (64 ≥ 10).
- S night curves: s2 102, 123, 156, 227, 223, 230, 237; s3 101, 155, 179, 235, 209, 210, 249 — gains continued past night 3.
- GPU: RTX 5090 (South Korea). Wall 67.1 min. Dollars ~$0.65 (contract 52669927, dph $0.4852, 1 rental, of $2.00 budget). Code origin/main 589946c9; model openbmb/MiniCPM5-1B @ 87179e5c (same files as blurt-4/5s). Instance destroyed, confirmed gone; results pushed to origin/builder-outbox (RESULTS-gpu.md, gpu/dl2_results.json, gpu/log.txt, ledger line).

Every deviation:
1. First remote launch ran from /root instead of /root/dl2 (relative script/model paths) and died instantly with "can't open file"; relaunched correctly from /root/dl2. No GPU work or data lost; code never edited.
2. Credit gate: `vastai show user` returned balance 0 but credit 5.12. I proceeded on credit (spendable funds ≥ $3.00 gate) and spent ~$0.65. Flagging the ambiguity explicitly.
3. Billed dph $0.4852 vs listed $0.469 (storage adder); still inside budget, kill-line $1.80 never approached.
4. Push to builder-outbox first rejected (another agent pushed concurrently); rebased and pushed cleanly with only the 3 additive paths.
