# Exp 167c RESULTS — Saved confirmations use the answer path's surface (Muse)

## Result

The one-change fix works, 5 of 6 marks pass. Loop167c renders
`Saved: Ada's place of birth is Paris.` (spaced, like answers) where
loop167b showed the raw key `place_of_birth`, for every underscore
relation, with stored facts, keys, and matching byte-identical. One honest
FAIL: G2's q4 leak-list improved 7 → 4 as a direct effect of the fix
(diagnosis D1 below) — a move I did not enumerate, so G2 is FAIL.

## Marks table (integer counts, every case reported, never averaged)

| mark | bar | number | status | secs |
|---|---|---|---|---|
| T1 sealed 25-case probe | 25/25 OK | 25/25 OK (allowed 16/16, verb 1/1, general 8/8) | PASS | 0.8 |
| T2 loop167b 64-case probe | identical except predicted replies | 64/64 OK; exactly the 11 born replies moved | PASS | 0.8 |
| G1 bench 600 items | 0 verdict/reply moves, 0 new wrong | 0/0 moves; teach entries moved exactly 415+640+668 | PASS | 26.6 |
| G2 marks123 vs marks167b | identical except listed moves | verdicts identical; see D1 | FAIL (D1) | 188.5 |
| G3 rt136+rt143+s152 | 0 verdict/write moves | 0 moves; exactly 38 rt136 Saved replies moved | PASS | 4.1 |
| G4 time | every run < 1500 s | max 188.5 s | PASS | — |

New WRONG / WRONG-WRITE / junk writes vs loop167b: 0 on every suite.
Director probe verbatim: 167b `Saved: Ada's place_of_birth is Paris.` →
167c `Saved: Ada's place of birth is Paris.`, same triple, same answers.

## What moved, exactly (all reply-text only)

- T2: M16–M22, T03, T07, T11, T15 (the only cases167b replies with an
  underscore key) → spaced, byte-exact.
- G1: 1723 bench teach_replies entries (Saved + underscore key) → spaced;
  0 verdict, 0 reply moves.
- G2: rt110 R4 (1), F6 (4), N5 (2) log replies + p4 rows 5, 6, 18, 19, 23
  (birth_year / place_of_birth / country_of_citizenship Saved lines) →
  spaced; sleep reason names loop167c; q4 leaks 7 → 4 (D1).
- G3: 38 redteam136 Saved replies (C004, C006–C009, C011–C014, C016,
  C019–C029, C030–C035, C037, C039–C042, C044, C045, C049, C061, C112,
  C126) → spaced; 0 moves in rt143/sessions152.
- Never moved: CONFLICT, MISSING_FACT (`never_taught_rel_N` lines),
  Forgotten, clarifies, answers, verdicts, writes, statuses, keys.

## D1 (the one diagnosis note)

q4 ("0 relation-name underscore leaks") scans suite replies for
underscore tokens. Three leaked tokens — birth_year, official_language,
place_of — previously leaked ONLY through Saved confirmations, so the
sealed render erased them from replies (0 hits left anywhere in
marks167c); the 4 remaining tokens come only from non-Saved replies the
fix deliberately leaves untouched (`I don't know Mira's
city_and_who_is_mira.`, `... city?_also_mira.`, `Forgotten: ...'s
country_of_citizenship.`). Verdict unchanged (FAIL → FAIL, bar is 0);
zero new wrong. The mechanism is the sealed change itself, but the move
was not enumerated in PASSMARKS, so G2 is FAIL. No driver/code edits
were made after the seal (seal 10/10 clean); no re-runs.

## What it means

Confirmations now read like answers for every underscore relation, and
nothing else changed — same facts, same keys, same matching.

## What it does not mean

It does not rename any stored relation or fix non-confirmation texts
(MISSING/Forgotten still show raw keys); q4 still fails its 0-leak bar.

## Deviations

D1 above (q4 improvement, reported not re-run — deterministic scan, a
re-run could not change it). No post-seal edits. No repo-root notebook
writes (all runs used temp/daemon dirs; scratch dirs removed).

## Reproduce (worktree root, one at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167c_probe.py --out artifacts/fable-label167c-20260922/probe167c-loop167c.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167c_t2.py --out artifacts/fable-label167c-20260922/t2167c-vs167b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167c_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167c_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop167c_agent.py --config artifacts/fable-label167c-20260922/loop167c-config.json --out artifacts/fable-label167c-20260922/marks167c --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167c_marksdiff.py

## Questions for Ben

None. (Possible future work, not questions: extend the render to
MISSING_FACT/Forgotten/CONFLICT texts; add wife~=spouse synonymy.)
