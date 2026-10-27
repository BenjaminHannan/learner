# Exp 189 PASSMARKS — say-again verbatim repeats on loop138g, sealed before run

Agent: `scripts/fable_loop189_agent.py` (Loop189AgentLoop / Loop189Daemon,
build_agent189, DEFAULT_CONFIG189, REPEAT189 + NO_PREV189 + is_repeat189).
Subclasses the frozen loop138g stack; the one change is an outermost
repeat-request stage in turn() (new file only, no existing file edited).
Config: `artifacts/fable-sayagain189-20260922/loop189-config.json`.
Driver (new, sealed): `scripts/fable_fix189_sayagain.py`
(`--only r1|junk|rt143|sessions|bench|marks123|all`).
R1 cases (new, sealed): `artifacts/fable-sayagain189-20260922/cases189.json`
(38 turns: 3 noprev + 13 repeat + 10 Say/repeat traps + 12 teach/ask base).
Design: `design/v3/30-modes/189-sayagain-muse.md`.
Ledger P189.1–P189.6 appended pre-run. Sealed files hashed to
SEAL.sha256.txt: this file, the agent file, the driver, the case file,
the config.
Base: `scripts/fable_loop138g_agent.py`,
`artifacts/fable-agent138g-20260922/` (sealed rows compared against),
`design/v3/30-modes/138g-merge-layer-a-muse.md`.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1`, `uv run --offline --no-project --python 3.12 --with
torch --with numpy python -B …`. Every seed/case reported, never
averaged. A registered FAIL stays FAIL with one diagnosis note. No rule
changes after the seal. Heavy suites run one at a time, each < 1500 s.
Daemon wrappers use idle_seconds=3600.0. Fictional names only.

## The one change (frozen)

Outermost repeat stage in `Loop189AgentLoop.turn`, before the unchanged
loop138g path (hence before the 137d Say-pretend rule). Whole-turn,
case-insensitive match (trailing .?! stripped) against 8 closed shapes:
say it again | say that again | repeat that | can you repeat that |
what did you say | come again | pardon | sorry.
Match -> echo `_prev189` (verbatim reply of the latest NON-REPEAT turn;
repeats never overwrite it) or the one fixed line
"I haven't said anything yet." when none exists. Never writes (no
notebook event/fact/correction/self-route), never re-runs the previous
turn (a repeated "Saved:" echo writes nothing). "Say Kim's boss is
Lee." and every other "Say X" stays pretend exactly as loop138g (only
whole-turn matches divert; "Say hello."/"Say it in French."/"Say that
Lee is kind." still take the 137d echo path; "Repeat after me: ...",
"Again, Kim's ..." never match).

## Marks

- R1 (`--only r1`, sealed 38-turn session, base loop138g + loop189 in
  lockstep, fresh in-process loops): 38/38 OK predicted —
  S01–S03 noprev -> fixed line, events unchanged (3/3);
  S05/S07/S09/S11/S13/S15/S18/S20/S22/S27/S29/S31/S35 repeat ->
  previous non-repeat reply byte-identical, events unchanged
  (triples+facts+events.jsonl lines identical before/after) (13/13,
  covering Saved echoes, answers, hearsay/hypo clarifies, pretend
  echoes, self-decline/favourites replies);
  S08/S14/S23/S24/S25/S30/S32/S33/S34/S37 traps (10/10) + S04/S06/S10/
  S12/S16/S17/S19/S21/S26/S28/S36/S38 base turns (12/12) byte-identical
  to loop138g replies AND stored triples AND events. Any other
  verdict/reply/store/events diff FAILs.
- R2 junk (`--only junk`: redteam136 + cases150 + f1 + cases139b with
  loop189 vs SEALED loop138g rows): 0 moves predicted (the only
  whole-turn repeat shape near any frozen case is redteam136's
  "Sorry, I meant Mira's pet is Rex.", which is longer than "sorry" and
  never matches). 0 new WRONG / WRONG-WRITE / junk writes vs loop138g.
- R2 rt143 (`--only rt143`) vs sealed redteam143-loop138g.json: 0 moves.
- R2 sessions (`--only sessions`) vs sealed sessions152-loop138g.json:
  0 verdict/reply moves, 0 new writes.
- R2 bench (`--only bench`, base driver's scorer over the 4 sealed
  splits vs sealed loop138g rows): 0 verdict moves, 0 new wrong.
- R2 marks123 (stock `scripts/fable_marks123_all.py --agent
  scripts/fable_loop189_agent.py --config
  artifacts/fable-sayagain189-20260922/loop189-config.json --out
  artifacts/fable-sayagain189-20260922/marks189`): every suite report
  per-case identical to sealed marks138g except the run-metadata paths;
  0 verdict/reply moves predicted (no whole-turn repeat shape occurs in
  those suites). Bench/daemon sub-runs inside marks123 inherit the same
  0-move bar. l6/soak timing-volatile counters reported, not predicted.
- G4: every registered invocation < 1500 s wall-clock (pilots: R1 ~10 s,
  rt143 ~10 s, sessions ~10 s, bench ~60 s, junk ~180 s, marks123 ~400 s).

## Predicted fault lines (part of the seal; FAILs stay FAIL)

- F1: any R1 non-OK, or any R2 move/new-wrong/new-write beyond the
  enumerated empty sets (R1 repeat-vs-base reply diffs are the intended
  change and are NOT counted as R2 moves: R1 checks them explicitly).
- F2: any new WRONG / WRONG-WRITE / junk write vs loop138g sealed rows
  on any suite.
- F3: "Say that again." must echo (repeat win over Say-pretend);
  "Repeat after me: ..."/"Again, ..." must stay base-identical.
