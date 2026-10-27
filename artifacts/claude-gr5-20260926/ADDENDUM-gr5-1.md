# ADDENDUM gr-5 #1: two report-only lines from the Thread manager's review (2026-09-26 20:20 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. Written before the adapter was trained and before
any gr-5 run. PASSMARKS-gr5.md is not edited. The marks, bars, arms, the dev stop rule and the decision rule are
unchanged. Both lines below are report only and gate nothing.

1. The 7 lookalikes that read_latin reads as a square. R2 stays on the 53 lookalikes whose truth is none, as sealed.
   Its truth is what the code stand-in reads, so on those 7 the stand-in is the judge. For them, and for L and P0
   separately, the report gives: read as a square, read as the same grid read_latin reads, and read as none. That shows
   whether the learned copy agrees with the stand-in where the blind writer meant "no square". The counts come from
   the run files (L_lookalikes.jsonl, P0_lookalikes.jsonl) in the blind recount.
2. The held-out dev squares, split by wrapper. 19 of the 72 held-out squares sit in a 1B wrapper that also wraps a
   training square. A wrapper is a message's lines that hold no digit. scripts/claude_gr5_devclean.py (selftest: clean
   53, shared 19) copies the 72 with the trained adapter and prints exact, wrong and none counts for the 53 clean and
   the 19 shared squares, so the dev gate's 65 of 72 can be read either way. It runs on BensPC right after the dev
   gate, whatever the gate says, and its output changes nothing.
