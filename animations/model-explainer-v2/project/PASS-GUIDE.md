**FORBIDDEN: never call any `mcp__hearthbot__*` tool (reply, update_status, react, ...). They post into a real person's chat. Do not narrate progress as messages; only your final structured result is read.**

# Shortened explainer: checking and fixing pass (checker, looker, fixer)

The long silent explainer about a research AI model was written as 15 chapters (120 minutes). It is being cut to a MAIN video of about 69 minutes made of 10 chapters.
You work on ONE of them. Everything you need is on this machine. Nothing here is published; your output goes to a folder the coordinator reads.

## The cut (important for every role)
Kept chapters, in play order, with their new on-screen numbering: ch00 "Start here" (trimmed to 11 scenes), ch01 Part 1 of 8, ch03 Part 2 of 8, ch04 Part 3 of 8, ch05 Part 4 of 8,
ch06 Part 5 of 8, ch07 Part 6 of 8, ch08 Part 7 of 8, ch09 Part 8 of 8, ch14 "Wrap-up" (trimmed to 7 scenes).
REMOVED from the main video (they live in a separate optional extras video): "the goal and the rules" (old ch02), "how we test fairly" (old ch10), "sleep" (old ch11),
"ideas being tried: B3 groups, experts, tokens, long text, domain mode" (old ch12), "does bigger help / size ladder" (old ch13).
So in a kept chapter: any sentence that points to a removed chapter ("Chapter 12 covers it", "Chapter 9 explains the test", "see the sleep part") must be rewritten so it stands alone
(say the plain fact, or say it is "not covered in this video"), and any pointer to a kept chapter must use the NEW numbering ("Part 8") or no number. A removed topic may still be mentioned
in one clause if a kept scene truly needs it, but never promise a later part that does not exist. The video must make sense without them.

## Paths
- `FINAL=/mnt/project-files/animations/model-explainer-final`; kit `FINAL/kit` (read `kit/AGENT-GUIDE.md` sections 4-7 for the content format, the kit API and the seek-safe rules; `kit/GLOSSARY.md` for words, analogy, colours);
  input chapter `FINAL/in/chNN/chNN.json` + `chNN.js`; output folder `FINAL/out/chNN/` (you write here; never write into `in/` or `kit/`).
- Working copy (local, fast): `W=/tmp/claude-0/-home-user-learner/01bcea25-2484-5edd-8248-d1fe6e738ef5/scratchpad/cut/work/chNN`. Set up with:
  `mkdir -p "$W" && cp -r FINAL/kit/. "$W"/ && cd "$W" && rm -rf snapshots && mkdir -p chapters content && cp <chapter json> content/ && cp <chapter js> chapters/`
  then `node tools/merge.mjs && node tools/mkindex.mjs --only chNN && node tools/audit.mjs chNN`; `npx --yes hyperframes@0.8.143 check .`; `node tools/shots.mjs chNN [sceneId] [--per N]` (contact sheets in `snapshots/chNN/sheet-XX.jpg`, six panels each, labelled `sNN @T s`).
  The machine has 4 CPUs shared with other agents: run check/shots only when you need them. Never run `hyperframes render`.
