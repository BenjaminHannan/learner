# Exp 163 RESULTS — lowercase names at the entity layer (Muse, resumed after handoff)

One change on loop150: name matching is case-insensitive at the entity layer
(`scripts/fable_fix163_lowercase.py`, thin `scripts/fable_loop163_agent.py`).
Lowercase questions resolve to the stored display form; all-lowercase new
teaches store capitalised; inner-capitals/mixed case keep typed form; ambiguous
spans are left for the base clarify path.

## Marks table (integer counts, every case reported, never averaged)

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| T1 sealed probe (53) | 26 lowerQ + 12 lowerTeach + 8 innerCaps + 7 noMerge exact | 26 + 12 + 8 + 0 (noMerge 4 WRONG-WRITE, 3 WRONG-REPLY) | FAIL |
| T2 sealed probe | >= 51/53 exact | 46/53 | FAIL |
| T1/T2 open probe (corrected noMerge cases) | report both | 53/53 | informational PASS |
| G1 bench 600 items (3 splits) | per-item verdict+reply identical to loop150, 0 new wrong | 0 moves, 0 new wrong (registered + open rerun) | PASS |
| G2 marks123 per-case vs marks150 | identical except predicted | identical except rt110 statuses-only flake + soak load flake, both clean on open rerun | PASS* |
| G3 sessions152 (180 turns) | only S2 [18,23] + S5 [4,10,12,13,14,25] move | exactly those 8, 0 new WRONG, 0 write moves (registered + open rerun) | PASS |
| G4 time | every run < 1500 s | slowest 196.1 s (marks123) | PASS |

*G2 detail: p2/p3/p4/q1/bench/rt81/q4 per-case identical (p2, q1, rt81 suite
FAILs inherited byte-identical from loop150); sleep SKIP verdict identical,
reason names the new agent file (predicted). rt110 registered: 1 move, T1
`statuses ['write'] vs []`, reply/fact_writes identical (known mailbox race);
open rerun pass, 0 moves. Soak registered: 2 wrong (turns 211/411,
SoakP011 write lost under kill-9 load); open rerun
turns=2000 kills=3 lost=0 wrong=0 doubled=0, PASS. Both reported.

## Diagnosis for the T1/T2 FAIL (one note, no silent re-runs)

The 7 sealed noMerge cases set up their collision with `person Tom` /
`person TOM` turns. Those turns store no entities on the base loop (verified:
`Who is Tom's boss?` then replies `I don't know anyone called Tom`), so no
case-only collision exists and the expected `I know more than one Tom...`
clarify can never fire. The premise was wrong, not the mixin: a true
Tom-vs-TOM collision is uncreatable through the normal teach path (resolve
merges case-insensitively), and the open corrected noMerge cases (single
stored entity + lowercase counterpart, cross-case non-merge, forget control)
pass 7/7 with 0 wrong writes. Sealed verdict stands as FAIL; the achievable
behaviour is verified in the open.

## Post-seal edits (reported; affected marks re-run in the open)

Sealed files untouched (`shasum -c` passes). After the seal two harness-only
edits: `scripts/fable_loop163_agent.py` (added `Loop163Daemon` +
`idle_seconds`, needed for daemon suites) and
`scripts/fable_fix163_probe.py` (added `--cases` flag for the open rerun).
The ONE CHANGE (`fable_fix163_lowercase.py`) is pre-seal and unedited.
Re-ran in the open with current code: sealed probe (same 46/53), open probe
(53/53), bench (0 moves), sessions (exact 8 predicted moves), rt110 (clean),
soak (clean).

## Deviations

None from the plan except the post-seal harness edits above and the corrected
open case file (`cases163-open.json`, sealed file kept).

## Reproduce (from worktree root)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix163_probe.py --out artifacts/fable-lowercase163-20260922/probe163-loop163.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix163_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop163_agent.py --config artifacts/fable-lowercase163-20260922/loop163-config.json --out artifacts/fable-lowercase163-20260922/marks163 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix163_marksdiff.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix163_session.py

## What it means

Lowercase typing now works for names: questions, teaches, and replies use the
stored display form, with zero behaviour change on 600 bench items, all
marks123 suites, and 172/180 phone-session turns.

## What it does not mean

It does not fix the 7 sealed collision cases (uncreatable premise, recorded
FAIL), nor the p2/q1/rt81 suite FAILs inherited from loop150.
