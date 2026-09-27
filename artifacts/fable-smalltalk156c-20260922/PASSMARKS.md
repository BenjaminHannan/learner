# Exp 156c PASSMARKS — wider small talk on loop138h (Muse), sealed before run

Agent: `scripts/fable_loop156c_agent.py` (Loop156cEars /
Loop156cAgentLoop / Loop156cDaemon, build_agent156c,
DEFAULT_CONFIG156c). THE ONE CHANGE lives in
`scripts/fable_fix156c_smalltalk.py` (Smalltalk156cMixin + closed
anchored phrase sets + normaliser + possessive/question guards); the
wrapper stacks it outermost on loop138h, which is imported read-only
— no existing file edited. `scripts/fable_fix156c_smalltalk.py` is a
byte-identical spare copy, unreferenced at runtime (kept + sealed).
Config: `artifacts/fable-smalltalk156c-20260922/loop156c-config.json`.
Cases: `artifacts/fable-smalltalk156c-20260922/cases156c.json` (77
rows: 44 new small-talk, 0 copied from 156/156b cases; 33
near-misses incl. "Happy is my dog."). Design:
`design/v3/30-modes/156c-smalltalk-muse.md`. Drivers (new, sealed):
`scripts/fable_fix156c_probe.py` (S1/S2),
`scripts/fable_fix156c_suites.py` (S3 frozen suites + bench),
`scripts/fable_fix156c_comparem.py` (S3 marks123 scrub-compare),
`scripts/fable_fix156c_smalltalk.py` (spare, no driver role).
Ledger P156c.1–P156c.7 appended pre-run. Sealed files hashed to
SEAL.sha256.txt: this file, both smalltalk files, the agent file, the
config, the cases, the drivers (probe, suites, comparem).

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1`, `uv run --offline --no-project --python 3.12
--with torch --with numpy python -B …`. Every seed/case reported,
never averaged. A registered FAIL stays FAIL with one diagnosis note.
No rule changes after the seal. Open pilots (same drivers, final
code) ran everything before the seal: probe 77/77 OK (re-piloted
after the D2 fix below); redteam136 0 moves; rt143 0 moves; sessions
0 moves; bench 800 items 0 moves; marks123 pilot scrub-identical
except rt110-D2 (see D-pilot note). The registered runs re-run
everything after the seal. Heavy suites one at a time.

D-pilot note (pre-seal, fixed before the seal): the marks123 pilot
hit rt110-D2 HARNESS-ERROR twice ("no reply for msg_00.txt",
daemon booted, inbox never consumed). D2's first turn is the 1 MB
"x"-junk case. Root cause was THIS experiment's code, not load:
_possessive_guard's ([A-Za-z]+)' backtracked quadratically on long
apostrophe-free alpha runs (100 KB took 40 s; 1 MB blew the 120 s
file timeout). Fixed pre-seal to a linear scan (one alpha char
beside the apostrophe + hand-expanded head; 1 MB now 0.03 s).
Parity battery (24 guard inputs incl. all contractions,
possessives, "'"+5000 x's, o'clock, 'tis) shows 0 output diffs vs
the old regex; full probe re-pilot 77/77 OK. Decisive replay: D2's
exact 3 turns in-process give byte-identical replies AND stored
triples loop156c vs loop138h (5.8 s vs 4.3 s), matching the sealed
138h D2 replies. rt110 re-piloted on the final code: suite pass=true,
D2 OK->OK, 0 harness errors (104.7 s). The rt110 suite is re-piloted on the final code
below; q4/summary pilot diffs (n_replies 478 vs 481, herr 1 vs 0)
were the same single D2 timeout, not agent moves.

Fixed class replies (clarify acts, 0 writes by
scripts/fable_agent_loop.py:337-339): greeting -> `Hi! Teach me like
"Tom's boss is Ann." Ask me like "Who is Tom's boss?"` (156b text
verbatim); howareyou -> `I'm just plain software, so I don't feel
much, but I'm ready to help!`; weather -> `Sounds nice! I don't feel
the weather - I'm just plain software.`; feelings -> `Thanks for
telling me. I'm just plain software with no feelings, but I'm here to
help.`; bye -> `Bye!` (verbatim, so base-answered overlaps stay
byte-identical).

## Marks

- S1 (probe driver; 44 new small-talk rows through loop156c, fresh
  loop each): every row gets its exact fixed class reply with 0
  stored triples. Bar: >= 90% (40/44). Predicted: 44/44 OK —
  greeting 8 (incl. "Hello there."), howareyou 11 (incl. "How are
  you?"), weather 10 (incl. "Nice weather today."), feelings 8
  (incl. "I'm tired.", "I'm happy today."), bye 7. Any WRONG-REPLY
  or WRONG-WRITE fails S1 honestly.
- S2 (probe driver; 33 near-miss rows through loop156c AND loop138h,
  fresh loops): reply byte-identical AND stored triples identical.
  Predicted: 33/33 OK, 0 NEAR-DIFF. Near-misses cover fact teaches
  ("Kim's boss is Lee.", "My sister is Ada."), questions about
  stored facts ("Who is Tom's boss?", "How is Kim's city?"),
  name-tailed chat ("How are you, Tom?", "Nice weather, Tom."),
  place-tailed weather ("It is cold in Oslo."), "Happy is my dog."
  (+ "Who is happy today?", "Are you happy?", "You are happy."),
  "I am hungry", "I am from Lima", "Are you happy?", "bye for now".
  Any NEAR-DIFF fails S2 honestly.
- S3 (suites driver + marks123 + comparem; per-case vs sealed 138h
  rows): 0 moves everywhere; exception list: EMPTY (no row listed —
  any move fails S3 honestly).
  - redteam136 (145): 0 verdict moves, 0 reply moves, 0 new
    WRONG/WRONG-WRITE, 0 new writes (pilot counter OK136 /
    WRONG-WRITE6 / MISSED3, base-identical).
  - redteam143 (124): 0 verdict moves, 0 reply moves, 0 new wrong
    (pilot OK107 / MISSED7 / WRONG-ANSWER10, base-identical).
  - sessions152 (6 sessions): 0 verdict moves, 0 reply moves, 0 new
    wrong, 0 new writes.
  - bench121 + edit200 + bench132_4hop (800 items): 0 verdict moves,
    0 reply moves, 0 new wrong per split (pilot cells new_121_4hop
    194/2/4, old_s2fresh_4hop 198/2/0, edit200 150/50/0,
    bench132_4hop 196/3/1 — all base-identical).
  - marks123 (`scripts/fable_marks123_all.py --agent
    scripts/fable_loop156c_agent.py --config
    artifacts/fable-smalltalk156c-20260922/loop156c-config.json
    --out artifacts/fable-smalltalk156c-20260922/marks156c --workers
    4` + comparem vs sealed marks138h): every report SAME after
    scrub, i.e. per-case identical except the predicted volatile set
    — sleep SKIP reason agent filename, fable_marks123_summary.json
    total_seconds timing, rt110 harness statuses log-metadata only
    (verdict+reply+fact_writes exact). Suite FAIL bars
    p3-l5z1/p4-1-nonpass/rt81-bug inherited byte-identical. 0 new
    WRONG / WRONG-WRITE / junk writes.
- S4 (timing): every registered run < 1500 s wall-clock Mac CPU
  (pilot: probe 19.4 s, junk 6.3 s, rt143 16.0 s, sessions 6.2 s,
  bench 44.6 s, marks ~330 s); daemon wrappers take idle_seconds.

## Predicted fault lines (part of the seal; FAILs stay FAIL)

- F1: any move beyond the enumerated sets (S1 44/44; S2 33/33; S3
  EMPTY exception list + volatile metadata only).
- F2: any new WRONG / WRONG-WRITE / junk write vs loop138h on any
  suite (small-talk clarify replies never write by construction).
- F3: mailbox-race flakes (empty-read clarifies, lost teaches, l6
  kill-counters, rt110 daemon log races) under parallel-agent load:
  recorded, re-run once in the open, both reported.
- F4: any post-seal edit to agent code, config, or case files forces
  FAIL whatever the re-run shows; never re-sealed. A
  driver/scorer-only bug fix after the seal is reported with the
  diff, and the affected marks re-run in the open.
