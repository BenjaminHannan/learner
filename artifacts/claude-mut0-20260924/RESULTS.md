# EXP mut-0 — RESULTS (verdict: mut-0 HOLDS, M1–M3 all hold)

The SLEEP mark now fails closed. ONE change, additive only: new file
`scripts/claude_marks_mut0.py` imports `scripts/fable_marks123_all.py`
read-only (never edited) and wraps `suite_sleep` so a skip returns
`pass=False, status="NOT-RUN"`; every run-all verdict that includes
SLEEP shows NOT-RUN instead of PASS (overall never PASS while SLEEP
is NOT-RUN). Plus three new run-all scripts = copies of the sealed
originals (+273 mirror, declared in PASSMARKS) that call the mut0
runner AND run `fable_sleepsmoke206.py` to completion.

**Verdict: mut-0 HOLDS.** M1 shows fail-closed (mut0 NOT-RUN) beside
the original's pass-while-skipping; 3/3 smokes ran to completion with
honest PASS records; every non-SLEEP suite verdict is identical to
the recorded 292t/273/F1 run-all results (0 moves everywhere).

## Marks table (integer counts)

| mark | bar | result |
|---|---|---|
| M1 mut0 suite_sleep on 292t agent | pass False, status NOT-RUN | pass=False, status=NOT-RUN, skipped=True, exit 2 |
| M1 original suite_sleep on 292t agent (report) | report (expect pass True) | pass=True, skipped=True, no status key, exit 0 |
| M2 smoke ran, 292t world | RAN + recorded (PASS or FAIL reportable) | RAN, 83.9 s, verdict PASS |
| M2 smoke ran, 273 world | RAN + recorded | RAN, 89.0 s, verdict PASS |
| M2 smoke ran, F1 world | RAN + recorded | RAN, 86.4 s, verdict PASS |
| M2 combined verdicts show NOT-RUN not PASS | 3/3 NOT-RUN | 3/3 NOT-RUN (exit 2 each) |
| M3 292t non-SLEEP vs recorded regscore292t | identical | identical (see below) |
| M3 273 non-SLEEP vs 292t recorded regscore | identical | identical |
| M3 F1 non-SLEEP vs recorded regscoref1 | identical | identical |
| Measure: sleep wall s/sleep on 273 | report | 89.0 s (89.0/1) |

## Every move, every miss, deviations

- **M1 moves: 0 code moves.** mut0 report
  (`m1unit/mut0/sleep-report.json`): mark SLEEP, skipped True,
  pass False, status NOT-RUN, 0.0 s. Original
  (`m1unit/orig/sleep-report.json`): skipped True, pass True, 0.0 s.
  Same skip reason both sides (no Sleep104Daemon path in the 292t
  agent). The old code exits 0 (PASS) on a suite that never ran; the
  wrapped code exits 2 (NOT-RUN).
- **M2 misses: 0.** 3/3 run-all scripts ran sleepsmoke206 to
  completion (exits 0, report files with all 12 required fields).
  Per world: sleeps_logged 1/1/1; installed true/true/true (word
  file sleep145-words.json, episodes_at_install 20/20/20); probes
  5/5 right, 0 wrong, 0 abstain on all three; taught 50/50 with
  0 dupes on all three; sleep_overwrote_taught 0/0/0; broken-chain
  probe abstain/abstain/abstain. Smoke verdict PASS/PASS/PASS under
  the sealed rule — both outcomes were reportable; the mark is RAN
  and honestly recorded, met 3/3.
- **M3 misses: 0.** 292t: sessions152 3 moves with identical ids
  (S2-casual-friends#1, S3-teachers-correction#0, S4-pets-identity#9),
  bench 0 moves, gates clean==clean, rt136 145 rows 0 diffs with
  identical NOT-clean gate strings, rt143 124 rows 0 diffs, vp
  [N06,E04], vs [], verdict PASS==PASS. 273: same 10 fields
  identical to 292t's recorded file (0 rows of its own differ from
  292t anywhere). F1: sessions152 57/57 identical ids, bench
  648/648 identical ids, gate clean==clean, rt136 52 reply-only
  identical ids + 0 other diffs, rt143 34 reply-only + 106
  teach-reply-text ids identical + 0 other diffs, vp 98 rows
  reply-only identical + 0 other, vs 12 rows identical + 0 other,
  verdict PASS==PASS, problems []. Timing fields ignored throughout.
