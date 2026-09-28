---
name: opus-key-audit
description: 2026-09-23 answer-key audit: 2 blind Opus labellers vs Opus-written key, 0 clear errors in 100; negatives rule missing
metadata:
  type: project
---
Replaced Ben's hand-labelling (he refused, 10:32 UTC). Files: reviews/keyaudit-2026-09-23/ (audit-results.md, messages, ai_key, label_A/B).
Result: 0 clear key errors / 100; 4 policy disputes: negatives (57, 94: both labellers save "dog: none", key saves nothing) and "so X is Y" without "?" (7, 97: 2 of 3 say don't save).
Caveat: labellers got the same rules as the key (blind to answers, not policy). Says nothing about Muse-written keys.
**How to apply:** check every Muse-written key with 2 blind Opus labellers before grading. Director ruled 10:37 (design/v3/30-modes/key-writing-rules.md): negatives save nothing (tag negation; deletion is the deny path); "so X is Y"/"right"/"yeah" = ASK/confirm gold; plural frame naming either true name = correct. See [[no-gpt-prompts-use-opus-agents]].
