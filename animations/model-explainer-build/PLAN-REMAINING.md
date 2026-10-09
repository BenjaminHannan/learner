# Explainer: what is done, what is left, how to finish it (written 10-09, about 4 PM ET)

Ben's rules for this job: Sonnet agents write code and scene files; Haiku agents (under 100k context) do the research and looking BEFORE coding; no deadline, be comprehensive. Weekly usage was 96% at 4 PM ET (resets 7 AM ET 10-10), so the big waves below wait for the reset.

## Done (all committed on branch claude/learner-new-g2)
- Delivered chapters: ch01 (424 s), ch03 (425), ch04 (471), ch05 (529), ch06 (413), ch09 (326). All pass audit (0 flags) and `check`. Notes in chapters-out/chNN/notes.md (ch03-ch06 generated from the JSON; ch01/ch09 by their authors).
- Browser preview of those six (43 min): `preview/watch.html` (see preview/README.md); rebuild with `./build-preview.sh` (needs Node 22: animations/.tools/node-v22.23.3-darwin-arm64/bin).
- Picture review, first pass: six Haiku reviewers already looked at ch03, ch05, ch06 sheets (reports are cached in workflow run wf_d5425066-799). The three Sonnet fixers were stopped before finishing. Resume with `Workflow({scriptPath: '<session>/workflows/scripts/explainer-picture-review-b-wf_d5425066-799.js', resumeFromRunId: 'wf_d5425066-799'})`: the six looks replay from cache and only the fixers run.

## Left
1. Fixers for ch03, ch05, ch06 (above). Then the same Haiku-look + Sonnet-fix pass for ch01 (sheets 1-11; only sheet 5 was ever viewed), ch04 (sheets 3-10; 1-2 viewed) and ch09 (8 sheets, never reviewed).
2. Nine chapters not written: ch00, ch02, ch07, ch08, ch10, ch11, ch12, ch13, ch14 (briefs in kit/briefs/). Target about 60 min in total (briefs give 150-380 s each).
3. One Sonnet checker per chapter (kit/VERIFIER-GUIDE.md): every number on screen against its source; ch09 has never been checked.
4. Assemble all chapters (`tools/assemble.mjs` reads /mnt/project-files; use build-preview.sh logic instead), `check`, then render.
5. Render needs an arm64 ffmpeg (the Mac's /usr/local/bin ffmpeg is Intel-only and fails). `brew install ffmpeg` is a download: ask Ben first. A 60-minute 1080p/30 fps render will take hours; plan chunked renders (`window.ONLY` / `--only chNN` keeps global progress-bar positions) and `render --fps 30 --quality standard --workers 4`.

## Pipeline per remaining chapter (agents: R = Haiku researcher, W = Sonnet writer, L = Haiku looker, F = Sonnet fixer, V = Sonnet checker)
- R1: read the chapter's brief and the sources it names (PFS = scratchpad/pfs/project-files-snapshot; sources/ folder), return a dossier: every fact and number with a file:line src, plus what the brief wants that no source supports. Read-only, under 100k tokens.
- R2: read what the earlier chapters already say about the same facts (chapters-out/*/chNN.json, grep only) so numbers and wording stay identical; list overlaps and conflicts.
- W: Sonnet author writes content/chNN.json and chapters/chNN.js from the dossier, loop from AGENT-GUIDE section 8 (merge, mkindex --only, audit, check, shots), views at most 3 sheets, delivers to chapters-out/chNN/. Splits into JSON phase and JS phase if the chapter has more than 12 scenes.
- L: two Haiku slice reviewers per chapter (sheets 1-5, 6-N), report-only, schema as in explainer-picture-review-b.
- F: Sonnet fixer verifies each reported defect on the sheet, fixes, runs gates, delivers.
- V: Sonnet checker per VERIFIER-GUIDE; Haiku researcher pre-pass lists each number with its source line.
Keep each workflow at 6-9 agents; run chapters in pairs so the box (4-10 CPUs) is not swamped. Haiku agents use agentType haiku-lean (shell/file tools only); Sonnet agents use agentType general-purpose with model 'sonnet'.

## Hard-won rules (from wave 1 and 2)
- Haiku authors run out of context when they read the whole guide plus every sheet and then write code: give them one small job and a short brief; make every agent end with StructuredOutput early (handoff if past ~60k).
- Never put the kit's CSS class or id names in new UI (`.t`, `#tm`, `#sc`, `#ch`, `#sp` clash with kit style.css).
- Every on-screen number needs a src in the content JSON; illustrations say "picture only" or "made-up example".
