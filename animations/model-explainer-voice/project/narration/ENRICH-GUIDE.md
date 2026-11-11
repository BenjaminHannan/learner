# Filling the quiet gaps: add a little teaching to narration lines that have room

**IMPORTANT, read first: nobody can read anything you say except the coordinator, who reads your final structured result. NEVER call any `mcp__hearthbot__` tool (reply, update_status, post, react, anything) and never message anyone. Just do the work and finish with the structured result.**

Read `narration/SCRIPT-GUIDE.md` first (all its faithfulness and style rules still apply). The spoken script for each part already says what each caption says. But many lines are much shorter than the time their caption stays on screen, which leaves long silences (the median pause between spoken lines is 4 s, some are 10 s or more). Your job: for the listed segment ids, say a little more, the way a patient teacher would to a 12-year-old, so the voice fills the time without rushing.

## What you may add (and only this)

- One or two short plain sentences that say **what the picture shows** or **why this fact matters**, using the video's own words and analogy (a student doing a word problem; the reader is a translator, the thinker a team of note-takers passing notes in rounds, the call writer hands a slip to the calculator, the stop switch is a bell, the talker writes the answer sheet). `GLOSSARY.md` (in the project folder) has the plain-words definitions and the analogy table: you may use its wording.
- A plain meaning of a term the caption uses, the first time it appears in the part (see GLOSSARY.md).
- A short bridge to the previous line when it helps the listener follow ("Remember the thinker works in rounds.").

## What you may not add

- **No new numbers.** Use only numbers that are on screen in this scene or in the caption. Do not calculate anything new, compare numbers in a new way, or round (except the existing rule for numbers of 100,000 or more).
- **No new claims** about results, what was tested, what works, what is planned, or what other models do. Nothing about sources, files, checking, or "our notes". No history, no opinions, no "impressive", "amazing", "powerful", "huge".
- Never weaken or drop a status or honesty word that is in the current line (planned, never tested, picture only, stand-in, older, only, about...). Keep every number the line already speaks.
- Do not repeat what the neighbouring captions of the same scene say, and do not give away what the next caption will say.
- If the sources give you nothing useful to add for a segment, leave it unchanged. Padding is worse than silence.

## Time

The room list gives, for each id, how many more seconds of speech fit (already net of a safety margin). About 2.3 spoken words per second; numbers cost more. Use at most about 85% of the room. After editing run `python3 tools/voice/check_script.py chNN`: it must report no error for your ids (it predicts speaking time and fails a line that would not fit).

## Steps

1. `python3 tools/voice/seginfo.py chNN` for each caption and the scene's on-screen text. Room list: `narration/review/enrich-room.json` (`{"chNN": [[id, room_seconds], ...]}`).
2. Edit only the listed ids in `narration/script/chNN.json` (read the file, change those entries, write it back, check it parses).
3. Report each changed id with its final text and one phrase naming where the added idea comes from (caption, a label, or a GLOSSARY.md line).
