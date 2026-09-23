# PASSMARKS — Experiment 132: question-phrasing coverage (2026-09-22)

Registered single-change follow-up to exp 121 (evidence on the sealed 4-hop
split: loop121 answers 136, abstains 63, wrong 1 -- 62 of the 63 abstains are
the loop's own "I didn't understand that": natural MQuAKE-style questions
with relative clauses and inverted order, which the N-hop composers
(exp 113/113c) cannot parse into the full chain).

THE ONE CHANGE: a deterministic question REWRITER placed before the
composers (`scripts/fable_qrewrite132.py`, new, prefix-owned) that turns
relative-clause / inverted multi-hop questions into the canonical
nested-possessive form the composers already accept ("X's performer's
director's country of citizenship's continent?"), using the notebook's own
relation vocabulary (relation surface phrases already in the code tables; no
model downloads, plain software + tiny grammar). Resolution is
notebook-grounded (verbatim entities, compound subjects with typo-normalised
prefixes, single-outgoing triple hops with island-hopping via string
containment); every content word of the original must be consumed (entity
spans, relation cue phrases, or scaffolding); the canonical form is verified
with the unchanged composers (exact frame + no compound-subject hit); exactly
one verified candidate wins. If the rewrite is not certain (any leftover
content word, ambiguity, failed verification), the question passes through
unchanged -- never a guess. Wrapper `scripts/fable_loop132_agent.py` (new,
prefix-owned; subclasses loop121 -- artifacts/fable-bench113d-20260922/
holds only PASSMARKS.md at build time, no PASS, so loop121 stands): the exact
base path runs first and every base ASK is returned untouched (base correct
answers stay correct by construction); only a base CLARIFY consults the
rewriter, and the rewritten turn goes through the exact base path again. No
existing file is edited.

HELD-OUT SPLIT (built STEP 1, blind): `data/open/bench132/fable_edit132_4hop.jsonl`
(200 items, seed 132, zero case_id overlap with bench103-fresh, bench121 and
bench65 splits, sealed `data/open/bench132/SEAL.sha256.txt` BEFORE the
rewriter's final version was written; its sentences are never printed or
read -- only its item count (200) and its structured-relation histogram were
recorded in its build manifest). Split seal:
`eb97d7aaedb302573049c09f1a7d61b19d85625eb3249746385d61ca834de801`.

FROZEN MODULES (sha256 at freeze, before this seal):
`8068960fd2b06a6123f3341f5aa7667be2c265d8544603c08c4b8a269fa4df3f  scripts/fable_qrewrite132.py`
`008da798a02f8392e818fae73a0aaed37950c45070eb6a80774c521539e93723  scripts/fable_loop132_agent.py`

DEVIATION (harness, before any completed registered run): the first seal
listed wrapper hash `18f8e76f...`; that build crashed only in `--daemon`
subprocess mode (`AttributeError: idle_seconds`, P3 harness) while all
in-process paths were identical. One line added
(`self.idle_seconds = float(idle_seconds)` in `Loop132Daemon.__init__`,
mirroring `Loop121Daemon`), hash updated above, PASSMARKS re-sealed, and the
entire wave re-run from scratch; the earlier bench-only pass (Q1 59->1,
Q2 2, Q3 0 moves) is DISCARDED, not reported as a result. The rewriter module
(`fable_qrewrite132.py`) is byte-identical to the first freeze.

Registered runs (Mac CPU, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch
--with numpy python -B ...`):
  scripts/fable_bench132_run.py --run   (paired: Loop121Daemon base +
                                         Loop132Daemon rewrite, NEW blind
                                         split only, scorer v2 from exp 113,
                                         unchanged)
  scripts/fable_loop132_marks.py --mark all  (Q4: P2/P3/P4 via the unchanged
                                         marks123 suites with the daemon
                                         class swapped to loop132, plus the
                                         red-team-124 runner with the daemon
                                         class swapped to loop121-before /
                                         loop132-after, judged with the
                                         runner's check_case and the loop113b
                                         expectations exactly as exp-113d)

SCORER v2 (unchanged from exp 113): answer value = text after the final
" is " / " are ", trailing period stripped; exact normalised match vs
gold+aliases = correct; abstain = the loop's own decline/clarify forms on WORD
boundaries; else wrong. Misunderstood = reply matches "i didn't understand
that" (word boundaries). Teach ACCEPTED = starts with "Saved:" or the
duplicate-ack "I already have that.".

| Mark | Pass condition |
|---|---|
| Q1 new split phrasing coverage | "I didn't understand that" replies drop by >= 50 % vs the base loop run on the same split (both runs reported) |
| Q2 new split correctness | wrong <= 3 on the new split |
| Q3 no correct lost | the base loop's correct answers on the new split all stay correct (0 correct->wrong) |
| Q4 exp 102 marks P2/P3/P4 + red team 124 unchanged | identical outcomes vs the base loop (P2/P3/P4 via marks123 suites; RT124 0 OK->BUG, 0 new wrong writes, 0 prefix-after) |
| Q5 whole registered wave | < 25 min wall-clock Mac CPU (< 1500 s) |

A registered FAIL is recorded as FAIL, never re-run into a pass.
