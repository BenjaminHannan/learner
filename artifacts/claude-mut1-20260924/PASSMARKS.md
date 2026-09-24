# EXP mut-1 — PASSMARKS (sealed 2026-09-24, before any run)

Report-only mutation test on the 274 base
(scripts/claude_loop274_agent.py, verified PASS M1-M4): do our tests catch
broken sleep/listen code? CPU only (GPU: no).

## Mutants (each a NEW file wrapping 274 with ONE deliberate break)

- scripts/claude_mut1_k1.py — k1: step order swapped back
  (sleep_due before inbox; 274 reply-first turn kept).
- scripts/claude_mut1_k2.py — k2: inbox branch dropped from step()
  (listening tick never chosen by step; turn kept).
- scripts/claude_mut1_k3.py — k3: sleep never due (sleep_due always
  False; step order and turn kept).
- scripts/claude_mut1_k4.py — k4: listening tick replaced by the
  thinking tick (inbox branch runs _thinking_tick; order/turn kept).

No existing file is edited. Fictional names only (the M1/M2/M4 cases use
the 274 test's invented pool). No sealed TEST-ONLY panel is read item by
item; the 292t/273 90-turn panel runs only as the M3 scorer input, once
per arm, counts only.

## Suites (same code for K0 and every mutant)

- S124: scripts/claude_loop274_test.py run_m124 (its M1 reply-before-sleep
  20/20, M2 sleep-within-3-ticks 20/20, M4 deaf meter). K0 runs the script
  directly; mutants run the SAME function with the mutant module standing
  in for the 274 arm builder (T.A274 = mutant; 273 comparison arm
  untouched, same seeds, same 0.5 s stub sleeper).
- SMOKE: scripts/fable_sleepsmoke206.py with the arm's agent script and
  artifacts/claude-join292t-20260923/loop292t-config.json (threshold 75).
- M3: scripts/claude_join292t_run.py panel (arm in the 273 slot, same
  sealed panel artifacts/claude-joinpanel292t-20260923/panel.jsonl, same
  loop292t config) scored once by scripts/claude_join292t_score.py via the
  274 test's run_m3 against recorded gold
  (artifacts/claude-loop273-20260923/run273/panel-273.json +
  panel-score273.json). Comparison arms cannot be touched by a slot-only
  mutant, so the recorded comparison runs serve as both new and recorded
  (byte-identical by construction); only the slot arm is re-run per
  mutant. A panel M3 verdict FAIL = caught by M3; PASS = blind spot.

## Marks

- K0 unmutated 274 passes every suite (same numbers as 274's results):
  M1 20/20 (273 arm 0/20), M2 20/20, M4 relational bars, M3 90/90
  identical incl. 4/4 comparison reruns, smoke sleeps >= 1 baseline.
- K1 each mutant is caught (at least one suite FAILS): 4/4. A mutant no
  suite catches = a test gap: reported, never fixed.

## Predicted catch table (predictions, not claims)

| mutant | S124 (M1/M2) | SMOKE | M3 panel |
|---|---|---|---|
| k1 sleep-first | FAIL M1 (sleep runs inside turn) + M2 (sleep already spent) | same as K0 (blind) | PASS identical (blind: sleep never due in panel) |
| k2 no inbox | FAIL M1 (inbox never drains) | FAIL (replies empty, probes differ) | FAIL (replies change) |
| k3 never due | FAIL M1 (precondition 0/20) + M2 (no SLEEP ever) | FAIL (0 sleeps vs K0 >= 1) | PASS identical (blind spot) |
| k4 think-listen | FAIL M1 + M2 (inbox never drains, shadows sleep) | FAIL (replies empty) | FAIL (replies change) |

SMOKE catch rule: sleeps_logged == 0 while K0 >= 1, or probes_right /
installed / broken_chain differs from K0. M4 reported per arm (no
catch claim attached).

## Verdict rule

PASS only if K0 holds every bar AND K1 is 4/4 (each mutant caught at
least once). The which-suite-catches-which table is reported as measured;
any uncaught mutant is reported as a test gap with its blind suites.