- Sources: `/mnt/project-files` (called PFS in the chapter notes) and the repo `/home/user/learner`. Code and result files cited as `custom_io/...`, `custom-io/...`, `g8a/...`, `results/8a-g/...` are on git branches that are already fetched:
  `git -C /home/user/learner show origin/claude/custom-reader-talker-4x309r:custom_io/models/tool.py` (T1SDR/H1 code, commit 17a356e62), `origin/claude/project-thread-f1to6a` (8a/G1 code), `origin/claude/project-thread-qtxfp4` (B3 group 1, PR #56),
  `origin/claude/8a-g-pc-results` (G1 raw results), `origin/claude/learner-new-g2` (newest notes). PR bodies are saved in `/mnt/project-files/animations/model-explainer-build/sources/`.
  The newest source of truth for how the finished model works is `/mnt/project-files/architecture/FINISHED-MODEL-2026-10-09.md`; it wins over older pages (17 vectors, 8 rounds, calculator inside = older design).
  Use `grep -n` on big files (big-run/PLAN.md is 80 KB, the audit 80 KB); do not read them whole.
- Do NOT call any `mcp__hearthbot__*` tool. Do not read or open protected/sealed panels (GOLD-PRIVATE, reserved, blind). No installs, no paid or external services.

## Role: CHECKER (Sonnet)
Goal: every number and claim on screen is supported by the sources, said at the same strength, and the chapter stands alone inside the cut video.
1. Read the chapter JSON completely and the JS for any string or number written in code (`grep -n` for quotes and digits). Every on-screen string except symbols and the kit's default chip words must be in the JSON; move offenders into the JSON.
2. For EVERY number, name, date and factual sentence: open the source the scene's `src` names (or find it), find the value, record file + line/section. Recompute any number the author computed (it must be flagged in the caption and explained in `notes`).
   Look for: "shows/proves/beats" where the source says suggested/untested; a result called tested when it ran once at one size; plans stated as done; an older design's number used for the current model; future dates stated as certain; two sources that disagree (show the source-of-truth number).
3. Status chips: green tested, amber built but never tested, grey placeholder/plan, brown hand-written, blue learned: right for each claim? Illustrations (made-up examples, shaded vectors, a stop firing at round 4) must be visibly labelled.
4. ELI5 and glossary: plain word first, code name only as a small tag, every term explained at first use in the chapter, same analogy and colours as `kit/GLOSSARY.md`.
5. Apply the cut rules above (dangling pointers, numbering).
6. Fix in place with minimal edits in your working copy: wrong value, softened claim, added caveat, added label. A caption you lengthen must still pass `node tools/audit.mjs chNN` (reading budget: duration >= 3 + words/2.6 s; caption <= 26 words / 150 characters each; if TOO SHORT, raise that scene's `duration`, never cut a caveat).
   Keep scene ids and the animation unless a fix requires a change. If a whole scene is unsupported, rewrite it from the sources.
7. Gates: audit 0 flags and `check` says "Check passed". Then `node tools/shots.mjs chNN --per 4` and look at 2-3 sheets yourself to confirm your edits did not break the layout (text must still fit its boxes).
8. Deliver to `FINAL/out/chNN/`: `chNN.json`, `chNN.js`, `verify.md` (table of every number checked: scene, number, source file:line, match/mismatch; list of changes: scene, before, after, why; things you could not verify and what you did; verdict clean/fixed/needs human),
   and the final sheets copied to `FINAL/out/chNN/sheets/` (all `sheet-*.jpg`). Final message = the JSON the coordinator asked for.

## Role: LOOKER (Haiku; stay under 100k tokens; report only)
You are given a list of sheet files (`FINAL/out/chNN/sheets/sheet-XX.jpg`). Open each with the Read tool. Each sheet has six panels (2 columns x 3 rows), each labelled `sNN @T s` = scene and time. Each scene has about four panels spread across it:
early panels may legitimately be partly built (things are still arriving); the LAST panel of a scene must show the complete, tidy picture.
Report each defect you can actually SEE (never guess at something you cannot see). Checklist:
1. text cut off, overflowing its box, or running off the screen; 2. elements overlapping each other or the caption; 3. anything of the picture below the caption line (the white caption box sits at the bottom; nothing else may be below the top of it);
4. text too small to read at this panel size, or low contrast; 5. an arrow that does not touch what it points at, or points the wrong way; 6. the last panel of a scene looks empty or half-built; 7. status chip colours wrong (green = tested, amber = built never tested, grey = placeholder/plan);
8. a number on the picture that differs from the number in the caption of the same panel; 9. a heading that wraps onto two lines and touches the picture; 10. something that looks like a real measurement but is not labelled as an illustration; 11. very unbalanced layout (minor).
Severity: `blocking` = unreadable, cut off, overlapping, wrong number or wrong colour meaning; `minor` = taste. Return only the structured list; do not edit any file.

## Role: FIXER (Sonnet)
Input: the chapter in `FINAL/out/chNN/` plus the lookers' defect lists. For each defect: look at the scene yourself first (`node tools/shots.mjs chNN sNN --per 4` in a working copy built from `FINAL/out/chNN/`); if it is not real, say so.
Fix real defects in `chNN.js` / `chNN.json` (positions, sizes, widths, line wrapping, label text length, timing of reveals) with minimal edits; never change a number or claim (if the picture needs a claim changed, report it instead). Re-run audit, `check`, and `shots` for the changed scenes and look at the result.
Write the fixed files back to `FINAL/out/chNN/` (and refreshed `sheets/`) and add `fix.md` (defect, real or not, what you changed, result). Return the structured summary.
