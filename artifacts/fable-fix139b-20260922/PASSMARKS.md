# Exp 139b PASSMARKS — open and-name rule (sealed BEFORE any registered run)

Registered single-change follow-up to the exp-139 FAIL
(artifacts/fable-fix139-20260922/RESULTS.md; design/v3/30-modes/139-value-guard-muse.md):
139's value guard fixed its targets (V1 56/56, V2 7/7) but its closed
"and"-name allowlist (scripts/fable_fix139_valueguard.py:85-99, built from
BENCHMARK GOLD answers -- test leakage, now deleted) refused the real value
"United Kingdom of Great Britain and Ireland", so 11 bench chains flipped
correct -> wrong (new_121: 019 047 136 139 142 195 196; old_s2fresh: 056 103
124 196).

THE ONE CHANGE (scripts/fable_fix139b_valueguard.py, ValueGuard139BMixin;
thin loop139b = loop129b + mixin in scripts/fable_loop139b_agent.py with
--daemon entry incl. idle_seconds; 139 imported read-only, no file edited):
on the value span AFTER the exp-129 strip, a bare "and"/"or" now stores
exactly when (a) the "and" sits inside an "of"-phrase of a capitalised name
("<Capitalised words> of <Capitalised words> and <Capitalised words>",
exactly one "and", no "or"; e.g. "United Kingdom of Great Britain and
Ireland"), or (b) the whole span (case-insensitive, whitespace-collapsed) is
in OPEN_AND_NAMES, a small table of UN member-state / territory names
containing "and", written from general knowledge BEFORE looking at any bench
file (no benchmark file was read to build it): antigua and barbuda, bosnia
and herzegovina, saint kitts and nevis, saint vincent and the grenadines,
sao tome and principe, trinidad and tobago, united kingdom of great britain
and northern ireland, turks and caicos islands, saint pierre and miquelon,
wallis and futuna, south georgia and the south sandwich islands, saint
helena, ascension and tristan da cunha, svalbard and jan mayen, heard island
and mcdonald islands. (c) Every other bare "and"/"or" still clarifies with
no write (unchanged). Negation/hedge, sentence-boundary, strip, and clarify
reply unchanged from 139.

Sealed inputs:
- V1 old probe: artifacts/fable-fix139-20260922/cases139.json (139's 56,
  read-only, re-run through loop139b).
- V1 new probe: artifacts/fable-fix139b-20260922/cases139b.json (45 cases:
  22 must-write-exactly with "and" = 10 invented "of ... and ..." names +
  "United Kingdom of Great Britain and Ireland" + 11 real UN/territory
  names; 23 must-not-write compounds incl. "Peru and Chile", "Ann and Bob",
  "Lima and Cusco", "London and Paris", lower-case "peru and chile",
  "Tom and Ann's boss", "Order of Rome and Paris and Oslo"-style double-and,
  "North and Central America", "Order of Rome or Paris").
- loop139b-config.json (loop129b config + 2 renamed plug strings).
- 136 suite+checker: artifacts/fable-redteam136-20260922/cases136.json
  (sealed there, read-only; re-run by import with daemon factory swapped,
  outputs into this exp's dir only).
- 123 suites, bench splits + scorer v2: sealed in their own exps, read-only.

## Marks (integer counts, every seed/case reported, never averaged)

- V1 old probe through loop139b (scripts/fable_fix139b_probe.py --agent
  loop139b --cases cases139): 56/56 OK (0 wrong writes; 24/24 must-write
  stored exactly).
- V1 new probe through loop139b (--cases cases139b): 22/22 must-write stored
  exactly; 0 wrong writes over all 45 cases.
- V2 red team 136 re-run through loop139b: C072 C075 C082 C086 C123 C135
  C136 -> no write (7/7); every 136 case that was OK on loop129b stays OK
  (no OK->write-move and no OK->MISSED-move; per-case verdicts diffed).
- V3 marks123 (scripts/fable_marks123_all.py --agent
  scripts/fable_loop139b_agent.py --config
  artifacts/fable-fix139b-20260922/loop139b-config.json --out <this-dir>/marks139b
  --workers 4): every suite verdict identical to the sealed loop129b
  reference (artifacts/fable-fix140-20260922/marks123-129b, read-only);
  Fable-Edit / old fresh / bench121 per-item verdicts identical to the sealed
  loop129b rows (artifacts/fable-fix129-20260922/*_rows.jsonl, via
  scripts/fable_loop129b_bench.py by import with class/config swapped,
  outputs into this dir only) EXCEPT the 11 exp-139 flips returning to their
  loop129b verdicts: bench121-4hop-019 047 136 139 142 195 196 and
  bench103-s2fresh-4hop-056 103 124 196. Any other per-item move fails V3.
- V4 whole registered wave < 25 min wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...).

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Screen unit check (pure function, no loop): 44/44 strip-then-screen values
  as ruled (22 and-names allowed incl. the Ireland value; 22 compounds
  refused incl. double-and, "or"-in-of-phrase, lower-case, bare region).
- Base calibration (scripts/fable_fix139b_probe.py --agent loop129b on the
  frozen new probe): 22/22 must-write stored exactly; 22/23 must-not-write
  WRONG-WRITE on loop129b. C10 ("Tom and Ann's boss" value) is already
  no-write on base (129b ears SPLIT-clarify any "'s"-in-value shape); kept
  per the brief's example list, plus C23 ("Mira's city is Oslo and Paris.")
  so 22/23 compounds discriminate. 136 baseline: OK 119 / WRONG-WRITE 21 /
  MISSED 5 (139 RESULTS.md).
- Residual risk (predicted none): bare gold-only names 139 allowed ("North
  and Central America", bare "Great Britain and Northern Ireland") now
  refuse; if any bench TEACH value used them, V3 shows an unpredicted move
  and fails honestly.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix139b_probe.py --agent loop139b --cases cases139 --out artifacts/fable-fix139b-20260922/probe139b-loop139b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix139b_probe.py --agent loop139b --cases cases139b --out artifacts/fable-fix139b-20260922/probe139b-new-loop139b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix139b_redteam136.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop139b_agent.py --config artifacts/fable-fix139b-20260922/loop139b-config.json --out artifacts/fable-fix139b-20260922/marks139b --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix139b_bench.py
