# PASSMARKS — Experiment 113e: gate inverse cues (2026-09-22)

Registered single-change follow-up to the exp 113d FAIL (design doc 113e,
artifact artifacts/fable-bench113d-20260922/, script
scripts/fable_loop113d_agent.py). 113d's fallback consumption gate stopped
every genuine prefix answer and turned wrongs into abstains (bench121 8
-> 1 wrong, fresh 3 -> 0, 0 new wrongs) but over-abstained: Fable-Edit
reversal 35/50 (15 reversed-relation frames such as author_of / written_by
whose surface words are not in REL_CUES92), two-hop 98/100, L5-Z1 52/60,
P4 29/30.

THE ONE CHANGE (question side only; teach path and everything else
identical to loop113d): the gate's cue set for R = every surface phrase
the existing code tables -- the relation maps the parser itself uses to
frame facts: REL_CUES92, LE.RELATION_MAP, the closed maps, and the
inverse-relation table -- canonicalise to R OR to inverse(R). Built
mechanically from those tables (scripts/fable_loop113e_agent.py
build_cue_sets()): no hand-added words, no words taken from any benchmark
item; the added words per relation are printed into
artifacts/fable-bench113e-20260922/fable_bench113e_added_cues.json.
Subclass of loop113d (scripts/fable_loop113e_agent.py); 113d's runner
scripts reused by import with class swap (new files prefixed
fable_bench113e_); artifact artifacts/fable-bench113e-20260922/; doc
design/v3/30-modes/113e-gate-inverse-cues-muse.md.

Registered runs (Mac CPU only, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with
torch --with numpy python -B ...`):
  scripts/fable_bench113e_redteam124.py --run  (E1: 62 sealed redteam124
      cases, loop113c-before vs loop113e-after, check_case with the
      loop113b expectations exactly as the director did)
  scripts/fable_bench113e_run.py --run  (E2: loop113c + loop113e, both
      splits, scorer v2 identical to exps 113/113b/113c/113d)
  scripts/fable_bench113e_121.py --run  (E3-121: new bench121 split,
      data/open/bench121/, bench121 protocol with the daemon class swapped
      to loop113c-before / loop113e-after)
  scripts/fable_bench113e_run.py --run  (E3-fresh: same invocation as E2)
  scripts/fable_marks123_all.py --agent scripts/fable_loop113e_agent.py
      --config artifacts/fable-bench113e-20260922/loop113e-config.json
      --out artifacts/fable-bench113e-20260922/marks123
      --suite p2|p3|p4  (E4: exp-102 marks P2, P3 L1-L6, P4 vs loop113e)

SCORER v2 (identical to exps 113/113b/113c/113d, registered here before any
run): extract the answer value from the loop's reply sentence (text after
the final " is " / " are ", stripped of the trailing period), exact
normalised match vs gold+aliases = correct; abstain = the loop's own
decline/clarify/"I don't know" forms matched on WORD boundaries; anything
else = wrong. Teach ACCEPTED = starts with "Saved:" or the duplicate-ack.

"Right behaviour" = correct on answer items + abstain on abstain items.

| Mark | Pass condition |
|---|---|
| E1 redteam124 62 cases (loop113c vs loop113e) | the 113d fixes hold (B5, B3 fixed; Q2/U1/V4 no prefix answer) and no OK->BUG vs loop113c; 0 new wrong writes |
| E2 Fable-Edit (scorer v2) | 200/200 right behaviour, 0 wrong |
| E3 fresh 4-hop + bench121 (scorer v2) | old fresh split >= 145 correct and 0 wrong; bench121 >= 119 correct and <= 1 wrong; exact per-item movement vs loop113c reported |
| E4 exp-102 marks via fable_marks123_all.py | P2 64/64; P3 L1-L6 outcomes as loop113c (L5-Z1 60/60); P4 30/30 |
| E5 whole registered wave | < 25 min wall-clock Mac CPU (< 1500 s) |

A registered FAIL is recorded as FAIL, never re-run into a pass.
Fable-Edit/L5/P4 items were seen by 113d: this measures repair, not
generalisation (stated plainly in RESULTS.md).
