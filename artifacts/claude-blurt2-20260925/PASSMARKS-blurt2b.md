# blurt-2b: practise every lucky hit (registered ~06:45 UTC 2026-09-25, before running)

blurt-2 = registered FAIL (VERIFY-blurt2.md): wins beat no-wins in both runs (+11, +6.5) but the gain over S0 was
+11 on CPU and +6 on GPU (bar +8). Ben's aim is to maximise lucky hits; blurt-2 kept only the FIRST lucky hit per
puzzle (173-184 examples) and threw away the rest (313-338 right blurts in total).
One change: --all-hits. W practises every distinct right blurt on each won puzzle (distinct once spaces are ignored); C = own right answers repeated to
the same count. Everything else as blurt-2 (DEV temperature rule, 30 blurts, LoRA r16 3 epochs, seeds 0 and 1).
New practice set (seed 4) and new fresh test set (seed 779), never printed.
Where: one GPU run on BensPC ($0); that run is the registered result. (No CPU repeat.)
Amended 09:25 UTC, before any run started (BensPC is busy with other jobs first; an earlier note here said the job runner had stalled, which was a misread of its local-time clock): the same command also runs on the
thread's CPU ($0, --out artifacts/claude-blurt2-20260925/cpu-b). If both finish, both are reported and PASS needs both
(the blurt-2 rule).

  python -B scripts/claude_blurt2.py loop --model BASE --out gpu-b --temps 1.0,1.5
      --dev-puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl --train-seed 4 --test-seed 779 --all-hits

Marks (same as blurt-2): L1 mean W − S0 ≥ +8; L2 mean W − mean C ≥ +5 and each W seed beats each C seed.
PASS = L1 and L2. Proved wrong: mean W ≤ mean C or mean W ≤ S0. Inconclusive: < 20 won puzzles, or S0 ≥ 60%.
