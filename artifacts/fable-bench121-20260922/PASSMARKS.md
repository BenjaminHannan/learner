# PASSMARKS — Experiment 121: teach-side phrasing coverage (2026-09-22)

Registered single-change follow-up to exps 111/113 (teach rejects out of scope
there: 22 rejects in 12 old-fresh items — 18x "I didn't understand…" on
"works in the field of" / "is employed by" / "X's child is Y", 4x
one-fact-at-a-time "and"-guard hits on names containing "and" such as
"United Kingdom of Great Britain and Ireland").

THE ONE CHANGE: teach-pattern coverage only, tuned ONLY on the 22 known
rejects and the old fresh split. `scripts/fable_loop121_agent.py` (new,
prefix-owned; wraps `scripts/fable_loop113b_agent.py`, which exists) adds, on
non-"?" turns only: teach patterns for the three rejected relation phrasings
(same regexes/keys as exp-92's EXTRA_STATEMENT_PATTERNS: employer, occupation,
child — anything bench73 already parses still goes down the exact old path),
and narrows the exp-91 word-count screen so "and" inside a single capitalised
name span (Title-Case run, lowercase glue only "of"/"and") passes, while every
other packed-fact screen (?, ;, possessive-is, and-possessive, second copula)
still refuses. Question side byte-identical to loop113b. No existing file is
edited.

HELD-OUT SPLIT (built STEP 1, blind): `data/open/bench121/fable_edit121_4hop.jsonl`
(200 items, seed 121, zero case_id overlap with bench103-fresh and bench65-200,
sealed `data/open/bench121/SEAL.sha256.txt` BEFORE these marks were written;
its sentences are never printed or read — only its item count (200) and its
structured-relation histogram were recorded in its build manifest).

Registered runs (Mac CPU, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch
--with numpy python -B ...`):
  scripts/fable_bench121_run.py --run   (loop121 on the NEW blind split +
                                         the OLD fresh split, scorer v2 from
                                         exp 113, unchanged)
  scripts/fable_loop121_marks.py --mark all  (T4 packed-fact probes + loop102
                                         marks P2/P3/P4 vs the loop121 agent)

SCORER v2 (unchanged from exp 113): answer value = text after the final
" is " / " are ", trailing period stripped; exact normalised match vs
gold+aliases = correct; abstain = the loop's own decline/clarify forms on WORD
boundaries; else wrong. Teach ACCEPTED = starts with "Saved:" or the
duplicate-ack "I already have that.".

| Mark | Pass condition |
|---|---|
| T1 new blind split teach coverage | teach_reject_items ≤ 5 of 200 |
| T2 new blind split correctness | confident wrong ≤ 5 of 200 |
| T3 old fresh split rejects | n_teach_reject == 0 (was 22 in 12 items) |
| T4 red-team packed facts still refused | R110 L1 + L2 + L4 re-run: each refuses (split-clarify) with 0 new fact writes on every turn; brief literal probe "Mira's city is Oslo and Tom's pet is a cat" likewise refused with 0 writes |
| T5 loop102 marks P2/P3/P4 unchanged | P2: 0 OK->BUG vs sealed run-2 AND 0 still-BUG; P3: L1/L2/L3/L4/L5z1/L5z2/L6 all pass; P4: pass with 0 false refusals (identical to sealed loop102 outcomes) |

A registered FAIL is recorded as FAIL, never re-run into a pass.
