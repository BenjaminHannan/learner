# PASSMARKS — Experiment 113c: partial/prefix composer frames treated like None (2026-09-22)

Registered single-change follow-up to exp 113b (diagnosis in design doc
113b and artifacts/fable-bench113b-20260922/RESULTS.md: B92 returns 1-hop
PREFIX frames, not None, on broken-chain / qualifier questions, so the
113b fallback never fires). THE ONE CHANGE: loop113c = loop113b + a
composer frame counts as usable only if it consumes every relation phrase
/ qualifier in the question (no leftover content words after the frame is
matched); a partial or prefix frame is treated exactly like None ->
delegate to the unchanged loop102 chain (as 113b does). Applied to both
the B92 N-hop branch and the B73 explicit-2-hop branch; compound-guard,
non-explicit clarify, hearsay screen, and teach path identical to
loop113b. The 3 remaining fresh teach-gap wrongs from exp 113b
(056/103/196) are OUT of scope (reported, not fixed).

Registered runs (Mac CPU, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with
torch --with numpy python -B ...`):
  scripts/fable_bench113c_run.py --run   (loop113b-before + loop113c-after,
                                          both splits, scorer v2 identical
                                          to exps 113/113b)
  scripts/fable_loop113c_marks.py --mark all  (M1: P2 + P3 L1-L6 + P4
                                               vs loop113c)

SCORER v2 (identical to exps 113/113b, registered here before any run):
extract the answer value from the loop's reply sentence (text after the
final " is " / " are ", stripped of the trailing period), exact
normalised match vs gold+aliases = correct; abstain = the loop's own
decline/clarify/"I don't know" forms matched on WORD boundaries; anything
else = wrong. Teach ACCEPTED = starts with "Saved:" or the duplicate-ack.

"Right behaviour" = correct on answer items + abstain on abstain items.

| Mark | Pass condition |
|---|---|
| M1 loop102 marks P2 + P3 (L1-L6) + P4 re-run against loop113c | outcome identical to loop102: P2 0 OK->BUG and 0 still-BUG (B7/C2/C5/D8 all OK); P3 L1-L6 all pass (L5-Z1 60/60, L6 200/200 per seed); P4 <= 2 false refusals and 0 non-pass |
| M2 loop113c Fable-Edit-200 | right behaviour 200/200 AND wrong 0 |
| M3 loop113c fresh-4hop (200) | correct >= 140 AND confident wrong <= 5 (exactly which items moved vs 113b reported by id with reasons) |
| M4 whole registered wave | < 25 min wall-clock Mac CPU (< 1500 s) |

A registered FAIL is recorded as FAIL, never re-run into a pass.
