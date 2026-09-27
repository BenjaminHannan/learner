# Exp 138d RESULTS — morning integration (138b + 10 late fixes)

IN (all 11 ported read-only): 142 speed index (swap + FastReasoner142 +
patch_chain142 + patch_loop121_teach + _patch_relation), 138c serving rule,
146d doubt, 153 reverse questions, 154 yes/no, 155 inverted frames (x135),
156b small talk, 157 fillers, 158 question forms, 159 hop-through-names,
150b clause-swallow guard. OUT: FastQuestionMixin142 "?" reroute only — it
bypasses 138b's sealed 148b neg/time screen and the 132 rewriter; porting it
changes two other pieces' behaviour. No rule changes after the seal
(`shasum -c SEAL.sha256.txt` passes). Ledger P138d.1–P138d.7 appended first.

## Marks table (counts are integers; every seed/case reported, never averaged)

| mark | bar | number | status |
|---|---|---|---|
| M1 piece probes | each at own bar | 142: 500/500 identity; 138c: 4/4; 146d: 21/21 (H13 ok, H17/H18 fail exactly as on 146c); 153: 50/50 0 writes; 154: 54/54 0 writes; 155x135: 5/5; 156b: 116/116 + T2 68/68; 157: 60/60; 158: 59/59; 159: 48/48 0 writes; 150b: 49/49 (42.8 s) | PASS |
| M2 bench121 | 0 new wrong vs 138b | new 194/4, old 198/0, edit200 150/50/0, bench132 196/1: 0 new wrong; 1 move bench132-152 wrong→abstain, listed (107.7 s) | PASS |
| M3 marks123 | per-case = marks138b, moves predicted or listed | rt110/p2/p4/q1/q4/bench/soak verdict-identical (rt110 S1 OK→BUG + 5 still-BUG same as 138b); l5z1 turns 49+58 CLARIFY→MISSING_FACT (predicted 154 honest replies); rt81 D_q_vs_s-04 OK→UNCLEAR (predicted), D_q_vs_s-03 OK→UNCLEAR (extra, listed), I_edges-03 UNCLEAR→OK (improvement, listed). p3-l5z1 and rt81 FAIL labels inherited from 138b (279 s) | PASS |
| M4 junk/red/sessions | 0 new WRONG, 0 new junk writes | redteam136: 4 new WRONG-WRITE (C124/C127/C129 inverted teaches, C142 all-caps shout); cases139b: 2 new WRONG-WRITE (C10/C21 compound inversions, garbage parses e.g. "Tom and Ann's boss is Lena's boss"); redteam143: 1 new WRONG-ANSWER (M3 yes-no "Yes — Norland's capital is Aldport" where abstain sealed); sessions152: 0 new WRONG, 129→165 OK, 3 new writes are correct filler-teach saves (predicted S2 gains) | FAIL |
| M5 sleep + soak | z104 3/3, 0 wrong; 3000-turn 10-kill exactly-once | seeds 1–3: installed, probes 5/5, taught 50/50, at parity with 138b (`wrong_install=1` is the checker's filename read, per 138b RESULTS — not a wrong install); Z4 run 1 harness CRASH ("daemon died before the kill", 138b Z4 passed) / run 2 PASS (marker 0, boot_ok, word absent, probes 5/5, taught 200/200, restore 5/5 — field-for-field 138b parity, both runs reported per sealed F3); Z5 exact 138b parity (noise4 install 5/5, noise8 no-install 5 abstains); dedicated soak 3000 turns/seed 931/10 aimed kills/0 graceful: K1 0 wrong PASS, K2 no lost/dup PASS, exactly-once receipts 3000/3000 clean, K3/K5 PASS (561.4 s), K4 p99-growth mark FAIL (135→4517 ms, 33x; 138b soak also FAIL overall — its K5 time 1500.6 s) | FAIL |
| M6 15k-fact asks | p50 < 50 ms (138b 4008 ms) | doorway-built 15k notebook, 25 asks/arm: 138d p50 5383 ms vs 138b p50 3872 ms (321 s) | FAIL |
| M7 time | every run < 1500 s | m1 42.8 s, bench 107.7 s, marks wave 279 s, speed 321 s, junk/sessions/143 < 120 s, z4+z5 completion 519.5 s, soak 561.4 s | PASS |

## Why each FAIL happened (one diagnosis note each)

- M4: pieces 155 + 154 widen the accept/answer surface past 138b's sealed
  abstain boundary. The 155 reverser saves inverted-shape teaches the base
  deliberately refused (sealed nowrite): plain inversions (C124/C127/C129),
  the shouted variant (C142), and compound inversions it mis-parses into
  junk (C10/C21). The 154 answerer says "Yes — …" to an ungrounded ask (M3)
  where the seal demands abstain. Their M1 probes passed because the sealed
  probes never contained refused-inversion or ungrounded-yes/no shapes.
- M5: registered FAIL stands (Z4 crashed on the sealed run; a FAIL is never
  re-run into a pass). The completion runs measured what was missing: Z4's
  retry passes at field-for-field 138b parity (mailbox-race family, both runs
  reported per sealed F3), Z5 is at exact 138b parity, and the 3000-turn soak
  proves exactly-once (0 lost/dup/wrong, K1/K2/K3/K5 pass). Its K4 latency
  mark fails — p99 grows 33x as teaches accumulate (index helps early: 135
  vs 138b's 630 ms at 1k; same ~4.5 s ceiling at 3k) — same root cause as M6.
- M6: with the FastQuestionMixin142 "?" reroute OUT (honest OUT, sealed), the
  index covers store+reasoner but the composers still scan all triples per
  ask — 138d is slower than 138b (5383 vs 3872 ms). P138d.6 predicted the
  miss (confirmed) but also predicted improvement (falsified).

## Deviations / notes

None from the sealed plan; no re-runs into passes (the Z4 retry + soak + Z5
are the unfinished sealed steps, both Z4 runs reported per sealed F3; no race
flakes seen elsewhere, so no other open re-run was needed). A prior agent
wrote this file through M4/M6; the resume completed M5 (new helper
`scripts/fable_loop138d_sleepz5.py`, `--only z4,z5n4,z5n8`) and updated the
M5/M7 rows only — PASSMARKS.md and config untouched. Soak K4 (p99 <10x) is a
driver-internal mark outside the sealed exactly-once bar, listed as found.
Delivered after the 06:20 target. M6 slower-than-base was not predicted and
is reported as found.

## What it means

The 10-piece stack composes cleanly (M1 11/11, M2 0 new wrong, M3 moves
listed, sessions +36 OK with 0 new WRONG): small talk, fillers, question
forms, doubt, reverse, yes/no-patterns, hop-names and the guard all hold.

## What it does not mean

It is not shippable: inverted-frame teaches and ungrounded yes/no answers
write/say things the base refused (M4), the kill-9 soak was never proven
(M5), and asks are slower, not faster (M6).

## Questions for Ben

None — defaults taken (honest OUT on the "?" reroute; FAILs recorded as FAIL).

## Reproduce (each < 1500 s; `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`;
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`)

- `scripts/fable_loop138d_m1.py` → `m1-138d.json`
- `scripts/fable_loop138d_bench121.py` → `fable_bench121_summary_loop138d.json`
- `scripts/fable_marks123_all.py --agent scripts/fable_loop138d_agent.py --config artifacts/fable-agent138d-20260922/loop138d-config.json --out artifacts/fable-agent138d-20260922/marks138d --workers 4`
- `scripts/fable_loop138d_junk.py`, `…_redteam143.py`, `…_sessions.py`
- `scripts/fable_loop138d_sleepdrive.py --only z104`; completion of the
  unfinished remainder: `scripts/fable_loop138d_sleepz5.py`
  (`--only z4,z5n4,z5n8`); `scripts/fable_loop138d_soak.py`
- `scripts/fable_loop138d_speed2.py` → `speed138d.json`
