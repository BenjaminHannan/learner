# Exp 171 RESULTS — name-shaped values (loop138d + one guard)

Base: loop138d read-only (`scripts/fable_loop138d_agent.py`,
`artifacts/fable-agent138d-20260922/loop138d-config.json`, its RESULTS.md
+ design doc read first). One change: `NameVal171Mixin` refuses
description values on 21 name keys (no write + one sealed clarify).
New files only: `scripts/fable_loop171_agent.py`,
`scripts/fable_fix171_*.py`, `artifacts/fable-nameval171-20260922/`,
`design/v3/30-modes/171-name-shaped-values-muse.md`. No commits, no
installs, Mac CPU, `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`. PASSMARKS +
cases + word lists + config + code hashed to SEAL.sha256.txt before any
registered run (`shasum -c` passes after). Ledger P171.1–P171.6 appended
first. Every seed/case reported, never averaged.

## Marks table (integer counts)

| mark | bar | number | status |
|---|---|---|---|
| T1 sealed 76-case/110-turn probe | 76/76 | 32/32 clarify (exact sealed reply, 0 writes, follow-up asks find nothing) + 44/44 byte-identical to loop138d (22 real names incl lowercase ana/zofia, 20 non-name relations, 2 corrections) (3.7 s) | PASS |
| T2 0 wrong writes | 0 | 0 facts on all 32 clarify cases; identical cases value-equal to taught | PASS |
| G1 bench121 (800 items, per-item vs sealed 138b rows) | exactly 4 predicted moves, 0 new wrong | new 192/4/4, old 198/2/0, edit200 150/50/0, bench132 195/4/1; moves: bench121-026/-099 + bench132-067 correct->abstain (spouse chain needs title "Queen"/"Lady", refused), bench132-152 wrong->abstain (inherited 138d) (63.2 s) | PASS |
| G2 marks123 (per-case vs frozen marks138d) | identical except predicted | p2 EQ (B4 fixed: Beth excluded); p4 only P4-08 pass->false-refusal ("actually Ana"); p3 l1-l6 verdict-identical (l5z1 FAIL inherited; l6 only timing metadata replied_before_kill); rt110/q1/q4/rt81/bench/sleep/soak identical modulo volatile seconds/paths (277.6 s) | PASS |
| G3 junk/red/sessions (vs 138d frozen rows + vs 138b rows) | 0 new vs 138d; vs 138b exactly inherited sets | 0 moves vs 138d on all 6 suites; vs 138b: rt136 C115/C124/C127/C129/C142, c150 A03 reply-only, f1 t14, 139b C10/C21, rt143 J8/K9/M3/O5/S4, sessions 36 moves + 3 writes (all == 138d rows); 0 new WRONG/WRONG-WRITE/writes beyond 138d (15.2 s) | PASS |
| G4 every run < 1500 s | < 1500 s | max 277.6 s (G2); daemon wrappers idle_seconds | PASS |

## Why the predicted moves happen (one note each)

- G1 026/099/067: bench edit-items supersede the chain through a spouse
  value ("Queen Sonja", "Lady Macbeth") whose first word is a title in the
  dictionary — the guard refuses, the chain breaks, abstain. Genuine-name
  collisions (Patty/Pat/Penny/Dick/Atom/Peter/Buffy/Lech/Tony/Marge/Beth/
  Bobby/Ann/Bob/Cora…) were added to the sealed given-names list instead
  (pre-seal corpus scan), so those chains hold.
- G2 P4-08: the suite's sealed expectation stores junk ("actually Ana");
  the guard reads "actually" as a common word and refuses. One honest
  disagree-and-list.
- G3 vs-138b sets: all are 138d's own sealed rows (138d M4 FAILs C124/
  C127/C129/C142/C10/C21/M3 included) — 171 adds nothing.

## Deviations / notes

Pre-seal dev runs (probe, G3, bench, marks) informed the predictions;
post-seal registered runs are the numbers above — no code/case edits after
the seal. Exclusion list grew pre-seal only (13 corpus names + common
nicknames + 12 bench spouse names + beth/bobby); T1 probe names all
verified non-dictionary pre-seal. No race flakes observed; no open
re-runs. Base negations ("not well") and "split that" clarifies fire
before the guard (base reply kept). A03 (cases150) reply-only diff is
byte-identical to 138d.

## What it means

The 8 director junk-writes are gone ("Kim's mom is sick" clarifies, 0
writes, follow-up finds nothing), while 44/44 name/non-name cases,
800 bench items (0 new wrong), all marks suites, and all 595 junk/red/
session turns match the base except the listed, predicted refusals.

## What it does not mean

Titles are still not names ("Lady Macbeth" chains abstain), and 138d's
inherited inverted-frame wrong-writes (C124/C127/C129/C142/C10/C21) are
unchanged — this fix closes the description-as-name class only.

## Questions for Ben

None — defaults taken (titles refuse; inherited FAILs listed, not fixed).

## Reproduce (`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`; `uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`)

- `scripts/fable_fix171_probe.py` → `probe171.json`
- `scripts/fable_fix171_bench121.py` → `fable_bench121_summary_loop171.json`
- `scripts/fable_marks123_all.py --agent scripts/fable_loop171_agent.py --config artifacts/fable-nameval171-20260922/loop171-config.json --out artifacts/fable-nameval171-20260922/marks171 --workers 4`
- `scripts/fable_fix171_g3.py` → `junk171-suites.json`, `sessions152-compare171.json`
