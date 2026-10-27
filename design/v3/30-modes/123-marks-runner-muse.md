# 123 — One-command marks runner for the joined-up agent (Muse, 2026-09-22)

Exp 123 is infrastructure: tonight's integration build will be judged with
it. One command takes a loop agent script plus its config JSON and replays
every prior registered mark suite that applies, each item in a fresh daemon
directory through the mailbox exactly as the original suite did — by
importing the original suites' code, never by copying it.

## Design (additive only)

One new file, `scripts/fable_marks123_all.py` (prefix `fable_marks123_`),
plus artifact `artifacts/fable-marks123-20260922/` and this doc. No existing
file is read-write; sealed artifacts are read-only inputs.

Generic agent binding: the runner imports the given script as a module,
finds the `*Daemon` class, the `build_agent*` function and the
`DEFAULT_CONFIG*`, and loads the given config JSON. Every suite then drives
that binding:

- P2: sealed `fable_redteam98_cases.CASES` + sealed `fable_redteam98_runner.judge`;
  the send/send_bytes/restart/tear_tail/kill9_burst driver mirrors
  `fable_loop102_marks.run_case` op-for-op with only the factory swapped;
  kill-9 burst uses the same texts/gold and the same no-`--config` launch.
- P3: `fable_loop96_marks.run_l1…run_l6` called directly, with the same
  runtime-only monkeypatch exp 117 used (`L96.build_agent96`,
  `L96.DEFAULT_CONFIG96`, `M96.PY96`, `M96.daemon_cfg96`). No file edited.
- P4: sealed `p4-innocent-30.json`, same store/refusal rules as the 113b runner.
- RT110: sealed `fable_redteam110_runner.run_case` + `judge` with only
  `daemon_cmd` repointed at the agent under test (real daemon subprocess,
  `uv run`, mailbox — byte-identical transport to the original).
- Q1: F5 (teach / please-forget / re-teach Paris / ask) and M5 (shouted
  possessive ask) through fresh daemons, same bars as exp 117.
- Bench: `fable_bench113_run.run_item` + `summarize` (scorer v2: answer
  value after the final "is/are", word-boundary abstain list) on both
  sealed splits, 200 + 200 fresh daemon dirs.
- RT81: sealed `fable_redteam81_probe.SEQS` with the probe's own verdict
  rules (nowrite ⇒ taught-FACT delta must be 0; `must` substrings; crash and
  personal-inference checks); transport is mailbox files via in-process
  `process_file` instead of `AgentLoop.turn()`, and the setup step calls the
  same `nb.new_entity` the probe calls.
- Sleep: capability detect — full Z1–Z5 only for a `Sleep104Daemon`
  carrier; anything else records SKIP with a printed reason.
- Soak: a real daemon subprocess serves 2,000 template turns (200 teaches,
  then asks and Actually-corrections against a ground-truth map); SIGKILL
  at 500/1,000/1,500 completed turns with reboot and victim reconcile;
  counts lost/wrong/doubled replies plus a notebook audit of taught pairs
  (lost/dup/wrong). Duplicates from kill-9 reprocessing are counted
  separately, never hidden.
- Q4: relation-name underscore scan over every collected reply.

Parallelism: the full run fans out to one subprocess per suite (fresh
interpreter each — no fork-with-torch hazards), `OMP_NUM_THREADS=1`
`MKL_NUM_THREADS=1` throughout; single-suite mode (`--suite NAME`) lets
tonight's build re-run just one leg. Output is one table (suite,
registered bar, number, PASS/FAIL/SKIP, seconds) plus
`fable_marks123_summary.json`; every per-case row lands in the per-suite
JSON, never averaged.

## Verification (sealed PASSMARKS, ledger P123.1–P123.5)

H1 vs loop102: P2/P3/P4, all 62 RT110 verdicts, and both bench tables
reproduce the sealed artifacts field-for-field; soak 0/0/0; sleep SKIP;
full run 268 s. H2 vs loop117: Q1 both OK, Q2 exactly F5+M5 moved with
R4/N6/S3/S6 staying, Q3 = H1 numbers, Q4 zero leaks, bench verbatim
(split-B identical to the loop102 arm); full run 142 s. Both < 25 min (H3).

Known gap, listed not hidden: RT81's `must` substrings are pinned to the
milestone-1 doorway's reply wording, so 13/74 items report UNCLEAR on the
joined-up agent (identical set on loop102 and loop117) with zero wrong
writes on every one — the suite's safety count (bug=0) reproduces, the
wording bar does not. The runner reports the items verbatim; re-sealing
RT81 for the joined-up agent (or gating on wrong writes) is follow-up work,
not this experiment's call. A PASSMARKS H1-Q1 note wrongly predicted F5 OK
on loop102; the sealed artifact (F5=BUG) and the harness agree, and the
sealed file stands.

## Limits

Template-soak only (FakeEars-shapes); bench/scorer inherited as-is,
including its teach-gap partials; sleep install is detected, not performed;
RT110 keeps the original's `uv` boot cost (~2–4 s/case under parallel load).

## What it means / does not mean

Means: one sealed, timed, import-faithful command replays the whole
regression surface and tells tonight's build exactly which suite and which
item moved. Does not mean the joined-up agent passes RT81 verbatim, or that
any suite was re-tuned to make it pass — failing rows are reported, never
edited away.
