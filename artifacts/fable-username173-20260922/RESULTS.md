# Exp 173 RESULTS (plain words for Ben) — SCORE: T1/T2/G1/G2/G3/G4 PASS (2 deviations disclosed)

The idea: the assistant knew "me" but never learned the user's NAME --
"My name is Sam." got "I didn't understand that." This run adds exactly
that: a name statement saves the name on the user's page, name questions
answer it ("Your name is Sam."), a second different name asks first
("Do you want me to change it to Max?") instead of silently replacing,
and after naming, "Nell's sister" means the same as "my sister". Anything
that merely LOOKS like naming ("I'm tired", "Call me later") works exactly
as before.

## Marks table (integer counts)

| check | bar | got |
|---|---|---|
| T1 sealed 166 probe reused unchanged (52 rows) | 52/52 byte-identical to loop166 | 52/52 PASS (1.1 s) |
| T1b new 45-dialogue probe | 45/45 OK | 45/45 PASS (0.8 s) |
| T1b statements (13 shapes x name set + answer) | 13/13 | 13/13 PASS |
| T1b look-alikes (11 x 0 writes + identical) | 11/11 | 11/11 PASS |
| T1b renames (4 x change-prompt, yes/no) | 4/4 | 4/4 PASS |
| T1b name-then-third-person (7 x USER facts) | 7/7 | 7/7 PASS |
| T1b unset (5 x honest don't-know) | 5/5 | 5/5 PASS |
| T1b other identical (5) | 5/5 | 5/5 PASS |
| T2 wrong writes (97 rows) / non-USER entities from name statements | 0 / 0 | 0 / 0 PASS |
| G1 bench 600/600 vs frozen loop166 rows | 0 moves, 0 new wrong | 0 moves PASS (28.1 s) |
| G2 marks123 per-case vs marks166 | predicted-only | PASS w/ deviation D2 (219.4 s) |
| G3 redteam136 (145) + redteam143 (124) + sessions152 (180 turns) | 0 moves | 0 moves PASS (6.0 s) |
| G4 every run < 1500 s Mac CPU | < 1500 s | max 219.4 s PASS |

Suite detail: p2 64/64, p4 30/30, rt81 74/74, q1/p3/q4/bench/sleep/soak
whole-files identical (after the disclosed scrub); p3 L1/L3/L4/L5/L6 PASS,
L2 FAIL inherited byte-identically (the 166 O_user behaviour is preserved);
q1 F5+M5 FAILs byte-identical; soak 2000 turns 0 lost/0 wrong/0 doubled
clean first try. rt110 verdicts 62/62 equal in BOTH runs; the only diffs
are 2 log-observability fields per run (see D2).

## What it means

Name statements set `(USER, name, X)` literally (no new entities),
questions answer it, renames always ask first, and the stored name resolves
third-person possessives to the same USER facts -- while 600 bench items,
all marks123 suites, and 449 G3 turns move nowhere in verdicts, replies
(race excepted), or writes.

## What it does not mean

It does not mean every self-description is a name -- states and
descriptions ("I'm tired", "I am from Oslo", "Call me later") still
clarify exactly as loop166 does; and a literal input of `USER's ...`
still shows the raw key exactly as the base does.

## Deviations (two, both reported, sealed files untouched)

- D1 (post-seal driver fix): the G2 triage scrub missed the
  `total_seconds` key, flagging a spurious summary whole-diff. Added the
  key to scripts/fable_fix173_marksdiff.py and re-ran the diff in the
  open (suite outputs untouched; seal re-verified: 3/3 hashes match).
- D2 (rt110 mailbox/log race, both runs reported): registered run moved
  R1+R5, open re-run moved R5+S3 -- always exactly the `log` field,
  verdicts 62/62 equal, replies equal (R5: the documented msg_02
  empty-read race, also present in the base's own sealed row),
  fact_writes equal, 0 new WRONG. Mechanism: the harness reads
  `daemon.log.jsonl` for `statuses`, but the daemon appends that log
  AFTER writing the outbox reply, so under load the read lands before the
  append (`statuses: []`). Same code, varying flake sets across the two
  runs = measurement noise, not behaviour; no further re-runs.

## Questions for Ben

None.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173_probe.py --which t1 --out artifacts/fable-username173-20260922/probe173-t1.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173_probe.py --which t1b --out artifacts/fable-username173-20260922/probe173-t1b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop173_agent.py --config artifacts/fable-username173-20260922/loop173-config.json --out artifacts/fable-username173-20260922/marks173 --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173_marksdiff.py
