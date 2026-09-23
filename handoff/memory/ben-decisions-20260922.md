---
name: ben-decisions-20260922
description: "Ben's 2026-09-22 morning rulings — one user \"me\", verb facts as relations, silent typo fix, \"Say X\" = pretend, two-hop corrections ask, DB compaction OK, no agent cap"
metadata: 
  node_type: memory
  type: project
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-22T11:10:11.329Z
---

Ben's rulings on the morning-report decisions (2026-09-22):
1. "me" / "my" = the user. There is only one user.
2. Verb facts ("Kwame lives in Accra"): anything that can be read as a relation should be. Ben expects these to end up in the weights eventually (notebook first, then sleep consolidation).
3. Typos ("toms boss"): fix silently.
4. "Say Kim's boss is Lee." = pretend (or a request for the agent to say it). Never save it; treat it like Suppose/Imagine.
5. A correction after a two-hop answer ("No, Milan."): ask which fact is meant; don't guess the last hop.
6. OK to clear or compact opencode sessions myself.
7. Don't cap agents for disk reasons. Delete finished agent sessions instead.
8. "language" is multi-valued (a person can speak several); citizenship stays single-valued (exp 154e / task 191).

**Why:** these unblock the parser and correction work that was waiting on Ben.

**How to apply:** write these into sealed marks for the follow-ups (the 160c two-hop clarify, the pretend-"Say" guard, the typo normaliser, the self "me" entity, verb-relation patterns). Related: [[disk-full-agent-limit]], [[teachable-assistant-goal]].
