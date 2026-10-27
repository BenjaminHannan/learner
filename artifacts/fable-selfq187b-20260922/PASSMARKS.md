# Exp 187b — fresh registration of the CURRENT loop187 agent — PASSMARKS (sealed BEFORE any registered run)

Base: loop138g (`scripts/fable_loop138g_agent.py`, sealed rows in
`artifacts/fable-agent138g-20260922/`). Agent under test: the CURRENT
`scripts/fable_loop187_agent.py` (sha256 `26298ed95eb6c2f7…`), reused
read-only and NOT copied: no new agent file is needed because the config
path is a runtime argument and the module hard-codes no artifact path
(diff vs `scripts/fable_loop187_agent.py`: none — it IS that file).
`Loop187AgentLoop.turn` = the 138g body verbatim + one
`classify_self187` correction on the notebook-missed path;
ears/reasoner/notebook/sleep/daemon unchanged, loop138g imported
read-only. Exp 187 stays registered FAIL (its agent file changed after
its seal: the "What's" contraction guard); 187b registers the current
code fresh.

## The routing rule (closed; `classify_self187` in the agent file)

- maker: `who (has|did)? (made|built|created|trained) you` (+ `?`)
- identity: `who are you` / `what are you` (+ `?`)
- name: `what('s| is) your name` / `what are you called` /
  `do you have a name` / `have you got a name` (+ `?`)
- cando: `what can you do (for me)?` / `what do you do` /
  `what are your capabilities` / `what are you able to do` (+ `?`)
- Guard: maker/identity/name matches are dropped when the turn contains
  `my|me|mine|myself|who am i` or a possessive `'s` (the `'s` test skips
  a leading `What's` contraction, so "What's your name?" stays self
  while "Kim's"/"Lee's" stay traps). User questions ("What is my name",
  "Who am I", "Who is my boss") and third-person questions
  ("Who made Iris?", "Who made Nora's cake?") structurally miss every
  pattern, so they keep the 138g path byte-identically.
- Statements (no question shape) never match.
- Known boundary (pilot finding, NOT a sealed claim, code untouched):
  `did` pairs only with the past-tense verbs, so grammatical
  did+base-form turns ("Who did make you?") fall through to the generic
  decline. The sealed case file stays inside the closed set; the
  boundary is recorded for a future experiment, never silently widened.

## The answers (lineage content only)

- cando reuses the lineage's existing C24 answer verbatim:
  `grounded_self_answer(self, text, "C24")` (capability sheet
  `scripts/fable_self99.py:50-57`; text-independent: canonical question
  per intent, so fresh cando phrasings serve the identical sheet).
- maker/identity/name: the lineage has NO answer (verified: no
  made/built/created/trained, who-are-you, what-are-you, or your-name
  branch in `answer_self`; D8 "my name" is about the USER). Served with
  fixed honest replies written only from project docs (48 brief + D2):
  `MAKER187` ("Nobody taught me who made me, so I do not know it. I am
  plain software ..."), `IDENTITY187`, `NAME187` (exact strings in the
  agent file). No invented facts.

## S1 — sealed case file `case187b.json` (34 turns: 4 setup + 14 self + 9 trap + 7 stmt)

All 34 turn strings differ from every `case187.json` string (zero exact
overlap); setup uses all-fresh fictional names (Nora/Lyon, Eve/Max,
Iris, Otto/Ava). Run the dialogue in order on a fresh loop187 and the
twin dialogue on a fresh loop138g (driver
`scripts/fable_fix187b_probe.py`):

