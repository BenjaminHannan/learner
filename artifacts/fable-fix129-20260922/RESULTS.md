# Exp 129 RESULTS — teach-punctuation single-change patch (Muse, 2026-09-22)

Loop129a = loop117 + mixin, loop129b = loop121 + mixin (subclass only; no
existing file edited). Sealed before the wave: PASSMARKS.md (SEAL.sha256.txt
verifies `8195b900…`), F1 cases (`d31fec…`, see deviation 1), ledger P129.1–8.

## Step 0 (probe of old code)

LEAK: bench73 citizen/capital/official-language (+ every pattern without a
trailing-dot guard) with `. ! ?` + trailing spaces; exp-92
employer/occupation/child with `.`; FakeEars possessive with `!`/`?`.
Clean: FakeEars possessive + `.`; explicit-dot patterns (apprentice_of…).
Old-loop calibration: `?` teaches clarify with 0 writes; `!` writes junk
(`Italy!`); `Actually, Gus Webb. …` writes subject `Gus Webb.` + value
`Chile.` and replies `Chile..`.

## Marks table (every case reported, never averaged)

| mark | result |
|---|---|
| F1 sealed probe (45 cases, 41 teach turns, 9 abbrev names) | PASS: 0 failures both loops; `Washington, D.C.`/`U.S.S.R.`/`U.K.`/`St. Louis`/`Apple Inc.` kept; `Italy.`/`!` etc. stripped |
| F2 124 re-runs (62 cases x 2 loops, sealed checker) | PASS on bar: 0 punct-caused wrong writes of 124 turns. 129b R1,V6 BUG→OK (chain now walks: `…official language is Portuguese.`); all other verdict moves: none. Remaining BUGs are the known question-side bugs (prefix truncation, Saved-ack echoes) |
| F3a Q1 (real subprocess daemons) | PASS: F5→Paris, M5→Lisbon |
| F3a Q2 (62 exp-110 cases) | PASS: 58 OK + 4 BUG, 0 OK→BUG, BUG→OK exactly F5+M5, still-BUG exactly R4/N6/S3/S6, 0 harness-error, per-case identical to loop117 (`diff-vs-117=[]`) |
| F3a P2 (64 redteam98) | PASS: 0 OK→BUG, 0 still-BUG, same 16 BUG→OK as loop102; reply diffs D8 (inherited render), G8 (`Albany..`→`Albany.`, the fix) |
| F3a P3 L1–L6 | PASS all 7 (l5z2 200/200 after deviation-3 fix) |
| F3a P4 (30 innocent) | PASS, 0 false refusals |
| F3a Q4 underscore scan | PASS, 0 leaks |
| F3b T4 packed facts | PASS, all refuse, 0 writes |
| F3b P2 | PASS: ok_to_bug exactly B7,D8; still_bug exactly B7,C2,C5,D8; `new_moves=[]` |
| F3b P3/P4 | PASS 7/7; PASS 0 refusals |
| F4 edit200 | 150 correct / 50 abstain / 0 wrong — literal 200/200 bar FAIL (structural, see below) |
| F4 old fresh 4-hop | PASS: 157 / 43 / 0 (bar ≥157, 0 wrong) |
| F4 new bench121 | PASS: 136 / 63 / 1 (bar ≥136, ≤1 wrong; residual is known 069 teach-gap) |
| F5 wall-clock | PASS: 840 s < 1500 s, Mac CPU, offline |

F2 byte-identity: all 129b non-punct rows byte-identical to 124-loop113b
rows; all 129a non-punct rows same-verdict with only the inherited
mouth-render + junk-cleanup diffs; all 10 remaining diffs are the R/V
punct rows (intended moves).

## What it means

Sentence punctuation no longer leaks into the notebook on any teach path:
re-teaches heal (`Portugal.`→`Portugal`), duplicate detection heals
(`AJ Lee.` re-teach → `I already have that.`), chains through cleaned
values walk full length, abbreviations (`D.C.`, `Inc.`, `St.`) survive,
and nothing else moved on any regression suite.

## What it does not mean

It does not mean the loops answer more questions: all remaining F2 BUGs
are the untouched question-side composer bugs, and the 50 edit200 abstains
are correct structural abstains (25 absent + 25 broken, expected-abstain).

## Deviations (all in new files only; reported numbers all from final code)

1. F1 harness: judge first flagged kept abbrev periods (false positive) —
   fixed to fail iff `strip(span) != span`; P23 expectation corrected
   clarify→teach (old-loop evidence: 117 teaches it via FakeEars, 121
   writes `Milo Ray.` junk). Cases hash `d31fec…`→`07e465…`; sealed bar
   unchanged.
2. F2 judges 129a with the matched loop102 arm rules (comparability).
3. Mixin v2 mid-wave (same one change): l5z2 found `Apple Inc.`→`Apple Inc`
   (WRONG on bench65-mquake-092); abbrev list extended (Inc/Corp/titles…);
   brackets/quotes made balance-aware (bench scan: `Ford Falcon (North
   America)` must not lose `)`). Full wave re-run on final code.
4. F4 edit200 literal 200/200 recorded FAIL: 50/200 items expect abstain
   (sealed type), so scorer-v2 max correct is 150; loop129b gets 150/150
   answers + 50/50 abstains, 0 wrong. Suggest re-sealing the bar as such.

## Questions for Ben

Should the F4 edit200 bar be re-sealed as 150 correct / 50 structural
abstains / 0 wrong (conservative default kept: literal bar, FAIL recorded)?

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project \
--python 3.12 --with torch --with numpy python -B <script> — F1
scripts/fable_fix129_f1.py; F2 scripts/fable_fix129_redteam124.py; Q1
scripts/fable_loop129a_repro.py; Q2 scripts/fable_loop129a_q2.py; marks
scripts/fable_loop129a_marks.py --mark all / scripts/fable_loop129b_marks.py
--mark all; Q4 scripts/fable_loop129a_q4scan.py; F4
scripts/fable_loop129b_bench.py --run --agent loop129b.

Daemons: `… python -B scripts/fable_loop129a_agent.py --daemon --dir DIR
--config artifacts/fable-fix129-20260922/loop129a-config.json` (same shape
for `fable_loop129b_agent.py` + `loop129b-config.json`).
