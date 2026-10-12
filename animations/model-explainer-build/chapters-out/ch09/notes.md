# ch09 notes: "Does the thinking really do the work?" (Part 9 of 14, accent thinker)

12 scenes, 321 s plus the 5 s title card = 326 s. Audit: `TOTAL 326 s = 5.4 min;  flags: 0`. `hyperframes check` passed (0 lint/runtime/layout/motion issues, 68/68 contrast).
Scene order: s01 where we are, s02 a score alone, s03 what the 6,040 questions are, s04 the dial 12-2-1-0, s05 24 rounds, s06 chain-5, s07 break the notes, s08 break the calculator, s09 the leak, s10 side by side, s11 what this does not show, s12 recap.
Supporting file: `g1-3m-s400-extract.json` (every number I used, re-added from the raw RESULT.json files; the `src` lists point at it).

## SOURCES READ
- Kit: AGENT-GUIDE.md, GLOSSARY.md, VERIFIER-GUIDE.md (appeared mid-work), briefs/ch09.md, examples/ch99-demo.js + ch99.json, kit.js, main.js, style.css, tools/*.mjs.
- /mnt/project-files/animations/source-g1-3m-s400.json (headline G1 numbers; the brief's numbers match it).
- Raw files, branch origin/claude/8a-g-pc-results: `results/8a-g/pc/8aG1d-pc/8aG1d-3M-s400/{B2,PT}/RESULT.json` (via `git show`). **These decided every number in s02-s10.** Fields used: final_eval.{in_dist,answer,frame,vocab,variant}, lesions.{loops:0,1,2,24,shuffle_state,donor}, chain5, extra.opswap, extra.noexec, PT lesions.calc and chain5.calc, n_params, steps_per_s, config.cfg.n_loops.
- Branch origin/claude/project-thread-qtxfp4: custom_io/PASS-MARKS.md (addendum 14, "Wiring checks", marks), custom_io/README.md, custom_io/models/{base,ledger,plain_tf_steps}.py, custom_io/results/RESULTS-EG2.md (leak numbers).
- whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md (addendum G), architecture/FINISHED-MODEL-2026-10-09.md (sec. 2, 4, 5), big-run/PLAN.md (scorecard row 2), custom-io/gpt-b2-leak-and-credit-2026-10-05.md (split definitions), architecture/model-deep-dive.html (read as text, for the explanations only), animations/storyboards-2026-10-09.md idea 2.

## NUMBERS I COMPUTED (value, formula, inputs)
| shown | formula | inputs |
|---|---|---|
| 73.01 / 4,410 | 100 x 4410/6040 | 1170+863+1178+715+484 right; 1360+1200+1360+800+1320 = 6,040 |
| 20.00 | 100 x 1208/6040 | loops:1, summed over the five splits |
| 29.30 | 100 x 1770/6040 | loops:2 |
| 0.66 | 100 x 40/6040 | loops:0 |
| 72.57 | 100 x 4383/6040 | loops:24 |
| 27 | 4410 - 4383 | right at 12 rounds minus right at 24 rounds |
| 0.96 | 100 x 13/1360 | loops:0, in_dist split only (s09) |
| 6.80 | 100 x 411/6040 | shuffle_state, summed |
| 86.03 / 4.19 / 55.15 | 1170/1360, 57/1360, 750/1360 | donor lesion, in_dist split only (s07) |
| 99.9 | 830/831 = 99.88 | extra.opswap (n_affected 831) |
| 69.62 | 100 x 4205/6040 | PT lesions.calc, summed |
| 5.9 (5.89) | 73.01 - 67.12 | s10 caption says "our subtraction" |
| 2.7 (2.735) | 6.51 / 2.38 | s10 caption says "our division"; 2.80/1.02 = 2.745 gives the same 2.7 |
| 3.39 | 73.01 - 69.62 | s10 caption says "our subtraction" |
| 72.35 | 73.01 - 0.66 | computed while checking; NOT shown |
The three scores the brief calls "the animations thread's recomputation" (20.00, 29.30, 72.57) were re-added from the raw files and match. Counts 1,208 / 1,770 / 40 / 4,383 are on the s04/s05 `notes`.

## NUMBERS AS WRITTEN IN SOURCES
- source-g1-3m-s400.json: train_hours 6.51 (line 7) and 2.38 (line 47); pooled5 73.01 (12), 0.66 (25), 20.0 (30), 29.3 (35), 72.57 (40), 67.12 (51); chain5 intact 99.9 (15), 91.0 (53).
- PT RESULT.json `calc` blocks (lines 908 and 2808 of the raw file): 69.62 pooled-5, 99.0 chain-5.
- B2 RESULT.json: opswap swap_match 99.88, n_affected 831 (lines 12090-12091); donor_match 55.147 (line 9575); noexec n 2085, intact 100.0, program rows 0.0.
- PASS-MARKS.md addendum 14 (line 341, 367, 372) and RESULTS-EG2.md line 11: loops:0 in_dist 18.09 (seed 200, with the Gemma reader) against 1.40 (plain B2V); mark 5.
- Model sizes 3,544,913 and 3,495,936 learned numbers (n_params in the two RESULT.json files; also in the source file).

## DISAGREEMENTS
1. **Lesion numbers.** The brief (and model-deep-dive.html) say: another question's notes 3.8%, shuffled 7.9%, no calculator 0.6%, swap 99.9%. Those belong to an older design (8 rounds, one seed 200). The raw G1 file holds the same lesions for the model this chapter is about, so s07/s08 show G1's numbers: 4.19 (on the 1,360 familiar questions), 6.80 (all 6,040), swap 830 of 831, calculator off 0.0 on 2,085 program questions. The swap result agrees (99.9). **Decided by:** the raw G1 RESULT.json; the brief's older numbers are not on screen.
2. **Calculator off.** The deep-dive says "program questions score 0.6%". G1 says 0.0 on the 2,085 questions that need the calculator (was 100.0). Shown 0.0.
3. **Leak.** Brief: "EGE 18.09 vs B2V 1.40 on seed 200", "G1's zero-round score is only 0.66". Those are different splits and different model versions: 18.09 and 1.40 are on the 1,360 familiar-template questions of the earlier (8-round) version, seed 200. G1's 0.66 is over all 6,040; on the familiar split alone it is 0.96. s09 shows all three on the same split (familiar questions) and says in the caption that 0.66 is the all-6,040 figure, and that the 200s are an "earlier version".
4. **Which model.** The guide's arc asks for the five-part map. The model that was tested has the calculator inside and 12 fixed rounds; the five-part map (kit default) shows a calculator "outside tool" and a "stop switch". s05 and s11 say the stop switch is built but never tested and that this is the older design. The map itself is the kit's own picture; I did not change its labels.
5. **Deep-dive says looping is "fixed at 8" and 17 thinker vectors.** Not used. Only "12 rounds" (G1 config n_loops 12) appears.

## ILLUSTRATIONS (picture only, labelled on screen)
- s06: the "Tom has 12 apples. He gives away 5, then buys 3." question and "two steps, two rounds". Chip "made-up example". The deep-dive says the real example is also made up; the one-step-per-round claim is taken from the older design page, not re-checked for G1.
- s07: the A/B pipelines, the note strips (random-looking shading) and the arrows. Chip "picture only". The score cards are real.
- s08: the Calculator box, the add/subtract pills and their swap, and the red cross. Chip "picture only". The cards are real.
- s04/s05: the dial picture: needle angle is 270 degrees x rounds/24, no data in it.

## OPEN QUESTIONS (for the project owner)
1. s07 "another question's notes" 4.19 is on the 1,360 familiar-template split only (that is how the donor test is run); the shuffle and calculator-off figures are on bigger sets. Is it OK to show these side by side as they are (each card states its own set), or would you prefer the donor test re-run on all 6,040?
2. I add a "plain model + calculator at the end, no retraining" column in s10 (69.62 pooled, 99.0 chain-5; gap 3.39 points). It makes the headline less flattering, but I think a viewer would ask for it. It is in PT RESULT.json. Please confirm you want it in the video. To cut it: remove the `calc` column in s10 (JSON `heads.calc`, `headSubs.calc`, `table[].calc`, the last caption) and the `calc` lines in the s10 builder (the builder is not conditional).

## KIT REQUESTS (things I worked around with local helpers in ch09.js)
- A **dial helper** (`S.dial`): `makeDial` in ch09.js draws the 0-24 dial, needle and readout. The dial picture is "owned" by ch09 per the brief; later chapters may want to reuse it.
- A **result card** helper (title + counting big number + sub line): `resultCard` in ch09.js.
- A **per-row reveal for `S.hbars`**: `hb.reveal(t)` shows all rows at once; I needed one row per caption (`revealRow`).
- A way to **relabel S.modelMap** parts (e.g. "tested model: calculator inside") so a chapter about the older design is not shown the finished map.
- A way to put a number in the JSON and have the audit not count it when it only drives a picture (needle values, tick marks).

## FOR THE NEXT AUTHOR
- Terms I introduced: **round** (one lap of the thinker), **dial** (rounds, turned down at test time), **lesion test** ("break one part and see if the answer breaks"), **pass mark** (the bar written down before the run), **wiring check** (a test that must pass by construction, so it shows plumbing, not reasoning), **pooled-5** (6,040 questions kept aside, five kinds), **chain-5** (1,000 multi-step questions), **copy** (instead of "seed"; "copy 200", "copy 400").
- Analogy used: the thinker as a team of note-takers working in rounds (GLOSSARY). I did not add a new one.
- You own: 73.01 (s02), 0.66 (s04), 67.12 (s10), the dial picture, as the brief says. The "plain model + calculator" column (69.62 / 99.0) is new from this chapter.
- The 5-part map is drawn for the finished design. ch09 says in s05/s11 that the tested model is the older design with 12 fixed rounds and no stop switch.
- Code names deliberately not on screen: G-B2, G-PT, C1', EGE, B2V, loops:K, noexec, opswap, donor (they are in `src`/`notes` only).

## GUIDE FEEDBACK (pilot)
What worked: `S.capAt`, `S.at`, the audit (it caught 10 scenes that were too short on the first pass), the VERIFIER-GUIDE idea, and the demo chapter for helper names. The kit's look is good.

Problems, most important first:
1. **Reading budget vs brief length.** The brief says 10-13 scenes, 240-300 s, "more scenes you should add for depth". The audit rule (3 s + words/2.6) makes each scene about 20-37 s for 45-85 words. My 12 scenes need 321 s even after I cut words several times, so the brief's own scene list cannot fit 300 s. Either raise the target (to about 330 s) or say which scenes in the brief to cut.
2. **Briefs gave older-design numbers.** The brief's lesion numbers (3.8 / 7.9 / 0.6) came from a page for an earlier model, while the raw G1 RESULT.json already had all lesions for the actual model. A brief should list, for each number, the raw file and field, and say "this number is for design X". The guide's rule "newer source wins; write it in notes" worked, but only because I opened the raw files.
3. **Setup commands.** The guide's loop does `mkdir -p chapters content` after copying the kit, but the kit already has `content/global.json` and `merge.mjs` needs it; `mkindex` prints "0 chapter file(s)" until chapters/chNN.js exists (confusing, not an error). Say so in section 7.
4. **What the audit counts is not written down.** It counts every JSON string token and every number as one word (including numbers that only drive pictures, such as ticks and needle positions, and `0.0` values), ignores only the keys `id, src, notes, duration, illustration, at`, and does not see text the kit draws itself (map labels). Authors can't tell where their words went. Please list it in section 3.
5. **Caption objects `{at, text}` are supported by main.js and audit.mjs but not in the guide.** I needed them (counts were still moving at the 0.8 frame). Document: `at` is a fraction 0..1 of the scene; the slot is the gap to the next caption; the audit checks each slot.
6. **Which frames are sampled.** shots samples at about 0.18, 0.39, 0.59, 0.8 of each scene (4 per scene). Anything still moving at 0.8 looks unfinished on the sheet (my count-ups). The guide's "last 20% is still" rule explains it, but say that the 0.8 frame is the one that matters, and that the four frames are not evenly spaced across captions.
7. **Tool side effects.** `hyperframes check` fetches Google Fonts (network) and writes a font cache; `shots` writes extra `contact-sheet-*.jpg` and `frame-*.png` next to `sheet-*.jpg` (and `--describe` complains about GEMINI_API_KEY). Rule 6 says "no network except reading"; say that this is allowed, and that only `sheet-*.jpg` are deliverables. `check`'s layout test samples just 9 frames, so overlap in a late caption can pass; I found my own problems only on the sheets.
8. **The kit changed during my work.** VERIFIER-GUIDE.md appeared after my first listing. Say which kit files are final, or version them.
9. **SVG z-order is creation order.** A drawing made with `S.svg()` before a card is hidden behind it (my red cross was invisible until I made a second `S.svg()` after the card). One sentence in section 4 would save a debugging round.
10. **No dial / big-number / result-card helpers**, and `hb.reveal` is all-rows-at-once (see KIT REQUESTS). The guide asks for 60% mechanism scenes, so these will be re-written 12 times.
11. **modelMap always shows the finished design** ("Calculator: outside tool", "Stop switch: ours"). A proof chapter about the older tested model has to explain the mismatch in later scenes.
12. **Fonts.** `check` reports fetching Inter and JetBrains Mono; my dial's SVG text asks for `DejaVu Sans Mono`. Harmless, but the guide should name the one mono font to use.
13. **Glossary gaps:** "lesion", "pass mark", "wiring check" and "copy" (for seed) are not defined, and the plain-word rule (code name only as a tag) leaves authors to invent them. I defined them in the chapter; a glossary entry would keep the 14 chapters consistent. "Refer to the project owner, not individuals" worked fine.
14. **Rates versus scores.** The "points out of 100" rule says every score; a share (830 of 831 = 99.9) and counts of right answers are not scores. I put the small head "points out of 100" over every set of score bars/cards and wrote the count where it was a count. Please say what to do with rates.
