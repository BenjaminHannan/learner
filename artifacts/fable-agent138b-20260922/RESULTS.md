# RESULTS — Exp 138b: the stack (loop138 + tonight's fixes, Muse, 2026-09-22)

Result first: 11 of 13 pieces stack cleanly in one new file
(`scripts/fable_loop138b_agent.py`; L2 inherited verbatim, no existing
file edited). Gains are large and counted per-item: bench correct
135→194 / 157→198 / 139→196 with edit200 untouched; 143 wrong 17→11
with 12 fixes; redteam136 wrong-write 14→7. Five registered FAILs, each
with one diagnosis note below; four are inherent to the ported pieces
(verified live on their own bases), one is a predicted stale sealed
expectation. B5-E116 was still running at the delivery line and is not
claimed.

IN: 135, 137, 139b, 140, 144, 150, 149, 132 (149-qrewrite shape), 151,
148b screen, sleep145 for sleep131, 141 settle + atomic-write clients.
OUT: 113e (registered FAIL on its own bars; swapping the frozen 113c
gate for the single A2-174 item risks new wrongs), 142 index (needs an
IndexedLoopNotebook lower-layer swap, barred by the brief).

## Marks (every seed/case reported)

| mark | bar | got | verdict |
|---|---|---|---|
| B1 marks123 | per-case = marks138 except L5-Z1 42/43; rt81 0 wrong | p2 64/64 + rt110 62/62 + rt81 74/74 + q1/p4/q4/soak/sleep/l1–l4/l6/L5-Z2 verdict- and reply-identical; L5-Z1 exactly turns 42/43 OK→UNSUPPORTED_QUESTION (predicted); bench-s2fresh 41 abstain→correct (rewriter); edit200 37 reply-only never-item diffs (predicted class); turn-53 stage-tag cosmetic; rt81 suite FAIL label inherited (60/0/14 identical, same bar as 134/138) | FAIL (moves beyond prediction) |
| B2 bench | 0 new wrong vs 138; 069 fix | edit200 150/50/0, 0 moves; old 198/0 (+41 a→c); new 194/4 (+57 a→c, +2 w→c incl. 069 Canberra and 165); bench132 196/2 (+54 a→c, +5 w→c incl. 022 Charleroi, 1 c→a 019). New wrongs: 025/073/149 (officeholder rewrite chains) + bench132-152 (150 "I Believe" hedge on a song name). 174 still wrong (113e OUT, as predicted) | FAIL (4 new wrong) |
| B3 junk | each ≥ own RESULTS, 0 new WW | redteam136 135 OK/7 WW/3 MISSED: 5/5 tail (C117–119/C126 +2 more) + 7/7 and-focus hold; fixes C063/C070/C124/C125/C127/C129/C130; new WW C089/C122 (inherited 137, verified live on loop137); cases150 57/57 verdicts + 19 mouth-render reply diffs (`country_of_citizenship` vs `country of citizenship`, the sealed 138 mouth); f1 26/26 must-write + t14-only write (as sealed); cases139b 101/101, 0 moves | FAIL (C089/C122) |
| B4 143 + sessions | 0 new WRONG vs 138 | 143: 96→106 OK, 17→11 WRONG (fixes B1/F5/H4/J5/J10/N1–N5/T5), 1 new WRONG H5 (rewriter answers; seal demands abstain); sessions152: 129 OK/2 WRONG both arms, 0 moves, 0 new writes | FAIL (H5) |
| B5 sleep145 | install, 0 wrong, taught wins | z104 (1049 s): seeds 1–3 installed, 20 eps, oof 1.0, refit 1.0, probes 5/5, taught 50/50, 0 overwrites; Z4 PASS (restore 5, taught 200/200); Z5 noise4 install 5/5, noise8 refuse+abstain 5/5, 0 wrong. `wrong_install=1` is the checker's `sleep104-word.json` filename read (145 serves `sleep145-words.json`; 145-D2 precedent), not a wrong install. e116 (E-family taught-wins): still running at delivery, NOT claimed | partial (z104 PASS, e116 unclaimed) |
| B6 kill-9 burst | 0 dup/lost/wrong | 4225/6000 turns, 10/10 aimed kills audit_ok, 0 doubled, 4225/4225 receipts exactly-once, 8/8 restart audits clean (K1 `wrong:1` is the driver's binary non-PASS flag, not a counted wrong). Driver hit its own 1500 s budget (settle ≥2 polls/file ≈ 0.35 s/turn vs 138's 0.036) | FAIL (time; exactly-once held) |
| B7 speed | both p50 reported | doorway-built 15k-fact notebook (D3), copied dir, 25 asks/arm: loop138 p50 4119.7 ms, loop138b p50 4008.2 ms (404.5 s). No index (142 OUT); composers scale with triples on both arms | PASS (reported) |
| B8 time | each run < 25 min | B1 479 s, B2 109+44 s, B3 29 s, B4a ~60 s, B4b 21 s, z104 1049 s, B7-backup 405 s; B6 1501 s (over) | FAIL (B6 time only) |

