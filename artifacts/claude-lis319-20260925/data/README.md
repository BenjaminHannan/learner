# lis-319 history training rows (2026-09-25)

Written from scratch by 3 Opus agents (brief WRITER319.md), 500 rows each, 60 dialogs of 8-9 turns per file.
No LoCoMo or LongMemEval text and nothing built from them; no panel (incl. readpanel319) or bank A/B was read;
0 DEV names (dev_names check, 81 names). Families per file: backref 170, local 110, ask 50, short_answer 40,
correct 40, ambiguous 30, nosave 30, smalltalk 30.
Blind second labeller (LABELLER319.md) per file saw only id, dialog, t, prev_reply, turn, in dialog order: label_B_h*.jsonl.
Agreement: scripts/claude_lis319_agree.py = the lis-300 rule, but the checker's "previous text" is the dialog's
earlier turns and replies plus prev_reply. (With the plain lis-300 checker every back-reference owner fails
owner_not_span in both labels, so those rows would "agree" by saving nothing: 0 of 223 agreed back-reference facts
in h1 would save.) Agreed 1,417 of 1,500 (h1 486, h2 465, h3 466); per family agreed / written:
ambiguous 88/90, ask 143/150, backref 478/510, correct 112/120, local 307/330, nosave 88/90, short_answer 112/120,
smalltalk 89/90.
Known convention split the filter does not remove: the h1 writer and labeller both wrote nosave turns as act CHAT,
facts []; h2/h3 (and lis-318) label them PLAN / REPORTED / SUPPOSE facts. Neither saves anything.
Builder dry run (CPU, scripts/claude_lis319_data.py): train 50,044 (o0b 27,000, opus 5,012, opus301 4,960,
chat318 7,936 after dropping UNCLEAR rows, hist319 5,136 = 1,284 x 4), dev 1,311 (lis-301's 959 + chat318_dev 219
+ hist319_dev 133, split by dialog). Longest prompt+target 1,628 characters (fits --max-len 512).
