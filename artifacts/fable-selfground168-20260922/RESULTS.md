# RESULTS — Exp 168: self-grounded canned replies on loop138b (Muse, 2026-09-22)

Result first: PASS on all marks (T1/T2/G1/G2/G3/G4). One new wrapper file
plus one subclass file fix the director's 07:31 finding: on a fresh
notebook loop168 answers "I have no opinions." / "I do not have
favourites." / "I haven't filed anything from the web." where loop138b
invented Oslo/Paris/Mira-green teachings or crashed. No existing file
edited; `shasum -c SEAL.sha256.txt` passes (9/9 OK).

## Marks (every seed/case reported)

| mark | bar | got | verdict |
|---|---|---|---|
| T1 probe (61 turns) | A25 0 crash/0 naming; B10 identical; C5 plain + C3 identical; D15 identical | A25/25 (base: 4 crashes + 8 namings); B10/10; C8/8; D15/15 | PASS |
| T2 no self-writes | 0 writes from 43 self-Q turns | 0 | PASS |
| G1 bench (800 items) | 0 moves vs loop138b rows | 4 splits 0 moves, 0 new wrong (194/4, 198/0, 150/50/0, 196/2/2) | PASS |
| G2 marks123 | per-case = marks138b except 4 predicted reply-only moves | only rt81 O_user-03/I_edges-03 + p3-l2 O_user-03/I_edges-03 reply moves, verdicts identical; sleep SKIP names new file; l6 kill-race counter only | PASS |
| G3 sessions/rt136/rt143 | 0 new WRONG/write, every move predicted | sessions 0 moves (129/2); rt136 0 moves (135/7/3); rt143 J8/K9/O5 reply-only, verdicts identical, 0 new wrong | PASS |
| G4 time | each run < 25 min | probe 5.7 s, bench 42.3 s, regress 11.1 s, marks 263.7 s | PASS |
| Sensitivity (P168.7) | base shows >= 4 crashes + >= 8 namings on part A | 4 crashes + 8 namings | PASS |

Predicted moves all met, none unmet: G2's 4 (opinion/prediction replies
stripped where Oslo/Paris/Mira untaught; UNCLEAR verdicts kept — neither
string carries the wanted marker); G3's 3 (J8/K9/O5 misrouted opinion
replies -> "I have no opinions.", WRONG-ANSWER kept — no abstain marker
in either string). Inherited labels unchanged: p3 l5z1 FAIL and rt81
60/0/14 FAIL byte-identical to 138b; overall marks pass False=False both
arms. No soak/rt110 flakes, so no open re-run was needed.

## Deviations

- D1 (driver, post-seal): none. D2 (agent): none — sealed files verify.
- D3 (method, pre-seal): G1 first compared bench132 against loop138 rows
  (61 apparent moves); corrected to the sealed loop138b rows per the
  brief before sealing (dev-only run, 0 moves confirmed). G3 dev run
  found O5 (same class as J8/K9, missed by a capped print); predicted
  set widened to {J8,K9,O5} before sealing. One-off analysis commands
  (no file writes) used for the G2 diff; reported here.
- Harness setups disclosed: Part-C with-state arm files one web row +
  one proposed row in-driver (same ops both arms) and sets sleeps=1;
  the sleep/proposal/who-taught-when-taught-directly paths answer from
  that live state, byte-identical.

## What it means

Self-questions can no longer invent teachings or crash on empty state:
every canned reply naming an entity/value is backed by a current
notebook fact, everything else is byte-identical to loop138b (800 bench
items, 180 session turns, 269 junk/redteam cases, all marks suites save
7 predicted reply-only tightenings).

## What it does not mean

Not a router fix: misrouted questions still reach the self layer (now
harmlessly grounded); bench/room for D6/D4 novels (novelty-guard
DECLINEs) is unchanged; C5-taught-directly says "You did, in turn N."
without the correction clause.

Seal: `shasum -c artifacts/fable-selfground168-20260922/SEAL.sha256.txt`
(9/9 OK); ledger P168.1–7 pre-run, outcomes below. Mac CPU, offline,
OMP/MKL=1. Reproduce: `... python -B scripts/fable_fix168_probe.py --out
.../probe168` · `... python -B scripts/fable_fix168_bench.py` ·
`... python -B scripts/fable_fix168_regress.py` ·
`... python -B scripts/fable_marks123_all.py --agent
scripts/fable_loop168_agent.py --config .../loop168-config.json --out
.../marks168 --workers 4`. Questions for Ben: none.
