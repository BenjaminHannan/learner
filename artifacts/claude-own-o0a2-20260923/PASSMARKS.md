# own-O0a2 PASSMARKS (sealed BEFORE the registered run)

Follow-up to the registered FAIL of own-O0a (oracle coverage 184/272 = 67.6%,
bar 85%). Diagnosis: 59 of 88 misses were "no relation cue" (v0 accepted only
the exact relation name/alias as a whole-word span). ONE change (rule v1):
a relation cue also counts when a whole-word span of the turn is
(a) a plural or possessive form of the relation's name or alias
(add s/es, 's, s'), or
(b) the fixed words of one of that relation's own "teach" templates in
artifacts/claude-smolear257-20260922/relation_table_v2.json
(template text with {X} and {Y} removed, e.g. "lives in", "moved to").
Everything else unchanged: value and owner must be exact whole-word spans
(typos still need asking), modes ASSERT/CORRECT/DENY only, OTHER never
writable.

Fresh dev set: 300 turns written before any rule code (180 statement /
80 no-save / 40 mixed), ACD gold facts = 281. The old 300 turns found the
diagnosis, so they cannot test the fix. This dev set deliberately contains
many plural and verb-template wordings (the diagnosed miss classes).

## Marks

- Pown0a2.1 (bar): v1 rule, WE not allowed: auto-writable >= 85% of the 281
  ASSERT/CORRECT/DENY gold facts. Predicted: ~252/281 (~90%).
  Misses predicted: 5 typo + 5 OTHER + 3 no-cue + 2 owner-not-span
  + 2 inflection + 2 irregular-plural(children) + 10 WE = ~29.
  Proves v1 wrong: below 85%.
- Pown0a2.2 (bar): no-save-mode facts writable = 0 under all three rules
  (v0, v1, learned-licensed) x WE allowed/not allowed (6 columns).
  Predicted 0 in all 6 (by construction: mode gate is first).
- Pown0a2.3 (report only): v0 ceiling and learned-licensed ceiling, WE both
  ways. Predicted v0 WE-not-allowed ~120/281 (~43%), v0 WE-allowed ~130/281;
  learned-licensed WE-not-allowed ~259/281 (~92%), WE-allowed ~269/281 (~96%).

## Method

- v0 column uses the same code as own-O0a (imported read-only from
  scripts/claude_own_o0a_compiler.py: toks, has_span, same cue expression).
- v1 adds plural/possessive cue variants and per-relation teach-template
  fixed words (alternations expanded, {X}/{Y} removed, contiguous
  whole-word span match). Learned-licensed drops the cue requirement
  (relation only needs to be in the table); spans and modes unchanged.
- One registered run on the sealed fresh turns. No tuning on these turns
  after the run: any post-seal change = FAIL.
