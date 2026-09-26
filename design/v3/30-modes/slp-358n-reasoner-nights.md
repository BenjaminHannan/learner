# slp-358n: sleep for the small reasoner (sleep research thread, 2026-09-26)

Ben (23:57 UTC 09-25): "you're the sleep thread". Split agreed with Fix sleep (proposed 23:59): Fix sleep keeps the
1B's nights (dl-1 follow-ups, bored mode + nights, keep rule / tripwire, slp-363); this thread runs nights for the
small reasoner of the 358 line.

## Why this test first
Today's evidence for nights: blurt-3/3r (1B practising its own checked lucky hits gets luckier on fresh puzzles),
blurt-5s (solver answers teach as well as own hits; repeating known answers collapses variety), dl-1 (copy nights
beat reward nights on the 1B and did not harm 300 general questions; a placebo night moved that score by up to 28).
The research pass (reviews/sleep-nights-research-2026-09-25/REPORT.md) says: small steps, mix old practice every
night, a broad tripwire instead of a veto. None of this has been tried on the reasoner that sleep is meant to train.

## Design (details in the script docstring; marks in artifacts/claude-slp358n-20260926/PASSMARKS.md)
Day: the reasoner tries 600 fresh puzzles of sizes it never practised (5-6 digit sums, 5x5 Latin grids); code
grades every try and supplies every checked answer. Night: 300 small steps, half the day's puzzles with answers,
half old practice. Controls: a rehearsal-only night of the same length (is it the day's material or just more
training?), a shuffled-answer placebo night, and no night. Morning: fixed fresh tests, a harm check on the
practised sizes, and a transfer check on bigger sizes.

## What comes next if it passes
The same night on the full-size 358a reasoner once 358a has a result; then nights that learn from the reasoner's
own right and wrong tries (reward) rather than copying, with the placebo and harm panel kept in every arm.
