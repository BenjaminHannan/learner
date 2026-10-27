---
name: run-note-at-start
description: Every run a thread starts (CPU, BensPC or rental) gets a committed run/RUN-NOTE.md within minutes of starting; Thread manager rule, 2026-09-26 23:55 UTC
metadata:
  type: feedback
  modified: 2026-09-26T23:50:18.177Z
---
When a run starts, commit `artifacts/<exp>/run/RUN-NOTE.md` within minutes. It holds:
- the start time from `date -u`;
- the PIDs;
- the machine or container;
- the expected steps and an estimated finish.

Never commit a log that is still being written. If an auto-start was expected but the run has not started, say why.

**Why:** the Thread manager could not tell whether rsn-358e3 had started, because the folder held only PASSMARKS and the seal. It was running on the sleep-research container's CPU, but nothing on main said so. All threads now follow this rule.
**How to apply:** put the run-note write inside the launcher script itself (right after the date stamp) so it can't be forgotten. See [[autocast-cache-bug]] for why the torch version belongs in the note too.
