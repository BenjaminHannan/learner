# slp-367 blind recount (2026-09-25)

Source: raw per-arm keys of `results.json` only (`IDLE-s1`, `FORCED-s1`, `IDLE-s2`, `FORCED-s2`). I did not use the stored `marks` key to get these numbers. I compared with it afterwards, and it agrees on every mark and detail.
Turn kinds come from `fable_sleep104_drive.build_turns()`: 50 teaches, 20 episodes, 5 fillers, then 5 probes. The test adds the Q99 probe.

## Marks

| Mark | Seed | Recounted value | Bar | Result |
|---|---|---|---|---|
| P367.1 sleeps inside a user turn (IDLE) | 1 | 0 | 0 | PASS |
| P367.1 | 2 | 0 | 0 | PASS |
| P367.2 word installs + new-people probes | 1 | installed; 5/5 | installed; ≥ 4/5 | PASS |
| P367.2 | 2 | installed; 5/5 | installed; ≥ 4/5 | PASS |
| P367.3 teach + filler replies identical to FORCED | 1 | 55/55 | 55/55 | PASS |
| P367.3 | 2 | 55/55 | 55/55 | PASS |
| P367.4 quiet: 3 turns, 60 s idle | 1 | THINKING | not SLEEP | PASS |
| P367.4 | 2 | THINKING | not SLEEP | PASS |
| P367.5 quiet: then 30 min idle | 1 | SLEEP | SLEEP | PASS |
| P367.5 | 2 | SLEEP | SLEEP | PASS |

Probe verdicts checked against the world (shown). Each chain is taught as `Txx's mother is Nxx` and `Nxx's mother is Hxx` (`build_turns`, lines 76-83). Each reply is exactly "Txx's maternal grandmother is Hxx." for T01-T05, in both arms and both seeds, so all five "correct" verdicts are right. `classify` is a substring test for "Hxx", so here it can't be fooled by a near-miss name. The Q99 reply in all four arms is "I don't know anyone called Q99.", which counts as abstain.

## Report-only

| Seed | Episode replies that differ (IDLE vs FORCED) | Differing IDLE replies: right / wrong / "I don't know" | IDLE episodes overall | FORCED episodes overall | Idle sleeps (main run) |
|---|---|---|---|---|---|
| 1 | 10 (K11-K20) | 10 / 0 / 0 | 10 right, 10 "I don't know" (K01-K10) | 20 "I don't know" | 7 (+1 in the quiet check) |
| 2 | 10 (K11-K20) | 10 / 0 / 0 | 10 right, 10 "I don't know" (K01-K10) | 20 "I don't know" | 7 (+1 in the quiet check) |

Ground truth (shown): `truth[(K11,'mother')] = M11` and `truth[(M11,'mother')] = G11`, so G11 is K11's maternal grandmother. The same holds for K12-K20. The idle sleep after turn 60 (built from the K01-K10 episodes) installed the word, and turns 61-70 then answered with it. Idle modes in both seeds: THINKING and SLEEP alternate (a sleep after turns 10, 20, … 70), then THINKING at 75 and on all 3 evening steps.

## Seal

From the tree root, `shasum -a 256 -c artifacts/claude-slp367-20260925/SEAL.sha256.txt` reports OK for `claude_slp367_idle.py`, `claude_slp367_test.py` and `PASSMARKS.md`. Timestamps: the seal and sealed files are from 02:29:39 and `results.json` from 02:38:43. (Run from inside the artifact directory, the check fails with "No such file", because the paths are relative to the root.)

## Concerns

1. **P367.1 passes by construction (shown, from the code).** `sleep_due367` returns False whenever `in_turn` is set, and the only thing counted is a `_sleep_tick` call made while `in_turn` is set. The mark can fail only if some code path sleeps without calling `sleep_due`. I found none: `turn → run_until_idle → busy()/step() → self.sleep_due()/self._sleep_tick()` in `fable_agent_loop.py` lines 287-317. The guard did get used, though. The experience count reaches 10 inside turns 10, 20, … 70, and without the guard the base `run_until_idle` would have slept inside those turns. `blocked_in_turn` records this but is not saved to results, so the evidence is indirect (suggested → shown from the code plus the idle_log pattern).
2. **P367.4 and P367.5 are arithmetic checks of the rule on a fake clock (shown).** 3 rows < 10 and 60 s < 1800 s gives no sleep. 1860 s ≥ 1800 s gives a sleep. They show the rule is wired up, not how it behaves in real time. P367.5 measures time since install or the last sleep, not since the last message. The mark's wording, "30 min idle", sounds stricter than the rule, which is "30 min since the last sleep". The test can't tell the two apart. In the real daemon an idle step only happens after `idle_seconds` with no mail, which reduces this gap (suggested).
3. **The "broken-chain probe" in PASSMARKS is really an unknown-name probe (shown).** Q99 is never taught. The reply is "I don't know anyone called Q99", which does not test a person whose mother is known and whose grandmother is not. It is not a mark, but the description overstates it.
4. **P367.2 is not trivial (shown), but it does not tell the arms apart.** Before the word installs, both arms say "I don't know" to grandmother questions, so the probes need the learned word. FORCED also scores 5/5, so the mark only shows no harm.
5. **The evening doesn't sleep on the last 5 turns (shown).** After the filler burst, 5 new rows are waiting. The 3 evening steps (180 s fake time) stay THINKING, and the test comment ("idle steps until a sleep has run with the day's episodes") holds only because the episodes were already slept after turns 60 and 70. Any teaches in that last burst would wait up to 30 minutes.
6. **The seal covers only the two slp-367 scripts and PASSMARKS (suggested risk, not shown).** The world driver, `claude_slp360_test.py`, `claude_slp360_scrap.py` and the 292t loop code affect the result but are not hashed.
