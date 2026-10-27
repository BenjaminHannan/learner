# Exp 167e RESULTS — every relation-key reply uses the answer surface (Muse)

## Result

All 6 marks pass. Loop167e renders `Forgotten: Ada's place of birth.`,
`I don't know Ada's place of birth.`, change-prompts, and broken-chain
lines with spaces (like answers) for every underscore relation, with
stored facts, keys, matching, and chosen replies byte-identical to
loop167c. Marks123 q4 is 0 leaks (was 4 fragments), exactly as
predicted -- the wound that made 167c a G2 FAIL is closed by the
predicted mechanism.

## Marks table (integer counts, every case reported, never averaged)

| mark | bar | number | status | secs |
|---|---|---|---|---|
| T1 sealed 34-turn probe | 34/34 OK, 0 leaks, events identical | 34/34 OK (saved 7, answer 6, missing 5, conflict 3, broken 3, forgotten 4, clarify 2, other 4) | PASS | 2.3 |
| T3 loop167c 25-case probe | identical, 0 moves | 25/25 identical, moved=[] | PASS | 2.0 |
| G1 bench 600 items | 0 verdict/teach moves, 0 new wrong | 0/0 moves; exactly the 37 predicted edit200 MISSING replies moved | PASS | 43.4 |
| G2 marks123 vs marks167c | identical except listed moves | exactly F6/L6/S2 rt110 moves; q4 FAIL->PASS leaks=[] | PASS | 223.2 |
| G3 rt136+rt143+s152 | 0 verdict/write/reply moves | 145+124+180 turns, 0 moves everywhere | PASS | 10.2 |
| G4 time | every run < 1500 s | max 223.2 s | PASS | -- |

New WRONG / WRONG-WRITE / junk writes vs loop167c: 0 on every suite.
Director probe verbatim: 167c `Forgotten: Ada's place_of_birth.` ->
167e `Forgotten: Ada's place of birth.`; 167c `I don't know Ada's
place_of_birth.` -> 167e `I don't know Ada's place of birth.`; same
triples, same answers.

## What moved, exactly (all reply-text only)

- T1: all 15 key-template turns (missing 5, conflict 3, broken 3,
  forgotten 4) spaced; base 167c showed raw keys on each (coverage
  proof in-file); answers/clarifies already clean.
- T3: nothing (25/25 byte-identical; 167e render idempotent on 167c rows).
- G1: 37 edit200 MISSING replies (bench65-abs-absent odd 01-23,
  bench65-abs-broken 00-24, never_taught_rel_N -> spaced); 0 moves in
  both 4hop splits; verdicts and teach_replies identical.
- G2: rt110 F6 Forgotten country_of_citizenship, L6 MISSING
  city_and_who_is_mira, S2 MISSING city?_also_mira -> spaced; q4 leaks
  [] (was [also_mira, city_and, country_of, who_is]); sleep reason
  names loop167e; p2/p3/p4/q1/bench/rt81/soak per-case identical.
- G3: nothing (0 moves on 145+124+180).
- Never moved: stored triples, keys, matching, verdicts, writes,
  clarifies, answers, listings, internal Saved texts.

## What it means

Confirmations, forgets, don't-knows, change-prompts, and broken-chain
lines now all read like answers for every underscore relation, and
nothing else changed -- same facts, same keys, same matching.

## What it does not mean

It does not rename any stored relation or change which reply is
chosen; adversarial relation keys with punctuation still space
verbatim (`city? also mira`); q4's 0-leak bar now passes but only
covers p2/p4/rt110/q1 reply fields.

## Deviations

None. No post-seal edits (seal 10/10 clean after all runs). No
repo-root notebook writes (all runs used temp/daemon dirs; scratch
dirs removed). No re-runs; no silent anything.

## Reproduce (worktree root, one at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167e_probe.py --out artifacts/fable-label167e-20260922/probe167e-loop167e.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167e_t3.py --out artifacts/fable-label167e-20260922/t3167e-vs167c.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167e_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167e_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop167e_agent.py --config artifacts/fable-label167e-20260922/loop167e-config.json --out artifacts/fable-label167e-20260922/marks167e --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167e_marksdiff.py

## Questions for Ben

None.
