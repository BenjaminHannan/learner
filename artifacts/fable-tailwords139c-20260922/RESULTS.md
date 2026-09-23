# RESULTS — Exp 139c: lowercase chat-tail strip on loop138b (Muse, 2026-09-22)

Result first: the strip works exactly as directed — all 8 director
examples now save clean ("Ann too"→"Ann", "black now" correction prompts
"change it to black?"), 61/61 probe OK, bench/G3 zero moves — with ONE
registered FAIL: marks123 P4-09, whose sealed expectation literally
encodes the bug (`stored_value: 'Ana, actually'`, note "verbatim
FakeEars value behaviour"). The fix stores "Ana".

## Marks (every seed/case reported)

| mark | bar | got | verdict |
|---|---|---|---|
| T1 probe (61: 31 tail + 15 title + 15 other) | 61/61 OK | 61/61 OK; tail 31/31 exact across all 20 list words x 8 relations (teaches, 5 corrections with yes incl. clean prompts, questions + 2-hop after); title/other stored+replies byte-identical to loop138b | PASS (P139c.1 held) |
| T2 wrong writes | 0; >= 30/31 exact | 0 wrong writes; 31/31 exact | PASS (P139c.2 held) |
| G1 bench 4x200 | 0 new wrong, 0 moves vs sealed loop138b rows | 194/2/4 + 198/2/0 + 150/50/0 + 196/2/2, 0 moves, 0 new wrong | PASS (P139c.3 held) |
| G2 marks123 | per-case = marks138b | p2 64/64, rt81 60/0/14, rt110 62 verdict-identical (both runs), q1/q4/bench/soak/sleep identical, p3 L1-L6 verdict-identical; ONE move: P4-09 (see FAIL) | FAIL (P139c.4 falsified by P4-09) |
| G3 rt136 + rt143 + sessions | 0 new WRONG/write, 0 moves | 135/7/3 + 106/11 + 129/2, 0 moves, 0 new wrong | PASS (P139c.5 held) |
| G4 time | each run < 25 min | probe 1.1 s, bench 28.7 s, marks 430 s, g3 22.7 s, rt110 rerun 613.5 s | PASS (P139c.6 held) |

## Why the FAIL happened (load-bearing, one note)

- G2-P4-09: the P4 suite's sealed expectation for "Mira's teacher is
  Ana, actually." is `stored_value: 'Ana, actually'` — the exact
  WRONG-WRITE this experiment removes. loop139c stores "Ana" (correct
  per the director brief). Stale sealed expectation, same class as
  138b's predicted L5-Z1 flip; I predicted 0 moves, so it records FAIL.

## Cosmetic-only notes (verdicts identical, not FAILs)

- rt110 M1 (both runs) + T2 (run 1 only; identical on rerun): only the
  harness log `statuses` metadata differs ([] vs ['write']); replies,
  fact_writes and agent_verdict identical. Known mailbox-race shape;
  rerun reported both (run1: T2+M1 metadata; rerun: M1 only).
- p3 L6: only `replied_before_kill` timing counts differ (11/… vs 6/…);
  correct/wrong/dupes/chain_ok/pass identical all seeds.
- Sleep SKIP reason names the new agent file (expected); verdict SKIP
  identical.

## Deviations (post-seal edits; affected marks re-run in the open)

- D1 (cases, post-seal): T30 lacked a pre-existing Rex-color fact, so no
  correction prompt could fire (registered run: 60 OK + 1 FAIL-PROMPT;
  stored value was exactly "green" — agent correct, case wrong). Added
  the "Rex's color is red." setup turn, regenerated cases139c.json,
  re-ran probe in the open: 61/61 OK. Agent untouched.
- D2 (driver, post-seal): G3 crashed on sealed redteam136-loop138b.json
  (JSONL rows, not one doc); fixed the loader to read JSONL. The crashed
  run kept nothing; the registered G3 is the post-fix re-run. Agent
  untouched.
- Seal: `shasum -c SEAL.sha256.txt` passes for PASSMARKS, config, agent,
  tail module, probe and bench drivers; the 3 D1/D2 files fail as
  reported above. The one change (`fable_fix139c_tail.py`,
  `fable_loop139c_agent.py`) is byte-identical since before the seal.

## What it means

Trailing chat junk no longer reaches the notebook on any teach path
(ears + pre-write + correction prompts carry the clean value), while
800 bench items, 145 junk cases, 143 Q-cases, 131 session turns and the
full marks123 battery behave exactly as loop138b — except the one
P4 case whose seal demanded the junk.

## What it does not mean

Not a clean superset of loop138b by the letter of the seal: P4-09
flips because its expectation requires "Ana, actually"; lowercase
trailing "right" strips even inside "all right" (brief's rule;
capitalised "All Right" is safe); "?"-inputs were never teaches.

Reproduce (Mac CPU, offline, OMP/MKL=1, after seal):
`python -B scripts/fable_fix139c_probe.py --out
artifacts/fable-tailwords139c-20260922/probe139c-loop139c.json`;
`python -B scripts/fable_fix139c_bench.py`;
`python -B scripts/fable_marks123_all.py --agent
scripts/fable_loop139c_agent.py --config
artifacts/fable-tailwords139c-20260922/loop139c-config.json --out
artifacts/fable-tailwords139c-20260922/marks139c --workers 4`;
`python -B scripts/fable_fix139c_g3.py`.
Questions for Ben: should P4-09's sealed expectation ("Ana, actually")
be updated to "Ana", or is verbatim storage of "actually" intended?
