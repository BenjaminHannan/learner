# Exp 187 — self-question paraphrase routing on loop138g — PASSMARKS (sealed BEFORE any registered run)

Base: loop138g (`scripts/fable_loop138g_agent.py`, sealed rows in
`artifacts/fable-agent138g-20260922/`). One change, turn only:
`scripts/fable_loop187_agent.py` (`Loop187AgentLoop.turn` = the 138g body
verbatim + one `classify_self187` correction on the notebook-missed path;
ears/reasoner/notebook/sleep/daemon unchanged, loop138g imported read-only).

## The routing rule (closed; `classify_self187` in the agent file)

- maker: `who (has|did)? (made|built|created|trained) you` (+ `?`)
- identity: `who are you` / `what are you` (+ `?`)
- name: `what('s| is) your name` / `what are you called` /
  `do you have a name` / `have you got a name` (+ `?`)
- cando: `what can you do (for me)?` / `what do you do` /
  `what are your capabilities` / `what are you able to do` (+ `?`)
- Guard: maker/identity/name matches are dropped when the turn contains
  `my|me|mine|myself|who am i` or a possessive `'s`. User questions
  ("What is my name?", "Who am I?", "Who is my boss?") and third-person
  questions ("Who made Lee?", "Who made Kim's cake?") structurally miss
  every pattern, so they keep the 138g path byte-identically.
- Statements (no question shape) never match.

## The answers (lineage content only)

- cando reuses the lineage's existing C24 answer verbatim:
  `grounded_self_answer(self, text, "C24")` (capability sheet
  `scripts/fable_self99.py:50-57`).
- maker/identity/name: the lineage has NO answer (verified: no
  made/built/created/trained, who-are-you, what-are-you, or your-name
  branch in `answer_self`; D8 "my name" is about the USER). Served with
  fixed honest replies written only from project docs (48 brief + D2):
  `MAKER187` ("Nobody taught me who made me, so I do not know it. I am
  plain software ..."), `IDENTITY187`, `NAME187` (exact strings in the
  agent file). No invented facts.

## S1 — sealed case file `case187.json` (33 turns: 4 setup + 14 self + 9 trap + 6 stmt)

Run the dialogue in order on a fresh loop187 and the twin dialogue on a
fresh loop138g (driver `scripts/fable_fix187_probe.py`):

- setup (S01-S04): replies byte-identical 187 vs 138g.
- self (Q01-Q14, >= 12 required): PASS iff loop187 reply == the matching
  187 self answer (MAKER187 / IDENTITY187 / NAME187 exact; cando ==
  138g's reply to canonical "What can you do?"), AND the reply is
  neither the D8 user-name reply ("You never told me your name, so I do
  not know it.") nor the generic decline (HONEST_DECLINE + suffix).
- trap (T01-T09, >= 8 required): PASS iff same turn byte-identical 187
  vs 138g (covers "What is my name?", "Who am I?", "Who is my boss?",
  "Who made Kim's cake?", "Who made Lee?", "Who made Lee's city
  Paris?", two normal asks, "Who built Ann's house?").
- stmt (U01-U06, >= 6 required): PASS iff same turn byte-identical 187
  vs 138g AND notebook triples unchanged on both (0 writes, 0 new WRONG
  vs loop138g).
- S1 PASS = 33/33 step checks (every turn reported, never averaged).

## S2 — frozen suites + marks123 vs sealed loop138g rows (identical except predicted)

- redteam136 (145 cases), redteam143 (124), sessions152 (180 turns):
  verdict+reply (+stored/writes) per case identical to the sealed
  `*-loop138g.json` rows; 0 new WRONG/WRONG-WRITE/junk writes vs base.
- bench121 4 splits: per-item verdict identical to sealed 138g rows,
  0 new wrong. Driver `scripts/fable_fix187_suites.py`
  (`--only rt136|rt143|sessions|bench|marks`, same sealed judges,
  loop187 swapped in).
- marks123 (`scripts/fable_marks123_all.py --agent
  scripts/fable_loop187_agent.py --config
  artifacts/fable-selfq187-20260922/loop187-config.json --workers 1`,
  one suite at a time): every suite per-case identical to
  `artifacts/fable-agent138g-20260922/marks138g/` after scrubbing
  volatile metadata, with exactly one predicted rename-only diff: the
  sleep SKIP reason agent-filename line naming
  `fable_loop187_agent.py`. 0 case-moves, 0 new WRONG/WRONG-WRITE/junk
  writes. Predicted because no 187 pattern matches any frozen-suite
  turn (all are notebook fact Q&A without bare who-made/built/you,
  who-are-you, your-name, or can-you-do shapes).
- S2 PASS = 0 unpredicted moves everywhere.

## G4 + etiquette

- Each registered run < 1500 s wall-clock Mac CPU,
  `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`, offline; daemon wrappers take
  `idle_seconds`. Heavy suites run one at a time. Never write to the
  repo-root notebook. Fictional names only. Disk: outputs small, only
  own scratch deleted.
- Any edit after the seal (driver/scorer/case files included) is
  reported and the affected marks re-run in the open. A FAIL is recorded
  as FAIL with one diagnosis note; no silent re-runs.

## Predictions pointer

Ledger block `## 2026-09-22 — Experiment 187 ...` with P187.1-P187.7 is
appended to `artifacts/fable-predictions-ledger.md` BEFORE the runs.
Sealed files hashed to `SEAL.sha256.txt`: PASSMARKS.md, case187.json,
loop187-config.json, `scripts/fable_loop187_agent.py`,
`scripts/fable_fix187_probe.py`, `scripts/fable_fix187_suites.py`.
