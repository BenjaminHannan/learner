# RESULTS — Exp 137c: hypotheticals saved as facts (Muse, 2026-09-22)

Result first: the one-change mixin ends the WRONG-WRITE class —
all 30 hypothetical sessions reply the exact pretend sentence with 0
writes, and later questions answer only from real saved facts.
Every sealed regression matches its written prediction: bench 800
items 0 moves, all marks123 suites per-case identical, sessions/rt143/
cases150/f1/139b 0 moves, rt136 C089 WRONG-WRITE→OK as the single
predicted verdict move. No new wrong anywhere.

Step 1 (asked): loop137b strips "Suppose" at
`scripts/fable_loop137b_agent.py:125`
(`rest = D137B.strip_first_token(...)` in `_upgrade137b`, lines
109–131; "?" strip lines 163–178).

## Marks (every seed/case reported; deterministic, no seeds)

| mark | bar | got | verdict |
|---|---|---|---|
| T1 probe (58 cases) | 58/58 OK | H-pure 22/22 (all 11 markers × plain+filler, 6 relations: exact reply, 0 writes, question avoids pretend value); H-conflict 8/8 (real value answered); N 12/12 + O 16/16 identical to 137b | PASS |
| T2 wrong writes | 0 | 0 writes on all 30 hypo turns | PASS |
| G1 bench (800) | 0 new wrong, moves predicted (none) | new 194/4, old 198/0, edit200 150/50/0, bench132 196/2; 0 verdict + 0 reply moves | PASS |
| G2 marks123 | per-case = marks137b except predicted (none) | p2 64/64, p4 30/30, q1 F5+M5, bench 400/400 rows, q4 leaks [], soak 2000/3/0-0-0, sleep SKIP (reason names new file, verdict identical), rt110 identical incl S1 ok→bug + F5/M5 bug→ok lists, p3 l1–l4/l6/L5-Z2 PASS, L5-Z1 58/60 (as 137b), rt81 60/0/14 (inherited FAIL label) | PASS (p3/rt81 FAILs inherited identical) |
| G3 junk/sessions | 0 new WRONG, moves predicted | rt136 C089 WRONG-WRITE→OK (0 writes, pretend reply), C122 identical (stores, WRONG-WRITE), C090/C091 verdict OK with reply moved to pretend sentence (predicted); 143 106/7/11 0 moves; sessions 129 OK/2 WRONG both arms 0 moves; 150 57/57, f1 45/46+1, 139b 101/101, 0 moves | PASS |
| G4 time | each run < 1500 s | probe 4.2, bench 86.9, junk 8.1, sessions 9.1, rt143 11.6, marks123 272.5 | PASS |

Notes. (1) p3 L6 `replied_before_kill` is timing metadata, not a
verdict: sealed base 21/24 → registered 5/18 → open re-run 8/6/7 on
the same agent, while correct=200/200, wrong=0, dupes=0, chain_ok hold
on all 3 seeds every run — the known mailbox race, both runs
reported, no verdict flake. (2) Pre-seal dev checks (detector unit
vectors + live twin spot-checks in temp dirs) are not marks; all marks
above are post-seal registered runs. (3) No code edit after the seal:
`shasum -c SEAL.sha256.txt` passes.

## Deviations

None. All six ledger predictions held as written.

## What it means

"Suppose/Supposing/Imagine/Pretend (that)/Let's–Lets say/
Hypothetically/In theory/What if/Say that" openers — with ok/so/and
fillers, any case — never write and always say the exact pretend
sentence; follow-up questions answer only real saved facts. "Say
Tom's …" still teaches, bare-"If …" still declines, "Btw./So/Hi."
phone teaches and marker-possessives ("What If's boss …") stay
byte-identical to loop137b.

## What it does not mean

Not counterfactual reasoning (pretend content is refused, never
modelled); titles in 137 position still strip (137b's "Hey Jude" edge
inherited); "Okay" is not a filler and lone "say"/"if" are not
markers, by sealed design.

Seal `SEAL.sha256.txt`, ledger P137c.1–6 pre-run. Mac CPU, offline,
OMP/MKL=1. Reproduce: `… python -B scripts/fable_fix137c_probe.py`;
`… python -B scripts/fable_fix137c_bench.py`;
`… python -B scripts/fable_fix137c_junk.py`;
`… python -B scripts/fable_fix137c_redteam143.py`;
`… python -B scripts/fable_fix137c_sessions.py`;
`… python -B scripts/fable_marks123_all.py --agent
scripts/fable_loop137c_agent.py --config
artifacts/fable-hypo137c-20260922/loop137c-config.json --out
artifacts/fable-hypo137c-20260922/marks137c --workers 4`.
Questions for Ben: none.
