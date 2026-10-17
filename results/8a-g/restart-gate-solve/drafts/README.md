# Draft: probe checkpoint guard, mean-form reading, soft-able mean item, rejudge tool

DRAFT for code review. Nothing here is installed, committed or pushed. The pack in `results/8a-g/pc-job-cards/g2fa4/` is untouched; every changed file is a copy in this folder, and `gatefix.patch` is the unified diff against the pack's originals (apply with `cd results/8a-g/pc-job-cards/g2fa4 && patch -p1 < ../../restart-gate-solve/drafts/gatefix.patch`; checked: the result is byte-identical to the drafts).

## What changed and why

**A. Probe checkpoint guard (bug fix).** `probe-resume` never checked that the checkpoint in `--keep` belongs to the job. The pack's README documents `--keep ...\work\g2fa4\ckpt-keep`, which holds g2fa4's accum-4 step 200, but without `--job` the probe picks the first job that is not skipped, which is g2fa8 (accum 8); `train.py` only emits a `resume_warning` on an accum mismatch (the config hash does not include `--accum`, so the hash cannot catch it either), so the probe would resume an accum-4 checkpoint under accum 8 and report a false FAIL. Now, after the cheap file checks and before anything is started or written, `probe_resume` reads `keep/step-<k>.json` and refuses (exit 2, message, no probe queue or folder created) if: its `step` is not `--step`; its `accum` differs from the job's accum (the `--accum B3G2=<n>` of the job's queue file, parsed by the new `queue_accum`; falls back to `accum` in plan.json; refuses if the two disagree, or if neither exists, or if the sidecar has no `accum`); its `config_hash` differs from the main run's own (full hashes of the sidecars in the run's `ckpt\`, else the 12-character prefix of the `resumed` events; if the main run has neither, the comparison is skipped and a line says so in supervisor.log). After each probe run, an `accum` `resume_warning` in the probe's events (new `Events.warnings`) makes the report FAIL with the reason and no statistics (other warnings, e.g. a code-id change, are only recorded in `resume_warnings` and shown in the .md). New pure functions: `queue_accum`, `main_run_hashes`, `keep_guard`.

**B. Mean-form reading and first-update diagnostic (additive).** `resume_probe_verdict` keeps the registered rule exactly (`verdict`, `n`, `d`, `limit`, `mean_abs_*`, `diff_*` are computed by the unchanged lines) and returns nine more keys: `first_r1_c`, `first_r2_c`, `first_r1_r2`, `Dbar`, `Nbar`, `ratio` (inf if Nbar = 0 and Dbar > 0; 1.0 if both 0), `mean_form_limit = max(0.02, 2 Nbar)`, `mean_form_verdict`, `lag1_autocorr` (of the signed R1 - R2 series; `None` for under 3 points or no variance; new stdlib `lag1_autocorr`, plain biased estimator). `Sup.md_probe` shows them under the heading "recorded beside (pre-registered mean form, not the registered gate)", after the table; a report in the old format still renders. The exit code and `verdict` are still the registered rule's.

**C. Trace-A mean item can be soft.** In `trace_a` the `resume_mean_abs` miss now goes through `miss('resume_mean_abs', ...)` like `resume_max_abs`, so listing it in `rules['soft']` records it in `soft_misses` instead of stopping the run. No default changed: with no soft list, or with today's soft list `['peak', 'resume_max_abs']`, `trace_a` returns exactly what the original returns (tested). Installer: new `--soft-trace-a-mean`, valid only together with `--soft-trace-a` (argparse error otherwise), which writes `soft = ['peak', 'resume_max_abs', 'resume_mean_abs']` (`SOFT_TRACE_A_MEAN`). Idempotency needed no new logic: `added_plan` compares the whole existing g2fa8 entry with the expected one, so the three variants (strict, soft, soft + mean) are mutually "differs from the expected entry" refusals in every order (tested both ways). The first redone update (0.01), NaN/Inf and the loss falling remain hard in every variant (tested with the most permissive list).

**D. `rejudge_probe.py` (new, stdlib only).** `python rejudge_probe.py PROBE-RESUME-<job>.json [--trace-a-mean 0.0282] [--trace-a-json TRACE-A-<job>.json|state.json]`. It recomputes everything from C, R1, R2 in the file (it does not need the new fields, so it also reads a probe made by the old supervisor), applies the pre-registered reading (text copied verbatim in the docstring, the output and the JSON), prints a plain-words paragraph plus the numbers and writes `REJUDGE-<job>.json` next to the input. The value v is `--trace-a-mean`, else `resume.mean_abs` of `--trace-a-json`, else 0.0282. Verdicts: INSIDE healthy noise (exit 0), UNRESOLVED (1), OUTSIDE (2); exit 3 for an unreadable file or a probe that did not judge (`why_fail` set, e.g. the accum refusal of change A). The restore check is exact equality with 0, so any nonzero first-update gap is OUTSIDE ("restore differs at the first update: ... do not read").

## Files for review

| file | status |
|---|---|
| `g2fa4_supervisor.py` | modified copy (+122 / -7 lines vs the pack) |
| `install_g2fa4.py` | modified copy (+12 / -8) |
| `rejudge_probe.py` | new |
| `tests/test_probe.py` | modified copy (+1 / -1: the fixture's sidecar was `{}`, now `step=200, accum=4, config_hash`; the pack's version would now be refused by change A, which is the intended behaviour) |
| `tests/test_gatefix.py` | new, 15 tests for A-D |
| `tests/run_all.py` | new runner: copies the pack to a temp folder, puts the drafts over it, runs the suites, writes `tests/logs/` |
| `tests/fake_runner.py`, `test_supervisor.py`, `test_addjob.py` | unchanged copies of the pack's files (needed by the new tests as helpers; `cmp` identical) |
| `gatefix.patch` | unified diff of the three modified files against the pack |
| `tests/logs/` | `test_gatefix.log`, `test_supervisor_drafted.log` (pack suite incl. test_probe + test_addjob, on the drafts), `baseline_original_pack_test_supervisor.log` (same suite on the unmodified pack) |

## Test results (Linux, Python 3.13, CPU, fake runner)

- `tests/test_gatefix.py`: 15 of 15 pass (A: queue_accum, keep_guard, main_run_hashes, Events warnings, six refusal/acceptance end-to-end cases through `probe-resume`, accum-warning FAIL; B: fields, Nbar = 0 cases, lag-1, 1000 random traces with every old key identical to the original function's output, md_probe; C: trace A routing, installer flag, idempotency and the three-way variant refusals; D: INSIDE / UNRESOLVED / OUTSIDE incl. boundaries, CLI, exit codes, `--trace-a-json`, run as a script).
- Pack suite `tests/test_supervisor.py` (20 scenarios, then test_probe: 6, then test_addjob: 11) run against the drafts: `ALL OK`, 37 `ok` lines, same as the unmodified pack (baseline log: `ALL OK`, 37 `ok` lines).
- Compiles under Python 3.11 (same f-string grammar as the PC's 3.10); no 3.10 interpreter was available.
- Not run here: `test_noise_logic.py` (needs torch and the overlay-tests), `test_supervisor_real.py`, `check_queue_a8.py` (need the real custom_io tree), the overlay tests. None touches a changed file (`overlay/train.py` is not changed).

## Untested

Windows (paths, `taskkill`, the PC's Python 3.10, PowerShell, `schtasks`); the real runner and real `train.py` sidecars/events (the guard reads the sidecar fields `step`, `accum`, `config_hash` as `train.py` `save_ckpt` writes them and the `resumed` event's `config_hash` 12-character prefix, but the tests use a fake runner and hand-written sidecars; no test runs `train.py`); a real `resume_warning` line (tested through `Events` parsing plus an injected warning, not a real resume); that rejudge's thresholds are right (they are the pre-registered ones as given). The installer was tested on the simulated PC folder only.

## Suggested pack text changes (not made)

README line 50: say that `--keep` must hold the checkpoint of the job being probed (the documented `ckpt-keep` is g2fa4's accum-4 step 200; probing it needs `--job g2fa4`, which the probe refuses while g2fa4 is skipped, see below), and mention the new refusals. `--soft-trace-a-mean` belongs in the README's "two variants" paragraph (line 57), which would become three.

## Re-run by the solve session (Opus), 2026-10-17 ~21:35-21:50 UTC
- `test_gatefix.py`: 15 of 15 pass.
- The pack suite on the drafts **failed once** while 4 CPU-bound positive-control processes were running. The failing scenario was `t_kill_fails_then_works`: the fake run reached update 600 during the simulated failed kill, so trace A found no redone updates. That code path is not touched by the patch. Re-run at low load it passed (`ALL OK`, 37 `ok` lines; the saved log is that re-run). Conclusion: the pack's own test is timing-sensitive under CPU load; it is not a regression. Run the suite on an idle machine.
- Reviewed by hand: every change in `gatefix.patch` is additive or routed through the existing `miss()`. `verdict` and the registered keys of `resume_probe_verdict` are unchanged (and the agent compared them on 1000 random traces). The guard reads the job's queue file from the same path `selftest` uses.
