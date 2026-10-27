# Exp 138f RESULTS — stack clean (138d minus 155, 154, 138c)

Result first: PASS. loop138f removes exactly the three pieces Step 1
named as causes (attribution-138f.json) and nothing else. All 7 cases are
byte-identical to loop138b, 0 new WRONG / WRONG-WRITE / junk writes
anywhere vs loop138b, all 8 remaining piece probes pass, and every
registered move was predicted in PASSMARKS.md before the seal
(`shasum -c SEAL.sha256.txt` passes; no code edits after the seal).

Removed (smallest fixing set; no single piece fixes C124/C127/C129/C142/
M3): 155 inverted frames (6 wrong writes: plain inversions, the all-caps
shout, compound-inversion junk parses), 154 yes/no (M3 ungrounded "Yes"),
138c serving rule (no wrong of its own; its L134 base path changed the
leftover-clarify reply text on 5 cases). Kept: 142, 146d, 153, 156b, 157,
158, 159, 150b. Per-piece queued fixes are in the design doc.

## Marks table (integers; every seed/case reported, never averaged)

| mark | bar | number | status |
|---|---|---|---|
| M1 remaining probes | each at own bar | 142: 500/500; 146d: 21/21 (H13 ok, H17/H18 fail as on 146c); 153: 50/50 0 writes; 156b: 116/116 + T2 68/68 (N02 = base-identical no-write, 155 gone); 157: 60/60; 158: 59/59; 159: 48/48 0 writes; 150b: 49/49 | PASS |
| M4 7 cases + junk | 7 identical to 138b, 0 new wrong | C124/C127/C129/C142/C10/C21/M3 all identical; rt136 135/7/3, 0 moves; cases150 57/57, 0 moves; f1 46/46 (only f144-t14 W→OK, inherited); cases139b 101/101, 0 moves; rt143 M3 identical, only S4 W→OK (inherited); sessions 165 OK/15 UNHELPFUL/0 WRONG = 138d's 36-move set exactly, same 3 correct S2 writes | PASS |
| G1 bench121 | 0 new wrong vs 138b | new 194/2/4, old 198/2/0, edit200 150/50/0, bench132 196/3/1: 0 moves except bench132-152 wrong→abstain (inherited listing) | PASS |
| G2 marks123 | per-case = marks138d except predicted | verdict moves only: l5z1 turns 49+58 →CLARIFY (status_match 58/60); rt81 D_q_vs_s-04 →OK (=138b), I_edges-03 →UNCLEAR (=138b); sleep SKIP names new file. Reply-only: p2 4, rt110 13, rt81 10, l2 12, l5z1 stage tags (all 138c-revert texts). l1/l2/l3/l4/l5z2/l6/q1/q4/p2/p4/bench/soak otherwise identical; l6 200/200/200 correct, 0 wrong (replied_before_kill 6/13/11, timing-volatile, reported). l5z1 + rt81 FAIL labels inherited per-case | PASS |
| G3 red/sessions | 0 new wrong vs 138b | covered by M4 numbers above; every move predicted | PASS |
| G4 time | every run < 1500 s | m1 28.3 s, junk 7.2 s, rt143 16.3 s, sessions 6.9 s, bench 53.7 s, marks wave 273.4 s | PASS |

## Deviations / notes

None from the sealed plan. One open pilot wave per suite enumerated the
predicted moves; the registered runs re-ran everything after the seal and
matched every prediction (verified field-by-field). No race flakes seen,
so no open re-run was needed. No rule changes after the seal. Speed/soak
latency out of scope per the brief (no 15k test run).

## What it means

The 138d wrong-write regression is fully explained and removed: six
inverted-teach writes belonged to piece 155, one ungrounded yes belonged
to 154, and five reply-text diffs belonged to the 138c base path. The
remaining 8-piece stack holds every bar with zero new wrongs.

## What it does not mean

It does not restore the removed capabilities (inverted teaches, yes/no
answers, grounded self-serves) — those need per-piece fixes, queued in
the design doc — and it does not address 138d's speed/soak-latency FAILs,
owned by a separate experiment.

## Questions for Ben

None — defaults taken (smallest removal set; 156b-N02 bar corrected to
base behaviour; FAIL labels inherited, never re-run into passes).

## Reproduce (each < 1500 s; `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`;
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`)

- `scripts/fable_fix138f_m1.py` → `m1-138f.json`
- `scripts/fable_fix138f_junk.py` → `junk138f-summary.json`
- `scripts/fable_fix138f_rt143.py` → `redteam143-compare.json`
- `scripts/fable_fix138f_sessions.py` → `sessions152-compare.json`
- `scripts/fable_fix138f_bench.py` → `fable_bench121_summary_loop138f.json`
- `scripts/fable_marks123_all.py --agent scripts/fable_loop138f_agent.py --config artifacts/fable-agent138f-20260922/loop138f-config.json --out artifacts/fable-agent138f-20260922/marks138f --workers 4`
- Seal: `shasum -c artifacts/fable-agent138f-20260922/SEAL.sha256.txt`
