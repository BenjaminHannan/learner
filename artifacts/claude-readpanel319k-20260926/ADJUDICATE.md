# Adjudicator brief: readpanel319k (TEST-ONLY)
Never use WebFetch or any web access. Open only: this file, LABELLER.md (the rules), blind_rows.jsonl (the dialogs; read
the whole dialog around each disputed row) and disputes.jsonl (14 rows where two independent labellers, A and B,
disagree), all in /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/rp319k. Never open panel.jsonl, label_B.jsonl, WRITER.md or WRITER_NOTES.md.
For each disputed row decide the correct facts (with the correction flag) and replaced list under LABELLER.md's rules.
Where a fact is genuinely ambiguous (reasonable people would disagree whether it is a stated, current fact about that
owner, or whether it replaces an earlier value), mark the row "drop" so it leaves the test rather than guessing. Keep
values short and verbatim from the turn; owner "USER" for the speaker; replaced values as written earlier.
Write /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/rp319k/resolved.jsonl, one line per disputed row:
{"id","facts":[{"owner","relation","value","needs_history","correction"}],"replaced":[{"owner","relation","value"}],
 "drop":false|true,"why":"one short phrase naming the rule"}
needs_history true only when the owner can't be known from the turn plus prev_reply alone.
Reply with counts only: rows kept as A, kept as B, merged/other, dropped. Quote no dialog text.
