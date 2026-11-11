# Critical-thinking reasoner: working notes (handed over 13:44 UTC 10-03)

Work on PR #23 moved to the Opus thread "Critical-thinking reasoner (Opus)". These are the raw notes from the first thread, pushed as-is so nothing is lost. All are design-only subagent outputs; nothing was trained or run. Treat numbers from papers as unverified until the paper itself is opened.

| File | What | Status |
|---|---|---|
| brief.md, shape-brief.md | Briefs given to the subagents | complete |
| opus-mechanism.md, opus-curriculum.md | First two design reports, merged into ../critical-thinking-reasoner-design.md | complete |
| shape-world.md | Online search: world-model / planning / agent shapes (top pick: score every move then branch) | complete |
| shape-memory.md | Online search: memory / hybrid shapes (top pick: Canon layers; TTT/Titans/Mamba dropped as fast weights under another name) | complete |
| shape-looped.md | Online search: looped / recursive shapes (partial-step updates, state lanes, unshared pre-block) | written, but the agent was stopped before its final repo cross-check |
| v5-check.md | 18 edits to PR #23 from the integrated design doc v5 | complete; edit 6 is out of date (see below) |
| f1_analysis.py, f1_results.json, f1_stdout.txt | Free check F1 (error shape) on the 128 saved outputs | PARTIAL: the analysis ran, but the report applying the pre-committed F1 readings (commit 8c49c5430) was not written. F0 not written. |

Corrections the next owner should know:
- v5-check edit 6 (budget/GPU) reflects CURRENT.json at 11:38 UTC. Ben later chose "Stop Qwen now" (11:59 UTC, PC GPU full time for Premonition) and authorized the whole remaining vast.ai credit (12:39 UTC). Check current state before applying it.
- The "128-question panel" is 16 questions (8 ADD/SUB pairs) x 8 checkpoints (2 seeds x static/contextual input x 2 LRs). Answers are two-digit single tokens. All but one call fired at loop 0 (f1_stdout.txt).
- Data: branch claude/critical-thinking-data-128-outputs, folder data-for-design/critical-thinking-128/. Consumed panel; GOLD is study-only, never a score.
