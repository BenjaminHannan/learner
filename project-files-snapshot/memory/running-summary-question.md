---
name: running-summary-question
description: Ben 8 PM ET 10-08 asked about a human-like running summary instead of attention; answer: B2 thinker already is one (Perceiver-like), add carry-over at long-input stage
metadata:
  type: project
  modified: 2026-10-09T17:34:17.797Z
---

Ben, 8:00 PM ET 10-08 (thread cmsg_01GSLCHTCnZxn7DhV19qcDvMBYeunCf3U9NTpyyYB4S9WA): humans keep "a general summary" instead of attending over every word; can we add it, would it help?
Answer (note /mnt/project-files/architecture/running-summary-2026-10-08.md): B2's thinker already is a small summary (8 controls + N_REG vectors cross-attending to all reader outputs each round, Perceiver pattern). Missing part: nothing carries over between pieces/questions. Verdict (suggested): little gain on today's short questions, could hurt copying if look-back removed (Jelassi 2402.01032); needed for long input / text world / Minecraft (RMT, BABILong 2402.10790); maybe few-example learning (Titans 2501.00663), untested; no paper shows it out-scales attention. No change to big-run recipe.
Follow-up 9:26 AM ET 10-09 (only keep important word links?): reader is local-only, thinker words never compare with each other; only frozen Gemma does all pairs and it helped (EGE +2.67). Learned picking (NSA 2502.11089) = long-input stage, not big run. Note architecture/important-links-2026-10-09.md.
Follow-up 1:32 PM ET 10-09: Sakana CMM (2610.07907) judged: our notes ~= its long-term slots; few-shot edge over RMT ~0.2; 35x memory; not for big run; optional 3M notebook test proposed, wait. Note architecture/cmm-sakana-2026-10-09.md.
Proposed, not run: free "look once" lesion on B2 confirm checkpoints (CPU, $0); Ben's call.

**Why:** a future long-input or text-world design should start from this, not redo the research.
**How to apply:** design long input as RMT-style carry-over of thinker vectors plus look-back at the current piece. Related: [[whole-model-roadmap]], [[scaling-bar-ben]], [[one-proven-run-rule]].
