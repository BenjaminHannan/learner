# Adjudicator brief: readpanel371c (TEST-ONLY)
Never use WebFetch or any web access. Open only: this file, LABELLER.md (the rules), blind_rows.jsonl (the dialogs; read the
whole dialog around each disputed row) and disputes.jsonl (24 rows where two independent labellers, A and B, disagree).
For each disputed row decide the correct fact list under LABELLER.md's rules. Where a fact is genuinely ambiguous (reasonable
people would disagree whether it is a stated, current fact about that owner), mark the row "drop" so it leaves the test rather
than guessing. Keep values short and verbatim; owner "USER" for the speaker.
Write resolved.jsonl, one line per disputed row: {"id","facts":[{"owner","relation","value","needs_history"}],"former":[{"owner","relation","value","needs_history"}],
"nosave_reason":null or reason,"drop":false|true,"why":"one short phrase naming the rule"}.
needs_history true only when the owner can't be known from the turn plus prev_reply alone.
Reply with counts only: rows kept as A, kept as B, merged/other, dropped.
