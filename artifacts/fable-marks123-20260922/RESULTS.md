# Exp 123 RESULTS — one-command regression runner (Muse, 2026-09-22)

Result: the harness works. Against loop102 it reproduces every sealed number
in (a) P2/P3/P4, (b) RT110 62 verdicts, and (d) bench scorer-v2 tables
field-for-field; against loop117 it reproduces all of exp 117 (Q1–Q4).
Both full runs (incl. 2,000-turn soak with 3 kill-9s) finish well under
25 min. One honest exception: the RT81 wording bar does not transfer
verbatim to the joined-up agent (61 OK / 0 BUG / 13 wording-drift, same 13
items on both agents, zero wrong writes either way). Details below.

## Marks table (integer counts, every case reported, never averaged)

H1 agent loop102 (268 s wall) — `h1-loop102/fable_marks123_summary.json`:

| suite | registered bar | number | verdict | secs |
|---|---|---|---|---|
| P2 (a) | 0 OK→BUG, 0 still-BUG, 64 cases | 64 cases, OK→BUG 0, still-BUG 0, BUG→OK the same sealed 16 ids | PASS | 8 |
| P3 (a) | L1–L6 all PASS | l1–l6 all PASS | PASS | 61 |
| P4 (a) | ≤2 refusals, 0 non-pass, 30 | 30 sents, refusals 0, nonpass 0 | PASS | 4 |
| RT110 (b) | 62/62, 0 harness-error | 62 cases, OK→BUG 0, still-BUG [F5,M5,N6,R4,S3,S6], herr 0 | PASS | 268 |
| Q1 (c) | F5+M5 OK | F5=FAIL (stale Lisbon stands), M5=FAIL (clarify) | recorded | 3 |
| BENCH (d) | scorer v2, split-A 0 wrong | split-A 200/200 right behaviour, 0 wrong; split-B 0/70/130 c/a/w, cg 5, tri 12, tr 22 | PASS | 26 |
| RT81 (e) | 74/74 OK | 74 turns: 61 OK, 0 BUG, 13 wording-drift (list in report) | FAIL* | 5 |
| SLEEP (f) | Z1–Z5 or SKIP+reason | SKIP: no Sleep104Daemon path in loop102 | SKIP | 0 |
| SOAK (g) | 0 lost/0 wrong/0 doubled | 2000 turns, 3 kill-9s, lost 0, wrong 0, doubled 0, audit 0/0/0 | PASS | 136 |
| Q4 (c) | 0 underscore leaks | leaks present (e.g. country_of_citizenship) | recorded | 0 |

H2 agent loop117 (142 s wall) — `h2-loop117/`:

| suite | registered bar | number | verdict | secs |
|---|---|---|---|---|
| P2 | same as H1 | 64, OK→BUG 0, still-BUG 0, same 16 BUG→OK | PASS | 7 |
| P3 | L1–L6 PASS | all PASS | PASS | 47 |
| P4 | 30/30 | refusals 0, nonpass 0 | PASS | 2 |
| RT110 (=Q2) | 0 OK→BUG, F5+M5 BUG→OK, R4/N6/S3/S6 stay | exactly that, herr 0 | PASS | 122 |
| Q1 | F5+M5 OK | F5=OK (Paris, no Lisbon), M5=OK (Lisbon) | PASS | 3 |
| BENCH | verbatim report | split-A 0 wrong; split-B 0/70/130, cg 5, tri 12, tr 22 (= loop102 arm) | PASS | 20 |
| RT81 | 74/74 OK | 61 OK, 0 BUG, same 13 drift items as H1 | FAIL* | 2 |
| SLEEP | SKIP+reason | SKIP: no Sleep104Daemon path in loop117 | SKIP | 0 |
| SOAK | 0/0/0 | 2000 turns, 3 kill-9s, 0/0/0, audit 0/0/0 | PASS | 131 |
| Q4 | 0 leaks | leaks=[] | PASS | 0 |

\* RT81: all 13 items (B-04, C-02, D-01/02/05, E-01/02, F-03, H-02, M-05,
N-02, O-02/03) have taught_delta=0 — zero wrong writes, matching the sealed
bug=0. Every one is reply-wording pinned to the milestone-1 doorway: e.g.
C-02 expects the old "another way" clarify but loop102's registered F2
forget parser answers "I don't know anyone called what I said about Mira";
D-01 expects "?"-teaching but the joined-up agent asks "Was that a
question?". The steps transport faithfully (same SEQS, same judge rules,
mailbox files); the expectations do not transfer across the doorway
versions. Neither the harness nor the original artifact is at fault — the
RT81 `must` strings are version-pinned. Tonight's build should either
re-seal RT81 expectations for the joined-up agent or gate only on the
wrong-write count (which reproduces exactly).

## What it means

Tonight's integration build can be judged with one command
(`scripts/fable_marks123_all.py --agent X --config Y`): the runner replays
P2/P3/P4, the 62 red-team cases, bench scorer-v2 on both splits, the 74
wrong-write turns, a sleep-path check, and a 2,000-turn kill-9 soak, each
item through a fresh daemon mailbox using the original suites' own
cases/judges/runners (imported, never copy-edited), and prints one table +
one JSON in under 5 minutes.

## What it does not mean

It does not mean RT81 passes verbatim on the joined-up agent (see above);
it does not install sleep words (SKIP with reason unless the agent carries
a Sleep104Daemon); soak covers template sentences only, not open English.

## Deviations

1. Sealed PASSMARKS H1-Q1 note said "F5 OK" on loop102 — wrong. The sealed
   `fable_redteam110_results.json` has F5=BUG on loop102 and the harness
   agrees (stale Lisbon). PASSMARKS stays sealed; the artifact is
   authoritative.
2. Soak boots the daemon with `sys.executable` (the current uv-managed
   interpreter) instead of re-entering `uv run`; the RT110 path keeps `uv`
   exactly as the original. Same interpreter, noted.
3. RT81 transport: original used `AgentLoop.turn()`; the runner uses mailbox
   files via in-process `daemon.process_file` (the mailbox equivalent for
   the joined-up agent); the `__SETUP_SECOND_MIRA__` step calls the same
   `nb.new_entity` as the original probe.
4. Two harness bugs in my own file were fixed mid-wave (bench factory
   keyword; soak audit resolved E-ids via ENTITY events). Pre-fix bench
   produced no JSON and pre-fix soak mis-audited; both were harness errors,
   re-run after the fix, and the failing rows (RT81/Q1/Q4) are reported as
   measured, never re-run into a pass.

## Exact reproduce command

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop102_agent.py --config artifacts/fable-loop102-20260921/loop102-config.json --out artifacts/fable-marks123-20260922/h1-loop102 --workers 4
```
(swap agent/config/out for the loop117 H2 run). Seal: `SEAL.sha256.txt`.

Questions for Ben: none.
