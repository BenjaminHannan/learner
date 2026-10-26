# English eval sets for Test B1 (copied, read-only)

Copied unchanged from branch `claude/project-thread-utxkpw`, commit `338e22ba9`, folder `reasoner_ptr/real/english/`,
so a staged `custom_io/` carries them to Ben's machines. Never train on these. They are not GOLD-PRIVATE, reserved or
blind panels.

| file | examples | what it tests | sha256 |
|---|---|---|---|
| FRESH-EN-R3.json | 48 | the 6 practised round-4 kinds, human wording | 9e0ca5b5b069b6592e6a3c1639c202942f6f8d85b29057e317437f26741037b9 |
| NEW-KINDS-R5.json | 48 | 6 kinds neither B1 arm practises | eafb2a556ba8db591a50b662e2ad751c87c75fa64c984873f083043c5ea869bc |
| NEW-KINDS2-R6.json | 48 | 6 more kinds neither arm practises | a3b8ec7baddbc605a7faea8996d555d492ea801d1bbbac8624e76c5fdafe7b5b |
| GEN-HELDOUT-R4.json | 48 | generator kinds; held out for round 4, but most of its names and nouns are in the B1 GEN arm's training pools, so it is that arm's own distribution (read, not judged) | 25b4e951d289654557605aff32cfff7d100864a7048cae088162e68f6d42c840 |

Each example has a passage (`source_text`), a `paraphrase` and 2 questions. Each set is scored on both passages, so
it gives 192 rows.
