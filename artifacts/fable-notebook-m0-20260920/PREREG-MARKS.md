# M0 -- Notebook demo v0: marks, registered BEFORE the run

Written before `eval` was run; `eval` refuses to start unless this file exists.
Evaluation only. No training of anything. Three FROZEN grow-blind operator checkpoints
(seeds 0, 1, 2), each 79,316 parameters, opened read-only with their sha256 recorded.
The fixed external loop is `astra_canonical_operator.execute`, which reads the hop
sequence off the question; there is no learned dispatcher anywhere in this run.

## Design

* 64 scripted teaching sessions, RNG namespace `fable-notebook-m0-v1` (new: not any existing
  panel's). Each session is a fresh notebook directory on disk. The same 64
  notebooks are read by all three operator seeds, so seeds are paired.
* Each session teaches 64 facts ONE AT A TIME -- 16 people x (one friend link + three
  attributes) -- which is every fact this token vocabulary can hold. Teaching order is a
  seeded shuffle with one declared fix-up: one friend fact is moved to position 0 and one
  attribute of that friend's target to position 1, so that a two-hop question exists from
  notebook size 2 onwards.
* At notebook sizes 1, 2, 4, 8, 16, 32, 64 the current view at that size is the story. Up to
  8 one-hop and 8 two-hop questions per session per size, sampled from the
  questions the current view actually answers. Every gold answer is re-derived by
  `astra_canonical_operator.truth_paths` from the packed story before scoring.
* Two corrections per session are appended after the 64th fact: one attribute value and one
  friend link. Five questions per session are then asked: the corrected attribute (one hop),
  the corrected link (one hop), and the three two-hop questions that run through the
  corrected link.
* 16 one-hop probe questions per session about people neither correction touches are
  asked before and after the corrections.
* Kill-and-reload: for the first 8 sessions of each seed, a FRESH PROCESS opens the
  notebook directory from disk and answers the same probe questions.

## Marks (per operator seed, never averaged)

| # | mark | threshold |
|---|---|---|
| 1 | one-hop accuracy at every notebook size | >= 95% |
| 2 | two-hop accuracy at every notebook size where a two-hop question exists | >= 95% |
| 3 | after a correction, the new answer | >= 95% |
| 4 | after a correction, the old answer | <= 2% |
| 5 | untouched facts' answers unchanged by a correction | 100% identical |
| 6 | kill-and-reload: rows, predictions and answer logits byte-identical | 100% |

Declared in advance:

* At notebook size 1 no two-hop question is answerable, so mark 2 is reported as
  `n/a (n=0)` at size 1 and is not scored there.
* Marks 3 and 4 are scored over all five correction questions per session pooled, and are
  also reported per question kind.
* Every "new" and "old" answer is computed by walking the current view AFTER and BEFORE the
  corrections, so a correction that also changes a two-hop answer is scored against the
  value the store actually implies. Where the old and new answers coincide (the two-hop case
  can draw the same value token twice), "old" is not distinguishable from "new", so mark 4's
  denominator is the number of questions whose old answer differs from the new one; that
  denominator is reported.

## Descriptive only, no mark

* Untaught questions at a 16-row notebook, in two kinds (a person the notebook knows but
  with that relation never taught; a person the notebook has never been told about): what
  it answers and how confident it is. EXPECTED: confident wrong answers. This is recorded
  as the baseline failure, not as a result.
* Wipe test: an empty notebook, eight questions -- what it answers with nothing to read.

## Declared handling of the named risk

Notebooks of 1-15 rows were never trained on: the grow-blind curriculum's floor is
`blind_lines = 16` kept fact rows. Nothing is padded and no filler fact is invented. A
current-view row is packed as `[WORLD, entity, relation, object, NEWLINE]` -- the
generator's own fact-row shape with zero trailing filler tokens, the low end of its
`randint(0, 2)` filler draw -- and `premonition_memnn.pack` sizes the memory tensor from
the rows it is given, so a one-row notebook is presented as a one-row story. An EMPTY
notebook is presented as a single all-padding row, which `pack` marks ineligible.

## What a pass would and would not show

Would show: a learned reader can sit behind a persistent, correctable notebook, and its
chained answers are caused by the notebook. Would NOT show: any learning of language,
"I don't know", names beyond 16, more than 64 facts, or learned control. The loop, the
reader, the printer and the correction rule are all supplied code.
