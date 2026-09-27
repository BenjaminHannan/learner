# Exp 188 RESULTS — statefall on loop138g (statement-shaped fallback)

Result first: PASS. loop188 adds exactly one change on loop138g — an
outermost reply swap that serves a fixed statement fallback for
statement-shaped turns the base cannot parse — with zero unpredicted
moves anywhere: F1 40/40, frozen suites verdict-identical to sealed
loop138g rows except the enumerated reply-only swaps (33 + 1 + 4),
bench 0 moves / 0 new wrong, marks123 15 reply-only moves, 0 new WRONG /
WRONG-WRITE / junk writes vs loop138b on every suite. `shasum -c
SEAL.sha256.txt` passes 7/7 (no edits after the seal); every ledger
prediction held as written.

## Marks table (integers; every seed/case reported, never averaged)

| mark | bar | number | status |
|---|---|---|---|
| F1 sealed 40 turns | 19 statement -> SFB 0 writes; 11 Q + 10 handled identical | 19/19 SFB (138g QFB 0 writes each); 11/11 Q identical; 10/10 handled identical replies+triples | PASS |
| F2 redteam136 (145) | 0 verdict moves, 33 listed reply-only | 136 OK / 6 WRONG-WRITE / 3 MISSED; 33 reply-only QFB->SFB (verdict+stored kept); seven C124/127/129/142 reply-only, C10/C21 identical; 0 new wrong vs 138b | PASS |
| F2 cases150 (57) | only A03 reply-only | 57/57 OK; A03 reply-only | PASS |
| F2 f1-144 (46) | 0 moves | 46/46 OK | PASS |
| F2 cases139b (101) | 0 moves | 101/101 | PASS |
| F2 rt143 (124) | 0 moves, M3 identical | 107 OK / 7 MISSED / 10 WRONG-ANSWER; M3 identical; 0 new wrong vs 138b | PASS |
| F2 sessions152 (180) | 0 verdict moves, 4 listed reply-only, 0 new writes | 165 OK / 15 UNHELPFUL; 4 reply-only (S2n8, S3n6, S4n1, S6n14) | PASS |
| G1 bench121 (4x200) | 0 moves, 0 new wrong | 194/2/4, 198/2/0, 150/50/0, 196/3/1 | PASS |
| G3 138g 7 probes | 7/7 | 7/7 OK | PASS |
| G2 marks123 | 15 listed reply-only, verdicts identical | rt81 5 + rt110 10 log lines; rest scrubbed-identical; sleep SKIP renames file only; p3 l5z1 + rt81 FAILs inherited per-case | PASS |
| G4 time | every run < 1500 s | f1 11 s, junk 12 s, rt143 11 s, sessions 8 s, bench 116 s, g3 5 s, marks 370 s | PASS |

## Deviations / notes

One sealed design adjustment, made BEFORE the seal and documented in
PASSMARKS: the statement fallback keeps two shared abstain markers
("don't know", "another way"). Pilots showed the bare paraphrase trips 2
sessions OK->WRONG and 3 rt81 OK->UNCLEAR verdicts under the frozen
mechanical judges; keeping the markers returns every suite to
verdict-identical with reply-only moves only. The fix changes the claim
the reply makes, not its abstain status. No post-seal edits (7/7 shasum
OK), no rule changes, no flakes, no open re-runs. Never wrote outside
owned paths (repo-root notebook/ untouched; verified my state dirs own
their event logs). Ran heavy suites one at a time.

## What it means

Unparseable statements no longer get an answer to a question nobody
asked: the 5 director probes plus 14 fictional variants (compound
subject, nested relations, unknown verbs, "Word is…" hearsay, negations)
get one fixed, honest statement fallback with zero writes, while real
questions keep the question fallback and everything the base handles
(teaches, pretend, greetings, confirmations, "I heard…"-hearsay) stays
byte-identical.

## What it does not mean

It does not teach the agent any new fact shapes — unparsed statements
are still declined, only more appropriately — and it does not touch
"and"-compounds (split-clarify kept) or "I heard…"-style hearsay
(HEARSAY_MSG kept); parsing coverage itself is unchanged.

## Questions for Ben

None — conservative default taken (reply-text swap only; no parser or
notebook change).

## Reproduce (each < 1500 s; `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`;
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`)

- `scripts/fable_fix188_f1.py` -> `f1-loop188.json`
- `scripts/fable_fix188_suites.py --only junk|rt143|sessions|bench|g3`
- `scripts/fable_marks123_all.py --agent scripts/fable_loop188_agent.py --config artifacts/fable-statefall188-20260922/loop188-config.json --out artifacts/fable-statefall188-20260922/marks188 --workers 4`
- `scripts/fable_fix188_compareg2.py` (read-only enumeration)
- Seal: `shasum -c artifacts/fable-statefall188-20260922/SEAL.sha256.txt`
