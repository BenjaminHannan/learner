# EXP mut-1 — RESULTS (verdict: PASS, K0 holds, K1 4/4)

Report-only mutation test on the 274 base
(scripts/claude_loop274_agent.py, verified PASS): do our tests catch
broken sleep/listen code? Four NEW mutants, each wrapping 274 with ONE
break (no existing file edited). CPU only (GPU: no).

**Verdict: PASS.** Unmutated 274 passes every suite with the same numbers
as 274's results, and all 4 mutants are caught by at least one suite
(4/4). No mutant escapes every suite, so there is no full test gap. Two
suites have blind spots (reported, not fixed): the 90-turn panel cannot
see sleep-timing breaks (k1) or sleep-never-due (k3); the sleep smoke
cannot see sleep-never-due (k3) because unmutated 274 itself logs zero
sleeps in that harness.

## Marks table (integer counts)

| mark | bar | result |
|---|---|---|
| K0 M1 274 reply-before-sleep | 20/20 (273 arm 0/20) | 20/20 (273 0/20, reply-match 20/20, preconditions 20) |
| K0 M2 sleep within 3 idle ticks | 20/20 | 20/20 |
| K0 M4 deaf meter | max274 < max273, median ≤ 2 s | PASS (0.00468/0.19425 s vs 273 0.51546/0.51860 s) |
| K0 M3 panel agreement | 90/90 identical | 90/90, 0 moved, 0 overlaps, 0 wrong, per-turn 90/90, arms 4/4 |
| K0 smoke baseline | report | sleeps 0, installed 0, probes 0/5 (abstain 5), taught 50/50, broken abstain |
| K1 k1 caught (sleep-first step) | ≥ 1 suite FAILS | CAUGHT by S124 (M1 0/20, M2 0/20) + SMOKE (sleeps 1 vs 0, probes 5/5 vs 0/5) |
| K1 k2 caught (no inbox branch) | ≥ 1 suite FAILS | CAUGHT by S124 (M1 0/20, M2 0/20) + SMOKE (taught 0/50, probes wrong 5) + M3 (45/90 FAIL) |
| K1 k3 caught (sleep never due) | ≥ 1 suite FAILS | CAUGHT by S124 (M1 0/20 with preconditions 0, M2 0/20) |
| K1 k4 caught (think-for-listen) | ≥ 1 suite FAILS | CAUGHT by S124 (M1 0/20, M2 0/20) + SMOKE (taught 0/50, probes wrong 5) + M3 (45/90 FAIL) |
| K1 total | 4/4 | 4/4 |

## Which suites catch which mutant (measured)

| mutant | S124 (M1/M2/M4 test) | SMOKE | M3 panel |
|---|---|---|---|
| k1 sleep-due-before-inbox | FAIL/FAIL (M1 0/20, M2 0/20; M4 FAIL) | CATCH (1 sleep + install + 5/5 probes vs K0 0/0/0-0-5) | PASS 90/90 — blind |
| k2 inbox branch dropped | FAIL/FAIL (M1 0/20, match 0/20; M2 0/20; M4 FAIL) | CATCH (taught 0/50, 5 wrong probes, broken wrong) | FAIL 45/90, 45 moved — caught |
| k3 sleep never due | FAIL/FAIL (M1 0/20, pre 0; M2 0/20; M4 PASS) | identical to K0 on all 9 fields — blind | PASS 90/90 — blind |
| k4 thinking for listening | FAIL/FAIL (M1 0/20, match 0/20; M2 0/20; M4 PASS) | CATCH (taught 0/50, 5 wrong probes, broken wrong) | FAIL 45/90, 45 moved — caught |

No mutant went uncaught: test gap = none. Suite blind spots: M3 sees
neither k1 nor k3; SMOKE sees nothing in k3.

## Every move, every miss, deviations

- Moves: k2/k4 move 45/90 panel turns each (per-turn 45/90 vs recorded
  273); k1/k3 move 0. Smoke probe/taught moves as tabled above.
- Misses: 0 against the bars (K0 all PASS with 274's numbers; K1 4/4).
- Deviations (6, all procedural, reported):
  1. OPUS-RULES.txt missing at the tasked path; used the identical copy
     at handoff/kit/briefs/OPUS-RULES.txt, same key rules as 274.
  2. Two sealed smoke predictions were wrong; corrected here against
     measured K0 (no re-seal, no file changed): K0 smoke logs 0 sleeps,
     not ≥ 1 (274 defers the due sleep past the harness STOP — daemon
     idle ticks need 30 s of inbox silence, stop exits first; end state
     shows experience 81 ≥ threshold 75 with counters.sleeps 0). And
     smoke catches k1 (sleeps 1 vs 0) instead of being blind to it.
  3. Mutant m124 runs call the SAME run_m124() with the mutant module as
     the 274-arm builder; 273 arm, seeds, sleeper, bars unchanged.
  4. M3 per mutant re-runs only the slot arm; recorded comparison files
     serve as both new and recorded (slot-only mutants cannot touch
     them; arm_match 4/4 True by construction, reported).
  5. Load 10–19 (under 60), disk 60 GB free (over 3 GB); 15 suites
     strictly sequential, one process, OMP/MKL threads 1.
  6. No git commit/push (OPUS-RULES forbids); PUSH list delivered as
     present files. No tracked file modified; seal re-verified OK after
     all runs. MiniLM snapshot present; nothing downloaded.

## What it means / doesn't mean (plain high-school English)

- Our sleep/listen tests work: all 4 ways of breaking the code got
  caught (4/4). The reply-before-sleep test (M1/M2) catches every single
  break — it is the net that never misses here.
- Two weaker spots, not failures: the big 90-turn panel can't see
  sleep-timing bugs (it never lets sleep go due, so k1 and k3 look
  identical there — 90/90), and the sleep smoke can't spot
  sleep-never-due (k3 looks exactly like normal 274 there, because normal
  274 also logs zero sleeps in that harness). Each of those mutants is
  still caught elsewhere, so nothing escapes entirely.
- This does NOT grade answer quality, does NOT test the reader/ear
  stages, and does NOT say what would happen with message wordings or
  sleep shapes never tried here — only the 20 seeded cases, one smoke
  world, and one 90-turn panel, counted above.

## Detail (counts only, never quoted)

- S124: 20 seeds × mutant arm vs 273 arm, threshold 5 + 5 prefilled rows,
  0.5 s never-accepting stub both arms. k1: sleeps-after-turn 1/case,
  inbox drained, reply-match 20/20. k2: inbox never drains, match 0/20.
  k3: preconditions 0/20, match 20/20. k4: inbox never drains, match
  0/20. M4 medians/maxima as tabled (k1 FAIL, k2 FAIL, k3 PASS, k4 PASS).
- SMOKE: 80 turns + 1 broken-chain probe, threshold 75. k1 150.4 s (real
  sleep ran inside the turn); k2/k4 ~39 s; k3 14.4 s ≈ K0 14.6 s.
- M3: 78 dialogs / 90 turns, slot arm re-run per mutant, scorer +
  run_m3 vs recorded 273 gold. k1/k3 score files identical on all 11
  fields; k2/k4 agree 45/90 with 45 moved ids, per-turn 45/90.
- Raw evidence: /tmp/mut1/m124-{k0,k1,k2,k3,k4}.json,
  smoke-{k0,k1,k2,k3,k4}.json, panel-{k0,k1,k2,k3,k4}.json +
  probes-*.json, m3-*.json (local rerun evidence, not pushed).
