# chatpanel361 (2026-09-25)

User-side test panel: 12 conversations (c361-01 to c361-12), 8 to 10 user messages each, 110 user messages total. Assistant replies are not included; they are produced later by the system under test.

File: `turns.jsonl`, one object per user message with `conv_id`, `turn_index`, `kind`, `user_text`.

| kind      | count |
|-----------|------:|
| smalltalk | 25 |
| feelings  | 20 |
| advice    | 25 |
| explain   | 20 |
| followup  | 20 |
| total     | 110 |

How it was written: Claude wrote every message by hand as a blind test-data writer, without opening any existing scripts, escrow or artifacts files, varying typing style (careful, casual lowercase with slang, long, very short), and using only fictional person and pet names starting with K to O; followup turns refer back to earlier turns in the same conversation and never open a conversation.
