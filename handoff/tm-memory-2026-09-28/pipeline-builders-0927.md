---
name: pipeline-builders-0927
description: Queue builders since 09-27 03:17 UTC run on rungo5 (free Zen Muse, then free mimo); Luna only as text helper; kill/Luna-builder refused for the Director
metadata:
  type: project
  modified: 2026-09-27T04:09:09.081Z
---
- 09-27 ~00:57 UTC Ben's opencode Go plan hit its WEEKLY usage limit. Every opencode-go model (muse-spark contributor, glm-5.3-flash, qwen) hangs. Builders stuck at "> build" with 0-byte replies.
- Fix: watcher.sh deploys handoff/kit/mimo/rungo5.sh from main into ~/premonition-watch each round. Builder chain: opencode/muse-spark-1.3-contributor-free, then opencode/mimo-v2.6-flash-free. No Go fallback. At most 2 rungo5 builders at once. Local cap MAX=8. A `LOAD-LIGHT: yes` header skips the load hold.
- Luna (GPT-6 Luna, model id gpt-6-luna, bundled codex CLI at /Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex) serves as the text/data helper scripts/claude_luna_codex.py (sha 342a0fb7…024e). Ben said 03:47 that Luna may write training data. Route budget: 15 parallel since 09:56 UTC 09-27 (lis-320 6, y1t 3, rd-378 3, mu-407/g406 2, k1h 1, bm398w 1 via handoff/luna-w/bm398w.txt); drop a share back if Luna limit errors appear. BASH-ONLY: yes jobs (no LLM builder, max 5 non-000 at once) are the route for fixed-script jobs; BensPC ssh shell is cmd.exe.
- The Director's permission check REFUSED: (a) killing hung builder PIDs, even with Ben's cited yes (3 tries); (b) Luna as a builder. Don't retry either. Kills go through Ben's Mac Claude or through an owner's own 000-stop job.
- The Mac worktree W is on branch claude/card-experiment-handoff-7c5b27, not main. Jobs must fetch main files themselves (git archive / checkout origin/main -- file). Builders can't git push; the watcher carries results via runs/ on builder-outbox.
Related: [[thread-manager-spending]]
