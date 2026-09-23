# RESULTS — Exp 138: tonight's agent (loop138 integration, Muse, 2026-09-22)

Loop138 stacks tonight's verified pieces in one new file
(`scripts/fable_loop138_agent.py`, sha `56e0123b…` at seal; fixed after,
see D1–D4; no existing file edited). All four layers delivered and judged;
no layer needed a lower-layer behaviour change, but L1b/L2 do change
replies on turns the base clarified — the measured moves are listed
exactly. PASSMARKS sealed pre-run (`SEAL.sha256.txt`: `4deb7764…`),
ledger P138.1–9 appended pre-run. Mac CPU, offline, OMP/MKL=1.

IN: loop134 base; 129 punct mixin; 113c gate (ported); 127 router +
Self99 answers over live loop138 state; 131 sleep retrofit; 108
exactly-once daemon. OUT (no PASS RESULTS.md when layer 1 closed):
113e, 135, 137. Daemon launch: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1;
uv run --offline --no-project --python 3.12 --with torch --with numpy
python -B scripts/fable_loop138_agent.py --daemon --dir DIR --config
artifacts/fable-agent138-20260922/loop138-config.json`.

## Marks (every seed/case reported)

| mark | bar | got | verdict |
|---|---|---|---|
| A1 q1/q4 | F5+M5 OK; 0 leaks | both OK; 0 leaks | PASS |
| A1 P2 (64) | 0 OK→BUG, 0 still-BUG | 0, 0 (B7/C2/C5/D8 OK; G8 `Albany.`) | PASS |
| A1 p3/p4 | 7/7; 0 refusals | 7/7; 0 | PASS |
| A1 rt110 (62) | equal 134 | OK→BUG 1 (S1), still-BUG 5 (R4/N6/S1/S3/S6), 0 herr | FAIL (1 move) |
| A1 bench | 150/50/0 + 157/43/0 | identical | PASS |
| A1 rt81 (74) | 0 wrong writes | 60 OK / 0 BUG / 14 UNCLEAR | gate-PASS (bar FAIL, 134 precedent 61/0/13) |
| A1 sleep/soak | SKIP / clean | SKIP (sleep-capable) / 2000 turns 3 kills 0/0/0 | PASS |
| A2 new121/old/edit200 | 0 new wrong vs 134 | 135/62/3 (2 new: 165, 174); 157/43/0; 150/50/0, 0 moves | FAIL (2 moves) |
| A3 panel (100, turn path) | ≤1 wrong | 6 wrong (Q033–36, Q059, Q078) | FAIL |
| A3 bench routing | 0 content-routed | 1 (165); 61 decline-served (all abstain) | FAIL |
| A4 Z1–Z5 | install, 0 wrong | seeds 1–3: 20 eps, OOF 1.0, agree 1.0, 5/5 probes sleep-derived, taught 50/50, 0 overwrites; Z4 PASS; Z5 noise4 install / noise8 refuse+abstain | PASS |
| A4 E1–E4 | install, 0 wrong, taught wins | installed, 8 eps, ow 0; E1–E4 OK, E2/E3/E4 src=taught | PASS |
| A4 other 116 | unchanged | 33/33 match 131-rescored (F1/F2 via fixed lookup) | PASS |
| A5 G2 (6000, seed 931) | 0 dup/lost/wrong, ≥10 kills | 10/10 aimed (attempts 1), 6000/6000 replies, 0 doubled, 6000/6000 receipts once, 10/10 audits, 0 wrong, 213.7 s | PASS |
| A6 time | each run <30 min | A1 147 s, A2 40 s, A3 6 s, A4z 624 s, A4e 1160 s, A5 214 s | PASS |

## Why each FAIL happened (all load-bearing)

- rt110 S1: redteam probe shaped like a self count-question; notebook
  missed, router fired C1, canonical self answer served (expects abstain).
  Inherent to the specified L2 rule, not a bug in any piece.
- A2-165: ambiguous mid-chain question; notebook missed, router fired,
  Self99 fell through to FALLBACK (scored wrong; base abstained). Same rule.
- A2-174: full N-hop frame misjudged partial by the frozen 113c gate
  ("is based" reads as an unconsumed cue) → loop102 truncation answered
  short. A genuine 113c-port edge on unseen phrasing; the gate file is
  sealed, so reported, not tuned.
- A3 Q033–36: C17/C18 checkers hardcode session state (turns==26, clean
  last-turn quote); any turn-path evaluation perturbs it — unwinnable
  through `loop.turn` by construction. Q059: notebook guard reply ("Was
  that a question?") is not a sealed-rule miss → notebook wins → scorer
  flags it. Q078: the known 127 near-blend (fires C18 on NEW) → wrong.
  Standalone router accounts for 1 (Q078); the turn path adds 5.

## Deviations (all in new files; full waves re-run on final code)

- D1: attempt-1 wave crashed in P3 — `Loop138Daemon` missed
  `idle_seconds` (subprocess `run()` only). Fixed; full re-run.
- D2: decline wording. Bare HONEST_DECLINE fails bench abstain-phrases
  (42 s2fresh wrongs in attempt-2); bare notebook clarify fails self
  markers. Served text keeps HONEST_DECLINE verbatim + the redteam bits
  ("I didn't understand that, I don't know — could you say it another
  way?"); passes all four checkers (verified by probe before re-run).
- D3: self answers use the routed intent's CANONICAL question (exactly
  `Self127Agent.answer_self`), not the asked text — asked-text fell to
  FALLBACK on rephrasings. Fixed P1/P3 vs attempt-2.
- D4: daemon now logs `sleep` events in the 104 schema (install worked —
  word file + 20 eps — but the 104/116 drives couldn't see it). A4 re-ran.

## What it means

One daemon serves notebook answers, honest live-state self-answers,
taught-beats-sleep derivations, exactly-once across kill-9s — with every
collateral move counted: 1 rt110 case, 2 bench items, 5 panel turns.

## What it does not mean

Not a clean superset of loop134: L2 content fires on redteam-shaped
misses (S1/165-class) and the 113c gate over-fires on clunky phrasing
(174-class); near-blend self-questions (Q078) still answer wrongly; the
turn path cannot satisfy session-hardcoded self-checkers (C17/C18).

## Reproduce

Seal: `shasum -c artifacts/fable-agent138-20260922/SEAL.sha256.txt`. A1:
`… python -B scripts/fable_marks123_all.py --agent
scripts/fable_loop138_agent.py --config
artifacts/fable-agent138-20260922/loop138-config.json --out
artifacts/fable-agent138-20260922/marks138 --workers 4`. A2/A3/A4/A5:
`python -B artifacts/fable-agent138-20260922/fable_loop138_bench121.py`
/ `fable_loop138_selfcheck.py` / `fable_loop138_sleepdrive.py --only
e116|z104` (+ `fable_loop138_rescore.py`) /
`fable_loop138_soak.py`. Questions for Ben: none.
