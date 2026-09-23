# Exp 180 — lowercase-names recase on loop138g — RESULTS (plain words)

Loop180 = loop138g plus one outermost ears step: if a turn doesn't parse
as typed, re-case it once (capitalise the first word; fix lowercase
words that match names already in the notebook) and retry. Re-cased
questions answer directly; re-cased teaches ask "Did you mean: ...?" and
write only after you say yes. Unknown words (bob, kofis, will/may/rose
when not taught) are never touched. Missing-apostrophe typos (kofis) are
exp 165's job, not this one.

## Marks table (integer counts, every turn reported, nothing averaged)

| mark | bar | result |
|---|---|---|
| T1 sealed case180.json (35 steps / 41 turns) | 35/35 step checks | PASS 35/35: 7/7 setup parity, 12/12 lowercase asks == capitalised-twin replies (1-hop x6, 2-hop x4, of-chain x2), 6/6 lowercase teaches confirm with 0 writes before yes and twin reply+facts after yes, 10/10 traps byte-identical to 138g (1.1 s) |
| T2 redteam136 (145 cases) | 0 moves, 0 new wrong | PASS: 136 OK / 6 WRONG-WRITE / 3 MISSED, all base-identical; moves_vs_138g=0, new_wrong_vs_138b=0 |
| T2 redteam143 (124 cases) | 0 moves, 0 new wrong | PASS: 107 OK / 7 MISSED / 10 WRONG-ANSWER, all base-identical; moves=0 |
| T2 sessions152 (180 turns) | 0 moves, 0 new writes | PASS: moves=0, new_wrong=0, new_writes=0 |
| T2 bench121 (800 items, 4 splits) | 0 moves, 0 new wrong | PASS: 200+200+200+200 per-item verdict-identical to sealed 138g rows |
| T2 marks123 (10 reports) | per-case identical except predicted | PASS: 10/10 reports identical after scrub; only the sleep SKIP agent filename + total_seconds timing differ (predicted); suite FAILs p3-l5z1, p4-1-nonpass, rt81-59ok/15unclear inherited byte-identical; max run 255.1 s |
| G4 time | every run < 1500 s | PASS (max 255.1 s; daemons take idle_seconds) |

Yes/no asks: loop138g answers no yes/no twin (both cases clarify), so the
brief's `if 138g answers the capitalised twin` admits none; trap X10
(`is lou kip's boss?`) pins the clarify stays put.

## What it means

Typing in lowercase now works for names the assistant already knows:
questions answer with the right reply, and teachings confirm once
("Did you mean: Lou's boss is Kim?") instead of silently saving a
second, wrong-cased copy — with zero behaviour change on anything else.

## What it does not mean

It does not fix missing apostrophes (`what is kofis city` still doesn't
understand — that's exp 165), it does not teach yes/no answering, and it
does not guess unknown names (bob/will/may/rose behave exactly as before).

## Deviations (post-seal edits, all re-run in the open)

- D1 (`notebook_names180`): only single-token values count as names. A
  multi-word value ("The Glass Orchard") leaked "The" as a name, so a
  determiner misfired the confirm (rt143 C5, found in the registered
  run). Fixed; rt143 re-run open: 0 moves.
- D2/D3 (`confirm_predicate180`): confirm only when the turn needs a
  known-name fix AND its first+last words are known names; retry-confirms
  need this on the original turn. Frozen sessions teach new lowercase
  names (`vera's city is lima`, filler leads like `btw marta's ...`) and
  the base saves them — 29 session moves, fixed; sessions re-run open:
  0 moves. First-word-only repairs (`no Vera's city is Quito`) never
  confirm.
- T1 re-ran open 35/35 after each edit; rt136 re-ran open 0 moves on
  final code; sessions+bench+marks123 ran once, on final code
  (sha 9e9861d6; probe/suites drivers unchanged from seal 5a7c8b81 /
  bda4c101).

## Reproduce (Mac CPU, offline, one suite at a time)

- `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`
- `uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix180_probe.py` (T1)
- `... python -B scripts/fable_fix180_suites.py --only rt136|rt143|sessions|bench` (T2 suites)
- `... python -B scripts/fable_marks123_all.py --agent scripts/fable_loop180_agent.py --config artifacts/fable-lowercase180-20260922/loop180-config.json --out artifacts/fable-lowercase180-20260922/marks180` (T2 marks)
- `... python -B scripts/fable_fix180_comparem.py` (marks scrub-compare)

## Questions for Ben

None. Most conservative defaults taken throughout (unknown words never
capitalised; teaches with any unknown name save exactly like the base).
