# Exp 138g RESULTS — merge layer A (loop138f + 139e/137e/158c/168)

Result first: PASS. loop138g stacks the four cleanly portable verified
fixes onto loop138f with zero unpredicted moves anywhere: M1 holds on
all four pieces (139e 65/65, 168 61/61, plus exactly the 6+8 listed
interactions), M2 holds except one listed reply-only move, M4/G1/G2/G3
show only the enumerated moves, 0 new WRONG / WRONG-WRITE / junk writes
vs loop138b on every suite. 157c + 160c are left out with reasons (see
design doc); `shasum -c SEAL.sha256.txt` passes 6/6 (no edits after the
seal); every ledger prediction held as written.

## Marks table (integers; every seed/case reported, never averaged)

| mark | bar | number | status |
|---|---|---|---|
| M1 added probes | same verdict+reply as own agent except listed | 139e 65/65 (27/27 exact, 0 writes); 137e 101/107 + 6 listed discourse leads, all 138f-identical; 158c 38/46 + 8 listed (6 138f-identical clarifies, O06/O10 grounded as written); 168 61/61 (A25 0 crash/0 naming/0 writes) | PASS |
| M2 138f pieces | unchanged except listed | 142 500/500; 146d 21/21; 153 50/50; 156b 116/116+T2 68/68 except N11 reply-only "I have no opinions." (168, 0 writes); 157 60/60; 158 59/59; 159 48/48; 150b 49/49 | PASS |
| M4 suites | 7 identical to 138b; vs 138f only listed | rt136 136/6/3 + C089 W→OK ("Suppose…" hypo-refused); cases150 57/57; f1 46/46; cases139b 101/101; rt143 107/7/10, M3 identical; sessions 165/15/0, 0 new writes | PASS |
| G1 bench121 | 0 moves, 0 new wrong vs 138f | 194/2/4, 198/2/0, 150/50/0, 196/3/1 | PASS |
| G2 marks123 | per-case = marks138f except 5 listed | P4-09 strip nonpass (stores clean ["Ana"]); rt81 + p3-l2 I_edges-03/O_user-03 reply-only 168 tightenings, verdicts kept; sleep SKIP renames file only; else identical incl. l5z1 | PASS |
| G3 director 7 | reply+store as sealed | G3-1 Ivy / G3-2 Leeds saves; G3-3 HEARSAY_MSG / G3-4 HYPO clarify, 0 writes; G3-5 Hey-Jude save (138f-identical, 157c out); G3-6 favourites; G3-7 name-decline | PASS |
| G4 time | every run < 1500 s | m1 7+26 s, junk 2 s, rt143 5 s, sessions 4 s, bench 52 s, g3 1 s, marks 263 s | PASS |

## Deviations / notes

None from the sealed plan. Raw driver rc=1 on M1-pieces/M2 is the sealed
design (drivers count raw diffs; the sealed bar exempts the listed
interactions, and the fail-ID sets match the sealed lists exactly — no
more, no fewer). One pilot wave per suite enumerated the moves; the
registered runs re-ran everything after the seal and matched every
prediction. No flakes, no open re-runs, no rule changes. l6
replied_before_kill + daemon-workdir hashes are timing-volatile only
(verified scrubbed-equal). Never wrote outside owned paths.

## What it means

Four overnight fixes now ride the clean stack with no regressions:
junk tails strip or clarify, framed teaches get one honest reply each,
city questions answer, and self-questions can no longer invent
teachings — one redteam wrong-write (C089) is gone too.

## What it does not mean

It does not restore titles ("Hey Jude" still saves, 157c needs its 157b
base) or bare-correction disambiguation (160c needs its 160b base), and
it does not add general question answering (six 158b-base shapes still
clarify) — all queued per the design doc.

## Questions for Ben

None — conservative defaults taken (two pieces left out rather than
ported with extra base behaviour).

## Reproduce (each < 1500 s; `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`;
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`)

- `scripts/fable_fix138g_m1.py --only pieces` → `m1-138g-pieces.json`
- `scripts/fable_fix138g_m1.py --only f` → `m1-138g-f.json`
- `scripts/fable_fix138g_suites.py --only junk|rt143|sessions|bench|g3`
- `scripts/fable_marks123_all.py --agent scripts/fable_loop138g_agent.py --config artifacts/fable-agent138g-20260922/loop138g-config.json --out artifacts/fable-agent138g-20260922/marks138g --workers 4`
- `scripts/fable_fix138g_compareg2.py` (read-only enumeration)
- Seal: `shasum -c artifacts/fable-agent138g-20260922/SEAL.sha256.txt`
