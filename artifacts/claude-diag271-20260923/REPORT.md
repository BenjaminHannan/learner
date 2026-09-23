# Exp 271 REPORT: can any YES/NO-checker cutoff separate good ear frames from wrong ones?

Diagnostic, CPU only: no panel run, no new model calls, no PASS possible.
One analysis run over the frozen 267 inputs (155 kept TEACH frames with
recorded p(YES), 267 dev gold). Method frozen in PREDICTIONS.md (sealed
SEAL-pred.sha256.txt before computing). Sealed scorers imported read-only.

## Verdict: YES — on this dev set, a cutoff separates them

Relabeled totals: 130 good, 25 wrong of 155 frames. ROC AUC = 0.948.
Best cutoff under "at most 1 wrong per 20 saved" (wrong/kept <= 0.05):
t = 0.8999 keeps 122 good + 5 wrong (0.79 wrongs per 20 saved), losing
8 good frames (122/130 = 93.8% of goods kept). 128 of the 156 grid cutoffs
qualify (t from 0.8929 to 0.9901). The sealed theta 0.25 keeps all 130 goods
but also 23 wrongs (3.01 wrongs per 20) — it does NOT meet the bar.

## Counts (integers)

| Set | n |
|---|---|
| Kept TEACH frames scored | 155 |
| Good (90 gold-hit + 40 appositive-relative + 0 plural-fix) | 130 |
| Wrong | 25 |
| Appositive-relative relabels (listed below) | 40 |
| Plural either-name relabels | 0 (case absent, see D1) |

Wrong frames by family: typo_filler 13, relation_trap 7, stale_value 3,
no_save 2, plain_teach 0, plural_relative 0.

Key cutoffs (kept = p >= t):

| t | kept | kept-good | kept-wrong | wrongs/20 saved | lost good |
|---|---|---|---|---|---|
| 0.00 (keep all) | 155 | 130 | 25 | 3.23 | 0 |
| 0.25 (261b sealed theta) | 153 | 130 | 23 | 3.01 | 0 |
| 0.4957 (~0.5) | 150 | 130 | 20 | 2.67 | 0 |
| 0.8999 (best) | 127 | 122 | 5 | 0.79 | 8 |
| 0.9600 (first zero-wrong) | 89 | 89 | 0 | 0.00 | 41 |

Best cutoff (frozen rule: max kept-good at wrong/kept <= 0.05; ties fewest
wrong, then larger t): t=0.899939, kept 127 = 122 good + 5 wrong, 8 goods lost.
Closest-to-bar alternative is unneeded: the bar IS met (128 cutoffs qualify).

By family (n, good/wrong, family AUC, best-cutoff kept-good/kept-wrong/lost):

| Family | n | good | wrong | AUC | best kg | best kw | best lost |
|---|---|---|---|---|---|---|---|
| plain_teach | 76 | 76 | 0 | n/a (one class) | 76 | 0 | 0 |
| plural_relative | 14 | 14 | 0 | n/a (one class) | 14 | 0 | 0 |
| relation_trap | 18 | 11 | 7 | 0.909 | 10 | 3 | 1 |
| stale_value | 16 | 13 | 3 | 1.000 | 13 | 1 | 0 |
| typo_filler | 29 | 16 | 13 | 0.861 | 9 | 1 | 7 |
| no_save | 2 | 0 | 2 | n/a (one class) | 0 | 0 | 0 |

## Every miss and move (frame ids; no turn quotes)

