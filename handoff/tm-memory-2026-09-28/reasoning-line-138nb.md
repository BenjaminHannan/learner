---
name: reasoning-line-138nb
description: Reasoning line (rsn-) state 2026-09-23 20:20 UTC: 292 main base; reader is F0's blocker; 294 learned brain-style reasoner registered and queued
metadata:
  type: project
---
Thread "Inverse fix and base merge" (cmsg_01FuvegZXjMmeUzStiEFVnEWMJUVXXZw5YaySDwW7qo6Ti) runs the reasoning line. Numbers: rsn owns 266, 268, 290-299; next free 294.

- Lineage (all verified, 2026-09-23): 138nb PASS (inverse label). 266/266b, 268/268b = registered FAILs ruled merge candidates. 291 (138nb+260+252c) FAIL on strict bars but ruled the base (73/96 corrections vs 138p 65). 293 yes/no reader PASS (85/85). 292 = 291+266b+268b+293 VERIFIED PASS 13:45 UTC (mixpanel292 73/80, 0 wrong; 291 got 35). 292 is the main base; 292t (talking layers) is the talking line's candidate.
- Cloud probing: `pip install torch numpy`; stub fable_self122.route122 to DECLINE (MiniLM download blocked); use module DEFAULT_CONFIGs, not config JSONs (Mac paths).
- Open leads: verb-worded denials fail on every arm; chain inside a yes/no question; the 268b employer shape; birthplace vs place_of_birth key.
- 19:05 UTC, Ben asked "make the reasoning model bigger?": F0 on 292, 84 ask turns: 6 right; 65 fact never saved (teach misread); 12 fact saved but question misread (7 "didn't understand", 5 relation parsed with "called"/"named" glued on); 1 wrong (correction not heard). Reasoning failures: 0. Every F0 question is a one-step lookup. Fix = the reader (lis-301 into 292t, scored on F0).

- 20:20 UTC: Ben wants a learned, brain-like reasoner (bulk of the model, RL, "emulate a brain but better", innovative). 294 = loop reasoner (2x1024 layers re-applied) vs equal-size plain (6x640), about 30.8M each, copy then practice RL, answers only copied from cited rows plus a code fact-check. Registered on blind reasonpanel294 v3 (items-v3.jsonl; v1 had 9 bad count golds). Code arm 210/300. Queued rsn-294-train (GPU rent). Plan design/v3/30-modes/294-learned-reasoner-plan.md; 295 = 1B RL add-on. Ben's $50 budget question is pending on a decision card.

**Why:** comparisons are valid only under the same runner and scorer; a bigger model only helps where the failure is.
**How to apply:** re-run the registered arm with its own scorer before any comparison (100% fidelity). Test a bigger or learned reasoner only once a benchmark has multi-fact questions that the reader reads right. See [[director-role]].
