# PASSMARKS — Experiment 113d: fallback partial-frame gate (2026-09-22)

Registered single-change follow-up to exp 113c (diagnosis in design doc
113d and the director's re-run: through loop113c the composer prefixes are
gone, but the loop102 fallback's Bench73Stage still answers 2-hop PREFIX
frames -- B5 "Duggan's spouse's country of citizenship is Spain", Q2 / U1
/ V4 "CM Punk's spouse's country of citizenship is Spain" -- to questions
naming more relations / qualifiers than consumed; red team 124 found 16
such loop102 cases). THE ONE CHANGE: loop113d = loop113c + 113c's
consume-every-relation-phrase/qualifier rule applied to the loop102
fallback path's question answering too (Bench73Stage and any other 2-hop
question path reached through the fallback): a fallback ask whose frame
leaves relation words/qualifiers unconsumed becomes the honest abstain
(L113.CHAIN_MISS_TEXT) instead of the prefix answer. Teach path and all
non-ask fallback actions identical to loop113c.

Registered runs (Mac CPU, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with
torch --with numpy python -B ...`):
  scripts/fable_bench113d_redteam124.py --run  (D1: 62 sealed redteam124
      cases through loop113c-before and loop113d-after, runner's check_case
      with the loop113b expectations exactly as the director did)
  scripts/fable_loop113d_marks.py --mark all  (D2: P2 + P3 L1-L6 + P4
      vs loop113d)
  scripts/fable_bench113d_run.py --run  (D3-bench: loop113c-before +
      loop113d-after, both splits, scorer v2 identical to exps 113/113b/113c)
  scripts/fable_bench113d_121.py --run  (D3-121: new bench121 split,
      data/open/bench121/, via the bench121 protocol with the daemon class
      swapped to loop113c-before / loop113d-after)

SCORER v2 (identical to exps 113/113b/113c, registered here before any run):
extract the answer value from the loop's reply sentence (text after the
final " is " / " are ", stripped of the trailing period), exact
normalised match vs gold+aliases = correct; abstain = the loop's own
decline/clarify/"I don't know" forms matched on WORD boundaries; anything
else = wrong. Teach ACCEPTED = starts with "Saved:" or the duplicate-ack.

"Right behaviour" = correct on answer items + abstain on abstain items.

| Mark | Pass condition |
|---|---|
| D1 redteam124 62 cases through loop113d | 0 prefix answers (B5, Q2, U1, V4 and every other case whose final reply answers fewer relations than asked -> abstain), 0 new wrong writes, every case that was OK on loop113c stays OK (full before/after list reported) |
| D2 exp-102 marks P2/P3/P4 vs loop113d | outcome identical to loop113c: P2 64/64 OK, L6 200/200 x 3 seeds, L5-Z1 60/60, P4 30/30 |
| D3 bench (scorer v2) | Fable-Edit-200 200/200, 0 wrong; old fresh 4-hop correct >= 145, wrong <= 3; new bench121 split wrong <= 8 and correct >= 115 (loop113c there: 119 / 73 / 8 -- exact movement reported) |
| D4 whole registered wave | < 25 min wall-clock Mac CPU (< 1500 s) |

A registered FAIL is recorded as FAIL, never re-run into a pass.
