# Exp 207 RESULTS — atomic inbox writes (driver-only; loop138i unchanged)

## Result
Patch works and is inert: 6/6 patched runs show zero mailbox-race events
(0 lost, 0 doubled, 0 empty file serves) across 6,000 soak turns +
186 rt110 cases, with 2,000 atomic inbox writes per soak run. But the
control is equally clean (0 races in 6/6), so the test is UNDERPOWERED:
loop138i's 141 settle gate already masks the startup race, and the
hypothesis (plain write_text causes the flake) is untested, not refuted.
Registered verdict: PASS WITH TWO DOCUMENTED NOTES. No agent change.

## Marks table (every seed/case reported, never averaged)
| run | mode | suite | lost | wrong | doubled | didnt_catch* | empty_serves | patched_writes | secs |
|---|---|---|---|---|---|---|---|---|---|
| soak-p1/p2/p3 | patched | soak 2000t | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 2000 x3 | 252/269/252 |
| soak-c1/c2/c3 | control | soak 2000t | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0 x3 | 230/231/231 |
| rt110-p1/p2/p3 | patched | rt110 62c | — | — | — | 2/2/2 | 0/0/0 | 376 x3 | 256/153/155 |
| rt110-c1/c2/c3 | control | rt110 62c | — | — | — | 2/2/2 | 0/0/0 | 0 x3 | 115/205/267 |
\* abstain-bit reply on a must-answer turn; the 2 (R4-msg_03 first-name
ask, S6-msg_01 two-sentence turn) are byte-identical in all 6 runs and
the daemon logs show complete turn_text (R4 teach "Saved ... Spain"
fully served) — deterministic loop138i agent behavior, not a race.

A3: rt110 per-case agent_verdict identical across all 6 runs
(ok_to_bug P1/P3/S1 vs sealed loop102 rows — pre-existing 138i-vs-102
agent drift, patch-independent); soak all-pass both arms. No other diff.

## What it means
Atomic inbox writes (`<name>.tmp<PID>.<n>.207` + fsync + os.replace, a
name the daemon ignores two ways) eliminate the half-read window with
zero behavior change, at negligible cost (patched ≈ control timing).

## What it does not mean
It does not prove the patch fixes the 192 flake — the control never
raced, so there was nothing to fix here; the settle gate gets the credit
for the clean controls. Keep the patch anyway: it is free insurance.

## Deviations / notes
None from plan. Seal 6/6 OK post-runs; no post-seal edits; heavy suites
one at a time; scratch pilots deleted. Reproduce:
`OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B
scripts/fable_atomic207.py --mode {patched,control} --suite {soak,rt110}
--agent scripts/fable_loop138i_agent.py
--config artifacts/fable-agent138i-20260922/loop138i-config.json --out DIR`
