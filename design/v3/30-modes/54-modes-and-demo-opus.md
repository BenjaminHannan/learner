# 54 — Modes scheduler + demo (design)

Status: built and registered-tested 21 Sep 2026. Implements docs 31 (integrated design), 32 (Ben’s simplification ruling — overrides 31 where they differ), 33 (CREATIVE stop mechanism). Artefacts: `artifacts/fable-modes54-20260921/`.

## 1. What Ben asked for (doc 32, verbatim intent)

Default is THINKING. Memory full → SLEEP. WORK on demand; CREATIVE is a sub-routine of WORK (got an idea → back to work; no idea → ask Ben). LISTENING is the doorway for everything Ben says. Bored/THINKING may use the web for things it judges helpful to learn; personal facts are asked, never searched. v1 switching = plain rules, no learned policy.

## 2. State machine (v1)

Five top-level modes: `LISTENING`, `WORK`, `CREATIVE`, `SLEEP`, `THINKING`. CREATIVE is implemented as a phase of a WORK job (`job.phase == "creative"`) so the job record and budget stay attached; it is still visible as its own mode in the log because Ben’s ruling treats it as a distinct “for a bit” activity.

**Priority (highest first):** LISTENING > WORK/CREATIVE > SLEEP > THINKING.

| Enter | When | In-flight on pre-empt |
|---|---|---|
| LISTENING | inbox non-empty at next tick | WORK/CREATIVE: park record; SLEEP: abort **before** commit (rollback, memory unchanged) |
| WORK | runnable job (queued or re-queued), inbox empty | — |
| CREATIVE | job `open_ended` at scoping, or a step failed 2 attempts with distinct signatures | same job record, round counter kept |
| SLEEP | no runnable job, inbox empty, `memory ≥ threshold` | chunked; commit clears memory; abort = no clear |
| THINKING | idle default (start state) | anything above becomes true |

**Authority:** every transition goes through `_transition()` and lands in `mode_log` as `{seq, t, from, to, reason, inbox, runnable_jobs, memory, …}`. A mode never switches itself. A mode *command* embedded in a payload (e.g. a creative probe returning `{"command": "SLEEP"}`) is logged and **rejected**; the scheduler still decides. This is doc 31 B4.2.

## 3. CREATIVE budget = fixed N = 11

Doc 33 designs a smart stop rule (stall tests, EV test, refine loop). The creative-stop toy (`fable_creative_stop_toy`) registered **KEEP_FIXED_N** on 3/3 seeds and the smart rule did not beat it. Per the parallel-build rule (“use the registered verdict”), WORK→CREATIVE hand-off uses `CREATIVE_FIXED_N = 11`:

- **FOUND:** checker PASS → resume WORK with the route.
- **GIVE-UP:** round == 11 and no PASS → `PARKED`, exactly **one** ASK_BEN question, drop to THINKING.
- Two jobs get separate budgets (s33). Silent drops are 0 (S4).

Doc 33’s stall/EV/refine machinery is designed but not wired until a checker exists that can beat fixed-N on held-out jobs.

## 4. SLEEP

Enter only when inbox empty AND no runnable job (parked jobs do not block). Three chunks, then commit: `memory = 0`, experience cleared. LISTENING during SLEEP sets an abort flag; commit never runs after abort (rollback). Asserted in S5 and in the demo show-piece.

## 5. The 34-scenario suite

Frozen in `SCENARIOS` before the registered run. Each scenario is a short script (submit / queue_job / grow_memory / step) plus a boolean check. Two schedulers run the identical list:

- **ours** (`ModeScheduler`) — must pass ≥ 34/34.
- **naive foil** (`NaiveAlwaysThinkingScheduler`) — accepts the same API but `step()` never leaves THINKING; must fail ≥ 12. It failed 30 (only the four idle-THINKING scenarios passed).

Global invariant checkers (S3–S5) re-run every scenario on a fresh scheduler and count log-field gaps, creative-round overruns, unclosed creative exits, double ASK_BEN, unsafe SLEEP entries, and commit-after-abort.

Why a foil: a suite only our scheduler can pass is not testing anything (same principle as the notebook contract’s naive foil).

## 6. The 10-minute demo

One frozen script (`BEN_LINES` + 9 questions + a mode show-piece), executed once:

1. **Teach** through LISTENING (`fable_listening_m1.hear` as `turn_handler`), interleaved with Q1–Q8.
2. **Show-piece:** approve a rule → infer Kai’s city (`inferred`); queue J-show (open-ended, FOUND at round 2) which writes one `proposed`; queue J-stuck (never FOUND) which parks at 11 with one ASK_BEN; drop `sleep_threshold` to current memory and let SLEEP commit.
3. **Q9 self-report** assembled only from active rows’ `source` tags, `fact_origin` (set by the listen turn / job / sleep that wrote them), and `mode_log` lines.
4. **Baseline:** plain decoder-only transformer written inside the demo file (2 layers, d=64, 4 heads, 104,832 params), trained full-batch Adam lr 1e-3 for 600 updates on the same story-prefix+question→gold pairs, seeds 5401/5402/5403, greedy decode, exact match. Q9 is untrainable (no notebook, no mode log) → 0 by construction.

Marks D1–D6 and outcome integers are in `RESULTS.md`. Design point: D5 forces the two systems to see **byte-identical** teaching lines (per-item prefixes of one master story); without that, any win is a story-parsing artifact.

## 7. Explicit non-goals / cut list

- Learned mode switching (needs ≥50 held-out episodes where the rule was wrong — doc 31 B1).
- Doc 33’s EV/stall/refine stop rule (toy says fixed-N is enough for now).
- Real English ears/mouth (demo uses structured lines; English is agent 1/6’s problem).
- Jobs with real side effects (J-show/J-stuck are scripted ticks).
- Web quarantine in the demo (0 web rows by design; THINKING’s web path is doc 37 / `fable_thinking_m2`).

## 8. Reproduce

```bash
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 python -B scripts/fable_modes54_scheduler.py --selftest
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_modes54_demo.py --out artifacts/fable-modes54-20260921
```

Source sha256 recorded in `RESULTS.md` before the registered runs.
