# PASSMARKS — Experiment 113: loop102 + N-hop questions, scorer v2 (2026-09-22)

Registered single-change follow-up to exp 111 (end-to-end bench FAIL).
THE ONE CHANGE: loop113 = loop102 + exp 103's N-hop question composer
(B92.compose_n_hop) wired into the question side of the ears chain, with
the safety rule "never answer a shorter question than was asked" (question
router + compound-subject guard; unparseable questions clarify/decline).
Teach patterns identical to loop102. The 22 fresh-phrasing teach rejects
from exp 111 are OUT of scope (reported, not fixed).

Registered runs (Mac CPU, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with
torch --with numpy python -B ...`):
  scripts/fable_bench113_run.py --run   (loop102-before + loop113-after,
                                         both splits, scorer v2)
  scripts/fable_loop113_marks.py --mark all  (N4: P2 + P3 vs loop113)

SCORER v2 (in scripts/fable_bench113_run.py, registered here before any
run): extract the answer value from the loop's reply sentence (text after
the final " is " / " are ", stripped of the trailing period), exact
normalised match vs gold+aliases = correct; abstain = the loop's own
decline/clarify/"I don't know" forms matched on WORD boundaries;
anything else = wrong. Teach ACCEPTED = starts with "Saved:" or the
duplicate-ack, as in exp 111.

"Right behaviour" = correct on answer items + abstain on abstain items.

| Mark | Pass condition |
|---|---|
| N1 loop113 fresh-4hop (200) | confident wrong ≤ 2 of 200 |
| N2 loop113 Fable-Edit-200 | right behaviour ≥ 195 of 200 AND wrong ≤ 2 |
| N3 loop113 abstain items (50) | 50/50 abstain (wrong == 0) |
| N4 loop102 marks P2 + P3 vs loop113 | outcome unchanged: P2 0 OK->BUG and 0 still-BUG; P3 all L-marks pass |
| N5 whole registered wave | < 25 min wall-clock Mac CPU (< 1500 s) |

A registered FAIL is recorded as FAIL, never re-run into a pass.
