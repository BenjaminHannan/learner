# Exp 154d PASSMARKS — grounded yes/no on loop138f (ONE CHANGE), sealed before run

Agent: `scripts/fable_loop154d_agent.py` (Loop154dEars / Loop154dAgentLoop =
YesNo154dMixin over Loop138fAgentLoop / Loop154dDaemon, build_agent154d,
DEFAULT_CONFIG154D). The one change: `scripts/fable_fix154d_yesno.py`
(parse_yesno154d + ground_yesno154d + YesNo154dMixin; SINGLE_VALUED_154
imported read-only from `scripts/fable_fix154_yesno.py`, never the mixin).
Base: `scripts/fable_loop138f_agent.py` + `artifacts/fable-agent138f-20260922/`
+ `design/v3/30-modes/138f-stack-clean-muse.md` (read-only; nothing there
edited). Drivers: `scripts/fable_fix154d_probe.py` (T1),
`scripts/fable_fix154d_suites.py` (frozen suites + bench).
Config: `artifacts/fable-yesno154d-20260922/loop154d-config.json`.
Design: `design/v3/30-modes/154d-yesno-muse.md`.
T1 case file: `artifacts/fable-yesno154d-20260922/cases154d.json`
(T154d-S1, 38 turns: 8 teach + 9 yes + 7 no-single + 4 multi + 10 fall).
Seeded in this file before any registered run; hashed to SEAL.sha256.txt
together with the config, the case file, the agent file and the three
`scripts/fable_fix154d_*.py` files. Ledger P154d.1–P154d.8 appended
pre-run.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL
with one diagnosis note. No rule changes after the seal. Heavy suites run
one at a time (--suite). Daemon constructors always take idle_seconds.
Never writes to the repo-root notebook. Open pilot runs (same drivers,
scratch out-dirs) enumerated the predicted moves below; the registered
runs re-run everything after the seal into
`artifacts/fable-yesno154d-20260922/`.

## The one change (frozen for this mark)

YesNo154dMixin._listening_tick peeks at the inbox head through the
unchanged ears hear and diverts ONLY when (a) the base returns exactly
the single didn't-understand clarify, AND (b) the turn parses as exactly
"Is V X's R?" / "Is X's R V?" (one "'s", single-token capitalised V/X,
lowercase relation, no or/and, trailing "?"), AND (c) the notebook
grounds it (X resolves OK, nb.current(X, R) non-empty). Then: stored
value equals V -> "Yes, X's R is V."; different value on a
SINGLE_VALUED_154 relation -> "No, X's R is W."; different value on a
multi-valued relation -> "Not that I know of. I have W as X's R."
(never "No"). Anything else delegates byte-identical to super(). Reads
only (nb.resolve + nb.current); the final record is a clarify. 0 writes.

## Marks

- T1 (`scripts/fable_fix154d_probe.py`, sealed 38-turn dialogue, fresh
  Loop154dDaemon vs fresh Loop138fDaemon in lockstep): 38/38 OK —
  8 teach replies byte-identical to 138f; 9 yes exact ("Yes, ...");
  7 no-single exact ("No, ..."); 4 multi exact ("Not that I know of. ...",
  never "No"); 10 fall-through byte-identical to 138f (unknown-subject
  n29, unknown-relation n30, two-hop n31, hypothetical n32, non-question
  n33, lowercase-value n34, lowercase-subject n35, or-question n36,
  of-form n37, old-154 M3-shape n38). 0 wrong answers, 0 writes on all
  30 question turns.
- T2 (`scripts/fable_marks123_all.py --agent
  scripts/fable_loop154d_agent.py --config
  artifacts/fable-yesno154d-20260922/loop154d-config.json --out
  artifacts/fable-yesno154d-20260922/marks154d --workers 2`): every
  report per-case IDENTICAL to `artifacts/fable-agent138f-20260922/marks138f`
  (p2, p3 l1/l2/l3/l4/l5z1/l5z2, p4, rt110, q1, q4, bench, rt81, sleep,
  soak) — the predicted yes/no move set is EMPTY (no grounded
  single-mention yes/no turn occurs in these suites). Disclosed
  non-case diffs only: sleep SKIP reason naming
  fable_loop154d_agent.py; l6 replied_before_kill timing-volatile
  (pass true per seed, correct 200/200/200, wrong 0 — reported, not
  predicted); wall-clock seconds. Inherited labels unchanged: p3 l5z1
  FAIL (turns 42/43 stale expectation, status_match 58/60), rt81 FAIL
  (59 ok / 15 unclear), both per-case identical to 138f.
- G3 frozen (`scripts/fable_fix154d_suites.py --suite <name>`, one at a
  time): 0 verdict/reply moves vs the sealed loop138f rows and 0 new
  WRONG / WRONG-WRITE / junk writes vs the sealed loop138b rows on all
  six suites — redteam136 (135 OK / 7 WW / 3 MISSED; seven C124/C127/
  C129/C142 identical to 138b), cases150 (57 OK), f1 (46 OK),
  cases139b (101 OK; seven C10/C21 identical to 138b), redteam143
  (107 OK / 7 MISSED / 10 WRONG-ANSWER; M3 identical to 138b),
  sessions152 (165 OK / 15 UNHELPFUL; 0 new writes vs 138f).
- G1 bench (same driver, `--suite bench`, all four splits): per-item
  verdict+reply identical to the sealed loop138f rows (new_121_4hop
  194/2/4, old_s2fresh_4hop 198/2/0, edit200 150/50/0, bench132_4hop
  196/3/1); 0 new wrong vs the sealed loop138b rows.
- G4: every registered run < 1500 s wall-clock (pilot: T1 1.4 s,
  redteam143 3.9 s, sessions152 3.3 s, junk 2.9 s, bench 17.0 s,
  marks123 317.6 s with --workers 2).

## Predicted fault lines (part of the seal; FAILs stay FAIL)

- F1: any move beyond the enumerated sets (T2 empty move set; G3/G1
  zero moves).
- F2: any new WRONG / WRONG-WRITE / junk write vs loop138b on any suite.
- F3: mailbox-race flakes under parallel-agent load: recorded, re-run
  once in the open, both reported.
