Building the chain-subject lift — reproducing the gap and verifying the fix.
I've confirmed the failure mode — now digging into the base agent to design the lift.
Gap confirmed on verb and when-questions with chain subjects — now mapping the full scope.
The verb-reader mechanics are clear — now checking the notebook-gated readers.
Build pattern mapped — now drafting the dev dialogs and the lift.
Design settled — now writing the dev set and the lift.
Lift core written — now the agent wrapper.
Lift works on all verb forms with correct values and honest abstains — now sealing the dev set.
Judge was checking setup turns too — narrowing to the final turn.
All 44 dev dialogs pass — now piloting the frozen suites.
Scorer and driver ready — generating config and starting pilots.
rt136 matches 138m exactly — now rt143 and restart probes.
No moves on ghost probes — running the remaining M3 pilots.
M3 pilot clean — now latency.
Path typo — rerunning with the right pred file.
Pilots all green — checking seal conventions before writing PASSMARKS.
PASSMARKS written — sealing now.
Registered M2–M4 pass — pulling the exact numbers.
Panel is up — copying it unchanged and verifying the seal.
138m reproduces the sealed base rows exactly — now the 266 arm.
**Verdict: FAIL** (M1 chain_verb 19/30 and chain_verb_three 1/6 miss the bars; M2, M3, M4 all pass exactly as predicted). Full report in `artifacts/claude-chain266-20260923/RESULTS.md`. No panel item is quoted anywhere; ids and counts only.

## Marks table (integer counts; 138m beside every figure)

| Mark | Bar | 138m | 266 | Pass? |
|---|---|---|---|---|
| M1 chain_verb (30) | ≥ 27 right | 8 | **19** | FAIL |
| M1 chain_verb_three (6) | ≥ 5 right | 1 | **1** | FAIL |
| M1 chain_possessive (10) | no 138m-RIGHT item lost | 10 (c266-037–046) | 10, same ids, identical replies | PASS |
| M1 broken_chain (12) | 12 honest abstain | 12 | 12 (c266-047–058) | PASS |
| M1 wrong over 80 | 0 | 0 | 0 | PASS |
| M1 question writes | 0 | 0 | 0 | PASS |
| M1 plain_control (14) | 14 identical | — | 14/14 identical | PASS |
| M1 statement_control (8) | 8 identical | — | 8/8 identical | PASS |
| M2 sessions152 / bench / marks123 | moves = predicted (0/0/0) | — | 0 / 0 / 0 | PASS |
| M2 rt136 (145 rows) | = C019–C031 + C076 + C079 | same set | exactly that set (13 WRONG-WRITE + 2 reply-only) | PASS |
| M2 rt136 direct vs 138m rows | [] | — | [] | PASS |
| M2 63 inherited exceptions identical | 63/63 | — | 13/13 + 25/25 + 25/25 | PASS |
| M2 rt143 no-gate (124 rows) | 0 moves, 0 flips | — | 0, 0 | PASS |
| M3 restart+verifier (115 dialogs, 7 restart audits) | 0 changes/ghosts/dup-fails/write-changes | — | 0 / 0 / 0 / 0 | PASS |
| M4 latency (624 turns/arm) | ≤ +5 ms | 2.489 ms | 2.448 ms (−0.04 ms) | PASS |
| Dev pilot (44 dialogs, not a gate) | — | 14 MISS + 6 MISS | 14 RIGHT + 6 ABSTAIN, 24 identical, 0 question writes | as predicted |

## Every move and every miss

- **Lifted on dev (20):** d01–d14 MISS→RIGHT (live, work-for, was-born-where, work-where, speak; 2-link, 3-link, my-chains); d17, d18, d20, d21, d22, d44 MISS→honest ABSTAIN (broken chains).
- **Panel gains (11):** the 8 already right on 138m plus 11 lifted to RIGHT.
- **Panel misses (16):** chain_verb c266-005, 008, 009, 015, 016, 017, 018, 019, 020, 023, 028; three c266-031, 032, 033, 035, 036. 15 of 16 are byte-identical on both arms (lift did not fire); c266-009 went OTHER→ABSTAIN (fired, abstained). Zero WRONG on either arm on any of the 80 items.
- **M2/M3 moves:** rt136 C019–C031, C076, C079 only (all inherited/pre-predicted); nothing else moved anywhere.

## Diagnosis (one note)

The lift fires only when the placeholder probe yields one one-hop ask frame; the 15 identical misses are three shapes the specced gate cannot see: (a) 5 when-birthday questions — no plain-name reader exists (out of scope by design); (b) 8 two/three-link questions with two-word-name bases — the detector assumes a single-token base so the probe clarifies; (c) 2 wh-city "my" forms — the notebook-gated reader yields no ask frame for the unknown placeholder. Nothing was guessed.

## Deviations

1. Driver-only path fix after seal (2 lines in `claude_266_runall.sh`, diff in RESULTS.md): M3b filenames vs scorer expectation. No suite re-run; only the read-only scorer ran after. All other 20 sealed files still verify OK.
2. Post-seal additive helper `scripts/claude_266_panelrun.py` (panel runner, no agent logic).
3. 266 rows scored by a byte-identical copy of the sealed scorer (sha verified); the in-place scorer reproduces the writer's base table exactly, and my 138m run reproduces sealed `base138m.jsonl` 80/80.
4. Panel 138m run started at load 65.87 (rule says wait at >60); waited to 58.79 for the 266 run. Timing only; determinism proven 80/80.
5. `seconds`-field exclusion in the 63-row check (pre-registered). No 5× reruns needed.

## What it means / doesn't mean (plain high-school English)

- **Means:** the trick works where it can see the question — the agent answers verb questions about "someone's someone" by re-asking itself the possessive version it already knew (8→19 on blind verbs), and it still says "I don't know" instead of guessing whenever a link is missing. Nothing else changed: no wrong answers, no new writes, frozen tests and speed untouched.
- **Doesn't mean:** the gap is closed — birthday questions, two-word names, and some "my" city questions still go unanswered, so the verdict is FAIL. It says nothing beyond the 80 sealed items, each run exactly once with no tuning.

**Push:** not done. OPUS-RULES forbid commits/pushes and this environment denies `git push`; all files are in the worktree ready: `artifacts/claude-chain266-20260923/` (+ untouched `artifacts/claude-chainpanel266-20260923/`), `scripts/claude_fix266_chainlift.py`, `scripts/claude_loop266_agent.py`, `scripts/claude_266_devscore.py`, `scripts/claude_266_runall.sh`, `scripts/claude_266_score.py`, `scripts/claude_266_panelrun.py`, and the appended `artifacts/fable-predictions-ledger.md` (P266.1–6).
