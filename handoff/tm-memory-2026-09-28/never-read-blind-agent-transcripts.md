---
name: never-read-blind-agent-transcripts
description: Never tail or read a blind writer/auditor/judge agent's output transcript; it echoes TEST-ONLY panel text into the builder's context
metadata:
  type: feedback
  modified: 2026-09-26T13:59:48.201Z
---
2026-09-26 ~13:58 UTC (everyday-chat thread, ch-403): while a blind auditor agent was still running, I ran `tail` on its task output file (/tmp/claude-0/.../tasks/<agent>.output) to check progress. That file is the agent's whole transcript, including its tool results, so it printed 3 conversations of the TEST-ONLY panel (chat403-58..60) into the build side's context. Code was already committed, but the panel was no longer fully unseen; the fix was to disclose it in PASSMARKS and have a fresh blind writer replace the seen conversations before sealing.

**Why:** blind panels are never read by the build side; a transcript tail is reading.

**How to apply:** to check a blind agent's progress, only `ls -la` its output folder (names, sizes, times) or run a counts-only checker on its files. [[verify-subagent-writes]] says to confirm "finished" from the tasks/<id>.output transcript: for blind agents do that with a script that prints only each line's type and whether the last entry is final assistant text, never the text itself. Never `tail`, `cat` or grep the task output file of a writer, auditor or judge. Put "your final reply: counts and ids only" in its prompt. Related: [[verify-subagent-writes]].
