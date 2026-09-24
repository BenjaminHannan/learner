Running your sleep/listen mutation test — checking if broken code gets caught.
Base checks are green — now digging into how the test suites exercise the agent.
The design is clear. Verifying the daemon turn path and thinker cost before writing the mutants.
All mechanics confirmed. Setting up the work plan and writing the four mutants.
Piloting the four mutants before sealing.
All four breaks behave as designed. Writing PASSMARKS and sealing.
Sealed and verified. Starting K0 (unmutated 274) runs.
K0 m124 passes. Running K0 sleep smoke.
K0 smoke shows zero sleeps — checking whether the smoke world even reaches the threshold before interpreting it.
K0 complete (m124 PASS, M3 90/90 PASS, smoke baseline recorded). Now the mutants — k1 first.
k1 caught by S124 (M1 0/20, M2 0/20). Running k1 smoke.
k1 M3 blind as predicted (90/90 PASS) — but already caught twice. Now k2.
k2 caught everywhere (M3: 45/90 FAIL). Now k3.
k3 smoke identical to K0 on all fields (blind). Running k3 panel to confirm the predicted M3 blind spot.
k3 M3 blind spot confirmed (90/90 PASS) — caught by S124 only. Now k4.
All 15 runs complete. Verifying the seal held and nothing existing was touched, then writing results.
Verdict: PASS — K0 holds every bar with 274's numbers, K1 is 4/4 (every mutant caught by at least one suite). No full test gap.

Marks table (integer counts):

| mark | bar | result |
|---|---|---|
| K0 M1 274 reply-before-sleep | 20/20 (273 arm 0/20) | 20/20 (273 0/20, match 20/20, pre 20) PASS |
| K0 M2 sleep within 3 ticks | 20/20 | 20/20 PASS |
| K0 M4 deaf meter | max274<max273, median≤2s | PASS (0.00468/0.19425s vs 0.51546/0.51860s) |
| K0 M3 panel | 90/90 identical | 90/90, 0 moved, per-turn 90/90, arms 4/4 PASS |
| K0 smoke | report | sleeps 0, installed 0, probes 0/5 (abst 5), taught 50/50 |
| k1 sleep-first step | caught ≥1 | CAUGHT: M1 0/20, M2 0/20, smoke (1 sleep + 5/5 probes vs K0 0/0) |
| k2 no inbox branch | caught ≥1 | CAUGHT: M1 0/20 (match 0/20), M2 0/20, smoke (taught 0/50, 5 wrong), M3 45/90 FAIL |
| k3 sleep never due | caught ≥1 | CAUGHT: M1 0/20 (pre 0/20), M2 0/20 |
| k4 think-for-listen | caught ≥1 | CAUGHT: M1 0/20 (match 0/20), M2 0/20, smoke (taught 0/50, 5 wrong), M3 45/90 FAIL |

Which suites catch which (measured): S124 M1/M2 catch all 4. Smoke catches k1, k2, k4 — blind to k3 (identical to K0 on all 9 fields). M3 catches k2, k4 (45/90, 45 moved each) — blind to k1 and k3 (90/90 PASS). M4 FAILs on k1/k2, PASSes on k3/k4 (reported, no catch claim). Misses: 0. Moves: k2/k4 move 45/90 panel turns each; k1/k3 move 0.

Deviations (6): (1) OPUS-RULES tasked path missing, used handoff/kit copy. (2) Two sealed smoke predictions were wrong, corrected against measured K0 with no file change: K0 logs 0 sleeps not ≥1 (274 defers sleep past harness STOP; idle ticks need 30s silence, end state exp 81≥75 with sleeps 0); smoke catches k1 instead of being blind (sleep-first step runs the due sleep inside the turn). (3) Mutant m124 runs call the same run_m124() with the mutant as 274-arm builder; 273 arm/seeds/bars unchanged. (4) M3 re-runs only the slot arm per mutant; recorded comparison files serve as new+rec (arm_match 4/4 by construction). (5) Load 10–19, disk 60GB; 15 suites sequential, one process. (6) No commit/push per OPUS-RULES (PUSH list = present files); no tracked file modified; seal re-verified OK post-run; MiniLM cache present, nothing downloaded.

What it means (high-school English): our sleep/listen tests work — all 4 breaks got caught, and the reply-before-sleep test is the net that never misses here. What it doesn't mean: the big panel can't see sleep-timing bugs (never lets sleep go due), and the smoke can't spot sleep-never-due (normal 274 also logs zero sleeps there) — each still caught elsewhere, so nothing escapes entirely. Nothing here grades answer quality or covers wordings/sleep shapes never tried.

Files (all present, additive-only): scripts/claude_mut1_k1..k4.py, artifacts/claude-mut1-20260924/PASSMARKS.md, SEAL.sha256.txt, RESULTS.md, results.json. Raw evidence in /tmp/mut1 (not pushed).
