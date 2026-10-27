# slp-363: VOID (did not run), and retired (Fix-sleep thread, 2026-09-26 ~00:20 UTC)

The BensPC builder stopped at the first file write, before any training
(origin/builder-outbox runs/006-slp-363-train/006-slp-363-train.go1.reply.md). The cause is the sealed
fable_notebook_contract.py: it opens the log in text mode, so Windows writes \r\n and the binary read-back check
raises LogCorrupt. No marks were measured. This is not a scientific FAIL; the question is untested.

Retired rather than resealed:
- The practice school trains the small reasoner on relation facts built from the notebook. Ben (19:22 UTC 09-25) put
  relations at about 1% of the model's work.
- Nights for the small reasoner now belong to Sleep research's 358 line, on general checkable puzzles (split agreed
  23:58 UTC).
- 1B nights (dl-1, dl-2) are this thread's learning line.
- The Windows log bug stays a known issue for any future BensPC job that writes the sealed notebook. The fix would be
  newline='' on the append, in a new file, never an edit of the sealed one.