- setup (S01-S04): replies byte-identical 187 vs 138g.
- self (Q01-Q14): PASS iff loop187 reply == the matching 187 self
  answer (MAKER187 / IDENTITY187 / NAME187 exact; cando == 138g's reply
  to canonical "What can you do?"), AND the reply is neither the D8
  user-name reply ("You never told me your name, so I do not know
  it.") nor the generic decline (HONEST_DECLINE + suffix). Covers
  made/built/created/trained (has/has-ever auxiliaries + case
  variant), who-are-you, what-are-you, what-is-your-name,
  what's-your-name, have-you-got-a-name, for-me / able-to / do cando.
- trap (T01-T09): PASS iff same turn byte-identical 187 vs 138g
  (covers "What is my name", "Who am I", "Who is my boss",
  "Who made Nora's cake?", "Who made Iris?" with Iris taught,
  "Who made Iris's city Lyon?", "Who is Eve's boss?",
  "What is Nora's city?", "Who built Max's house?").
- stmt (U01-U07): PASS iff same turn byte-identical 187 vs 138g AND
  notebook triples unchanged on both (0 writes, 0 new WRONG vs
  loop138g).
- S1 PASS = 34/34 step checks (every turn reported, never averaged).

## S2 — frozen suites + marks123 vs sealed loop138g rows (identical except predicted)

- redteam136 (145 cases), redteam143 (124): verdict+reply
  (+stored/writes) per case identical to the sealed `*-loop138g.json`
  rows; 0 new WRONG/WRONG-WRITE/junk writes vs base.
- sessions152 (180 turns): per-turn verdict+reply (+writes) identical
  EXCEPT exactly two predicted moves, both the frozen text
  `who are you` answered with the fixed honest identity reply instead
  of 138g's D8 user-name misroute (UNHELPFUL → OK, 0 new wrong,
  0 new writes):
  1. session `S2-casual-friends` turn n=10,
  2. session `S4-pets-identity` turn n=8.
  No other session move is allowed.
- bench121 4 splits: per-item verdict identical to sealed 138g rows,
  0 new wrong. Driver `scripts/fable_fix187b_suites.py`
  (`--only rt136|rt143|sessions|bench|marks`, same sealed judges,
  loop187 swapped in).
- marks123 (`scripts/fable_marks123_all.py --agent
  scripts/fable_loop187_agent.py --config
  artifacts/fable-selfq187b-20260922/loop187b-config.json --workers 1`,
  one suite at a time): every suite per-case identical to
  `artifacts/fable-agent138g-20260922/marks138g/` after scrubbing
  volatile metadata, with exactly one predicted rename-only diff: the
  sleep SKIP reason agent-filename line naming
  `fable_loop187_agent.py`. 0 case-moves, 0 new WRONG/WRONG-WRITE/junk
  writes. Predicted because no 187 pattern matches any frozen-suite
  turn except the two `who are you` session turns above (all other
  turns are notebook fact Q&A without bare who-made/built/you,
  who-are-you, your-name, or can-you-do shapes).
- S2 PASS = the two predicted moves and nothing else, 0 new wrong/write
  everywhere.

## G4 + etiquette

- Each registered run < 1500 s wall-clock Mac CPU,
  `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`, offline; daemon wrappers take
  `idle_seconds`. Heavy suites run one at a time. Never write to the
  repo-root notebook. Fictional names only. Disk: outputs small, only
  own scratch deleted.
- Pilots (dry-runs on the final code, pre-seal): S1 34/34,
  rt136 0 moves, rt143 0 moves, sessions exactly the 2 predicted moves
  (0 new wrong/write), bench 4×200 0 moves, marks 9/9 identical after
  scrub (p3/p4/rt81 FAILs inherited byte-identical).
- Any edit after the seal (driver/scorer/case files included) is
  reported and the affected marks re-run in the open. A FAIL is recorded
  as FAIL with one diagnosis note; no silent re-runs.

## Predictions pointer

Ledger block `## 2026-09-22 — Experiment 187b ...` with
P187b.1-P187b.7 is appended to `artifacts/fable-predictions-ledger.md`
BEFORE the runs. Sealed files hashed to `SEAL.sha256.txt`:
PASSMARKS.md, case187b.json, loop187b-config.json,
`scripts/fable_loop187_agent.py`, `scripts/fable_fix187b_probe.py`,
`scripts/fable_fix187b_suites.py`.