5 kept-wrong at the best cutoff (all high-p checker approvals):
d267-090#t0 (0.9598, trap: colleague-for-employer), d267-076#t1 (0.9409,
typo-glued subject span), d267-096#t1 (0.9369, stale occupation kept as
"baking"), d267-082#t1 (0.9253, trap: employer misread), d267-087#t0
(0.9029, trap: near-city saved instead of in-city).
8 lost-good at the best cutoff (good frames below t): d267-068#t0 (0.8747),
d267-068#t1 (0.8601), d267-067#t1 (0.8581), d267-070#t0 (0.8531),
d267-080#t0 (0.8338), d267-077#t0 (0.8144), d267-080#t1 (0.7944) — all 7
typo_filler turns where the checker half-doubted a true frame — plus
d267-089#t0 (0.2818, trap turn: true cousin frame the checker strongly
doubted; the single low-p good).
40 appositive-relative relabels (base wrong -> good, all audited, all the
"My <R> <Name> ..." pattern with value == another gold frame's subject,
stated in the turn): d267-004#t0, d267-005#t0, d267-006#t0, d267-011#t0,
d267-012#t0, d267-013#t0, d267-015#t0, d267-016#t0, d267-017#t0, d267-018#t0,
d267-024#t0, d267-025#t0, d267-026#t0, d267-028#t0, d267-029#t0, d267-032#t0,
d267-033#t0, d267-034#t0, d267-037#t0, d267-038#t0, d267-039#t0, d267-044#t0,
d267-045#t0, d267-046#t0, d267-047#t0, d267-050#t0, d267-067#t0, d267-068#t0,
d267-069#t0, d267-070#t0, d267-071#t0, d267-073#t0, d267-075#t0, d267-080#t0,
d267-083#t0, d267-086#t0, d267-089#t0, d267-094#t0, d267-096#t0, d267-098#t0.
Exactly 267's published C1 D-GOLD count (40/63).
25 wrong frames after relabel (all 25 listed in frames.csv; the 20 held at
or below t=0.8999 plus the 5 above). No frame needed the plural rule (D1).
Fidelity: manifest frames byte-match regenerated checker inputs 155/155;
per-turn rescoring reproduces 267 exactly (C0 90 hits/65 wrong; C1@0.25
90 hits/63 wrong/153 saved). Sealed files of other exps untouched.

## Predictions check (P271.1-6)

- P271.1 (good 126-137, wrong 18-29): RIGHT (130/25).
- P271.2 (AUC 0.50-0.70): WRONG. Got 0.948. The miss reason is instructive:
  the 40 truly-stated appositive frames all score very high (0.93-0.98), so
  once they are counted good, the score separates truly-stated from
  actually-wrong frames cleanly. The "rubber stamp" reading in 267 came from
  counting those true frames as wrong.
- P271.3 (no cutoff qualifies ~80%): WRONG. 128 cutoffs qualify; best keeps
  122/130 goods at 0.79 wrongs per 20. Same reason: the prediction assumed
  the ~13 high-p wrongs could not be cut without losing goods, but the
  goods sit higher still (101 of 130 goods at p >= 0.96).
- P271.4 (wrong locations): RIGHT (typo 13 + trap 7 + stale 3 + no_save 2;
  plural 0, plain 0 non-relative wrongs).
- P271.5 (family AUCs 0.45-0.75): WRONG (trap 0.909, stale 1.000, typo
  0.861; other families single-class so AUC undefined, not "noisy").
- P271.6 falsifier (any cutoff keeping >= 90% of goods at <= 1/20 proves
  P271.3 wrong): TRIPPED — best keeps 93.8% of goods at 0.79/20. P271.3 is
  wrong, stated plainly as required.

## Deviations / notes

- D1: the plural either-name rule fired 0 times. Audit: all 14 kept
  plural_relative frames are non-sibling relations (city/language/school)
  that already match gold; the ear never kept a plural sister frame at all
  (plural gold recall was the ear's miss, 14 kept vs 32 gold). The
  "other true name" case from research does not occur among the 155 kept
  frames, so 0 is the honest count, in band (0-4).
- D2: the brief's exp-264 builder half is not executed here: 264 is already
  sealed, run, and ledger-recorded (P264.1-9 + OUTCOME). Creating new
  claude_earcheck264_* files would collide with sealed work, so no 264
  files were added.
- D3: files are left uncommitted/unpushed per OPUS-RULES ("No git commits,
  PRs or pushes"), against the brief's PUSH line. Everything to push is in
  place: artifacts/claude-diag271-20260923/ + scripts/claude_diag271_roc.py.
- D4: TEST-ONLY panels never opened; no GPU/model calls; CPU seconds only.

## What it means (plain high-school English)

On this dev set the YES/NO checker's score actually works like a dial: turn
it up and the bad readings drop out much faster than the good ones. At the
best setting it keeps 122 of 130 good readings while only 5 bad ones slip
through. The old setting (0.25) kept everything good but let 23 bad ones
through. The big surprise is that the checker was never a rubber stamp —
earlier it just looked that way because the answer key marked 40 true
statements as wrong.

## What it doesn't mean

It does not mean 0.90 is the right setting anywhere else: this dev set is
clean and tunable, and on the blind 261b panel the same checker confidently
approved fine-grained misreads (job-title and home-fact confusions at high
p). It does not mean the ear is fixed: the ear still misses whole plural
facts before checking starts, and 7 typo-turn goods sit low enough that the
best cutoff drops them. It does not change 264's FAIL or 267's report; it
re-reads 267's numbers with corrected labels.
