# RESULTS — Exp 139d: unknown-tail clarify on loop139c (Muse, 2026-09-22)

Result first: the clarify works exactly as specified (probe 65/65, exact
replies, 0 writes; G3 zero moves) — but the sealed rule is too broad for
real bench prose: values like "Gaelic football" / "American football" /
"Wa language" are indistinguishable from chat tails, so G1 FAILs (20 new
wrong, 33 moves) and G2 FAILs on bench detail rows only (11 verdict +
2 teach-reply moves; every report suite 0 moves).

## Marks (every seed/case reported)

| mark | bar | got | verdict |
|---|---|---|---|
| T1 probe (65: 28 tailu + 16 same + 21 other) | every case OK | sealed run 59/62 OK + 3 case bugs (D1); open re-run 65/65 OK, 28/28 exact replies | PASS w/ deviation (P139d.1 held) |
| T2 wrong writes | 0 | 0 in both runs | PASS (P139d.2 held) |
| G1 bench 4x200 vs sealed 139c rows | 0 new wrong, 0 moves | 186/3/11 + 187/7/6 + 150/50/0 + 182/9/9; 33 moves, 20 new wrong | FAIL (P139d.3 falsified) |
| G2 marks123 semantic vs marks139c | identical every suite | reports identical (p2 64, p4 30, rt81 74, rt110 62, p3 submarks, q1/q4/soak/sleep/bench-sum); bench-rows detail: 11 verdict + 2 reply-only moves | FAIL (P139d.4 falsified) |
| G3 rt136 + rt143 + sessions | 0 new WRONG/write, 0 moves | 135/7/3 + 106/11 + 129/2, 0 moves, 0 new wrong | PASS (P139d.5 held) |
| G4 time | each run < 25 min | probe 3.0 s, bench 61.8 s, marks ~300 s (rt110 145.3 s, no flakes), g3 21.9 s | PASS (P139d.6 held) |

## Why the FAILs happened (load-bearing, one note each)

- G1/G2-bench: bench teaches carry real values shaped exactly like the
  trigger (Capitalised + lowercase common noun): "Gaelic football",
  "American football" (-> `Did you mean "American"?`), "Wa language".
  The guard clarifies mid-chain, later hops fall back to London/Europe/
  abstain/self answers. Same 11 items move in G1 and the marks bench
  suite; the 2 edit200 items differ in teach_replies only (final
  verdicts identical). Pre-seal scan found 0 hits only because it
  matched possessive shapes, while bench values arrive via declarative
  bench73 templates — scan-method miss, reported.
- T1 sealed run (D1, case bugs, agent correct all 3): "Max maybe." /
  "Leeds probably." never reach any guard — base ears split-clarify
  first (byte-identical both arms, now locked as O19/O20); "black
  honestly" starts lowercase so the sealed rule byte-matches loop139c's
  dirty correction prompt (now locked as O21). U08/U09/U23 rewritten to
  in-spec shapes; agent untouched.

## Cosmetic-only notes (verdicts identical, not FAILs)

- rt110: no flakes this run, no rerun needed; 62/62 verdict-identical
  (S1 OK->BUG as base). p3 L5-Z1 58/60, P4-09, rt81 60/0/14 match base
  sealed-expectation bars exactly. Sleep SKIP reason names the new file.

## Deviations (post-seal edits; affected marks re-run in the open)

- D1 (cases, post-seal): 3 case bugs above; regenerated cases139d.json
  (62 -> 65 cases incl. 3 base-identity locks), re-ran probe in the
  open: 65/65 OK. Agent untouched.
- D2 (analysis driver, post-seal): compare script descended into daemon
  tmp workdirs (timestamps/hash-chains); fixed the filter to report
  files + top-level rows. No registered run affected.
- Seal: `shasum -c SEAL.sha256.txt` passes except the 3 D1/D2 files
  (cases script + cases json + compare script), as reported. The one
  change (`fable_fix139d_tail.py`, `fable_loop139d_agent.py`) is
  byte-identical since before the seal.

## What it means

Unknown chat tails on name values now clarify instead of writing junk
("Rome honestly" -> `Did you mean "Rome"?...`, 0 writes, corrections
included), while titles, lowercase values, connectors, questions, junk,
redteam and session suites behave exactly as loop139c.

## What it does not mean

Not safe for declarative prose: any real Capitalised + common-noun
value ("Gaelic football", "Pad thai") is questioned or refused, which
breaks multi-hop bench chains; "maybe"/"probably" and lowercase-start
tails keep base behaviour by design.

Reproduce (Mac CPU, offline, OMP/MKL=1, after seal):
`python -B scripts/fable_fix139d_probe.py --out
artifacts/fable-tail139d-20260922/probe139d-loop139d.json`;
`python -B scripts/fable_fix139d_bench.py`;
`python -B scripts/fable_marks123_all.py --agent
scripts/fable_loop139d_agent.py --config
artifacts/fable-tail139d-20260922/loop139d-config.json --out
artifacts/fable-tail139d-20260922/marks139d --workers 4`;
`python -B scripts/fable_fix139d_g3.py`.
Questions for Ben: should the trigger gain a common-noun allowlist
(e.g. football, language), or stay names-only as sealed?
