# ADDENDUM gr-2 #1: the square search is a disclosed hand-written stand-in (2026-09-26 18:57 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. This addendum was written before the blind panel
exists and before any gr-2 run. PASSMARKS-gr2.md is not edited, and the marks, arms and decision rule are unchanged.

## Why
The Thread manager asked (18:56 UTC) whether "code picks the most probable tagging that forms a square" is a
hand-written rule placed after the learned head. Ben's 16:04 Redirect allows a stand-in only as disclosed scaffolding
with a learned part owed.

## Disclosure
claude_gr2.joint_decode is hand-written code. Its only knowledge is the definition of the answer's shape: s rows of s
cells, 3 <= s <= 9, values 1..s or blank. gr-1's code used the same definition to accept or reject a reading. What
reads the message (which tokens are cells, where rows start) stays the learned head. The search adds no wording, no
layout pattern and no threshold. It is still a hand-written step, and it is labelled here as disclosed scaffolding.
If gr-2 passes and joins 358b3's path, it joins under that label.

## The learned part owed
A reader that learns the square's consistency itself. The plan is that the head also learns each cell's row and
column number, so that "every row has s cells" comes from learned outputs rather than a search. A first-order CRF
(learned transition scores between neighbouring tags) was considered and set aside. It can learn "I follows B" but
cannot express "every row has the same number of cells", because that is a count across the whole grid. It would
therefore not do what the search does. The learned part will be its own sealed test, one change against gr-2.

## Why run gr-2 first
It tests, at $0 on this CPU, whether per-token slips are what failed gr-1. The P arm (gr-1's per-token reading from
the same forward pass) is reported next to L on a fresh blind panel. Every square that L reads and P misses is a
reading lost to a slip, not a head that failed to see the grid.
