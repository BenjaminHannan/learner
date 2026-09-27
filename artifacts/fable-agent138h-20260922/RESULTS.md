# Exp 138h RESULTS — merge layer B part 1 (5 text fixes onto loop138g)

Result first: PASS. loop138h stacks the five verified 150/162b-lineage text
fixes onto loop138g with zero unpredicted moves anywhere: M1 holds on all
eight probe arms (diff-ID sets match the seal exactly, no more no fewer),
M2 holds with exactly the sealed 6+7+1+3+1 rows, M4/G1/G2/G3 show only the
enumerated moves, 0 new WRONG / WRONG-WRITE / junk writes vs loop138b on
every suite. 173b is not ported (seal but no PASS RESULTS — 173 ported
instead, stated); 155 is absent (MRO has no 155 class, no fable_loop155*
module imported — check output in m1-138h-pieces.json). `shasum -c
SEAL.sha256.txt` passes 6/6 with no post-seal edits; every ledger
prediction held as written (8/8).

## Marks table (integers; every seed/case reported, never averaged)

| mark | bar | number | status |
|---|---|---|---|
| M1 pieces | same verdict+reply as own agent except listed | 162b 48/76 + 28 listed; 165 37/53 + 16; 166c 34/52 + 18; B 24/30 + 6; C 16/24 + 8; 173-t1 35/52 + 17; 173-t1b 32/45 + 13; 167b 27/64 + 37 (classes R1–R5 + CAP rows, all pilot-verified per-turn piece/138g-identical, 0 OTHER) | PASS |
| M2 138g pieces | unchanged except listed | 139e 65/65 clean; 137e 6 fails (138g-identical); 158c 7 fails + O01 improvement ("Sue's city is Leeds."); 168 3 fails (name replies); 138f 8 at bar except 156b-N11 reply-only | PASS |
| M4 suites | 7 identical to 138b; vs 138g only listed | rt136 136/6/3 + C089 kept; cases150 57/57; f1 46/46; cases139b 101/101; rt143 107/7/10 M3 identical; sessions 166/14 + exactly S4-pets-identity/1 ("Saved: your dog is biscuit.") | PASS |
| G1 bench121 | 0 moves, 0 new wrong vs 138g | 194/2/4, 198/2/0, 150/50/0, 196/3/1 | PASS |
| G2 marks123 | per-case = marks138g except predicted | rt81 O_user-02/-03, p3-l2 O_user-02/-03, rt110 P1/P3, sleep rename; p4 P4-09, l5z1 FAIL, l6 kept | PASS |
| G3 director 5 pairs | reply+store as sealed | 10/10 (drummer clarifies; toms-boss lowercase answer; sister Ada; Juno clarify + don't-know; Kwame verb save+answer) | PASS |
| G4 time | every run < 1500 s | m1 8.8 s, m2 16.3 s, junk/rt143/sessions small, bench ~60 s, g3 2 s, marks 256.6 s | PASS |

## Deviations / notes

Two pre-seal pilot findings, both fixed/listed before the seal (no
post-seal edits): (1) the 168 unsure path rendered the raw USER key
("USER's name (never taught)") — added a my-file-only turn() backstop that
scrubs residual raw keys unless the turn mentions USER literally (A22 now
"I am unsure about: your name (never taught)."); (2) that backstop first
touched the O13 literal-USER control — gated on literal mention, O13 now
raw-138g-identical. Post-seal metadata-only note: p3-l2 l5z1-T59
ears_stage "fake"/1.0 vs "none"/0.0 (verdict CLARIFY, reply+store
identical, 0 writes). No flakes, no open re-runs, no rule changes. l6
replied_before_kill + daemon paths timing-volatile only. Never wrote
outside owned paths. G3h-4a "My name is Juno." clarifies (Juno is a
dictionary word, not name-shaped — loop173-identical, not a bug).

## What it means

Plural teaches ("The Beatles' founder…"), typo'd possessives ("toms
boss"), first-person facts ("my sister…"), the user's name, and verb facts
("lives in…") now all work on the clean stack, with every old behavior
kept except the listed, intended moves.

## What it does not mean

It does not teach singular "The X" names the 162-chain way (those behave
as 138g: some save, some clarify), it does not render multiword Saved
labels with underscores (138b mouth renders spaces), and verb saves still
trip rt110's pre-167 pronoun rows (P1/P3, inherited from loop167) — all
listed per the design doc.

## Questions for Ben

None — conservative defaults taken (173 not 173b; 155 out; stale judge
labels documented, not patched).

## Reproduce (each < 1500 s; `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`;
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`)

- `scripts/fable_fix138h_m1pieces.py --out artifacts/fable-agent138h-20260922/m1-138h-pieces.json`
- `scripts/fable_fix138h_m2.py --out artifacts/fable-agent138h-20260922/m2-138h.json`
- `scripts/fable_fix138h_suites.py --only junk|rt143|sessions|bench|g3`
- `scripts/fable_marks123_all.py --agent scripts/fable_loop138h_agent.py --config artifacts/fable-agent138h-20260922/loop138h-config.json --out artifacts/fable-agent138h-20260922/marks138h --workers 4`
- Seal: `shasum -c artifacts/fable-agent138h-20260922/SEAL.sha256.txt`
