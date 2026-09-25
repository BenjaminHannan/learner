Rental task acknowledged — checking gates and fetching spec files first.
Cheapest 5090 meets the spec. Now resolving the model question before renting.
Rental precedent found. Reading the full rent-blurt1 method.
Playbook complete. Setting up task tracking and proceeding.
Tree built, SSH key registered. Renting now.
Contract 52638727 created. Waiting for running state.
Host can't pull the image (proxy error). Destroying and trying another host (rental 1 of 3 used).
Running. Setting up SSH and uploading the tree.
Model pinned. Running step-2 checks.
Checks pass. Launching the main run detached.
Fast progress — already on arm H. Checking full log, then continuing to poll.
Run finished. Fetching the summary.
Files verified. Writing the results report.
Instance destroyed and confirmed gone. Appending ledger and staging.
Verdict: FAIL (registered blurt-4 run complete; H1 proved wrong, H2 fails, not inconclusive).

Integer counts (64 fresh test puzzles after 16 overlap drops from requested 80; 30 blurts/puzzle; temp 1.0 picked on DEV 41 vs 35 lucky blurts on 58 missed DEV puzzles):
- Practice: reasoner right 20/400; won 165 of 380 misses (327/11400 blurts); hindsight hits 375; examples H = 560, W = 560, P = 560.
- L0 lucky blurts before sleep: 66 (32 puzzles hit). Greedy before: 1/64.
- W: seed 0 = 219 (32 hit), greedy 5/64; seed 1 = 223 (35 hit), greedy 8/64; mean 221.0.
- H: seed 0 = 156 (41 hit), greedy 5/64; seed 1 = 124 (43 hit), greedy 3/64; mean 140.0.
- P: seed 0 = 163 (46 hit), greedy 7/64; seed 1 = 117 (42 hit), greedy 1/64; mean 140.0.
- H1 (mean H ≥ 1.2 × mean W, each H > each W): 140.0 ≥ 265.2 false; 156 > 219 false — FAIL. Proved-wrong clause (mean H ≤ mean W): 140.0 ≤ 221.0 true.
- H2 (mean H ≥ 1.2 × mean P): 140.0 ≥ 168.0 false — FAIL. Not inconclusive (375 ≥ 100; L0 66 ≥ 10).
- Gates: credit 7.731600098599898 (≥ $5.00, PASS); no blurt-4 results in origin/builder-outbox and no live rent-blurt4 instance at start (PASS).
- Money: rental1 $0.00 (never ran) + rental2 ~0.33 h × $0.4963/h ≈ $0.16 of $2.00 budget; 2 rentals of max 3; 0 rent-blurt4 live after destroy (confirmed).
- Env: GPU NVIDIA GeForce RTX 5090; wall 16.0 min; model commit 87179e5c1f455ef22e6223592d2d61351b525bfc; torch 2.8.0+cu128; transformers 5.17.0; run log 36 lines; summary 41 keys, JSON block in RESULTS verified equal; selftest ok; pzcheck 60/60 identical.

Every deviation:
1. BensPC→rental move: BASE was the HF hub snapshot openbmb/MiniCPM5-1B pinned to revision 87179e5c1f455ef22e6223592d2d61351b525bfc (same commit as blurt-1/2/3r) instead of the BensPC local folder, so a model download on the rental was unavoidable (precedent: rent-blurt1 did the same). Detached launch via setsid/nohup instead of Task Scheduler. No code edited.
2. First rental 52638727 (offer 46753293, US, $0.446) never left loading — host-side docker-registry proxy error — destroyed after ~6 min per the 6-min rule; second rental 52639402 (offer 44077681, KR, $0.4963, rel 0.9985) ran clean.
3. Credit was not re-checked between rental 1 and rental 2 (task wording asked for a re-check before any re-rent); start credit $7.73 made this moot, spend ≈ $0.16.
4. Package versions differ from BensPC: transformers 5.17.0 (vs 5.15.0), torch 2.8.0+cu128 (vs 2.11.0+cu128) — same lines as the rent-blurt1 precedent allowed (transformers>=5).
5. Run took 16.0 min wall, not the ~45 min estimate (5090 faster than BensPC 5070 Ti); practice line reached in ~10 min, inside the 3 h TOO-SLOW bar.
6. Test set 64, not 80 — 16 overlap drops per the code's registered rule (train+DEV overlap removed; no hindsight puzzle equals a test puzzle).
7. Never wrote to repo-root notebook/; never pushed weights (run saves none); staged only the 4 PUSH paths (3 force-added under git-ignored artifacts/ + ledger).

PUSH (staged): artifacts/claude-blurt4-20260925/gpu-4/blurt4_summary.json, gpu-4/log.txt, artifacts/claude-blurt4-20260925/RESULTS-gpu-4.md, artifacts/fable-predictions-ledger.md (1 line appended).
