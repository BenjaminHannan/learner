# Long explainer: where it stands (stopped 10-09 ~2:30 PM ET on Ben's usage limit)

Ask (Ben, 10-09): a long animation explaining every part of the model, as in-depth and long as possible, written by Sonnet agents, built with HyperFrames.
Plan: 15 chapters (ch00 to ch14, about 60 minutes), one content JSON + one scene-builder JS per chapter, assembled into one video, then draft render, one frame per second review, 1080p MP4.

DONE (all in this folder):
- kit/  the working HyperFrames project: kit.js (scene helpers), main.js, style.css, tools/ (merge, mkindex, audit, shots, assemble), examples/ (demo chapter), content/global.json.
  Checked: `npx hyperframes@0.8.143 check` passes on the demo; local render works (10 s of 1080p in about 16 s). No paid compute used.
- kit/AGENT-GUIDE.md, GLOSSARY.md, VERIFIER-GUIDE.md, briefs/ch00.md to ch14.md: everything a Sonnet author or checker needs.
- sources/  saved PR bodies (#53 sleep, #56 B3 group 1 and token test, #58 domain mode).
- ../storyboards-2026-10-09.md (earlier storyboards) and ../source-g1-3m-s400.json (G1 numbers).

CHAPTER 09 WAS DELIVERED before the stop: chapters-out/ch09/ (ch09.json, ch09.js, notes.md with GUIDE FEEDBACK, 8 contact sheets). The author reports 12 scenes, 326 s, audit 0 flags, `check` passed. I have NOT re-checked any of that, and no checker has verified its numbers yet. It chose raw G1 lesion numbers (donor 4.19, shuffle 6.80, swap 830/831, calculator off 0.0 on 2,085 questions) over the older page's, and added a plain-model-plus-calculator column (69.62 / 99.0) in s10 that the owner may not want.
NOT DONE: chapters 00-08 and 10-14 (the ch01 and ch03 pilots were stopped before delivering anything).

TO RESUME (when Ben says go):
1. Read chapters-out/ch09/notes.md GUIDE FEEDBACK (14 items: what the audit counts, `{at,text}` captions, check/shots extra files, SVG layer order, no dial or result-card helper) and fix the guide/kit. Then run the ch01 and ch03 pilots (Agent tool, model sonnet, background; prompt = read AGENT-GUIDE.md, GLOSSARY.md, briefs/chNN.md, then deliver to chapters-out/chNN/). Fix the guide from their GUIDE FEEDBACK.
2. Launch the other 12 chapters (about 5 at a time; the box has 4 CPUs).
3. One Sonnet checker per chapter (VERIFIER-GUIDE.md), then `node tools/assemble.mjs` in a copy of kit/, `npx hyperframes@0.8.143 check`, draft render, `snapshot --at` one frame per second, fix, `render --fps 30 --quality standard --workers 4`.
Cost warning: this is a big token job (15 authors + 15 checkers). Ask Ben before starting, or shrink to fewer chapters (the briefs say which matter most: ch01, ch04, ch09, ch12).
