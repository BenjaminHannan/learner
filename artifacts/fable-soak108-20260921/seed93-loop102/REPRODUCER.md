# Scale-step K4 miss (unregistered; NOT a registered FAIL, no re-run)

Command (deterministic plan, timing-sensitive latency bar):
`python -B scripts/fable_soak108_run.py --turns 20000 --seed 93 --kills 5
--graceful 3 --loop102 --artifact-dir
artifacts/fable-soak108-20260921/seed93-loop102`

Reference bars applied: exp-93 K1–K5 wording. Result: K1 0 wrong / 20,000
PASS; K2 8/8 audits clean PASS; K3 boot 1.073 + verify 0.139 = 1.212 s PASS;
K5 20,000 turns in 783.5 s PASS; exactly-once evidence perfect (0 doubled
replies of 20,000; 20,000/20,000 receipt ids exactly once; 3 ghosts dropped
over 9 boots). K4 MISSED: p99 last-1000 1096.26 ms vs 10x p99 first-1000
(661.8 ms), ratio 16.6x.

Localization (read-only post-hoc): checkpoint curve is smooth to 19k
(p50 154 ms, p99 243 ms, 6.25/s) then accelerates in turns 19000–20000
(p50 227 ms, p99 1096 ms, 3.07/s). Slowest daemon-side completions are
scattered across the run (asks and teaches, several right after restarts =
burst catch-up queueing), so no single turn kind is the cliff; the driver-side
submit→reply metric amplifies it under the DEPTH-3 pipeline. Notebook holds
only taught rows (2,000 entities, 14,003 taught FACTs, 0 sleep-derived rows;
no sleep/think/idle event in 20,026 log lines), so the growth is loop102
per-turn work + load, not a runaway hook. Machine contention from parallel
agents cannot be excluded (latency bar is load-sensitive by construction).

Stop per protocol. No re-run into a pass.
