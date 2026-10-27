# Exp 188 PASSMARKS — statefall on loop138g (statement-shaped fallback), sealed before run

Agent: `scripts/fable_loop188_agent.py` (Loop188AgentLoop / Loop188Daemon,
build_agent188, DEFAULT_CONFIG188). Subclasses the frozen loop138g stack;
the ONE change is an outermost turn() reply swap, everything rule-related
imported read-only, no existing file edited.
Config: `artifacts/fable-statefall188-20260922/loop188-config.json`.
Design: `design/v3/30-modes/188-statefall-muse.md`.
Drivers (new, sealed): `scripts/fable_fix188_f1.py` (F1),
`scripts/fable_fix188_suites.py` (F2 junk+rt143+sessions+bench+g3),
`scripts/fable_fix188_compareg2.py` (marks123 enumeration, read-only).
G2 runner: stock `scripts/fable_marks123_all.py` (new args only).
Case file (new, sealed): `artifacts/fable-statefall188-20260922/cases188.json`
(40 turns: 19 statement + 11 question + 10 handled, fresh loop per turn).
Ledger P188.1–P188.7 appended pre-run. Sealed files hashed to
SEAL.sha256.txt: this file, the agent file, the config, the case file,
the 3 drivers.

Sealed sentences (byte-exact):
- QUESTION_FALLBACK188 (base, replaced): "I do not know that from what you
  taught me. I have no record of it, so I will not guess. I didn't
  understand that, I don't know — could you say it another way?"
- STATEMENT_FALLBACK188 (188, served): "I couldn't save that as a fact.
  I don't know that shape yet. Could you say it another way, like
  "Kim's boss is Lee.""
- The swap fires ONLY when the base reply equals QUESTION_FALLBACK188 AND
  the turn is statement-shaped (no "?", first word not a question
  word/auxiliary/command-pretend-greeting opener; closed lists in the
  agent file). It keeps two shared abstain markers ("don't know",
  "another way") so the frozen mechanical judges (sessions152
  is_clarify, bench121 ABSTAIN_PHRASES, rt81 wanted-marker) still read it
  as an honest abstain; it drops only the question-answering head. Zero
  new writes/events by construction (notebook untouched; hearsay
  HEARSAY_MSG / hypo / pretend / split-clarify / grounded replies never
  equal the question fallback, so never change).

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL with
one diagnosis note. No rule changes after the seal. Heavy suites run one at
a time. Open pilots (same drivers, same paths) enumerated every predicted
move below; the registered runs re-run everything after the seal.

## Marks

- F1 (`scripts/fable_fix188_f1.py`, 40 fresh loops): 19/19 statements ->
  STATEMENT_FALLBACK188 with 0 triples (base check: loop138g gives
  QUESTION_FALLBACK188 with 0 triples on each); 11/11 unanswerable
  questions -> reply byte-identical to loop138g (question fallback stays
  for questions); 10/10 handled (5 teaches, pretend, hypo, greeting,
  name-decline, confirmation) -> replies AND triples byte-identical.
  Bar: 40/40 OK, 0 writes on statements/questions.
- F2 suites (`scripts/fable_fix188_suites.py`, per-case vs sealed 138g rows):
  - redteam136 (145): 0 verdict moves (136 OK / 6 WRONG-WRITE / 3 MISSED,
    138g-identical counts); 33 reply-only QFB->SFB with verdict+stored
    identical: C063 C064 C065 C066 C067 C068 C069 C070 C071 C073 C074 C080
    C081 C083 C084 C085 C087 C088 C092 C093 C097 C098 C106 C115 C124 C127
    C129 C131 C133 C137 C138 C141 C142. Seven: C124/C127/C129/C142
    reply-only (verdict+stored 138b-identical), C10/C21 fully identical.
    0 new wrong vs 138b rows.
  - cases150 (57): 57/57 OK; 1 reply-only (A03 QFB->SFB, verdict kept).
  - f1-144 (46): 46/46 OK; 0 moves.
  - cases139b (101): 101/101; 0 moves.
  - rt143 (124): 107 OK / 7 MISSED / 10 WRONG-ANSWER, 0 moves, M3
    identical, 0 new wrong vs 138b.
  - sessions152 (180 turns): 165 OK / 15 UNHELPFUL, 0 verdict moves,
    0 new writes; 4 reply-only QFB->SFB (verdict+writes kept):
    S2-casual-friends n8, S3-teachers-correction n6, S4-pets-identity n1,
    S6-pronouns-corrections n14.
  - bench121 (4x200): per-item verdict-identical to sealed 138g rows
    (194/2/4, 198/2/0, 150/50/0, 196/3/1), 0 moves, 0 new wrong.
  - G3 (138g's 7 sealed probes): 7/7 OK (saves/pretend/hearsay/greeting
    shapes never equal the question fallback).
  - 0 new WRONG / WRONG-WRITE / junk writes vs loop138b on every suite.
- G2 (`scripts/fable_marks123_all.py --agent scripts/fable_loop188_agent.py
  --config artifacts/fable-statefall188-20260922/loop188-config.json --out
  artifacts/fable-statefall188-20260922/marks188 --workers 4`): every suite
  per-case vs sealed marks138g EXCEPT 15 reply-only moves, all enumerated
  in pilots: rt81 5 (B_corrections-04 + F_pronoun-03 UNCLEAR kept,
  K_json-01 + K_json-02 + Q_quote-01 OK kept); rt110 10 mailbox-log reply
  lines (D2, P1-P6, T1-T3; verdicts/statuses/writes identical). Sleep SKIP
  reason names the new agent file (verdict identical). l6
  pass/correct/wrong predicted (replied_before_kill timing-volatile,
  reported not predicted). p2/p4/q1/q4/soak/bench/p3 scrubbed-identical;
  p3 l5z1 FAIL + rt81 FAIL labels inherited per-case. 0 new WRONG
  anywhere vs 138b rows.
- G4: every registered run < 1500 s wall-clock (pilot: f1 ~120 s, junk
  ~120 s, rt143 ~30 s, sessions ~60 s, bench ~60 s, g3 ~20 s, marks wave
  ~260 s).

## Predicted fault lines (part of the seal; FAILs stay FAIL)

- F1: any reply/write beyond the F1 bar (statement without the sealed
  fallback, any write on S/Q turns, any byte-diff on Q/H turns).
- F2: any verdict move, any reply diff outside the enumerated sets
  (rt136 33, cases150 A03, sessions 4, marks123 15), any new WRONG /
  WRONG-WRITE / junk write vs loop138b, any bench new-wrong.
- F3: mailbox-race flakes (empty-read clarifies, lost teaches, l6
  kill-counters, soak loss) under parallel-agent load: recorded, re-run
  once in the open, both reported.
