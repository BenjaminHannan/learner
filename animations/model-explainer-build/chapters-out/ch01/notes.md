# ch01 notes: "One question, start to finish" (Part 1 of 14, accent thinker)

## SOURCES READ
- architecture/FINISHED-MODEL-2026-10-09.md, whole file (191 lines). Source of truth for every model fact. Section and line numbers are cited per scene in content/ch01.json `src`.
- animations/storyboards-2026-10-09.md, idea 1 (lines 50-66). Used for the legend wording and the two illustrations (done? switch, rounds 3-4).
- Kit: AGENT-GUIDE.md, GLOSSARY.md, briefs/ch01.md, examples/ch99-demo.js, examples/ch99.json. kit.js read only at letters (lines 194-204) and modelMap (lines 332-340).
- NOT read: model-deep-dive.html (older design, not needed), REPO custom_io code (no model fact was re-checked against code; all facts come from FINISHED-MODEL, which cites the code).

## NUMBERS I COMPUTED
- 71 characters, spaces included: our count of `Tom has 12 apples. He gives away 5, then buys 3. How many does he have?` (wc -c). Shown as two rows of 35 + 1 space + 35.
- Scene durations sum to 419 s. The audit total is 424 s, which includes the automatic 5 s title card.

## NUMBERS AS WRITTEN IN SOURCES
- 271,002,624 reader numbers, borrowed and frozen: FINISHED-MODEL line 31.
- 768 numbers per letter (Gemma state): FINISHED-MODEL line 31.
- 4 letters each side (letter window): FINISHED-MODEL line 33.
- 8 operations (add, sub, mul, div, mod, min, max, cmp): FINISHED-MODEL line 37.
- At least 1 round, at most 32 rounds (stop switch): FINISHED-MODEL line 36.
- Calls after rounds 2 to 8 in the tested model (T1SDR): FINISHED-MODEL lines 60-61.
- Program questions score 0.0 with the calculator off: FINISHED-MODEL lines 106-107.
- Calculator matched the old model over 6 copies (seeds): FINISHED-MODEL line 106.
- Gemma in front tested once, 3M, seed 400: FINISHED-MODEL lines 109-110.
- Talker about 25M numbers, planned, not built: FINISHED-MODEL line 38.

## DISAGREEMENTS AND WHAT THE VIDEO SHOWS
- Gemma reader test: the storyboard says "1 test" and the brief says "tested once". FINISHED line 31 also records an earlier 6-copy Gemma test (EGE) that passed its meaning check but missed its zero-round check. The video says "tested once" and does NOT mention the EGE result. See OPEN QUESTIONS.
- Calculator: the storyboard says "6 tests, one leak check cleared by Ben". FINISHED lines 106-108 say the reply-swap check held on 5 of 6 copies. The video says only "matched the old model over 6 copies".
- Scene count: the guide asks for 8-16 scenes (section 2) and 11-14 (section 11). The brief asks for 14-18. Chose 16, which satisfies both.
- Older deep-dive page (17 vectors, 8 rounds): not used. Thinker vector counts are not shown.
- Scale of the example question: the deep-dive page says real questions average 81 characters. Not used anywhere.

## ILLUSTRATIONS (picture only, not measurements)
- s02: the "made-up example" tag is on screen.
- s03: shaded vector strips are decoration. The grouping of letters into Gemma tokens is not drawn (the real tokenisation was not seen).
- s05: the look, pass notes, think loop is a picture of the design, not a recording.
- s06: the empty call slot is a picture of rounds without a call.
- s11: round 3 and the copy arrows are a made-up example.
- s12: round tiles 3 to 8 and the bar text are a picture only. The file does not record how many rounds this question uses (tag: "rounds not recorded").
- s13: the done? switch turning green is an illustration (tag: "illustration"). No file records a stop round for this question.
- s10 and s09: the calculator-and-Gemma picture combines two parts that have never run together. The legend (s15) says so.

## OPEN QUESTIONS (for the project owner)
1. Should the legend mention the earlier 6-copy Gemma test (EGE) that missed its zero-round check? Right now it says only "tested once".
2. The 0.0 score in s09 is shown as "points out of 100". The source gives no unit, so this follows the glossary rule. Confirm the unit, or drop it.
3. Should the reply-swap check (5 of 6 copies) be on screen? It is not in the video.

## KIT REQUESTS
- None needed. The kit gives each scene only its own content JSON, so the example question text is repeated in each scene that shows it (scenes 2, 3, 4, 6, 8, 11). A shared chapter-level field would avoid this. Note this for the audit: repeated question text counts toward each scene's reading time.

## FOR THE NEXT AUTHOR
- Terms introduced: round, call, reply, vector, frozen, borrowed, learned, call slot, control vector (first mention only).
- The line "now we open each box" (s16) hands off to chapters 3-7.

## GUIDE FEEDBACK
- Section 2 says 8-16 scenes; section 11 says 11-14; the brief says 14-18. Please pick one number.
- Audit counts the question text repeated in each scene, and chip default words are not audited. Both behaviours are fine but worth stating in the guide.
- Visual review: the contact sheets were generated, but this author did not review every sheet (context limit). Review sheet-01 to sheet-16 before publishing, especially s05 (curve bend), s12 (tile row) and s15 (chips against captions).
