# 138f — stack clean: loop138d minus the pieces that add wrong writes (design)

One new file (`scripts/fable_loop138f_agent.py`) subclasses the frozen
loop138d shape. Loop138d's ears/loop/turn are REPLACED by slimmer
versions defined here; every rule body is imported read-only and no
existing file is edited. Drivers are `scripts/fable_fix138f_*.py`.

## Step 1 attribution (diagnosis before the seal)

Each of the 7 M4 cases was run on loop138d with each of the 11 pieces
switched off one at a time (omit-one-mixin subclasses in
`scripts/fable_fix138f_ablate.py`; evidence
`artifacts/fable-agent138f-20260922/attribution-138f.json`):

| case | single piece that fixes it | fix |
|---|---|---|
| redteam136 C124 "The mother of Ann is Sue." | none | 155+138c |
| redteam136 C127 "The father of Bob is Ted." | none | 155+138c |
| redteam136 C129 "The boss of Tom is Ann." | none | 155+138c |
| redteam136 C142 "THE CAPITAL OF PERU IS LIMA." | none | 155+138c |
| cases139b C10 "Lena's boss is Tom and Ann's boss." | 155 | 155 |
| cases139b C21 "Mira is the founder of Initech and Globex." | 155 | 155 |
| redteam143 M3 "Is Aldport the capital of Norland?" | none | 154+138c |

No case is fixed by any other single piece, and no two-piece set smaller
than {155, 154, 138c} fixes all seven (teaches need 155, M3 needs 154,
and five cases need 138c for the 138b reply text). So the removal set is
exactly these three — the smallest set that fixes everything.

## What each removed piece did, and what its removal costs

- 155 inverted frames (x135): converted leftover clarifies in
  "V is X's R / V is the R of X / The R of X is V" shapes into teaches,
  including the shouted variant (C142) and compound inversions it
  mis-parsed into junk (C10/C21 "Tom and Ann's boss is Lena's boss").
  Cost: inverted-shape teaches clarify as on loop138b. Per-piece fix
  queued: restrict the reverser to single-fact shapes the base already
  parses (refuse compounds and all-caps shouts).
- 154 yes/no: answered Is-questions on didn't-understand via wh-run,
  saying "Yes — Norland's capital is Aldport" where abstain is sealed
  (M3). Cost: yes/no questions fall back to the base clarify; marks123
  turns 49/58 and rt81 D_q_vs_s-04 revert to base (predicted). Queued
  fix: answer yes/no only on single-mention grounded frames.
- 138c serving rule: served grounded Self99 answers on notebook-miss and
  rendered leftover clarifies through the L134 base path ("I didn't
  understand that…") where loop138b renders the long abstain sentence.
  It adds no wrong write/answer itself, but byte-identity on five cases
  needs it off. Cost: notebook-missed turns serve the base reply
  verbatim (loop138 rule); rt110/S1-style grounded serves revert;
  13+4+10 reply-only reverts across marks123 (all enumerated in
  PASSMARKS.md, verdicts unchanged). Queued fix: keep the grounded-serve
  rule but render leftover clarifies through the loop138 mouth path.

## Kept pieces (8) and composition

142 index, 146d doubt, 153 reverse, 156b small talk, 157 fillers,
158 question forms, 159 hop fallback, 150b clause guard. Ears outer→inner:
Qform158 > Filler157 > Smalltalk156b > Doubt146b > Subject150B >
Reverse153 > Loop138bEars (155 gone). Loop _act unchanged (Doubt146b >
Subject150B > 138b guards); no YesNo154Mixin. turn() is loop138 verbatim.
Reasoner138d, IndexedLoopNotebook, 142 patches, doubt store and the
sleep145 retrofit are reused unchanged.

## Known edges

- 156b probe N02 ("thanks, Bob is Tom's boss") encoded the 155 polluted
  save; on 138f the bar is base-identical no-write (documented in the
  M1 driver, not a code change to any sealed file).
- l6 `replied_before_kill` is timing-volatile; only pass/correct/wrong
  fields are predicted.
- Speed/soak-latency (138d M6) are out of scope per the brief; no 15k
  test is run.
