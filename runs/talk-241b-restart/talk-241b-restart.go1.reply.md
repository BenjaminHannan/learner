Rebuilding the mouth stage — inventorying your brief and prior work.
Your prior seal is missing here — I'll verify the workspace state.
Stylesheet verified. Now pulling the registered briefs and prior state.
History understood. Now inventorying the existing v2 code.
Inventory is done — now checking machine load before running anything.
Unit tests pass 29/29. Now pulling the dev material and driver usage.
All 42 old misses changed with zero sub-mark hits. Now the M2a/M5 pilot.
Load is high but I'll start the dev suite pilot (228 baseline + 241b) to get the M3/M2/wall signal.
228 baseline clean (0 moves, 31.5s). Now the 241b dev suite run.
Dev pilot fully green. Now verifying the sweep generator and pairs sampler meet the brief.
Generators check out. Gathering the last details for PASSMARKS.
All details confirmed. Writing PASSMARKS (stylesheet embedded verbatim by script).
Stylesheet verbatim. Sealing now.
Fresh sweep sealed in 0.9s (1205, all route A). Now the pairs.
Both seals verify 23/23. Starting registered runs: M2a + M5 on the fresh sweep.
M2a and M5-latency pass on the fresh sweep. Load is high — waiting briefly before the registered wall runs.
Sleep identical, M3 run1 clean. Running the registered checks.
All 28 sub-marks zero on the fresh sweep. Final verifications for RESULTS.
Everything verified. Writing RESULTS.md.
**Verdict: BUILD half done, not a PASS — two flags for the director.** M2 (a/b/c), M3, M5-latency, sleep smoke, and all 28 mechanical M1 sub-marks pass. M1-grader and M4-judge are unscored by design (I never grade; you launch fresh graders/judge). Flag 1: M5 suite wall missed at +8.1% (bar +5%), measured at extreme load. Flag 2: the S1 script exits 1 on 241b's own rows with 22 listed diffs — all intended, verdicts 100% identical; you rule on S1.

**Marks (integer counts)**

| mark | bar | result |
|---|---|---|
| M1 grader overall / per-act | ≥99.0% / ≥97% each | pending (your grader) |
| M1 mechanical (6 S + 22 C) | 0 each | 0/28 on fresh sweep — pass |
| M2(a) | 0 | 0/1205 unfaithful, 0 sev-1, 0 rule-9 fails — pass |
| M2(b) | 0 | 0/7646 (A 7268, passthrough 378, legacy 0) — pass |
| M2(c) | 0 | 1016/1016 normalised identical — pass |
| M3 | GATE clean, reply-only only | GATE clean, 752 moves, 0 verdict changes, 0 abstain flips — pass |
| M4 | win ≥70% non-tie, loss ≤10% | pending (your judge; 120 pairs sealed) |
| M5 latency | med ≤2ms, p99 ≤20ms | 0.172ms / 1.111ms, max 2.056 (n=1205) — pass |
| M5 wall | ≤228+5% | 45.5s vs 42.1s (limit 44.2s), **+8.1% — miss** |
| S1 | 100% verdict identity | verdicts 2400/2400; script lists 22 decision diffs — you judge |
| sleep smoke | identical to 228 | identical except agent/label/seconds — pass |

Walls (D6 alternating; load 160–220 throughout): 228: 42.1, 40.7, 44.3 → med 42.1. 241b: 42.8, 47.1, 45.5 → med 45.5.

**Fresh artifacts + sha256:** sweep.jsonl (1205 replies) `6c837ee3…32b79e`; sweep-frames.jsonl `5ee5c793…f6f4bed`; pairs.jsonl (120) `9f453488…393fd540`; pairs-key.jsonl `f763b6dd…f497fbe7238d54`. All under `artifacts/claude-mouth241b-20260922/`; seals SEAL (19 files) + SEAL2 re-verified 23/23 OK, nothing re-sealed.

**Every move:** M3 run1 vs 138i — rt136 45, rt143 24, sessions152 60, bench 623, all reply-only, 0 new WRONG/WRONG-WRITE/junk/lost-OK. Changed lines by act: SAVED 3953, CONFLICT 721, ANSWER 673, ABSTAIN_MISSING 7. Dev re-render of 241's sweep: 209 lines changed (CONFLICT 20, BROKEN_CHAIN 80, FORGOTTEN_ONE 67, AMBIGUOUS 30, ANSWER_LIST 6, YESNO_NO 3, YESNO_NOTKNOWN 2, SAVED 1), all 42 old misses mechanically "changed", 0 sub-mark hits.

**Every miss:** (1) Wall +8.1%. Mouth render sums 2.2–2.4s of the 3.4s gap (mean 0.30ms/line vs ≈0.28 budget) — caching cut 241's ≈1ms/line (+17%) by ~four-fifths but not enough; run spread exceeds the gap so noise also contributes. (2) S1: 0 diffs on 228's 800 v3 rows and 241's 800 dev rows; on 241b's own 800 rows, 22 decision diffs on 11 items — every one the intended article/case match ("the United Kingdom?" vs "citizen of United Kingdom"), all 11 verdict 'correct' in both runs with equal confirms. 0 verdict diffs anywhere.

**Deviations:** D-A: ran walls at load 160–220 after two waits failed (load rose); alternation shares load, every run <25 min, loads reported. D-B: S1 script flag above, listed in `runs/s1-241b.out`. Nothing else: no sealed file touched, no re-seal, no self-grading, no flake re-runs needed.

**What it means (plain English):** The mouth now only rewords replies — zero wrong answers, zero notebook changes, zero cheating across 1205 fresh + 7646 suite lines. All 42 old grammar mistakes got reworded with no machine-detectable complaints left, but human graders still need to confirm. The scorer change agrees with the old one on all 1600 old rows.

**What it doesn't mean:** Not a PASS — wall missed, M1/M4 unscored, S1 needs your call. Machine-check zeros aren't proof of good English. The +8.1% wall at load 200+ mixes real cost with noise. Pairs are single replies without conversation context. Only fictional names and the 150-relation table are covered.

PUSH set (on disk, uncommitted per rules): `artifacts/claude-mouth241b-20260922` `scripts/claude_mouth241b_*` `scripts/claude_loop241b_*` `scripts/claude_confirm241b*` `scripts/claude_fix172b241b_*` `artifacts/fable-predictions-ledger.md` (9 P241b lines appended, 0 lines changed).
