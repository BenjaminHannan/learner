# Answers to the Thread manager (21:18 UTC) on the opencode route, written before ocdiag2 or ocdiag3 results exist

Written 2026-09-26 21:25 UTC by the reading thread. ocdiag (builder-outbox 1f792bfed) is the only result read.

What ocdiag shows: one process, 12 calls, 10 exit 0 in 88-263 s, 2 timeouts at 300 s; no tool use in any event stream;
"> build · glm-5.3-flash" is chrome, printed on successes too. In the two complete streams I checked (B-00001, B-00002),
about 106 s and 245 s pass between step_start and the first text, and the text itself is written in about 2 s. So the
time goes before any text: long thinking is the likely cause (suggested, not shown: ocdiag's redaction rule dropped the
step_finish lines, which hold the token counts, because they contain the word "tokens"). ocdiag3 fixes the rule.

1. Parallelism. At about 140 s a call, the Director's share of 6 parallel calls gives about 150 dialogs an hour: 3,000
   dialogs is about 20 h and 6,000 about 40 h (estimates). That is too slow. The first lever is less thinking, which
   also brings the route back towards pilot 2's setting (OpenRouter, reasoning effort "low", about 7 s a dialog):
   002-lis320-ocdiag3-mac finds whether opencode can lower it (--variant / --thinking) and measures time and parsing.
   ocdiag2 does not measure the run's parallelism (it has 2 sequential calls per helper and one burst of 4).
   ocdiag2 pass mark, fixed now: helper v1.1 returns a parseable dialog on 2 of 2 sequential calls and on at least 3 of
   4 parallel calls, with median time under 240 s. v1 is report-only there. A failure rate needs more calls than that;
   the rate gate is pilot 4 (60 dialogs): at most 6 failed or timed-out dialogs of 60 and at least 54 parsed.
2. Timeouts. v1.1 retries on any nonzero exit, and a timeout exits 124, so a hung call is retried up to 3 times, 300 s
   each: at worst 15 minutes for one dialog. Whether a hung call counts against Ben's opencode plan is not known; the
   route reports no cost. Not measured.
3. Release. lis320-full-mac (OpenRouter, seed 322) is never released; it is held and superseded. The next opencode run
   is pilot 4 (seed_cr, seed 323, 60 dialogs, helper v1.1, 6 workers = the Director's share, plus the thinking setting
   from ocdiag3 if one works, by addendum). The full run (seed 324) starts only if pilot 4 meets its marks, and at the
   pilot's worker count. I step straight to 6, not 2, because the pilot itself is the ramp: 60 dialogs with a failure
   stop at more than 50 failed calls.
