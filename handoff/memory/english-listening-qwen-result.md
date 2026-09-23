---
name: english-listening-qwen-result
description: 2026-09-21 English→notebook parser with Qwen placeholder — two registered FAILs on the zero-bad-writes mark (126/150, then 141/150 with 1 reversed nickname); chat works end to end
metadata:
  type: project
---

`scripts/fable_listening_english.py` + Qwen3.8-27B (BensPC, started by hand, tunnel to 127.0.0.1:18081, ~2.5 s/sentence, thinking switched off via chat_template_kwargs).
Registered rounds (marks: 0 unsafe writes AND ≥135/150): round 1 = 126/150, 3 unsafe ("X is a person" → junk fact) → FAIL; round 2 (fresh set, frozen parser) = 141/150, 1 unsafe (nickname direction reversed, no echo) → FAIL on primary. Trap sentences (suppose / hearsay / negation) wrote nothing false in 50/50.
End-to-end `--chat --folder DIR` works: teach, two-hop ask through `self creator city`, correction with yes/no, abstains on unknown names. `self` and `Ben` entries are auto-created.

**Why:** placeholder ears so Ben can talk to it now ([[placeholder-english-ok]]); every sentence is logged as training data for our own ears ([[talker-must-be-our-architecture]]).
**How to apply:** lesson learned — take bookkeeping away from the LLM (value kind, person/alias filing, yes/no, undo are decided by plain software). Next: nicknames always echo-confirm; round 3 on a fresh GPT-written set with "unsafe = wrong write with no echo" fixed beforehand. Artifacts: `artifacts/fable-english-listening-20260921/`. The GPT bridge drops the backslash in `\"` — parse replies item by item.

**Round 3 (same day): PASS** — 140/150 exact, 0 silent wrong writes, 4 wrong-but-echoed (mark redefined in advance as 'wrong write with no yes/no echo'; under the old definition it would still fail). Nicknames now always echo. Remaining weak spots: 'wait X' without comma, 'call X Y' direction, 'friends with', dropped last hop on 3-hop questions.
