# ch13 notes: Size, and whether it pays off (13 scenes, 498 s; audit 0 flags; hyperframes check passed)

## SOURCES READ
Per scene, the file:line pointers are in the `src` list of each entry in ch13.json. Main sources: architecture/FINISHED-MODEL-2026-10-09.md (sec. 1, 5), big-run/PLAN.md (lines 17-18, 33, 38-51, 77, 197-200, 270-284), whole-model-roadmap/8A-10M-RESULT-2026-10-08.md (lines 7-11, 27-31, 49, 68, 78-97), 8AG-GEMMA-GROWTH-SPEC-2026-10-08.md (sec. 4, 9, 12, 13), animations/source-g1-3m-s400.json, sources/pr-56-b3-group1-and-token-test.md.
The planned dossier ch13-A.md did not exist on disk; the JSON src pointers from the earlier author were used instead. Not re-verified line by line against the sources in this final pass (the earlier author wrote them).

## NUMBERS I COMPUTED
- 5.89 = 73.01 minus 67.12 (s07; caption and label say "our subtraction"; ch09 rounds it to 5.9).
- Bar and segment widths in s02 (bars) and s03 (stacked bar) are drawn to scale from the source numbers; no other number is derived.
- 6.9 days = 25.0 s x 24,000 updates, as written in PLAN.md line 18.
## NUMBERS AS WRITTEN IN SOURCES
Ladder 4,039,957 / 9,832,977 / 29,789,693 / 102,116,618 (pr-56 line 15); 373.1 = 271.0 + 102.1 and about 398 plan (373.1 + 25; PLAN lines 47, 270; FINISHED sec. 1 says 397); 8a gains +0.49 / +3.77 / +15.77 and 72.34 to 72.83 (8A-10M-RESULT lines 49, 68); per-type scores (lines 84, 94, 95); 73.01 = 4,410 of 6,040 and 67.12 = 4,054 of 6,040 (source-g1-3m-s400.json); odds "about 1 in 3", "well under 1 in 10" (PLAN line 51); Mac 25.0 s per update, PC 3 to 5 weeks, rented about $80 cap $120 (PLAN lines 18, 273-275).
Design: 8a numbers belong to the older B2 as it ran (9 note vectors, 8-letter targets); 73.01 vs 67.12 is the G1 re-run (12 fixed rounds, calculator inside); ladder counts are the B3 group-1 thinker at caps_b3.

## DISAGREEMENTS
- Plain gains: summary text says about 3.7 / 15.6, the table says 3.77 / 15.77 (5 seeds). Video uses the table.
- Planned total: FINISHED line 21 says about 397M (thinker counted as about 100M), PLAN.md lines 47 and 270 say about 398M. FIXED after the number check: video now shows about 398M so it matches the on-screen sum 373.1 + 25 = 398.1.
- 3M size: B3 thinker 4,039,957 (s02) vs G1 older thinker 3,544,913 (ch09). Labelled by build in notes only.
- Race timing: PLAN.md line 33 races the 30M model first; brief and R4 race the finished model. Caption says "after the model exists".

## ILLUSTRATIONS (all tagged on screen)
s01 two lines (chip "picture only: not a measurement"); s06 cell shading (chip "picture only: cell shading means nothing"); s08 number line and the "?" marker (chip "picture only: shows the written rule, not a result"); s10 boxes show odds only (chip "judgment, not measured"); s12 lanes (chip "picture only: no race has been run").

## OPEN QUESTIONS
- Seed 401 timing and the 10M readout are estimates in the sources; the video gives no time ("not in yet").
- The 6-seed 3M confirm cited in ch03 is not judged (seeds 202-207 missing); ch13 does not rely on it.

## KIT REQUESTS
- S.hbars has no `pre` option (needed "+" on the s04 gain bars); built rows locally with S.bar + S.grow.
- No dashed-border option on S.card/S.box; set borderStyle on the element directly (s03, s06).

## For the next chapter
Ch13 owns the ladder numbers and the "scaling bar" (ours must gain more from size than a plain model). No size claim is made: one 3M rung of one copy only. Chapter 14 can refer to "the ladder" and "the bar" without re-defining them.

- Fix pass (number check): s03 397 -> 398; s08 PLAN locator now lines 204 and 206; s09 and s10 each got a 'picture only' tag (s10 also says under 1 in 10 is not zero); durations s09 41 s, s10 42 s to keep reading time.
