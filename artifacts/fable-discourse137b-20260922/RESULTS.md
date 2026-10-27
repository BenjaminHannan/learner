# RESULTS — Exp 137b: discourse-glued names (Muse, 2026-09-22)

Result first: the one-change mixin fixes C089/C122 and all 31
discourse-led twins exactly, with zero moves on every sealed suite
(800 bench items, all marks123 suites per-case, 145+124+180+57+46+101
junk/session/redteam cases). Two registered suite FAILs are inherited
byte-for-byte from loop138b (p3 L5-Z1, rt81 label); no new wrong anywhere.

Step 1 (asked): 137's 2–4 Title-case token rule is
`scripts/fable_fix137_names.py:123-127`
(`toks` 2..`MAX_NAME_TOKENS` + `all(is_name137_token)`), called from
`scripts/fable_loop138b_agent.py:142-169` (`_upgrade137`, line 149).

## Marks (every seed/case reported; deterministic, no seeds)

| mark | bar | got | verdict |
|---|---|---|---|
| T1 probe (59 cases) | D twins = bare (reply+write); T/R identical to 138b; 0 wrong writes | 59/59 OK: D 31/31 (16 words + Hi./Hello./Okay. + 12 questions), T 12/12, R 16/16 | PASS |
| T2 C089/C122 | 0 junk writes | both store `[Tom,boss,Ann]`, reply `Saved: Tom's boss is Ann.`, sealed verdicts stay WRONG-WRITE (nowrite expectation) with clean subjects | PASS |
| G1 bench (800) | 0 new wrong, every move predicted | new 194/4, old 198/0, edit200 150/50/0, bench132 196/2; 0 verdict + 0 reply moves | PASS |
| G2 marks123 | per-case = marks138b except predicted | p2 64/64 rows identical; p4 30/30; q1 F5+M5; bench rows 400/400; q4 leaks []; soak 2000/3/0-0-0; sleep SKIP (reason names new file, verdict identical); p3 l1–l4/l6/L5-Z2 PASS, L5-Z1 58/60 (42/43 UNSUPPORTED, as 138b); rt81 60/0/14 (inherited FAIL label); rt110 62/62 verdict+reply identical, 3/62 statuses-metadata noise (see note) | PASS (p3/rt81 FAILs inherited identical) |
| G3 junk/sessions | 0 new WRONG/junk, moves predicted | rt136 135 OK/7 WW/3 MISSED, 0 verdict moves, C089/C122 clean-store, junk 2→0, C090/C105 stay OK; 143 106/7/11 0 moves; sessions 129 OK/2 WRONG both arms 0 moves; 150 57/57, f1 45/46+1, 139b 101/101, 0 moves | PASS |
| G4 time | each run < 1500 s | probe 4.0, junk 12.9, sessions 11.5, rt143 25.3, bench 116.6, marks123 633.0 | PASS |

Notes. (1) rt110 F1/M1/D6: `statuses` log labels differ
(`['write']` vs `[]`) with identical replies, verdicts and fact_writes;
in-process `last_records` are identical on both agents, so this is the
known mailbox-log race, not a verdict flake — no open re-run (10 min)
spent on metadata. (2) Title edge, as predicted: "Hey Jude's director
…" → Jude (138b: Hey Jude); "Mary Ann's favorite movie is Hey Jude." →
Jude (138b: Hey Jude). No sealed suite contains a 137-position title
(scanned 800 bench inputs + rt136/143 + sessions + marks sources).
(3) No code edit after the seal: `shasum -c SEAL.sha256.txt` passes.

## Deviations

- D1 (doc arithmetic, file untouched): PASSMARKS says "56 cases"; the
  sealed probe file holds 59 (16+3+12 D, 12 T, 16 R). All thresholds
  (≥50, ≥25 across ≥12 words, ≥10, ≥15) hold either way; 59/59 OK.

## What it means

Discourse-fronted teaches/questions ("Suppose Tom's …", "Btw …",
"So what is …") land on the bare twin exactly; junk subjects ("Suppose
Tom", "Hi. Tom", "Also Wren") are gone; hypothetical of-forms
("Imagine the capital …"), "Actually, …", lowercase phone sludge and
abbreviations ("A. A. Milne") are byte-identical to loop138b.

## What it does not mean

Not an understanding of hypotheticals ("Suppose …" still teaches the
rest as fact); titles in 137 position do not survive (listed edge);
lowercase-fronted sludge still clarifies with 0 writes, as before.

Seal `SEAL.sha256.txt`, ledger P137b.1–7 pre-run. Mac CPU, offline,
OMP/MKL=1. Reproduce: `… python -B scripts/fable_fix137b_probe.py`;
`… python -B scripts/fable_fix137b_bench.py`;
`… python -B scripts/fable_fix137b_junk.py`;
`… python -B scripts/fable_fix137b_redteam143.py`;
`… python -B scripts/fable_fix137b_sessions.py`;
`… python -B scripts/fable_marks123_all.py --agent
scripts/fable_loop137b_agent.py --config
artifacts/fable-discourse137b-20260922/loop137b-config.json --out
artifacts/fable-discourse137b-20260922/marks137b --workers 4`.
Questions for Ben: none.
