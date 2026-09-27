# RESULTS — Exp 216: DECLINE INTENTS NEED THEIR CUE (Muse)

Registered verdict: **PASS** (M1–M5 all pass; seal 8/8 OK post-runs; no
post-seal edits). Base: loop138i. One routing change: a D-intent (D1–D10) is
served only with its cue words or a second-person word, else today's DECLINE
reply (`HONEST_DECLINE + DECLINE_SUFFIX`), never a new sentence.

## Marks (integer counts)

| mark | bar | got | verdict |
|---|---|---|---|
| M1 P1 40 world questions, D-intent replies on loop216 | 0 | 0 (all 40 today's DECLINE; base beside 6/40: P1-01/P1-02 D1, P1-03/P1-04/P1-21/P1-32 D5) | PASS |
| M2 P2 30 self questions, moves vs base | 0 | 0 (30/30 byte-identical reply + intent) | PASS |
| M3 rt136 (145) moves / new wrong | 0 / 0 | 0 / 0 (136 OK, 6 WRONG-WRITE, 3 MISSED, identical; stored 145/145) | PASS |
| M3 rt143 (124) moves / new wrong | only J8,K9,O5 / 0 | J8 W-A→MISSED, K9 W-A→OK, O5 W-A→OK; 0 elsewhere; 0 new wrong | PASS |
| M3 sessions152 moves / new writes | 0 / 0 | 0 (165 OK/15 UNHELPFUL) / 0 | PASS |
| M3 bench v3 4×200 moves / new wrong | 0 / 0 | 0 / 0 (187/9/4, 195/5/0, 149/51/0, 191/9/0) | PASS |
| M3 marks123 moves | only rt81 I_edges-03 | I_edges-03 UNCLEAR→OK (reply→DECLINE, facts_delta 0); p2/p3/p4/rt110/q1/bench/sleep/soak 0 | PASS |
| M4 write deltas anywhere | 0 | 0 (replies only) | PASS |
| M5 sleep smoke | pass | 1 sleep, installed ep20, probes 5/5, wrong 0, broken abstains, taught 50/50, ow 0, 125.8 s | PASS |

All 4 registered moves were scan-predicted pre-seal (`fable216_scan.py`:
rt143 J8/K9/O5 + rt81 I_edges-03; everything else 0, incl. whole-blob
D-canned search over all marks sealed reports). No new WRONG/WRONG-WRITE/junk
writes. Every run < 25 min (max soak 263.6 s, smoke 125.8 s).

## What it means
World questions that miss the notebook now get an honest "I don't know, say
it another way" instead of a canned self-reply to a question nobody asked;
genuine self questions answer exactly as before.

## What it does not mean
Not a Router fix: cueless self questions ("Is Ambrax better than Corvin?")
still decline, and cue-carrying statements ("My favourite colour is teal.")
still route — that is exp 212's scope, stackable with this gate.

## Deviations (all pre-seal)
1. P2-D7b replaced before seal: "Is Lumen better than Brack?" base-routes D1
   (cueless → would move); replaced with "Which city is better, Lumen or
   Brack?" (routes D7, gate passes). 2. Stock marks123 CLI has no q4 suite
   (same for exp 212); q4 covered by a `[a-z]_[a-z]` scan over every pilot
   reply: 0 leaks (sealed q4 leaks []). 3. Driver-only: marks sleep compare
   scrubs bare agent basenames (filename in reason string, not behavior).
4. Smoke ran with explicit `--idle-seconds 30.0`; suite daemons 3600.

## Reproduce (each < 25 min; OMP/MKL=1; uv offline py3.12)
- Panel: `python -B scripts/fable216_panel.py --out <DIR> --cases artifacts/fable-declinecue216-20260922`
- Suites: `python -B scripts/fable216_suites.py --only <rt136|rt143|sessions> --out <DIR>`; bench: `--only benchv3 --bench <split>`; marks: `--only marks --suites <suite>` (one at a time)
- Scan: `python3 scripts/fable216_scan.py`
- Smoke: `python -B scripts/fable_sleepsmoke206.py --agent scripts/fable_loop216_agent.py --config artifacts/fable-declinecue216-20260922/loop216-config.json --root <DIR> --report <REP> --label s1-216 --idle-seconds 30.0`
- Seal: `shasum -c artifacts/fable-declinecue216-20260922/SEAL.sha256.txt`
