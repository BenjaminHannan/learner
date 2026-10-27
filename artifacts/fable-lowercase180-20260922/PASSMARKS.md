# Exp 180 — lowercase-names recase on loop138g — PASSMARKS (sealed BEFORE any registered run)

Base: loop138g (`scripts/fable_loop138g_agent.py`, sealed rows in
`artifacts/fable-agent138g-20260922/`). One change, ears only, outermost:
`scripts/fable_loop180_agent.py` (`Loop180Ears` over the unchanged 138g
stack; `Loop180AgentLoop`, daemon, config identical in shape to 138g).

## The recase rule (closed)

`recase(turn)`: capitalise the first word; capitalise any other lowercase
token whose possessive-stripped stem equals (case-insensitively) a name
ALREADY IN THE NOTEBOOK as a taught+active subject or value (notebook
canonical casing wins, e.g. `kip's` -> `Kip's`); every other token is
untouched (unknown words `bob`/`kofis`, common words `will`/`may`/`rose`
when absent from the notebook, keep their case).

## The gate (closed; interpretation I1)

- Base hear yields ASK-bearing actions -> return as-is. Asks answer
  directly; a lowercase ask is NEVER re-cased (echo included).
- Base hear yields TEACH/CORRECT and some token matches a known notebook
  name but is not in canonical case (I1: this counts as
  not-parsed-as-is) -> return `Did you mean: <recased>?`, stash the
  recased teach, WRITE NOTHING. The next turn `yes`/`yeah`/`yep`
  (case-insensitive, optional period) runs the recased teach (twin
  events); any other turn drops the stash and is processed fresh.
- Base hear yields TEACH/CORRECT with all names canonical -> as-is.
- Base hear all-clarify -> retry `recase(turn)` ONCE through the full
  138g stack: ask-bearing retry returned; teach/correct retry -> confirm
  (no write); else base reply byte-identical.
- I1 rationale (fixed at seal): the only reading under which the
  teach-confirm clause below is satisfiable; capitalised teaches, all
  asks, unknown-name turns and missing-apostrophe turns are still never
  re-cased. Missing-apostrophe typos (`kofis`) are exp 165's: out of
  scope here (verified trap X02 stays base-identical).

## T1 — sealed case file `case180.json` (35 steps, 41 turns)

- 7 cap setup teaches (A1-A7, identical on both agents).
- 12 lowercase asks Q01-Q12 (1-hop x6, 2-hop x4, of-chain x2, lowercase
  first word only): PASS iff loop180 reply == loop138g capitalised-twin
  reply. No yes/no asks: loop138g answers no yes/no twin (clarifies both
  cases), so the `if 138g answers the capitalised twin` condition admits
  none.
- 6 lowercase teaches E1-E6 (every name already in the notebook):
  PASS iff loop180 replies exactly `Did you mean: <twin>?`, the notebook
  triple set is unchanged before `yes`, and after `yes` the reply ==
  twin reply and the full triple set == twin loop's triple set.
- 10 traps X01-X10 (unknown-name ask, `kofis` typo, will/may/rose asks,
  capitalised ask, capitalised teach, all-lowercase asks incl. no-`?`,
  known-name yes/no): PASS iff same turn byte-identical 180 vs 138g.
- T1 PASS = 35/35 step checks (every turn reported, never averaged).
  Driver: `scripts/fable_fix180_probe.py`.

## T2 — frozen suites vs sealed loop138g rows + live base

- redteam136 (145 cases), redteam143 (124), sessions152 (180 turns):
  verdict+reply (+stored/writes) per case identical to the sealed
  `*-loop138g.json` rows; 0 new WRONG/WRONG-WRITE/junk writes vs base.
- bench121 4 splits (`new_121_4hop`, `old_s2fresh_4hop`, `edit200`,
  `bench132_4hop`): per-item verdict identical to sealed 138g rows,
  0 new wrong. Driver: `scripts/fable_fix180_suites.py` (same sealed
  judges, loop180 swapped in).
- marks123 (`scripts/fable_marks123_all.py --agent
  scripts/fable_loop180_agent.py`): every suite per-case identical to
  `artifacts/fable-agent138g-20260922/marks138g/` after scrubbing
  volatile metadata + the sleep SKIP reason agent filename (predicted
  rename-only diff); 0 case-moves, 0 new WRONG/WRONG-WRITE/junk writes.
- T2 PASS = all five identical-except-predicted (0 unpredicted moves).

## G4 + etiquette

- Each registered run < 1500 s wall-clock Mac CPU,
  `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`, offline; daemon wrappers take
  `idle_seconds`. Heavy suites run one at a time. Never write to the
  repo-root notebook. Fictional names only.
- Any edit after the seal (driver/scorer/case files included) is
  reported and the affected marks re-run in the open. A FAIL is recorded
  as FAIL with one diagnosis note; no silent re-runs.

## Predictions pointer

Ledger block `## 2026-09-22 — Experiment 180 ...` with P180.1-P180.7 is
appended to `artifacts/fable-predictions-ledger.md` BEFORE the runs.
