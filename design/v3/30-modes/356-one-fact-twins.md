# 356: practice with one-fact twins (road map R6)

Sleep research thread, 2026-09-25 03:00 UTC. From sleep research round 2, idea #1 (with the skeptic's
fixes: no "reorder rows" twins, pairing is the new part, a held-out edit type, a same-mix control).

## Idea (plain words)
A lazy trick gives the same answer to two puzzles that look alike. If every puzzle comes with a twin that
differs by one needed fact (so the right answer changes), and both land side by side in the same practice
batch, the lazy trick gets one of each pair wrong and loses reward. The model is pushed to read the fact
that decides the answer. Evidence is mixed: counterfactual pairs cut shortcut use (Kaushik 1909.12434,
shown) but were no better than the same amount of plain data on NLI (Huang 2010.04762, shown). That is
why the control has the same puzzles, just not paired.

## The one change (scripts/claude_rsn356_run.py, scripts/claude_rsn356_twins.py)
Training only. After each practice puzzle that has a clean twin, the next puzzle is:
- paired arm: its own twin (one needed row deleted: a chain step -> "I don't know"; a counted member ->
  one fewer; the newest of a correction -> the older value). Re-solved by 296's independent solver.
- unpaired arm (control): the twin of a different, freshly made puzzle that is thrown away.
Both arms get the same mix (checked on 2,000 puzzles: 537 vs 546 twins, 422 vs 435 "I don't know"
answers; paired twins sit next to their original 537/537 times, unpaired 0). Everything else is 296's
plain arm. Base: 296, not 355, so the two tonight's runs don't depend on each other.

## Held-out test (scripts/claude_rsn356_pairs.py)
600 code-made pairs at seed 4242 using an edit type practice never uses ("change": an answer value
changes, yes/no flips, a compared number flips the winner, a counted member is added, correction stamps
swap). Counted: pairs where BOTH answers are right after the fact-check. Code-made pairs share the
generator's quirks, so the fresh blind panel296 is the main mark.
Deviation (as in 355): BensPC is Windows, so --workers 0.
