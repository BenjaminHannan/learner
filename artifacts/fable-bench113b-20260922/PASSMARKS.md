# PASSMARKS — Experiment 113b: loop113 + fallback to the exact loop102 chain (2026-09-22)

Registered single-change follow-up to exp 113 (diagnosis in design doc 113
and artifacts/fable-bench113-20260922/RESULTS.md). THE ONE CHANGE: loop113b
= loop113 + delegation to the exact loop102 chain (Loop102Ears.hear on the
same instance: same nb binding, same inner loop96 chain, same FakeStage
path) whenever BOTH composers return None on a "?" turn. Flat clarify is
kept ONLY for compound-guard hits and non-explicit 2-hop frames (the
truncation shape). Teach patterns identical to loop102/loop113. The 22
fresh-phrasing teach rejects and the 5 teach-gap fresh wrongs from exp 113
are OUT of scope (reported, not fixed).

Registered runs (Mac CPU, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with
torch --with numpy python -B ...`):
  scripts/fable_bench113b_run.py --run   (loop113-before + loop113b-after,
                                          both splits, scorer v2 identical
                                          to exp 113)
  scripts/fable_loop113b_marks.py --mark all  (M1: P2 + P3 L1-L6 + P4
                                               vs loop113b)

SCORER v2 (identical to exp 113, registered here before any run): extract
the answer value from the loop's reply sentence (text after the final
" is " / " are ", stripped of the trailing period), exact normalised match
vs gold+aliases = correct; abstain = the loop's own decline/clarify/"I
don't know" forms matched on WORD boundaries; anything else = wrong.
Teach ACCEPTED = starts with "Saved:" or the duplicate-ack, as in exp 113.

"Right behaviour" = correct on answer items + abstain on abstain items.

| Mark | Pass condition |
|---|---|
| M1 loop102 marks P2 + P3 (L1-L6) + P4 re-run against loop113b | outcome identical to loop102: P2 0 OK->BUG and 0 still-BUG; P3 L1-L6 all pass (L5-Z1 60/60, L6 200/200 per seed); P4 <= 2 false refusals and 0 non-pass |
| M2 loop113b Fable-Edit-200 | right behaviour 200/200 AND wrong 0 |
| M3 loop113b fresh-4hop (200) | correct >= 145 AND confident wrong <= 5 (the 5 teach-gap wrongs 056/103/196/125/200 reported by id, not fixed) |
| M4 whole registered wave | < 25 min wall-clock Mac CPU (< 1500 s) |

A registered FAIL is recorded as FAIL, never re-run into a pass.