## Why each FAIL happened (all load-bearing)

- B2-025/073/149: the 132 rewriter repairs 113c over-fires into full
  N-hop asks through the catch-all `officeholder` relation, which
  resolves confidently but wrong. Vetoing officeholder rewrites would
  also kill 140 measured correct fixes on the same chains — inherent,
  not tunable without new science.
- B2-152: the 150 hedge list is case-insensitive, so the Title-Case
  song name "I Believe I Can Fly" refuses as "i believe" and the chain
  answers short. 150's probe exempted "I Feel …" songs but never met
  "I Believe …" (its sealed H07 hedge is lowercase "I believe Kip").
- B2-019 (correct→abstain, listed): question-side interaction on the
  "Tu-95" item; does not change the FAIL already set by the wrongs.
- B3-C089/C122: the 137 upgrade accepts any 2–4 Title-case tokens, so
  "Suppose Tom's boss …" and "Hi. Tom's boss …" teach. Verified live
  on loop137 itself (`Saved: Suppose Tom's boss is Ann.`) — inherited
  from the piece, not introduced by the port.
- B4-H5: the rewriter converts H5's clarify into a confident answer;
  the seal demands abstain (the documented H5 expectation error — 149's
  variant A also moves H5). Same rewriter trade as B2.
- B1: the p3 L5-Z1 flip (42/43) is the predicted stale expectation
  (the seal encodes the qualifier-blind OK); the bench-s2fresh 41 are
  the same rewriter fixes as B2; rt81's FAIL label is inherited
  byte-for-byte (60/0/14 per-case identical, same bar as 134/138).
- B6: the 141 settle rule (serve only after two stable polls) costs
  ≈0.35 s/mailbox-file vs 138's 0.036 s; the driver's own 1500 s
  budget aborted the burst at turn 4225. Exactly-once held throughout.

## Deviations (all reported; affected marks re-run in the open)

- D1 (driver, post-seal): `fable_loop138b_junk.py` assumed
  JSONL/dict shapes for all four suites; fixed three loaders
  (redteam136/150 dict shells, f1 dict shell, cases139 56+45 union).
  The crashed B3 run kept nothing; the registered B3 is the post-fix
  re-run. Agent file untouched by D1.
- D2 (agent: none). `scripts/fable_loop138b_agent.py` is unchanged
  since before the seal; `shasum -c SEAL.sha256.txt` passes.
- D3 (B7 method, post-seal): the turn-built 15k teach ran ~4 turns/s
  under parallel load (no result produced); B7 ran instead on a
  doorway-built 15k-fact notebook (`loop.listening._teach`, the same
  call the loop's own `_act` makes; same notebook class, copied dir,
  same 25-ask protocol). New driver file only; agent untouched.
- OUT pieces (113e, 142) judged in `design/v3/30-modes/138b-stack-muse.md`.

## What it means

One daemon serves full-name teaches, junk refusals on five fronts,
whole-word answers, no-"?" and rewritten questions (165 repaired
through the rewriter, 069/022 through 144), honest neg/time
abstentions (N1–N5/T5/B1 fixed), sleep145 growth with taught intact,
and settled exactly-once mail — with every collateral move itemised
per-case: 4 bench wrongs, 1 bench abstain, 2 redteam writes, 1 redteam
answer, 41+1 bench flips, 2 stale-expectation flips.

## What it does not mean

Not a clean superset of loop138: the rewriter guesses wrong through
`officeholder` chains and answers sealed-abstain H5; discourse-led
subjects still teach; "I Believe …"-shaped names still refuse; sleep
E-family taught-wins (e116) and the full 6000-turn burst are not
claimed here — z104 and 4225 exactly-once turns are the sleep/soak
evidence.

Seal (`shasum -c …/SEAL.sha256.txt`; `97b9c150…`/`c55f05ce…`, ledger
P138b.1–8 pre-run). Mac CPU, offline, OMP/MKL=1, every seed/case reported.
B1: `… python -B scripts/fable_marks123_all.py --agent
scripts/fable_loop138b_agent.py --config
artifacts/fable-agent138b-20260922/loop138b-config.json --out
artifacts/fable-agent138b-20260922/marks138b --workers 4`.
B2/B3/B4/B5/B7: `artifacts/fable-agent138b-20260922/fable_loop138b_bench121.py
--agent loop138b` / `scripts/fable_loop138b_junk.py` /
`scripts/fable_loop138b_redteam143.py` /
`scripts/fable_loop138b_sessions.py` /
`scripts/fable_loop138b_sleepdrive.py --only z104` /
`scripts/fable_loop138b_speed2.py`
(B6: `artifacts/fable-agent138b-20260922/fable_loop138b_soak.py`;
e116: `scripts/fable_loop138b_sleepdrive.py --only e116`).
Questions for Ben: none.
