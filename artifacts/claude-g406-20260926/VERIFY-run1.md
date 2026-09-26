# g406 run 1: INCONCLUSIVE on the GLM route, not on the labels (written 2026-09-26 20:35:40 UTC by date -u)

- Verdict: INCONCLUSIVE (V failed: 23 of 560 transcripts usable, bar 532). Recorded as a route failure: the run stopped
  itself at 20:08 UTC on its failed-call limit after 80 transcripts, 57 of them without a usable answer. It says nothing
  about whether GLM's labels agree with the judges.
- Blind recount (a fresh agent with its own script, read-only, 20:3x UTC; scratchpad recount406/recount.py) of
  run/glm.jsonl (sha256 147818e3...): 80 rows, 80 distinct transcripts, all from mu-402; 23 usable (every one a 0/1
  list of the right length), 57 with no flags. Seconds for unusable rows: 18 under 60, 37 from 60 to 299, 2 from 300 to
  899, 0 at 900 or more; usable rows: 20 under 60, 3 from 60 to 299. Usable rows hold 113 replies with 12 GLM flags.
  Matches the builder's RESULTS.md and the thread's own count exactly.
- What the 57 are: not recorded. claude_g406_glm.py wrote a helper failure (the helper raises after 3 failed tries)
  and an unparseable reply as the same empty row with no error text. No row took 900 s or more, which three 300-s
  timeouts would need, so timeouts are unlikely to be the main cause (suggested, not shown).
- Next: no resume until lis320-ocdiag says which prompt form works on this route (ADDENDUM-3). If the working form is
  g406's sealed prompt, the held resume runs unchanged on helper v1.1. If it needs a different form, that is a new gate
  (g406-2) with its own seal before any call, not a resume under these marks.
