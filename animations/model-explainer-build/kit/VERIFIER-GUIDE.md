# Guide for chapter checkers

You check ONE finished chapter of a long silent explainer video about a research AI model. A different author wrote it from project files.
Your job is to find every claim on screen that the sources do not support, and fix it. You did not write the chapter, so do not defend it.

Inputs: `/mnt/project-files/animations/model-explainer-build/chapters-out/chNN/` holds `chNN.json` (every word and number on screen), `chNN.js` (the animation code),
`notes.md` (the author's own list of sources, computed numbers, disagreements). Sources are under `/mnt/project-files` and the repo at `/home/user/learner`;
the PR bodies are saved in `/mnt/project-files/animations/model-explainer-build/sources/`. The newest source of truth for how the finished model works is
`/mnt/project-files/architecture/FINISHED-MODEL-2026-10-09.md`; older pages describe older designs (17 thinker vectors, 8 rounds, calculator inside).

## What to check, in this order

1. **Every number** on screen (JSON values, captions, labels, and numbers written in the JS builder), against the source the scene's `src` names. Open the source and find the number.
   Record: scene, number, where you found it (file + line or section), match / mismatch. Numbers the author computed must be flagged in the caption and explained in `notes`: recompute them.
2. **Every factual sentence** in captions and labels: is it in the sources, said at the same strength? Watch for: "proves/shows" where the source says "suggested" or "untested";
   a result called tested when it only ran once at the smallest size; a plan stated as done; an older design's number used for the current model; dates stated as certain.
3. **Status chips** (green tested / amber built never tested / grey placeholder): is each one right? Look at the JS for `S.chip(` calls and the JSON labels.
4. **Illustrations**: anything made up must be visibly labelled. Anything that looks like a measurement but is not in a source is a fault.
5. **Code names and plain words**: plain name first, code name only as a small tag; no unexplained jargon.
6. **Consistency with the glossary** (`kit/GLOSSARY.md`): the same analogy, the same colours per part, the same words.
7. Read the JS builders for strings written in code (not in JSON). Every on-screen string except symbols and default chip words must be in the JSON; move any offender into the JSON.

## How to fix

- Fix in place in the delivered files (`chNN.json`, and `chNN.js` only where a string or number is in the code). Minimal edits: change the wrong value, soften the claim, add the caveat, add the missing label.
- A caption you lengthen must still pass the reading-speed audit: copy the kit to a scratch folder as the author guide says (kit path `/mnt/project-files/animations/model-explainer-build/kit/`; work copy
  `/tmp/claude-0/-home-user-learner/01bcea25-2484-5edd-8248-d1fe6e738ef5/scratchpad/hf/verify/chNN`), put the chapter files in `content/` and `chapters/`, run `node tools/merge.mjs && node tools/mkindex.mjs --only chNN && node tools/audit.mjs chNN`.
  If it says TOO SHORT, raise that scene's `duration` (do not cut the caveat).
- If a whole scene is unsupported, rewrite it from the sources or replace it with a short honest scene; keep the scene id.
- If sources disagree, show the source-of-truth number and say so in the verifier log.
- Do not change the chapter's structure or animation unless a fix requires it. Do not run `hyperframes render`. Do not call any `mcp__hearthbot__` tool. Do not touch protected/sealed panels.

## Deliver

Write `/mnt/project-files/animations/model-explainer-build/chapters-out/chNN/verify.md`:
- table of every number checked (scene, number, source, result), grouped by scene;
- list of every change made (scene, before, after, why);
- list of things you could not verify (and what you did about them);
- one line: verdict (clean / fixed / needs the author or project owner).
Final message to the coordinator: at most 150 words: counts (numbers checked, mismatches fixed, unverifiable), and anything needing a human decision.