- **Deviations: 3 (all environmental, reported, none silent).**
  - D1: OPUS-RULES.txt absent at its stated /private/tmp path
    (same class as F1 D8); the COMMON RULES in the task message
    were followed. `scratchpad/` holds no `briefs/`.
  - D2: the first 292t mut0 run failed before any valid result:
    the machine's `~/.cache/huggingface` held no MiniLM snapshot,
    so every question-turn needing route122 CRASHed
    (FileNotFoundError) and the smoke daemon died at turn t071
    (evidence preserved in `run292t-envfail/`, not pushed). The
    frozen encoder was restored from HuggingFace main revision
    `1110a24` (dated 2026-06-01, predates the builder runs; only
    the 3 files `load_encoder` reads: config.json, vocab.txt,
    model.safetensors; repo untouched, `~/.cache` only), the router
    verified on an invented sentence, and the 292t run was done
    once cleanly into `run292t/` (reported here, not silent).
  - D3: heavy-step gating waited on load as designed (F1 run:
    load1 113 -> 47 across VP waits; totals 479 s / 582 s / 1130 s
    for 292t / 273 / F1). Free disk stayed >= 14 GB (stop bar 3 GB).
- Not a deviation: the pre-existing tracked modification
  `artifacts/fable-predictions-ledger.md` was already modified
  before this task started (seen in the first `git status`) and
  was never touched here. Not a deviation: sealed files verify
  5/5 OK after all runs (nothing sealed changed).

## What it means / doesn't mean (plain high-school English)

- Before: the SLEEP test always answered "PASS" even though it never
  actually ran the sleep test — like getting an A on an exam you
  never took. Now the same situation reports "NOT-RUN" and refuses
  to pass, so a missing sleep test can never again look like a
  passed one.
- The fix changes nothing else: all three agents (292t, 273, F1)
  get exactly the same scores as their recorded runs on every real
  test (0 changed answers anywhere), and each one now also
  completes a live sleep run (1 sleep, new word installed, 5/5
  follow-up questions right, 50/50 taught facts kept, 0 destroyed).
- This does NOT prove sleep works in general (one smoke world per
  arm, one sleep each), does NOT grade answer quality (director's
  job), and does NOT test the reader/ear stages.

## PLAN for mut-1 (semantic mutants of 273; not run)

Each mutant is one small behaviour change to 273's step order;
each names the suite that should catch it:

1. Swap tick order back (sleep_due before inbox, i.e. 292t order)
   -> caught by M1 order test (expect 0/20 listening-first).
2. Drop the inbox check (sleep -> work -> thinking; user turns
   never heard) -> caught by M1 (0/20) and M3 panel (mass moves).
3. Make sleep never due (sleep_due always False) -> caught by M2
   starvation test (0/20 sleep within 3 ticks) and the 206 smoke
   (sleeps_logged 0 -> smoke FAIL).
4. Keep the order but replace the listening tick with a thinking
   tick (message seen then dropped) -> caught by M3 panel (lost
   user turns move) while M1 still passes (first step still reads
   the inbox) — the pair that proves M1+M3 are both needed.

## Detail (counts only, never quoted)

- M1: `claude_marks_mut0.py --suite sleep` vs
  `fable_marks123_all.py --suite sleep`, agent
  `claude_loop292t_agent.py`, 292t config. mut0: pass False /
  NOT-RUN / exit 2. Original: pass True / exit 0.
- M2: run dirs (local evidence, not pushed)
  `artifacts/claude-mut0-20260924/{run292t,run273,runf1}` hold the
  full suite outputs, `mut0/sleep-report.json` (NOT-RUN each),
  `smoke206-*.json` (PASS each: 83.9/89.0/86.4 s),
  `mut0-verdict.json` (NOT-RUN each: non-SLEEP PASS + SLEEP
  NOT-RUN). Failed first attempt preserved at `run292t-envfail/`.
- M3: comparisons above are field-by-field on scorer outputs and
  id lists only; no panel or benchmark item text was read, quoted,
  or tuned on. F1 mouth log present (`mouthf1.jsonl`,
  behavior-neutral, as sealed).
- Push: the 4 scripts + PASSMARKS.md + SEAL.sha256.txt (sealed,
  verified 5/5 after the runs) + this RESULTS.md + results.json.
  Run dirs stay local (same pattern as 273's run273).
