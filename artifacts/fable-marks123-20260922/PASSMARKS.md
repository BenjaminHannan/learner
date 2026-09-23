# Exp 123 PASSMARKS — one-command regression runner (sealed before any registered run)

Harness: `scripts/fable_marks123_all.py`. Usage:
`--agent <loop script> --config <config json> [--out DIR] [--suites ...]`.
Every suite runs each item in a fresh daemon dir through the mailbox exactly
as the original suite did, by importing the original suites' cases/judges/
runners/scorers (never copy-edited): R98 judge + RC.CASES, M96 L1-L6 runners,
p4-innocent-30.json, R110.run_case + R110.judge, B113.run_item + scorer v2,
P81.SEQS verdict rules, soak via real daemon subprocess + kill -9.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims never
exceed evidence. Every seed/case reported, never averaged. Mac CPU, offline,
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B ...`.

## H1 — harness vs loop102 reproduces sealed numbers exactly

Agent: `scripts/fable_loop102_agent.py`,
config `artifacts/fable-loop102-20260921/loop102-config.json`.

- P2 (`artifacts/fable-loop102-20260921/p2-report.json` fields): mark=P2,
  n=64, ok_to_bug=[], still_bug=[],
  bug_to_ok=[A2,A3,A5,A6,A8,B5,C1,C2,C3,C4,C5,C7,D2,D7,E7,H5], pass=true.
- P3 (`artifacts/fable-loop102-20260921/p3-report-{l1,l2,l3,l4,l5z1,l5z2,l6}.json`
  field `pass`): true in all 7 files.
- P4 (`artifacts/fable-loop102-20260921/p4-report.json` fields): n=30,
  false_refusals=[], nonpass=[], pass=true.
- RT110 (`artifacts/fable-redteam110-20260921/fable_redteam110_results.json`
  field `verdict` per case): 62/62 executed, OK=56, BUG=6,
  BUG ids exactly [F5,M5,N6,R4,S3,S6], 0 HARNESS-ERROR-shaped failures.
- BENCH (`artifacts/fable-bench113-20260922/fable_bench113_summary.json`
  field `arms.loop102`): fable_edit_200 n=200 right-behaviour 200/200
  (mquake-twohop 100 correct; reversal 50 correct; abstain-absent 25 abstain;
  abstain-broken 25 abstain), wrong=0, teach_reject_items=0;
  s2fresh_4hop n=200 mquake-s2fresh-4hop correct=0 abstain=70 wrong=130
  contains_gold=5 teach_reject_items=12 teach_rejects=22.
- RT81 (`artifacts/fable-redteam81-20260921/fable_redteam81_results.json`
  field `summary`): n=74 ok=74 bug=0 unclear=0.
- SLEEP: SKIP with printed reason (loop102 has no Sleep104Daemon path).
- SOAK: 2000 turns, 3 kill-9s; bar 0 lost / 0 wrong / 0 doubled replies
  (no sealed artifact; counts reported, never averaged).
- Q1: F5 OK (re-teach Paris stands) + M5 evaluated but loop102 is EXPECTED
  to show the M5 miss (shouted possessive) — recorded, never hidden.
  H1 passes on suites (a)(b)(d)(e) only; Q1/Q4 rows are reported verbatim.
- Q4: loop102 replies contain relation-key underscores (e.g.
  country_of_citizenship); leaks>0 EXPECTED on loop102 — reported, not a bar.

## H2 — harness vs loop117 reproduces exp 117's reported numbers

Agent: `scripts/fable_loop117_agent.py`,
config `artifacts/fable-loop117-20260922/loop117-config.json`.

- Q1 (per `artifacts/fable-loop117-20260922/RESULTS.md` + repro/
  fable_loop117_repro_{F5,M5}.py): F5 OK + M5 OK.
- Q2 (`artifacts/fable-loop117-20260922/q2-report.json` fields): n=62,
  pass=true, ok_to_bug=[], bug_to_ok=[F5,M5],
  still_bug=[R4,N6,S3,S6] (order-free), harness_errors=[].
- Q3a P2 (`artifacts/fable-loop117-20260922/p2-report.json`): n=64,
  ok_to_bug=[], still_bug=[],
  bug_to_ok=[A2,A3,A5,A6,A8,B5,C1,C2,C3,C4,C5,C7,D2,D7,E7,H5], pass=true.
- Q3b P3 (`artifacts/fable-loop117-20260922/p3-report-all.json` fields
  `pass` + `marks.*.pass`): true throughout.
- Q3c P4 (`artifacts/fable-loop117-20260922/p4-report.json`): n=30,
  false_refusals=[], nonpass=[], pass=true.
- Q4: 0 relation-name underscore leaks in any transcript reply.
- RT81/BENCH/SLEEP/SOAK: same bars as H1 (RT81 74/74; bench loop102-arm
  numbers are the reference for scorer fidelity — loop117 bench rows are
  reported verbatim, not gated, since exp 117 never ran bench).
- SLEEP: SKIP with printed reason (loop117 has no Sleep104Daemon path).

## H3 — each full run < 25 min wall-clock Mac CPU

Suites run in parallel worker subprocesses (ThreadPool over suite
subprocesses, one interpreter each, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1).
`fable_marks123_summary.json` field `total_seconds` < 1500 for H1 and H2.

## Mismatch protocol

Any mismatch = report suite + item + verdict on whether the harness or the
original artifact is at fault (do NOT fix by editing the originals).
