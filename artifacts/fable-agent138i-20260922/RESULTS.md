# RESULTS — Exp 138i: merge layer B part 2 onto loop138h (Muse)

Loop138i stacks 9 verified pieces onto loop138h as mixins only (no loop155
in MRO or modules): 154e multi allow-list (incl. language) outside 172b
copula asks, 171b word-names, 173b replacing 173, 167e reply templates, 167d
verbs, 154d yes/no, 174 of-chains, 170 index. Registered verdict: **PASS**
(every move was predicted case-by-case in PASSMARKS before the seal; seal
9/9 OK after all runs; no post-seal edits).

## Marks table (integer counts, every case reported)

| mark | bar | number | verdict |
|---|---|---|---|
| M1 pieces | identical to own agent except listed classes | 154e 76/76, 172b-t1 81/81, t1c 92/92, 154d 38/38; t1b 75/83; 171b 120/122; 173b 58/94; 167e 33/34; 167d 22/32; 174 39/40; no-155 | PASS |
| M2 138h cases | identical to loop138h except predicted | A: moves only 13 ids (154e x5, 171b x8 incl. S13); B: 139e/146d/150b/153/157/158/159 pass, 137e/158c/168/156b fail-sets == 138h, 142 exactly 50 pet/song | PASS |
| G1 bench v3 | 0 new wrong vs 138h | 138i 800 items, 17 moves, 0 new wrong; 138h-v3 == old 799/800 (162 wrong->abstain) | PASS |
| G2 frozen | 0 moves except predicted, 0 new wrong/write | rt136 0, rt143 0, sessions 1 (S4 n1) | PASS |
| G2 marks123 | per-case vs marks138h, moves only as predicted | p2 6, l5z2 100, bench 298, p4 1; all == owning-piece rows; rest identical; 0 new wrong/write | PASS* |
| G3 pairs | 6/6 reply-exact, fresh loops | a,b,c,d,f == own agent; e composed Urdu+Hindi; d saves Juno | PASS |
| G4 index | on == off, 1000 turns | 0 reply diffs, facts-sha equal, events 1129/1129 | PASS |

*marks123 suite bars read FAIL at suite level by construction (ask-first
kept-chain under the stock no-confirm driver); every per-case move was
predicted by id and matches the owning piece's sealed rows (see below).

## Detail

M1 diffs: 172b-t1b n=9,10,11 (language multi-add "Spanish and French") +
state-carry n=12,16,20,24,28 (replies identical to 172-own); 171b T1-D12
lineage wording (==138h), T1-C02 dog multi-add; 173b t1 F12/F20 multi-add,
F14 MILO clarify, A/O lineage forms (==138h), t1c C/O reply-forms only
(stored [] both, ==138h), W/I identical to 173b-own; 167d X01-X10, 167e n32,
174 n35 lineage forms (all ==138h). M2-A moves vs 138h (13): 166c
F12/F20, 166c-B C11, 173-t1 F12/F20 (multi-add "(I also have …)"); 166c F14,
166c-B C06/C08, 166c-C S02/S03/E07/E08/T07/T08, 173-t1b S13 (lowercase
screen, no write). M2-B-142: 25 pet/song ask->multi-add + 25 ask-prefix
knock-ons. G1 138i-v3 moves: new_121 026/069/079/110/137/162/195, bench132
022/045/113/142/162/179, edit200 mquake-033, s2fresh 031/125/200. G2 p2
B1/B2/B3/B7/B8/F2 finals byte-identical to 172b sealed rows; l5z2 100-id set
== 172b; marks-bench 400/400 verdict+reply == 172b rows; P4-08 == 171b-own;
l2/l5z1 fail per-case identically to 138h; rt110/rt81/q1/q4/soak identical;
soak 2000 turns 0 lost/wrong/doubled.

## Refinement (reported, verdicts unaffected)

PASSMARKS G1 prose says all 17 moves "keep both values and ask";
bench121-4hop-026 instead decline-abstains (confirmed chain breaks, same
mechanism as 162). Id, direction (correct->abstain) and 0-new-wrong held;
reply states nothing false. No re-run hidden; no rule change.

## Deviations from plan

Bench protocol v3 per director resume note (confirming "yes" after edit
turns); 138h-v3 == 138h-old shown (799/800 + noted 162). marks123 bench
stays stock (no confirming user) with ask-first moves predicted by id and
verified against 172b's sealed rows, the way 172b did. No other agent's
file touched; no repo-root notebook writes. Scratch in scratch138i-pilot/.

## Reproduce (Mac CPU, offline; seal 12:26)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix138i_m1pieces.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix138i_m2.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix138i_suites.py --only g3,g4 --out artifacts/fable-agent138i-20260922/g3g4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix138i_suites.py --only rt136,rt143,sessions --out artifacts/fable-agent138i-20260922/g2frozen
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix138i_suites.py --only benchv3 --bench-arm loop138i --out artifacts/fable-agent138i-20260922/g1bench
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop138i_agent.py --config artifacts/fable-agent138i-20260922/loop138i-config.json --out artifacts/fable-agent138i-20260922/marks138i --suites p2,p3,p4,rt110,q1,bench,rt81,sleep,soak,q4 --workers 2
```

## What it means

Nine verified behaviours compose on one loop with no surprise
interactions: every reply or stored fact that differs from loop138h was
named in advance, and asking-first plus keeping both values cost zero new
wrong answers anywhere.

## What it does not mean

It does not mean re-teaches apply silently anymore — allow-listed
relations add, everything else asks, so unconfirmed drivers score
kept-chain stale by design.
