# ch02 notes (The goal and the rules of the game)

STATE: delivered. 12 scenes, 412 s (6.9 min) plus the 5 s title card. Audit 0 flags; `hyperframes check` passes (layout 0 issues in 9 samples, contrast 48/48); 8 snapshot sheets. Sheets 01, 02 and 05 were looked at (s01-s03, s07, s08 start) and two overlaps were fixed (s03 planned-bar chip, s07 leak numbers). s04-s06 and s09-s12 were NOT looked at closely beyond check's 9-sample layout pass: a reviewer should open sheets 03, 04, 06, 07, 08.

SOURCES READ (PFS = project-files-snapshot): big-run/PLAN.md lines 3-90 (90% bar l.51, scorecard l.62-88, l.75, l.80), architecture/FINISHED-MODEL-2026-10-09.md lines 1-39, 71-151, no-hardcoding/PLAN-AND-MARKS-2026-10-07.md lines 17-25, 66-70, 95, whole-model-roadmap-2026-10-06.md lines 1-30, 83-88, 424-448, memory/MEMORY.md lines 8-18, repo CLAUDE.md lines 3-17.

NUMBERS AS WRITTEN: 271,002,624 (FINISHED l.31); 102.1M trained + 271.0M frozen = 373.1M as built (l.21-23); planned about 271M + about 100M + about 25M = about 397M (FINISHED l.21-22; PLAN l.26 says about 398M, video shows 397); 191,172 of 1,655,902 pool rows (PLAN l.75); leak 5.0-5.6 against limit 5 (PLAN-AND-MARKS l.95); 6-seed calculator test, seed 205 checkpoint lost (FINISHED l.107-108); 171,940 teaching rows (roadmap l.445); 6+ paired seeds (roadmap l.432); about 1 in 3 / well under 1 in 10 (PLAN l.51, the plan's own judgement); 0 of 9 fully green (PLAN l.80).
NUMBERS COMPUTED: none. (Bar lengths in s03 are drawn to scale of the millions shown, 3.3 px per million.)
DISAGREEMENTS: PLAN says about 398M with the talker, FINISHED-MODEL says about 397M; FINISHED is the source of truth, so 397 is shown. The planned row is NOT 373.1 + 25: the plan counts the thinker as about 100M, not 102.1M.
ILLUSTRATIONS (all labelled on screen): s04 growth lines ("picture only, no numbers"); s06 six pairs of squares ("picture only"); s09 bar lengths (picture of 1 in 3 and of under 1 in 10, tagged "judgement, not measured"); s10 half-filled idea is only colour = status from PLAN l.80; s07 six squares with one greyed are a picture of 6 copies, 1 lost.
STATUS COLOURS: green chip "partly shown" is used for rows with a result but not a full pass (s01, s10); grey = plan / never tested; warn orange = hand code left or where rules slipped.
BRIEF ITEMS: brief asked 9-12 scenes at 200-260 s; guide section 11 (330-420 s) won. Scorecard row names in s10 are our short plain-word versions of the nine principles.
OPEN QUESTIONS: none real. The scorecard is dated 10-09 11:00 AM ET and may move.
KIT REQUESTS: none (local helpers growX and counter live in ch02.js).
FOR LATER CHAPTERS: this chapter introduces "marks", "seeds" (copies), "plain model", "whole size", "the 90% bar", "scorecard". Colour use: planned thinker indigo, learned-by-us blue.
