# RESULTS — Exp 138e: officeholder rewrite-chain guard (Muse, 2026-09-22)

Result first: PASS on all six marks. The rule vetoes exactly the 3
confident-wrong officeholder rewrites (025/073/149 → abstain) and keeps all
140 measured correct fixes, with zero moves on every regression suite.

Diagnosis (STEP 1, dev only, no seal): 146 rewritten asks whose winning
chain touches `officeholder` — 140 correct, 3 wrong (025/073/149), 2
abstain off the rewrite path, 1 redteam143-F5 fix. Every wrong shares one
shape: a first-hop edit teach with a long "A and B" value is refused
("split that"), leaving a complete stale branch plus a dangling edit branch
with a different holder; the rewriter walks the reachable stale branch and
verifies it. No answer-time-only feature separates them (sibling divergence
alone vetoes dozens of corrects). The separator is teach history plus
contradiction: all 3 wrongs have a refused first-hop teach; 139/140
corrects have zero refusals; the 1 correct with a refusal (bench132-105)
has a dangling sibling with the SAME holder.

The ONE sealed rule: skip the officeholder rewrite (base 113c stands) iff
the rewrite fires through officeholder AND a refused teach/correct
mentioning the ask's entities is recorded AND a same-office sibling
compound dangles (target unreachable from the seeds) with a different
holder. Mixin subclass of loop138b; no loop138b file edited.

## Marks (every seed/case reported; registered runs post-seal)

| mark | bar | got | verdict |
|---|---|---|---|
| T1 held-out (32 fresh: R01–R16 rewrite-right, W01–W16 would-be-wrong) | 0 wrong, >= 13/16 right kept | 0 wrong, R 16/16 correct (stage loop138b-rewrite), W 16/16 abstain (stage loop138e-veto) | PASS |
| T2 025/073/149 | no longer wrong | wrong→abstain ×3 (base abstain text); 174 still wrong | PASS |
| G1 bench 4×200 vs sealed 138b rows | 0 new wrong, 3 predicted moves | new 194/5/1, old 198/2/0, edit200 150/50/0, bench132 196/2/2; moves exactly 025/073/149; all else verdict+reply+stage identical | PASS |
| G2 marks123 vs marks138b | per-case verdict-identical | 0 verdict moves all suites; statuses identical (p3 FAIL l5z1-only, rt81 FAIL inherited, sleep SKIP); predicted cosmetics only (sleep reason names new file, rt110 M1 log statuses, l6 kill-timing counters) | PASS |
| G3 junk/143/sessions vs frozen 138b | 0 moves, 0 new WRONG/writes | redteam136 135/7/3, cases150 57/57, f1 45+t14, cases139b 101/101, 143 106/7/11 (H5 WRONG + F5 OK kept), sessions 0 moves 0 new writes | PASS |
| G4 time | each run < 25 min | T1 1.9 s, G1 66 s, G3a 7.9 s, G3b 14.4 s, G2 302 s | PASS |

Seal (`shasum -c …/SEAL.sha256.txt` all OK; ledger P138e.1–6 pre-run, outcomes
appended). Mac CPU, offline, OMP/MKL=1. `shasum -c
artifacts/fable-officechain138e-20260922/SEAL.sha256.txt`. T1: `…
python -B scripts/fable_fix138e_heldrun.py`. G1: `… python -B
scripts/fable_fix138e_bench.py`. G2: `… python -B scripts/fable_marks123_all.py
--agent scripts/fable_loop138e_agent.py --config
artifacts/fable-officechain138e-20260922/loop138e-config.json --out
artifacts/fable-officechain138e-20260922/marks138e --workers 4`. G3: `…
python -B scripts/fable_fix138e_junk.py`, `… python -B
scripts/fable_fix138e_redteam.py`.

## Deviations (pre-seal only; no post-seal edits)

- Held-out construction iterated on the GENERATOR with the frozen base
  only (never 138e): fixed "X of A and B" edit names (the rewriter splits
  compounds at the last " of ", so " of " became " for "), bench-exact
  sport/broadcaster teach phrasings, and one hearsay-tripping name
  ("Threads"). The sealed 32 were written before any 138e run on them.
- One open 138e trial per suite ran before sealing to inventory moves;
  every open result matched its registered run exactly.

## What it means

The confident-wrong officeholder answers came from answering over a
notebook the loop itself knew was incomplete — it had just refused the
linking fact — while a contradictory branch dangled. Gating that one hop
on the refusal-plus-contradiction signal removes the 3 wrongs and costs
nothing measurable anywhere else.

## What it does not mean

Not a general rewriter fix: H5's wrong-start-entity answer, fully-landed
two-branch gambles, and any divergence without a recorded refusal are
untouched by design — the rule abstains only where the loop has witnessed
its own missing fact.

Questions for Ben: none.
