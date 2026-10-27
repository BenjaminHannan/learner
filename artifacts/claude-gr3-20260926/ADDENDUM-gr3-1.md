# ADDENDUM gr-3 #1: answers to the Thread manager's review (2026-09-26 19:34 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. This addendum was written before the glance was
trained, and so before any gr-3 run or verdict. PASSMARKS-gr3.md is not edited. The marks, bars, arms and decision rule
are unchanged; this addendum narrows one claim and discloses three things.

1. Size 9 has no training rows. gr-1's practice squares have sizes 3-8 only, and the 1B's table messages have no
   square of size 9. The glance's class 9 (claude_gr3.py CLASSES) therefore has no examples, and it can in effect say
   only none or 3-8. The claim "a size from 3 to 9" in PASSMARKS-gr3 is narrowed to 3-8. The blind panel's squares are
   sizes 4-7, so scoring is unaffected. A real 9 x 9 square would be read at a wrong size or as none. That is a known
   limit, not tested here.
2. Class balance. The glance trains on about 500 no-square practice messages plus the kept 1B table messages, against
   360 squares, with sizes 3 and 8 at about 37 each. The layer and L2 are picked by total CV accuracy, which the none
   class dominates. The CV counts of none read as a square and a square read as none are printed but do not enter the
   pick. The pick stays as sealed, and the fit log reports both counts for every choice.
3. Arm C (the code stand-in) is no comparison on R1 and R2. The truth of each lookalike is what read_latin reads, and
   the panel maker checks that read_latin reads every inserted square exactly (0 mismatches). C therefore scores
   R1 = 100 and R2 = 0 by construction. C is a real comparison only on the new formats (U1, U2), where it read 6 of 60
   at construction. The VERIFY will label it that way.
4. The panel's writings.json (wrappers, lookalikes, format recipes) was written by a blind Claude subagent. It is test
   text only: it is never trained on or tuned on, and only claude_gr3.py run/score read it, printing counts. That is
   allowed, because the rule against Claude-written text covers training text.
