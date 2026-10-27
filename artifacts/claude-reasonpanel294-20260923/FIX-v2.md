# reasonpanel294 v2 (key fix after the blind Opus audit)

AUDIT-opus.md flagged 9 counting items (wrong_gold): each person had one extra `instrument` row
that a careful reader would also count, so the gold was one too low. Fix chosen: drop that one
distractor row in each of the 9 items (the audit's option 1). Done mechanically by the director
without reading the items: for the 9 flagged ids, remove rows with relation `instrument` whose
subject is the frame's counted person. 9 rows dropped; gold, frames and every other item are
unchanged. items.jsonl (v1) is kept as sealed. **items-v2.jsonl is the registered panel.**
