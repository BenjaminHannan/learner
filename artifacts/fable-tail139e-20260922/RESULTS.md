# RESULTS — Exp 139e: relation-gated unknown-tail clarify on loop139c (Muse, 2026-09-22)

Result first: PASS on every mark. The one change vs 139d — firing the
clarify only on person/place-valued relations — fixes 139d's FAIL while
keeping its chat behaviour: probe 65/65 exact, G1 0 moves / 0 new wrong
on all 4 bench splits, G2 suite reports identical to loop139c, G3 0 moves.

## Marks (every seed/case reported)

| mark | bar | got | verdict |
|---|---|---|---|
| T1 probe (65: 27 tailu + 17 same + 21 other) | every case OK | 65/65 OK, 27/27 exact clarify replies | PASS (P139e.1 held) |
| T2 wrong writes | 0 | 0 | PASS (P139e.2 held) |
| G1 bench 4x200 vs sealed 139c rows | 0 new wrong, 0 moves | 194/2/4 + 198/2/0 + 150/50/0 + 196/2/2; 0 moves, 0 new wrong | PASS (P139e.3 held) |
| G2 marks123 semantic vs marks139c | identical every suite | p2 64, p4 30, rt81 74 (60/0/14), rt110 62, p3 submarks, q1/q4/soak/sleep/bench-sum identical; bench detail 0 moves | PASS (P139e.4 held) |
| G3 rt136 + rt143 + sessions | 0 new WRONG/write, 0 moves | 135/7/3 + 106/11 + 129/2, 0 moves, 0 new wrong | PASS (P139e.5 held) |
| G4 time | each run < 25 min | probe 1.2 s, bench 55.4 s, marks 261.9 s, g3 13.5 s | PASS (P139e.6 held) |

## Why it passed (load-bearing, one note each)

- G1: the relation gate is exactly where 139d's killers live —
  "Gaelic/American football" teach sport, "Wa language" teaches
  language, all unlisted, so the guard never fires on bench triples
  (pre-seal scan: 0 gated hits in all 5375 taught triples, declarative
  templates included). Listed relations (city, boss, …) never carry
  tail-shaped bench values.
- G2/G3: the 9 static scan hits were over-matches — base hearsay veto,
  multi-fact split, and question paths fire before any tail guard, so
  all 9 verified byte-identical end-to-end pre-seal. No bench-detail
  moves this time (139d had 11 + 2).
- T1: all 27 listed-relation tails clarify exactly with 0 writes
  (incl. 5 corrections + stacked "honestly tbh"); all three 139d
  killers now store byte-identical to loop139c; "maybe"/"probably" and
  lowercase-start tails keep base behaviour by design (O19/O20/O21).

## Cosmetic-only notes (verdicts identical, not passes-by-luck)

- marks123 generic bars read FAIL on p3 (L5-Z1), p4 (1 nonpass), rt81 —
  exactly as the sealed base does (same submarks); the G2 bar is
  per-case identity vs marks139c, which holds everywhere.
- The inherited compare script lists 5401 "semantic moves", all in p3
  daemon-workdir volatile lines only (timestamps, hash chains,
  event_ids, sleep139c→sleep139e note) — same class as 139d's D2; zero
  moves in any suite report or bench row. Summary-table diffs are
  seconds + config path + the predicted sleep SKIP agent-name only.
- rt110: 0 harness errors, soak 2000/3/0-0-0 clean — no flakes, no
  re-run needed.

## Deviations

None. No post-seal edits of any kind; `shasum -c SEAL.sha256.txt`
passes 11/11. One registered run per suite, no re-runs.

## What it means

Chat junk on names ("Rome honestly", "Rose tbh", corrections too)
clarifies instead of writing junk, while real common-noun values on
sport/language/food/genre/occupation/instrument store normally — the
bench chains 139d broke now run exactly as loop139c.

## What it does not mean

Not a general common-noun fix: a listed-relation value really shaped
like Capitalised + common noun (a city called "Green Valley") is still
questioned; "maybe"/"probably" and lowercase-start tails still keep
base behaviour.

Reproduce (Mac CPU, offline, OMP/MKL=1, after seal):
`python -B scripts/fable_fix139e_probe.py --out
artifacts/fable-tail139e-20260922/probe139e-loop139e.json`;
`python -B scripts/fable_fix139e_bench.py`;
`python -B scripts/fable_marks123_all.py --agent
scripts/fable_loop139e_agent.py --config
artifacts/fable-tail139e-20260922/loop139e-config.json --out
artifacts/fable-tail139e-20260922/marks139e --workers 4`;
`python -B scripts/fable_fix139e_g3.py`.
Questions for Ben: none.
