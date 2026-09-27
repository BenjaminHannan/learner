# Exp 171b RESULTS — word-names save (loop171 + one exception)

Base: loop171 read-only (`scripts/fable_loop171_agent.py`, its RESULTS.md +
design doc read first). One change: `NameVal171BMixin` (subclass of 171's
mixin, bypassing only its guard) saves name-relation values of ONLY 1–3
Title-case tokens even when dictionary words — except the sealed 62-word
closed list (state/place/time words), refused exactly as in 171. New files
only: `scripts/fable_loop171b_agent.py`, `scripts/fable_fix171b_*.py`,
`artifacts/fable-nameval171b-20260922/`,
`design/v3/30-modes/171b-word-names-muse.md`. No commits, no installs, Mac
CPU, `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`. PASSMARKS + cases + lists +
config + code hashed to SEAL.sha256.txt before any registered run
(`shasum -c` passes before AND after all runs). Ledger P171b.1–P171b.8
appended first. Every seed/case reported, never averaged.

## Marks table (integer counts)

| mark | bar | number | status |
|---|---|---|---|
| T1 sealed 76-case 171 probe | 76/76, all rows byte-identical to sealed probe171.json | 32/32 clarify (exact sealed reply, 0 writes, follow-up finds nothing) + 44/44 identical to 138d AND sealed 171 rows (1.2 s) | PASS |
| T1b new 46-dialogue probe | 46/46 | 16 word-name saves + 4 save-after-clarify (director Zed/Bo/Tia/Rae cases) saved + answered; 18/18 refused (12 lowercase + Sick/Busy/Tired/Happy/Late/Here); 8/8 identical | PASS |
| T2 0 wrong writes | 0 | 0 facts on all clarify cases; saves/identical value-equal (122 turns) | PASS |
| G1 bench121 (800 items, per-item vs 171 AND sealed 138b rows) | exactly 2 predicted moves vs 171, 0 new wrong | vs 171: bench121-099 + bench132-067 abstain→correct ("Lady Macbeth" saves, chains heal); vs 138b: 026 correct→abstain ("Queen Sonja of Norway" has lowercase "of") + 152 wrong→abstain (both inherited) (46.2 s) | PASS |
| G2 marks123 (per-case vs frozen marks171) | identical except predicted | all 10 reports + bench rows + soak identical; only sleep SKIP reason names the new file; p3 l5z1 FAIL + p4 P4-08 nonpass inherited (285.6 s) | PASS |
| G3 junk/red/sessions (vs 171 frozen rows + vs 138b rows) | 0 moves/diffs vs 171; vs 138b exactly 171's sets | 6/6 suites 0 verdict/reply/write diffs vs 171; inherited: rt136 C115/C124/C127/C129/C142, A03, t14, C10/C21, rt143 J8/K9/M3/O5/S4, sessions 36 moves + 3 writes (17.5 s) | PASS |
| G4 every run < 1500 s | < 1500 s | max 285.6 s (G2) | PASS |

## Why the predicted moves happen (one note each)

- T1b word-name saves (20) + I07 Biscuit: 171's first-word rule refused them
  (hope/grant/rich/ora/… are dictionary words); 171b's Title-case rule saves
  them exactly like 138d. Right in every case: Hope, Grant, Rich, Ora, Jade,
  Biscuit are genuine names of fictional people/pets here.
- T1 holds 76/76 because the only six Title-case clarify values
  (Sick/Tall/Mean/Brown/Here/There) are real descriptions and all sit on the
  sealed closed list — holding them is right.
- G1 099/067 heal: "Lady Macbeth" is 2 Title-case tokens, not closed-listed;
  026 still abstains: "Queen Sonja of Norway" contains lowercase "of".
- G3 rt143 M3 trips the same inherited new_wrong_vs_138b counter as 171's
  own driver (OK→WRONG-ANSWER is 138d's row, unchanged); the G3 driver rc=1
  comes only from these inherited vs-138b counters, 0 from vs-171 diffs.

## Deviations / notes

Pre-seal dev runs (probe, bench, G3, marks) informed the predictions (one
probe-code fix pre-seal: tuples→lists normalisation for sealed-row compare;
one g3-driver key-name fix pre-seal); post-seal registered runs are the
numbers above — no code/case/config/list edits after the seal (seal
re-verified OK after). G1/G3 drivers copy 171's files with only the agent
swapped but reuse 171's driver stack (138d SPLITS/load_rows/junk/sessions/
rt143 + sealed scorers) by import. No race flakes; no open re-runs. Scratch
daemon dirs deleted post-run (87 MB total, parity with 171's 77 MB).

## What it means

Word-names that are also English words (Hope, Grant, Rich, Ora, …) save and
answer again — including as the answer to the agent's own "What is X's
name?" — while all 32 description clarifies, all bench/marks/junk/session
verdicts match 171 except the two healed "Lady Macbeth" chains.

## What it does not mean

Single-token closed-list surnames ("Young", "Brown") still refuse, titles
save by design, and 138d's inherited inverted-frame wrong-writes plus the
"Queen Sonja of Norway" abstain are unchanged — phrases with any lowercase
word still refuse.

## Questions for Ben

None — defaults taken (whole-value closed-list match; titles save; residual
single-token surname refusals listed, not fixed).

## Reproduce (`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`; `uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`)

- `scripts/fable_fix171b_probe.py` → `probe171b_T1.json`, `probe171b.json`
- `scripts/fable_fix171b_bench121.py` → `fable_bench121_summary_loop171b.json`
- `scripts/fable_marks123_all.py --agent scripts/fable_loop171b_agent.py --config artifacts/fable-nameval171b-20260922/loop171b-config.json --out artifacts/fable-nameval171b-20260922/marks171b --workers 4`
- `scripts/fable_fix171b_g3.py` → `junk171b-suites.json`, `sessions152-compare171b.json`
